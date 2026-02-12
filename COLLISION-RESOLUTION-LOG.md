# Collision Resolution Log

Last updated: 2026-02-12 05:22 UTC

## Phase 2 — Port Collision Remediation

- 4317: observability-otel -> host 9004; system-70-opentelemetry -> host 9006
- 4318: observability-otel -> host 9005; system-70-opentelemetry -> host 9007
- 9650: system-46-multi-agent-debate -> host 8358; temporal-orchestrator -> host 8359
- 9651: system-47-semantic-code-engine -> host 8330; observability-otel -> host 9008
- 9652: policy-engine -> host 8337; system-48-api-intelligence -> host 8338
- 9653: system-49-execution-verification -> host 8339; attestation-hub -> host 8340
- 9654: system-50-style-learner -> host 8335; database-design-intelligence -> host 8336; temporal-ui -> host 8362
- 9656: system-54-performance-engineering -> host 8357; observability-otel health -> host 9010
- 9670: system-70-opentelemetry -> host 9011; system-167-design-forge -> host 9602

## Phase 2 — Additional Deconfliction (2026-02-12 04:36 UTC)

- 8330: knowledge-freshness -> host 8361; mcp-pipeline -> host 8345
- 8335/8336/8337/8338: mcp-servers (orchestrator/knowledge/automation/financial) -> hosts 8346/8347/8348/8349
- 8335/8336/8337/8338: system-44 MCP servers -> hosts 8326/8327/8328/8329
- 8326/8327/8328/8329: tool-selector, mcp-package-registry, mcp-docs, mcp-schema -> hosts 8341/8342/8343/8344

## Phase 2 — Mixed Collision Remediation (2026-02-12 05:22 UTC)

- 8090 collision: crater -> host 3024 (internal 80); dast-penetration-testing kept 8090
- 8180 collision: karma -> host 9312 (internal 8180); crowdsec kept 8180
- 8181 collision: anomaly-detector -> host 9300 (internal 8181); opa host ports disabled (internal 8181)
- 9004 collision: portainer -> host 9026 (internal 9000); otel-collector kept 9004/9005
- 9622 collision: hallucination-detector -> host 8375 (internal 9622); cost-tracking kept 9622
- 9657 collision: dead-code-detection -> host 8376 (internal 9657)
- 9658 collision: agentic-sre-self-healing -> host 8377 (internal 9658)
- 9659 collision: domain-specific-intelligence -> host 8378 (internal 9659)
- 9662 collision: architecture-diagram-generation -> host 8379 (internal 9662)
- 9668 collision: data-validation-framework -> host 8382 (internal 9668)
- 9671 collision: visual-verification-agent -> host 8383 (internal 9671)
- 9672 collision: hallucinated-dependency-protection -> host 8384 (internal 9672)
- gate-engine-v2 -> host 8351 (internal 8351) to avoid 8361 collision with knowledge-freshness
- docker-compose.elite-72.yml: ports disabled for duplicated containers to prevent global collisions
