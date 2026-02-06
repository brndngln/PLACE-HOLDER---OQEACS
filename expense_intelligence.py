# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                              EXPENSE INTELLIGENCE - "Know Where Your Money Goes"                                                       ║
# ║                              OMNI QUANTUM ELITE v3.0                                                                                   ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

import asyncio, json, uuid, re
from dataclasses import dataclass, field
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional
from collections import defaultdict
import asyncpg

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ENUMS & CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ExpenseCategory(Enum):
    SOFTWARE = "SOFTWARE"; INFRASTRUCTURE = "INFRASTRUCTURE"; HOSTING = "HOSTING"
    PAYROLL = "PAYROLL"; CONTRACTORS = "CONTRACTORS"; ADVERTISING = "ADVERTISING"
    MARKETING = "MARKETING"; PAYMENT_PROCESSING = "PAYMENT_PROCESSING"
    LEGAL = "LEGAL"; ACCOUNTING = "ACCOUNTING"; EQUIPMENT = "EQUIPMENT"
    OFFICE = "OFFICE"; TRAVEL = "TRAVEL"; INSURANCE = "INSURANCE"; OTHER = "OTHER"

class SubscriptionStatus(Enum):
    ACTIVE = "ACTIVE"; CANCELLED = "CANCELLED"; PAUSED = "PAUSED"

class BudgetStatus(Enum):
    ON_TRACK = "ON_TRACK"; WARNING = "WARNING"; OVER_BUDGET = "OVER_BUDGET"

VENDOR_CATEGORIES = {
    ExpenseCategory.SOFTWARE: ["github", "gitlab", "atlassian", "notion", "slack", "zoom", "figma", "canva"],
    ExpenseCategory.INFRASTRUCTURE: ["aws", "amazon web services", "google cloud", "azure", "digitalocean", "heroku", "vercel"],
    ExpenseCategory.ADVERTISING: ["google ads", "facebook ads", "linkedin ads", "twitter ads"],
    ExpenseCategory.PAYMENT_PROCESSING: ["stripe", "paypal", "square", "wise", "mercury"],
    ExpenseCategory.ACCOUNTING: ["quickbooks", "xero", "freshbooks", "bench"],
}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class Vendor:
    id: str; org_id: str; name: str; normalized_name: str
    category: ExpenseCategory; is_subscription: bool = False
    total_spent: Decimal = Decimal("0"); transaction_count: int = 0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Subscription:
    id: str; org_id: str; vendor_id: str; name: str
    amount: Decimal = Decimal("0"); billing_cycle: str = "MONTHLY"
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE
    annual_cost: Decimal = Decimal("0"); usage_score: int = 100
    next_billing_date: Optional[date] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Budget:
    id: str; org_id: str; name: str
    category: Optional[ExpenseCategory] = None; department: Optional[str] = None
    amount: Decimal = Decimal("0"); spent: Decimal = Decimal("0")
    remaining: Decimal = Decimal("0"); percentage_used: Decimal = Decimal("0")
    status: BudgetStatus = BudgetStatus.ON_TRACK; alert_threshold: int = 80
    period_start: Optional[date] = None; period_end: Optional[date] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

