from __future__ import annotations

from collections import defaultdict, deque

from src.models import ContractChange, ImpactMap, ServiceGraph


class CrossRepoImpactAnalyzer:
    def analyze_impact(self, changed_service: str, changes: list[ContractChange], graph: ServiceGraph) -> ImpactMap:
        reverse = defaultdict(list)
        for src, dst in graph.edges:
            reverse[dst].append(src)

        q = deque([changed_service])
        seen = {changed_service}
        affected: list[str] = []
        while q:
            node = q.popleft()
            for consumer in reverse.get(node, []):
                if consumer in seen:
                    continue
                seen.add(consumer)
                affected.append(consumer)
                q.append(consumer)

        breaking_count = sum(1 for c in changes if c.breaking)
        return ImpactMap(
            changed_service=changed_service,
            affected_services=sorted(affected),
            total_consumers=len(affected),
            breaking_changes_count=breaking_count,
        )
