#!/usr/bin/env bash
set -e

source /opt/ros/jazzy/setup.bash
source "$HOME/ball_launcher_ws/install/setup.bash"

exec ros2 launch \
  ball_launch_sim \
  heybeliada_backend.launch.py
