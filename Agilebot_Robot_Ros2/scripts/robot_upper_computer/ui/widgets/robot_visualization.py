#!/usr/bin/env python3
# ========== 修复1：强制指定matplotlib后端 ==========
import matplotlib
matplotlib.use('Agg')  # 禁用Qt后端，使用无界面的Agg后端
import rclpy
from rclpy.node import Node
from urdf_parser_py.urdf import URDF
import pyvista as pv
try:
    from pyvistaqt import QtInteractor
except ImportError:
    QtInteractor = None
import threading
import subprocess
import numpy as np
from tf2_ros import TransformListener, Buffer
from scipy.spatial.transform import Rotation as R
import time
import os
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QSizePolicy
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QResizeEvent
import logging  # 新增：用于日志输出


class ROS2TFWorker(QThread):
    """ROS2 TF 更新线程（避免阻塞Qt主线程）"""
    update_signal = Signal()

    def __init__(self, viewer):
        super().__init__()
        self.viewer = viewer
        self.is_running = True

    def run(self):
        while self.is_running:
            now = time.time()
            if now - self.viewer.last_tf_time > self.viewer.tf_interval:
                self.viewer.update_tf_transforms()
                self.viewer.last_tf_time = now
                self.update_signal.emit()  # 通知主线程更新渲染
            time.sleep(0.01)

    def stop(self):
        self.is_running = False
        self.wait()


