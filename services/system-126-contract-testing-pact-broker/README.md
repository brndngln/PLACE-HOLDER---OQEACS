# System 126 - Contract Testing Pact Broker

Service codename: contract-testing-pact-broker

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /metrics

Run:
docker compose -f services/system-126-contract-testing-pact-broker/docker-compose.yml up -d --build

Default port:
10126
