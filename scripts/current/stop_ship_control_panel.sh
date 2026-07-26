#!/usr/bin/env bash
set +u

PANEL_DIR="$HOME/ball_launcher_ship_panel"
RUN_DIR="$PANEL_DIR/run"

source /opt/ros/jazzy/setup.bash 2>/dev/null || true
source "$HOME/ball_launcher_ws/install/setup.bash" 2>/dev/null || true

set -u

ros2 topic pub --once \
    /backend/platform_cmd_vel \
    geometry_msgs/msg/Twist \
    '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' \
    >/dev/null 2>&1 || true

ros2 topic pub --once \
    /test/target_cmd_vel \
    geometry_msgs/msg/Twist \
    '{linear: {x: 0.0, y: 0.0, z: 0.0}, angular: {x: 0.0, y: 0.0, z: 0.0}}' \
    >/dev/null 2>&1 || true

stop_pid_file() {
    local pid_file="$1"

    if [[ ! -f "$pid_file" ]]; then
        return
    fi

    local pid
    pid="$(cat "$pid_file" 2>/dev/null || true)"
    rm -f "$pid_file"

    if [[ -n "$pid" ]] && kill -0 "$pid" 2>/dev/null; then
        kill -TERM "-$pid" 2>/dev/null \
            || kill -TERM "$pid" 2>/dev/null \
            || true

        for _ in {1..20}; do
            if ! kill -0 "$pid" 2>/dev/null; then
                break
            fi
            sleep 0.2
        done

        if kill -0 "$pid" 2>/dev/null; then
            kill -KILL "-$pid" 2>/dev/null \
                || kill -KILL "$pid" 2>/dev/null \
                || true
        fi
    fi
}

stop_pid_file "$RUN_DIR/ship_control_panel.pid"
stop_pid_file "$RUN_DIR/target_cmd_vel_bridge.pid"
stop_pid_file "$RUN_DIR/ship_cmd_vel_bridge.pid"

echo "Ship Control Panel and its bridge processes were stopped."
