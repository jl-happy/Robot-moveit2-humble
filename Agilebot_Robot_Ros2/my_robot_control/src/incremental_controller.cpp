#include <rclcpp/rclcpp.hpp>
#include <interface/srv/set_int16.hpp>               // 自定义服务：SetInt16
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <tf2_ros/buffer.h>                          // TF2 缓冲区
#include <tf2_ros/transform_listener.h>              // TF2 监听器
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>   // TF2 与几何消息转换
#include <tf2/LinearMath/Quaternion.h>
#include <tf2/LinearMath/Matrix3x3.h>
#include <cmath>

/**
 * @brief 增量控制器节点
 * 
 * 功能：
 * 1. 提供服务 /joint_teleop   : 控制单个关节增量运动
 * 2. 提供服务 /cart_teleop    : 控制末端笛卡尔增量运动
 * 3. 订阅 /joint_states 获取最新关节状态
 * 4. 发布增量目标到 /joint_goal 和 /cartesian_goal，由 cartesian_controller 执行
 */
class IncrementalController : public rclcpp::Node
{
public:
    IncrementalController() : Node("incremental_controller")
    {
        // 声明参数
        this->declare_parameter<std::string>("reference_frame", "base_link");
        this->declare_parameter<std::string>("tip_frame", "link6");
        this->declare_parameter<double>("joint_step", 0.1);        // 关节步长（弧度）
        this->declare_parameter<double>("cart_step_trans", 0.01);  // 平移步长（米）
        this->declare_parameter<double>("cart_step_rot", 0.1);     // 旋转步长（弧度）

        // 读取参数
        reference_frame_ = this->get_parameter("reference_frame").as_string();
        tip_frame_ = this->get_parameter("tip_frame").as_string();
        joint_step_ = this->get_parameter("joint_step").as_double();
        cart_step_trans_ = this->get_parameter("cart_step_trans").as_double();
        cart_step_rot_ = this->get_parameter("cart_step_rot").as_double();

        // 创建 TF2 缓冲区和监听器
        tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

        // 订阅关节状态，用于获取当前关节角度
        joint_state_sub_ = this->create_subscription<sensor_msgs::msg::JointState>(
            "joint_states", 10,
            std::bind(&IncrementalController::jointStateCallback, this, std::placeholders::_1)
        );

        // 创建发布器，将增量目标发送给 cartesian_controller
        joint_goal_pub_ = this->create_publisher<sensor_msgs::msg::JointState>("joint_goal", 10);
        cart_goal_pub_ = this->create_publisher<geometry_msgs::msg::PoseStamped>("cartesian_goal", 10);

        using namespace std::placeholders;
        // 创建服务：关节增量
        joint_teleop_srv_ = this->create_service<interface::srv::SetInt16>(
            "joint_teleop",
            std::bind(&IncrementalController::handleJointTeleop, this, _1, _2)
        );
        // 创建服务：笛卡尔增量
        cart_teleop_srv_ = this->create_service<interface::srv::SetInt16>(
            "cart_teleop",
            std::bind(&IncrementalController::handleCartTeleop, this, _1, _2)
        );

        RCLCPP_INFO(this->get_logger(), "Incremental controller started");
    }

private:
    /**
     * @brief 关节状态回调，保存最新状态
     */
    void jointStateCallback(const sensor_msgs::msg::JointState::SharedPtr msg)
    {
        latest_joint_state_ = *msg;
        joint_state_received_ = true;
    }

    /**
     * @brief 处理关节增量服务请求
     * 
     * 请求数据说明：
     *   req->data 的绝对值 = 关节编号（1~N）
     *   正号表示正向增加角度，负号表示反向减小
     */
    void handleJointTeleop(const std::shared_ptr<interface::srv::SetInt16::Request> req,
                           std::shared_ptr<interface::srv::SetInt16::Response> resp)
    {
        if (!joint_state_received_) {
            resp->success = false;
            resp->message = "No joint state received yet";
            return;
        }

        int joint_idx = std::abs(req->data) - 1;  // 转为0基索引
        if (joint_idx < 0 || joint_idx >= (int)latest_joint_state_.position.size()) {
            resp->success = false;
            resp->message = "Invalid joint number";
            return;
        }

        // 确定步长方向
        double step = joint_step_;
        if (req->data < 0) step = -step;

        // 构造新的关节目标（当前值加上步长）
        sensor_msgs::msg::JointState goal = latest_joint_state_;
        goal.position[joint_idx] += step;

        // 发布到 /joint_goal，由 cartesian_controller 执行
        joint_goal_pub_->publish(goal);

        resp->success = true;
        resp->message = "Joint teleop command sent";
    }

