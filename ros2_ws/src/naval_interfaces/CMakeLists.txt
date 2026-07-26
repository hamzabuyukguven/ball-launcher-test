cmake_minimum_required(VERSION 3.8)
project(naval_interfaces)

if(CMAKE_COMPILER_IS_GNUCXX OR CMAKE_CXX_COMPILER_ID MATCHES "Clang")
  add_compile_options(-Wall -Wextra -Wpedantic)
endif()

find_package(ament_cmake REQUIRED)
find_package(rosidl_default_generators REQUIRED)
find_package(builtin_interfaces REQUIRED)

rosidl_generate_interfaces(${PROJECT_NAME}
  "msg/GunRateCommand.msg"
  "msg/FireCommand.msg"
  "msg/GunInfo.msg"
  "msg/GunStatusInfo.msg"
  "msg/PlatformPositionInfo.msg"
  "msg/PlatformVelocityInfo.msg"
  "msg/StabilizationData.msg"
  "msg/PlatformStatusInfo.msg"
  "msg/TargetPositionInfo.msg"
  "msg/Heartbeat.msg"
  DEPENDENCIES
  builtin_interfaces
)

ament_export_dependencies(rosidl_default_runtime)
ament_package()