@dataclass
class Expense:
    id: str; org_id: str; date: date; amount: Decimal; description: str
    category: ExpenseCategory; vendor_id: Optional[str] = None
    vendor_name: str = ""; department: Optional[str] = None
    tax_deductible: bool = True
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 1: VENDOR ANALYSIS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class VendorAnalyzer:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def process_expense(self, expense: Dict) -> Vendor:
        vendor_name = self._extract_vendor_name(expense.get("description", ""))
        normalized = self._normalize_vendor_name(vendor_name)
        vendor = await self._find_vendor(expense["org_id"], normalized)
        
        if not vendor:
            category = self._categorize_vendor(vendor_name, expense.get("description", ""))
            vendor = Vendor(
                id=f"VND-{uuid.uuid4().hex[:12].upper()}", org_id=expense["org_id"],
                name=vendor_name, normalized_name=normalized, category=category,
                total_spent=Decimal(str(expense["amount"])), transaction_count=1
            )
            await self._save_vendor(vendor)
        else:
            await self._update_vendor_stats(vendor["id"], expense)
        return vendor
    
    async def get_vendor_spend_report(self, org_id: str, start: date, end: date) -> Dict:
        async with self.db.acquire() as conn:
            vendors = await conn.fetch("""
                SELECT v.*, COALESCE(SUM(e.amount), 0) as period_spend
                FROM vendors v LEFT JOIN expenses e ON v.id = e.vendor_id AND e.date BETWEEN $2 AND $3
                WHERE v.org_id = $1 GROUP BY v.id ORDER BY period_spend DESC LIMIT 20
            """, org_id, start, end)
            by_cat = await conn.fetch("""
                SELECT category, SUM(amount) as total FROM expenses
                WHERE org_id = $1 AND date BETWEEN $2 AND $3 GROUP BY category ORDER BY total DESC
            """, org_id, start, end)
        return {"top_vendors": [dict(v) for v in vendors], "by_category": [dict(c) for c in by_cat]}
    
    async def detect_duplicate_vendors(self, org_id: str) -> List[Dict]:
        async with self.db.acquire() as conn:
            vendors = await conn.fetch("SELECT * FROM vendors WHERE org_id = $1", org_id)
        duplicates, checked = [], set()
        for i, v1 in enumerate(vendors):
            if v1["id"] in checked: continue
            similar = [{"vendor": dict(v2), "similarity": self._similarity(v1["normalized_name"], v2["normalized_name"])}
                       for v2 in vendors[i+1:] if v2["id"] not in checked and self._similarity(v1["normalized_name"], v2["normalized_name"]) > 0.8]
            if similar:
                duplicates.append({"primary": dict(v1), "duplicates": similar})
                checked.update(s["vendor"]["id"] for s in similar)
        return duplicates
    
    def _extract_vendor_name(self, desc: str) -> str:
        for prefix in ["payment to", "purchase at", "pos purchase"]:
            if desc.lower().startswith(prefix): desc = desc[len(prefix):].strip()
        return " ".join(desc.split()[:3]).title()
    
    def _normalize_vendor_name(self, name: str) -> str:
        normalized = re.sub(r'[^a-z0-9\s]', '', name.lower())
        for suffix in [" inc", " llc", " ltd", " corp"]:
            if normalized.endswith(suffix): normalized = normalized[:-len(suffix)]
        return normalized.strip()
    
    def _categorize_vendor(self, name: str, desc: str) -> ExpenseCategory:
        combined = (name + " " + desc).lower()
        for cat, keywords in VENDOR_CATEGORIES.items():
            if any(kw in combined for kw in keywords): return cat
        return ExpenseCategory.OTHER
    
    def _similarity(self, s1: str, s2: str) -> float:
        if not s1 or not s2: return 0
        set1, set2 = set(s1), set(s2)
        return len(set1 & set2) / len(set1 | set2) if set1 | set2 else 0
    
    async def _find_vendor(self, org_id: str, normalized: str):
        async with self.db.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM vendors WHERE org_id = $1 AND normalized_name = $2", org_id, normalized)
    
    async def _save_vendor(self, v: Vendor):
        async with self.db.acquire() as conn:
            await conn.execute("""INSERT INTO vendors (id, org_id, name, normalized_name, category, is_subscription, total_spent, transaction_count, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)""", v.id, v.org_id, v.name, v.normalized_name, v.category.value, v.is_subscription, float(v.total_spent), v.transaction_count, v.created_at)
    
    async def _update_vendor_stats(self, vendor_id: str, expense: Dict):
        async with self.db.acquire() as conn:
            await conn.execute("UPDATE vendors SET total_spent = total_spent + $1, transaction_count = transaction_count + 1 WHERE id = $2", float(expense["amount"]), vendor_id)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 2: SUBSCRIPTION TRACKER
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class SubscriptionTracker:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def detect_subscriptions(self, org_id: str) -> List[Subscription]:
        async with self.db.acquire() as conn:
            vendor_expenses = await conn.fetch("""
                SELECT vendor_id, vendor_name, array_agg(amount ORDER BY date) as amounts, array_agg(date ORDER BY date) as dates
                FROM expenses WHERE org_id = $1 AND vendor_id IS NOT NULL AND date >= CURRENT_DATE - 180
                GROUP BY vendor_id, vendor_name HAVING COUNT(*) >= 2
            """, org_id)
        
        detected = []
        for ve in vendor_expenses:
            amounts = [Decimal(str(a)) for a in ve["amounts"]]
            pattern = self._detect_pattern(amounts, ve["dates"])
            if pattern:
                sub = Subscription(id=f"SUB-{uuid.uuid4().hex[:12].upper()}", org_id=org_id, vendor_id=ve["vendor_id"],
                    name=ve["vendor_name"], amount=pattern["amount"], billing_cycle=pattern["cycle"],
                    annual_cost=self._annual_cost(pattern["amount"], pattern["cycle"]))
                await self._save_subscription(sub)
                detected.append(sub)
        return detected
    
    async def get_subscription_inventory(self, org_id: str) -> Dict:
        async with self.db.acquire() as conn:
            subs = await conn.fetch("SELECT s.*, v.name as vendor_name FROM subscriptions s JOIN vendors v ON s.vendor_id = v.id WHERE s.org_id = $1 AND s.status = 'ACTIVE' ORDER BY s.annual_cost DESC", org_id)
        
        total_annual = sum(Decimal(str(s["annual_cost"])) for s in subs)
        return {"total_subscriptions": len(subs), "total_monthly_cost": float(total_annual / 12), "total_annual_cost": float(total_annual),
            "subscriptions": [{"id": s["id"], "name": s["name"], "amount": float(s["amount"]), "billing_cycle": s["billing_cycle"], 
                "annual_cost": float(s["annual_cost"]), "usage_score": s["usage_score"]} for s in subs],
            "potential_savings": await self._identify_savings(org_id)}
    
    async def detect_unused(self, org_id: str) -> List[Dict]:
        async with self.db.acquire() as conn:
            return [dict(s) for s in await conn.fetch("SELECT * FROM subscriptions WHERE org_id = $1 AND status = 'ACTIVE' AND usage_score < 30", org_id)]
    
    async def get_renewals(self, org_id: str, days: int = 30) -> List[Dict]:
        async with self.db.acquire() as conn:
            return [dict(r) for r in await conn.fetch("SELECT * FROM subscriptions WHERE org_id = $1 AND status = 'ACTIVE' AND renewal_date <= CURRENT_DATE + $2 AND renewal_date >= CURRENT_DATE ORDER BY renewal_date", org_id, days)]
    
    def _detect_pattern(self, amounts: List[Decimal], dates: List[date]) -> Optional[Dict]:
        if len(amounts) < 2: return None
        avg = sum(amounts) / len(amounts)
        if sum(abs(a - avg) for a in amounts) / len(amounts) / avg > 0.1: return None
        intervals = [(dates[i] - dates[i-1]).days for i in range(1, len(dates))]
        if not intervals: return None
        avg_int = sum(intervals) / len(intervals)
        if 25 <= avg_int <= 35: return {"amount": avg.quantize(Decimal("0.01")), "cycle": "MONTHLY", "confidence": 0.9}
        if 355 <= avg_int <= 375: return {"amount": avg.quantize(Decimal("0.01")), "cycle": "ANNUAL", "confidence": 0.85}
        return None
    
    def _annual_cost(self, amount: Decimal, cycle: str) -> Decimal:
        return amount * {"WEEKLY": 52, "MONTHLY": 12, "QUARTERLY": 4, "ANNUAL": 1}.get(cycle, 12)
    
    async def _identify_savings(self, org_id: str) -> Dict:
        unused = await self.detect_unused(org_id)
        return {"unused_count": len(unused), "potential_annual_savings": sum(float(u.get("annual_cost", 0)) for u in unused)}
    
    async def _save_subscription(self, s: Subscription):
        async with self.db.acquire() as conn:
            await conn.execute("""INSERT INTO subscriptions (id, org_id, vendor_id, name, amount, billing_cycle, status, annual_cost, usage_score, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)""", s.id, s.org_id, s.vendor_id, s.name, float(s.amount), s.billing_cycle, s.status.value, float(s.annual_cost), s.usage_score, s.created_at)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 3: BUDGET MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class BudgetManager:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def create_budget(self, org_id: str, name: str, amount: Decimal, category: ExpenseCategory = None, department: str = None) -> Budget:
        today = date.today()
        budget = Budget(id=f"BUD-{uuid.uuid4().hex[:12].upper()}", org_id=org_id, name=name, category=category, department=department,
            amount=amount, remaining=amount, period_start=today.replace(day=1), period_end=(today.replace(day=28) + timedelta(days=4)).replace(day=1) - timedelta(days=1))
        await self._save_budget(budget)
        return budget
    
    async def get_budget_status(self, org_id: str) -> Dict:
        await self._update_spending(org_id)
        async with self.db.acquire() as conn:
            budgets = await conn.fetch("SELECT * FROM budgets WHERE org_id = $1 ORDER BY percentage_used DESC", org_id)
        total_budget = sum(Decimal(str(b["amount"])) for b in budgets)
        total_spent = sum(Decimal(str(b["spent"])) for b in budgets)
        return {"total_budget": float(total_budget), "total_spent": float(total_spent), "total_remaining": float(total_budget - total_spent),
            "budgets": [{"id": b["id"], "name": b["name"], "amount": float(b["amount"]), "spent": float(b["spent"]), "remaining": float(b["remaining"]),
                "percentage_used": float(b["percentage_used"]), "status": b["status"]} for b in budgets],
            "over_budget_count": sum(1 for b in budgets if b["status"] == "OVER_BUDGET")}
    
    async def forecast_budget(self, budget_id: str) -> Dict:
        async with self.db.acquire() as conn:
            b = await conn.fetchrow("SELECT * FROM budgets WHERE id = $1", budget_id)
        if not b: return None
        today, days_elapsed = date.today(), (date.today() - b["period_start"]).days
        if days_elapsed <= 0: return {"message": "Period not started"}
        days_remaining = (b["period_end"] - b["period_start"]).days - days_elapsed
        daily_rate = Decimal(str(b["spent"])) / days_elapsed
        projected = Decimal(str(b["spent"])) + daily_rate * days_remaining
        return {"budget_amount": float(b["amount"]), "current_spent": float(b["spent"]), "daily_rate": float(daily_rate),
            "projected_total": float(projected), "will_exceed": projected > Decimal(str(b["amount"]))}
    
    async def _update_spending(self, org_id: str):
        async with self.db.acquire() as conn:
            for b in await conn.fetch("SELECT * FROM budgets WHERE org_id = $1", org_id):
                query = "SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE org_id = $1 AND date BETWEEN $2 AND $3"
                params = [org_id, b["period_start"], b["period_end"]]
                if b["category"]: query += " AND category = $4"; params.append(b["category"])
                elif b["department"]: query += " AND department = $4"; params.append(b["department"])
                spent = Decimal(str((await conn.fetchrow(query, *params))[0]))
                remaining = Decimal(str(b["amount"])) - spent
                pct = (spent / Decimal(str(b["amount"])) * 100) if b["amount"] else Decimal("0")
                status = "OVER_BUDGET" if pct >= 100 else "WARNING" if pct >= b["alert_threshold"] else "ON_TRACK"
                await conn.execute("UPDATE budgets SET spent=$1, remaining=$2, percentage_used=$3, status=$4 WHERE id=$5", float(spent), float(remaining), float(pct), status, b["id"])
    
    async def _save_budget(self, b: Budget):
        async with self.db.acquire() as conn:
            await conn.execute("""INSERT INTO budgets (id, org_id, name, category, department, amount, spent, remaining, percentage_used, status, alert_threshold, period_start, period_end, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)""", b.id, b.org_id, b.name, b.category.value if b.category else None, b.department, float(b.amount), float(b.spent), float(b.remaining), float(b.percentage_used), b.status.value, b.alert_threshold, b.period_start, b.period_end, b.created_at)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 4: UNIT ECONOMICS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class UnitEconomics:
    def __init__(self, db_pool: asyncpg.Pool): self.db = db_pool
    
    async def calculate(self, org_id: str, start: date, end: date) -> Dict:
        async with self.db.acquire() as conn:
            expenses = {e["category"]: Decimal(str(e["total"])) for e in await conn.fetch("SELECT category, SUM(amount) as total FROM expenses WHERE org_id = $1 AND date BETWEEN $2 AND $3 GROUP BY category", org_id, start, end)}
            customers = (await conn.fetchrow("SELECT COUNT(*) FROM customers WHERE org_id = $1 AND status = 'ACTIVE'", org_id))[0] or 1
            revenue = Decimal(str((await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE org_id = $1 AND transaction_type = 'REVENUE' AND created_at BETWEEN $2 AND $3", org_id, start, end))[0]))
            new_customers = (await conn.fetchrow("SELECT COUNT(*) FROM customers WHERE org_id = $1 AND created_at BETWEEN $2 AND $3", org_id, start, end))[0] or 1
        
        total_expenses = sum(expenses.values())
        marketing = expenses.get("ADVERTISING", Decimal("0")) + expenses.get("MARKETING", Decimal("0"))
        cac = marketing / max(new_customers, 1)
        cogs = expenses.get("INFRASTRUCTURE", Decimal("0")) + expenses.get("HOSTING", Decimal("0"))
        gross_margin = ((revenue - cogs) / revenue * 100) if revenue else Decimal("0")
        
        return {"customers": customers, "revenue": float(revenue), "revenue_per_customer": float(revenue / customers),
            "total_expenses": float(total_expenses), "cost_per_customer": float(total_expenses / customers),
            "cac": float(cac), "gross_margin_pct": float(gross_margin),
            "ltv_cac_ratio": float(revenue / customers * 12 / cac) if cac > 0 else None}
    
    async def burn_rate(self, org_id: str) -> Dict:
        async with self.db.acquire() as conn:
            expenses = Decimal(str((await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE org_id = $1 AND date >= CURRENT_DATE - 90", org_id))[0]))
            revenue = Decimal(str((await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) FROM transactions WHERE org_id = $1 AND transaction_type = 'REVENUE' AND created_at >= CURRENT_DATE - 90", org_id))[0]))
            cash = Decimal(str((await conn.fetchrow("SELECT COALESCE(SUM(cached_balance), 0) FROM bank_accounts WHERE org_id = $1 AND status = 'active'", org_id))[0]))
        monthly_expenses, monthly_revenue = expenses / 3, revenue / 3
        net_burn = monthly_expenses - monthly_revenue
        runway = float(cash / net_burn) if net_burn > 0 else float("inf")
        return {"monthly_expenses": float(monthly_expenses), "monthly_revenue": float(monthly_revenue), "net_burn": float(net_burn), "cash": float(cash), "runway_months": runway if runway != float("inf") else "Infinite"}

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ExpenseIntelligence:
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.vendors = VendorAnalyzer(db_pool)
        self.subscriptions = SubscriptionTracker(db_pool)
        self.budgets = BudgetManager(db_pool)
        self.economics = UnitEconomics(db_pool)
    
    async def record_expense(self, org_id: str, dt: date, amount: Decimal, description: str, category: ExpenseCategory = None, vendor_name: str = None, department: str = None) -> Expense:
        if not category: category = self.vendors._categorize_vendor(vendor_name or "", description)
        expense = Expense(id=f"EXP-{uuid.uuid4().hex[:12].upper()}", org_id=org_id, date=dt, amount=amount, description=description, category=category, vendor_name=vendor_name or "", department=department)
        if vendor_name:
            vendor = await self.vendors.process_expense({"org_id": org_id, "date": dt, "amount": amount, "description": description})
            expense.vendor_id = vendor.id if isinstance(vendor, Vendor) else vendor["id"]
        await self._save_expense(expense)
        return expense
    
    async def get_dashboard(self, org_id: str) -> Dict:
        today, month_start = date.today(), date.today().replace(day=1)
        vendor_report = await self.vendors.get_vendor_spend_report(org_id, month_start, today)
        subscription_inv = await self.subscriptions.get_subscription_inventory(org_id)
        budget_status = await self.budgets.get_budget_status(org_id)
        burn = await self.economics.burn_rate(org_id)
        
        async with self.db.acquire() as conn:
            mtd = Decimal(str((await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE org_id = $1 AND date >= $2", org_id, month_start))[0]))
            last_month_start = (month_start - timedelta(days=1)).replace(day=1)
            last_month = Decimal(str((await conn.fetchrow("SELECT COALESCE(SUM(amount), 0) FROM expenses WHERE org_id = $1 AND date >= $2 AND date < $3", org_id, last_month_start, month_start))[0]))
        
        return {"mtd_spending": float(mtd), "last_month": float(last_month), "mom_change_pct": float((mtd - last_month) / last_month * 100) if last_month else 0,
            "burn_rate": burn, "top_vendors": vendor_report["top_vendors"][:5], "by_category": vendor_report["by_category"][:10],
            "subscriptions": {"count": subscription_inv["total_subscriptions"], "monthly_cost": subscription_inv["total_monthly_cost"]},
            "budgets": {"total": budget_status["total_budget"], "spent": budget_status["total_spent"], "over_budget": budget_status["over_budget_count"]}}
    
    async def _save_expense(self, e: Expense):
        async with self.db.acquire() as conn:
            await conn.execute("""INSERT INTO expenses (id, org_id, date, amount, description, category, vendor_id, vendor_name, department, tax_deductible, created_at)
                VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)""", e.id, e.org_id, e.date, float(e.amount), e.description, e.category.value, e.vendor_id, e.vendor_name, e.department, e.tax_deductible, e.created_at)

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE IF NOT EXISTS vendors (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), name VARCHAR(255), normalized_name VARCHAR(255), category VARCHAR(50), is_subscription BOOLEAN DEFAULT false, total_spent DECIMAL(15,2) DEFAULT 0, transaction_count INTEGER DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS subscriptions (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), vendor_id VARCHAR(50), name VARCHAR(255), amount DECIMAL(15,2) DEFAULT 0, billing_cycle VARCHAR(20) DEFAULT 'MONTHLY', status VARCHAR(20) DEFAULT 'ACTIVE', annual_cost DECIMAL(15,2) DEFAULT 0, usage_score INTEGER DEFAULT 100, renewal_date DATE, next_billing_date DATE, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS budgets (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), name VARCHAR(255), category VARCHAR(50), department VARCHAR(100), amount DECIMAL(15,2), spent DECIMAL(15,2) DEFAULT 0, remaining DECIMAL(15,2) DEFAULT 0, percentage_used DECIMAL(5,2) DEFAULT 0, status VARCHAR(20) DEFAULT 'ON_TRACK', alert_threshold INTEGER DEFAULT 80, period_start DATE, period_end DATE, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE IF NOT EXISTS expenses (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), date DATE, amount DECIMAL(15,2), description TEXT, category VARCHAR(50), vendor_id VARCHAR(50), vendor_name VARCHAR(255), department VARCHAR(100), tax_deductible BOOLEAN DEFAULT true, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE INDEX IF NOT EXISTS idx_expenses_org_date ON expenses(org_id, date);
"""

# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI
app = FastAPI(title="Expense Intelligence", version="3.0.0")

@app.get("/api/v1/expenses/{org_id}/dashboard")
async def dashboard(org_id: str): return {"status": "requires_db"}

@app.post("/api/v1/expenses/{org_id}")
async def record(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/expenses/{org_id}/vendors")
async def vendors(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/expenses/{org_id}/subscriptions")
async def subscriptions(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/expenses/{org_id}/budgets")
async def budgets(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/expenses/{org_id}/economics")
async def economics(org_id: str): return {"status": "requires_db"}

@app.get("/api/v1/expenses/{org_id}/burn-rate")
async def burn_rate(org_id: str): return {"status": "requires_db"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4023)
