from moveit_configs_utils import MoveItConfigsBuilder
from moveit_configs_utils.launches import generate_moveit_rviz_launch

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument,
    IncludeLaunchDescription,
)
from moveit_configs_utils.launch_utils import (
    add_debuggable_node,
    DeclareBooleanLaunchArg,
)
from launch.substitutions import LaunchConfiguration
from launch_ros.parameter_descriptions import ParameterValue

"""
文件说明：
该文件用于启动 MoveIt 和 RViz，以便在 Gazebo 中进行机械臂的仿真和调试。

功能：
- 启动 MoveIt 节点以支持运动规划。
- 启动 RViz 以进行可视化。
- 将joint state 发送到 gazebo 进行仿真。
"""

def generate_launch_description():
    # 创建MoveItConfigsBuilder对象，用于生成MoveIt配置
    moveit_config = MoveItConfigsBuilder("c5a_description", package_name="c5a_moveit_config").to_moveit_configs() 

    # 创建LaunchDescription对象，用于启动节点
    ld = LaunchDescription()

    # 启动move_group
    gbt_generate_move_group_launch(ld, moveit_config)
    # 启动rviz
    gbt_generate_moveit_rviz_launch(ld, moveit_config)

    # 返回LaunchDescription对象
    return ld


def gbt_generate_move_group_launch(ld, moveit_config):
    """
    配置并添加 move_group 节点的启动参数和节点到 LaunchDescription。
    """

    # 添加一个布尔类型的启动参数，用于调试，默认值为False
    ld.add_action(DeclareBooleanLaunchArg("debug", default_value=False))
    # 添加一个布尔类型的启动参数，用于允许轨迹执行，默认值为True
    ld.add_action(
        DeclareBooleanLaunchArg("allow_trajectory_execution", default_value=True)
    )
    # 添加一个布尔类型的启动参数，用于发布监控规划场景，默认值为True
    ld.add_action(
        DeclareBooleanLaunchArg("publish_monitored_planning_scene", default_value=True)
    )
    # load non-default MoveGroup capabilities (space separated)
    ld.add_action(DeclareLaunchArgument("capabilities", default_value=""))
    # inhibit these default MoveGroup capabilities (space separated)
    ld.add_action(DeclareLaunchArgument("disable_capabilities", default_value=""))

    # do not copy dynamics information from /joint_states to internal robot monitoring
    # default to false, because almost nothing in move_group relies on this information
    ld.add_action(DeclareBooleanLaunchArg("monitor_dynamics", default_value=False))

    should_publish = LaunchConfiguration("publish_monitored_planning_scene")

    move_group_configuration = {
        "publish_robot_description_semantic": True,
        "allow_trajectory_execution": LaunchConfiguration("allow_trajectory_execution"),
        # Note: Wrapping the following values is necessary so that the parameter value can be the empty string
        "capabilities": ParameterValue(
            LaunchConfiguration("capabilities"), value_type=str
        ),
        "disable_capabilities": ParameterValue(
            LaunchConfiguration("disable_capabilities"), value_type=str
        ),
        # Publish the planning scene of the physical robot so that rviz plugin can know actual robot
        "publish_planning_scene": should_publish,
        "publish_geometry_updates": should_publish,
        "publish_state_updates": should_publish,
        "publish_transforms_updates": should_publish,
        "monitor_dynamics": False,
    }

    move_group_params = [
        moveit_config.to_dict(),
        move_group_configuration,
    ]
    move_group_params.append({"use_sim_time": True})

    # 添加可调试的 move_group 节点
    add_debuggable_node(
        ld,
        package="moveit_ros_move_group",
        executable="move_group",
        commands_file=str(moveit_config.package_path / "launch" / "gdb_settings.gdb"),
        output="screen",
        parameters=move_group_params,
        extra_debug_args=["--debug"],
        # Set the display variable, in case OpenGL code is used internally
        additional_env={"DISPLAY": ":0"},
    )
    return ld

def gbt_generate_moveit_rviz_launch(ld, moveit_config):
    """
    配置并添加 RViz 节点的启动参数到 LaunchDescription。
    """

    # 添加一个布尔类型的启动参数，默认值为False
    ld.add_action(DeclareBooleanLaunchArg("debug", default_value=False))
    # 添加 RViz 配置文件参数，默认为 MoveIt 配置中的 RViz 文件，默认值为config/moveit.rviz
    ld.add_action(
        DeclareLaunchArgument(
            "rviz_config",
            default_value=str(moveit_config.package_path / "config/moveit.rviz"),
        )
    )

    # 定义rviz的参数
    rviz_parameters = [
        moveit_config.planning_pipelines,
        moveit_config.robot_description_kinematics,
    ]
    # 添加一个参数，使用仿真时间
    rviz_parameters.append({"use_sim_time": True})

    # 添加一个可调试的节点，使用rviz2包，可执行文件为rviz2，输出为log，参数为rviz_config和rviz_parameters
    add_debuggable_node(
        ld,
        package="rviz2",
        executable="rviz2",
        output="log",
        respawn=False,
        arguments=["-d", LaunchConfiguration("rviz_config")],
        parameters=rviz_parameters,
    )

    # 返回launch描述符
    return ld
