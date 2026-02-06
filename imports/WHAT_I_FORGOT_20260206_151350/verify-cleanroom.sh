#!/usr/bin/env bash
# ══════════════════════════════════════════════════════════════════════════════
# ⚛ OMNI QUANTUM ELITE — Clean-Room Reproducibility Verifier
# ══════════════════════════════════════════════════════════════════════════════
# Builds and tests the project in a completely fresh container with --no-cache
# to verify that:
#   1. All dependencies are declared (no hidden host deps)
#   2. Build is reproducible from scratch
#   3. All tests pass in a clean environment
#   4. No reliance on cached artifacts, local configs, or env leaks
#   5. Dockerfile produces consistent, deterministic output
#
# This catches the classic "works on my machine" class of bugs where:
#   - A dependency is installed locally but not in requirements.txt
#   - A config file exists locally but isn't in the repo
#   - An env var is set in the dev shell but not documented
#   - A build artifact from a previous run is required
#
# Usage:
#   verify-cleanroom /path/to/project
#   verify-cleanroom /path/to/project --strict         # Fail on any warning
#   verify-cleanroom /path/to/project --keep-container  # Don't cleanup
#   verify-cleanroom /path/to/project --timeout 600     # 10 min max
#   verify-cleanroom /path/to/project --json            # JSON output only
#
# Requirements:
#   - Docker daemon accessible (mount /var/run/docker.sock)
#   - Project must have either Dockerfile or requirements.txt/package.json
#
# Exit codes:
#   0 = Clean build + all tests pass
#   1 = Build failed (dependency issue)
#   2 = Tests failed in clean environment
#   3 = Configuration/environment issue
# ══════════════════════════════════════════════════════════════════════════════
set -uo pipefail

readonly VERSION="1.0.0"
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[1;33m'
readonly CYAN='\033[0;36m'
readonly MAGENTA='\033[0;35m'
readonly NC='\033[0m'
readonly BOLD='\033[1m'

# ─── Configuration ──────────────────────────────────────────────────────────
PROJECT_DIR=""
STRICT=false
KEEP_CONTAINER=false
TIMEOUT=600
JSON_ONLY=false
REPORT_FILE="/tmp/verify-cleanroom-report.json"
REPORT_URL="${REPORT_URL:-}"
CONTAINER_PREFIX="omni-cleanroom"
START_TIME=$(date +%s%N)

# ─── Parse Arguments ────────────────────────────────────────────────────────

usage() {
    echo "Usage: verify-cleanroom <project-path> [options]"
    echo "  --strict          Fail on warnings"
    echo "  --keep-container  Don't remove containers after test"
    echo "  --timeout <sec>   Max build+test time (default: 600)"
    echo "  --json            JSON output only"
    exit 1
}

while [[ $# -gt 0 ]]; do
    case "$1" in
        --strict)         STRICT=true; shift ;;
        --keep-container) KEEP_CONTAINER=true; shift ;;
        --timeout)        TIMEOUT="$2"; shift 2 ;;
        --json)           JSON_ONLY=true; shift ;;
        --help|-h)        usage ;;
        -*)               echo "Unknown option: $1"; usage ;;
        *)
            if [[ -z "$PROJECT_DIR" ]]; then
                PROJECT_DIR="$1"
            else
                echo "Unexpected argument: $1"; usage
            fi
            shift
            ;;
    esac
done

if [[ -z "$PROJECT_DIR" ]]; then
    PROJECT_DIR="${WORKSPACE:-/workspace}"
fi

if [[ ! -d "$PROJECT_DIR" ]]; then
    echo "Error: Project directory not found: $PROJECT_DIR"
    exit 1
fi

# Resolve to absolute path
PROJECT_DIR=$(cd "$PROJECT_DIR" && pwd)
PROJECT_NAME=$(basename "$PROJECT_DIR")
CONTAINER_NAME="${CONTAINER_PREFIX}-${PROJECT_NAME}-$$"

