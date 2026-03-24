"""
机器人状态模拟器
定期发布模拟的关节状态，并通过信号发送给前端
"""
from PySide6.QtCore import QObject, QTimer, Signal, Slot
import math
import random
from .data_models import JointState, RobotStatus, RobotMode, ProgramStep


class RobotSimulator(QObject):
    # 定义信号
    joint_state_updated = Signal(list)  # List[JointState]
    robot_status_updated = Signal(object)  # RobotStatus
    system_log = Signal(str, str)  # (消息, 级别)
    planned_path_progress = Signal(int, int)  # (当前点, 总点)

    def __init__(self):
        super().__init__()
        self.joint_count = 6
        self.joint_positions = [0.0] * self.joint_count
        self.joint_velocities = [0.0] * self.joint_count
        self.is_enabled = False
        self.is_connected = True
        self._mode = RobotMode.IDLE
        self.is_emergency_stopped = False
        self.error_code = 0
        self.error_message = ""
        self.program_running = False
        self.program_line = 0
        self.program_paused = False
        self._program_steps: list = []
        self._program_tick = 0  # 每 20 次约 1 秒前进一步
        self.is_manual_mode = True  # True=手动, False=自动
        self._planned_path = []
        self._planned_path_running = False
        self._planned_path_total = 0
        self._planned_path_done = 0

        # 定时器：每50ms更新一次关节状态（20Hz）
        self.timer = QTimer()
        self.timer.timeout.connect(self._update_joint_states)
        self.timer.start(50)

    def _update_joint_states(self):
        """更新关节位置（模拟运动）"""
        # 若在执行规划路径，则按路径点更新位置
        if self._planned_path_running and self._planned_path:
            next_positions = self._planned_path.pop(0)
            self.joint_positions = list(next_positions)
            self.joint_velocities = [0.0] * self.joint_count
            self._mode = RobotMode.MOVING

            self._planned_path_done += 1
            self.planned_path_progress.emit(self._planned_path_done, self._planned_path_total)

            if not self._planned_path:
                self._planned_path_running = False
                self._mode = RobotMode.IDLE
                self.system_log.emit("目标位置路径执行完成", "INFO")
                self.planned_path_progress.emit(self._planned_path_total, self._planned_path_total)
        else:
            # 根据当前速度积分位置
            dt = 0.05  # 50ms
            for i in range(self.joint_count):
                self.joint_positions[i] += self.joint_velocities[i] * dt
                # 限制在 ±3.14 rad
                if self.joint_positions[i] > 3.14:
                    self.joint_positions[i] = 3.14
                    self.joint_velocities[i] = 0
                if self.joint_positions[i] < -3.14:
                    self.joint_positions[i] = -3.14
                    self.joint_velocities[i] = 0

        # 生成 JointState 列表
        states = []
        for i in range(self.joint_count):
            state = JointState(
                id=i,
                name=f"joint{i + 1}",
                position=self.joint_positions[i],
                velocity=self.joint_velocities[i],
                torque=random.uniform(0, 10) if self.is_enabled else 0,
                temperature=random.uniform(30, 45) if self.is_enabled else 25,
                is_enabled=self.is_enabled
            )
            states.append(state)

        # 程序步进（模拟：每秒前进一步）
        if self.program_running and not self.program_paused and self._program_steps:
            self._program_tick += 1
            if self._program_tick >= 20:
                self._program_tick = 0
                self.program_line += 1
                if self.program_line > len(self._program_steps):
                    self.program_running = False
                    self.program_line = 0
                    self._mode = RobotMode.IDLE
                    self.system_log.emit("程序执行完毕", "INFO")

        self.joint_state_updated.emit(states)

        status = RobotStatus(
            is_connected=self.is_connected,
            is_enabled=self.is_enabled,
            is_emergency_stopped=self.is_emergency_stopped,
            is_manual_mode=self.is_manual_mode,
            mode=self._mode,
            error_code=self.error_code,
            error_message=self.error_message,
            program_running=self.program_running,
            program_line=self.program_line,
        )
        self.robot_status_updated.emit(status)

    # ========== 外部调用的控制接口 ==========
    @Slot(int, float)
    def jog_joint(self, joint_id: int, velocity: float):
        """关节点动（仅手动模式允许）"""
        if self.is_emergency_stopped:
            self.system_log.emit("急停状态下禁止点动", "WARN")
            return
        if not self.is_manual_mode:
            self.system_log.emit("自动模式下禁止点动，请切换到手动模式", "WARN")
            return
        if self._mode == RobotMode.ERROR:
            self.system_log.emit("故障状态下禁止点动", "WARN")
            return
        if self._planned_path_running:
            self.system_log.emit("路径执行中，禁止手动点动", "WARN")
            return
        if self.is_enabled and 0 <= joint_id < self.joint_count:
            self.joint_velocities[joint_id] = velocity
            self._mode = RobotMode.MOVING
            self.system_log.emit(f"关节{joint_id + 1} 点动速度 {velocity:.2f} rad/s", "INFO")

    @Slot(int)
    def stop_joint(self, joint_id: int):
        """停止指定关节"""
        if 0 <= joint_id < self.joint_count:
            self.joint_velocities[joint_id] = 0.0
            if all(abs(v) < 0.001 for v in self.joint_velocities) and not self.is_emergency_stopped:
                self._mode = RobotMode.IDLE
            self.system_log.emit(f"关节{joint_id + 1} 停止", "INFO")

    @Slot()
    def enable_robot(self):
        """使能机器人"""
        if self.is_emergency_stopped:
            return
        self.is_enabled = True
        self.system_log.emit("机器人使能", "INFO")

    @Slot()
    def disable_robot(self):
        """去使能机器人"""
        self.is_enabled = False
        for i in range(self.joint_count):
            self.joint_velocities[i] = 0.0
        if not self.is_emergency_stopped:
            self._mode = RobotMode.IDLE
        self.system_log.emit("机器人去使能", "INFO")

    @Slot()
    def emergency_stop(self):
        """急停：停止所有运动并进入急停状态"""
        for i in range(self.joint_count):
            self.joint_velocities[i] = 0.0
        self.is_emergency_stopped = True
        self._mode = RobotMode.EMERGENCY_STOP
        self.system_log.emit("急停已触发", "WARN")

    @Slot(bool)
    def set_manual_mode(self, manual: bool):
        """设置手动/自动模式。True=手动(可点动), False=自动(可运行程序)"""
        self.is_manual_mode = manual
        self.system_log.emit("手动模式" if manual else "自动模式", "INFO")

    @Slot()
    def reset_emergency_stop(self):
        """急停复位"""
        self.is_emergency_stopped = False
        self._mode = RobotMode.IDLE
        self.system_log.emit("急停已复位", "INFO")

    @Slot(int, str)
    def set_error(self, code: int, message: str):
        """设置故障（供测试或真实驱动调用）"""
        self.error_code = code
        self.error_message = message
        self._mode = RobotMode.ERROR
        for i in range(self.joint_count):
            self.joint_velocities[i] = 0.0
        self.system_log.emit(f"故障 [{code}] {message}", "ERROR")

    @Slot()
    def clear_error(self):
        """清除故障"""
        self.error_code = 0
        self.error_message = ""
        if self._mode == RobotMode.ERROR:
            self._mode = RobotMode.IDLE
        self.system_log.emit("故障已清除", "INFO")

    # ========== 程序执行（模拟） ==========
    @Slot(list)
    def start_program(self, steps: list):
        """开始执行程序（steps 为 ProgramStep 列表）"""
        if self.is_emergency_stopped or self._mode == RobotMode.ERROR:
            return
        self._program_steps = list(steps)
        self.program_line = 1  # 当前执行第 1 行
        self.program_running = True
        self.program_paused = False
        self._program_tick = 0
        self._mode = RobotMode.MOVING
        self.system_log.emit(f"程序开始执行，共 {len(steps)} 步", "INFO")

    @Slot()
    def stop_program(self):
        """停止程序"""
        self.program_running = False
        self.program_paused = False
        self.program_line = 0
        if not self.is_emergency_stopped and self._mode == RobotMode.MOVING:
            self._mode = RobotMode.IDLE
        self.system_log.emit("程序已停止", "INFO")

    @Slot(list, float)
    def plan_to_target(self, target_positions: list, speed_ratio: float = 1.0):
        """规划并执行到目标关节位置（简化线性插补）。"""
        if self.is_emergency_stopped:
            self.system_log.emit("急停状态下禁止路径规划", "WARN")
            return
        if not self.is_manual_mode:
            self.system_log.emit("自动模式下禁止路径规划，请切换到手动模式", "WARN")
            return
        if self._mode == RobotMode.ERROR:
            self.system_log.emit("故障状态下禁止路径规划", "WARN")
            return
        if not self.is_enabled:
            self.system_log.emit("未使能状态下禁止路径规划", "WARN")
            return
        if len(target_positions) != self.joint_count:
            self.system_log.emit("目标关节数量不正确，路径规划失败", "ERROR")
            return

        target = [max(-3.14, min(3.14, float(v))) for v in target_positions]
        current = list(self.joint_positions)
        max_delta = max(abs(t - c) for t, c in zip(target, current))

        step_base = max(0.05, min(1.0, float(speed_ratio))) * 0.04
        steps = max(2, int(max_delta / step_base))

        # S曲线（平滑步进）：3x^2-2x^3
        path = []
        for s in range(1, steps + 1):
            x = s / steps
            ratio = 3 * x * x - 2 * x * x * x
            point = [c + (t - c) * ratio for c, t in zip(current, target)]
            path.append(point)

        self._planned_path = path
        self._planned_path_total = len(path)
        self._planned_path_done = 0
        self._planned_path_running = True
        self.planned_path_progress.emit(0, self._planned_path_total)
        self.system_log.emit(
            f"已规划平滑路径，插补点 {len(path)} 个，速度倍率 {speed_ratio:.2f}",
            "INFO",
        )

    @Slot()
    def stop_planned_path(self):
        """停止规划路径执行"""
        self._planned_path = []
        self._planned_path_running = False
        self._planned_path_done = 0
        self._planned_path_total = 0
        self.planned_path_progress.emit(-1, -1)
        if not self.is_emergency_stopped:
            self._mode = RobotMode.IDLE
        self.system_log.emit("规划路径已停止", "INFO")

    @Slot()
    def pause_program(self):
        """暂停程序"""
        self.program_paused = True
        self.system_log.emit("程序已暂停", "INFO")

    @Slot()
    def resume_program(self):
        """恢复程序"""
        self.program_paused = False
        self.system_log.emit("程序已恢复", "INFO")

    @Slot()
    def step_program(self):
        """单步执行：将当前行前进一步（仅当已暂停时有效）"""
        if not self.program_running or not self._program_steps:
            return
        self.program_line += 1
        if self.program_line > len(self._program_steps):
            self.program_running = False
            self.program_line = 0
            self._mode = RobotMode.IDLE
            self.system_log.emit("程序执行完毕", "INFO")
        else:
            self.system_log.emit(f"单步执行至第 {self.program_line} 行", "INFO")