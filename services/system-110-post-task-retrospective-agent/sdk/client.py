"""SDK client placeholder for post-task-retrospective-agent."""

from dataclasses import dataclass


@dataclass
class System110Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
