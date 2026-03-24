cmake_minimum_required(VERSION 3.8)
project(my_robot_control)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rclcpp REQUIRED)
find_package(moveit_ros_planning_interface REQUIRED)
find_package(geometry_msgs REQUIRED)
find_package(sensor_msgs REQUIRED)               # 必须添加
find_package(tf2_ros REQUIRED)
find_package(tf2_geometry_msgs REQUIRED)         # 必须添加
find_package(interface REQUIRED)
find_package(rclcpp_action REQUIRED)
find_package(control_msgs REQUIRED)
find_package(trajectory_msgs REQUIRED)
find_package(rclpy REQUIRED)
find_package(ament_cmake_python REQUIRED)  # <-- 新增

add_executable(cartesian_controller src/cartesian_controller.cpp)
ament_target_dependencies(cartesian_controller
  rclcpp
  geometry_msgs
  moveit_ros_planning_interface
  tf2_ros
)

add_executable(incremental_controller src/incremental_controller.cpp)
ament_target_dependencies(incremental_controller
  rclcpp
  interface
  sensor_msgs
  geometry_msgs
  tf2_ros
  tf2_geometry_msgs
)

install(TARGETS cartesian_controller incremental_controller 
  DESTINATION lib/${PROJECT_NAME}
)

install(DIRECTORY launch
  DESTINATION share/${PROJECT_NAME})

# 安装 Python 可执行脚本到 lib 目录
install(PROGRAMS
  scripts/play_trajectory.py
  scripts/record_trajectory.py
  DESTINATION lib/${PROJECT_NAME}
)

if(BUILD_TESTING)
  find_package(ament_lint_auto REQUIRED)
  set(ament_cmake_copyright_FOUND TRUE)
  set(ament_cmake_cpplint_FOUND TRUE)
  ament_lint_auto_find_test_dependencies()
endif()

ament_package()