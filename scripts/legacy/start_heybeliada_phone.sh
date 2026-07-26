#!/usr/bin/env bash
set -eo pipefail

source /opt/ros/jazzy/setup.bash
source "$HOME/ball_launcher_ws/install/setup.bash"

BRIDGE_CONFIG="$HOME/ship_cmd_vel_bridge.yaml"
PHONE_DIR="$HOME/phone_test"
TARGET_BRIDGE_CONFIG="$PHONE_DIR/target_cmd_vel_bridge.yaml"
BRIDGE_LOG="/tmp/ship_cmd_vel_bridge.log"
TARGET_BRIDGE_LOG="/tmp/target_cmd_vel_bridge.log"
AUTO_LOG="/tmp/auto_engagement_test_controller.log"

BRIDGE_PID=""
TARGET_BRIDGE_PID=""
AUTO_PID=""

cleanup() {
    if [[ -n "${AUTO_PID}" ]] && kill -0 "${AUTO_PID}" 2>/dev/null; then
        echo
        echo "AUTO AIM test controller kapatılıyor..."
        kill -INT "${AUTO_PID}" 2>/dev/null || true
        wait "${AUTO_PID}" 2>/dev/null || true
    fi

    if [[ -n "${TARGET_BRIDGE_PID}" ]] && kill -0 "${TARGET_BRIDGE_PID}" 2>/dev/null; then
        echo "Target hareket bridge'i kapatılıyor..."
        kill -INT "${TARGET_BRIDGE_PID}" 2>/dev/null || true
        wait "${TARGET_BRIDGE_PID}" 2>/dev/null || true
    fi

    if [[ -n "${BRIDGE_PID}" ]] && kill -0 "${BRIDGE_PID}" 2>/dev/null; then
        echo "Gemi hareket bridge'i kapatılıyor..."
        kill -INT "${BRIDGE_PID}" 2>/dev/null || true
        wait "${BRIDGE_PID}" 2>/dev/null || true
    fi
}

trap cleanup EXIT INT TERM HUP

for required_file in \
    "$BRIDGE_CONFIG" \
    "$TARGET_BRIDGE_CONFIG" \
    "$PHONE_DIR/phone_control.py" \
    "$PHONE_DIR/auto_engagement_test_controller.py"
do
    if [[ ! -f "$required_file" ]]; then
        echo "HATA: Dosya bulunamadı:"
        echo "  $required_file"
        exit 1
    fi
done

if pgrep -af '[p]arameter_bridge.*ship_cmd_vel_bridge.yaml' >/dev/null; then
    echo "Gemi hareket bridge'i zaten çalışıyor."
else
    echo "Gemi hareket bridge'i başlatılıyor..."
    ros2 run ros_gz_bridge parameter_bridge \
        --ros-args \
        -p config_file:="$BRIDGE_CONFIG" \
        > "$BRIDGE_LOG" 2>&1 &
    BRIDGE_PID=$!
    sleep 2

    if ! kill -0 "$BRIDGE_PID" 2>/dev/null; then
        echo "HATA: Gemi hareket bridge'i başlayamadı."
        cat "$BRIDGE_LOG"
        exit 1
    fi
fi

if pgrep -af '[p]arameter_bridge.*target_cmd_vel_bridge.yaml' >/dev/null; then
    echo "Target hareket bridge'i zaten çalışıyor."
else
    echo "Target hareket bridge'i başlatılıyor..."
    ros2 run ros_gz_bridge parameter_bridge \
        --ros-args \
        -p config_file:="$TARGET_BRIDGE_CONFIG" \
        > "$TARGET_BRIDGE_LOG" 2>&1 &
    TARGET_BRIDGE_PID=$!
    sleep 2

    if ! kill -0 "$TARGET_BRIDGE_PID" 2>/dev/null; then
        echo "HATA: Target hareket bridge'i başlayamadı."
        cat "$TARGET_BRIDGE_LOG"
        exit 1
    fi
fi

if pgrep -af '[a]uto_engagement_test_controller.py' >/dev/null; then
    echo "AUTO AIM test controller zaten çalışıyor."
else
    echo "AUTO AIM test controller IDLE modda başlatılıyor..."
    python3 -u \
        "$PHONE_DIR/auto_engagement_test_controller.py" \
        > "$AUTO_LOG" 2>&1 &
    AUTO_PID=$!
    sleep 2

    if ! kill -0 "$AUTO_PID" 2>/dev/null; then
        echo "HATA: AUTO AIM test controller başlayamadı."
        cat "$AUTO_LOG"
        exit 1
    fi
fi

echo
echo "Telefon arayüzü başlatılıyor."
echo "İki joystick aynı hız, dönüş, dead-zone, 20 Hz yayın ve timeout dinamiklerini kullanır."
echo "Target hareketi yalnızca /test/target_cmd_vel topic'ini kullanır."
echo "Ana backend/gRPC sistemi değiştirilmedi."
echo "AUTO AIM yalnızca butona basılınca komut yayınlar."
echo

cd "$PHONE_DIR"
python3 -u phone_control.py
