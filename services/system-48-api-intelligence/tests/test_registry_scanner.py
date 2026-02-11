from __future__ import annotations

import pytest

from src.services.registry_scanner import RegistryScanner


@pytest.mark.anyio
async def test_version_compare_newer() -> None:
    scanner = RegistryScanner()
    assert scanner._version_is_newer("0.1.0", "0.2.0") is True
    await scanner.close()


@pytest.mark.anyio
async def test_version_compare_same() -> None:
    scanner = RegistryScanner()
    assert scanner._version_is_newer("1.0.0", "1.0.0") is False
    await scanner.close()


@pytest.mark.anyio
async def test_parse_changelog_fallback() -> None:
    scanner = RegistryScanner()
    out = await scanner._parse_changelog("breaking change: removed x", "1.0.0", "2.0.0", "demo")
    assert isinstance(out, list)
    await scanner.close()


@pytest.mark.anyio
async def test_scan_all_empty() -> None:
    scanner = RegistryScanner()
    out = await scanner.scan_all([])
    assert out == []
    await scanner.close()


@pytest.mark.anyio
async def test_security_check_handles_unknown() -> None:
    scanner = RegistryScanner()
    advisories = await scanner._check_security("nonexistent-package", "pypi")
    assert isinstance(advisories, list)
    await scanner.close()


@pytest.mark.anyio
async def test_invalid_versions_safe() -> None:
    scanner = RegistryScanner()
    assert scanner._version_is_newer("bad", "also-bad") is False
    await scanner.close()