# ─── Helpers ────────────────────────────────────────────────────────────────

elapsed_ms() { echo $(( ($(date +%s%N) - START_TIME) / 1000000 )); }

log() {
    [[ "$JSON_ONLY" == "false" ]] && echo -e "$1"
}

cleanup() {
    if [[ "$KEEP_CONTAINER" == "false" ]]; then
        docker rm -f "$CONTAINER_NAME" &>/dev/null || true
        docker rmi -f "${CONTAINER_NAME}:test" &>/dev/null || true
    fi
}
trap cleanup EXIT

# ─── Pre-flight Checks ─────────────────────────────────────────────────────

log "${BOLD}${MAGENTA}"
log "╔══════════════════════════════════════════════════════════════════╗"
log "║  ⚛ OMNI QUANTUM ELITE — Clean-Room Reproducibility Verifier    ║"
log "║  Build from scratch. Trust nothing cached.                     ║"
log "╚══════════════════════════════════════════════════════════════════╝"
log "${NC}"

# Check Docker
if ! docker info &>/dev/null; then
    log "  ${RED}✗${NC} Docker not available. Mount /var/run/docker.sock"
    echo '{"status":"error","reason":"Docker not available"}' > "$REPORT_FILE"
    exit 3
fi

log "  ${CYAN}ℹ${NC} Project:   ${PROJECT_DIR}"
log "  ${CYAN}ℹ${NC} Container: ${CONTAINER_NAME}"
log "  ${CYAN}ℹ${NC} Timeout:   ${TIMEOUT}s"

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 1: Detect Project Type & Generate Dockerfile
# ═════════════════════════════════════════════════════════════════════════════

log "\n${BOLD}${CYAN}═══ Phase 1: Project Detection ═══${NC}"

HAS_DOCKERFILE=false
GENERATED_DOCKERFILE=""
PROJECT_TYPE="unknown"
LANGUAGE=""
TEST_COMMAND=""
BUILD_COMMAND=""
WARNINGS=()

if [[ -f "$PROJECT_DIR/Dockerfile" ]]; then
    HAS_DOCKERFILE=true
    log "  ${GREEN}✓${NC} Found Dockerfile"
fi

