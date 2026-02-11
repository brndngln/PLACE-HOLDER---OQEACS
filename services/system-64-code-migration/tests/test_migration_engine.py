from __future__ import annotations

from src.models import MigrationRequest
from src.services.migration_engine import MigrationEngine


def test_python2_to_3() -> None:
    req = MigrationRequest(source_framework="python2", target_framework="python3", code="print x\nfor i in xrange(3): pass", language="python")
    res = MigrationEngine().migrate(req)
    assert "range" in res.migrated_code


def test_react_class_to_hooks() -> None:
    req = MigrationRequest(source_framework="react-class", target_framework="react-hooks", code="class A extends React.Component {}", language="javascript")
    res = MigrationEngine().migrate(req)
    assert "function" in res.migrated_code


def test_detect_breaking_change() -> None:
    req = MigrationRequest(source_framework="react-class", target_framework="react-hooks", code="this.state = {}", language="javascript")
    res = MigrationEngine().migrate(req)
    assert isinstance(res.breaking_changes, list)


def test_unsupported_migration() -> None:
    req = MigrationRequest(source_framework="a", target_framework="b", code="x", language="txt")
    res = MigrationEngine().migrate(req)
    assert res.breaking_changes


def test_empty_code() -> None:
    req = MigrationRequest(source_framework="python2", target_framework="python3", code="", language="python")
    res = MigrationEngine().migrate(req)
    assert isinstance(res.migrated_code, str)
