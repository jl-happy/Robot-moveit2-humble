// 笛卡尔位姿控制，速度控制，停止控制,新增关节目标控制
#include <rclcpp/rclcpp.hpp>
#include <geometry_msgs/msg/pose_stamped.hpp>
#include <sensor_msgs/msg/joint_state.hpp>
#include <std_msgs/msg/float32.hpp>
#include <std_msgs/msg/bool.hpp>
#include <moveit/move_group_interface/move_group_interface.h>
#include <moveit/planning_scene_interface/planning_scene_interface.h>
#include <tf2_ros/transform_listener.h>
#include <tf2_geometry_msgs/tf2_geometry_msgs.hpp>
#include <tf2/time.h>   // 用于 tf2::durationFromSec

/**
 * @brief 笛卡尔控制器节点
 * 
 * 功能：
 * 1. 订阅 /cartesian_goal (PoseStamped) 执行绝对笛卡尔运动
 * 2. 订阅 /joint_goal (JointState) 执行绝对关节运动
 * 3. 订阅 /velocity_scale (Float32) 动态调整速度缩放因子
 * 4. 订阅 /stop_motion (Bool) 立即停止当前运动
 * 5. 添加地面碰撞体，防止机器人向下运动过低
 * 6. 使用 MoveGroupInterface 进行运动规划与执行
 */
class CartesianController : public rclcpp::Node
{
public:
    CartesianController() : Node("cartesian_controller")
    {
        // 声明所有可配置参数，提供默认值
        this->declare_parameter<std::string>("planning_group", "arm_group");
        this->declare_parameter<std::string>("root_link", "base_link");
        this->declare_parameter<std::string>("tip_link", "link6");
        this->declare_parameter<double>("ground_z", -0.01);
        this->declare_parameter<double>("ground_size_x", 10.0);
        this->declare_parameter<double>("ground_size_y", 10.0);
        this->declare_parameter<double>("ground_size_z", 0.01);
        this->declare_parameter<double>("safety_z_offset", 0.1);
        this->declare_parameter<double>("default_velocity_scale", 0.4);
    }

