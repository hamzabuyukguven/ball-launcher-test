cmake_minimum_required(VERSION 3.8)

project(projectile_launch_plugin LANGUAGES CXX)

find_package(ament_cmake REQUIRED)
find_package(gz-sim8 REQUIRED)
find_package(gz-plugin2 REQUIRED COMPONENTS register)

add_library(
  projectile_launch_system
  SHARED
  src/projectile_launch_system.cpp
)

set_property(
  TARGET projectile_launch_system
  PROPERTY CXX_STANDARD 17
)

target_compile_options(
  projectile_launch_system
  PRIVATE
  -Wall
  -Wextra
  -Wpedantic
)

target_link_libraries(
  projectile_launch_system
  PRIVATE
  gz-sim8::gz-sim8
  gz-plugin2::gz-plugin2
)

install(
  TARGETS projectile_launch_system
  LIBRARY DESTINATION lib
)

ament_package()
