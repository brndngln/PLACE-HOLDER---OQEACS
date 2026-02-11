# System 51 - Continuous Profiling (Pyroscope)

Service codename: continuous-profiling-pyroscope

Endpoints:
- GET /health
- GET /ready
- GET /info
- GET /profiles
- GET /metrics

Run:

docker compose -f services/continuous-profiling-pyroscope/docker-compose.yml up -d --build

Default port:
4040
