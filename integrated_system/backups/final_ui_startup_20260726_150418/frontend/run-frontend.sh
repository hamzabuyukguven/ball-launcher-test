#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "${BASH_SOURCE[0]}")"

: "${KAFKA_BOOTSTRAP_SERVERS:=localhost:9092}"
export KAFKA_BOOTSTRAP_SERVERS

echo "Kafka: ${KAFKA_BOOTSTRAP_SERVERS}"

command -v java >/dev/null || { echo "HATA: Java bulunamadı." >&2; exit 1; }
command -v mvn >/dev/null || { echo "HATA: Maven bulunamadı." >&2; exit 1; }

exec mvn -q clean javafx:run
