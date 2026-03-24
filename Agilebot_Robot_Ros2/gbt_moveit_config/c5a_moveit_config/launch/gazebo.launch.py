import os
from launch import LaunchDescription
from launch.actions import ExecuteProcess, RegisterEventHandler
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.event_handlers import OnProcessExit
import xacro
import re
from launch.actions import IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
"""
文件说明：
此文件用于启动 Gazebo 仿真环境，并加载机器人模型。
"""

# 定义一个函数，用于移除 URDF 标签中的注释
def remove_comments(text):
    pattern = r'<!--(.*?)-->'
    return re.sub(pattern, '', text, flags=re.DOTALL)

def generate_launch_description():
    """
    生成启动描述，用于启动 Gazebo 和机器人相关的 ROS 2 节点。
    """
    # 定义机器人名称、包名称和launch文件名称
    robot_name_in_model = 'gbt_c5a'
    package_name = 'gbt_gazebo'
    launch_name = "gazebo_c5a_demo.launch.py"

    # 获取包路径
    pkg_share = FindPackageShare(package=package_name).find(package_name)
    launch_script_path = os.path.join(pkg_share, 'launch', launch_name)

    # 创建启动描述并添加所有动作
    ld = LaunchDescription()

    # 使用 IncludeLaunchDescription 启动另一个launch文件
    ld.add_action(
        IncludeLaunchDescription(
            PythonLaunchDescriptionSource(launch_script_path)
        )
    )

   
    return ld
