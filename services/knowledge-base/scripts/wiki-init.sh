#!/usr/bin/env bash
# ╔══════════════════════════════════════════════════════════════════════════════╗
# ║  Wiki.js Knowledge Base Initialization Script                               ║
# ║  Waits for Wiki.js → configures admin, Git sync, OIDC, search, navigation  ║
# ╚══════════════════════════════════════════════════════════════════════════════╝

set -euo pipefail

WIKI_HOST=""
WIKI_PORT="${WIKI_PORT:-3000}"
WIKI_URL="http://${WIKI_HOST}:${WIKI_PORT}"
WIKI_GRAPHQL="${WIKI_URL}/graphql"
ADMIN_EMAIL="${WIKI_ADMIN_EMAIL:-admin@omni-quantum.local}"
ADMIN_PASSWORD="${WIKI_ADMIN_PASSWORD:-quantum_elite_2024}"
GITEA_HOST="${GITEA_HOST:-omni-gitea}"
GITEA_PORT="${GITEA_PORT:-3000}"
GITEA_USER="${GITEA_USER:-omni-admin}"
GITEA_TOKEN="${GITEA_TOKEN:-}"
GITEA_REPO="${GITEA_REPO:-omni-admin/knowledge-base}"
AUTHENTIK_HOST="${AUTHENTIK_HOST:-omni-authentik}"
AUTHENTIK_PORT="${AUTHENTIK_PORT:-9000}"
AUTHENTIK_CLIENT_ID="${AUTHENTIK_CLIENT_ID:-wiki-js}"
AUTHENTIK_CLIENT_SECRET="${AUTHENTIK_CLIENT_SECRET:-}"
MAX_WAIT="${MAX_WAIT:-120}"

log() {
    echo "[$(date -u '+%Y-%m-%dT%H:%M:%SZ')] [wiki-init] $*"
}

gql() {
    local query="$1"
    local token="${2:-}"
    local auth_header=""
    if [ -n "${token}" ]; then
        auth_header="-H \"Authorization: Bearer ${token}\""
    fi
    eval curl -sf -X POST "${WIKI_GRAPHQL}" \
        -H "Content-Type: application/json" \
        ${auth_header} \
        -d "{\"query\": $(echo "${query}" | jq -Rs .)}"
}

# ─────────────────────────────────────────────────────────────────────────────
# 1. Wait for Wiki.js to be healthy
# ─────────────────────────────────────────────────────────────────────────────

log "Waiting for Wiki.js at ${WIKI_URL}..."
elapsed=0
until curl -sf "${WIKI_URL}/healthz" > /dev/null 2>&1; do
    if [ "$elapsed" -ge "$MAX_WAIT" ]; then
        log "ERROR: Wiki.js did not become ready within ${MAX_WAIT}s"
        exit 1
    fi
    sleep 2
    elapsed=$((elapsed + 2))
    log "Waiting... (${elapsed}s)"
done
log "Wiki.js is ready."

# ─────────────────────────────────────────────────────────────────────────────
# 2. Finalize admin setup and get API token
# ─────────────────────────────────────────────────────────────────────────────

log "Authenticating as admin..."
LOGIN_RESULT=$(curl -sf -X POST "${WIKI_GRAPHQL}" \
    -H "Content-Type: application/json" \
    -d "{\"query\": \"mutation { authentication { login(username: \\\"${ADMIN_EMAIL}\\\", password: \\\"${ADMIN_PASSWORD}\\\", strategy: \\\"local\\\") { responseResult { succeeded message } jwt } } }\"}" 2>/dev/null || echo '{}')

JWT=$(echo "${LOGIN_RESULT}" | jq -r '.data.authentication.login.jwt // empty' 2>/dev/null || true)

if [ -z "${JWT}" ]; then
    log "WARNING: Could not obtain admin JWT. Wiki.js may need initial setup via browser."
    log "Attempting API key authentication..."
    # Try with API key if set
    if [ -n "${WIKI_API_KEY:-}" ]; then
        JWT="${WIKI_API_KEY}"
        log "Using WIKI_API_KEY for authentication."
    else
        log "No API key available. Skipping programmatic configuration."
        log "Please complete initial setup at ${WIKI_URL} and re-run."
        exit 0
    fi
fi

log "Admin authentication successful."