    /**
     * @brief 初始化函数，必须在创建节点后调用
     * 
     * 执行顺序：
     * 1. 创建 MoveGroupInterface，并验证
     * 2. 读取参数，设置 MoveGroup 配置
     * 3. 添加地面碰撞体到规划场景
     * 4. 创建 TF2 缓冲区和监听器，并等待必要 TF
     * 5. 创建所有订阅者
     */
    void init()
    {
        RCLCPP_INFO(this->get_logger(), "Initializing CartesianController...");

        // ---------- 1. 创建 MoveGroupInterface ----------
        std::string planning_group = this->get_parameter("planning_group").as_string();
        RCLCPP_INFO(this->get_logger(), "Planning group: %s", planning_group.c_str());

        try {
            move_group_ = std::make_shared<moveit::planning_interface::MoveGroupInterface>(
                shared_from_this(), planning_group);
        } catch (const std::exception& e) {
            // 捕获异常（如规划组不存在），打印错误并关闭节点
            RCLCPP_ERROR(this->get_logger(), "Failed to create MoveGroupInterface: %s", e.what());
            rclcpp::shutdown();
            return;
        }

        if (!move_group_) {
            RCLCPP_ERROR(this->get_logger(), "MoveGroupInterface is null");
            rclcpp::shutdown();
            return;
        }

        // ---------- 2. 获取并验证参数 ----------
        reference_frame_ = move_group_->getPlanningFrame();  // MoveGroup 的规划坐标系
        root_link_ = this->get_parameter("root_link").as_string();
        tip_link_ = this->get_parameter("tip_link").as_string();

        if (tip_link_.empty()) {
            RCLCPP_ERROR(this->get_logger(), "tip_link parameter is empty");
            rclcpp::shutdown();
            return;
        }

        RCLCPP_INFO(this->get_logger(), "Reference frame: %s, root: %s, tip: %s",
                    reference_frame_.c_str(), root_link_.c_str(), tip_link_.c_str());

        // ---------- 3. 配置 MoveGroup ----------
        move_group_->setPlanningTime(20.0);               // 规划最长允许时间（秒）
        move_group_->setNumPlanningAttempts(20);          // 规划尝试次数
        move_group_->setGoalPositionTolerance(0.01);      // 位置误差容限（米）
        move_group_->setGoalOrientationTolerance(0.05);   // 姿态误差容限（弧度）
        move_group_->allowReplanning(true);                // 允许重规划（避障时有用）
        move_group_->setPlannerId("RRTConnectkConfigDefault"); // 指定规划器

        double default_scale = this->get_parameter("default_velocity_scale").as_double();
        move_group_->setMaxVelocityScalingFactor(default_scale); // 设置初始速度缩放
        RCLCPP_INFO(this->get_logger(), "Default velocity scale set to %.2f", default_scale);

        // ---------- 4. 添加地面碰撞体 ----------
        addGroundCollisionObject();

        // ---------- 5. 创建 TF2 Buffer 和 Listener ----------
        tf_buffer_ = std::make_unique<tf2_ros::Buffer>(this->get_clock());
        if (!tf_buffer_) {
            RCLCPP_ERROR(this->get_logger(), "Failed to create tf_buffer");
            rclcpp::shutdown();
            return;
        }
        tf_listener_ = std::make_shared<tf2_ros::TransformListener>(*tf_buffer_);

        // 等待必要 TF 可用（避免回调中使用时失败）
        RCLCPP_INFO(this->get_logger(), "Waiting for TF from %s to %s...", root_link_.c_str(), tip_link_.c_str());
        try {
            tf_buffer_->lookupTransform(root_link_, tip_link_, tf2::TimePointZero, tf2::durationFromSec(5.0));
            RCLCPP_INFO(this->get_logger(), "TF ready.");
        } catch (const tf2::TransformException& ex) {
            RCLCPP_WARN(this->get_logger(), "TF not ready after 5s: %s", ex.what());
            // 继续运行，回调中会处理失败
        }

        // ---------- 6. 创建订阅者和服务 ----------
        subscription_ = this->create_subscription<geometry_msgs::msg::PoseStamped>(
            "cartesian_goal", 10,
            std::bind(&CartesianController::goalCallback, this, std::placeholders::_1));

        velocity_sub_ = this->create_subscription<std_msgs::msg::Float32>(
            "velocity_scale", 10,
            std::bind(&CartesianController::velocityCallback, this, std::placeholders::_1));

        stop_sub_ = this->create_subscription<std_msgs::msg::Bool>(
            "stop_motion", 10,
            std::bind(&CartesianController::stopCallback, this, std::placeholders::_1));

        joint_goal_sub_ = this->create_subscription<sensor_msgs::msg::JointState>(
            "joint_goal", 10,
            std::bind(&CartesianController::jointGoalCallback, this, std::placeholders::_1));

        RCLCPP_INFO(this->get_logger(), "Cartesian controller initialized successfully");
    }

private:
    /**
     * @brief 向规划场景添加一个地面碰撞体，防止机器人向下运动过低
     */
    void addGroundCollisionObject()
    {
        moveit::planning_interface::PlanningSceneInterface planning_scene_interface;

        std::vector<moveit_msgs::msg::CollisionObject> collision_objects(1);
        collision_objects[0].id = "ground";
        collision_objects[0].header.frame_id = root_link_;
        collision_objects[0].operation = moveit_msgs::msg::CollisionObject::ADD;

        // 地面形状：长方体
        shape_msgs::msg::SolidPrimitive ground_primitive;
        ground_primitive.type = ground_primitive.BOX;
        ground_primitive.dimensions = {
            this->get_parameter("ground_size_x").as_double(),
            this->get_parameter("ground_size_y").as_double(),
            this->get_parameter("ground_size_z").as_double()
        };

        geometry_msgs::msg::Pose ground_pose;
        ground_pose.orientation.w = 1.0;  // 无旋转
        ground_pose.position.z = this->get_parameter("ground_z").as_double(); // 地面高度

        collision_objects[0].primitives.push_back(ground_primitive);
        collision_objects[0].primitive_poses.push_back(ground_pose);
        planning_scene_interface.applyCollisionObjects(collision_objects);
        RCLCPP_INFO(this->get_logger(), "Ground collision object added (z=%.3f)", ground_pose.position.z);
    }

