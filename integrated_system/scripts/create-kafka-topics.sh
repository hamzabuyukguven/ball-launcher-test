#!/usr/bin/env bash
set -euo pipefail

CONTAINER=${KAFKA_CONTAINER_NAME:-ball-launcher-kafka}
TOPICS=(launcher.commands launcher.status launcher.telemetry launcher.reports)

command -v docker >/dev/null || { echo "HATA: Docker bulunamadı." >&2; exit 1; }

docker inspect "$CONTAINER" >/dev/null 2>&1 || {
  echo "HATA: $CONTAINER container'ı çalışmıyor." >&2
  exit 1
}

for topic in "${TOPICS[@]}"; do
  docker exec "$CONTAINER" kafka-topics \
    --bootstrap-server 127.0.0.1:9092 \
    --create --if-not-exists \
    --topic "$topic" \
    --partitions 1 \
    --replication-factor 1
done

docker exec "$CONTAINER" kafka-topics \
  --bootstrap-server 127.0.0.1:9092 \
  --list
