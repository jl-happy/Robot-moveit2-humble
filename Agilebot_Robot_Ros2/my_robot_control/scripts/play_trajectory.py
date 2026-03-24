#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from control_msgs.action import FollowJointTrajectory
from trajectory_msgs.msg import JointTrajectory, JointTrajectoryPoint
from rclpy.action import ActionClient
import csv
import os
import sys

class GazeboTrajectoryPlayer(Node):
    def __init__(self):
        super().__init__('gazebo_trajectory_player')
        # 指定你的控制器Action名称
        self._client = ActionClient(
            self, 
            FollowJointTrajectory, 
            '/gbt_arm_controller/follow_joint_trajectory'
        )
        self.get_logger().info("Waiting for FollowJointTrajectory action server...")
        self._client.wait_for_server()
        self.get_logger().info("Action server ready.")

    def play(self, joint_names, trajectory):
        # 构建JointTrajectory消息
        traj_msg = JointTrajectory()
        traj_msg.joint_names = joint_names

        for t, joints in trajectory:
            point = JointTrajectoryPoint()
            point.positions = joints
            # 将时间戳拆分为秒和纳秒
            point.time_from_start.sec = int(t)
            point.time_from_start.nanosec = int((t % 1) * 1e9)
            traj_msg.points.append(point)

        # 创建Goal并发送
        goal_msg = FollowJointTrajectory.Goal()
        goal_msg.trajectory = traj_msg

        self.get_logger().info("Sending trajectory to Gazebo...")
        send_goal_future = self._client.send_goal_async(goal_msg)
        rclpy.spin_until_future_complete(self, send_goal_future)
        goal_handle = send_goal_future.result()
        if not goal_handle.accepted:
            self.get_logger().error("Goal rejected by action server!")
            return

        self.get_logger().info("Goal accepted, waiting for trajectory to complete...")

        # 等待轨迹执行完成
        result_future = goal_handle.get_result_async()
        rclpy.spin_until_future_complete(self, result_future)
        result = result_future.result()
        self.get_logger().info("Trajectory execution finished!")

def read_csv(filename):
    trajectory = []
    with open(filename) as f:
        reader = csv.reader(f)
        next(reader)  # 跳过标题
        for row in reader:
            t = float(row[0])
            joints = [float(x) for x in row[1:]]
            trajectory.append((t, joints))
    return trajectory

def main(args=None):
    rclpy.init(args=args)
    node = GazeboTrajectoryPlayer()

    # 根据你的机器人修改joint_names顺序
    joint_names = ["joint1","joint2","joint3","joint4","joint5","joint6"]
    
    # 构建csv目录路径
    home = os.path.expanduser("~")
    csv_dir = os.path.join(home, "rb_ws/src/Agilebot_Robot_Ros2/my_robot_control/csv")
    
    # 确定要读取的文件
    if len(sys.argv) > 1:
        # 如果提供了参数，使用参数作为文件名
        csv_file = os.path.join(csv_dir, sys.argv[1])
    else:
        # 否则读取第一个可用的CSV文件
        csv_file = os.path.join(csv_dir, "trajectory_001.csv")
    
    node.get_logger().info(f"Reading trajectory from: {csv_file}")
    trajectory = read_csv(csv_file)

    # 播放轨迹，并等待执行完成
    node.play(joint_names, trajectory)

    # 轨迹执行完成后再退出
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()