# ─────────────────────────────────────────────────────────────────────────────
# 3. Configure Git sync with Gitea
# ─────────────────────────────────────────────────────────────────────────────

if [ -n "${GITEA_TOKEN}" ]; then
    log "Configuring Git storage with Gitea..."
    GIT_CONFIG_QUERY='mutation {
      storage {
        updateTargets(targets: [{
          isEnabled: true
          key: "git"
          mode: "sync"
          syncInterval: "PT5M"
          config: {
            authType: "token"
            repoUrl: "http://'"${GITEA_HOST}:${GITEA_PORT}/${GITEA_REPO}"'.git"
            branch: "main"
            token: "'"${GITEA_TOKEN}"'"
            localPath: "./data/repo"
            gitBinaryPath: "git"
          }
        }]) {
          responseResult { succeeded message }
        }
      }
    }'
    GIT_RESULT=$(gql "${GIT_CONFIG_QUERY}" "${JWT}")
    GIT_OK=$(echo "${GIT_RESULT}" | jq -r '.data.storage.updateTargets.responseResult.succeeded // false' 2>/dev/null || echo "false")
    if [ "${GIT_OK}" = "true" ]; then
        log "Git sync configured: ${GITEA_HOST}:${GITEA_PORT}/${GITEA_REPO}"
    else
        log "WARNING: Git sync configuration returned: $(echo "${GIT_RESULT}" | jq -r '.data.storage.updateTargets.responseResult.message // "unknown"' 2>/dev/null)"
    fi
else
    log "GITEA_TOKEN not set. Skipping Git sync configuration."
fi

# ─────────────────────────────────────────────────────────────────────────────
# 4. Configure Authentik OIDC authentication
# ─────────────────────────────────────────────────────────────────────────────

if [ -n "${AUTHENTIK_CLIENT_SECRET}" ]; then
    log "Configuring Authentik OIDC authentication..."
    OIDC_QUERY='mutation {
      authentication {
        updateStrategies(strategies: [{
          key: "oidc"
          strategyKey: "oidc"
          displayName: "Authentik SSO"
          isEnabled: true
          selfRegistration: true
          domainWhitelist: []
          autoEnrollGroups: []
          config: {
            clientId: "'"${AUTHENTIK_CLIENT_ID}"'"
            clientSecret: "'"${AUTHENTIK_CLIENT_SECRET}"'"
            authorizationURL: "http://'"${AUTHENTIK_HOST}:${AUTHENTIK_PORT}"'/application/o/authorize/"
            tokenURL: "http://'"${AUTHENTIK_HOST}:${AUTHENTIK_PORT}"'/application/o/token/"
            userInfoURL: "http://'"${AUTHENTIK_HOST}:${AUTHENTIK_PORT}"'/application/o/userinfo/"
            issuer: "http://'"${AUTHENTIK_HOST}:${AUTHENTIK_PORT}"'/application/o/wiki-js/"
            logoutURL: "http://'"${AUTHENTIK_HOST}:${AUTHENTIK_PORT}"'/application/o/wiki-js/end-session/"
            scope: "openid email profile"
            mapGroups: true
            mapId: "sub"
            mapDisplayName: "name"
            mapEmail: "email"
          }
        }]) {
          responseResult { succeeded message }
        }
      }
    }'
    OIDC_RESULT=$(gql "${OIDC_QUERY}" "${JWT}")
    OIDC_OK=$(echo "${OIDC_RESULT}" | jq -r '.data.authentication.updateStrategies.responseResult.succeeded // false' 2>/dev/null || echo "false")
    if [ "${OIDC_OK}" = "true" ]; then
        log "Authentik OIDC configured: ${AUTHENTIK_HOST}:${AUTHENTIK_PORT}"
    else
        log "WARNING: OIDC configuration returned: $(echo "${OIDC_RESULT}" | jq -r '.data.authentication.updateStrategies.responseResult.message // "unknown"' 2>/dev/null)"
    fi
else
    log "AUTHENTIK_CLIENT_SECRET not set. Skipping OIDC configuration."
fi

# ─────────────────────────────────────────────────────────────────────────────
# 5. Configure search engine
# ─────────────────────────────────────────────────────────────────────────────

