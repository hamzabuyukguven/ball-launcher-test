#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/system.env"
RUN_DIR="${ROOT_DIR}/.run"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"
[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

find_script() {
  local name=$1
  find "$HOME" -type f -name "$name" \
    -not -path '*/.cache/*' \
    -not -path '*/.local/share/Trash/*' \
    -not -path '*/safe_backup*/*' \
    -not -path '*/backup*/*' \
    2>/dev/null | head -n 1
}

launch_group() {
  local name=$1 command=$2
  local pid_file="${RUN_DIR}/${name}.pid"
  local log_file="${LOG_DIR}/${name}.log"
  if [[ -s "$pid_file" ]] && kill -0 "$(cat "$pid_file")" 2>/dev/null; then
    echo "$name is already running."
    return 0
  fi
  setsid bash -lc "${command}" >"$log_file" 2>&1 < /dev/null &
  echo $! > "$pid_file"
  echo "$name started. Log: $log_file"
}

PLATFORM_CMD=${PLATFORM_CONTROLLER_COMMAND:-}
PHONE_CMD=${PHONE_CONTROL_COMMAND:-}

if [[ -z "$PLATFORM_CMD" ]]; then
  PLATFORM_FILE=$(find_script platform_motion_controller.py || true)
  [[ -n "$PLATFORM_FILE" ]] && PLATFORM_CMD=$(printf 'python3 %q' "$PLATFORM_FILE")
fi
if [[ -z "$PHONE_CMD" ]]; then
  PHONE_FILE=$(find_script phone_control.py || true)
  [[ -n "$PHONE_FILE" ]] && PHONE_CMD=$(printf 'python3 %q' "$PHONE_FILE")
fi

ROS_PREFIX="source /opt/ros/jazzy/setup.bash; source \"$HOME/ball_launcher_ws/install/setup.bash\";"

if [[ -n "$PLATFORM_CMD" ]]; then
  launch_group platform-controller "$ROS_PREFIX $PLATFORM_CMD"
else
  echo "platform_motion_controller.py was not found; skipping platform controller."
fi

if [[ -n "$PHONE_CMD" ]]; then
  launch_group phone-control "$ROS_PREFIX $PHONE_CMD"
else
  echo "phone_control.py was not found. Set PHONE_CONTROL_COMMAND in $ENV_FILE."
  exit 1
fi
