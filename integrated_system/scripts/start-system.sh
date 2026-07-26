#!/usr/bin/env bash
set -Eeuo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_FILE="${ROOT_DIR}/system.env"
RUN_DIR="${ROOT_DIR}/.run"
LOG_DIR="${ROOT_DIR}/logs"
mkdir -p "$RUN_DIR" "$LOG_DIR"

[[ -f "$ENV_FILE" ]] && source "$ENV_FILE"

: "${KAFKA_BOOTSTRAP_SERVERS:=127.0.0.1:9092}"
: "${KAFKA_ADVERTISED_HOST:=127.0.0.1}"
: "${SIMULATION_GRPC_HOST:=127.0.0.1}"
: "${SIMULATION_GRPC_PORT:=50052}"
: "${CONTROL_ENABLED:=true}"
: "${MAX_PAN_RATE:=0.20}"
: "${MAX_TILT_RATE:=0.10}"
: "${MUZZLE_VELOCITY:=100.0}"
: "${SIMULATION_START_COMMAND:=}"

START_PHONE=false
PHONE_GUN_CONTROL=false
for arg in "$@"; do
  case "$arg" in
    --with-phone) START_PHONE=true ;;
    --phone-gun-control) START_PHONE=true; PHONE_GUN_CONTROL=true ;;
    *) echo "Unknown option: $arg" >&2; exit 2 ;;
  esac
done

if $PHONE_GUN_CONTROL; then
  CONTROL_ENABLED=false
fi

log() { printf '[%s] %s\n' "$(date '+%H:%M:%S')" "$*"; }
port_open() { timeout 1 bash -c "</dev/tcp/$1/$2" >/dev/null 2>&1; }

pid_running() {
  local file=$1
  [[ -s "$file" ]] || return 1
  local pid
  pid=$(cat "$file")
  kill -0 "$pid" 2>/dev/null
}

launch_group() {
  local name=$1
  local command=$2
  local pid_file="${RUN_DIR}/${name}.pid"
  local log_file="${LOG_DIR}/${name}.log"

  if pid_running "$pid_file"; then
    log "$name is already running (PID $(cat "$pid_file"))."
    return 0
  fi

  rm -f "$pid_file"
  setsid bash -lc "${command}" >"$log_file" 2>&1 < /dev/null &
  local pid=$!
  echo "$pid" > "$pid_file"
  sleep 0.5

  if ! kill -0 "$pid" 2>/dev/null; then
    log "$name failed to start. See $log_file"
    tail -n 30 "$log_file" || true
    return 1
  fi
  log "$name started (PID $pid). Log: $log_file"
}

resolve_simulation_command() {
  if [[ -n "$SIMULATION_START_COMMAND" ]]; then
    printf '%s' "$SIMULATION_START_COMMAND"
    return 0
  fi

  local candidate
  for candidate in \
    "$HOME/start_heybeliada_with_fire.sh" \
    "$HOME/start_heybeliada_sydney.sh" \
    "$HOME/start_heybeliada.sh"; do
    if [[ -f "$candidate" ]]; then
      printf 'bash %q' "$candidate"
      return 0
    fi
  done
  return 1
}

command -v docker >/dev/null 2>&1 || {
  echo "Docker is not installed." >&2
  exit 1
}
command -v java >/dev/null 2>&1 || { echo "Java is not installed." >&2; exit 1; }
command -v mvn >/dev/null 2>&1 || { echo "Maven is not installed." >&2; exit 1; }

if ! docker info >/dev/null 2>&1; then
  log "Starting Docker..."
  sudo systemctl start docker
  sleep 2
fi

export KAFKA_ADVERTISED_HOST
log "Starting Kafka and Zookeeper..."
docker compose -f "${ROOT_DIR}/backend/docker-compose.yml" up -d

for _ in $(seq 1 60); do
  port_open 127.0.0.1 9092 && break
  sleep 1
done
port_open 127.0.0.1 9092 || { echo "Kafka did not become ready on port 9092." >&2; exit 1; }

"${ROOT_DIR}/scripts/create-kafka-topics.sh" >/dev/null
log "Kafka is ready."

if ! port_open "$SIMULATION_GRPC_HOST" "$SIMULATION_GRPC_PORT"; then
  SIM_CMD=$(resolve_simulation_command) || {
    echo "No simulation start script was found." >&2
    echo "Set SIMULATION_START_COMMAND in ${ENV_FILE}." >&2
    exit 1
  }
  launch_group simulation "source /opt/ros/jazzy/setup.bash; source \"$HOME/ball_launcher_ws/install/setup.bash\"; ${SIM_CMD}"
  log "Waiting for simulation gRPC on ${SIMULATION_GRPC_HOST}:${SIMULATION_GRPC_PORT}..."
  for _ in $(seq 1 120); do
    port_open "$SIMULATION_GRPC_HOST" "$SIMULATION_GRPC_PORT" && break
    sleep 1
  done
fi
port_open "$SIMULATION_GRPC_HOST" "$SIMULATION_GRPC_PORT" || {
  echo "Simulation gRPC did not become ready on ${SIMULATION_GRPC_HOST}:${SIMULATION_GRPC_PORT}." >&2
  exit 1
}
log "Simulation gRPC is ready."

BACKEND_CMD=$(printf 'cd %q; export KAFKA_BOOTSTRAP_SERVERS=%q SIMULATION_GRPC_HOST=%q SIMULATION_GRPC_PORT=%q CONTROL_ENABLED=%q MAX_PAN_RATE=%q MAX_TILT_RATE=%q MUZZLE_VELOCITY=%q; exec ./run-backend.sh' \
  "${ROOT_DIR}/backend" "$KAFKA_BOOTSTRAP_SERVERS" "$SIMULATION_GRPC_HOST" "$SIMULATION_GRPC_PORT" "$CONTROL_ENABLED" "$MAX_PAN_RATE" "$MAX_TILT_RATE" "$MUZZLE_VELOCITY")
launch_group backend "$BACKEND_CMD"

sleep 2
FRONTEND_CMD=$(printf 'cd %q; export KAFKA_BOOTSTRAP_SERVERS=%q; exec ./run-frontend.sh' \
  "${ROOT_DIR}/frontend" "$KAFKA_BOOTSTRAP_SERVERS")
launch_group frontend "$FRONTEND_CMD"

if $START_PHONE; then
  "${ROOT_DIR}/scripts/start-phone-control.sh"
fi

cat <<SUMMARY

Ball Launcher system started.
  Kafka:      ${KAFKA_BOOTSTRAP_SERVERS}
  Simulation: ${SIMULATION_GRPC_HOST}:${SIMULATION_GRPC_PORT}
  Gun control enabled: ${CONTROL_ENABLED}
  Muzzle velocity: ${MUZZLE_VELOCITY} m/s

Logs:
  ${LOG_DIR}/simulation.log
  ${LOG_DIR}/backend.log
  ${LOG_DIR}/frontend.log

Stop command:
  ${ROOT_DIR}/scripts/stop-system.sh
SUMMARY