    /**
     * @brief 处理绝对笛卡尔目标（来自 /cartesian_goal）
     * 
     * 1. 将目标位姿变换到 root_link 坐标系
     * 2. 检查 z 轴高度是否低于安全阈值
     * 3. 设置 MoveGroup 目标，规划并执行
     */
    void goalCallback(const geometry_msgs::msg::PoseStamped::SharedPtr msg)
    {
        if (!move_group_) {
            RCLCPP_ERROR(this->get_logger(), "goalCallback: move_group_ is null");
            return;
        }
        if (!tf_buffer_) {
            RCLCPP_ERROR(this->get_logger(), "goalCallback: tf_buffer_ is null");
            return;
        }

        std::string target_frame = msg->header.frame_id.empty() ? reference_frame_ : msg->header.frame_id;
        geometry_msgs::msg::PoseStamped pose_in_base;
        try {
            // 将目标位姿变换到 root_link_ 坐标系，超时1秒
            tf_buffer_->transform(*msg, pose_in_base, root_link_, tf2::durationFromSec(1.0));
        } catch (const tf2::TransformException &ex) {
            RCLCPP_ERROR(this->get_logger(), "Transform failed: %s", ex.what());
            return;
        }

        // 检查 z 轴是否过低（地面碰撞）
        double ground_z = this->get_parameter("ground_z").as_double();
        double safety_z = this->get_parameter("safety_z_offset").as_double();
        if (pose_in_base.pose.position.z < ground_z + safety_z) {
            RCLCPP_WARN(this->get_logger(), "Target z too low!");
            return;
        }

        move_group_->setPoseTarget(pose_in_base, tip_link_); // 设置目标位姿
        moveit::planning_interface::MoveGroupInterface::Plan plan;
        if (move_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS) {
            move_group_->asyncExecute(plan); // 异步执行，不阻塞回调
        } else {
            RCLCPP_ERROR(this->get_logger(), "Planning failed");
        }
    }

    /**
     * @brief 处理速度缩放因子（来自 /velocity_scale）
     */
    void velocityCallback(const std_msgs::msg::Float32::SharedPtr msg)
    {
        if (!move_group_) {
            RCLCPP_ERROR(this->get_logger(), "velocityCallback: move_group_ is null");
            return;
        }
        double scale = msg->data;
        // 限制速度范围 [0.1, 1.0]
        if (scale < 0.1) scale = 0.1;
        if (scale > 1.0) scale = 1.0;
        move_group_->setMaxVelocityScalingFactor(scale);
        RCLCPP_INFO(this->get_logger(), "Velocity scale updated to %.2f", scale);
    }

    /**
     * @brief 处理停止命令（来自 /stop_motion）
     */
    void stopCallback(const std_msgs::msg::Bool::SharedPtr msg)
    {
        if (!move_group_) {
            RCLCPP_ERROR(this->get_logger(), "stopCallback: move_group_ is null");
            return;
        }
        if (msg->data) {
            move_group_->stop(); // 立即停止当前轨迹执行
            RCLCPP_INFO(this->get_logger(), "Motion stopped by user request");
        }
    }

    /**
     * @brief 处理绝对关节目标（来自 /joint_goal）
     */
    void jointGoalCallback(const sensor_msgs::msg::JointState::SharedPtr msg)
    {
        if (!move_group_) {
            RCLCPP_ERROR(this->get_logger(), "jointGoalCallback: move_group_ is null");
            return;
        }
        // 检查关节数量是否匹配
        if (msg->position.size() != move_group_->getJointNames().size()) {
            RCLCPP_ERROR(this->get_logger(), "Joint goal size mismatch");
            return;
        }
        move_group_->setJointValueTarget(*msg);
        moveit::planning_interface::MoveGroupInterface::Plan plan;
        if (move_group_->plan(plan) == moveit::core::MoveItErrorCode::SUCCESS) {
            move_group_->asyncExecute(plan);
        } else {
            RCLCPP_ERROR(this->get_logger(), "Joint goal planning failed");
        }
    }

    // ---------- 成员变量 ----------
    std::shared_ptr<moveit::planning_interface::MoveGroupInterface> move_group_; // MoveGroup 接口
    std::unique_ptr<tf2_ros::Buffer> tf_buffer_;      // TF 缓冲区
    std::shared_ptr<tf2_ros::TransformListener> tf_listener_; // TF 监听器
    rclcpp::Subscription<geometry_msgs::msg::PoseStamped>::SharedPtr subscription_;   // 笛卡尔目标订阅
    rclcpp::Subscription<std_msgs::msg::Float32>::SharedPtr velocity_sub_;              // 速度缩放订阅
    rclcpp::Subscription<std_msgs::msg::Bool>::SharedPtr stop_sub_;                     // 停止订阅
    rclcpp::Subscription<sensor_msgs::msg::JointState>::SharedPtr joint_goal_sub_;      // 关节目标订阅
    std::string reference_frame_, root_link_, tip_link_; // 常用坐标系名称
};

int main(int argc, char** argv)
{
    rclcpp::init(argc, argv);
    auto node = std::make_shared<CartesianController>();
    node->init();  // 执行初始化
    // 如果初始化过程中未触发 shutdown，则开始 spin
    if (rclcpp::ok()) {
        rclcpp::spin(node);
    }
    rclcpp::shutdown();
    return 0;
}