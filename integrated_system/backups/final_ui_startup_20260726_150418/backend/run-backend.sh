#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

: "${KAFKA_BOOTSTRAP_SERVERS:=localhost:9092}"
: "${SIMULATION_GRPC_HOST:=127.0.0.1}"
: "${SIMULATION_GRPC_PORT:=50052}"
: "${CONTROL_ENABLED:=true}"

export KAFKA_BOOTSTRAP_SERVERS SIMULATION_GRPC_HOST SIMULATION_GRPC_PORT CONTROL_ENABLED

echo "Kafka:      ${KAFKA_BOOTSTRAP_SERVERS}"
echo "Simulation: ${SIMULATION_GRPC_HOST}:${SIMULATION_GRPC_PORT}"
echo "Top control enabled: ${CONTROL_ENABLED}"

command -v java >/dev/null || { echo "HATA: Java bulunamadı." >&2; exit 1; }
command -v mvn >/dev/null || { echo "HATA: Maven bulunamadı." >&2; exit 1; }

mvn -q -DskipTests clean package
exec java -jar target/ball-launcher-backend-1.0.0.jar
