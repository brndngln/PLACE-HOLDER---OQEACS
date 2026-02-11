from __future__ import annotations

from src.models import MigrationRequest, MigrationResult
from src.services.rule_registry import RuleRegistry


class MigrationEngine:
    def __init__(self, registry: RuleRegistry | None = None) -> None:
        self.registry = registry or RuleRegistry()

    def migrate(self, request: MigrationRequest) -> MigrationResult:
        rules = self.registry.get_rules(request.source_framework, request.target_framework)
        if not rules:
            return MigrationResult(
                migrated_code=request.code,
                changes_made=[],
                breaking_changes=[f"Unsupported migration {request.source_framework}->{request.target_framework}"],
                manual_review_needed=["No automatic rules available"],
            )

        migrated = request.code
        changes: list[str] = []
        manual: list[str] = []

        for rule in rules:
            if rule.from_pattern in migrated:
                if rule.auto_applicable:
                    migrated = migrated.replace(rule.from_pattern, rule.to_pattern)
                    changes.append(rule.description)
                else:
                    manual.append(rule.description)

        breaking = ["Potential runtime behavior drift"] if manual else []
        return MigrationResult(migrated_code=migrated, changes_made=changes, breaking_changes=breaking, manual_review_needed=manual)
