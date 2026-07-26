#!/usr/bin/env bash
set -euo pipefail

if [[ $# -ne 2 ]]; then
  echo "Kullanım: $0 <kafka-broker-ip> <simulation-ip>" >&2
  exit 2
fi

KAFKA_HOST=$1
SIM_HOST=$2

check_port() {
  local name=$1 host=$2 port=$3
  if timeout 3 bash -c "</dev/tcp/${host}/${port}" 2>/dev/null; then
    echo "OK   ${name}: ${host}:${port} erişilebilir"
  else
    echo "HATA ${name}: ${host}:${port} erişilemiyor"
    return 1
  fi
}

result=0
check_port "Kafka" "$KAFKA_HOST" 9092 || result=1
check_port "Simulation gRPC" "$SIM_HOST" 50052 || result=1
exit "$result"
