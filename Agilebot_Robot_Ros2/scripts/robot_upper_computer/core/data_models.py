"""
核心数据模型定义
所有前后端共享的数据结构必须在此定义
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from enum import Enum
import math


class RobotMode(Enum):
    """机器人运行模式"""
    IDLE = "IDLE"
    MOVING = "MOVING"
    TEACHING = "TEACHING"
    ERROR = "ERROR"
    EMERGENCY_STOP = "EMERGENCY_STOP"


class CommandType(Enum):
    """程序命令类型"""
    MOVEJ = "MoveJ"
    MOVEL = "MoveL"
    MOVEC = "MoveC"
    WAIT = "Wait"
    SET_DO = "SetDO"
    SET_AO = "SetAO"
    IF = "If"
    CALL = "Call"


@dataclass
class JointState:
    """单个关节状态"""
    id: int
    name: str
    position: float          # rad
    velocity: float          # rad/s
    torque: Optional[float] = 0.0
    temperature: Optional[float] = 0.0
    is_enabled: bool = False


@dataclass
class RobotStatus:
    """机器人整体状态"""
    is_connected: bool = False
    is_enabled: bool = False
    is_emergency_stopped: bool = False
    is_manual_mode: bool = True   # True=手动, False=自动
    mode: RobotMode = RobotMode.IDLE
    error_code: int = 0
    error_message: str = ""
    program_running: bool = False
    program_line: int = 0


@dataclass
class ToolTCP:
    """工具坐标系 (Tool Center Point)"""
    name: str
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])  # [x, y, z] in meters
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])  # [x, y, z, w] quaternion
    frame_id: str = "tool0"

    def to_euler(self) -> List[float]:
        """将四元数转换为欧拉角 [roll, pitch, yaw] (弧度)"""
        x, y, z, w = self.orientation
        # 避免除零错误
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)

        sinp = 2 * (w * y - z * x)
        if abs(sinp) >= 1:
            pitch = math.copysign(math.pi / 2, sinp)
        else:
            pitch = math.asin(sinp)

        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)

        return [roll, pitch, yaw]

    @classmethod
    def from_euler(cls, name: str, position: List[float], euler: List[float], frame_id: str = "tool0"):
        """从欧拉角创建 ToolTCP 对象"""
        roll, pitch, yaw = euler
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

        return cls(
            name=name,
            position=position,
            orientation=[x, y, z, w],
            frame_id=frame_id
        )


@dataclass
class WorkObject:
    """工件坐标系"""
    name: str = "base"
    frame_id: str = "world"
    position: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0])
    orientation: List[float] = field(default_factory=lambda: [0.0, 0.0, 0.0, 1.0])  # [x,y,z,w] 四元数
    user_frame_id: int = 0

    def to_euler(self) -> List[float]:
        """四元数转欧拉角 [roll, pitch, yaw] 弧度"""
        x, y, z, w = self.orientation
        sinr_cosp = 2 * (w * x + y * z)
        cosr_cosp = 1 - 2 * (x * x + y * y)
        roll = math.atan2(sinr_cosp, cosr_cosp)
        sinp = 2 * (w * y - z * x)
        pitch = math.asin(sinp) if abs(sinp) < 1 else math.copysign(math.pi / 2, sinp)
        siny_cosp = 2 * (w * z + x * y)
        cosy_cosp = 1 - 2 * (y * y + z * z)
        yaw = math.atan2(siny_cosp, cosy_cosp)
        return [roll, pitch, yaw]

    @classmethod
    def from_euler(
        cls,
        name: str,
        position: List[float],
        euler: List[float],
        frame_id: str = "world",
        user_frame_id: int = 0,
    ):
        """从欧拉角 [roll,pitch,yaw] 弧度创建"""
        roll, pitch, yaw = euler
        cy, sy = math.cos(yaw * 0.5), math.sin(yaw * 0.5)
        cp, sp = math.cos(pitch * 0.5), math.sin(pitch * 0.5)
        cr, sr = math.cos(roll * 0.5), math.sin(roll * 0.5)
        w = cr * cp * cy + sr * sp * sy
        x = sr * cp * cy - cr * sp * sy
        y = cr * sp * cy + sr * cp * sy
        z = cr * cp * sy - sr * sp * cy
        return cls(
            name=name,
            position=position,
            orientation=[x, y, z, w],
            frame_id=frame_id,
            user_frame_id=user_frame_id,
        )


@dataclass
class SafetyConfig:
    """安全配置参数"""
    joint_limits_lower: List[float]   # 6个关节下限 (rad)
    joint_limits_upper: List[float]   # 6个关节上限 (rad)
    tcp_max_velocity: float           # m/s
    tcp_max_acceleration: float       # m/s²
    collision_sensitivity: int = 3
    enable_soft_limits: bool = True
    enable_collision_detection: bool = True


@dataclass
class ProgramStep:
    """程序步骤（用于图形化编程）"""
    id: int
    command: str
    parameters: Dict[str, Any]
    comment: str = ""
    line_number: int = 0