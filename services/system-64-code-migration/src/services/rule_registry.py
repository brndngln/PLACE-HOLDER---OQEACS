from __future__ import annotations

from src.models import MigrationRule, SupportedMigration


class RuleRegistry:
    def __init__(self) -> None:
        self._rules: dict[tuple[str, str], list[MigrationRule]] = {
            ("python2", "python3"): [
                MigrationRule(from_pattern="print ", to_pattern="print(", description="Wrap print statements"),
                MigrationRule(from_pattern="xrange", to_pattern="range", description="xrange renamed to range"),
            ],
            ("react-class", "react-hooks"): [
                MigrationRule(from_pattern="class ", to_pattern="function ", description="Convert class component to function"),
                MigrationRule(from_pattern="this.state", to_pattern="useState", description="State hook migration", auto_applicable=False),
            ],
            ("express", "fastify"): [MigrationRule(from_pattern="app.get", to_pattern="fastify.get", description="Route registration API")],
            ("javascript", "typescript"): [MigrationRule(from_pattern="var ", to_pattern="let ", description="Prefer block scope")],
        }

    def get_rules(self, source: str, target: str) -> list[MigrationRule]:
        return self._rules.get((source, target), [])

    def add_rule(self, source: str, target: str, rule: MigrationRule) -> None:
        self._rules.setdefault((source, target), []).append(rule)

    def list_supported_migrations(self) -> list[SupportedMigration]:
        out: list[SupportedMigration] = []
        for (src, tgt), rules in self._rules.items():
            complexity = "high" if any(not r.auto_applicable for r in rules) else "medium"
            out.append(SupportedMigration(source=src, target=tgt, complexity=complexity, rule_count=len(rules)))
        return out
