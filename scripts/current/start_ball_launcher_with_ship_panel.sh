#!/usr/bin/env bash
set -o pipefail

LOG_DIR="$HOME/ball_launcher_ship_panel/logs"
LOG_FILE="$LOG_DIR/integrated-start.log"
LOCK_DIR="$HOME/.cache/ball-launcher-ship-control-start.lockdir"

mkdir -p "$LOG_DIR" "$HOME/.cache"
exec >>"$LOG_FILE" 2>&1

echo
echo "=================================================="
echo "$(date '+%Y-%m-%d %H:%M:%S') - Starting Ball Launcher"
echo "=================================================="

notify_user() {
    if command -v notify-send >/dev/null 2>&1; then
        notify-send "Ball Launcher" "$1"
    fi
}

if ! mkdir "$LOCK_DIR" 2>/dev/null; then
    echo "Another startup operation is already running."
    notify_user "The system is already starting."
    exit 0
fi

cleanup_lock() {
    rmdir "$LOCK_DIR" 2>/dev/null || true
}
trap cleanup_lock EXIT INT TERM

export PATH="$HOME/.local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

for candidate in \
    "$HOME/.sdkman/candidates/maven/current/bin" \
    "/opt/maven/bin" \
    /opt/apache-maven-*/bin \
    "/usr/share/maven/bin"
do
    if [[ -d "$candidate" ]]; then
        export PATH="$candidate:$PATH"
    fi
done

if ! command -v mvn >/dev/null 2>&1; then
    MAVEN_EXECUTABLE="$(
        find "$HOME" /opt /usr/local \
            -maxdepth 5 \
            -type f \
            -name mvn \
            -perm -u+x \
            2>/dev/null \
        | head -n 1
    )"

    if [[ -n "$MAVEN_EXECUTABLE" ]]; then
        export PATH="$(dirname "$MAVEN_EXECUTABLE"):$PATH"
    fi
fi

MAIN_START="$HOME/start_ball_launcher_system.sh"
PANEL_START="$HOME/start_ship_control_panel.sh"
PANEL_APP="$HOME/open_ship_control_app.sh"

for required_file in "$MAIN_START" "$PANEL_START" "$PANEL_APP"; do
    if [[ ! -f "$required_file" ]]; then
        echo "ERROR: Required file was not found: $required_file"
        notify_user "Required file is missing: $(basename "$required_file")"
        exit 1
    fi
done

if pgrep -af '[p]hone_control.py' >/dev/null 2>&1; then
    echo "ERROR: The legacy phone-control process is running."
    notify_user "Stop the legacy Phone Control system first."
    exit 1
fi

if ss -ltn 2>/dev/null | grep -qE ':50052[[:space:]]'; then
    echo "The main simulation is already running."
else
    echo "Starting the main integrated system..."

    /usr/bin/bash "$MAIN_START"
    main_result=$?

    if (( main_result != 0 )); then
        echo "ERROR: Main system start failed with code: $main_result"
        notify_user "Main Ball Launcher system failed to start."
        exit "$main_result"
    fi
fi

echo "Waiting for simulation gRPC port 50052..."

grpc_ready=false

for _ in {1..120}; do
    if ss -ltn 2>/dev/null | grep -qE ':50052[[:space:]]'; then
        grpc_ready=true
        break
    fi
    sleep 0.5
done

if [[ "$grpc_ready" != true ]]; then
    echo "ERROR: Simulation gRPC port 50052 did not become ready."
    notify_user "Simulation gRPC failed to become ready."
    exit 1
fi

echo "Simulation gRPC is ready."

if curl -fsS "http://127.0.0.1:8090/health" >/dev/null 2>&1; then
    echo "Ship Control Panel is already running."
else
    echo "Starting Ship Control Panel..."

    /usr/bin/bash "$PANEL_START"
    panel_result=$?

    if (( panel_result != 0 )); then
        echo "ERROR: Ship Control Panel failed with code: $panel_result"
        notify_user "Ship Control Panel failed to start."
        exit "$panel_result"
    fi
fi

panel_ready=false

for _ in {1..60}; do
    if curl -fsS "http://127.0.0.1:8090/health" >/dev/null 2>&1; then
        panel_ready=true
        break
    fi
    sleep 0.5
done

if [[ "$panel_ready" != true ]]; then
    echo "ERROR: Ship Control Panel is unavailable on port 8090."
    notify_user "Ship Control Panel failed to become ready."
    exit 1
fi

echo "Opening Ship Control Panel application..."

nohup /usr/bin/bash "$PANEL_APP" \
    >>"$LOG_FILE" 2>&1 &

notify_user "Ball Launcher system started."
echo "Startup completed successfully."
exit 0
