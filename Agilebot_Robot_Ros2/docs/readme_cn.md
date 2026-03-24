

# 上海捷勃特机器人 ROS2 项目

该项目是上海捷勃特机器人产品对ros2的支持（http://www.sh-agilebot.com），包含的 URDF 描述文件、Gazebo 配置和 MoveIt2 配置。目前仅包含 **C5A 机器人**，未来会逐步添加其他型号。

## 项目结构

```
.
├── asset                    # 通用资源文件
├── gbt_description          # 机器人描述文件和URDF模型
├── gbt_gazebo               # Gazebo仿真配置
├── gbt_roob_driver          # ROS2底层驱动功能包，其作用为订阅和发布机械臂底层相关话题信息(暂未实现)
└── gbt_moveit_config        # MoveIt2 配置

```

## 功能和特性

- **通用机器人描述 (URDF)**：包含各机器人型号的物理和视觉模型。
- **Gazebo 仿真**： Gazebo 中仿真各型号机器人。
- **MoveIt2 支持**：各型号机器人配置 MoveIt2，支持路径规划和运动控制。

## 环境依赖

- **ROS2 Distribution**: Humble
- **Gazebo**：用于物理仿真
- **MoveIt2**：用于路径规划

## 安装

1. 克隆仓库到本地：

    ```bash
    cd {你的ros2工作空间目录}/src
    git clone <repo-url>
    
    ```

2. 构建项目：

    ```bash
    cd {你的ros2工作空间目录}
    colcon build
    source install/setup.bash
    ```

## 快速开始

### 启动 RViz 可视化urdf
```bash
ros2 launch gbt_description display_{机器人型号}.launch.py

```
比如：
```bash
ros2 launch gbt_description display_c5a.launch.py
```

### 启动 Gazebo 仿真

```bash
ros2 launch gbt_gazebo gazebo_{机器人型号}_demo.launch.py
```
比如：
```bash
ros2 launch gbt_gazebo gazebo_c5a_demo.launch.py
```

### 启动 MoveIt2 配置

```bash
ros2 launch {机器人型号}_moveit_config demo.launch.py
```
比如：
```bash
ros2 launch c5a_moveit_config demo.launch.py
```

### 启动 MoveIt2+Gazebo 仿真

**终端1**：启动gazebo仿真
```bash
ros2 launch {机器人型号}_moveit_config gazebo.launch.py
```
比如：
```bash
ros2 launch c5a_moveit_config gazebo.launch.py
```

**终端2**：启动moveit2 运动规划
```bash
ros2 launch {机器人型号}_moveit_config gazebo_moveit_rviz.launch.py
```
比如：
```bash
ros2 launch c5a_moveit_config gazebo_moveit_rviz.launch.py
```

## 后续开发计划

- [x] 添加机器人模型及其描述文件
    - [x] C5A 机器人
    - [ ] 添加更多机器人型号
- [ ] 添加更多仿真配置
    - [x] C5A 机器人
    - [ ] 添加更多机器人型号
- [ ] 添加更多 MoveIt2 配置
    - [x] C5A 机器人
    - [ ] 添加更多机器人型号
- [ ] 添加控制物理机器人模块

- [ ] 添加控制模拟器模块

  


## 联系方式

如有任何问题或建议，请通过项目的issue提交。

## 贡献

欢迎贡献代码、提出意见和建议！如贡献代码，请查看贡献指南。

## 许可证

本项目采用 **BSD 3-Clause  许可证**，使用本项目前请确保您了解并同意许可证条款。






