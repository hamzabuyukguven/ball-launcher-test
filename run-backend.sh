#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

: "${KAFKA_BOOTSTRAP_SERVERS:=localhost:9092}"
: "${SIMULATION_GRPC_HOST:=127.0.0.1}"
: "${SIMULATION_GRPC_PORT:=50052}"
: "${CONTROL_ENABLED:=true}"
: "${MAX_PAN_RATE:=0.20}"
: "${MAX_TILT_RATE:=0.10}"
: "${MUZZLE_VELOCITY:=100.0}"
export KAFKA_BOOTSTRAP_SERVERS SIMULATION_GRPC_HOST SIMULATION_GRPC_PORT
export CONTROL_ENABLED MAX_PAN_RATE MAX_TILT_RATE MUZZLE_VELOCITY

echo "Kafka:           ${KAFKA_BOOTSTRAP_SERVERS}"
echo "Simulation:      ${SIMULATION_GRPC_HOST}:${SIMULATION_GRPC_PORT}"
echo "Gun control:     ${CONTROL_ENABLED}"
echo "Max pan rate:    ${MAX_PAN_RATE} rad/s"
echo "Max tilt rate:   ${MAX_TILT_RATE} rad/s"
echo "Muzzle velocity: ${MUZZLE_VELOCITY} m/s"

command -v java >/dev/null || { echo "ERROR: Java was not found." >&2; exit 1; }
command -v mvn >/dev/null || { echo "ERROR: Maven was not found." >&2; exit 1; }

JAR="target/ball-launcher-backend-1.0.0.jar"
if [[ ! -f "$JAR" ]] || find src pom.xml -type f -newer "$JAR" -print -quit | grep -q .; then
  mvn -q -DskipTests clean package
fi
exec java -jar "$JAR"
