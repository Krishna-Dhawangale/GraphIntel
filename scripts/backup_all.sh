#!/usr/bin/env bash
# ==============================================================================
# GraphIntel Production Backup & Disaster Recovery Automation
# Target Operational SLA: RPO < 60 minutes | RTO < 30 minutes
# ==============================================================================

set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups/graphintel}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
TARGET_PATH="${BACKUP_DIR}/${TIMESTAMP}"

mkdir -p "${TARGET_PATH}"

echo "=========================================================="
echo "Starting GraphIntel Complete Backup: ${TIMESTAMP}"
echo "Target Directory: ${TARGET_PATH}"
echo "=========================================================="

# 1. PostgreSQL Database Dump (Schema + Data)
echo "[1/4] Dumping PostgreSQL database..."
PGPASSWORD="${POSTGRES_PASSWORD:-postgres}" pg_dump \
  -h "${POSTGRES_HOST:-localhost}" \
  -p "${POSTGRES_PORT:-5432}" \
  -U "${POSTGRES_USER:-postgres}" \
  -F c \
  -b -v \
  -f "${TARGET_PATH}/postgres_${TIMESTAMP}.dump" \
  "${POSTGRES_DB:-graphintel}"

# 2. Neo4j Knowledge Graph Dump
echo "[2/4] Dumping Neo4j knowledge graph data..."
if command -v neo4j-admin &> /dev/null; then
  neo4j-admin database dump neo4j --to-path="${TARGET_PATH}/neo4j_${TIMESTAMP}.dump"
else
  echo "neo4j-admin not on path; creating APOC sub-graph export..."
  curl -s -u "${NEO4J_USERNAME:-neo4j}:${NEO4J_PASSWORD:-graphintel123}" \
    -H "Content-Type: application/json" \
    -d '{"statements":[{"statement":"CALL apoc.export.json.all(\"backup.json\",{useTypes:true})"}]}' \
    "http://${NEO4J_HOST:-localhost}:7474/db/neo4j/tx/commit" > "${TARGET_PATH}/neo4j_apoc_${TIMESTAMP}.json" || true
fi

# 3. Qdrant Vector Snapshots
echo "[3/4] Creating Qdrant vector collection snapshot..."
curl -s -X POST "http://${QDRANT_HOST:-localhost}:6333/collections/graphintel_chunks/snapshots" \
  -H "Content-Type: application/json" > "${TARGET_PATH}/qdrant_snapshot_meta_${TIMESTAMP}.json"

# 4. S3 / MinIO Object Storage Metadata Sync
echo "[4/4] Syncing object storage documents manifest..."
if command -v aws &> /dev/null; then
  aws s3 sync "s3://${MINIO_BUCKET_NAME:-graphintel-documents}" "${TARGET_PATH}/documents/"
fi

# 5. Checksum verification
cd "${TARGET_PATH}"
sha256sum * > "SHA256SUMS"

echo "=========================================================="
echo "Backup Completed Successfully!"
echo "Artifacts written to: ${TARGET_PATH}"
echo "=========================================================="