class Robot3DViewer(Node):
    def __init__(self, parent_widget=None, plotter=None):
        super().__init__("ros2_moveit_3d_viewer")
        self.parent_widget = parent_widget  # Qt父控件
        self.get_logger().info("正在读取机器人模型...")

        # ===================== 获取URDF =====================
        result = subprocess.run(
            ["ros2", "param", "get", "/robot_state_publisher", "robot_description"],
            capture_output=True, text=True
        )
        output = result.stdout.strip()
        idx = output.find('<?xml')
        self.urdf_str = output[idx:]

        # ===================== 解析URDF =====================
        self.robot = URDF.from_xml_string(self.urdf_str)
        self.get_logger().info("✅ 机器人模型加载成功！")

        # ===================== 读取Mesh =====================
        self.link_meshes = {}
        self.load_robot_model()

        # ===================== TF =====================
        self.tf_buffer = Buffer()
        self.tf_listener = TransformListener(self.tf_buffer, self)
        self.base_link = "base_link"
        self.last_tf_time = time.time()
        self.tf_interval = 0.02

        # ===================== 可视化（嵌入Qt版本）=====================
        # 支持 pyvistaqt QtInteractor 或直接 Plotter（兼容性）
        if plotter is not None:
            self.plotter = plotter
        else:
            self.plotter = pv.Plotter(
                title="机械臂 3D 上位机",
                window_size=(1000, 700),
                off_screen=False
            )

        self.plotter.set_background("white")
        try:
            self.plotter.enable_anti_aliasing('fxaa')
        except Exception:
            pass
        try:
            self.plotter.enable_lightkit()
        except Exception:
            pass

        # 避免 VTK 渲染层冲突
        try:
            if hasattr(self.plotter, 'render_window') and self.plotter.render_window is not None:
                self.plotter.render_window.SetNumberOfLayers(1)
            for renderer in getattr(self.plotter, 'renderers', []):
                try:
                    renderer.SetLayer(0)
                except Exception:
                    pass
        except Exception:
            pass

        # ===================== 地面网格 =====================
        grid_size = 6
        num_lines = 5

        for i in range(num_lines + 1):
            x = -grid_size / 2 + i * grid_size / num_lines
            line = pv.Line(pointa=(x, -grid_size / 2, 0), pointb=(x, grid_size / 2, 0))
            self.plotter.add_mesh(line, color="gray", line_width=1)

            y = -grid_size / 2 + i * grid_size / num_lines
            line = pv.Line(pointa=(-grid_size / 2, y, 0), pointb=(grid_size / 2, y, 0))
            self.plotter.add_mesh(line, color="gray", line_width=1)

        self.plotter.add_axes()

        # ===================== 加载机器人 =====================
        self.actors = {}
        for link_name, mesh in self.link_meshes.items():
            actor = self.plotter.add_mesh(
                mesh,
                color="#4fc3f7",
                smooth_shading=False
            )
            actor.SetScale(1, 1, 1)
            self.actors[link_name] = actor

        # ===================== 相机设置 =====================
        self.plotter.camera_position = [
            (3, 3, 2),
            (0, 0, 0),
            (0, 0, 1)
        ]
        self.plotter.enable_parallel_projection()
        self.plotter.enable_terrain_style()

        # ===================== TF更新线程 =====================
        self.tf_worker = ROS2TFWorker(self)
        self.tf_worker.update_signal.connect(self.update_plotter)
        self.tf_worker.start()

        self.get_logger().info("✅ 3D视图已嵌入Qt UI！")

    def update_plotter(self):
        """Qt主线程更新渲染（线程安全）"""
        if hasattr(self, 'plotter'):
            self.plotter.camera.up = (0, 0, 1)
            self.plotter.update()

    # ===================== 加载模型 =====================
    def load_robot_model(self):
        # 正确的Mesh基础路径
        self.mesh_base_path = "/root/rb_ws/src/Agilebot_Robot_Ros2/gbt_description/"
        
        for link_name, link in self.robot.link_map.items():
            try:
                if link.visual and link.visual.geometry and hasattr(link.visual.geometry, 'filename'):
                    path = link.visual.geometry.filename
                    
                    # 调试信息
                    self.get_logger().info(f"原始路径 [{link_name}]: {path}")
                    
                    # 清理路径
                    if path.startswith('file://'):
                        path = path[7:]  # 移除 file://
                    
                    # 替换 package:// 路径
                    if 'package://gbt_description/' in path:
                        path = path.replace(
                            "package://gbt_description/",
                            self.mesh_base_path
                        )
                    
                    # 处理可能的 file: 前缀
                    if path.startswith('file:') and not path.startswith('file://'):
                        path = path.replace('file:', '', 1)
                    
                    # 移除可能的重复路径
                    if 'file:/root' in path:
                        path = path.replace('file:/root', '/root')
                    
                    
                    # 检查文件是否存在
                    if os.path.exists(path):
                        mesh = pv.read(path)
                        self.link_meshes[link_name] = mesh
                        self.get_logger().info(f"✅ 加载成功: {link_name}")
                    else:
                        # 尝试替代路径
                        alt_path = path.replace('/install/', '/src/Agilebot_Robot_Ros2/')
                        if os.path.exists(alt_path):
                            mesh = pv.read(alt_path)
                            self.link_meshes[link_name] = mesh
                            self.get_logger().info(f"✅ 使用替代路径加载成功: {link_name}")
                        else:
                            self.get_logger().error(f"❌ 文件不存在: {path}")
                            
            except Exception as e:
                self.get_logger().error(f"❌ 加载失败 {link_name}: {e}")

    # ===================== TF更新 =====================
    def update_tf_transforms(self):
        for link_name in self.link_meshes.keys():
            try:
                transform = self.tf_buffer.lookup_transform(
                    self.base_link,
                    link_name,
                    rclpy.time.Time(),
                    timeout=rclpy.duration.Duration(seconds=0.05)
                )

                t = transform.transform.translation
                x, y, z = t.x, t.y, t.z

                q = transform.transform.rotation
                rot = R.from_quat([q.x, q.y, q.z, q.w])
                rot_mat = rot.as_matrix()

                mat = np.eye(4)
                mat[:3, :3] = rot_mat
                mat[:3, 3] = [x, y, z]

                if link_name in self.actors:
                    self.actors[link_name].user_matrix = mat

            except Exception as e:
                continue

    def shutdown(self):
        """停止线程和节点"""
        self.tf_worker.stop()
        self.destroy_node()


