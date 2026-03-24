from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_demo_launch

"""
文件说明：
该文件用于启动 MoveIt 和 RViz，以便进行机械臂的运动规划和可视化。

功能：
- 启动 MoveIt 节点以支持运动规划。
- 启动 RViz 以进行可视化。
"""
def generate_launch_description():
    moveit_config = MoveItConfigsBuilder("c5a_description", package_name="c5a_moveit_config").to_moveit_configs()
    return generate_demo_launch(moveit_config)
