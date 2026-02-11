from __future__ import annotations

from src.services.command_registry import CommandRegistry


def test_list_commands() -> None:
    cmds = CommandRegistry().list_commands()
    assert len(cmds) >= 8


def test_get_known_command() -> None:
    reg = CommandRegistry()
    assert reg.get_command("generate") is not None


def test_get_unknown_command() -> None:
    reg = CommandRegistry()
    assert reg.get_command("nope") is None


def test_register_command() -> None:
    reg = CommandRegistry()
    before = len(reg.list_commands())
    from src.models import CLICommand

    reg.register_command(CLICommand(name="x", description="y"))
    assert len(reg.list_commands()) == before + 1
