"""SDK client placeholder for continuous-learning-pipeline."""

from dataclasses import dataclass


@dataclass
class System98Client:
    base_url: str

    def health_url(self) -> str:
        return f"{self.base_url}/health"
