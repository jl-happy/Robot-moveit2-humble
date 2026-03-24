from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QGridLayout,
    QLabel,
    QDoubleSpinBox,
    QSpinBox,
    QCheckBox,
    QDialogButtonBox,
    QMessageBox,
)
from PySide6.QtCore import Qt
from core.data_models import SafetyConfig


class SafetyConfigDialog(QDialog):
    """
    安全参数配置对话框：
    - 关节软限位（角度）
    - TCP 最大速度 / 加速度
    - 碰撞灵敏度、软限位开关、碰撞检测开关
    """

    def __init__(self, config_manager, parent=None):
        super().__init__(parent)
        self.config_manager = config_manager
        self.joint_lower_boxes = []
        self.joint_upper_boxes = []

        self.setWindowTitle("安全参数配置")
        self.resize(600, 400)
        self._setup_ui()
        self._load_from_config()

    def _setup_ui(self):
        main_layout = QVBoxLayout()

        # 关节限位
        joint_group = QGroupBox("关节软限位（°）")
        joint_layout = QGridLayout()

        joint_layout.addWidget(QLabel("关节"), 0, 0)
        joint_layout.addWidget(QLabel("下限 (°)"), 0, 1)
        joint_layout.addWidget(QLabel("上限 (°)"), 0, 2)

        for i in range(6):
            row = i + 1
            joint_layout.addWidget(QLabel(f"J{i+1}"), row, 0)

            lower_box = QDoubleSpinBox()
            lower_box.setRange(-720.0, 720.0)
            lower_box.setDecimals(1)
            lower_box.setSingleStep(1.0)
            joint_layout.addWidget(lower_box, row, 1)

            upper_box = QDoubleSpinBox()
            upper_box.setRange(-720.0, 720.0)
            upper_box.setDecimals(1)
            upper_box.setSingleStep(1.0)
            joint_layout.addWidget(upper_box, row, 2)

            self.joint_lower_boxes.append(lower_box)
            self.joint_upper_boxes.append(upper_box)

        joint_group.setLayout(joint_layout)
        main_layout.addWidget(joint_group)

        # TCP 速度 / 加速度 & 碰撞
        motion_group = QGroupBox("TCP 运动与碰撞")
        motion_layout = QGridLayout()

        motion_layout.addWidget(QLabel("TCP 最大速度 (m/s)"), 0, 0)
        self.tcp_vel_box = QDoubleSpinBox()
        self.tcp_vel_box.setRange(0.01, 10.0)
        self.tcp_vel_box.setDecimals(2)
        self.tcp_vel_box.setSingleStep(0.1)
        motion_layout.addWidget(self.tcp_vel_box, 0, 1)

        motion_layout.addWidget(QLabel("TCP 最大加速度 (m/s²)"), 1, 0)
        self.tcp_acc_box = QDoubleSpinBox()
        self.tcp_acc_box.setRange(0.1, 50.0)
        self.tcp_acc_box.setDecimals(2)
        self.tcp_acc_box.setSingleStep(0.5)
        motion_layout.addWidget(self.tcp_acc_box, 1, 1)

        motion_layout.addWidget(QLabel("碰撞灵敏度 (1-5)"), 2, 0)
        self.collision_spin = QSpinBox()
        self.collision_spin.setRange(1, 5)
        motion_layout.addWidget(self.collision_spin, 2, 1)

        self.soft_limit_check = QCheckBox("启用关节软限位")
        self.collision_check = QCheckBox("启用碰撞检测")
        motion_layout.addWidget(self.soft_limit_check, 3, 0, 1, 2)
        motion_layout.addWidget(self.collision_check, 4, 0, 1, 2)

        motion_group.setLayout(motion_layout)
        main_layout.addWidget(motion_group)

        # 按钮
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)

        main_layout.addWidget(button_box)
        self.setLayout(main_layout)

    def _load_from_config(self):
        """从 ConfigManager 加载当前安全配置"""
        config: SafetyConfig = self.config_manager.get_safety_config()

        # 关节限位（弧度 -> 度）
        for i in range(6):
            lower_deg = config.joint_limits_lower[i] * 180.0 / 3.1415926
            upper_deg = config.joint_limits_upper[i] * 180.0 / 3.1415926
            self.joint_lower_boxes[i].setValue(lower_deg)
            self.joint_upper_boxes[i].setValue(upper_deg)

        self.tcp_vel_box.setValue(config.tcp_max_velocity)
        self.tcp_acc_box.setValue(config.tcp_max_acceleration)
        self.collision_spin.setValue(config.collision_sensitivity)
        self.soft_limit_check.setChecked(config.enable_soft_limits)
        self.collision_check.setChecked(config.enable_collision_detection)

    def _on_accept(self):
        """收集 UI 数据并保存"""
        try:
            joint_lower_rad = []
            joint_upper_rad = []
            for i in range(6):
                low = self.joint_lower_boxes[i].value()
                up = self.joint_upper_boxes[i].value()
                if low > up:
                    raise ValueError(f"J{i+1} 的下限不能大于上限")
                joint_lower_rad.append(low * 3.1415926 / 180.0)
                joint_upper_rad.append(up * 3.1415926 / 180.0)

            config = SafetyConfig(
                joint_limits_lower=joint_lower_rad,
                joint_limits_upper=joint_upper_rad,
                tcp_max_velocity=self.tcp_vel_box.value(),
                tcp_max_acceleration=self.tcp_acc_box.value(),
                collision_sensitivity=self.collision_spin.value(),
                enable_soft_limits=self.soft_limit_check.isChecked(),
                enable_collision_detection=self.collision_check.isChecked(),
            )

            if self.config_manager.save_safety_config(config):
                self.accept()
            else:
                QMessageBox.critical(self, "错误", "保存安全配置失败")
        except ValueError as e:
            QMessageBox.warning(self, "输入错误", str(e))
        except Exception as e:
            QMessageBox.critical(self, "错误", f"未知错误: {e}")

