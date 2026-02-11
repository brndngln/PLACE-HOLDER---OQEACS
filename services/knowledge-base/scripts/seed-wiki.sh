#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Wiki.js Seed Content Script                                                ║
# ║  Imports markdown files from seed-content/ into Wiki.js via GraphQL         ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

WIKI_HOST=""
WIKI_PORT="${WIKI_PORT:-3000}"
WIKI_URL="http://${WIKI_HOST}:${WIKI_PORT}"
WIKI_GRAPHQL="${WIKI_URL}/graphql"
ADMIN_EMAIL="${WIKI_ADMIN_EMAIL:-admin@omni-quantum.local}"
ADMIN_PASSWORD="${WIKI_ADMIN_PASSWORD:-quantum_elite_2024}"
SEED_DIR="${SEED_DIR:-/seed-content}"
MAX_WAIT="${MAX_WAIT:-60}"

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [seed-wiki] $*"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Wait for Wiki.js
# ─────────────────────────────────────────────────────────────────────────────

log "Waiting for Wiki.js at ${WIKI_URL}..."
elapsed=0
until curl -sf "${WIKI_URL}/healthz" > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        log "ERROR: Wiki.js not ready within ${MAX_WAIT}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
done
log "Wiki.js is ready."

# ─────────────────────────────────────────────────────────────────────────────
# 2. Authenticate
# ─────────────────────────────────────────────────────────────────────────────

log "Authenticating..."
LOGIN_RESULT=$(curl -sf -X POST "${WIKI_GRAPHQL}" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"mutation { authentication { login(username: \\\"${ADMIN_EMAIL}\\\", password: \\\"${ADMIN_PASSWORD}\\\", strategy: \\\"local\\\") { responseResult { succeeded message } jwt } } }\"}" 2>/dev/null || echo '{}')

JWT=$(echo "${LOGIN_RESULT}" | jq -r '.data.authentication.login.jwt // empty' 2>/dev/null || true)

if [ -z "${JWT}" ]; then
    if [ -n "${WIKI_API_KEY:-}" ]; then
        JWT="${WIKI_API_KEY}"
        log "Using WIKI_API_KEY."
    else
        log "ERROR: Could not authenticate. Run wiki-init.sh first."
        exit 1
    fi
fi
log "Authenticated."

# ─────────────────────────────────────────────────────────────────────────────
# 3. Helper: create or update a page
# ─────────────────────────────────────────────────────────────────────────────

