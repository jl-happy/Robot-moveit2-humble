#!/usr/bin/env python3
import rclpy
from rclpy.node import Node
from moveit_msgs.msg import DisplayTrajectory
import csv
import os
from pathlib import Path

class TrajectoryRecorder(Node):
    def __init__(self):
        super().__init__('trajectory_recorder')
        # 订阅MoveIt规划的轨迹
        self.subscription = self.create_subscription(
            DisplayTrajectory,
            '/display_planned_path',
            self.listener_callback,
            10)
        self.subscription  # 防止被GC
        
        # 初始化文件索引
        self.file_index = 1
        
        # 创建csv目录路径
        home = os.path.expanduser("~")
        self.csv_dir = os.path.join(home, "rb_ws/src/Agilebot_Robot_Ros2/my_robot_control/csv")
        Path(self.csv_dir).mkdir(parents=True, exist_ok=True)
        
        self.get_logger().info("Trajectory recorder started...")

    def listener_callback(self, msg: DisplayTrajectory):
        if not msg.trajectory:
            return
        traj = msg.trajectory[0].joint_trajectory
        
        # 生成带序号的文件名
        filename = f"trajectory_{self.file_index:03d}.csv"
        filepath = os.path.join(self.csv_dir, filename)
        
        with open(filepath, "w", newline='') as csvfile:
            writer = csv.writer(csvfile)
            # 写标题
            header = ["time"] + traj.joint_names
            writer.writerow(header)
            # 写轨迹点
            for point in traj.points:
                t = point.time_from_start.sec + point.time_from_start.nanosec * 1e-9
                row = [t] + list(point.positions)
                writer.writerow(row)
        
        self.file_index += 1
        self.get_logger().info(f"Trajectory saved to {filepath}")

def main(args=None):
    rclpy.init(args=args)
    node = TrajectoryRecorder()
    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass
    node.destroy_node()
    rclpy.shutdown()

if __name__ == "__main__":
    main()