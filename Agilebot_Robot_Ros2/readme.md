
<div align="right">
  
[中文简体](docs/readme_cn.md)

</div>

# Agiblebot Robot ROS2 Project



This project provides ROS 2 support for Agilebot Robotics products (http://www.sh-agilebot.com), including URDF description files, Gazebo configurations, and MoveIt2 configurations. Currently, it only includes the **C5A robot**, with plans to gradually add other models in the future.

## Project Structure

```
.
├── asset                    # Common asset files
├── gbt_description          # Robot description files and URDF models
├── gbt_gazebo               # Gazebo simulation configurations
├── gbt_roob_driver          # ROS 2 low-level driver package, designed to subscribe to and publish topics related to the robotic arm’s low-level information (not yet implemented)
└── gbt_moveit_config        # MoveIt2 configurations
```
markdown-preview-enhanced 
## Features

- **Universal Robot Descriptions (URDF)**: Physical and visual models for each robot model.
- **Gazebo Simulation**: Simulate each robot model within Gazebo.
- **MoveIt2 Support**: MoveIt2 configuration for each robot model, enabling path planning and motion control.

## Dependencies

- **ROS2 Distribution**: Humble
- **Gazebo**: For physics simulation
- **MoveIt2**: For path planning

## Installation

1. Clone the repository locally:

    ```bash
    cd {your_ros2_workspace_directory}/src
    git clone <repo-url>
    ```

2. Build the project:

    ```bash
    cd {your_ros2_workspace_directory}
    colcon build
    source install/setup.bash
    ```

## Quick Start

### Launch URDF Visualization in RViz

```bash
ros2 launch gbt_description display_{robot_model}.launch.py
```

Example:
```bash
ros2 launch gbt_description display_c5a.launch.py
```

### Start Gazebo Simulation

```bash
ros2 launch gbt_gazebo gazebo_{robot_model}_demo.launch.py
```

Example:
```bash
ros2 launch gbt_gazebo gazebo_c5a_demo.launch.py
```

### Launch MoveIt2 Configuration

```bash
ros2 launch {robot_model}_moveit_config demo.launch.py
```

Example:
```bash
ros2 launch c5a_moveit_config demo.launch.py
```

### Start MoveIt2 + Gazebo Simulation

**Terminal 1**: Launch the Gazebo simulation
```bash
ros2 launch {robot_model}_moveit_config gazebo.launch.py
```

Example:
```bash
ros2 launch c5a_moveit_config gazebo.launch.py
```

**Terminal 2**: Launch MoveIt2 motion planning
```bash
ros2 launch {robot_model}_moveit_config gazebo_moveit_rviz.launch.py
```

Example:
```bash
ros2 launch c5a_moveit_config gazebo_moveit_rviz.launch.py
```

## Future Development Plan

- [x] Add robot models and description files
    - [x] C5A robot
    - [ ] Add more robot models
- [ ] Add more simulation configurations
    - [x] C5A robot
    - [ ] Add more robot models
- [ ] Add more MoveIt2 configurations
    - [x] C5A robot
    - [ ] Add more robot models
- [ ] Add control modules for physical robots
- [ ] Add control modules for the simulator

## Contact

If you have any questions or suggestions, please submit them through the issue tracker.

## Contribution

Contributions of code, opinions, and suggestions are welcome! If contributing code, please review the contribution guidelines.

## License

This project is licensed under the **BSD 3-Clause License**. Please ensure you understand and agree to the terms before using the project.

