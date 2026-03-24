import json
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget,
    QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QStatusBar, QMessageBox,
    QMenu, QToolBar, QComboBox,
    QFrame, QGridLayout, QFileDialog,
    QDialog, QDialogButtonBox,
    QListWidget, QListWidgetItem, QBoxLayout,
    QScrollArea, QSizePolicy, QSplitter,
)
from PySide6.QtCore import Qt, Slot, QSize, QTimer
from PySide6.QtGui import QAction, QKeySequence
from .widgets.jog_panel import JogPanel, TargetPosePanel
from core.robot_simulator import RobotSimulator
from api.moveit_api import Ros2Bridge
from ui.widgets.monitoring_panel import MonitoringPanel
from ui.widgets.tcp_config_dialog import TCPConfigDialog
from ui.widgets.robot_visualization import RobotVisualizationWidget
from ui.widgets.program_editor import ProgramEditor
from ui.widgets.user_management_dialog import UserManagementDialog
from core.data_models import JointState, RobotStatus

# 应用信息（关于 / 标题用）
APP_NAME = "协作机械臂上位机"
APP_VERSION = "1.0.0"


class MainWindow(QMainWindow):
    def __init__(self, user_role: str = "使用者", username: str = ""):
        super().__init__()
        self.setWindowTitle(f"{APP_NAME}  v{APP_VERSION}")
        self.resize(1400, 900)
        self.setMinimumSize(1100, 700)

        self.simulator = RobotSimulator()
        self.moveit_bridge = Ros2Bridge()
        self.user_role = user_role
        self.username = username

        # 轨迹模块状态
        self._trajectory_points = []
        self._is_recording_trajectory = False
        self._is_replaying_trajectory = False
        self._replay_index = 0
        self._last_joint_states = []
        self._record_start_ts = 0.0
        self._trajectory_replay_timer = QTimer(self)
        self._trajectory_replay_timer.timeout.connect(self._on_replay_tick)

        # 运行态持久化
        self._runtime_state_file = Path("configs") / "runtime_state.json"
        self._current_tcp_name = "未配置"
        self._current_work_object_name = "未配置"

        # 日志缓存
        self._logs = []
        self._max_logs = 500

        # 精简层级：移除顶部菜单栏，仅保留工具栏 + 标签页
        self.setup_toolbar()
        self.setup_ui()
        self.setup_status_bar()
        self.connect_signals()

        self._load_runtime_state()
        self._refresh_config_summary()
        self._apply_role_permissions()
        self.simulator.enable_robot()
        self._append_log(f"用户登录: {self.username or 'unknown'} ({self.user_role})", "INFO")
        self._append_log("系统启动完成", "INFO")
        self._switch_page(0)

    def setup_menu_bar(self):
        """菜单栏：文件、设置、帮助、系统"""
        menubar = self.menuBar()

        # 文件
        file_menu = menubar.addMenu("文件(&F)")
        exit_act = QAction("退出(&X)", self)
        exit_act.setShortcut(QKeySequence.Quit)
        exit_act.triggered.connect(self.close)
        file_menu.addAction(exit_act)

        # 设置
        settings_menu = menubar.addMenu("设置(&S)")
        lang_act = QAction("语言 / Language(&L)", self)
        lang_act.triggered.connect(self._on_language)
        settings_menu.addAction(lang_act)

        # 帮助
        help_menu = menubar.addMenu("帮助(&H)")
        about_act = QAction("关于(&A)", self)
        about_act.triggered.connect(self._on_about)
        help_menu.addAction(about_act)

        # 系统（重启/关机）
        system_menu = menubar.addMenu("系统(&Y)")
        restart_act = QAction("重启程序(&R)", self)
        restart_act.triggered.connect(self._on_restart)
        system_menu.addAction(restart_act)
        shutdown_act = QAction("关机(&S)", self)
        shutdown_act.triggered.connect(self._on_shutdown)
        system_menu.addAction(shutdown_act)

    def setup_toolbar(self):
        """顶部工具栏：运行/点动/监控/编程/轨迹/配置、模式切换、急停、扩展"""
        self.toolbar = QToolBar()
        self.toolbar.setObjectName("main_toolbar")
        self.toolbar.setMovable(False)
        self.toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(Qt.TopToolBarArea, self.toolbar)

        self._act_run = QAction("运行", self)
        self._act_run.setCheckable(True)
        self._act_run.triggered.connect(lambda: self._switch_page(0))
        self.toolbar.addAction(self._act_run)

        self._act_jog = QAction("点动", self)
        self._act_jog.setCheckable(True)
        self._act_jog.triggered.connect(lambda: self._switch_page(2))
        self.toolbar.addAction(self._act_jog)

        self._act_monitor = QAction("监控", self)
        self._act_monitor.setCheckable(True)
        self._act_monitor.triggered.connect(lambda: self._switch_page(1))
        self.toolbar.addAction(self._act_monitor)

        self._act_program = QAction("编程", self)
        self._act_program.setCheckable(True)
        self._act_program.triggered.connect(lambda: self._switch_page(3))
        self.toolbar.addAction(self._act_program)

        self._act_trajectory = QAction("轨迹", self)
        self._act_trajectory.setCheckable(True)
        self._act_trajectory.triggered.connect(lambda: self._switch_page(4))
        self.toolbar.addAction(self._act_trajectory)

        self._act_config = QAction("配置", self)
        self._act_config.setCheckable(True)
        self._act_config.triggered.connect(lambda: self._switch_page(5))
        self.toolbar.addAction(self._act_config)

        self._nav_actions = {
            0: self._act_run,
            1: self._act_monitor,
            2: self._act_jog,
            3: self._act_program,
            4: self._act_trajectory,
            5: self._act_config,
        }

        self.toolbar.addSeparator()

        self._mode_combo = QComboBox()
        self._mode_combo.addItems(["手动", "自动"])
        self._mode_combo.setMinimumWidth(80)
        self._mode_combo.currentIndexChanged.connect(self._on_mode_combo_changed)
        self.toolbar.addWidget(QLabel(" 模式: "))
        self.toolbar.addWidget(self._mode_combo)

        self.toolbar.addSeparator()

        self.toolbar_stop_btn = QPushButton("  STOP  ")
        self.toolbar_stop_btn.setProperty("emergency", True)
        self.toolbar_stop_btn.setMinimumHeight(36)
        self.toolbar_stop_btn.clicked.connect(self.simulator.emergency_stop)
        self.toolbar.addWidget(self.toolbar_stop_btn)

        self._act_plugin = QAction("扩展", self)
        self._act_plugin.triggered.connect(self._on_plugin_platform)
        self.toolbar.addAction(self._act_plugin)

        self._act_user_mgmt = QAction("用户管理", self)
        self._act_user_mgmt.triggered.connect(self._on_user_management)
        self.toolbar.addAction(self._act_user_mgmt)

    def setup_ui(self):
        """创建UI布局：运行、监控、控制、编程、轨迹、配置"""
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(False)
        self.tabs.setContentsMargins(0, 0, 0, 0)
        # 仅保留工具栏导航，隐藏标签栏
        self.tabs.tabBar().hide()

        self.run_tab = self._create_run_tab()
        self.tabs.addTab(self.run_tab, "  运行  ")

        self.monitor_tab = self._create_monitor_tab()
        self.tabs.addTab(self.monitor_tab, "  监控  ")

        self.control_tab = self._create_control_tab()
        self.tabs.addTab(self.control_tab, "  点动  ")

        self.program_tab = self._create_program_tab()
        self.tabs.addTab(self.program_tab, "  编程  ")

        self.trajectory_tab = self._create_trajectory_tab()
        self.tabs.addTab(self.trajectory_tab, "  轨迹  ")

        self.config_tab = self._create_config_tab()
        self.tabs.addTab(self.config_tab, "  配置  ")

        self.tabs.currentChanged.connect(self._sync_toolbar_nav_state)
        self.setCentralWidget(self.tabs)

    def _create_run_tab(self):
        """运行（主页）：简要状态、当前程序、快捷操作"""
        wrap = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("操作主页")
        title.setProperty("pageTitle", True)
        layout.addWidget(title)

        frame = QFrame()
        frame.setObjectName("contentCard")
        flay = QVBoxLayout(frame)
        flay.setContentsMargins(20, 20, 20, 20)
        flay.setSpacing(14)

        self.run_status_label = QLabel("状态: 就绪")
        self.run_status_label.setProperty("sectionTitle", True)
        flay.addWidget(self.run_status_label)

        self.run_program_label = QLabel("当前程序: —")
        self.run_program_label.setProperty("subtleText", True)
        flay.addWidget(self.run_program_label)

        self.run_config_label = QLabel("TCP: 未配置 | 工件: 未配置")
        self.run_config_label.setProperty("subtleText", True)
        flay.addWidget(self.run_config_label)

        btn_row = QHBoxLayout()
        self.run_btn_main = QPushButton("运行程序")
        self.run_btn_main.setObjectName("primaryBtn")
        self.run_btn_main.setMinimumHeight(44)
        self.run_btn_main.clicked.connect(self._on_program_run)
        btn_row.addWidget(self.run_btn_main)

        to_program = QPushButton("进入编程")
        to_program.setMinimumHeight(44)
        to_program.clicked.connect(lambda: self.tabs.setCurrentIndex(3))
        btn_row.addWidget(to_program)

        to_jog = QPushButton("进入点动")
        to_jog.setMinimumHeight(44)
        to_jog.clicked.connect(lambda: self.tabs.setCurrentIndex(2))
        btn_row.addWidget(to_jog)

        to_monitor = QPushButton("进入监控")
        to_monitor.setMinimumHeight(44)
        to_monitor.clicked.connect(lambda: self.tabs.setCurrentIndex(1))
        btn_row.addWidget(to_monitor)

        flay.addLayout(btn_row)
        layout.addWidget(frame)
        layout.addStretch()
        wrap.setLayout(layout)
        return wrap

    def _create_monitor_tab(self):
        """监控页面 - 监控面板 + 日志面板"""
        wrap = QWidget()
        self.monitor_layout = QBoxLayout(QBoxLayout.TopToBottom)
        self.monitor_layout.setContentsMargins(8, 8, 8, 8)
        self.monitor_layout.setSpacing(8)

        self.monitor_panel = MonitoringPanel()
        self.monitor_layout.addWidget(self.monitor_panel, 3)

        log_card = QFrame()
        log_card.setObjectName("contentCard")
        log_layout = QVBoxLayout(log_card)
        log_layout.setContentsMargins(12, 12, 12, 12)
        log_layout.setSpacing(8)

        title_row = QHBoxLayout()
        title = QLabel("系统日志")
        title.setProperty("sectionTitle", True)
        title_row.addWidget(title)

        self.log_level_combo = QComboBox()
        self.log_level_combo.addItems(["ALL", "INFO", "WARN", "ERROR"])
        self.log_level_combo.currentTextChanged.connect(self._refresh_log_view)
        title_row.addWidget(self.log_level_combo)

        export_btn = QPushButton("导出日志")
        export_btn.clicked.connect(self._export_logs)
        title_row.addWidget(export_btn)

        clear_btn = QPushButton("清空日志")
        clear_btn.clicked.connect(self._clear_logs)
        title_row.addWidget(clear_btn)
        title_row.addStretch()
        log_layout.addLayout(title_row)

        self.log_list = QListWidget()
        log_layout.addWidget(self.log_list)

        alarm_title = QLabel("告警历史（WARN/ERROR）")
        alarm_title.setProperty("sectionTitle", True)
        log_layout.addWidget(alarm_title)

        self.alarm_list = QListWidget()
        self.alarm_list.setMaximumHeight(120)
        log_layout.addWidget(self.alarm_list)

        self.monitor_layout.addWidget(log_card, 2)
        wrap.setLayout(self.monitor_layout)
        return wrap

    def _create_control_tab(self):
        """控制页面 - 集成点动面板"""
        tab = QWidget()
        self.control_layout = QHBoxLayout()
        self.control_layout.setSpacing(12)
        self.control_layout.setContentsMargins(12, 12, 12, 12)

        self.jog_panel = JogPanel()
        jog_scroll = QScrollArea()
        jog_scroll.setWidgetResizable(True)
        jog_scroll.setFrameShape(QFrame.NoFrame)
        jog_scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        jog_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        jog_scroll.setWidget(self.jog_panel)
        self.control_layout.addWidget(jog_scroll, 1)

        # 右侧：机械臂示意图 + 底部目标位姿规划（垂直布局，防止遮挡）
        self.visualization_panel = RobotVisualizationWidget()
        self.visualization_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.target_pose_panel = TargetPosePanel()
        self.target_pose_panel.setMinimumHeight(260)
        self.target_pose_panel.setMaximumHeight(340)
        self.target_pose_panel.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Minimum)

        right_col = QWidget()
        right_col_layout = QVBoxLayout()
        right_col_layout.setContentsMargins(0, 0, 0, 0)
        right_col_layout.setSpacing(8)
        right_col_layout.addWidget(self.visualization_panel, 7)
        right_col_layout.addWidget(self.target_pose_panel, 3)
        right_col.setLayout(right_col_layout)
        self.control_layout.addWidget(right_col, 1)

        tab.setLayout(self.control_layout)
        return tab

    def _create_program_tab(self):
        """编程页面"""
        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(12)
        self.program_editor = ProgramEditor()
        layout.addWidget(self.program_editor)
        tab.setLayout(layout)
        return tab

    def _create_config_tab(self):
        """配置页面 - 卡片式配置入口"""
        from PySide6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel, QGridLayout, QFrame

        tab = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)

        title = QLabel("系统配置")
        title.setProperty("pageTitle", True)
        layout.addWidget(title)

        card = QFrame()
        card.setObjectName("contentCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(14)

        grid = QGridLayout()
        grid.setSpacing(12)

        tcp_btn = QPushButton("TCP / 工具坐标系")
        tcp_btn.setMinimumHeight(56)
        tcp_btn.clicked.connect(self.open_tcp_config)
        grid.addWidget(tcp_btn, 0, 0)

        safety_btn = QPushButton("安全参数")
        safety_btn.setMinimumHeight(56)
        safety_btn.clicked.connect(self.open_safety_config)
        grid.addWidget(safety_btn, 0, 1)

        wo_btn = QPushButton("工件坐标系")
        wo_btn.setMinimumHeight(56)
        wo_btn.clicked.connect(self.open_work_object_config)
        grid.addWidget(wo_btn, 1, 0)

        card_layout.addLayout(grid)
        card_layout.addStretch()
        layout.addWidget(card)
        layout.addStretch()
        tab.setLayout(layout)
        return tab

    def _create_trajectory_tab(self):
        """轨迹页：录制、保存、加载、回放"""
        wrap = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(14)

        title = QLabel("轨迹")
        title.setProperty("pageTitle", True)
        layout.addWidget(title)

        desc = QLabel("支持示教录制关节轨迹，保存/加载轨迹文件并按倍率回放。")
        desc.setProperty("subtleText", True)
        desc.setWordWrap(True)
        layout.addWidget(desc)

        card = QFrame()
        card.setObjectName("contentCard")
        card_layout = QVBoxLayout(card)
        card_layout.setContentsMargins(18, 18, 18, 18)
        card_layout.setSpacing(12)

        self.trajectory_info_label = QLabel("未加载轨迹")
        self.trajectory_info_label.setProperty("sectionTitle", True)
        card_layout.addWidget(self.trajectory_info_label)

        self.trajectory_progress_label = QLabel("点数: 0 | 时长: 0.00s")
        self.trajectory_progress_label.setProperty("subtleText", True)
        card_layout.addWidget(self.trajectory_progress_label)

        ctrl_row = QHBoxLayout()
        self.record_btn = QPushButton("开始录制")
        self.record_btn.setMinimumHeight(42)
        self.record_btn.clicked.connect(self._toggle_trajectory_recording)
        ctrl_row.addWidget(self.record_btn)

        self.save_traj_btn = QPushButton("保存轨迹")
        self.save_traj_btn.setMinimumHeight(42)
        self.save_traj_btn.clicked.connect(self._save_trajectory)
        ctrl_row.addWidget(self.save_traj_btn)

        self.load_traj_btn = QPushButton("加载轨迹")
        self.load_traj_btn.setMinimumHeight(42)
        self.load_traj_btn.clicked.connect(self._load_trajectory)
        ctrl_row.addWidget(self.load_traj_btn)

        self.replay_btn = QPushButton("开始回放")
        self.replay_btn.setMinimumHeight(42)
        self.replay_btn.clicked.connect(self._toggle_trajectory_replay)
        ctrl_row.addWidget(self.replay_btn)

        card_layout.addLayout(ctrl_row)

        speed_row = QHBoxLayout()
        speed_row.addWidget(QLabel("回放倍率"))
        self.trajectory_speed_combo = QComboBox()
        self.trajectory_speed_combo.addItems(["0.5x", "1.0x", "1.5x", "2.0x"])
        self.trajectory_speed_combo.setCurrentText("1.0x")
        self.trajectory_speed_combo.setMinimumWidth(100)
        speed_row.addWidget(self.trajectory_speed_combo)
        speed_row.addStretch()
        card_layout.addLayout(speed_row)

        layout.addWidget(card)
        layout.addStretch()
        wrap.setLayout(layout)
        return wrap

    # 添加打开TCP配置对话框的方法
    def open_tcp_config(self):
        """打开TCP配置对话框"""
        from core.config_manager import ConfigManager

        config_manager = ConfigManager()
        dialog = TCPConfigDialog(config_manager, self)

        # 连接配置变更信号，以便更新其他界面
        dialog.config_changed.connect(self.on_tcp_config_changed)

        if dialog.exec():
            self.status_bar.showMessage("TCP配置已更新", 3000)

    def open_safety_config(self):
        """打开安全参数配置对话框"""
        from core.config_manager import ConfigManager
        from ui.widgets.safety_config_dialog import SafetyConfigDialog

        config_manager = ConfigManager()
        dialog = SafetyConfigDialog(config_manager, self)
        if dialog.exec():
            self.status_bar.showMessage("安全参数配置已更新", 3000)

    def open_work_object_config(self):
        """打开工件坐标系配置对话框"""
        from core.config_manager import ConfigManager
        from ui.widgets.work_object_config_dialog import WorkObjectConfigDialog

        config_manager = ConfigManager()
        dialog = WorkObjectConfigDialog(config_manager, self)
        dialog.config_changed.connect(self.on_work_object_config_changed)
        if dialog.exec():
            self.status_bar.showMessage("工件坐标系配置已更新", 3000)

    def on_work_object_config_changed(self):
        """工件坐标系配置变更"""
        self._refresh_config_summary()
        self.status_bar.showMessage("工件坐标系配置已应用", 2500)

    def on_tcp_config_changed(self):
        """TCP配置变更时的处理"""
        self._refresh_config_summary()
        self.status_bar.showMessage("TCP配置已应用", 2500)

    def setup_status_bar(self):
        """状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)

        # 故障信息（仅当 error_code != 0 时显示）
        self.error_label = QLabel("")
        self.error_label.setStyleSheet("color: red;")
        self.status_bar.addWidget(self.error_label)

        # 急停复位 / 清除故障
        self.reset_estop_btn = QPushButton("急停复位")
        self.reset_estop_btn.clicked.connect(self.simulator.reset_emergency_stop)
        self.clear_error_btn = QPushButton("清除故障")
        self.clear_error_btn.clicked.connect(self.simulator.clear_error)
        self.status_bar.addPermanentWidget(self.reset_estop_btn)
        self.status_bar.addPermanentWidget(self.clear_error_btn)

        # 当前页面与登录信息
        self.current_page_label = QLabel("当前页: 运行")
        self.current_page_label.setProperty("subtleText", True)
        self.status_bar.addPermanentWidget(self.current_page_label)

        self.user_info_label = QLabel(f"用户: {self.username or '-'} | 角色: {self.user_role}")
        self.user_info_label.setProperty("subtleText", True)
        self.status_bar.addPermanentWidget(self.user_info_label)

        # 连接状态指示灯
        self.conn_indicator = QLabel("●")
        self.conn_indicator.setStyleSheet("color: green; font-size: 16px;")
        self.status_bar.addPermanentWidget(self.conn_indicator)
        self._last_error_shown = False

    def connect_signals(self):
        """连接前后端信号"""
        # 点动命令 -> 模拟器（紧急停止 / 急停复位）
        self.jog_panel.jog_signal.connect(self._on_jog_joint_moveit)

        self.jog_panel.stop_signal.connect(self.simulator.stop_joint)
        self.jog_panel.emergency_stop_signal.connect(self.simulator.emergency_stop)
        self.jog_panel.reset_estop_signal.connect(self.simulator.reset_emergency_stop)
        # 直接用moveit bridge替换仿真规划
        self.target_pose_panel.plan_to_target_signal.connect(self._on_plan_to_target_moveit)
        self.target_pose_panel.stop_planned_path_signal.connect(self._on_stop_plan_moveit)

        # 模拟器状态更新 -> UI
        self.simulator.joint_state_updated.connect(self.on_joint_state_updated)
        self.simulator.robot_status_updated.connect(self.on_robot_status_updated)
        self.simulator.system_log.connect(self.on_system_log)

        # 模拟器关节状态 -> 监控与可视化
        self.simulator.joint_state_updated.connect(self.monitor_panel.update_joint_states)
        self.simulator.joint_state_updated.connect(self.visualization_panel.update_joint_states)
        # self.simulator.planned_path_progress 绑定已由UI不需要展示而最小化

        # 点动速度同步给目标位姿规划速度比例
        self.target_pose_panel.set_speed_ratio(self.jog_panel.speed_slider.value() / 100.0)
        self.jog_panel.speed_slider.valueChanged.connect(
            lambda v: self.target_pose_panel.set_speed_ratio(v / 100.0)
        )

        # 程序运行：编程页按钮 -> 模拟器
        self.program_editor.run_clicked.connect(self._on_program_run)
        self.program_editor.stop_clicked.connect(self.simulator.stop_program)
        self.program_editor.pause_clicked.connect(self.simulator.pause_program)
        self.program_editor.resume_clicked.connect(self.simulator.resume_program)
        self.program_editor.step_clicked.connect(self.simulator.step_program)
        # 模拟器状态 -> 编程页当前行高亮
        self.simulator.robot_status_updated.connect(self._on_robot_status_for_program)
    def _on_jog_joint_moveit(self, joint_id, velocity):
        # joint_id: 0-based, moveit_api期望1-based
        # velocity: 正负方向，实际只需方向
        direction = 1 if velocity > 0 else -1
        self.moveit_bridge.send_joint_increment(joint_id + 1, direction)

    def _on_stop_plan_moveit(self):
        # 调用moveit_api的停止方法
        self.moveit_bridge.send_stop_command()

    def _on_plan_to_target_moveit(self, values, speed_ratio):
        # values: [x, y, z, roll, pitch, yaw]，单位：m, deg
        frame_id = "base_link"
        x, y, z, roll, pitch, yaw = values
        self.moveit_bridge.send_velocity_scale(speed_ratio)
        self.moveit_bridge.send_cartesian_goal(frame_id, x, y, z, roll, pitch, yaw)
    # ========== 槽函数 ==========
    @Slot(list)
    def on_joint_state_updated(self, states):
        """更新点动面板上的关节角度"""
        self._last_joint_states = states
        for i, state in enumerate(states):
            self.jog_panel.update_joint_position(i, state.position)

        if self._is_recording_trajectory and states:
            now = time.time()
            point = {
                "t": round(now - self._record_start_ts, 4),
                "positions": [round(s.position, 6) for s in states],
            }
            self._trajectory_points.append(point)
            self._refresh_trajectory_summary()

    @Slot(object)
    def on_robot_status_updated(self, status):
        """更新状态栏"""
        if status.is_connected:
            self.conn_indicator.setStyleSheet("color: green; font-size: 16px;")
        else:
            self.conn_indicator.setStyleSheet("color: red; font-size: 16px;")

        mode_text = status.mode.value if hasattr(status.mode, "value") else str(status.mode)
        if status.is_emergency_stopped:
            self.status_label.setText("状态: 急停 (未使能)")
        elif status.is_enabled:
            self.status_label.setText(f"状态: {mode_text} (已使能)")
        else:
            self.status_label.setText(f"状态: {mode_text} (未使能)")

        # 运行页状态与程序名
        if hasattr(self, "run_status_label"):
            self.run_status_label.setText(self.status_label.text())
        if hasattr(self, "run_program_label"):
            self.run_program_label.setText("当前程序: " + self.program_editor.get_program_name())
        # 同步工具栏 手动/自动 与模拟器（避免重复触发）
        if hasattr(self, "_mode_combo"):
            idx = 0 if status.is_manual_mode else 1
            if self._mode_combo.currentIndex() != idx:
                self._mode_combo.blockSignals(True)
                self._mode_combo.setCurrentIndex(idx)
                self._mode_combo.blockSignals(False)

        # 故障显示与弹窗
        if status.error_code != 0:
            self.error_label.setText(f"  [故障 {status.error_code}] {status.error_message}")
            if not self._last_error_shown:
                self._last_error_shown = True
                QMessageBox.warning(
                    self,
                    "机器人故障",
                    f"故障码: {status.error_code}\n{status.error_message}\n\n请排查后点击「清除故障」。",
                )
        else:
            self.error_label.setText("")
            self._last_error_shown = False

    @Slot(str, str)
    def on_system_log(self, msg, level):
        """处理日志（统一缓存并显示）"""
        self._append_log(msg, level)

    def _append_log(self, msg: str, level: str = "INFO"):
        ts = time.strftime("%H:%M:%S")
        item = {
            "time": ts,
            "level": level.upper(),
            "msg": str(msg),
        }
        self._logs.append(item)
        if len(self._logs) > self._max_logs:
            self._logs = self._logs[-self._max_logs:]
        self._refresh_log_view()

    def _refresh_log_view(self):
        if not hasattr(self, "log_list"):
            return
        current_level = self.log_level_combo.currentText() if hasattr(self, "log_level_combo") else "ALL"
        self.log_list.clear()
        if hasattr(self, "alarm_list"):
            self.alarm_list.clear()

        for log in self._logs:
            text = f"[{log['time']}] [{log['level']}] {log['msg']}"

            if current_level == "ALL" or log["level"] == current_level:
                item = QListWidgetItem(text)
                if log["level"] == "WARN":
                    item.setForeground(Qt.yellow)
                elif log["level"] == "ERROR":
                    item.setForeground(Qt.red)
                self.log_list.addItem(item)

            if hasattr(self, "alarm_list") and log["level"] in {"WARN", "ERROR"}:
                alarm_item = QListWidgetItem(text)
                if log["level"] == "WARN":
                    alarm_item.setForeground(Qt.yellow)
                else:
                    alarm_item.setForeground(Qt.red)
                self.alarm_list.addItem(alarm_item)

        if self.log_list.count() > 0:
            self.log_list.scrollToBottom()
        if hasattr(self, "alarm_list") and self.alarm_list.count() > 0:
            self.alarm_list.scrollToBottom()

    def _clear_logs(self):
        self._logs.clear()
        self._refresh_log_view()
        self.status_bar.showMessage("日志已清空", 2000)

    def _export_logs(self):
        if not self._logs:
            self.status_bar.showMessage("没有可导出的日志", 2000)
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "导出日志", "", "Log Files (*.json)")
        if not file_path:
            return
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(self._logs, f, ensure_ascii=False, indent=2)
        self.status_bar.showMessage("日志导出完成", 2500)

    def _on_program_run(self):
        """运行程序：将当前编程页步骤交给模拟器执行"""
        ok, err, err_line = self.program_editor.validate_program()
        if not ok:
            self.program_editor.set_error_line(err_line)
            QMessageBox.warning(self, "程序校验失败", err or "程序存在非法参数")
            self._append_log(f"程序校验失败: {err}", "ERROR")
            self.status_bar.showMessage("程序校验失败", 3000)
            return
        self.program_editor.clear_error_line()

        steps = self.program_editor.get_steps()
        if self.simulator.is_emergency_stopped:
            QMessageBox.warning(self, "无法运行", "当前处于急停状态，请先急停复位。")
            self._append_log("急停状态下尝试运行程序", "WARN")
            return
        if self.simulator.error_code != 0:
            QMessageBox.warning(self, "无法运行", f"存在故障[{self.simulator.error_code}]，请先清除故障。")
            self._append_log(f"故障状态下尝试运行程序: {self.simulator.error_code}", "WARN")
            return
        if self.simulator.is_manual_mode:
            QMessageBox.information(self, "提示", "当前为手动模式，已自动切换为自动模式后运行。")
            self._mode_combo.setCurrentIndex(1)

        self.simulator.start_program(steps)
        self._append_log(f"程序开始执行: {self.program_editor.get_program_name()}", "INFO")
        self.status_bar.showMessage("程序已开始执行", 3000)

    @Slot(object)
    def _on_robot_status_for_program(self, status):
        """根据机器人状态更新编程页当前执行行高亮"""
        self.program_editor.set_current_line(status.program_line)

    def _on_language(self):
        """语言切换（占位，后续可接 QTranslator）"""
        QMessageBox.information(
            self,
            "语言",
            "当前支持：简体中文。\n语言切换（多语言）可后续接入 QTranslator 实现。",
        )

    def _on_about(self):
        """关于"""
        QMessageBox.about(
            self,
            "关于",
            f"<h3>{APP_NAME}</h3><p>版本 {APP_VERSION}</p><p>基于 PySide6 的协作机械臂控制系统。</p>",
        )

    def _on_restart(self):
        """重启程序"""
        if QMessageBox.Yes != QMessageBox.question(
            self, "重启", "确定要重新启动程序吗？", QMessageBox.Yes | QMessageBox.No
        ):
            return
        import sys
        import subprocess
        subprocess.Popen([sys.executable] + sys.argv)
        from PySide6.QtWidgets import QApplication
        QApplication.quit()

    def _on_shutdown(self):
        """关机（此处为退出程序；真实关机由操作系统执行）"""
        if QMessageBox.Yes != QMessageBox.question(
            self, "退出", "确定要退出程序吗？", QMessageBox.Yes | QMessageBox.No
        ):
            return
        self.close()

    def _switch_page(self, index: int):
        """通过工具栏切换页面并刷新选中态"""
        self.tabs.setCurrentIndex(index)
        self._sync_toolbar_nav_state(index)
        if index == 2 and hasattr(self, "jog_panel"):
            self.jog_panel.ensure_interactive()
        if index == 2 and hasattr(self, "jog_panel"):
            self.jog_panel.ensure_interactive()

    @Slot(int)
    def _sync_toolbar_nav_state(self, current_index: int):
        """同步工具栏导航按钮的选中态"""
        for idx, action in self._nav_actions.items():
            action.setChecked(idx == current_index)

        page_names = {
            0: "运行",
            1: "监控",
            2: "点动",
            3: "编程",
            4: "轨迹",
            5: "配置",
        }
        if hasattr(self, "current_page_label"):
            self.current_page_label.setText(f"当前页: {page_names.get(current_index, '未知')}")

    def _refresh_trajectory_summary(self):
        count = len(self._trajectory_points)
        duration = self._trajectory_points[-1]["t"] if count > 0 else 0.0
        self.trajectory_progress_label.setText(f"点数: {count} | 时长: {duration:.2f}s")

    def _toggle_trajectory_recording(self):
        if self._is_replaying_trajectory:
            self.status_bar.showMessage("回放中无法录制", 2500)
            return
        if not self._is_recording_trajectory:
            self._trajectory_points = []
            self._record_start_ts = time.time()
            self._is_recording_trajectory = True
            self.record_btn.setText("停止录制")
            self.trajectory_info_label.setText("轨迹录制中...")
            self.status_bar.showMessage("开始录制轨迹", 2000)
            return

        self._is_recording_trajectory = False
        self.record_btn.setText("开始录制")
        self.trajectory_info_label.setText("录制完成")
        self._refresh_trajectory_summary()
        self.status_bar.showMessage("轨迹录制已停止", 2500)

    def _save_trajectory(self):
        if not self._trajectory_points:
            self.status_bar.showMessage("没有可保存的轨迹", 2500)
            return
        file_path, _ = QFileDialog.getSaveFileName(self, "保存轨迹", "", "Trajectory Files (*.json)")
        if not file_path:
            return
        payload = {
            "version": 1,
            "joint_count": self.simulator.joint_count,
            "points": self._trajectory_points,
        }
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        self.trajectory_info_label.setText(f"已保存: {file_path}")
        self.status_bar.showMessage("轨迹已保存", 2500)

    def _load_trajectory(self):
        if self._is_recording_trajectory:
            self.status_bar.showMessage("录制中无法加载轨迹", 2500)
            return
        file_path, _ = QFileDialog.getOpenFileName(self, "加载轨迹", "", "Trajectory Files (*.json)")
        if not file_path:
            return
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                payload = json.load(f)
            points = payload.get("points", [])
            if not points:
                raise ValueError("轨迹点为空")
            self._trajectory_points = points
            self._refresh_trajectory_summary()
            self.trajectory_info_label.setText(f"已加载: {file_path}")
            self.status_bar.showMessage("轨迹加载成功", 2500)
        except Exception as e:
            QMessageBox.warning(self, "加载失败", f"轨迹文件无效：{e}")

    def _toggle_trajectory_replay(self):
        if not self._is_replaying_trajectory:
            if not self._trajectory_points:
                self.status_bar.showMessage("请先录制或加载轨迹", 2500)
                return
            if self.simulator.is_emergency_stopped:
                self.status_bar.showMessage("急停状态下不可回放", 2500)
                self._append_log("急停状态下尝试回放轨迹", "WARN")
                return
            if self.simulator.error_code != 0:
                self.status_bar.showMessage("故障状态下不可回放", 2500)
                self._append_log("故障状态下尝试回放轨迹", "WARN")
                return

            valid_points = []
            for p in self._trajectory_points:
                positions = p.get("positions", []) if isinstance(p, dict) else []
                if len(positions) != self.simulator.joint_count:
                    continue
                clipped = [max(-3.14, min(3.14, float(v))) for v in positions]
                valid_points.append({"t": float(p.get("t", 0.0)), "positions": clipped})

            if not valid_points:
                QMessageBox.warning(self, "轨迹无效", "轨迹点无效或维度不匹配，无法回放。")
                self._append_log("轨迹回放失败：轨迹点无效", "ERROR")
                return

            self._trajectory_points = valid_points
            self._is_replaying_trajectory = True
            self._replay_index = 0
            self.replay_btn.setText("停止回放")
            self.trajectory_info_label.setText("轨迹回放中...")
            self._append_log(f"轨迹开始回放，点数={len(self._trajectory_points)}", "INFO")
            self._start_replay_timer()
            return

        self._stop_trajectory_replay("轨迹回放已停止")

    def _start_replay_timer(self):
        speed_text = self.trajectory_speed_combo.currentText().replace("x", "")
        try:
            speed = float(speed_text)
        except ValueError:
            speed = 1.0
        interval_ms = max(20, int(50 / speed))
        self._trajectory_replay_timer.start(interval_ms)

    def _on_replay_tick(self):
        if self._replay_index >= len(self._trajectory_points):
            self._stop_trajectory_replay("轨迹回放完成")
            return
        point = self._trajectory_points[self._replay_index]
        positions = point.get("positions", [])
        if positions:
            for i, pos in enumerate(positions):
                if i < self.simulator.joint_count:
                    self.simulator.joint_positions[i] = float(pos)
                    self.jog_panel.update_joint_position(i, float(pos))
            self.simulator.joint_velocities = [0.0] * self.simulator.joint_count
        self._replay_index += 1

    def _stop_trajectory_replay(self, msg: str):
        self._is_replaying_trajectory = False
        self._trajectory_replay_timer.stop()
        self.replay_btn.setText("开始回放")
        self.trajectory_info_label.setText("轨迹已就绪")
        self._append_log(msg, "INFO")
        self.status_bar.showMessage(msg, 2500)

    def _refresh_config_summary(self):
        from core.config_manager import ConfigManager

        config_manager = ConfigManager()
        tools = config_manager.load_tool_config()
        work_objects = config_manager.load_work_object_config()
        self._current_tcp_name = tools[0].name if tools else "未配置"
        self._current_work_object_name = work_objects[0].name if work_objects else "未配置"
        self._config_applied_time = time.strftime("%H:%M:%S")

        if hasattr(self, "run_config_label"):
            self.run_config_label.setText(
                f"TCP: {self._current_tcp_name} | 工件: {self._current_work_object_name} | 生效: {self._config_applied_time}"
            )

    def _load_runtime_state(self):
        try:
            if not self._runtime_state_file.exists():
                return
            with open(self._runtime_state_file, "r", encoding="utf-8") as f:
                state = json.load(f)
            last_page = int(state.get("last_page", 0))
            mode = str(state.get("mode", "manual"))
            if mode == "auto":
                self._mode_combo.setCurrentIndex(1)
            else:
                self._mode_combo.setCurrentIndex(0)

            w = int(state.get("window_w", self.width()))
            h = int(state.get("window_h", self.height()))
            x = int(state.get("window_x", self.x()))
            y = int(state.get("window_y", self.y()))
            self.resize(max(1100, w), max(700, h))
            self.move(x, y)

            self._switch_page(last_page if 0 <= last_page <= 5 else 0)
        except Exception:
            self._switch_page(0)

    def _apply_role_permissions(self):
        """根据角色控制入口权限。"""
        role = self.user_role

        if role == "使用者":
            self._act_config.setEnabled(False)
            self._act_program.setEnabled(False)
            if hasattr(self, "_act_plugin"):
                self._act_plugin.setEnabled(False)
            if hasattr(self, "_act_user_mgmt"):
                self._act_user_mgmt.setEnabled(False)
            self._append_log("已应用使用者权限：禁用编程/配置/扩展/用户管理", "INFO")

        elif role == "管理者":
            self._act_config.setEnabled(True)
            self._act_program.setEnabled(True)
            if hasattr(self, "_act_plugin"):
                self._act_plugin.setEnabled(False)
            if hasattr(self, "_act_user_mgmt"):
                self._act_user_mgmt.setEnabled(False)
            self._append_log("已应用管理者权限：允许编程与配置，禁用扩展/用户管理", "INFO")

        else:  # 超级管理者
            self._act_config.setEnabled(True)
            self._act_program.setEnabled(True)
            if hasattr(self, "_act_plugin"):
                self._act_plugin.setEnabled(True)
            if hasattr(self, "_act_user_mgmt"):
                self._act_user_mgmt.setEnabled(True)
            self._append_log("已应用超级管理者权限：全功能可用", "INFO")

    def _save_runtime_state(self):
        try:
            self._runtime_state_file.parent.mkdir(parents=True, exist_ok=True)
            g = self.geometry()
            state = {
                "last_page": self.tabs.currentIndex(),
                "mode": "manual" if self._mode_combo.currentIndex() == 0 else "auto",
                "last_program_name": self.program_editor.get_program_name(),
                "window_x": g.x(),
                "window_y": g.y(),
                "window_w": g.width(),
                "window_h": g.height(),
            }
            with open(self._runtime_state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._adapt_layout_for_window_size()

    def _adapt_layout_for_window_size(self):
        """窗口尺寸变化时，仅调整比例，不切换布局方向。"""
        if hasattr(self, "control_layout"):
            # 固定左右方向，只按窗口比例调整权重
            self.control_layout.setDirection(QBoxLayout.LeftToRight)
            if self.width() < 1280:
                self.control_layout.setStretch(0, 3)
                self.control_layout.setStretch(1, 2)
            else:
                self.control_layout.setStretch(0, 2)
                self.control_layout.setStretch(1, 3)

        if hasattr(self, "monitor_layout"):
            # 高度不足时，监控页面分区按比例压缩
            if self.height() < 800:
                self.monitor_layout.setStretch(0, 2)
                self.monitor_layout.setStretch(1, 3)
            else:
                self.monitor_layout.setStretch(0, 3)
                self.monitor_layout.setStretch(1, 2)

    def closeEvent(self, event):
        self._save_runtime_state()
        super().closeEvent(event)

    def _on_mode_combo_changed(self, index: int):
        """工具栏 手动/自动 切换"""
        self.simulator.set_manual_mode(index == 0)

    def _on_plugin_platform(self):
        """扩展 / HRApp 插件平台（占位）"""
        dlg = QDialog(self)
        dlg.setWindowTitle("扩展平台")
        layout = QVBoxLayout(dlg)
        layout.addWidget(QLabel("插件平台（开发中）\n\n类似 HRApp，可在此接入扩展应用与插件。"))
        layout.addWidget(QDialogButtonBox(QDialogButtonBox.Ok, accepted=dlg.accept))
        dlg.exec()

    def _on_user_management(self):
        """用户管理（仅超级管理者）"""
        if self.user_role != "超级管理者":
            QMessageBox.warning(self, "无权限", "仅超级管理者可打开用户管理。")
            return
        dlg = UserManagementDialog(current_username=self.username, parent=self)
        dlg.exec()