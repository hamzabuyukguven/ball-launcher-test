#!/usr/bin/env bash
set -eo pipefail

PANEL_DIR="$HOME/ball_launcher_ship_panel"
RUN_DIR="$PANEL_DIR/run"
LOG_DIR="$PANEL_DIR/logs"
SHIP_CONFIG="$HOME/ship_cmd_vel_bridge.yaml"
TARGET_CONFIG="$HOME/phone_test/target_cmd_vel_bridge.yaml"

mkdir -p "$RUN_DIR" "$LOG_DIR"

set +u
source /opt/ros/jazzy/setup.bash
source "$HOME/ball_launcher_ws/install/setup.bash"
set -u

for file in \
    "$SHIP_CONFIG" \
    "$TARGET_CONFIG" \
    "$PANEL_DIR/ship_control_panel.py"
do
    if [[ ! -f "$file" ]]; then
        echo "ERROR: Required file was not found: $file"
        exit 1
    fi
done

if pgrep -af '[p]hone_control.py' >/dev/null; then
    echo "ERROR: The legacy phone-control process is running."
    echo "Stop the old phone-control system first."
    exit 1
fi

if curl -fsS "http://127.0.0.1:8090/health" >/dev/null 2>&1; then
    echo "Ship Control Panel is already running."
    exit 0
fi

start_bridge() {
    local name="$1"
    local config="$2"
    local pattern="$3"
    local pid_file="$RUN_DIR/${name}.pid"
    local log_file="$LOG_DIR/${name}.log"
    local pid
    local ready=false

    if pgrep -af "$pattern" >/dev/null; then
        echo "$name is already running; using the existing process."
        rm -f "$pid_file"
        return 0
    fi

    echo "Starting $name..."

    nohup ros2 run ros_gz_bridge parameter_bridge \
        --ros-args \
        -p config_file:="$config" \
        > "$log_file" 2>&1 &

    pid=$!
    echo "$pid" > "$pid_file"

    for _ in {1..40}; do
        if pgrep -af "$pattern" >/dev/null; then
            ready=true
            break
        fi

        if ! kill -0 "$pid" 2>/dev/null; then
            break
        fi

        sleep 0.25
    done

    if [[ "$ready" != true ]]; then
        echo "ERROR: $name failed to stay running."
        tail -n 100 "$log_file" 2>/dev/null || true
        return 1
    fi

    echo "$name is ready."
}

start_bridge \
    "ship_cmd_vel_bridge" \
    "$SHIP_CONFIG" \
    '[p]arameter_bridge.*ship_cmd_vel_bridge.yaml'

start_bridge \
    "target_cmd_vel_bridge" \
    "$TARGET_CONFIG" \
    '[p]arameter_bridge.*target_cmd_vel_bridge.yaml'

echo "Starting Ship Control Panel..."

nohup env \
    SHIP_PANEL_HOST="${SHIP_PANEL_HOST:-0.0.0.0}" \
    SHIP_PANEL_PORT="${SHIP_PANEL_PORT:-8090}" \
    SHIP_FORWARD_SIGN="${SHIP_FORWARD_SIGN:-1.0}" \
    SHIP_YAW_SIGN="${SHIP_YAW_SIGN:-1.0}" \
    TARGET_FORWARD_SIGN="${TARGET_FORWARD_SIGN:-1.0}" \
    TARGET_YAW_SIGN="${TARGET_YAW_SIGN:-1.0}" \
    python3 -u "$PANEL_DIR/ship_control_panel.py" \
    > "$LOG_DIR/ship_control_panel.log" 2>&1 &

PANEL_PID=$!
echo "$PANEL_PID" > "$RUN_DIR/ship_control_panel.pid"

panel_ready=false

for _ in {1..40}; do
    if curl -fsS "http://127.0.0.1:8090/health" >/dev/null 2>&1; then
        panel_ready=true
        break
    fi

    if ! kill -0 "$PANEL_PID" 2>/dev/null; then
        break
    fi

    sleep 0.25
done

if [[ "$panel_ready" != true ]]; then
    echo "ERROR: Ship Control Panel failed to start."
    tail -n 120 "$LOG_DIR/ship_control_panel.log" 2>/dev/null || true
    exit 1
fi

IP_ADDRESS="$(hostname -I | awk '{print $1}')"

echo
echo "Ship Control Panel is ready."
echo "Computer: http://127.0.0.1:8090"
echo "Same network: http://${IP_ADDRESS}:8090"
