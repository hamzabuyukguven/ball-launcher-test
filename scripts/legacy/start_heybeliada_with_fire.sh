#!/usr/bin/env bash

source /opt/ros/jazzy/setup.bash
source ~/ball_launcher_ws/install/setup.bash

export ROS_DOMAIN_ID=0
export ROS_AUTOMATIC_DISCOVERY_RANGE=SUBNET

pkill -f '/home/fatih/phone_test/manual_fire_bridge.py' \
    2>/dev/null || true

nohup python3 -u \
    /home/fatih/phone_test/manual_fire_bridge.py \
    > /home/fatih/manual_fire_bridge.log 2>&1 &

sleep 1

exec /home/fatih/start_heybeliada_sydney.sh