class RobotVisualizationWidget(QWidget):
    """将3D视图直接嵌入Qt Widget的最终版本"""

    def __init__(self, parent=None):
        super().__init__(parent)
        # ========== 修复2：初始化日志器 ==========
        self.logger = logging.getLogger("RobotVisualizationWidget")
        logging.basicConfig(level=logging.INFO)

        self.setMinimumSize(800, 600)
        self.viewer = None  # ROS2 3D视图节点
        self.executor = None  # ROS2 executor for viewer
        self.init_ui()

    def init_ui(self):
        # 主布局
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(0, 0, 0, 0)

        # 1. 控制按钮区域
        self.btn_layout = QVBoxLayout()
        self.btn_layout.setContentsMargins(10, 10, 10, 10)
        
        self.restart_btn = QPushButton("重启3D可视化", self)
        self.restart_btn.clicked.connect(self.restart_viewer)
        self.btn_layout.addWidget(self.restart_btn)

        # 2. 3D视图容器（核心：PyVista会嵌入到这个widget）
        self.view_container = QWidget(self)
        self.view_container.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.view_container_layout = QVBoxLayout(self.view_container)
        self.view_container_layout.setContentsMargins(0, 0, 0, 0)
        self.view_container_layout.setSpacing(0)

        if QtInteractor is not None:
            self.view_interactor = QtInteractor(self.view_container)
            self.view_container_layout.addWidget(self.view_interactor)
        else:
            self.view_interactor = None
            print("⚠️ 未安装 pyvistaqt，无法嵌入 3D 视图")

        # 添加到主布局
        self.main_layout.addLayout(self.btn_layout, stretch=1)
        self.main_layout.addWidget(self.view_container, stretch=9)

        # 启动3D视图
        self.start_viewer()

    def start_viewer(self):
        """启动ROS2 3D视图并嵌入到Qt控件"""
        if self.viewer is not None:
            self.stop_viewer()

        # 确保ROS2初始化
        if not rclpy.ok():
            rclpy.init()

        # 启动Viewer（绑定到Qt容器）
        def _start_viewer_worker():
            try:
                if self.view_interactor is None:
                    raise RuntimeError("pyvistaqt 未可用，无法创建嵌入式 3D 视图")

                self.viewer = Robot3DViewer(plotter=self.view_interactor)
                self.executor = rclpy.executors.SingleThreadedExecutor()
                self.executor.add_node(self.viewer)

                while rclpy.ok() and self.viewer is not None:
                    self.executor.spin_once(timeout_sec=0.01)
            except Exception as e:
                print(f"❌ 3D 可视化启动失败: {e}")
                self.logger.error(f"Viewer启动失败: {e}")
            finally:
                if self.executor is not None:
                    try:
                        if self.viewer is not None:
                            self.executor.remove_node(self.viewer)
                        self.executor.shutdown()
                    except Exception:
                        pass
                    self.executor = None

        # 启动ROS2线程（避免阻塞Qt UI）
        self.viewer_thread = threading.Thread(target=_start_viewer_worker, daemon=True)
        self.viewer_thread.start()

    def stop_viewer(self):
        """停止3D视图"""
        if self.viewer is not None:
            self.viewer.shutdown()
            self.viewer = None
        if self.executor is not None:
            try:
                self.executor.shutdown()
            except Exception:
                pass
            self.executor = None
        if self.view_interactor is not None:
            try:
                self.view_interactor.clear()
            except Exception:
                pass

    def restart_viewer(self):
        """重启3D视图"""
        self.stop_viewer()
        time.sleep(0.5)
        self.start_viewer()

    def closeEvent(self, event):
        """窗口关闭时清理资源"""
        self.stop_viewer()
        if rclpy.ok():
            rclpy.shutdown()
        event.accept()

    def update_joint_states(self, states):
        """兼容 MainWindow 信号接口。
        3D 可视化已通过 TF 更新，这里仅保留接口占位，可后续绑定关节角直接控制。"""
        # 如果需要，把 joint state 同步给 viewer；当前不做额外处理
        return


# 测试入口（单独运行时）
def main():
    import sys
    from PySide6.QtWidgets import QApplication

    app = QApplication(sys.argv)
    
    # 创建主窗口
    window = RobotVisualizationWidget()
    window.setWindowTitle("机械臂3D可视化 - 嵌入Qt版")
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()