#!/usr/bin/env python3

import tkinter as tk
from tkinter import ttk, messagebox
import threading
import math

import rclpy
from rclpy.node import Node
from geometry_msgs.msg import PoseStamped
from std_msgs.msg import Float32, Bool
from interface.srv import SetInt16

def euler_to_quaternion(roll, pitch, yaw):
    cy = math.cos(yaw * 0.5)
    sy = math.sin(yaw * 0.5)
    cp = math.cos(pitch * 0.5)
    sp = math.sin(pitch * 0.5)
    cr = math.cos(roll * 0.5)
    sr = math.sin(roll * 0.5)
    w = cr * cp * cy + sr * sp * sy
    x = sr * cp * cy - cr * sp * sy
    y = cr * sp * cy + sr * cp * sy
    z = cr * cp * sy - sr * sp * cy
    return (w, x, y, z)

class CartesianTestUI(Node):
    def __init__(self):
        super().__init__('cartesian_test_ui')
        # 发布者
        self.publisher_ = self.create_publisher(PoseStamped, 'cartesian_goal', 10)
        self.vel_publisher_ = self.create_publisher(Float32, 'velocity_scale', 10)
        self.stop_publisher_ = self.create_publisher(Bool, 'stop_motion', 10)

        # 服务客户端（增量控制）
        self.cart_teleop_client = self.create_client(SetInt16, 'cart_teleop')
        self.joint_teleop_client = self.create_client(SetInt16, 'joint_teleop')

        # 等待服务可用（非阻塞，但可打印警告）
        if not self.cart_teleop_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('cart_teleop service not available')
        if not self.joint_teleop_client.wait_for_service(timeout_sec=1.0):
            self.get_logger().warn('joint_teleop service not available')

        self.get_logger().info('UI node started')

    def publish_goal(self, frame_id, x, y, z, roll_deg, pitch_deg, yaw_deg):
        msg = PoseStamped()
        msg.header.frame_id = frame_id
        msg.header.stamp = self.get_clock().now().to_msg()
        msg.pose.position.x = float(x)
        msg.pose.position.y = float(y)
        msg.pose.position.z = float(z)
        roll = math.radians(float(roll_deg))
        pitch = math.radians(float(pitch_deg))
        yaw = math.radians(float(yaw_deg))
        q = euler_to_quaternion(roll, pitch, yaw)
        msg.pose.orientation.w = q[0]
        msg.pose.orientation.x = q[1]
        msg.pose.orientation.y = q[2]
        msg.pose.orientation.z = q[3]
        self.publisher_.publish(msg)
        self.get_logger().info(f'Published goal: {frame_id} ({x},{y},{z}) RPY({roll_deg},{pitch_deg},{yaw_deg})')

    def stop_motion(self):
        msg = Bool()
        msg.data = True
        self.stop_publisher_.publish(msg)
        self.get_logger().info('Stop motion command sent')

    def call_cart_teleop(self, op, direction):
        """笛卡尔增量服务调用"""
        req = SetInt16.Request()
        req.data = op * direction
        future = self.cart_teleop_client.call_async(req)
        future.add_done_callback(self.service_callback)

    def call_joint_teleop(self, joint_id, direction):
        """关节增量服务调用 (joint_id: 1~6, direction: +1 或 -1)"""
        req = SetInt16.Request()
        req.data = joint_id * direction
        future = self.joint_teleop_client.call_async(req)
        future.add_done_callback(self.service_callback)

    def service_callback(self, future):
        try:
            response = future.result()
            if response.success:
                self.get_logger().info(f'Service success: {response.message}')
            else:
                self.get_logger().error(f'Service failed: {response.message}')
        except Exception as e:
            self.get_logger().error(f'Service call exception: {e}')

def ros_spin(node):
    rclpy.spin(node)
    node.destroy_node()
    rclpy.shutdown()

