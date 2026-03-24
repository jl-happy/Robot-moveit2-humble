"""
监控面板
显示6个关节的实时位置曲线 + 关节状态数值表
"""
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QGroupBox, QGridLayout)
from PySide6.QtCore import Qt, QTimer
import pyqtgraph as pg

class MonitoringPanel(QWidget):
    def __init__(self):
        super().__init__()
        # 先初始化数据缓冲区
        self.data_buffer = {}
        self.curves = []
        self.joint_status_labels = []
        self.time_counter = 0

        # 再设置UI
        self.setup_ui()

        # 定时器：推进时间轴
        self.timer = QTimer()
        self.timer.timeout.connect(self._advance_time)
        self.timer.start(100)  # 100ms

    def setup_ui(self):
        main_layout = QHBoxLayout()
        main_layout.setSpacing(16)
        main_layout.setContentsMargins(8, 8, 8, 8)

        # === 左侧：关节实时曲线（深色主题） ===
        curve_group = QGroupBox("关节位置实时曲线")
        curve_layout = QVBoxLayout()

        self.plot_widget = pg.PlotWidget(title="关节位置 (rad)")
        self.plot_widget.setBackground("#252538")
        self.plot_widget.getPlotItem().getViewBox().setBackgroundColor("#252538")
        self.plot_widget.setLabel("left", "位置", units="rad", color="#a0a0b8")
        self.plot_widget.setLabel("bottom", "时间", units="s", color="#a0a0b8")
        self.plot_widget.getPlotItem().getAxis("left").setPen(pg.mkPen("#606078"))
        self.plot_widget.getPlotItem().getAxis("bottom").setPen(pg.mkPen("#606078"))
        self.plot_widget.getPlotItem().getAxis("left").setTextPen(pg.mkPen("#a0a0b8"))
        self.plot_widget.getPlotItem().getAxis("bottom").setTextPen(pg.mkPen("#a0a0b8"))
        self.plot_widget.showGrid(x=True, y=True, alpha=0.25)
        self.plot_widget.addLegend(offset=(10, 10))

        colors = ["#ef5350", "#ff9800", "#ffca28", "#66bb6a", "#42a5f5", "#ab47bc"]
        for i in range(6):
            curve = self.plot_widget.plot(
                pen=pg.mkPen(color=colors[i], width=2),
                name=f'J{i+1}'
            )
            self.curves.append(curve)
            self.data_buffer[f'joint_{i}'] = {'time': [], 'pos': []}

        curve_layout.addWidget(self.plot_widget)
        curve_group.setLayout(curve_layout)
        main_layout.addWidget(curve_group, 3)

        # === 右侧：关节状态数值面板 ===
        status_group = QGroupBox("关节详细状态")
        status_layout = QGridLayout()

        # 表头
        status_layout.addWidget(QLabel("关节"), 0, 0)
        status_layout.addWidget(QLabel("位置(rad)"), 0, 1)
        status_layout.addWidget(QLabel("速度(rad/s)"), 0, 2)
        status_layout.addWidget(QLabel("力矩(Nm)"), 0, 3)
        status_layout.addWidget(QLabel("温度(℃)"), 0, 4)

        for i in range(6):
            row = i + 1
            # 关节名称
            status_layout.addWidget(QLabel(f"J{i+1}"), row, 0)

            # 位置
            pos_label = QLabel("0.000")
            pos_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            status_layout.addWidget(pos_label, row, 1)

            # 速度
            vel_label = QLabel("0.000")
            vel_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            status_layout.addWidget(vel_label, row, 2)

            # 力矩
            torque_label = QLabel("0.0")
            torque_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            status_layout.addWidget(torque_label, row, 3)

            # 温度
            temp_label = QLabel("0.0")
            temp_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            status_layout.addWidget(temp_label, row, 4)

            self.joint_status_labels.append((pos_label, vel_label, torque_label, temp_label))

        status_group.setLayout(status_layout)
        main_layout.addWidget(status_group, 1)

        self.setLayout(main_layout)

    def update_joint_states(self, states):
        """由主窗口调用，更新关节状态显示和曲线"""
        for i, state in enumerate(states):
            if i >= 6:
                break
            # 更新右侧数值
            pos_label, vel_label, torque_label, temp_label = self.joint_status_labels[i]
            pos_label.setText(f"{state.position:.3f}")
            vel_label.setText(f"{state.velocity:.3f}")
            torque_label.setText(f"{state.torque:.1f}")
            temp_label.setText(f"{state.temperature:.1f}")

            # 更新曲线数据
            self.data_buffer[f'joint_{i}']['time'].append(self.time_counter)
            self.data_buffer[f'joint_{i}']['pos'].append(state.position)

            # 只保留最近200个点
            if len(self.data_buffer[f'joint_{i}']['time']) > 200:
                self.data_buffer[f'joint_{i}']['time'] = self.data_buffer[f'joint_{i}']['time'][-200:]
                self.data_buffer[f'joint_{i}']['pos'] = self.data_buffer[f'joint_{i}']['pos'][-200:]

            # 更新曲线
            self.curves[i].setData(
                self.data_buffer[f'joint_{i}']['time'],
                self.data_buffer[f'joint_{i}']['pos']
            )

    def _advance_time(self):
        """推进时间计数器"""
        self.time_counter += 0.1  # 每100ms增加0.1秒