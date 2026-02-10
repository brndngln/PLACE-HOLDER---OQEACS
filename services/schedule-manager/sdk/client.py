import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CalcomClient:
    def __init__(
        self,
        base_url: str = "http://omni-calcom:3000/api/v1",
        api_token: str = "",
    ):
        self._client = httpx.Client(
            base_url=base_url,
            headers={"Authorization": f"Bearer {api_token}"},
            timeout=30.0,
        )

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _get(self, path: str, **params) -> dict:
        r = self._client.get(path, params=params)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _post(self, path: str, data: dict) -> dict:
        r = self._client.post(path, json=data)
        r.raise_for_status()
        return r.json()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    def _patch(self, path: str, data: dict) -> dict:
        r = self._client.patch(path, json=data)
        r.raise_for_status()
        return r.json()

    def list_bookings(self, status: str | None = None) -> list:
        params = {"status": status} if status else {}
        return self._get("/bookings", **params).get("bookings", [])

    def get_availability(self, date_range: dict) -> dict:
        return self._get("/availability", **date_range)

    def create_event_type(self, **kw) -> dict:
        return self._post("/event-types", kw)

    def list_event_types(self) -> list:
        return self._get("/event-types").get("event_types", [])

    def cancel_booking(self, booking_id: int, reason: str) -> dict:
        return self._post(f"/bookings/{booking_id}/cancel", {"reason": reason})
