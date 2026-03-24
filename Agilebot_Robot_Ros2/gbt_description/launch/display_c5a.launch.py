import os
from launch import LaunchDescription
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from launch_ros.substitutions import FindPackageShare
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription


"""
文件说明：
此文件用于在 RViz 中可视化 URDF 机器人模型。
"""

def generate_launch_description():
    # 定义包名、urdf文件名和rviz配置文件名
    package_name = 'gbt_description'
    urdf_name = "GBT_C5A.urdf"
    rviz_name="display.rviz"

    ld = LaunchDescription()
    # 查找包的路径
    pkg_share = FindPackageShare(package=package_name).find(package_name) 
    # 拼接urdf文件路径
    urdf_model_path = os.path.join(pkg_share, f'urdf/{urdf_name}')
    # 拼接rviz配置文件路径
    rviz_config_path = os.path.join(pkg_share, f'rviz/{rviz_name}')

    # 创建robot_state_publisher节点
    robot_state_publisher_node = Node(
        package='robot_state_publisher',
        executable='robot_state_publisher',
        arguments=[urdf_model_path]
        )

    # 创建joint_state_publisher_gui节点
    joint_state_publisher_node = Node(
        package='joint_state_publisher_gui',
        executable='joint_state_publisher_gui',
        name='joint_state_publisher_gui',
        arguments=[urdf_model_path]
        )

    # Launch Argument: RViz 配置文件的路径
    rvizconfig_arg = DeclareLaunchArgument(
        name='rvizconfig',
        default_value=rviz_config_path,
        description='Absolute path to rviz config file'
    )


    # 创建rviz2节点
    rviz2_node = Node(
        package='rviz2',
        executable='rviz2',
        name='rviz2',
        output='screen',
        arguments=['-d', LaunchConfiguration('rvizconfig')],
        parameters=[{'use_sim_time': False}]
        )
    
    # 添加Launch Argument
    ld.add_action(rvizconfig_arg)  # Ensure this is added
    # 添加robot_state_publisher节点
    ld.add_action(robot_state_publisher_node)
    # 添加joint_state_publisher_gui节点
    ld.add_action(joint_state_publisher_node)
    # 添加rviz2节点
    ld.add_action(rviz2_node)

    return ld