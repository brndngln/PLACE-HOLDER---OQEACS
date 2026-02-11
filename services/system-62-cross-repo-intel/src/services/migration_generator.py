from __future__ import annotations

from src.models import ContractChange, ImpactMap, MigrationPlan


class MigrationGenerator:
    def generate_migrations(self, impact_map: ImpactMap, changes: list[ContractChange]) -> list[MigrationPlan]:
        plans: list[MigrationPlan] = []
        for svc in impact_map.affected_services:
            code = "\n".join(
                [
                    f"# Migration for {svc}",
                    "# 1. Update API client endpoints/methods",
                    "# 2. Adjust request/response model mapping",
                    "# 3. Add backward-compatible adapter if needed",
                ]
            )
            effort = "high" if impact_map.breaking_changes_count > 0 else "medium"
            plans.append(MigrationPlan(affected_service=svc, changes=changes, generated_code=code, estimated_effort=effort))
        return plans
