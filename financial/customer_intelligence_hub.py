# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                              CUSTOMER INTELLIGENCE HUB - "Know Your Customers Deeply"                                                  ║
# ║                              OMNI QUANTUM ELITE v3.0                                                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

import asyncio, json, uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict
import asyncpg

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class CustomerStatus(Enum):
    LEAD = "LEAD"; TRIAL = "TRIAL"; ACTIVE = "ACTIVE"; AT_RISK = "AT_RISK"; CHURNED = "CHURNED"

class CustomerSegment(Enum):
    ENTERPRISE = "ENTERPRISE"; MID_MARKET = "MID_MARKET"; SMB = "SMB"; STARTUP = "STARTUP"

class ChurnRisk(Enum):
    LOW = "LOW"; MEDIUM = "MEDIUM"; HIGH = "HIGH"; CRITICAL = "CRITICAL"

class HealthScore(Enum):
    EXCELLENT = "EXCELLENT"; GOOD = "GOOD"; FAIR = "FAIR"; POOR = "POOR"; CRITICAL = "CRITICAL"

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 1: LTV CALCULATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class LTVCalculator:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def calculate_ltv(self, customer_id: str) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            customer = await conn.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
            revenue = await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) as total, MIN(created_at) as first, MAX(created_at) as last FROM transactions WHERE customer_id = $1 AND transaction_type = 'REVENUE'", customer_id)
        if not customer: return None
        total_revenue = Decimal(str(revenue["total"]))
        months_active = max(1, ((revenue["last"] - revenue["first"]).days / 30) if revenue["first"] and revenue["last"] else 1)
        avg_monthly = total_revenue / Decimal(str(months_active))
        
        async with self.db.acquire() as conn:
            churn = await conn.fetchrow("SELECT COUNT(*) FILTER (WHERE status = 'CHURNED') as churned, COUNT(*) as total FROM customers WHERE org_id = $1", customer["org_id"])
        churn_rate = max(Decimal(str(churn["churned"])) / max(Decimal(str(churn["total"])), Decimal("1")), Decimal("0.01"))
        avg_lifespan = Decimal("1") / churn_rate
        predicted_ltv = avg_monthly * avg_lifespan
        
        async with self.db.acquire() as conn:
            await conn.execute("UPDATE customers SET ltv = $1, total_revenue = $2 WHERE id = $3", float(predicted_ltv), float(total_revenue), customer_id)
        
        return {"customer_id": customer_id, "total_revenue": float(total_revenue), "months_active": float(months_active),
            "avg_monthly_revenue": float(avg_monthly), "predicted_ltv": float(predicted_ltv)}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 2: CHURN PREDICTION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ChurnPredictor:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def calculate_churn_risk(self, customer_id: str) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            customer = await conn.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
            events = await conn.fetch("SELECT * FROM customer_events WHERE customer_id = $1 ORDER BY occurred_at DESC LIMIT 100", customer_id)
        if not customer: return None
        
        risk_score, risk_factors = 0, []
        days_inactive = (datetime.now(timezone.utc) - customer["last_activity"]).days if customer["last_activity"] else 999
        if days_inactive > 30: risk_score += min(30, days_inactive - 30); risk_factors.append(f"Inactive {days_inactive} days")
        
        complaints = sum(1 for e in events if e["event_type"] in ["support_ticket", "complaint"])
        if complaints > 3: risk_score += min(20, complaints * 4); risk_factors.append(f"{complaints} complaints")
        
        failed = sum(1 for e in events if e["event_type"] == "payment_failed")
        if failed > 0: risk_score += min(15, failed * 5); risk_factors.append(f"{failed} failed payments")
        
        if customer["health_score"] < 50: risk_score += 10; risk_factors.append("Low health")
        
        risk_level = ChurnRisk.CRITICAL if risk_score >= 70 else ChurnRisk.HIGH if risk_score >= 50 else ChurnRisk.MEDIUM if risk_score >= 30 else ChurnRisk.LOW
        
        async with self.db.acquire() as conn:
            status = CustomerStatus.AT_RISK if risk_level in [ChurnRisk.HIGH, ChurnRisk.CRITICAL] else CustomerStatus.ACTIVE
            await conn.execute("UPDATE customers SET churn_risk = $1, status = $2 WHERE id = $3", risk_level.value, status.value, customer_id)
        
        return {"customer_id": customer_id, "risk_score": risk_score, "risk_level": risk_level.value,
            "risk_factors": risk_factors, "mrr_at_risk": float(customer["mrr"])}
    
    async def get_at_risk_customers(self, org_id: str) -> List[Dict]:
        async with self.db.acquire() as conn:
            customers = await conn.fetch("SELECT * FROM customers WHERE org_id = $1 AND churn_risk IN ('HIGH', 'CRITICAL') AND status != 'CHURNED' ORDER BY mrr DESC", org_id)
        return [{"id": c["id"], "name": c["name"], "mrr": float(c["mrr"]), "churn_risk": c["churn_risk"], "health_score": c["health_score"]} for c in customers]
    
    async def calculate_churn_rate(self, org_id: str, period_days: int = 30) -> Dict:
        async with self.db.acquire() as conn:
            start = await conn.fetchrow("SELECT COUNT(*) as count, COALESCE(SUM(mrr), 0) as mrr FROM customers WHERE org_id = $1 AND status != 'CHURNED'", org_id)
            churned = await conn.fetchrow("SELECT COUNT(*) as count, COALESCE(SUM(mrr), 0) as mrr FROM customers WHERE org_id = $1 AND status = 'CHURNED' AND churned_at >= CURRENT_DATE - $2", org_id, period_days)
        return {"customer_churn_rate": round((churned["count"] or 0) / max(start["count"], 1) * 100, 2),
            "revenue_churn_rate": round(float(churned["mrr"]) / max(float(start["mrr"]), 1) * 100, 2), "mrr_lost": float(churned["mrr"])}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 3: COHORT ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class CohortAnalyzer:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def generate_cohort_analysis(self, org_id: str, months: int = 12) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            customers = await conn.fetch(f"SELECT id, mrr, status, acquired_at, churned_at, DATE_TRUNC('month', acquired_at) as cohort_month FROM customers WHERE org_id = $1 AND acquired_at >= CURRENT_DATE - INTERVAL '{months} months' ORDER BY acquired_at", org_id)
        
        cohorts = defaultdict(lambda: {"customers": [], "initial_count": 0, "initial_mrr": Decimal("0")})
        for c in customers:
            key = c["cohort_month"].strftime("%Y-%m")
            cohorts[key]["customers"].append(c)
            cohorts[key]["initial_count"] += 1
            cohorts[key]["initial_mrr"] += Decimal(str(c["mrr"]))
        
        results = []
        for cohort_month, data in sorted(cohorts.items()):
            cohort_start = datetime.strptime(cohort_month, "%Y-%m").date()
            months_since = (date.today().year - cohort_start.year) * 12 + (date.today().month - cohort_start.month)
            retention = {}
            for offset in range(min(months_since + 1, 12)):
                check = cohort_start + timedelta(days=30 * offset)
                active = sum(1 for c in data["customers"] if c["status"] != "CHURNED" or (c["churned_at"] and c["churned_at"].date() > check))
                retention[f"M{offset}"] = round(active / data["initial_count"] * 100, 1) if data["initial_count"] else 0
            results.append({"cohort": cohort_month, "initial_customers": data["initial_count"], "initial_mrr": float(data["initial_mrr"]), "retention": retention})
        
        return {"cohorts": results, "avg_retention_m3": sum(c["retention"].get("M3", 0) for c in results) / max(len(results), 1)}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 4: EXPANSION TRACKING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ExpansionTracker:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def track_mrr_movements(self, org_id: str, period_days: int = 30) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            new = await conn.fetchrow("SELECT COUNT(*) as count, COALESCE(SUM(mrr), 0) as mrr FROM customers WHERE org_id = $1 AND acquired_at >= CURRENT_DATE - $2", org_id, period_days)
            churned = await conn.fetchrow("SELECT COUNT(*) as count, COALESCE(SUM(mrr), 0) as mrr FROM customers WHERE org_id = $1 AND churned_at >= CURRENT_DATE - $2", org_id, period_days)
            changes = await conn.fetch("SELECT * FROM mrr_changes WHERE org_id = $1 AND changed_at >= CURRENT_DATE - $2", org_id, period_days)
        
        expansion = sum(Decimal(str(c["new_mrr"])) - Decimal(str(c["old_mrr"])) for c in changes if c["change_type"] == "EXPANSION")
        contraction = sum(Decimal(str(c["old_mrr"])) - Decimal(str(c["new_mrr"])) for c in changes if c["change_type"] == "CONTRACTION")
        new_mrr, churned_mrr = Decimal(str(new["mrr"])), Decimal(str(churned["mrr"]))
        
        return {"new": {"count": new["count"], "mrr": float(new_mrr)}, "expansion": float(expansion),
            "contraction": float(contraction), "churned": {"count": churned["count"], "mrr": float(churned_mrr)},
            "net_mrr": float(new_mrr + expansion - contraction - churned_mrr),
            "quick_ratio": float((new_mrr + expansion) / max(churned_mrr + contraction, Decimal("1")))}
    
    async def get_expansion_opportunities(self, org_id: str) -> List[Dict]:
        async with self.db.acquire() as conn:
            customers = await conn.fetch("SELECT * FROM customers WHERE org_id = $1 AND status = 'ACTIVE' AND health_score >= 70 ORDER BY mrr DESC LIMIT 20", org_id)
        return [{"id": c["id"], "name": c["name"], "mrr": float(c["mrr"]), "health_score": c["health_score"], "segment": c["segment"]} for c in customers]

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 5: HEALTH SCORING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class HealthScorer:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def calculate_health_score(self, customer_id: str) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            customer = await conn.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
            events = await conn.fetch("SELECT event_type, COUNT(*) as count FROM customer_events WHERE customer_id = $1 AND occurred_at >= CURRENT_DATE - 30 GROUP BY event_type", customer_id)
        if not customer: return None
        
        event_map = {e["event_type"]: e["count"] for e in events}
        score, factors = 50, []
        
        logins = event_map.get("login", 0)
        if logins >= 20: score += 25; factors.append("High activity")
        elif logins >= 10: score += 15
        elif logins < 5: score -= 10; factors.append("Low activity")
        
        if event_map.get("support_ticket", 0) > 5: score -= 15; factors.append("Many tickets")
        if event_map.get("payment_failed", 0) > 0: score -= 10; factors.append("Payment issues")
        
        score = max(0, min(100, score))
        health = HealthScore.EXCELLENT if score >= 80 else HealthScore.GOOD if score >= 60 else HealthScore.FAIR if score >= 40 else HealthScore.POOR if score >= 20 else HealthScore.CRITICAL
        
        async with self.db.acquire() as conn:
            await conn.execute("UPDATE customers SET health_score = $1 WHERE id = $2", score, customer_id)
        
        return {"customer_id": customer_id, "health_score": score, "health_level": health.value, "factors": factors}
    
    async def get_health_distribution(self, org_id: str) -> Dict:
        async with self.db.acquire() as conn:
            dist = await conn.fetch("SELECT CASE WHEN health_score >= 80 THEN 'EXCELLENT' WHEN health_score >= 60 THEN 'GOOD' WHEN health_score >= 40 THEN 'FAIR' ELSE 'POOR' END as level, COUNT(*) as count, COALESCE(SUM(mrr), 0) as mrr FROM customers WHERE org_id = $1 AND status = 'ACTIVE' GROUP BY level", org_id)
        return {"distribution": [{"level": d["level"], "count": d["count"], "mrr": float(d["mrr"])} for d in dist]}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class CustomerIntelligenceHub:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.ltv = LTVCalculator(db_pool)
        self.churn = ChurnPredictor(db_pool)
        self.cohorts = CohortAnalyzer(db_pool)
        self.expansion = ExpansionTracker(db_pool)
        self.health = HealthScorer(db_pool)
    
    async def get_customer_360(self, customer_id: str) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            customer = await conn.fetchrow("SELECT * FROM customers WHERE id = $1", customer_id)
            events = await conn.fetch("SELECT * FROM customer_events WHERE customer_id = $1 ORDER BY occurred_at DESC LIMIT 20", customer_id)
        if not customer: return None
        return {"customer": dict(customer), "ltv": await self.ltv.calculate_ltv(customer_id),
            "churn_risk": await self.churn.calculate_churn_risk(customer_id),
            "health": await self.health.calculate_health_score(customer_id), "recent_events": [dict(e) for e in events]}
    
    async def get_dashboard(self, org_id: str) -> Dict[str, Any]:
        async with self.db.acquire() as conn:
            totals = await conn.fetchrow("SELECT COUNT(*) as total, COUNT(*) FILTER (WHERE status = 'ACTIVE') as active, COALESCE(SUM(mrr) FILTER (WHERE status = 'ACTIVE'), 0) as mrr, COALESCE(AVG(ltv), 0) as avg_ltv, COALESCE(AVG(health_score), 0) as avg_health FROM customers WHERE org_id = $1", org_id)
        
        return {"totals": {"total": totals["total"], "active": totals["active"], "mrr": float(totals["mrr"]), "avg_ltv": float(totals["avg_ltv"]), "avg_health": float(totals["avg_health"])},
            "churn": await self.churn.calculate_churn_rate(org_id), "at_risk": await self.churn.get_at_risk_customers(org_id),
            "mrr_movements": await self.expansion.track_mrr_movements(org_id), "health_dist": await self.health.get_health_distribution(org_id),
            "expansion_opps": await self.expansion.get_expansion_opportunities(org_id)}
    
    async def record_event(self, org_id: str, customer_id: str, event_type: str, data: Dict = None):
        async with self.db.acquire() as conn:
            await conn.execute("INSERT INTO customer_events (id, org_id, customer_id, event_type, event_data, occurred_at) VALUES ($1,$2,$3,$4,$5,$6)",
                f"EVT-{uuid.uuid4().hex[:12]}", org_id, customer_id, event_type, json.dumps(data or {}), datetime.now(timezone.utc))
            await conn.execute("UPDATE customers SET last_activity = $1 WHERE id = $2", datetime.now(timezone.utc), customer_id)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

