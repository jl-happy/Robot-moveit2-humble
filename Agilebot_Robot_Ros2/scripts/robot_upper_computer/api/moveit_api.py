# moveit_api.py
import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Bool, Float32
from interface.srv import SetInt16  # 请根据你的实际消息包名调整（可能是 interface 或 elfin_robot_msgs）
import threading
import math


class Ros2Bridge:
    """ROS2 桥接类，负责与 ROS2 系统交互"""

    def __init__(self):
        if not rclpy.ok():
            rclpy.init(args=None)
        self.node = Node('ui_publisher')
        self.cartesian_pub = self.node.create_publisher(PoseStamped, 'cartesian_goal', 10)
        self.stop_pub = self.node.create_publisher(Bool, 'stop_motion', 10)
        self.velocity_pub = self.node.create_publisher(Float32, 'velocity_scale', 10)

        # 创建 /joint_teleop 服务客户端（用于关节增量）
        self.joint_teleop_client = self.node.create_client(SetInt16, 'joint_teleop')
        # 等待服务可用（可选，但建议添加）
        while not self.joint_teleop_client.wait_for_service(timeout_sec=1.0):
            self.node.get_logger().warn('Waiting for joint_teleop service...')

        # 不再独立启动spin线程，使用同步服务调用来避免多线程 spin 的等待集冲突
        # 如果后续需要订阅消息，请改用单独 executor（rclpy.executors.SingleThreadedExecutor）
        self._spin_thread = None

    # def _ros_spin(self):
    #     while rclpy.ok():
    #         rclpy.spin_once(self.node, timeout_sec=0.1)

    @staticmethod
    def euler_to_quaternion(roll_rad: float, pitch_rad: float, yaw_rad: float):
        """将欧拉角（弧度）转换为四元数 (w, x, y, z)"""
        cy = math.cos(yaw_rad * 0.5)
        sy = math.sin(yaw_rad * 0.5)
        cp = math.cos(pitch_rad * 0.5)
        sp = math.sin(pitch_rad * 0.5)
        cr = math.cos(roll_rad * 0.5)
        sr = math.sin(roll_rad * 0.5)
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        return w, x, y, z

    def send_cartesian_goal(self, frame_id: str, x: float, y: float, z: float,
                            roll_deg: float, pitch_deg: float, yaw_deg: float):
        """发送绝对笛卡尔目标位姿（话题）"""
        msg = PoseStamped()
        msg.header.frame_id = frame_id
        msg.header.stamp = self.node.get_clock().now().to_msg()
        msg.pose.position.x = x
        msg.pose.position.y = y
        msg.pose.position.z = z

        roll = math.radians(roll_deg)
        pitch = math.radians(pitch_deg)
        yaw = math.radians(yaw_deg)
        q = self.euler_to_quaternion(roll, pitch, yaw)
        msg.pose.orientation.w = q[0]
        msg.pose.orientation.x = q[1]
        msg.pose.orientation.y = q[2]
        msg.pose.orientation.z = q[3]

        self.cartesian_pub.publish(msg)

    def send_stop_command(self):
        """发送停止命令（话题）"""
        msg = Bool()
        msg.data = True
        self.stop_pub.publish(msg)

    def send_velocity_scale(self, scale: float):
        """发送速度缩放因子（话题）"""
        msg = Float32()
        msg.data = scale
        self.velocity_pub.publish(msg)

    def send_joint_increment(self, joint_id: int, direction: int):
        """
        发送关节增量命令（通过服务）
        :param joint_id: 关节编号，从1开始（例如 1 表示关节1）
        :param direction: 运动方向，+1 表示正方向，-1 表示负方向
        """
        if not self.joint_teleop_client.service_is_ready():
            self.node.get_logger().error('joint_teleop service not available')
            return

        req = SetInt16.Request()
        req.data = joint_id * direction
        future = self.joint_teleop_client.call_async(req)

        # 同步等待服务响应，避免单独 spin 线程与其它 rclpy 线程冲突
        rclpy.spin_until_future_complete(self.node, future, timeout_sec=2.0)

        if future.done():
            self._joint_teleop_callback(future)
        else:
            self.node.get_logger().error('joint_teleop 请求超时')

    def _joint_teleop_callback(self, future):
        """处理服务响应的回调"""
        try:
            response = future.result()
            if response.success:
                self.node.get_logger().info(f'Joint teleop success: {response.message}')
            else:
                self.node.get_logger().error(f'Joint teleop failed: {response.message}')
        except Exception as e:
            self.node.get_logger().error(f'Service call failed: {e}')

    def shutdown(self):
        """清理 ROS2 资源"""
        if rclpy.ok():
            self.node.destroy_node()
            rclpy.shutdown()