# Architecture Decision Record (ADR) Template

## ADR-XXXX: [Short Title of Decision]

**Status**: Proposed | Accepted | Deprecated | Superseded by ADR-YYYY
**Date**: YYYY-MM-DD
**Deciders**: [List of people involved in the decision]
**Technical Story**: [Link to issue or task, if applicable]

---

## Context

[Describe the issue motivating this decision. What is the problem or requirement? What forces are at play? Include technical constraints, business requirements, and team capabilities.]

Example:
> We need to choose a pattern recommendation strategy for the Neo4j GraphRAG API. The current keyword-based approach has low precision (45% relevance rate). Token Infinity needs higher-quality pattern recommendations to build effective LLM prompts.

---

## Decision Drivers

- [Driver 1: e.g., "Recommendation precision must exceed 80%"]
- [Driver 2: e.g., "Solution must work within existing infrastructure (no new services)"]
- [Driver 3: e.g., "Latency budget is 500ms p99"]
- [Driver 4: e.g., "Must be maintainable by the current team"]

---

## Considered Options

### Option 1: [Name]

[Description of the option]

**Pros**:
- [Pro 1]
- [Pro 2]

**Cons**:
- [Con 1]
- [Con 2]

**Estimated Effort**: [T-shirt size: S/M/L/XL]

### Option 2: [Name]

[Description of the option]

**Pros**:
- [Pro 1]
- [Pro 2]

**Cons**:
- [Con 1]
- [Con 2]

**Estimated Effort**: [T-shirt size: S/M/L/XL]

### Option 3: [Name]

[Description of the option]

**Pros**:
- [Pro 1]
- [Pro 2]

**Cons**:
- [Con 1]
- [Con 2]

**Estimated Effort**: [T-shirt size: S/M/L/XL]

---

## Decision

[State the decision that was made. Be specific about what will be implemented.]

Example:
> We will use LiteLLM-based keyword extraction (Option 2) for pattern recommendations. The LiteLLM proxy extracts design pattern keywords from natural language task descriptions, which are then used to query the Neo4j fulltext index. Fallback to synonym-based extraction when LiteLLM is unavailable.

---

## Rationale

[Explain why this option was chosen over alternatives. Reference the decision drivers.]

Example:
> Option 2 provides the best balance of precision (estimated 85% relevance) and implementation effort (M). It leverages our existing LiteLLM infrastructure without adding new dependencies. The fallback mechanism ensures the API remains functional even if LiteLLM is temporarily unavailable.

---

## Consequences

### Positive
- [Positive consequence 1]
- [Positive consequence 2]

### Negative
- [Negative consequence 1]
- [Negative consequence 2]

### Risks
- [Risk 1 and mitigation strategy]
- [Risk 2 and mitigation strategy]

---

## Implementation Plan

1. [Step 1]
2. [Step 2]
3. [Step 3]

**Target completion**: YYYY-MM-DD
**Affected services**: [List of services that need changes]

---

## Validation

How will we verify this decision was correct?

- [Metric 1: e.g., "Monitor recommendation precision via Langfuse traces"]
- [Metric 2: e.g., "Track p99 latency stays under 500ms"]
- [Review date: e.g., "Re-evaluate after 30 days of production data"]

---

## References

- [Link to relevant documentation]
- [Link to related ADRs]
- [Link to technical specifications]

---

*Template version: 1.0 | Based on [MADR](https://adr.github.io/madr/) format*
