"""SDK client placeholder for realtime-websocket."""

from dataclasses import dataclass


@dataclass
class System138Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