create_page() {
    local file_path="$1"
    local wiki_path="$2"
    local title="$3"
    local tags="$4"
    local description="$5"

    if [ ! -f "${file_path}" ]; then
        log "WARNING: File not found: ${file_path}"
        return 1
    fi

    local content
    content=$(jq -Rs . < "${file_path}")

    # Check if page already exists
    local check_query="{ pages { single(id: 0, path: \"${wiki_path}\", locale: \"en\") { id } } }"
    local existing
    existing=$(curl -sf -X POST "${WIKI_GRAPHQL}" \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer ${JWT}" \
        -d "{\"query\": $(echo "${check_query}" | jq -Rs .)}" 2>/dev/null || echo '{}')

    local existing_id
    existing_id=$(echo "${existing}" | jq -r '.data.pages.single.id // empty' 2>/dev/null || true)

    if [ -n "${existing_id}" ] && [ "${existing_id}" != "null" ]; then
        # Update existing page
        log "Updating existing page: ${wiki_path} (id: ${existing_id})"
        local update_query
        update_query=$(cat <<GRAPHQL
mutation {
  pages {
    update(
      id: ${existing_id}
      content: ${content}
      description: "${description}"
      tags: [${tags}]
      title: "${title}"
    ) {
      responseResult { succeeded message }
    }
  }
}
GRAPHQL
)
        local result
        result=$(curl -sf -X POST "${WIKI_GRAPHQL}" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${JWT}" \
            -d "{\"query\": $(echo "${update_query}" | jq -Rs .)}" 2>/dev/null || echo '{}')

        local ok
        ok=$(echo "${result}" | jq -r '.data.pages.update.responseResult.succeeded // false' 2>/dev/null || echo "false")
        if [ "${ok}" = "true" ]; then
            log "  Updated: ${wiki_path}"
        else
            log "  WARNING: Update failed for ${wiki_path}: $(echo "${result}" | jq -r '.data.pages.update.responseResult.message // "unknown"' 2>/dev/null)"
        fi
    else
        # Create new page
        log "Creating page: ${wiki_path}"
        local create_query
        create_query=$(cat <<GRAPHQL
mutation {
  pages {
    create(
      content: ${content}
      description: "${description}"
      editor: "markdown"
      isPublished: true
      isPrivate: false
      locale: "en"
      path: "${wiki_path}"
      tags: [${tags}]
      title: "${title}"
    ) {
      responseResult { succeeded message }
      page { id path title }
    }
  }
}
GRAPHQL
)
        local result
        result=$(curl -sf -X POST "${WIKI_GRAPHQL}" \
            -H "Content-Type: application/json" \
            -H "Authorization: Bearer ${JWT}" \
            -d "{\"query\": $(echo "${create_query}" | jq -Rs .)}" 2>/dev/null || echo '{}')

        local ok
        ok=$(echo "${result}" | jq -r '.data.pages.create.responseResult.succeeded // false' 2>/dev/null || echo "false")
        if [ "${ok}" = "true" ]; then
            local page_id
            page_id=$(echo "${result}" | jq -r '.data.pages.create.page.id // "?"' 2>/dev/null)
            log "  Created: ${wiki_path} (id: ${page_id})"
        else
            log "  WARNING: Create failed for ${wiki_path}: $(echo "${result}" | jq -r '.data.pages.create.responseResult.message // "unknown"' 2>/dev/null)"
        fi
    fi
}

# ─────────────────────────────────────────────────────────────────────────────
# 4. Seed all content pages
# ─────────────────────────────────────────────────────────────────────────────

log "Starting content seeding from ${SEED_DIR}..."

TOTAL=0
SUCCESS=0

# Platform overview
create_page "${SEED_DIR}/platform-overview.md" \
    "platform-overview" \
    "Platform Architecture Overview" \
    '"architecture", "platform", "overview"' \
    "Complete architecture overview of the Omni Quantum Elite AI Coding System" && ((SUCCESS++)) || true
((TOTAL++))

# API Reference
for api_file in "${SEED_DIR}"/api-reference/*.md; do
    [ -f "${api_file}" ] || continue
    basename_no_ext=$(basename "${api_file}" .md)
    title=$(echo "${basename_no_ext}" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')
    create_page "${api_file}" \
        "api-reference/${basename_no_ext}" \
        "${title}" \
        '"api", "reference", "documentation"' \
        "API reference documentation for ${title}" && ((SUCCESS++)) || true
    ((TOTAL++))
done

# Runbooks
for runbook_file in "${SEED_DIR}"/runbooks/*.md; do
    [ -f "${runbook_file}" ] || continue
    basename_no_ext=$(basename "${runbook_file}" .md)
    title=$(echo "${basename_no_ext}" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')
    create_page "${runbook_file}" \
        "runbooks/${basename_no_ext}" \
        "${title}" \
        '"runbook", "operations", "procedures"' \
        "Operational runbook: ${title}" && ((SUCCESS++)) || true
    ((TOTAL++))
done

# Templates
for template_file in "${SEED_DIR}"/templates/*.md; do
    [ -f "${template_file}" ] || continue
    basename_no_ext=$(basename "${template_file}" .md)
    title=$(echo "${basename_no_ext}" | sed 's/-/ /g' | sed 's/\b\(.\)/\u\1/g')
    create_page "${template_file}" \
        "templates/${basename_no_ext}" \
        "${title}" \
        '"template", "documentation"' \
        "Document template: ${title}" && ((SUCCESS++)) || true
    ((TOTAL++))
done

log "Seeding complete: ${SUCCESS}/${TOTAL} pages created/updated."

# ─────────────────────────────────────────────────────────────────────────────
# 5. Rebuild search index after seeding
# ─────────────────────────────────────────────────────────────────────────────

log "Rebuilding search index..."
curl -sf -X POST "${WIKI_GRAPHQL}" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer ${JWT}" \
    -d '{"query": "mutation { search { rebuildIndex { responseResult { succeeded message } } } }"}' > /dev/null 2>&1 || true

log "Search index rebuild triggered."
log "Wiki.js seed complete."
