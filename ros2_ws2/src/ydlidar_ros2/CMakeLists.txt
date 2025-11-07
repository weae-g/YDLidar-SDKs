cmake_minimum_required(VERSION 3.8)
project(ydlidar_ros2)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(rclcpp REQUIRED)
find_package(sensor_msgs REQUIRED)

# Абсолютные пути к YDLidar SDK
include_directories(/home/weae/weae/YDLidar-SDKs/src)
link_directories(/home/weae/weae/YDLidar-SDKs/src)

add_executable(ydlidar_node src/ydlidar_node.cpp)
ament_target_dependencies(ydlidar_node rclcpp sensor_msgs)

# Линкуем SDK
target_link_libraries(ydlidar_node ydlidar_sdk)

install(TARGETS ydlidar_node DESTINATION lib/${PROJECT_NAME})

ament_package()
