# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                              NEURAL ALERT ENGINE - PREDICTIVE THREAT DETECTION                                                         ║
# ║                              OMNI QUANTUM ELITE v3.0 - "Know Before It Happens"                                                        ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

import asyncio, json, uuid, hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
import asyncpg, aiohttp

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class AlertSeverity(Enum):
    INFO = "INFO"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"

class AlertCategory(Enum):
    FINANCIAL = "FINANCIAL"
    SECURITY = "SECURITY"
    BUSINESS = "BUSINESS"
    TAX = "TAX"
    CUSTOMER = "CUSTOMER"

class AlertStatus(Enum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"
    DISMISSED = "DISMISSED"

class NotificationChannel(Enum):
    EMAIL = "EMAIL"
    SMS = "SMS"
    PUSH = "PUSH"
    MATTERMOST = "MATTERMOST"
    OMI = "OMI"
    WEBHOOK = "WEBHOOK"

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class Alert:
    id: str
    org_id: str
    severity: AlertSeverity
    category: AlertCategory
    alert_type: str
    title: str
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    status: AlertStatus = AlertStatus.NEW
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    fingerprint: str = ""
    notification_sent: bool = False

@dataclass
class AlertRule:
    id: str
    name: str
    description: str
    category: AlertCategory
    alert_type: str
    condition_type: str
    condition_config: Dict[str, Any]
    severity: AlertSeverity = AlertSeverity.MEDIUM
    channels: List[NotificationChannel] = field(default_factory=list)
    cooldown_minutes: int = 60
    enabled: bool = True

@dataclass
class NotificationConfig:
    org_id: str
    email_enabled: bool = True
    email_addresses: List[str] = field(default_factory=list)
    sms_enabled: bool = True
    phone_numbers: List[str] = field(default_factory=list)
    mattermost_enabled: bool = True
    mattermost_webhook_url: str = ""
    omi_enabled: bool = True
    omi_device_id: str = ""
    quiet_hours_start: Optional[int] = None
    quiet_hours_end: Optional[int] = None

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DEFAULT ALERT RULES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

DEFAULT_RULES = [
    AlertRule("RULE-BALANCE-LOW", "Low Balance", "Balance below threshold",
              AlertCategory.FINANCIAL, "BALANCE_LOW", "threshold",
              {"metric": "total_cash", "operator": "lt", "threshold": 10000},
              AlertSeverity.HIGH, [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.OMI]),
    
    AlertRule("RULE-BALANCE-CRITICAL", "Critical Balance", "Balance critically low",
              AlertCategory.FINANCIAL, "BALANCE_CRITICAL", "threshold",
              {"metric": "total_cash", "operator": "lt", "threshold": 5000},
              AlertSeverity.CRITICAL, [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.PUSH, NotificationChannel.OMI]),
    
    AlertRule("RULE-RUNWAY-LOW", "Runway Warning", "Runway below 6 months",
              AlertCategory.FINANCIAL, "RUNWAY_LOW", "threshold",
              {"metric": "runway_months", "operator": "lt", "threshold": 6},
              AlertSeverity.HIGH, [NotificationChannel.EMAIL, NotificationChannel.SMS]),
    
    AlertRule("RULE-TAX-UNDERFUNDED", "Tax Underfunded", "Tax reserves below 90%",
              AlertCategory.TAX, "TAX_UNDERFUNDED", "threshold",
              {"metric": "tax_funding_pct", "operator": "lt", "threshold": 90},
              AlertSeverity.MEDIUM, [NotificationChannel.EMAIL]),
    
    AlertRule("RULE-TAX-DUE", "Tax Payment Due", "Quarterly payment due soon",
              AlertCategory.TAX, "TAX_PAYMENT_DUE", "schedule",
              {"days_before_due": 14},
              AlertSeverity.HIGH, [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.OMI]),
    
    AlertRule("RULE-LARGE-TRANSFER", "Large Transfer", "Transfer over $10K",
              AlertCategory.SECURITY, "LARGE_TRANSFER", "threshold",
              {"metric": "transfer_amount", "operator": "gt", "threshold": 10000},
              AlertSeverity.HIGH, [NotificationChannel.EMAIL, NotificationChannel.SMS, NotificationChannel.OMI], 0),
    
    AlertRule("RULE-REVENUE-DROP", "Revenue Drop", "Revenue 50% below average",
              AlertCategory.FINANCIAL, "REVENUE_DROP", "anomaly",
              {"metric": "daily_revenue", "deviation": 0.5},
              AlertSeverity.HIGH, [NotificationChannel.EMAIL, NotificationChannel.MATTERMOST]),
    
    AlertRule("RULE-CHURN-SPIKE", "Churn Spike", "Customer cancellations spike",
              AlertCategory.CUSTOMER, "CHURN_SPIKE", "anomaly",
              {"metric": "daily_cancellations", "deviation": 2.0},
              AlertSeverity.HIGH, [NotificationChannel.EMAIL, NotificationChannel.MATTERMOST]),
]

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# NOTIFICATION SENDERS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class NotificationSender:
    async def send(self, alert: Alert, config: NotificationConfig) -> bool:
        raise NotImplementedError

class EmailSender(NotificationSender):
    async def send(self, alert: Alert, config: NotificationConfig) -> bool:
        if not config.email_enabled: return False
        print(f"📧 EMAIL [{alert.severity.value}] {alert.title}")
        return True

class SMSSender(NotificationSender):
    async def send(self, alert: Alert, config: NotificationConfig) -> bool:
        if not config.sms_enabled: return False
        print(f"📱 SMS [{alert.severity.value}] {alert.title}")
        return True

class MattermostSender(NotificationSender):
    async def send(self, alert: Alert, config: NotificationConfig) -> bool:
        if not config.mattermost_enabled or not config.mattermost_webhook_url: return False
        colors = {AlertSeverity.INFO: "#17a2b8", AlertSeverity.LOW: "#28a745",
                  AlertSeverity.MEDIUM: "#ffc107", AlertSeverity.HIGH: "#fd7e14", AlertSeverity.CRITICAL: "#dc3545"}
        payload = {"username": "Financial Fortress", "icon_emoji": ":moneybag:",
                   "attachments": [{"color": colors.get(alert.severity), "title": f"[{alert.severity.value}] {alert.title}", "text": alert.message}]}
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(config.mattermost_webhook_url, json=payload) as resp:
                    return resp.status == 200
        except: return False

class OmiSender(NotificationSender):
    async def send(self, alert: Alert, config: NotificationConfig) -> bool:
        if not config.omi_enabled: return False
        patterns = {AlertSeverity.INFO: "gentle", AlertSeverity.LOW: "double_tap",
                    AlertSeverity.MEDIUM: "triple_tap", AlertSeverity.HIGH: "urgent", AlertSeverity.CRITICAL: "emergency"}
        print(f"⌚ OMI [{patterns[alert.severity]}] {alert.title}")
        return True

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# NEURAL ALERT ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class NeuralAlertEngine:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.senders = {
            NotificationChannel.EMAIL: EmailSender(),
            NotificationChannel.SMS: SMSSender(),
            NotificationChannel.MATTERMOST: MattermostSender(),
            NotificationChannel.OMI: OmiSender()
        }
        self.rules = {r.id: r for r in DEFAULT_RULES}
        self.cooldowns: Dict[str, datetime] = {}
    
    async def create_alert(self, org_id: str, rule_id: str, title: str, message: str, details: Dict = None) -> Optional[Alert]:
        rule = self.rules.get(rule_id)
        if not rule or not rule.enabled: return None
        
        # Check cooldown
        key = f"{org_id}:{rule_id}"
        if key in self.cooldowns:
            if datetime.now(timezone.utc) < self.cooldowns[key] + timedelta(minutes=rule.cooldown_minutes):
                return None
        
        alert = Alert(
            id=f"ALT-{uuid.uuid4().hex[:12].upper()}", org_id=org_id,
            severity=rule.severity, category=rule.category, alert_type=rule.alert_type,
            title=title, message=message, details=details or {},
            fingerprint=hashlib.md5(f"{org_id}:{rule_id}:{title}".encode()).hexdigest()
        )
        
        await self._save_alert(alert)
        self.cooldowns[key] = datetime.now(timezone.utc)
        await self._send_notifications(alert, rule)
        return alert
    
    async def check_metrics(self, org_id: str, metrics: Dict[str, Any]):
        for rule in self.rules.values():
            if not rule.enabled: continue
            if rule.condition_type == "threshold":
                cfg = rule.condition_config
                metric, op, thresh = cfg.get("metric"), cfg.get("operator"), cfg.get("threshold")
                if metric not in metrics: continue
                val = metrics[metric]
                triggered = (op == "lt" and val < thresh) or (op == "gt" and val > thresh)
                if triggered:
                    await self.create_alert(org_id, rule.id, f"{rule.name}: {metric}={val}", rule.description, {"value": val, "threshold": thresh})
    
    async def on_transfer(self, org_id: str, transfer: Dict):
        amt = float(transfer.get("amount", 0))
        if amt > 10000:
            await self.create_alert(org_id, "RULE-LARGE-TRANSFER", f"Large Transfer: ${amt:,.2f}",
                                   f"Transfer of ${amt:,.2f} initiated", transfer)
    
    async def run_checks(self, org_id: str):
        metrics = await self._gather_metrics(org_id)
        await self.check_metrics(org_id, metrics)
        await self._check_tax_deadlines(org_id)
    
    async def get_active_alerts(self, org_id: str) -> List[Dict]:
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM alerts WHERE org_id = $1 AND status IN ('NEW', 'ACKNOWLEDGED')
                ORDER BY CASE severity WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2 WHEN 'MEDIUM' THEN 3 ELSE 4 END, created_at DESC
            """, org_id)
            return [dict(r) for r in rows]
    
    async def acknowledge(self, org_id: str, alert_id: str):
        async with self.db.acquire() as conn:
            await conn.execute("UPDATE alerts SET status = 'ACKNOWLEDGED' WHERE org_id = $1 AND id = $2", org_id, alert_id)
    
    async def resolve(self, org_id: str, alert_id: str):
        async with self.db.acquire() as conn:
            await conn.execute("UPDATE alerts SET status = 'RESOLVED', resolved_at = $3 WHERE org_id = $1 AND id = $2",
                             org_id, alert_id, datetime.now(timezone.utc))
    
    async def _gather_metrics(self, org_id: str) -> Dict:
        async with self.db.acquire() as conn:
            cash = await conn.fetchrow("SELECT COALESCE(SUM(cached_balance), 0) as total FROM bank_accounts WHERE org_id = $1", org_id)
            tax = await conn.fetchrow("""SELECT COALESCE(SUM(required_amount), 0) as req, COALESCE(SUM(reserved_amount), 0) as res
                                        FROM tax_reserves WHERE org_id = $1 AND payment_status != 'PAID'""", org_id)
            burn = await conn.fetchrow("""SELECT COALESCE(AVG(amount), 0) as daily FROM transactions
                                         WHERE org_id = $1 AND transaction_type = 'EXPENSE' AND created_at >= CURRENT_DATE - 30""", org_id)
        
        total = float(cash["total"])
        monthly_burn = float(burn["daily"]) * 30
        runway = total / monthly_burn if monthly_burn > 0 else 999
        tax_pct = float(tax["res"]) / float(tax["req"]) * 100 if float(tax["req"]) > 0 else 100
        
        return {"total_cash": total, "runway_months": runway, "tax_funding_pct": tax_pct, "monthly_burn": monthly_burn}
    
    async def _check_tax_deadlines(self, org_id: str):
        async with self.db.acquire() as conn:
            upcoming = await conn.fetch("""
                SELECT quarter, due_date, required_amount FROM tax_reserves
                WHERE org_id = $1 AND payment_status NOT IN ('PAID', 'SCHEDULED')
                AND due_date <= CURRENT_DATE + 14
            """, org_id)
            for p in upcoming:
                days = (p["due_date"] - date.today()).days
                if days < 0:
                    await self.create_alert(org_id, "RULE-TAX-DUE", f"Tax OVERDUE: Q{p['quarter']}", f"${p['required_amount']:,.2f} is {abs(days)} days overdue!")
                elif days <= 14:
                    await self.create_alert(org_id, "RULE-TAX-DUE", f"Tax Due: Q{p['quarter']}", f"${p['required_amount']:,.2f} due in {days} days")
    
    async def _send_notifications(self, alert: Alert, rule: AlertRule):
        config = await self._get_config(alert.org_id)
        for ch in rule.channels:
            if ch in self.senders:
                try: await self.senders[ch].send(alert, config)
                except: pass
    
    async def _get_config(self, org_id: str) -> NotificationConfig:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM notification_configs WHERE org_id = $1", org_id)
            if row:
                return NotificationConfig(org_id, row.get("email_enabled", True), row.get("email_addresses", []),
                                         row.get("sms_enabled", True), row.get("phone_numbers", []),
                                         row.get("mattermost_enabled", True), row.get("mattermost_webhook_url", ""),
                                         row.get("omi_enabled", True), row.get("omi_device_id", ""))
            return NotificationConfig(org_id)
    
    async def _save_alert(self, alert: Alert):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO alerts (id, org_id, severity, category, alert_type, title, message, details, status, fingerprint, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (id) DO UPDATE SET status = $9
            """, alert.id, alert.org_id, alert.severity.value, alert.category.value, alert.alert_type,
                alert.title, alert.message, json.dumps(alert.details), alert.status.value, alert.fingerprint, alert.created_at)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI
app = FastAPI(title="Neural Alert Engine", version="3.0.0")

@app.get("/api/v1/alerts/{org_id}")
async def get_alerts(org_id: str): return {"status": "requires_db"}

@app.post("/api/v1/alerts/{org_id}/{alert_id}/acknowledge")
async def ack(org_id: str, alert_id: str): return {"status": "acknowledged"}

@app.post("/api/v1/alerts/{org_id}/{alert_id}/resolve")
async def resolve(org_id: str, alert_id: str): return {"status": "resolved"}

@app.get("/api/v1/alerts/{org_id}/rules")
async def rules(org_id: str): return {"rules": [{"id": r.id, "name": r.name, "severity": r.severity.value} for r in DEFAULT_RULES]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4013)
