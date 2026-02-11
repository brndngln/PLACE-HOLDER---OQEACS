from __future__ import annotations

from src.models import CLICommand


class CommandRegistry:
    def __init__(self) -> None:
        self._commands: dict[str, CLICommand] = {}
        self._seed()

    def _seed(self) -> None:
        self.register_command(CLICommand(name="generate", description="Generate code from prompt", arguments=["description"], examples=["omni generate 'build api'"]))
        self.register_command(CLICommand(name="review", description="Review file", arguments=["file_path"], examples=["omni review app.py"]))
        self.register_command(CLICommand(name="test", description="Generate/run tests", arguments=["file_path"]))
        self.register_command(CLICommand(name="debug", description="Debug error", arguments=["error"]))
        self.register_command(CLICommand(name="deploy", description="Trigger deploy", arguments=["target"]))
        self.register_command(CLICommand(name="status", description="Platform status"))
        self.register_command(CLICommand(name="explain", description="Explain code", arguments=["file_path"]))
        self.register_command(CLICommand(name="migrate", description="Run migration", arguments=["source", "target"]))

    def register_command(self, command: CLICommand) -> None:
        self._commands[command.name] = command

    def get_command(self, name: str) -> CLICommand | None:
        return self._commands.get(name)

    def list_commands(self) -> list[CLICommand]:
        return sorted(self._commands.values(), key=lambda x: x.name)
