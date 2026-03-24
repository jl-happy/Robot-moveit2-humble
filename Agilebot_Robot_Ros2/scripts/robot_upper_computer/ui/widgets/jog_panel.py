"""
点动控制相关面板：
- JogPanel: 关节点动 + 速度 + 急停
- TargetPosePanel: 目标位姿路径规划
"""
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGroupBox,
    QPushButton,
    QLabel,
    QSlider,
    QGridLayout,
    QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt, Signal


class JogPanel(QWidget):
    jog_signal = Signal(int, float)  # 关节ID, 速度(rad/s)
    stop_signal = Signal(int)
    emergency_stop_signal = Signal()   # 紧急停止
    reset_estop_signal = Signal()      # 急停复位

    def __init__(self):
        super().__init__()
        self.joint_count = 6
        self.default_speed = 0.5  # rad/s
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(12, 12, 12, 12)

        speed_group = QGroupBox("点动速度")
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("速度比例:"))

        self.speed_slider = QSlider(Qt.Horizontal)
        self.speed_slider.setRange(10, 100)  # 0.1~1.0
        self.speed_slider.setValue(40)       # 默认0.4
        self.speed_slider.setEnabled(True)
        self.speed_slider.valueChanged.connect(self._on_speed_changed)

        self.speed_label = QLabel("40%")
        speed_layout.addWidget(self.speed_slider)
        speed_layout.addWidget(self.speed_label)
        speed_layout.addStretch()
        speed_group.setLayout(speed_layout)
        main_layout.addWidget(speed_group)

        jog_group = QGroupBox("关节点动（长按连续、松开即停）")
        grid = QGridLayout()
        grid.setHorizontalSpacing(10)
        grid.setVerticalSpacing(8)

        header_joint = QLabel("关节")
        header_joint.setProperty("sectionTitle", True)
        grid.addWidget(header_joint, 0, 0)
        header_pos = QLabel("当前位置")
        header_pos.setProperty("sectionTitle", True)
        grid.addWidget(header_pos, 0, 1)
        header_neg = QLabel("负向")
        header_neg.setProperty("sectionTitle", True)
        grid.addWidget(header_neg, 0, 2)
        header_pos_btn = QLabel("正向")
        header_pos_btn.setProperty("sectionTitle", True)
        grid.addWidget(header_pos_btn, 0, 3)

        self.joint_labels = []

        for i in range(self.joint_count):
            row = i + 1
            grid.addWidget(QLabel(f"J{i + 1}"), row, 0)

            pos_label = QLabel("0.000 rad")
            pos_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            pos_label.setProperty("monoValue", True)
            grid.addWidget(pos_label, row, 1)
            self.joint_labels.append(pos_label)

            btn_neg = QPushButton(" − ")
            btn_neg.setMinimumWidth(44)
            btn_neg.pressed.connect(lambda j=i: self._on_jog_start(j, -1))
            btn_neg.released.connect(lambda j=i: self._on_jog_stop(j))
            grid.addWidget(btn_neg, row, 2)

            btn_pos = QPushButton(" + ")
            btn_pos.setMinimumWidth(44)
            btn_pos.pressed.connect(lambda j=i: self._on_jog_start(j, 1))
            btn_pos.released.connect(lambda j=i: self._on_jog_stop(j))
            grid.addWidget(btn_pos, row, 3)

        jog_group.setLayout(grid)
        main_layout.addWidget(jog_group)

        estop_layout = QHBoxLayout()
        self.stop_all_btn = QPushButton("紧急停止")
        self.stop_all_btn.setProperty("emergency", True)
        self.stop_all_btn.clicked.connect(self._on_stop_all)
        self.reset_estop_btn = QPushButton("急停复位")
        self.reset_estop_btn.clicked.connect(self.reset_estop_signal.emit)
        estop_layout.addWidget(self.stop_all_btn)
        estop_layout.addWidget(self.reset_estop_btn)
        main_layout.addLayout(estop_layout)

        main_layout.addStretch()
        self.setLayout(main_layout)

    def _on_speed_changed(self, value):
        self.speed_label.setText(f"{value}%")

    def ensure_interactive(self):
        """强制恢复点动控件可交互状态。"""
        self.setEnabled(True)
        self.speed_slider.setEnabled(True)

    def _on_jog_start(self, joint_id, direction):
        speed_ratio = self.speed_slider.value() / 100.0
        velocity = self.default_speed * speed_ratio * direction
        self.jog_signal.emit(joint_id, velocity)

    def _on_jog_stop(self, joint_id):
        self.stop_signal.emit(joint_id)

    def _on_stop_all(self):
        for i in range(self.joint_count):
            self.stop_signal.emit(i)
        self.emergency_stop_signal.emit()

    def update_joint_position(self, joint_id, position_rad):
        if 0 <= joint_id < len(self.joint_labels):
            self.joint_labels[joint_id].setText(f"{position_rad:.3f} rad")


