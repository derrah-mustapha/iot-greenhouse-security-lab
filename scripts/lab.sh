#!/bin/bash
# scripts/lab.sh up baseline|hardened | down | status | logs <service>
set -euo pipefail
cd "$(dirname "$0")/.."
case "${1:-}" in
  up)
    export PROFILE=${2:?baseline|hardened}
    scripts/gen_certs.sh >/dev/null
    docker compose down --remove-orphans >/dev/null 2>&1 || true
    rm -f data/readings.db*
    docker compose up -d broker
    sleep 3
    docker compose up -d ingestor node1 node2 node3 admin attacker
    echo "profile=$PROFILE; collecting data..."
    sleep 12
    "$0" status
    ;;
  down) docker compose down --remove-orphans ;;
  status)
    docker compose ps --format 'table {{.Name}}\t{{.Status}}'
    echo "readings per node (total / flagged as anomaly):"
    docker compose exec -T ingestor python /app/q.py "select node,count(*),sum(anomaly),max(fw) from readings group by node" || true
    ;;
  logs) docker compose logs "${2:?service}" ;;
  *) sed -n '2p' "$0"; exit 1;;
esac
