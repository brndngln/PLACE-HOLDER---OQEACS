# Omni Social Media Command Center (System 39)

Production-ready FastAPI service for multi-platform social publishing, trend monitoring, competitor tracking, engagement queueing, analytics, and 100M follower strategy planning.

## Run

```bash
docker compose -f services/social-media/docker-compose.yml up -d --build
```

## Core Endpoints

- `POST /api/v1/accounts`
- `POST /api/v1/content/generate`
- `POST /api/v1/posts`
- `POST /api/v1/trends/scan`
- `GET /api/v1/analytics/dashboard`
- `POST /api/v1/strategy/100m-plan`

## Infra

- Port: `9641`
- Container: `omni-social-media`
- DB: `social_media_db` on `omni-gi-postgres`
- Redis: DB `17`
