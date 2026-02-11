from __future__ import annotations

from collections import defaultdict, deque

from src.models import BuildPlan, DependencyGraph


class BuildPlanner:
    def plan_build(self, changed_files: list[str], dep_graph: DependencyGraph) -> BuildPlan:
        reverse = defaultdict(list)
        for src, dep in dep_graph.edges:
            reverse[dep].append(src)

        rebuild = set(changed_files)
        q = deque(changed_files)
        while q:
            cur = q.popleft()
            for parent in reverse.get(cur, []):
                if parent not in rebuild:
                    rebuild.add(parent)
                    q.append(parent)

        cached = [n for n in dep_graph.nodes if n not in rebuild]
        ratio = 0.0 if not dep_graph.nodes else len(cached) / len(dep_graph.nodes)
        saved = round(len(cached) * 0.8, 2)
        return BuildPlan(files_to_rebuild=sorted(rebuild), files_cached=sorted(cached), estimated_time_saved=saved, cache_hit_ratio=round(ratio, 3))
