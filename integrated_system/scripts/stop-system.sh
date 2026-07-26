#!/usr/bin/env bash
set -Eeuo pipefail
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_DIR="${ROOT_DIR}/.run"
KEEP_SIMULATION=false
KEEP_KAFKA=false
for arg in "$@"; do
  case "$arg" in
    --keep-simulation) KEEP_SIMULATION=true ;;
    --keep-kafka) KEEP_KAFKA=true ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

stop_group() {
  local name=$1
  local file="${RUN_DIR}/${name}.pid"
  [[ -s "$file" ]] || return 0
  local pid
  pid=$(cat "$file")
  if kill -0 "$pid" 2>/dev/null; then
    kill -TERM -- "-$pid" 2>/dev/null || kill -TERM "$pid" 2>/dev/null || true
    for _ in $(seq 1 20); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.25
    done
    kill -KILL -- "-$pid" 2>/dev/null || true
    echo "$name stopped."
  fi
  rm -f "$file"
}

stop_group frontend
stop_group backend
stop_group phone-control
stop_group platform-controller
$KEEP_SIMULATION || stop_group simulation

if ! $KEEP_KAFKA; then
  docker compose -f "${ROOT_DIR}/backend/docker-compose.yml" down >/dev/null 2>&1 || true
  echo "Kafka and Zookeeper stopped."
fi