log "Configuring search engine (database)..."
SEARCH_QUERY='mutation {
  search {
    updateSearchEngines(engines: [{
      isEnabled: true
      key: "db"
      config: {}
    }]) {
      responseResult { succeeded message }
    }
  }
}'
SEARCH_RESULT=$(gql "${SEARCH_QUERY}" "${JWT}")
SEARCH_OK=$(echo "${SEARCH_RESULT}" | jq -r '.data.search.updateSearchEngines.responseResult.succeeded // false' 2>/dev/null || echo "false")
if [ "${SEARCH_OK}" = "true" ]; then
    log "Search engine configured (database-backed)."
else
    log "WARNING: Search configuration returned: $(echo "${SEARCH_RESULT}" | jq -r '.data.search.updateSearchEngines.responseResult.message // "unknown"' 2>/dev/null)"
fi

# Rebuild search index
log "Rebuilding search index..."
REBUILD_QUERY='mutation { search { rebuildIndex { responseResult { succeeded message } } } }'
gql "${REBUILD_QUERY}" "${JWT}" > /dev/null 2>&1 || true

# ─────────────────────────────────────────────────────────────────────────────
# 6. Configure locale
# ─────────────────────────────────────────────────────────────────────────────

log "Configuring locale (en)..."
LOCALE_QUERY='mutation {
  localization {
    updateLocale(locale: "en", autoUpdate: true, namespacing: false, namespaces: []) {
      responseResult { succeeded message }
    }
  }
}'
gql "${LOCALE_QUERY}" "${JWT}" > /dev/null 2>&1 || true
log "Locale configured."

# ─────────────────────────────────────────────────────────────────────────────
# 7. Configure navigation
# ─────────────────────────────────────────────────────────────────────────────

log "Configuring site navigation..."
NAV_QUERY='mutation {
  navigation {
    updateTree(tree: [
      {kind: "link", label: "Home", icon: "mdi-home", targetType: "page", target: "home"},
      {kind: "header", label: "Platform"},
      {kind: "link", label: "Architecture", icon: "mdi-sitemap", targetType: "page", target: "platform-overview"},
      {kind: "link", label: "API Reference", icon: "mdi-api", targetType: "page", target: "api-reference/foundation-apis"},
      {kind: "header", label: "Operations"},
      {kind: "link", label: "Runbooks", icon: "mdi-book-open-variant", targetType: "page", target: "runbooks/deploy-new-service"},
      {kind: "link", label: "Templates", icon: "mdi-file-document-outline", targetType: "page", target: "templates/architecture-decision-record"},
      {kind: "header", label: "Knowledge"},
      {kind: "link", label: "Pattern Graph", icon: "mdi-graph", targetType: "external", target: "http://omni-neo4j:7474"},
      {kind: "link", label: "Observability", icon: "mdi-chart-line", targetType: "external", target: "http://omni-grafana:3000"}
    ]) {
      responseResult { succeeded message }
    }
  }
}'
NAV_RESULT=$(gql "${NAV_QUERY}" "${JWT}")
NAV_OK=$(echo "${NAV_RESULT}" | jq -r '.data.navigation.updateTree.responseResult.succeeded // false' 2>/dev/null || echo "false")
if [ "${NAV_OK}" = "true" ]; then
    log "Navigation configured."
else
    log "WARNING: Navigation configuration returned: $(echo "${NAV_RESULT}" | jq -r '.data.navigation.updateTree.responseResult.message // "unknown"' 2>/dev/null)"
fi

# ─────────────────────────────────────────────────────────────────────────────
# 8. Configure site settings
# ─────────────────────────────────────────────────────────────────────────────

log "Configuring site settings..."
SITE_QUERY='mutation {
  site {
    updateConfig(
      host: "'"${WIKI_URL}"'"
      title: "Omni Quantum Elite — Knowledge Base"
      description: "Internal knowledge base for the Omni Quantum Elite AI Coding System"
      company: "Omni Quantum"
      contentLicense: "private"
      logoUrl: ""
      featurePageRatings: true
      featurePageComments: true
      featurePersonalWikis: false
      featureSearch: true
    ) {
      responseResult { succeeded message }
    }
  }
}'
gql "${SITE_QUERY}" "${JWT}" > /dev/null 2>&1 || true
log "Site settings configured."

log "Wiki.js initialization complete."
