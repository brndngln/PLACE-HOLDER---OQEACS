from __future__ import annotations

from src.models import DependencyNode, DependencyTree
from src.services.license_checker import LicenseChecker


def test_license_default_unknown() -> None:
    tree = DependencyTree(id="1", nodes=[DependencyNode(name="x", version="1", ecosystem="pypi", direct=True)], edges=[], has_cycles=False)
    out = LicenseChecker().check_licenses(tree)
    assert out[0].license == "UNKNOWN"


def test_license_known_mapping() -> None:
    tree = DependencyTree(id="1", nodes=[DependencyNode(name="fastapi", version="1", ecosystem="pypi", direct=True)], edges=[], has_cycles=False)
    out = LicenseChecker().check_licenses(tree)
    assert out[0].license == "MIT"


def test_gpl_conflict_marks_incompatible() -> None:
    tree = DependencyTree(
        id="1",
        nodes=[
            DependencyNode(name="gpl-lib", version="1", ecosystem="pypi", direct=True),
            DependencyNode(name="fastapi", version="1", ecosystem="pypi", direct=True),
        ],
        edges=[],
        has_cycles=False,
    )
    out = LicenseChecker().check_licenses(tree)
    assert any(not x.compatible for x in out)


def test_returns_list() -> None:
    tree = DependencyTree(id="1", nodes=[], edges=[], has_cycles=False)
    assert isinstance(LicenseChecker().check_licenses(tree), list)
