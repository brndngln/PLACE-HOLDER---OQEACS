import httpx
import structlog
from pydantic import BaseModel
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class CraterClient:
    def __init__(
        self,
        base_url: str = "http://omni-crater:80/api/v1",
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

    def list_invoices(self, status: str | None = None) -> list:
        params = {"status": status} if status else {}
        return self._get("/invoices", **params).get("data", [])

    def create_invoice(self, customer_id: str, items: list, template: str = "standard", **kw) -> dict:
        payload = {"customer_id": customer_id, "items": items, "template": template, **kw}
        return self._post("/invoices", payload)

    def send_invoice(self, invoice_id: str) -> dict:
        return self._post(f"/invoices/{invoice_id}/send", {})

    def get_invoice(self, invoice_id: str) -> dict:
        return self._get(f"/invoices/{invoice_id}")

    def mark_paid(self, invoice_id: str, payment_date: str, method: str) -> dict:
        return self._post(f"/invoices/{invoice_id}/payments", {
            "payment_date": payment_date,
            "method": method,
        })

    def get_overdue(self) -> list:
        return self.list_invoices(status="OVERDUE")

    def invoice_summary(self) -> dict:
        invoices = self.list_invoices()
        total_invoiced = sum(i.get("total", 0) for i in invoices)
        total_paid = sum(i.get("total", 0) for i in invoices if i.get("status") == "PAID")
        total_outstanding = sum(i.get("total", 0) for i in invoices if i.get("status") in ("SENT", "OVERDUE"))
        total_overdue = sum(i.get("total", 0) for i in invoices if i.get("status") == "OVERDUE")
        return {
            "total_invoiced": total_invoiced,
            "total_paid": total_paid,
            "total_outstanding": total_outstanding,
            "total_overdue": total_overdue,
            "count": len(invoices),
        }
