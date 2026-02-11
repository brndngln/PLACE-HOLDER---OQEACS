from __future__ import annotations

from src.models import GameDay, ResilienceReport


class GameDayManager:
    def __init__(self) -> None:
        self._gamedays: dict[str, GameDay] = {}
        self._results: dict[str, list[bool]] = {}

    def schedule_game_day(self, game_day: GameDay) -> GameDay:
        self._gamedays[game_day.id] = game_day
        return game_day

    def record_result(self, game_day_id: str, passed: bool) -> None:
        self._results.setdefault(game_day_id, []).append(passed)

    def generate_report(self, game_day_id: str, service: str = "platform") -> ResilienceReport:
        vals = self._results.get(game_day_id, [])
        total = len(vals)
        passed = sum(1 for v in vals if v)
        score = 0.0 if total == 0 else round((passed / total) * 100, 2)
        weaknesses = [] if score >= 80 else ["Steady state not maintained under all faults"]
        return ResilienceReport(service=service, experiments_run=total, experiments_passed=passed, resilience_score=score, weaknesses=weaknesses)
