from __future__ import annotations

from src.services.cache_manager import CacheManager


def test_store_and_get() -> None:
    c = CacheManager()
    h = c.compute_file_hash("abc")
    c.store_artifact(h, "/tmp/a")
    assert c.get_artifact(h) is not None


def test_invalidate() -> None:
    c = CacheManager()
    h = c.compute_file_hash("abc")
    c.store_artifact(h, "/tmp/a")
    assert c.invalidate(h) is True


def test_evict_lru() -> None:
    c = CacheManager()
    for i in range(3):
        c.store_artifact(c.compute_file_hash(str(i)), f"/tmp/{i}")
    removed = c.evict_lru(max_items=1)
    assert removed == 2


def test_stats() -> None:
    c = CacheManager()
    stats = c.get_cache_stats()
    assert "items" in stats