SCHEMA = """
ALTER TABLE customers ADD COLUMN IF NOT EXISTS segment VARCHAR(20) DEFAULT 'SMB';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS mrr DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS ltv DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_revenue DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS health_score INTEGER DEFAULT 100;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS churn_risk VARCHAR(20) DEFAULT 'LOW';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS last_activity TIMESTAMPTZ;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS acquired_at TIMESTAMPTZ;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS churned_at TIMESTAMPTZ;

CREATE TABLE IF NOT EXISTS customer_events (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), customer_id VARCHAR(50), event_type VARCHAR(100), event_data JSONB DEFAULT '{}', occurred_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS mrr_changes (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), customer_id VARCHAR(50), old_mrr DECIMAL(15,2), new_mrr DECIMAL(15,2), change_type VARCHAR(20), changed_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX IF NOT EXISTS idx_events_customer ON customer_events(customer_id, occurred_at);
"""

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI
app = FastAPI(title="Customer Intelligence Hub", version="3.0.0")

@app.get("/api/v1/customers/{org_id}/dashboard")
async def dashboard(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/customers/{org_id}/{customer_id}/360")
async def customer_360(org_id: str, customer_id: str): return {"status": "requires_db"}

@app.get("/api/v1/customers/{org_id}/{customer_id}/ltv")
async def ltv(org_id: str, customer_id: str): return {"status": "requires_db"}

@app.get("/api/v1/customers/{org_id}/{customer_id}/churn-risk")
async def churn(org_id: str, customer_id: str): return {"status": "requires_db"}

@app.get("/api/v1/customers/{org_id}/at-risk")
async def at_risk(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/customers/{org_id}/cohorts")
async def cohorts(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/customers/{org_id}/mrr-movements")
async def mrr(org_id: str): return {"status": "requires_db"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4024)
