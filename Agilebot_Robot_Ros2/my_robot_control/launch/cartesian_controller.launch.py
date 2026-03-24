# 文件名：controllers.launch.py（建议重命名，以反映功能）
from launch import LaunchDescription
from launch_ros.actions import Node
from launch.actions import DeclareLaunchArgument
from launch.substitutions import LaunchConfiguration

def generate_launch_description():
    # ========== 通用参数声明 ==========
    declare_planning_group_arg = DeclareLaunchArgument(
        'planning_group',
        default_value='arm_group',
        description='MoveIt!规划组名称（如arm_group/manipulator）'
    )
    declare_root_link_arg = DeclareLaunchArgument(
        'root_link',
        default_value='base_link',
        description='机器人根连杆名称'
    )
    declare_tip_link_arg = DeclareLaunchArgument(
        'tip_link',
        default_value='link6',
        description='机器人末端连杆名称'
    )
    declare_ground_z_arg = DeclareLaunchArgument(
        'ground_z',
        default_value='-0.01',
        description='地面碰撞体z轴位置（适配你的基座高度）'
    )
    declare_safety_z_arg = DeclareLaunchArgument(
        'safety_z_offset',
        default_value='0.1',
        description='目标最低z轴安全偏移（单位：米）'
    )

    # ========== 增量控制器专用参数 ==========
    declare_reference_frame_arg = DeclareLaunchArgument(
        'reference_frame',
        default_value='base_link',
        description='增量控制器参考坐标系'
    )
    declare_tip_frame_arg = DeclareLaunchArgument(
        'tip_frame',
        default_value='link6',
        description='增量控制器末端连杆'
    )
    declare_joint_step_arg = DeclareLaunchArgument(
        'joint_step',
        default_value='0.1',
        description='关节步长（弧度）'
    )
    declare_cart_step_trans_arg = DeclareLaunchArgument(
        'cart_step_trans',
        default_value='0.01',
        description='笛卡尔平移步长（米）'
    )
    declare_cart_step_rot_arg = DeclareLaunchArgument(
        'cart_step_rot',
        default_value='0.1',
        description='笛卡尔旋转步长（弧度）'
    )

    # ========== 笛卡尔控制器节点 ==========
    cartesian_controller_node = Node(
        package='my_robot_control',
        executable='cartesian_controller',
        name='cartesian_controller',
        output='screen',
        parameters=[{
            'planning_group': LaunchConfiguration('planning_group'),
            'root_link': LaunchConfiguration('root_link'),
            'tip_link': LaunchConfiguration('tip_link'),
            'ground_z': LaunchConfiguration('ground_z'),
            'safety_z_offset': LaunchConfiguration('safety_z_offset'),
            'ground_size_x': 10.0,
            'ground_size_y': 10.0,
            'ground_size_z': 0.01
        }],
        remappings=[]
    )

    # ========== 增量控制器节点 ==========
    incremental_controller_node = Node(
        package='my_robot_control',
        executable='incremental_controller',
        name='incremental_controller',
        output='screen',
        parameters=[{
            'reference_frame': LaunchConfiguration('reference_frame'),
            'tip_frame': LaunchConfiguration('tip_frame'),
            'joint_step': LaunchConfiguration('joint_step'),
            'cart_step_trans': LaunchConfiguration('cart_step_trans'),
            'cart_step_rot': LaunchConfiguration('cart_step_rot')
        }],
        remappings=[]
    )

    return LaunchDescription([
        # 声明所有参数
        declare_planning_group_arg,
        declare_root_link_arg,
        declare_tip_link_arg,
        declare_ground_z_arg,
        declare_safety_z_arg,
        declare_reference_frame_arg,
        declare_tip_frame_arg,
        declare_joint_step_arg,
        declare_cart_step_trans_arg,
        declare_cart_step_rot_arg,
        # 启动节点
        cartesian_controller_node,
        incremental_controller_node
    ])