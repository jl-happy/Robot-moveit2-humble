"""
配置管理器
负责所有配置文件的读写和管理（YAML格式）
"""
import yaml
import math
import hashlib
from pathlib import Path
from typing import List, Optional
from core.data_models import ToolTCP, SafetyConfig, WorkObject


class ConfigManager:
    """配置管理器"""

    def __init__(self, config_dir: str = "configs"):
        self.config_dir = Path(config_dir)
        self.config_dir.mkdir(exist_ok=True)

        # 配置文件路径
        self.tool_config_file = self.config_dir / "tool_config.yaml"
        self.work_object_config_file = self.config_dir / "work_object_config.yaml"
        self.safety_config_file = self.config_dir / "safety_config.yaml"
        self.robot_config_file = self.config_dir / "robot_config.yaml"
        self.users_config_file = self.config_dir / "users.yaml"

        # 初始化默认配置
        self._init_default_configs()

    def _init_default_configs(self):
        """初始化默认配置文件（如果不存在）"""
        if not self.tool_config_file.exists():
            default_tools = {
                "tools": [
                    {
                        "name": "default_gripper",
                        "position": [0.0, 0.0, 0.1],
                        "orientation_euler": [0.0, 0.0, 0.0],  # 度
                        "frame_id": "tool0"
                    }
                ]
            }
            self.save_yaml(self.tool_config_file, default_tools)

        if not self.work_object_config_file.exists():
            default_wo = {
                "work_objects": [
                    {
                        "name": "base",
                        "position": [0.0, 0.0, 0.0],
                        "orientation_euler": [0.0, 0.0, 0.0],
                        "frame_id": "world",
                        "user_frame_id": 0,
                    }
                ]
            }
            self.save_yaml(self.work_object_config_file, default_wo)

        if not self.safety_config_file.exists():
            default_safety = {
                "joint_limits_deg": [
                    [-360, 360], [-180, 180], [-180, 180],
                    [-360, 360], [-360, 360], [-360, 360]
                ],
                "tcp_max_velocity": 1.0,
                "tcp_max_acceleration": 3.0,
                "collision_sensitivity": 3
            }
            self.save_yaml(self.safety_config_file, default_safety)

        if not self.robot_config_file.exists():
            default_robot = {
                "robot": {
                    "type": "UR5e",
                    "ip": "192.168.1.100",
                    "port": 30003,
                    "joint_count": 6
                },
                "simulation": {
                    "enabled": True,
                    "simulator": "pybullet"
                }
            }
            self.save_yaml(self.robot_config_file, default_robot)

        if not self.users_config_file.exists():
            default_users = {
                "users": [
                    {
                        "username": "operator",
                        "password_hash": self.hash_password("123456"),
                        "role": "使用者",
                    },
                    {
                        "username": "manager",
                        "password_hash": self.hash_password("admin123"),
                        "role": "管理者",
                    },
                    {
                        "username": "root",
                        "password_hash": self.hash_password("root123"),
                        "role": "超级管理者",
                    },
                ]
            }
            self.save_yaml(self.users_config_file, default_users)

    # ========== 工具TCP配置 ==========
    def load_tool_config(self) -> List[ToolTCP]:
        """加载工具TCP配置"""
        if not self.tool_config_file.exists():
            return []

        data = self.load_yaml(self.tool_config_file)
        tools = []
        for tool_data in data.get("tools", []):
            # 欧拉角转弧度
            euler_deg = tool_data.get("orientation_euler", [0, 0, 0])
            euler_rad = [math.radians(d) for d in euler_deg]
            tool = ToolTCP.from_euler(
                name=tool_data["name"],
                position=tool_data["position"],
                euler=euler_rad,
                frame_id=tool_data.get("frame_id", "tool0")
            )
            tools.append(tool)
        return tools

    def save_tool_config(self, tools: List[ToolTCP]) -> bool:
        """保存工具TCP配置"""
        tools_data = []
        for tool in tools:
            euler = tool.to_euler()
            euler_deg = [math.degrees(e) for e in euler]
            tools_data.append({
                "name": tool.name,
                "position": tool.position,
                "orientation_euler": euler_deg,
                "frame_id": tool.frame_id
            })
        return self.save_yaml(self.tool_config_file, {"tools": tools_data})

    # ========== 工件坐标系配置 ==========
    def load_work_object_config(self) -> List[WorkObject]:
        """加载工件坐标系配置"""
        if not self.work_object_config_file.exists():
            return []

        data = self.load_yaml(self.work_object_config_file)
        result = []
        for wo in data.get("work_objects", []):
            euler_deg = wo.get("orientation_euler", [0, 0, 0])
            euler_rad = [math.radians(d) for d in euler_deg]
            result.append(
                WorkObject.from_euler(
                    name=wo.get("name", "base"),
                    position=wo.get("position", [0.0, 0.0, 0.0]),
                    euler=euler_rad,
                    frame_id=wo.get("frame_id", "world"),
                    user_frame_id=int(wo.get("user_frame_id", 0)),
                )
            )
        return result

    def save_work_object_config(self, work_objects: List[WorkObject]) -> bool:
        """保存工件坐标系配置"""
        data_list = []
        for wo in work_objects:
            euler = wo.to_euler()
            euler_deg = [math.degrees(e) for e in euler]
            data_list.append({
                "name": wo.name,
                "position": wo.position,
                "orientation_euler": euler_deg,
                "frame_id": wo.frame_id,
                "user_frame_id": wo.user_frame_id,
            })
        return self.save_yaml(self.work_object_config_file, {"work_objects": data_list})

    # ========== 安全配置 ==========
    def get_safety_config(self) -> SafetyConfig:
        """获取安全配置"""
        if not self.safety_config_file.exists():
            return self._default_safety_config()

        data = self.load_yaml(self.safety_config_file)
        limits_deg = data.get("joint_limits_deg", [])
        # 如果配置文件为空或关节数量不正确，回退到默认配置
        if not limits_deg or len(limits_deg) != 6:
            return self._default_safety_config()
        limits_lower = [math.radians(l[0]) for l in limits_deg]
        limits_upper = [math.radians(l[1]) for l in limits_deg]

        return SafetyConfig(
            joint_limits_lower=limits_lower,
            joint_limits_upper=limits_upper,
            tcp_max_velocity=data.get("tcp_max_velocity", 1.0),
            tcp_max_acceleration=data.get("tcp_max_acceleration", 3.0),
            collision_sensitivity=data.get("collision_sensitivity", 3),
            enable_soft_limits=data.get("enable_soft_limits", True),
            enable_collision_detection=data.get("enable_collision_detection", True),
        )

    def _default_safety_config(self) -> SafetyConfig:
        """默认安全配置"""
        return SafetyConfig(
            joint_limits_lower=[-6.283, -3.142, -3.142, -6.283, -6.283, -6.283],
            joint_limits_upper=[6.283, 3.142, 3.142, 6.283, 6.283, 6.283],
            tcp_max_velocity=1.0,
            tcp_max_acceleration=3.0,
            collision_sensitivity=3,
            enable_soft_limits=True,
            enable_collision_detection=True,
        )

    def save_safety_config(self, config: SafetyConfig) -> bool:
        """保存安全配置"""
        limits_deg = []
        for low, up in zip(config.joint_limits_lower, config.joint_limits_upper):
            limits_deg.append([math.degrees(low), math.degrees(up)])

        data = {
            "joint_limits_deg": limits_deg,
            "tcp_max_velocity": config.tcp_max_velocity,
            "tcp_max_acceleration": config.tcp_max_acceleration,
            "collision_sensitivity": config.collision_sensitivity,
            "enable_soft_limits": config.enable_soft_limits,
            "enable_collision_detection": config.enable_collision_detection,
        }
        return self.save_yaml(self.safety_config_file, data)

    # ========== 用户配置 ==========
    def load_users(self) -> List[dict]:
        """加载用户配置"""
        if not self.users_config_file.exists():
            return []
        data = self.load_yaml(self.users_config_file)
        users = data.get("users", [])
        return users if isinstance(users, list) else []

    def save_users(self, users: List[dict]) -> bool:
        """保存用户配置。若存在明文 password，会自动转为 password_hash。"""
        normalized = []
        for user in users:
            username = str(user.get("username", "")).strip()
            role = str(user.get("role", "使用者")).strip() or "使用者"
            if not username:
                continue

            item = {
                "username": username,
                "role": role,
            }

            if user.get("password_hash"):
                item["password_hash"] = str(user.get("password_hash"))
            elif user.get("password"):
                item["password_hash"] = self.hash_password(str(user.get("password")))
            else:
                # 无密码信息则跳过该用户
                continue

            normalized.append(item)

        if not normalized:
            return False

        return self.save_yaml(self.users_config_file, {"users": normalized})

    def save_users(self, users: List[dict]) -> bool:
        """保存用户配置（自动清理并保证使用 password_hash）"""
        cleaned = []
        for user in users:
            username = str(user.get("username", "")).strip()
            role = str(user.get("role", "使用者")).strip() or "使用者"
            if not username:
                continue

            item = {
                "username": username,
                "role": role,
            }
            if "password_hash" in user and user.get("password_hash"):
                item["password_hash"] = str(user.get("password_hash"))
            elif "password" in user and user.get("password"):
                item["password_hash"] = self.hash_password(str(user.get("password")))
            else:
                # 若没有密码信息则跳过，避免写入不可登录账号
                continue
            cleaned.append(item)

        return self.save_yaml(self.users_config_file, {"users": cleaned})

    @staticmethod
    def hash_password(password: str) -> str:
        """密码哈希（SHA-256）"""
        return hashlib.sha256(password.encode("utf-8")).hexdigest()

    @staticmethod
    def verify_password(raw_password: str, user: dict) -> bool:
        """验证密码。兼容旧字段 password，优先 password_hash。"""
        if "password_hash" in user:
            return ConfigManager.hash_password(raw_password) == str(user.get("password_hash", ""))
        return str(user.get("password", "")) == raw_password

    def migrate_users_to_password_hash(self) -> bool:
        """将 users.yaml 中明文 password 迁移为 password_hash。"""
        users = self.load_users()
        changed = False
        migrated = []

        for user in users:
            item = dict(user)
            if "password_hash" in item:
                migrated.append(item)
                continue

            raw_pwd = str(item.get("password", ""))
            if raw_pwd:
                item["password_hash"] = self.hash_password(raw_pwd)
                item.pop("password", None)
                changed = True
            migrated.append(item)

        if changed:
            return self.save_yaml(self.users_config_file, {"users": migrated})
        return True

    # ========== YAML文件操作 ==========
    @staticmethod
    def save_yaml(path: Path, data: dict) -> bool:
        """保存YAML文件"""
        try:
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(data, f, default_flow_style=False, allow_unicode=True)
            return True
        except Exception as e:
            print(f"保存YAML失败 {path}: {e}")
            return False

    @staticmethod
    def load_yaml(path: Path) -> dict:
        """加载YAML文件"""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            print(f"加载YAML失败 {path}: {e}")
            return {}