    /**
     * @brief 处理笛卡尔增量服务请求
     * 
     * 请求数据说明：
     *   req->data 的绝对值 = 操作类型：
     *       1: X 平移
     *       2: Y 平移
     *       3: Z 平移
     *       4: 绕 X 轴旋转 (Rx)
     *       5: 绕 Y 轴旋转 (Ry)
     *       6: 绕 Z 轴旋转 (Rz)
     *   正负号表示方向（+ 增加/正转，- 减少/反转）
     */
    void handleCartTeleop(const std::shared_ptr<interface::srv::SetInt16::Request> req,
                          std::shared_ptr<interface::srv::SetInt16::Response> resp)
    {
        // 获取当前末端在参考坐标系下的位姿
        geometry_msgs::msg::PoseStamped current_pose;
        try {
            auto transform = tf_buffer_->lookupTransform(
                reference_frame_, tip_frame_,
                tf2::TimePointZero, tf2::durationFromSec(1.0) // 超时1秒
            );
            current_pose.header.frame_id = reference_frame_;
            current_pose.header.stamp = this->now();
            current_pose.pose.position.x = transform.transform.translation.x;
            current_pose.pose.position.y = transform.transform.translation.y;
            current_pose.pose.position.z = transform.transform.translation.z;
            current_pose.pose.orientation = transform.transform.rotation;
        } catch (const tf2::TransformException &ex) {
            resp->success = false;
            resp->message = "Failed to get current pose: " + std::string(ex.what());
            return;
        }

        int op = std::abs(req->data);          // 操作类型
        double direction = (req->data > 0) ? 1.0 : -1.0;
        geometry_msgs::msg::Pose target_pose = current_pose.pose; // 复制当前位姿

        switch (op) {
            // 平移
            case 1: target_pose.position.x += direction * cart_step_trans_; break;
            case 2: target_pose.position.y += direction * cart_step_trans_; break;
            case 3: target_pose.position.z += direction * cart_step_trans_; break;
            // 旋转（使用四元数乘法，避免万向锁）
            case 4: case 5: case 6: {
                tf2::Quaternion q_current, q_delta;
                tf2::fromMsg(target_pose.orientation, q_current);  // 当前姿态的四元数
                
                // 构造增量四元数（绕对应轴旋转 direction * cart_step_rot_ 弧度）
                double angle = direction * cart_step_rot_;
                if (op == 4)      q_delta.setRPY(angle, 0.0, 0.0);  // Rx
                else if (op == 5) q_delta.setRPY(0.0, angle, 0.0);  // Ry
                else              q_delta.setRPY(0.0, 0.0, angle);  // Rz
                
                // 新姿态 = 增量 * 当前（世界坐标系旋转）
                tf2::Quaternion q_new = q_delta * q_current;
                q_new.normalize();                                   // 归一化
                target_pose.orientation = tf2::toMsg(q_new);
                break;
            }
            default:
                resp->success = false;
                resp->message = "Invalid operation number (use 1-6)";
                return;
        }

        // 构造目标位姿消息并发布到 /cartesian_goal
        geometry_msgs::msg::PoseStamped goal_msg;
        goal_msg.header.frame_id = reference_frame_;
        goal_msg.header.stamp = this->now();
        goal_msg.pose = target_pose;
        cart_goal_pub_->publish(goal_msg);

        resp->success = true;
        resp->message = "Cartesian teleop command sent";
    }

    // ---------- 成员变量 ----------
    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_;
    rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_state_sub_;
    rclcpp::Publisher<sensor_msgs::msg::JointState>::SharedPtr joint_goal_pub_;
    rclcpp::Publisher<geometry_msgs::msg::PoseStamped>::SharedPtr cart_goal_pub_;
    rclcpp::Service<interface::srv::SetInt16>::SharedPtr joint_teleop_srv_;
    rclcpp::Service<interface::srv::SetInt16>::SharedPtr cart_teleop_srv_;

    sensor_msgs::msg::JointState latest_joint_state_; // 最近一次关节状态
    bool joint_state_received_ = false;               // 是否已收到关节状态

    std::string reference_frame_, tip_frame_;
    double joint_step_, cart_step_trans_, cart_step_rot_;
};

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<IncrementalController>();
    rclcpp::spin(node);
    rclcpp::shutdown();
    return 0;
}