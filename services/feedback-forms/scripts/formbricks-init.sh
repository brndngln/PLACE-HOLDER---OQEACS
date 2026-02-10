#!/usr/bin/env bash
set -Eeuo pipefail

FORMBRICKS_URL="${FORMBRICKS_URL:-http://omni-formbricks:3000}"
FORMBRICKS_API_KEY="${FORMBRICKS_API_KEY:-}"
FORMBRICKS_ADMIN_EMAIL="${FORMBRICKS_ADMIN_EMAIL:-admin@omni.local}"
FORMBRICKS_ADMIN_NAME="${FORMBRICKS_ADMIN_NAME:-Brendan}"
MM_WEBHOOK="${MM_WEBHOOK:-http://omni-mattermost-webhook:8066/hooks/builds}"

for _ in $(seq 1 120); do
  if curl -fsS "$FORMBRICKS_URL/api/health" >/dev/null; then
    break
  fi
  sleep 2
done

mkdir -p /tmp/formbricks

cat > /tmp/formbricks/client-project-intake.json <<'JSON'
{
  "name": "Client Project Intake",
  "questions": [
    {"label": "Company name", "type": "text", "required": true},
    {"label": "Contact email", "type": "email", "required": true},
    {"label": "Contact name", "type": "text", "required": true},
    {"label": "Project description", "type": "textarea", "required": true, "description": "Describe what you want built in plain English"},
    {"label": "Project type", "type": "select", "options": ["web application", "API/backend", "mobile app", "data pipeline", "AI integration", "full platform", "other"]},
    {"label": "Budget range", "type": "select", "options": ["under $5K", "$5-15K", "$15-50K", "$50-100K", "$100K+", "not sure"]},
    {"label": "Timeline", "type": "select", "options": ["ASAP", "1-2 weeks", "1 month", "2-3 months", "flexible"]},
    {"label": "Technical requirements", "type": "multiselect", "options": ["authentication", "database", "file storage", "payment processing", "AI/ML features", "real-time updates", "third-party integrations", "none specific"]},
    {"label": "Existing codebase?", "type": "select", "options": ["starting from scratch", "have existing code to extend", "need to integrate with existing systems"]},
    {"label": "How did you hear about us?", "type": "select", "options": ["referral", "search", "social media", "conference", "other"]}
  ],
  "webhookUrl": "http://omni-n8n:5678/webhook/client-intake"
}
JSON

cat > /tmp/formbricks/project-feedback-survey.json <<'JSON'
{
  "name": "Project Feedback Survey",
  "questions": [
    {"label": "Overall satisfaction", "type": "nps"},
    {"label": "Code quality rating", "type": "stars", "scale": 5},
    {"label": "Communication rating", "type": "stars", "scale": 5},
    {"label": "Timeline adherence", "type": "select", "options": ["ahead of schedule", "on time", "slightly delayed", "significantly delayed"]},
    {"label": "Would you recommend us?", "type": "select", "options": ["yes", "no", "maybe"]},
    {"label": "What went well?", "type": "textarea"},
    {"label": "What could be improved?", "type": "textarea"},
    {"label": "Interested in future projects?", "type": "select", "options": ["yes", "no"]}
  ],
  "webhookUrl": "http://omni-n8n:5678/webhook/project-feedback"
}
JSON

cat > /tmp/formbricks/deliverable-review.json <<'JSON'
{
  "name": "Deliverable Review",
  "questions": [
    {"label": "Which deliverable are you reviewing?", "type": "text"},
    {"label": "Does it meet requirements?", "type": "select", "options": ["exceeds", "meets", "partially meets", "does not meet"]},
    {"label": "Specific issues found", "type": "textarea", "required": false},
    {"label": "Approval decision", "type": "select", "options": ["approve", "approve with minor changes", "request revisions", "reject"]},
    {"label": "Revision details", "type": "textarea", "conditional": {"field": "Approval decision", "in": ["request revisions", "reject"]}}
  ],
  "webhookUrl": "http://omni-n8n:5678/webhook/deliverable-review"
}
JSON

cat > /tmp/formbricks/platform-config.md <<CFG
# Formbricks Platform Config

- Admin: ${FORMBRICKS_ADMIN_NAME} <${FORMBRICKS_ADMIN_EMAIL}>
- Authentik SSO: configure OIDC provider with redirect ${FORMBRICKS_URL}/api/auth/callback
- Embed target: client portal pages should use Formbricks web embed snippet by survey id.
- Submission notifications: route to SMTP ${FORMBRICKS_URL} via listmonk relay.
CFG

if [[ -z "$FORMBRICKS_API_KEY" ]]; then
  echo "[formbricks-init] FORMBRICKS_API_KEY missing; templates prepared under /tmp/formbricks for manual import."
else
  existing="$(curl -fsS -H "Authorization: Bearer $FORMBRICKS_API_KEY" "$FORMBRICKS_URL/api/v1/surveys" || echo '{}')"
  for f in /tmp/formbricks/*.json; do
    name="$(python -c 'import json,sys; print(json.load(open(sys.argv[1]))["name"])' "$f")"
    if echo "$existing" | grep -q "$name"; then
      echo "[formbricks-init] survey exists: $name (skip)"
      continue
    fi
    curl -fsS -X POST "$FORMBRICKS_URL/api/v1/surveys" \
      -H "Authorization: Bearer $FORMBRICKS_API_KEY" \
      -H "Content-Type: application/json" \
      --data-binary "@$f" >/dev/null || true
  done
fi

curl -fsS -X POST "$MM_WEBHOOK" -H 'Content-Type: application/json' \
  -d '{"text":"[formbricks-init] feedback forms configured (templates + webhook endpoints + admin docs)"}' || true

echo "[formbricks-init] completed"
