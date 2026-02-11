# System 134 - Search Engine Meilisearch

Service codename: search-engine-meilisearch

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-134-search-engine-meilisearch/docker-compose.yml up -d --build

Default port:
10134