def main():
    rclpy.init()
    node = CartesianTestUI()
    spin_thread = threading.Thread(target=ros_spin, args=(node,), daemon=True)
    spin_thread.start()

    root = tk.Tk()
    root.title("笛卡尔/关节控制 UI")
    root.geometry("700x700")  # 调大窗口
    root.resizable(False, False)

    # ========== 绝对目标输入 ==========
    ttk.Label(root, text="参考坐标系:").grid(row=0, column=0, sticky='e', padx=5, pady=5)
    frame_entry = ttk.Entry(root, width=20)
    frame_entry.insert(0, "base_link")
    frame_entry.grid(row=0, column=1, padx=5, pady=5, sticky='w')

    ttk.Label(root, text="X (m):").grid(row=1, column=0, sticky='e', padx=5, pady=5)
    x_entry = ttk.Entry(root, width=10)
    x_entry.insert(0, "0.2")
    x_entry.grid(row=1, column=1, padx=5, pady=5, sticky='w')

    ttk.Label(root, text="Y (m):").grid(row=2, column=0, sticky='e', padx=5, pady=5)
    y_entry = ttk.Entry(root, width=10)
    y_entry.insert(0, "0.1")
    y_entry.grid(row=2, column=1, padx=5, pady=5, sticky='w')

    ttk.Label(root, text="Z (m):").grid(row=3, column=0, sticky='e', padx=5, pady=5)
    z_entry = ttk.Entry(root, width=10)
    z_entry.insert(0, "0.3")
    z_entry.grid(row=3, column=1, padx=5, pady=5, sticky='w')

    ttk.Label(root, text="Roll (deg):").grid(row=4, column=0, sticky='e', padx=5, pady=5)
    roll_entry = ttk.Entry(root, width=10)
    roll_entry.insert(0, "0")
    roll_entry.grid(row=4, column=1, padx=5, pady=5, sticky='w')

    ttk.Label(root, text="Pitch (deg):").grid(row=5, column=0, sticky='e', padx=5, pady=5)
    pitch_entry = ttk.Entry(root, width=10)
    pitch_entry.insert(0, "0")
    pitch_entry.grid(row=5, column=1, padx=5, pady=5, sticky='w')

    ttk.Label(root, text="Yaw (deg):").grid(row=6, column=0, sticky='e', padx=5, pady=5)
    yaw_entry = ttk.Entry(root, width=10)
    yaw_entry.insert(0, "0")
    yaw_entry.grid(row=6, column=1, padx=5, pady=5, sticky='w')

    def send_goal():
        try:
            frame = frame_entry.get().strip()
            x = float(x_entry.get())
            y = float(y_entry.get())
            z = float(z_entry.get())
            roll = float(roll_entry.get())
            pitch = float(pitch_entry.get())
            yaw = float(yaw_entry.get())
        except ValueError:
            messagebox.showerror("输入错误", "请输入有效的数字")
            return
        node.publish_goal(frame, x, y, z, roll, pitch, yaw)
        status_label.config(text=f"已发送: {frame} ({x},{y},{z}) RPY({roll},{pitch},{yaw})")

    send_btn = ttk.Button(root, text="发送笛卡尔目标", command=send_goal)
    send_btn.grid(row=7, column=0, columnspan=2, pady=10)

    # ========== 速度滑块 ==========
    ttk.Label(root, text="速度缩放因子 (0.1~1.0):").grid(row=8, column=0, sticky='e', padx=5, pady=5)
    velocity_scale = tk.DoubleVar(value=0.4)
    def on_velocity_change(val):
        scale = velocity_scale.get()
        msg = Float32()
        msg.data = scale
        node.vel_publisher_.publish(msg)
        velocity_label.config(text=f"{scale:.2f}")
    velocity_slider = ttk.Scale(root, from_=0.1, to=1.0, orient='horizontal',
                                variable=velocity_scale, command=on_velocity_change,
                                length=200)
    velocity_slider.grid(row=8, column=1, padx=5, pady=5, sticky='w')
    velocity_label = ttk.Label(root, text="0.40")
    velocity_label.grid(row=8, column=2, padx=5, pady=5, sticky='w')

    # ========== 停止按钮 ==========
    stop_btn = ttk.Button(root, text="停止运动", command=node.stop_motion)
    stop_btn.grid(row=9, column=0, columnspan=3, pady=5)

    # ========== 笛卡尔增量控制 ==========
    cart_frame = ttk.LabelFrame(root, text="笛卡尔增量控制", padding=5)
    cart_frame.grid(row=10, column=0, columnspan=3, pady=10, sticky='ew')

    ttk.Label(cart_frame, text="平移:").grid(row=0, column=0, padx=2)
    ttk.Button(cart_frame, text="X+", command=lambda: node.call_cart_teleop(1, 1)).grid(row=0, column=1, padx=2)
    ttk.Button(cart_frame, text="X-", command=lambda: node.call_cart_teleop(1, -1)).grid(row=0, column=2, padx=2)
    ttk.Button(cart_frame, text="Y+", command=lambda: node.call_cart_teleop(2, 1)).grid(row=0, column=3, padx=2)
    ttk.Button(cart_frame, text="Y-", command=lambda: node.call_cart_teleop(2, -1)).grid(row=0, column=4, padx=2)
    ttk.Button(cart_frame, text="Z+", command=lambda: node.call_cart_teleop(3, 1)).grid(row=0, column=5, padx=2)
    ttk.Button(cart_frame, text="Z-", command=lambda: node.call_cart_teleop(3, -1)).grid(row=0, column=6, padx=2)

    ttk.Label(cart_frame, text="旋转:").grid(row=1, column=0, padx=2, pady=5)
    ttk.Button(cart_frame, text="Rx+", command=lambda: node.call_cart_teleop(4, 1)).grid(row=1, column=1, padx=2)
    ttk.Button(cart_frame, text="Rx-", command=lambda: node.call_cart_teleop(4, -1)).grid(row=1, column=2, padx=2)
    ttk.Button(cart_frame, text="Ry+", command=lambda: node.call_cart_teleop(5, 1)).grid(row=1, column=3, padx=2)
    ttk.Button(cart_frame, text="Ry-", command=lambda: node.call_cart_teleop(5, -1)).grid(row=1, column=4, padx=2)
    ttk.Button(cart_frame, text="Rz+", command=lambda: node.call_cart_teleop(6, 1)).grid(row=1, column=5, padx=2)
    ttk.Button(cart_frame, text="Rz-", command=lambda: node.call_cart_teleop(6, -1)).grid(row=1, column=6, padx=2)

    # ========== 关节增量控制 ==========
    joint_frame = ttk.LabelFrame(root, text="关节增量控制", padding=5)
    joint_frame.grid(row=11, column=0, columnspan=3, pady=10, sticky='ew')

    # 生成 J1+ ~ J6- 按钮（假设6个关节）
    joints = [("J1", 1), ("J2", 2), ("J3", 3), ("J4", 4), ("J5", 5), ("J6", 6)]
    for i, (label, idx) in enumerate(joints):
        ttk.Label(joint_frame, text=f"{label}:").grid(row=i, column=0, padx=2, pady=2)
        ttk.Button(joint_frame, text="+", width=4,
                   command=lambda idx=idx: node.call_joint_teleop(idx, 1)).grid(row=i, column=1, padx=2)
        ttk.Button(joint_frame, text="-", width=4,
                   command=lambda idx=idx: node.call_joint_teleop(idx, -1)).grid(row=i, column=2, padx=2)

    # ========== 状态标签 ==========
    status_label = ttk.Label(root, text="等待发送...", foreground="blue")
    status_label.grid(row=12, column=0, columnspan=3, pady=10)

    def on_closing():
        rclpy.shutdown()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()