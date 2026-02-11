# Omni Marketing Engine (System 38)

Production-ready FastAPI service for campaign orchestration, AI content generation, lead scoring, A/B testing, audience segmentation, competitor intelligence, and executive analytics.

## Run

```bash
docker compose -f services/marketing-engine/docker-compose.yml up -d --build
```

## Core Endpoints

- `POST /api/v1/campaigns`
- `POST /api/v1/content/generate/ad-copy`
- `POST /api/v1/leads`
- `POST /api/v1/ab-tests/{campaign_id}/create`
- `GET /api/v1/analytics/dashboard`
- `POST /api/v1/competitors/{id}/analyze`

## Infra

- Port: `9640`
- Container: `omni-marketing-engine`
- DB: `marketing_db` on `omni-gi-postgres`
- Redis: DB `16`
