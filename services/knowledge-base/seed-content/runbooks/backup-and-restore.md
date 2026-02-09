# Runbook: Backup and Restore

## Overview
Procedures for backing up and restoring all persistent data in the Omni Quantum Elite platform.

**Audience**: Platform engineers, DevOps
**Estimated time**: 15 min (backup) / 30–60 min (restore)
**Risk level**: Medium (backup) / High (restore)

---

## Backup Strategy

| Data Source | Method | Schedule | Retention | Target |
|-------------|--------|----------|-----------|--------|
| PostgreSQL | pg_dump | Hourly | 30 days | MinIO `omni-backups/postgres/` |
| Neo4j | neo4j-admin dump | Daily | 14 days | MinIO `omni-backups/neo4j/` |
| Redis | RDB snapshot | Every 6 hours | 7 days | MinIO `omni-backups/redis/` |
| Qdrant | Snapshot API | Daily | 14 days | MinIO `omni-backups/qdrant/` |
| Gitea | gitea dump | Daily | 30 days | MinIO `omni-backups/gitea/` |
| Wiki.js | DB + Git sync | Continuous (Git) + Daily (DB) | 30 days | MinIO + Gitea |
| MinIO | Cross-bucket replication | Daily | 14 days | External S3 (if configured) |
| Vault | vault operator raft snapshot | Daily | 30 days | MinIO `omni-backups/vault/` |
| Docker volumes | Duplicati | Hourly incremental | 30 days | MinIO `omni-backups/volumes/` |

---

## Backup Procedures

### PostgreSQL Backup

```bash
# Automated (runs via cron in omni-duplicati)
docker exec omni-postgres pg_dumpall -U postgres | gzip > /backup/postgres/all_$(date +%Y%m%d_%H%M%S).sql.gz

# Manual backup of specific database
docker exec omni-postgres pg_dump -U postgres -d wikijs -Fc > /backup/postgres/wikijs_$(date +%Y%m%d).dump

# Upload to MinIO
mc cp /backup/postgres/all_*.sql.gz omni/omni-backups/postgres/
```

### Neo4j Backup

```bash
# Stop writes (optional — neo4j-admin dump works on running DB)
docker exec omni-neo4j neo4j-admin database dump neo4j --to-path=/backup/

# Copy out of container
docker cp omni-neo4j:/backup/neo4j.dump /backup/neo4j/neo4j_$(date +%Y%m%d).dump

# Upload to MinIO
mc cp /backup/neo4j/neo4j_*.dump omni/omni-backups/neo4j/
```

### Redis Backup

```bash
# Trigger RDB save
docker exec omni-redis redis-cli BGSAVE

# Wait for save to complete
docker exec omni-redis redis-cli LASTSAVE

# Copy RDB file
docker cp omni-redis:/data/dump.rdb /backup/redis/dump_$(date +%Y%m%d_%H%M%S).rdb

# Upload to MinIO
mc cp /backup/redis/dump_*.rdb omni/omni-backups/redis/
```

### Qdrant Backup

```bash
# Create snapshots for each collection
for collection in code_embeddings doc_embeddings conversation_memory pattern_cache; do
    curl -X POST "http://omni-qdrant:6333/collections/${collection}/snapshots"
done

# List and download snapshots
curl http://omni-qdrant:6333/collections/code_embeddings/snapshots

# Download snapshot
curl -o /backup/qdrant/code_embeddings_$(date +%Y%m%d).snapshot \
  "http://omni-qdrant:6333/collections/code_embeddings/snapshots/<snapshot_name>"
```

### Gitea Backup

```bash
# Full Gitea dump (repos, DB, config)
docker exec omni-gitea gitea dump -c /data/gitea/conf/app.ini -f /backup/gitea_$(date +%Y%m%d).zip

# Copy out
docker cp omni-gitea:/backup/gitea_*.zip /backup/gitea/

# Upload to MinIO
mc cp /backup/gitea/gitea_*.zip omni/omni-backups/gitea/
```

### Vault Backup

```bash
# Raft snapshot (for integrated storage)
curl -o /backup/vault/vault_$(date +%Y%m%d).snap \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  http://omni-vault:8200/v1/sys/storage/raft/snapshot

# Upload to MinIO
mc cp /backup/vault/vault_*.snap omni/omni-backups/vault/
```

---

## Restore Procedures

