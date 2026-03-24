# gbt_gazebo 配置包

## 简介
该包是用于在 Gazebo 中配置和仿真机器人环境的 Gazebo 配置包，提供了必要的配置文件和启动文件，以便在 Gazebo 中加载和控制机器人。

## 目录结构

```plaintext
├── CMakeLists.txt
├── config
├── launch
└── package.xml
```

- **CMakeLists.txt**：构建系统配置文件。
- **config**：包含 Gazebo 仿真所需的配置文件（如 Gazebo 世界文件、控制参数等）。
- **launch**：包含启动文件，用于快速启动 Gazebo 仿真环境。
- **package.xml**：ROS2 包的元数据文件，描述了包的依赖项和其他信息。

## 依赖项

- ROS2 Humble
- Gazebo
- 与机器人相关的描述文件包（如 `gbt_description`）

## 快速开始

1. 将 `gbt_gazebo` 文件夹复制到 ROS 工作空间的 `src` 目录下。
2. 进入工作空间并进行编译：

   ```bash
   cd {你的ROS2工作空间}
   colcon build
   source install/setup.bash
   ```

### 启动 Gazebo 仿真

```bash
ros2 launch gbt_gazebo gazebo_{机器人型号}_demo.launch.py
```
比如：
```bash
ros2 launch gbt_gazebo gazebo_c5a_demo.launch.py
```

## 使用示例
![](../assets/gazebo.png)

## 配置与自定义

可以通过修改 `config` 目录中的文件来自定义 Gazebo 仿真环境，包括调整物理参数、添加或删除对象等。

## 许可证
此项目采用 [BSD-3-clause 许可证](https://opensource.org/license/BSD-3-clause)。