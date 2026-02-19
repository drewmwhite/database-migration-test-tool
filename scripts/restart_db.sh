#!/usr/bin/env bash
# Restart (or start) the local SQL Server Docker container and wait until
# it is ready to accept connections.

set -euo pipefail

CONTAINER="sql_server_dev"
MAX_WAIT=60   # seconds before giving up on readiness check

# Load password from .env so we can probe the server with sqlcmd
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$SCRIPT_DIR/../.env"
if [[ -f "$ENV_FILE" ]]; then
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi
SA_PASSWORD="${MSSQL_SA_PASSWORD:-YourStrong!Passw0rd}"

# ── Container state ──────────────────────────────────────────────────────────

STATUS=$(docker inspect -f '{{.State.Status}}' "$CONTAINER" 2>/dev/null || echo "missing")

case "$STATUS" in
  running)
    echo "Container '$CONTAINER' is running — restarting..."
    docker restart "$CONTAINER"
    ;;
  exited|paused|created)
    echo "Container '$CONTAINER' is $STATUS — starting..."
    docker start "$CONTAINER"
    ;;
  missing)
    echo "Container '$CONTAINER' not found."
    echo "Create it first with: docker run (see docs/run-sql-server-on-docker.md)"
    exit 1
    ;;
  *)
    echo "Container '$CONTAINER' is in unexpected state '$STATUS' — attempting start..."
    docker start "$CONTAINER"
    ;;
esac

# ── Readiness check ──────────────────────────────────────────────────────────

echo "Waiting for SQL Server to be ready..."
ELAPSED=0
until docker exec "$CONTAINER" \
        /opt/mssql-tools18/bin/sqlcmd \
        -S localhost -U sa -P "$SA_PASSWORD" \
        -No -Q "SELECT 1" &>/dev/null; do
    if (( ELAPSED >= MAX_WAIT )); then
        echo "SQL Server did not become ready within ${MAX_WAIT}s."
        echo "Check logs with: docker logs $CONTAINER"
        exit 1
    fi
    sleep 2
    (( ELAPSED += 2 ))
done

echo "SQL Server is ready. (${ELAPSED}s)"
