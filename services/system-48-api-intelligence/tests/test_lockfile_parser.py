from __future__ import annotations

from src.services.lockfile_parser import LockfileParser


def test_parse_requirements_txt() -> None:
    parser = LockfileParser()
    out = parser.parse_requirements_txt("fastapi==0.115.6\nhttpx==0.28.1\n")
    assert ("fastapi", "0.115.6") in out


def test_parse_requirements_ignores_comments() -> None:
    parser = LockfileParser()
    out = parser.parse_requirements_txt("# comment\nuvicorn==0.34.0\n")
    assert out == [("uvicorn", "0.34.0")]


def test_parse_package_lock() -> None:
    parser = LockfileParser()
    payload = '{"packages": {"": {}, "node_modules/react": {"version": "18.2.0"}}}'
    out = parser.parse_package_lock(payload)
    assert ("react", "18.2.0") in out


def test_parse_cargo_lock() -> None:
    parser = LockfileParser()
    payload = '[[package]]\nname = "serde"\nversion = "1.0.215"\n'
    out = parser.parse_cargo_lock(payload)
    assert ("serde", "1.0.215") in out


def test_parse_go_sum() -> None:
    parser = LockfileParser()
    out = parser.parse_go_sum("github.com/gin-gonic/gin v1.10.0 h1:xyz\n")
    assert ("github.com/gin-gonic/gin", "1.10.0") in out