class TargetPosePanel(QWidget):
    plan_to_target_signal = Signal(list, float)  # 目标位姿(list[6])、速度比例
    stop_planned_path_signal = Signal()           # 停止规划路径执行

    def __init__(self):
        super().__init__()
        self.input_count = 6
        self._speed_ratio = 0.4  # 默认0.4
        self.setup_ui()

    def setup_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setSpacing(8)
        main_layout.setContentsMargins(0, 0, 0, 0)

        target_group = QGroupBox("目标位姿路径规划")
        target_layout = QVBoxLayout()

        pose_grid = QGridLayout()
        pose_grid.setContentsMargins(20, 12, 20, 10)
        pose_grid.setHorizontalSpacing(14)
        pose_grid.setVerticalSpacing(10)

        self.target_inputs = []
        pose_items = [
            ("X (m):", "0.0"),
            ("Y (m):", "0.0"),
            ("Z (m):", "0.0"),
            ("Roll (deg):", "0.0"),
            ("Pitch (deg):", "0.0"),
            ("Yaw (deg):", "0.0"),
        ]

        for i, (label_text, placeholder) in enumerate(pose_items):
            row = i % 3
            col_base = 0 if i < 3 else 2

            label = QLabel(label_text)
            label.setMinimumWidth(95)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            edit = QLineEdit()
            edit.setPlaceholderText(placeholder)
            edit.setReadOnly(False)
            edit.setEnabled(True)
            edit.setFixedHeight(34)
            edit.setMinimumWidth(140)
            edit.setMaximumWidth(210)
            edit.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

            pose_grid.addWidget(label, row, col_base)
            pose_grid.addWidget(edit, row, col_base + 1)
            self.target_inputs.append(edit)

        pose_grid.setColumnStretch(1, 1)
        pose_grid.setColumnStretch(3, 1)
        target_layout.addLayout(pose_grid)

        plan_row = QHBoxLayout()
        plan_row.setSpacing(12)
        plan_row.setContentsMargins(20, 14, 20, 0)

        self.plan_btn = QPushButton("规划并执行")
        self.plan_btn.setObjectName("primaryBtn")
        self.plan_btn.setMinimumHeight(36)
        self.plan_btn.setMinimumWidth(130)
        self.plan_btn.clicked.connect(self._on_plan_to_target)
        plan_row.addWidget(self.plan_btn)

        self.stop_plan_btn = QPushButton("停止规划路径")
        self.stop_plan_btn.setMinimumHeight(36)
        self.stop_plan_btn.setMinimumWidth(130)
        self.stop_plan_btn.clicked.connect(self.stop_planned_path_signal.emit)
        plan_row.addWidget(self.stop_plan_btn)

        plan_row.addStretch()
        target_layout.addSpacing(8)
        target_layout.addLayout(plan_row)

        # 不显示路径进度标签，保留计算逻辑（如果需要后台逻辑）
        target_group.setLayout(target_layout)
        main_layout.addWidget(target_group)
        self.setLayout(main_layout)

    def ensure_interactive(self):
        self.setEnabled(True)
        for edit in self.target_inputs:
            edit.setEnabled(True)
            edit.setReadOnly(False)
        self.plan_btn.setEnabled(True)
        self.stop_plan_btn.setEnabled(True)

    def _on_plan_to_target(self):
        values = []
        for edit in self.target_inputs:
            text = edit.text().strip()
            if not text:
                QMessageBox.warning(self, "输入错误", "请完整填写 X/Y/Z/Roll/Pitch/Yaw 六个目标值。")
                return
            try:
                values.append(float(text))
            except ValueError:
                QMessageBox.warning(self, "输入错误", "目标值格式错误，请输入有效数字。")
                return

        if len(values) != self.input_count:
            QMessageBox.warning(self, "输入错误", "目标值数量必须为6个。")
            return

        self.plan_to_target_signal.emit(values, self._speed_ratio)

    def set_speed_ratio(self, speed_ratio: float):
        self._speed_ratio = max(0.1, min(1.0, float(speed_ratio)))

    def update_plan_progress(self, current: int, total: int):
        # 取消UI路径进度显示，保留接口兼容性
        return
