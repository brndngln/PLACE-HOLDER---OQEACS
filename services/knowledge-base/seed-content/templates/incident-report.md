# Incident Report Template

## Incident Report: [Brief Title]

**Incident ID**: INC-YYYY-MMDD-NNN
**Severity**: SEV-1 | SEV-2 | SEV-3 | SEV-4
**Status**: Resolved | Monitoring | Open
**Date**: YYYY-MM-DD
**Duration**: HH:MM (start) — HH:MM (end) UTC = X hours Y minutes

---

## Summary

[1-2 sentence summary of what happened and the impact.]

Example:
> The Neo4j GraphRAG API became unresponsive for 45 minutes due to heap memory exhaustion, causing Token Infinity pattern recommendations to fail. Approximately 120 recommendation requests returned errors during the incident window.

---

## Timeline

| Time (UTC) | Event |
|------------|-------|
| HH:MM | [First alert triggered / Issue detected] |
| HH:MM | [Incident commander assigned] |
| HH:MM | [Root cause identified] |
| HH:MM | [Mitigation applied] |
| HH:MM | [Service restored] |
| HH:MM | [Monitoring confirmed stable] |
| HH:MM | [Incident closed] |

---

## Impact

### User Impact
- [Number of users/requests affected]
- [Which features were degraded or unavailable]
- [Duration of impact]

### System Impact
- [Which services were affected]
- [Were there cascading failures]
- [Data loss (if any)]

### Business Impact
- [Revenue impact (if applicable)]
- [SLA breach (if applicable)]
- [Client communication needed (if applicable)]

---

## Root Cause

[Detailed technical explanation of the root cause. Be specific.]

Example:
> The Neo4j container was configured with a 2GB heap limit (`NEO4J_server_memory_heap_max__size=2g`). After the pattern graph grew to 54 patterns with full relationships and code templates, complex traversal queries (particularly the recommendation endpoint's fulltext search combined with relationship expansion) exceeded available heap memory during concurrent requests. Neo4j's garbage collector entered a stop-the-world loop, causing all queries to time out.

---

## Detection

- **How was the issue detected?** [Alert / User report / Monitoring / Manual check]
- **Detection time**: [Time from incident start to detection]
- **Alert name**: [Name of alert that fired, if applicable]
- **Monitoring gap**: [Was there a gap in monitoring that delayed detection?]

---

## Response

### Actions Taken

1. [Action 1: e.g., "Restarted Neo4j container"]
2. [Action 2: e.g., "Increased heap to 4GB in docker-compose.yml"]
3. [Action 3: e.g., "Verified pattern count and query performance"]
4. [Action 4: e.g., "Monitored for 30 minutes to confirm stability"]

### What Worked
- [Effective response actions]

### What Didn't Work
- [Actions that were tried but didn't help, and why]

---

## Resolution

[What was done to resolve the issue.]

Example:
> Increased Neo4j heap allocation from 2GB to 4GB and page cache from 1GB to 2GB. Added a connection pool limit of 50 concurrent queries to the GraphRAG API to prevent query overload. Deployed changes and verified all endpoints responding within normal latency bounds.

---

## Contributing Factors

- [ ] **Configuration**: [Misconfiguration, resource limits too low]
- [ ] **Code**: [Bug, missing error handling, race condition]
- [ ] **Infrastructure**: [Hardware failure, network issue, disk full]
- [ ] **Deployment**: [Bad deploy, missing migration, config drift]
- [ ] **External**: [Third-party service outage, API changes]
- [ ] **Process**: [Missing runbook, unclear ownership, delayed response]

---

## Prevention

### Immediate Actions (within 1 week)

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | YYYY-MM-DD | [Done / In Progress / Pending] |
| [Action 2] | [Name] | YYYY-MM-DD | [Done / In Progress / Pending] |

### Long-Term Improvements (within 1 month)

| Action | Owner | Due Date | Status |
|--------|-------|----------|--------|
| [Action 1] | [Name] | YYYY-MM-DD | [Done / In Progress / Pending] |
| [Action 2] | [Name] | YYYY-MM-DD | [Done / In Progress / Pending] |

### Monitoring Improvements

| Improvement | Description |
|-------------|-------------|
| [New alert] | [What it monitors and threshold] |
| [New dashboard] | [What it visualizes] |
| [New health check] | [What it verifies] |

---

## Lessons Learned

### What went well
- [Positive aspect of the response]

### What could be improved
- [Area for improvement]

### Surprises
- [Anything unexpected that was learned]

---

## Responders

| Role | Name |
|------|------|
| Incident Commander | [Name] |
| Technical Lead | [Name] |
| Communicator | [Name] |
| Other | [Name] |

---

## Post-Mortem

- **Post-mortem meeting date**: YYYY-MM-DD
- **Attendees**: [List]
- **Recording/Notes**: [Link]

---

## References

- Related alerts: [Links to Grafana alerts]
- Related logs: [Links to Loki queries]
- Related traces: [Links to Langfuse traces]
- Related PRs: [Links to fix PRs]
- Related ADRs: [Links to architectural decisions]

---

*Template version: 1.0 | Complete within 48 hours of incident resolution for SEV-1/2.*
