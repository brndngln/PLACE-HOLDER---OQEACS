#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Neo4j GraphRAG Initialization Script                                       ║
# ║  Waits for Neo4j health → runs seed Cypher → starts API → verifies          ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

NEO4J_HOST="${NEO4J_HOST:-omni-neo4j}"
NEO4J_BOLT_PORT="${NEO4J_BOLT_PORT:-7687}"
NEO4J_HTTP_PORT="${NEO4J_HTTP_PORT:-7474}"
NEO4J_USER="${NEO4J_USER:-neo4j}"
NEO4J_PASSWORD="${NEO4J_PASSWORD:-quantum_elite_2024}"
API_PORT="${API_PORT:-7475}"
SEED_FILE="${SEED_FILE:-/seed/init-patterns.cypher}"
MAX_WAIT="${MAX_WAIT:-120}"

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [neo4j-init] $*"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Wait for Neo4j to be healthy
# ─────────────────────────────────────────────────────────────────────────────

log "Waiting for Neo4j at ${NEO4J_HOST}:${NEO4J_BOLT_PORT}..."
elapsed=0
until cypher-shell -a "bolt://${NEO4J_HOST}:${NEO4J_BOLT_PORT}" \
      -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" \
      "RETURN 1" > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        log "ERROR: Neo4j did not become ready within ${MAX_WAIT}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    log "Waiting... (${elapsed}s)"
done
log "Neo4j is ready."

# ─────────────────────────────────────────────────────────────────────────────
# 2. Run seed Cypher script
# ─────────────────────────────────────────────────────────────────────────────

if [ -f "${SEED_FILE}" ]; then
    log "Running seed script: ${SEED_FILE}"

    # Check if patterns already exist
    PATTERN_COUNT=$(cypher-shell -a "bolt://${NEO4J_HOST}:${NEO4J_BOLT_PORT}" \
        -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" \
        --format plain \
        "MATCH (p:Pattern) RETURN count(p) AS cnt" 2>/dev/null | tail -1 || echo "0")

    if [ "${PATTERN_COUNT}" -gt "10" ]; then
        log "Database already seeded with ${PATTERN_COUNT} patterns. Skipping."
    else
        log "Seeding database..."
        cypher-shell -a "bolt://${NEO4J_HOST}:${NEO4J_BOLT_PORT}" \
            -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" \
            --file "${SEED_FILE}" 2>&1 | tail -5

        # Verify seed
        NEW_COUNT=$(cypher-shell -a "bolt://${NEO4J_HOST}:${NEO4J_BOLT_PORT}" \
            -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" \
            --format plain \
            "MATCH (p:Pattern) RETURN count(p) AS cnt" 2>/dev/null | tail -1 || echo "0")
        log "Seed complete. Pattern count: ${NEW_COUNT}"
    fi
else
    log "WARNING: Seed file not found at ${SEED_FILE}"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 3. Verify pattern count and relationships
# ─────────────────────────────────────────────────────────────────────────────

log "Verifying graph integrity..."

STATS=$(cypher-shell -a "bolt://${NEO4J_HOST}:${NEO4J_BOLT_PORT}" \
    -u "${NEO4J_USER}" -p "${NEO4J_PASSWORD}" \
    --format plain \
    "MATCH (p:Pattern) WITH count(p) AS patterns
     MATCH (c:Category) WITH patterns, count(c) AS categories
     MATCH (l:Language) WITH patterns, categories, count(l) AS languages
     MATCH (pr:Principle) WITH patterns, categories, languages, count(pr) AS principles
     MATCH ()-[r]->() WITH patterns, categories, languages, principles, count(r) AS rels
     RETURN patterns, categories, languages, principles, rels" 2>/dev/null | tail -1)

log "Graph stats: ${STATS}"

# ─────────────────────────────────────────────────────────────────────────────
# 4. Start API service (if running as entrypoint)
# ─────────────────────────────────────────────────────────────────────────────

if [ "${START_API:-false}" = "true" ]; then
    log "Starting Pattern Query API on port ${API_PORT}..."
    exec uvicorn main:app --host 0.0.0.0 --port "${API_PORT}"
fi

log "Neo4j initialization complete."
