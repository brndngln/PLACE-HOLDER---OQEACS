#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

banner() {
  echo "══════════════════════════════════════="
  echo "  STRUCTURE VERIFICATION"
  echo "══════════════════════════════════════="
}

count_glob() {
  shopt -s nullglob
  local patterns=("$@")
  local files=()
  for p in "${patterns[@]}"; do
    files+=( $p )
  done
  echo "${#files[@]}"
  shopt -u nullglob
}

banner

# Financial files moved
echo -n "Financial files in financial/: "
count_glob "financial/*.py"
echo " (should be 8)"

# Design docs moved
echo -n "Design docs in docs/: "
count_glob "docs/*.md" "docs/*.docx" "docs/*.jsx"
echo " (should be 13+)"

# No stray Python at root
echo -n "Root .py files: "
count_glob "*.py"
echo " (should be 0)"

# No stray design docs at root
echo -n "Root design docs: "
count_glob "omni-quantum-elite-*.md" "omni-quantum-elite-*.jsx" "HIGH-PRIORITY-*.md" "MEDIUM-PRIORITY-*.md"
echo " (should be 0)"

# No duplicates at root
echo -n "Root junk files: "
python - <<'PY'
import os
count = 0
for name in os.listdir('.'):
    if os.path.isfile(name) and ' (' in name and ')' in name:
        count += 1
print(count)
PY
echo " (should be 0)"

# No hardcoded passwords
echo -n "Hardcoded passwords: "
{ grep -rn "quantum_elite_2024\|fortress_pass\|changeme" . --include="*.yml" --include="*.py" | grep -v '.git/' | grep -v 'archive/' || true; } | wc -l
echo " (should be 0)"

# No :latest tags
echo -n "Unpinned :latest: "
{ grep -rn ":latest" . --include="*.yml" | grep -v '.git/' | grep -v 'archive/' || true; } | wc -l
echo " (should be 0)"

# Networks (robust YAML parse)
echo -n "Services missing omni-quantum-network: "
python - <<'PY'
from pathlib import Path
import yaml

missing = []
files = []
for path in Path('.').rglob('docker-compose*.yml'):
    if '.git' in path.parts or 'archive' in path.parts:
        continue
    files.append(path)

for path in files:
    try:
        data = yaml.safe_load(path.read_text())
    except Exception:
        continue
    if not isinstance(data, dict):
        continue
    services = data.get('services')
    if not isinstance(services, dict):
        continue
    for name, svc in services.items():
        if not isinstance(svc, dict):
            continue
        nets = svc.get('networks')
        ok = False
        if nets is None:
            ok = False
        elif isinstance(nets, list):
            ok = 'omni-quantum-network' in nets
        elif isinstance(nets, dict):
            ok = 'omni-quantum-network' in nets
        elif isinstance(nets, str):
            ok = nets == 'omni-quantum-network'
        if not ok:
            missing.append((path, name))

print(len(missing))
PY
echo " (should be 0)"

# Schema tables vs financial CREATE TABLE blocks
echo -n "Schema CREATE TABLE count: "
grep -c "CREATE TABLE" database/schema.sql 2>/dev/null

echo -n "Missing CREATE TABLE blocks from financial modules: "
python - <<'PY'
import re
from pathlib import Path

schema_text = Path('database/schema.sql').read_text()
schema_tables = set(re.findall(r'CREATE TABLE(?: IF NOT EXISTS)?\s+([A-Za-z_][A-Za-z0-9_]*)', schema_text, flags=re.IGNORECASE))

create_re = re.compile(r'CREATE TABLE IF NOT EXISTS\s+([A-Za-z_][A-Za-z0-9_]*)\s*\((.*?)\);', re.IGNORECASE | re.DOTALL)

missing = []
for path in Path('financial').glob('*.py'):
    text = path.read_text(errors='ignore')
    for match in create_re.finditer(text):
        table = match.group(1)
        if table not in schema_tables:
            missing.append(table)

print(len(missing))
PY
echo " (should be 0)"

echo ""
echo "══════════════════════════════════════="
echo "  VERIFICATION COMPLETE"
echo "══════════════════════════════════════="
