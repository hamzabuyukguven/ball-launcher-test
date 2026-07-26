#!/usr/bin/env bash

LOG_DIR="$HOME/ball_launcher_ship_panel/logs"
LOG_FILE="$LOG_DIR/integrated-stop.log"
COMPOSE_FILE="$HOME/ball_launcher_integration_test/ball_launcher_integrated/backend/docker-compose.yml"

mkdir -p "$LOG_DIR"
exec >>"$LOG_FILE" 2>&1

echo
echo "=================================================="
echo "$(date '+%Y-%m-%d %H:%M:%S') - Stopping Ball Launcher"
echo "=================================================="

# Önce normal kapatma scriptlerini çalıştır.
"$HOME/stop_ship_control_panel.sh" 2>/dev/null || true
"$HOME/stop_ball_launcher_system.sh" 2>/dev/null || true

sleep 3

PATTERNS=(
  '[s]hip_control_panel.py'
  '[s]hip-control-app'
  '[p]hone_control.py'
  '[p]latform_motion_controller.py'
  '[a]uto_engagement_test_controller.py'
  '[p]arameter_bridge.*ship_cmd_vel_bridge.yaml'
  '[p]arameter_bridge.*target_cmd_vel_bridge.yaml'
  '[r]os2 launch.*heybeliada'
  '[s]tart_heybeliada_with_fire.sh'
  '[s]tart_heybeliada_phone.sh'
  '[g]z sim'
)

for pattern in "${PATTERNS[@]}"; do
    pkill -TERM -f "$pattern" 2>/dev/null || true
done

sleep 4

for pattern in "${PATTERNS[@]}"; do
    pkill -KILL -f "$pattern" 2>/dev/null || true
done

if [[ -f "$COMPOSE_FILE" ]]; then
    docker compose -f "$COMPOSE_FILE" down 2>/dev/null || true
fi

rm -f \
  "$HOME/ball_launcher_ship_panel/run/"*.pid \
  "$HOME/ball_launcher_integration_test/ball_launcher_integrated/.run/"*.pid \
  2>/dev/null || true

if command -v notify-send >/dev/null 2>&1; then
    notify-send "Ball Launcher" "The system has been stopped."
fi

echo "Ball Launcher, Ship Control Panel, Gazebo and Kafka were stopped."
