#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="backups/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

echo "Backing up PostgreSQL..."
docker compose exec -T postgres pg_dump -U veritas -d veritas > "$BACKUP_DIR/postgres.sql"

echo "Creating Qdrant snapshot..."
curl -fsS -X POST \
  "http://localhost:6333/collections/veritas_documents/snapshots"

echo
echo "PostgreSQL backup created:"
ls -lh "$BACKUP_DIR/postgres.sql"

echo
echo "Backup complete."