> **WARNING**: Restore operations are destructive. They replace current data with backup data. Always verify the backup integrity before restoring.

### PostgreSQL Restore

```bash
# Stop dependent services
docker compose stop omni-wikijs omni-langfuse omni-accounts omni-invoicing omni-analytics omni-crm

# Restore from dump
gunzip -c /backup/postgres/all_YYYYMMDD_HHMMSS.sql.gz | docker exec -i omni-postgres psql -U postgres

# Or restore specific database
docker exec -i omni-postgres pg_restore -U postgres -d wikijs --clean < /backup/postgres/wikijs_YYYYMMDD.dump

# Restart dependent services
docker compose start omni-wikijs omni-langfuse omni-accounts omni-invoicing omni-analytics omni-crm
```

### Neo4j Restore

```bash
# Stop Neo4j and dependent services
docker compose stop omni-neo4j-graphrag-api omni-neo4j

# Copy dump into container
docker cp /backup/neo4j/neo4j_YYYYMMDD.dump omni-neo4j:/backup/neo4j.dump

# Restore (requires neo4j to be stopped)
docker exec omni-neo4j neo4j-admin database load neo4j --from-path=/backup/ --overwrite-destination

# Start services
docker compose start omni-neo4j
sleep 30  # Wait for Neo4j to initialize
docker compose start omni-neo4j-graphrag-api
```

### Redis Restore

```bash
# Stop Redis
docker compose stop omni-redis

# Copy RDB file
docker cp /backup/redis/dump_YYYYMMDD_HHMMSS.rdb omni-redis:/data/dump.rdb

# Start Redis (it loads from dump.rdb on startup)
docker compose start omni-redis
```

### Qdrant Restore

```bash
# Restore from snapshot
curl -X PUT "http://omni-qdrant:6333/collections/code_embeddings/snapshots/recover" \
  -H "Content-Type: application/json" \
  -d '{
    "location": "file:///backup/qdrant/code_embeddings_YYYYMMDD.snapshot"
  }'
```

### Vault Restore

```bash
# Restore raft snapshot
curl -X POST http://omni-vault:8200/v1/sys/storage/raft/snapshot-force \
  -H "X-Vault-Token: ${VAULT_TOKEN}" \
  --data-binary @/backup/vault/vault_YYYYMMDD.snap
```

---

## Backup Verification

Run monthly:

```bash
#!/usr/bin/env bash
# Verify backup integrity
set -euo pipefail

echo "=== Backup Verification $(date) ==="

# Check MinIO bucket contents
echo "--- MinIO Backup Inventory ---"
for dir in postgres neo4j redis qdrant gitea vault; do
    count=$(mc ls omni/omni-backups/${dir}/ 2>/dev/null | wc -l)
    latest=$(mc ls omni/omni-backups/${dir}/ 2>/dev/null | tail -1)
    echo "${dir}: ${count} backups, latest: ${latest}"
done

# Test PostgreSQL backup restore (to temp database)
echo "--- PostgreSQL Backup Test ---"
docker exec omni-postgres createdb -U postgres backup_test 2>/dev/null || true
latest_pg=$(ls -t /backup/postgres/all_*.sql.gz | head -1)
gunzip -c "${latest_pg}" | docker exec -i omni-postgres psql -U postgres -d backup_test > /dev/null 2>&1
echo "PostgreSQL restore test: OK"
docker exec omni-postgres dropdb -U postgres backup_test

echo "=== Verification Complete ==="
```

---

## Disaster Recovery

### Full Platform Recovery (RTO: 30 minutes)

1. Ensure Docker and Docker Compose are installed on new host
2. Restore `docker-compose.yml` and service configurations from Gitea backup
3. Start infrastructure services: PostgreSQL, Redis, Neo4j, MinIO, Vault
4. Restore data from MinIO backups (follow restore procedures above)
5. Start remaining services in dependency order
6. Verify health of all services
7. Re-register Prometheus scrape targets
8. Verify Grafana dashboards

---

## Common Issues

| Issue | Solution |
|-------|----------|
| pg_dump fails with "too many connections" | Reduce `max_connections` or kill idle connections |
| Neo4j dump takes too long | Increase `dbms.memory.heap.max_size` temporarily |
| MinIO upload fails | Check disk space on MinIO volume |
| Qdrant snapshot too large | Archive older snapshots, increase storage |
| Vault snapshot unauthorized | Verify root token or recovery keys |
