from __future__ import annotations

import uuid

from src.models import ErrorPattern, IngestRequest
from src.services.pattern_matcher import PatternMatcher


class ErrorIngester:
    def __init__(self, store: dict[str, ErrorPattern], matcher: PatternMatcher) -> None:
        self.store = store
        self.matcher = matcher

    def ingest(self, req: IngestRequest) -> ErrorPattern:
        signature = self.matcher.compute_signature(req.error_message, req.traceback)
        existing = next((p for p in self.store.values() if p.pattern_signature == signature), None)
        if existing:
            existing.frequency += 1
            return existing

        pattern = ErrorPattern(
            id=str(uuid.uuid4()),
            language=req.language,
            error_type=req.error_message.split(":", 1)[0][:100],
            pattern_signature=signature,
            description=req.error_message,
            root_causes=["runtime exception"],
            frequency=1,
            fix_templates=["Add validation and targeted exception handling"],
        )
        self.store[pattern.id] = pattern
        return pattern
