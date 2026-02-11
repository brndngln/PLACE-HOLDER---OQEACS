# System 41: Formal Verification Engine

Mathematical proof of code correctness. Testing finds bugs; formal verification proves their absence. Wraps TLA+, CBMC, Dafny, SPIN, Alloy, CrossHair, and Kani behind a unified API.

## API

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | /api/v1/verify | Submit code for formal verification |
| GET | /api/v1/verify/{id} | Check verification status |
| GET | /api/v1/verify/{id}/report | Get human-readable report |
| POST | /api/v1/spec/generate | Generate spec from source code |
| GET | /api/v1/tools | List available verification tools |
| GET | /api/v1/proofs | List completed proofs |
| GET | /health | Health check |
| GET | /metrics | Prometheus metrics |

## Supported Tools

| Tool | Language | Purpose |
|------|----------|---------|
| CrossHair | Python | Symbolic execution, contract verification |
| CBMC | C/C++ | Bounded model checking, memory safety |
| Dafny | Dafny | Pre/post conditions, loop invariants |
| TLA+ | Protocol | Distributed protocol safety/liveness |
| SPIN | Protocol | Concurrent deadlock freedom |
| Kani | Rust | Bounded model checking |
| Alloy | Alloy | Relational modeling, constraints |

## Configuration

| Env Var | Default | Description |
|---------|---------|-------------|
| SERVICE_PORT | 9634 | Service port |
| DATABASE_URL | postgresql://... | PostgreSQL connection |
| REDIS_URL | redis://... | Redis for result caching |
| LITELLM_URL | http://omni-litellm:4000 | LLM for spec generation |
| VERIFICATION_TIMEOUT_SECONDS | 300 | Max verification time |
| WORK_DIR | /app/data/workdir | Temp directory for verification files |
