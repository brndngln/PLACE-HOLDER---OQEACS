from __future__ import annotations

import hashlib
from collections import OrderedDict

from src.models import BuildCache


class CacheManager:
    def __init__(self) -> None:
        self._cache: OrderedDict[str, BuildCache] = OrderedDict()

    def compute_file_hash(self, content: str) -> str:
        return hashlib.sha256(content.encode()).hexdigest()

    def store_artifact(self, file_hash: str, artifact_path: str) -> BuildCache:
        item = BuildCache(id=file_hash[:16], file_hash=file_hash, artifact_path=artifact_path)
        self._cache[file_hash] = item
        self._cache.move_to_end(file_hash)
        return item

    def get_artifact(self, file_hash: str) -> BuildCache | None:
        item = self._cache.get(file_hash)
        if item:
            item.hit_count += 1
            self._cache.move_to_end(file_hash)
        return item

    def invalidate(self, file_hash: str) -> bool:
        return self._cache.pop(file_hash, None) is not None

    def evict_lru(self, max_items: int = 1000) -> int:
        removed = 0
        while len(self._cache) > max_items:
            self._cache.popitem(last=False)
            removed += 1
        return removed

    def get_cache_stats(self) -> dict[str, float]:
        total = len(self._cache)
        hits = sum(x.hit_count for x in self._cache.values())
        return {"items": total, "total_hits": hits}
