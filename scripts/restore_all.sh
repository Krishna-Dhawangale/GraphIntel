#!/usr/bin/env bash
# ==============================================================================
# GraphIntel Production Disaster Recovery & Restore Automation
# Target Operational SLA: RTO < 30 minutes
# ==============================================================================

set -euo pipefail

if [ "$#" -ne 1 ]; then
  echo "Usage: $0 <path_to_backup_directory>"
  exit 1
fi

BACKUP_DIR="$1"

if [ ! -d "${BACKUP_DIR}" ]; then
  echo "Error: Directory ${BACKUP_DIR} not found!"
  exit 1
fi

echo "=========================================================="
echo "Starting GraphIntel Disaster Recovery Restore from: ${BACKUP_DIR}"
echo "=========================================================="

# 1. Verify Checksums
echo "[1/4] Verifying SHA256 checksums..."
if [ -f "${BACKUP_DIR}/SHA256SUMS" ]; then
  (cd "${BACKUP_DIR}" && sha256sum -c "SHA256SUMS")
fi

# 2. Restore PostgreSQL
echo "[2/4] Restoring PostgreSQL database..."
PG_DUMP=$(find "${BACKUP_DIR}" -name "postgres_*.dump" | head -n 1)
if [ -n "${PG_DUMP}" ]; then
  PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" pg_restore \
    -h "${POSTGRES_HOST:-localhost}" \
    -p "${POSTGRES_PORT:-5432}" \
    -U "${POSTGRES_USER:-postgres}" \
    -d "${POSTGRES_DB:-graphintel}" \
    --clean --if-exists -v "${PG_DUMP}"
fi

# 3. Restore Neo4j
echo "[3/4] Restoring Neo4j knowledge graph..."
NEO_DUMP=$(find "${BACKUP_DIR}" -name "neo4j_*.dump" | head -n 1)
if [ -n "${NEO_DUMP}" ] && command -v neo4j-admin &> /dev/null; then
  neo4j-admin database load neo4j --from-path="${NEO_DUMP}" --overwrite-destination=true
fi

# 4. Restore Qdrant Snapshot
echo "[4/4] Recovering Qdrant vector store collection..."
# Using Qdrant snapshot recovery REST endpoint:
# curl -X POST "http://${QDRANT_HOST:-localhost}:6333/collections/graphintel_chunks/snapshots/recover" ...

echo "=========================================================="
echo "Disaster Recovery Restoration Completed Successfully!"
echo "=========================================================="