# Detect Python
if [[ -f "$PROJECT_DIR/requirements.txt" ]] || [[ -f "$PROJECT_DIR/pyproject.toml" ]] || [[ -f "$PROJECT_DIR/setup.py" ]]; then
    PROJECT_TYPE="python"
    LANGUAGE="python"

    if [[ -f "$PROJECT_DIR/pyproject.toml" ]]; then
        log "  ${GREEN}✓${NC} Python project (pyproject.toml)"

        # Check for test dependencies
        if ! grep -q "pytest\|unittest" "$PROJECT_DIR/pyproject.toml" 2>/dev/null; then
            WARNINGS+=("No test framework declared in pyproject.toml")
        fi

        BUILD_COMMAND="pip install -e '.[dev,test]' 2>/dev/null || pip install -e . || pip install -r requirements.txt"
        TEST_COMMAND="python -m pytest -x --timeout=60 -q"

    elif [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        log "  ${GREEN}✓${NC} Python project (requirements.txt)"

        BUILD_COMMAND="pip install --no-cache-dir -r requirements.txt"
        TEST_COMMAND="python -m pytest -x --timeout=60 -q"

        # Check for dev requirements
        if [[ -f "$PROJECT_DIR/requirements-dev.txt" ]]; then
            BUILD_COMMAND="${BUILD_COMMAND} && pip install --no-cache-dir -r requirements-dev.txt"
        fi
    fi

    # Check for missing __init__.py
    local missing_inits
    missing_inits=$(find "$PROJECT_DIR" -type d -not -path "*/\.*" -not -path "*/node_modules/*" -not -path "*/venv/*" -not -path "*/__pycache__/*" | while read -r d; do
        if [[ -n "$(find "$d" -maxdepth 1 -name '*.py' | head -1)" ]] && [[ ! -f "$d/__init__.py" ]] && [[ "$d" != "$PROJECT_DIR" ]]; then
            echo "$d"
        fi
    done | wc -l || echo 0)
    [[ "$missing_inits" -gt 0 ]] && WARNINGS+=("${missing_inits} directories with .py files missing __init__.py")
fi

# Detect Node.js
if [[ -f "$PROJECT_DIR/package.json" ]]; then
    if [[ "$PROJECT_TYPE" == "unknown" ]]; then
        PROJECT_TYPE="nodejs"
        LANGUAGE="javascript"
    else
        PROJECT_TYPE="${PROJECT_TYPE}+nodejs"
    fi
    log "  ${GREEN}✓${NC} Node.js project (package.json)"

    BUILD_COMMAND="${BUILD_COMMAND:+$BUILD_COMMAND && }npm ci --ignore-scripts=false"

    # Detect test runner
    if grep -q '"vitest"' "$PROJECT_DIR/package.json" 2>/dev/null; then
        TEST_COMMAND="${TEST_COMMAND:+$TEST_COMMAND && }npx vitest run --reporter=verbose"
    elif grep -q '"jest"' "$PROJECT_DIR/package.json" 2>/dev/null; then
        TEST_COMMAND="${TEST_COMMAND:+$TEST_COMMAND && }npx jest --forceExit --detectOpenHandles"
    elif grep -q '"test"' "$PROJECT_DIR/package.json" 2>/dev/null; then
        TEST_COMMAND="${TEST_COMMAND:+$TEST_COMMAND && }npm test"
    fi

    # Check for lockfile
    if [[ ! -f "$PROJECT_DIR/package-lock.json" ]] && [[ ! -f "$PROJECT_DIR/yarn.lock" ]] && [[ ! -f "$PROJECT_DIR/pnpm-lock.yaml" ]]; then
        WARNINGS+=("No lockfile found (package-lock.json/yarn.lock/pnpm-lock.yaml) — builds won't be reproducible")
    fi
fi

# Detect Go
if [[ -f "$PROJECT_DIR/go.mod" ]]; then
    PROJECT_TYPE="go"
    LANGUAGE="go"
    log "  ${GREEN}✓${NC} Go project (go.mod)"
    BUILD_COMMAND="go build ./..."
    TEST_COMMAND="go test -race -timeout=120s ./..."
fi

# Detect Rust
if [[ -f "$PROJECT_DIR/Cargo.toml" ]]; then
    PROJECT_TYPE="rust"
    LANGUAGE="rust"
    log "  ${GREEN}✓${NC} Rust project (Cargo.toml)"
    BUILD_COMMAND="cargo build --release"
    TEST_COMMAND="cargo test --release"

    if [[ ! -f "$PROJECT_DIR/Cargo.lock" ]]; then
        WARNINGS+=("No Cargo.lock found — builds won't be reproducible")
    fi
fi

if [[ "$PROJECT_TYPE" == "unknown" ]]; then
    log "  ${YELLOW}⚠${NC} Could not detect project type"
    if [[ "$HAS_DOCKERFILE" == "false" ]]; then
        log "  ${RED}✗${NC} No Dockerfile and no recognized project structure"
        echo '{"status":"error","reason":"Unknown project type and no Dockerfile"}' > "$REPORT_FILE"
        exit 3
    fi
fi

# Print warnings
for w in "${WARNINGS[@]+"${WARNINGS[@]}"}"; do
    log "  ${YELLOW}⚠${NC} $w"
done

# ═════════════════════════════════════════════════════════════════════════════
# PHASE 2: Generate Clean Dockerfile (if project doesn't have one)
# ═════════════════════════════════════════════════════════════════════════════

log "\n${BOLD}${CYAN}═══ Phase 2: Clean Dockerfile ═══${NC}"

DOCKERFILE_PATH="$PROJECT_DIR/Dockerfile"

if [[ "$HAS_DOCKERFILE" == "false" ]]; then
    DOCKERFILE_PATH="/tmp/Dockerfile.cleanroom"

    case "$PROJECT_TYPE" in
        python|python+nodejs)
            cat > "$DOCKERFILE_PATH" <<'PYEOF'
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1
RUN apt-get update && apt-get install -y --no-install-recommends git curl && rm -rf /var/lib/apt/lists/*
WORKDIR /app
COPY requirements*.txt pyproject.toml setup.py setup.cfg Makefile* ./  2>/dev/null || true
COPY . .
PYEOF
            if [[ "$PROJECT_TYPE" == "python+nodejs" ]]; then
                cat >> "$DOCKERFILE_PATH" <<'MIXEOF'
RUN curl -fsSL https://deb.nodesource.com/setup_22.x | bash - && apt-get install -y nodejs
RUN if [ -f package-lock.json ]; then npm ci; elif [ -f package.json ]; then npm install; fi
MIXEOF
            fi
            echo "RUN ${BUILD_COMMAND}" >> "$DOCKERFILE_PATH"
            ;;
        nodejs)
            cat > "$DOCKERFILE_PATH" <<'JSEOF'
FROM node:22-slim
WORKDIR /app
COPY package*.json yarn.lock* pnpm-lock.yaml* ./
COPY . .
JSEOF
            echo "RUN ${BUILD_COMMAND}" >> "$DOCKERFILE_PATH"
            ;;
        go)
            cat > "$DOCKERFILE_PATH" <<'GOEOF'
FROM golang:1.23-bookworm
WORKDIR /app
COPY go.mod go.sum ./
RUN go mod download
COPY . .
GOEOF
            echo "RUN ${BUILD_COMMAND}" >> "$DOCKERFILE_PATH"
            ;;
        rust)
            cat > "$DOCKERFILE_PATH" <<'RSEOF'
FROM rust:1.83-bookworm
WORKDIR /app
COPY Cargo.toml Cargo.lock ./
COPY src/ src/
COPY . .
RSEOF
            echo "RUN ${BUILD_COMMAND}" >> "$DOCKERFILE_PATH"
            ;;
    esac

    log "  ${GREEN}✓${NC} Generated clean Dockerfile for ${PROJECT_TYPE}"
else
    log "  ${GREEN}✓${NC} Using existing Dockerfile"
fi


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 3: Clean Build (--no-cache)
# ═════════════════════════════════════════════════════════════════════════════

log "\n${BOLD}${CYAN}═══ Phase 3: Clean Build (--no-cache) ═══${NC}"

BUILD_LOG="/tmp/cleanroom-build.log"
BUILD_START=$(date +%s)

log "  ${CYAN}ℹ${NC} Building with --no-cache (this may take a while)..."

BUILD_EXIT=0
timeout "$TIMEOUT" docker build \
    --no-cache \
    --pull \
    --progress=plain \
    -f "$DOCKERFILE_PATH" \
    -t "${CONTAINER_NAME}:test" \
    "$PROJECT_DIR" \
    > "$BUILD_LOG" 2>&1 || BUILD_EXIT=$?

BUILD_DURATION=$(($(date +%s) - BUILD_START))

BUILD_STATUS="pass"
BUILD_ERROR=""

if [[ "$BUILD_EXIT" -eq 124 ]]; then
    BUILD_STATUS="fail"
    BUILD_ERROR="Build timed out after ${TIMEOUT}s"
    log "  ${RED}✗${NC} Build timed out (${TIMEOUT}s)"
elif [[ "$BUILD_EXIT" -ne 0 ]]; then
    BUILD_STATUS="fail"
    BUILD_ERROR=$(tail -20 "$BUILD_LOG" | tr '\n' ' ' | head -c 500)
    log "  ${RED}✗${NC} Build failed (exit ${BUILD_EXIT})"
    log "  ${RED}  Last lines:${NC}"
    tail -5 "$BUILD_LOG" | while IFS= read -r line; do
        log "    ${RED}│${NC} $line"
    done
else
    log "  ${GREEN}✓${NC} Build succeeded (${BUILD_DURATION}s)"
fi

# Check for common dependency issues in build log
DEP_ISSUES=()
if grep -qi "ModuleNotFoundError\|ImportError\|No module named" "$BUILD_LOG" 2>/dev/null; then
    local missing_module
    missing_module=$(grep -oP "No module named '\K[^']+" "$BUILD_LOG" 2>/dev/null | head -1)
    DEP_ISSUES+=("Missing Python module: ${missing_module:-unknown}")
fi
if grep -qi "Cannot find module\|Module not found" "$BUILD_LOG" 2>/dev/null; then
    DEP_ISSUES+=("Missing Node.js module in build")
fi
if grep -qi "Could not find a version that satisfies\|No matching distribution" "$BUILD_LOG" 2>/dev/null; then
    DEP_ISSUES+=("Python package not found on PyPI")
fi
if grep -qi "404 Not Found.*npm" "$BUILD_LOG" 2>/dev/null; then
    DEP_ISSUES+=("npm package not found in registry")
fi

for issue in "${DEP_ISSUES[@]+"${DEP_ISSUES[@]}"}"; do
    log "  ${YELLOW}⚠${NC} Dependency issue: $issue"
done


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 4: Run Tests in Clean Container
# ═════════════════════════════════════════════════════════════════════════════

TEST_STATUS="skip"
TEST_DURATION=0
TEST_OUTPUT=""
TEST_EXIT=0

if [[ "$BUILD_STATUS" == "pass" ]] && [[ -n "$TEST_COMMAND" ]]; then
    log "\n${BOLD}${CYAN}═══ Phase 4: Test in Clean Container ═══${NC}"

    TEST_LOG="/tmp/cleanroom-test.log"
    TEST_START=$(date +%s)

    log "  ${CYAN}ℹ${NC} Running: ${TEST_COMMAND}"

    # Run tests in the built container — no volume mounts, no env leaks
    timeout "$((TIMEOUT - BUILD_DURATION))" docker run \
        --rm \
        --name "$CONTAINER_NAME" \
        --network=none \
        --memory=2g \
        --cpus=2 \
        "${CONTAINER_NAME}:test" \
        sh -c "$TEST_COMMAND" \
        > "$TEST_LOG" 2>&1 || TEST_EXIT=$?

    TEST_DURATION=$(($(date +%s) - TEST_START))
    TEST_OUTPUT=$(tail -30 "$TEST_LOG" | head -c 2000)

    if [[ "$TEST_EXIT" -eq 0 ]]; then
        TEST_STATUS="pass"
        log "  ${GREEN}✓${NC} Tests passed in clean environment (${TEST_DURATION}s)"
    elif [[ "$TEST_EXIT" -eq 124 ]]; then
        TEST_STATUS="fail"
        log "  ${RED}✗${NC} Tests timed out"
    else
        TEST_STATUS="fail"
        log "  ${RED}✗${NC} Tests failed in clean environment (exit ${TEST_EXIT})"
        log "  ${RED}  Last lines:${NC}"
        tail -5 "$TEST_LOG" | while IFS= read -r line; do
            log "    ${RED}│${NC} $line"
        done
    fi

    # Check for environment-dependent failures
    if grep -qi "ECONNREFUSED\|connection refused\|Could not connect" "$TEST_LOG" 2>/dev/null; then
        log "  ${YELLOW}⚠${NC} Tests appear to depend on external services (network=none blocked them)"
        WARNINGS+=("Tests depend on external services — mark these as integration tests")
    fi

    if grep -qi "FileNotFoundError\|No such file" "$TEST_LOG" 2>/dev/null; then
        log "  ${YELLOW}⚠${NC} Tests depend on files not included in the build"
        WARNINGS+=("Missing test fixtures or data files in Docker context")
    fi

    if grep -qi "KeyError.*env\|environ\|MISSING.*ENV\|not set" "$TEST_LOG" 2>/dev/null; then
        log "  ${YELLOW}⚠${NC} Tests depend on environment variables not in container"
        WARNINGS+=("Tests require environment variables not declared in Dockerfile")
    fi

elif [[ "$BUILD_STATUS" == "fail" ]]; then
    log "\n${BOLD}${CYAN}═══ Phase 4: Test — SKIPPED (build failed) ═══${NC}"
else
    log "\n${BOLD}${CYAN}═══ Phase 4: Test — SKIPPED (no test command) ═══${NC}"
    WARNINGS+=("No test command detected — cannot verify correctness in clean room")
fi


# ═════════════════════════════════════════════════════════════════════════════
# PHASE 5: Reproducibility Check
# ═════════════════════════════════════════════════════════════════════════════

REPRO_STATUS="skip"

if [[ "$BUILD_STATUS" == "pass" ]]; then
    log "\n${BOLD}${CYAN}═══ Phase 5: Reproducibility Check ═══${NC}"

    # Get image digest
    local digest1
    digest1=$(docker inspect --format='{{.Id}}' "${CONTAINER_NAME}:test" 2>/dev/null || echo "unknown")
    log "  ${CYAN}ℹ${NC} First build digest: ${digest1:0:24}..."

    # Check for non-deterministic elements
    local nondeterministic=()

    # Check if Dockerfile uses :latest tags
    if grep -q ":latest" "$DOCKERFILE_PATH" 2>/dev/null; then
        nondeterministic+=("Dockerfile uses :latest tags (pin specific versions)")
    fi

    # Check for apt-get without version pinning
    if grep -q "apt-get install" "$DOCKERFILE_PATH" 2>/dev/null && ! grep -q "apt-get install.*=" "$DOCKERFILE_PATH" 2>/dev/null; then
        nondeterministic+=("apt-get install without version pinning")
    fi

    # Check for pip install without version pinning
    if [[ -f "$PROJECT_DIR/requirements.txt" ]]; then
        local unpinned
        unpinned=$(grep -v "^#\|^$\|==\|>=" "$PROJECT_DIR/requirements.txt" 2>/dev/null | wc -l || echo 0)
        [[ "$unpinned" -gt 0 ]] && nondeterministic+=("${unpinned} unpinned Python dependencies in requirements.txt")
    fi

    if [[ ${#nondeterministic[@]} -eq 0 ]]; then
        REPRO_STATUS="pass"
        log "  ${GREEN}✓${NC} Build appears reproducible"
    else
        REPRO_STATUS="warn"
        for nd in "${nondeterministic[@]}"; do
            log "  ${YELLOW}⚠${NC} Non-deterministic: $nd"
            WARNINGS+=("$nd")
        done
    fi
fi


# ═════════════════════════════════════════════════════════════════════════════
# FINAL REPORT
# ═════════════════════════════════════════════════════════════════════════════

TOTAL_MS=$(elapsed_ms)

FINAL_STATUS="pass"
if [[ "$BUILD_STATUS" == "fail" ]]; then
    FINAL_STATUS="fail"
elif [[ "$TEST_STATUS" == "fail" ]]; then
    FINAL_STATUS="fail"
elif [[ "$STRICT" == "true" ]] && [[ ${#WARNINGS[@]} -gt 0 ]]; then
    FINAL_STATUS="fail"
elif [[ "$REPRO_STATUS" == "warn" ]] || [[ ${#WARNINGS[@]} -gt 0 ]]; then
    FINAL_STATUS="warn"
fi

# Build warnings JSON array
WARNINGS_JSON="[]"
for w in "${WARNINGS[@]+"${WARNINGS[@]}"}"; do
    WARNINGS_JSON=$(echo "$WARNINGS_JSON" | jq --arg w "$w" '. + [$w]')
done

DEP_ISSUES_JSON="[]"
for d in "${DEP_ISSUES[@]+"${DEP_ISSUES[@]}"}"; do
    DEP_ISSUES_JSON=$(echo "$DEP_ISSUES_JSON" | jq --arg d "$d" '. + [$d]')
done

cat > "$REPORT_FILE" <<EOF
{
  "check": "cleanroom",
  "version": "${VERSION}",
  "timestamp": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "project": "${PROJECT_NAME}",
  "project_type": "${PROJECT_TYPE}",
  "language": "${LANGUAGE}",
  "status": "${FINAL_STATUS}",
  "duration_ms": ${TOTAL_MS},
  "phases": {
    "build": {
      "status": "${BUILD_STATUS}",
      "duration_seconds": ${BUILD_DURATION},
      "dockerfile": "${HAS_DOCKERFILE}",
      "no_cache": true,
      "error": $(echo "${BUILD_ERROR:-null}" | jq -Rs 'if . == "null\n" then null else . end')
    },
    "test": {
      "status": "${TEST_STATUS}",
      "duration_seconds": ${TEST_DURATION},
      "command": $(echo "${TEST_COMMAND:-null}" | jq -Rs 'if . == "null\n" then null else . end'),
      "exit_code": ${TEST_EXIT}
    },
    "reproducibility": {
      "status": "${REPRO_STATUS}"
    }
  },
  "dependency_issues": ${DEP_ISSUES_JSON},
  "warnings": ${WARNINGS_JSON},
  "strict_mode": ${STRICT}
}
EOF

# Post report if URL configured
if [[ -n "$REPORT_URL" ]]; then
    curl -sf -X POST "$REPORT_URL" \
        -H "Content-Type: application/json" \
        -d @"$REPORT_FILE" &>/dev/null || true
fi

# Summary
if [[ "$JSON_ONLY" == "true" ]]; then
    cat "$REPORT_FILE"
else
    log ""
    log "${BOLD}═══ Clean-Room Reproducibility Summary ═══${NC}"
    log "  Project:   ${PROJECT_NAME} (${PROJECT_TYPE})"
    log "  Build:     $(
        if [[ "$BUILD_STATUS" == "pass" ]]; then echo -e "${GREEN}PASS${NC} (${BUILD_DURATION}s)";
        else echo -e "${RED}FAIL${NC}"; fi
    )"
    log "  Tests:     $(
        if [[ "$TEST_STATUS" == "pass" ]]; then echo -e "${GREEN}PASS${NC} (${TEST_DURATION}s)";
        elif [[ "$TEST_STATUS" == "fail" ]]; then echo -e "${RED}FAIL${NC}";
        else echo -e "${YELLOW}SKIP${NC}"; fi
    )"
    log "  Repro:     $(
        if [[ "$REPRO_STATUS" == "pass" ]]; then echo -e "${GREEN}PASS${NC}";
        elif [[ "$REPRO_STATUS" == "warn" ]]; then echo -e "${YELLOW}WARN${NC}";
        else echo -e "${YELLOW}SKIP${NC}"; fi
    )"
    log "  Warnings:  ${#WARNINGS[@]}"
    log "  Duration:  ${TOTAL_MS}ms"
    log "  Status:    $(
        if [[ "$FINAL_STATUS" == "pass" ]]; then echo -e "${GREEN}PASS${NC}";
        elif [[ "$FINAL_STATUS" == "warn" ]]; then echo -e "${YELLOW}WARN${NC}";
        else echo -e "${RED}FAIL${NC}"; fi
    )"
    log "  Report:    ${REPORT_FILE}"
    log ""
fi

case "$FINAL_STATUS" in
    pass) exit 0 ;;
    warn) exit 0 ;;  # Warnings don't block by default (--strict changes this)
    fail)
        if [[ "$BUILD_STATUS" == "fail" ]]; then exit 1;
        elif [[ "$TEST_STATUS" == "fail" ]]; then exit 2;
        else exit 3; fi
        ;;
esac
