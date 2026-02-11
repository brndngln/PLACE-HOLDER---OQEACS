# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                                                                                                                                       ║
# ║                              QUANTUM TAX FORTRESS - COMPLETE IMPLEMENTATION                                                            ║
# ║                              OMNI QUANTUM ELITE v3.0                                                                                   ║
# ║                                                                                                                                       ║
# ║                              The Most Advanced Self-Hosted Tax Intelligence System                                                     ║
# ║                              "Never Be Surprised by Taxes Again"                                                                       ║
# ║                                                                                                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

"""
QUANTUM TAX FORTRESS - The 7 Pillars of Tax Protection

PILLAR 1: Real-Time Tax Calculation Engine
PILLAR 2: Intelligent Reserve Management  
PILLAR 3: Multi-Entity Tax Optimization
PILLAR 4: Deduction Maximizer AI
PILLAR 5: Quarterly Payment Automation
PILLAR 6: Tax Scenario Simulator
PILLAR 7: Year-End Report Generator

100% Open Source • 100% Self-Hosted • Zero Compromise
"""

import asyncio
import json
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone, date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
import asyncpg


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# TAX CONFIGURATION - 2026 Tax Rates & Rules
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

# Federal Tax Brackets 2026 (Single Filer - estimated)
FEDERAL_TAX_BRACKETS_2026 = [
    (Decimal("11600"), Decimal("0.10")),
    (Decimal("47150"), Decimal("0.12")),
    (Decimal("100525"), Decimal("0.22")),
    (Decimal("191950"), Decimal("0.24")),
    (Decimal("243725"), Decimal("0.32")),
    (Decimal("609350"), Decimal("0.35")),
    (Decimal("999999999"), Decimal("0.37")),
]

# Self-Employment Tax
SELF_EMPLOYMENT_TAX_RATE = Decimal("0.153")
SELF_EMPLOYMENT_INCOME_FACTOR = Decimal("0.9235")
SOCIAL_SECURITY_WAGE_BASE_2026 = Decimal("168600")

# State Tax Rates (simplified)
STATE_TAX_RATES = {
    "CA": Decimal("0.093"), "NY": Decimal("0.0882"), "TX": Decimal("0"),
    "FL": Decimal("0"), "WA": Decimal("0"), "NV": Decimal("0"),
    "IL": Decimal("0.0495"), "PA": Decimal("0.0307"), "OH": Decimal("0.04"),
    "GA": Decimal("0.055"), "NC": Decimal("0.0525"), "MI": Decimal("0.0425"),
    "NJ": Decimal("0.0897"), "VA": Decimal("0.0575"), "AZ": Decimal("0.025"),
    "MA": Decimal("0.05"), "CO": Decimal("0.044"), "MD": Decimal("0.0575"),
    "TN": Decimal("0"), "IN": Decimal("0.0315"), "MO": Decimal("0.054"),
    "WI": Decimal("0.0765"), "MN": Decimal("0.0985"), "SC": Decimal("0.07"),
    "AL": Decimal("0.05"), "LA": Decimal("0.0425"), "KY": Decimal("0.05"),
    "OR": Decimal("0.099"), "OK": Decimal("0.05"), "CT": Decimal("0.0699"),
    "UT": Decimal("0.0485"), "IA": Decimal("0.06"), "NV": Decimal("0"),
    "AR": Decimal("0.055"), "MS": Decimal("0.05"), "KS": Decimal("0.057"),
    "NM": Decimal("0.059"), "NE": Decimal("0.0684"), "ID": Decimal("0.058"),
    "WV": Decimal("0.065"), "HI": Decimal("0.11"), "NH": Decimal("0"),
    "ME": Decimal("0.0715"), "MT": Decimal("0.0675"), "RI": Decimal("0.0599"),
    "DE": Decimal("0.066"), "SD": Decimal("0"), "ND": Decimal("0.029"),
    "AK": Decimal("0"), "VT": Decimal("0.0875"), "WY": Decimal("0"),
    "DC": Decimal("0.0895"),
}

# QBI Deduction
QBI_DEDUCTION_RATE = Decimal("0.20")
QBI_THRESHOLD_SINGLE = Decimal("182100")

# Quarterly Due Dates
QUARTERLY_DUE_DATES = {
    1: (4, 15),  # Q1: April 15
    2: (6, 15),  # Q2: June 15
    3: (9, 15),  # Q3: September 15
    4: (1, 15),  # Q4: January 15 (next year)
}


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TaxEntityType(Enum):
    SOLE_PROPRIETOR = "SOLE_PROPRIETOR"
    SINGLE_MEMBER_LLC = "SINGLE_MEMBER_LLC"
    PARTNERSHIP = "PARTNERSHIP"
    S_CORP = "S_CORP"
    C_CORP = "C_CORP"


class IncomeType(Enum):
    BUSINESS_INCOME = "BUSINESS_INCOME"
    SUBSCRIPTION_REVENUE = "SUBSCRIPTION_REVENUE"
    USAGE_REVENUE = "USAGE_REVENUE"
    CONSULTING_INCOME = "CONSULTING_INCOME"
    INTEREST_INCOME = "INTEREST_INCOME"
    OTHER_INCOME = "OTHER_INCOME"


class ExpenseCategory(Enum):
    ADVERTISING = "ADVERTISING"
    CONTRACT_LABOR = "CONTRACT_LABOR"
    DEPRECIATION = "DEPRECIATION"
    INSURANCE = "INSURANCE"
    LEGAL_PROFESSIONAL = "LEGAL_PROFESSIONAL"
    OFFICE_EXPENSE = "OFFICE_EXPENSE"
    RENT_LEASE = "RENT_LEASE"
    SUPPLIES = "SUPPLIES"
    TRAVEL = "TRAVEL"
    MEALS = "MEALS"
    UTILITIES = "UTILITIES"
    HOME_OFFICE = "HOME_OFFICE"
    HEALTH_INSURANCE = "HEALTH_INSURANCE"
    RETIREMENT_CONTRIBUTION = "RETIREMENT_CONTRIBUTION"
    SOFTWARE_SUBSCRIPTIONS = "SOFTWARE_SUBSCRIPTIONS"
    CLOUD_HOSTING = "CLOUD_HOSTING"
    AI_ML_COSTS = "AI_ML_COSTS"
    BANK_FEES = "BANK_FEES"
    PROCESSING_FEES = "PROCESSING_FEES"
    EQUIPMENT = "EQUIPMENT"
    EDUCATION = "EDUCATION"
    OTHER_EXPENSE = "OTHER_EXPENSE"


class ReserveStatus(Enum):
    UNDERFUNDED = "UNDERFUNDED"
    ADEQUATE = "ADEQUATE"
    FULLY_FUNDED = "FULLY_FUNDED"
    OVERFUNDED = "OVERFUNDED"


class PaymentStatus(Enum):
    NOT_DUE = "NOT_DUE"
    UPCOMING = "UPCOMING"
    DUE_SOON = "DUE_SOON"
    OVERDUE = "OVERDUE"
    PAID = "PAID"
    SCHEDULED = "SCHEDULED"


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class TaxProfile:
    """Tax profile for an organization"""
    org_id: str
    filing_status: str = "single"
    state: str = "CA"
    entity_type: TaxEntityType = TaxEntityType.SOLE_PROPRIETOR
    reserve_percentage: Decimal = Decimal("0.32")
    include_state_tax: bool = True
    include_self_employment_tax: bool = True
    safety_buffer_percentage: Decimal = Decimal("0.10")
    auto_reserve_enabled: bool = True
    reserve_account_id: Optional[str] = None
    auto_pay_quarterly: bool = False
    pay_days_before_due: int = 5
    notify_reserve_low: bool = True
    notify_quarterly_upcoming: bool = True
    notify_deduction_opportunities: bool = True


@dataclass
class TaxCalculationResult:
    """Result of a tax calculation"""
    gross_income: Decimal
    total_deductions: Decimal
    qbi_deduction: Decimal
    taxable_income: Decimal
    self_employment_income: Decimal
    federal_income_tax: Decimal
    state_income_tax: Decimal
    self_employment_tax: Decimal
    total_tax: Decimal
    effective_tax_rate: Decimal
    marginal_tax_rate: Decimal
    recommended_reserve: Decimal
    reserve_percentage: Decimal
    federal_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    deduction_breakdown: Dict[str, Decimal] = field(default_factory=dict)
    calculated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tax_year: int = field(default_factory=lambda: datetime.now().year)


@dataclass
class TaxReserve:
    """Tax reserve bucket"""
    id: str
    org_id: str
    business_id: Optional[str]
    tax_year: int
    quarter: int
    due_date: date
    required_amount: Decimal
    reserved_amount: Decimal
    paid_amount: Decimal = Decimal("0")
    status: ReserveStatus = ReserveStatus.UNDERFUNDED
    payment_status: PaymentStatus = PaymentStatus.NOT_DUE
    federal_portion: Decimal = Decimal("0")
    state_portion: Decimal = Decimal("0")
    se_tax_portion: Decimal = Decimal("0")
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    paid_at: Optional[datetime] = None


@dataclass
class DeductionOpportunity:
    """A potential tax deduction opportunity"""
    id: str
    category: str
    title: str
    description: str
    potential_savings: Decimal
    confidence: Decimal
    action_required: str
    learn_more_url: Optional[str] = None
    expires_at: Optional[date] = None
    priority: int = 1  # 1 = highest


@dataclass
class TaxScenario:
    """A tax scenario for what-if analysis"""
    id: str
    name: str
    description: str
    annual_income: Decimal
    annual_expenses: Decimal
    additional_deductions: Decimal = Decimal("0")
    result: Optional[TaxCalculationResult] = None
    compared_to: Optional[str] = None
    difference: Optional[Dict[str, Decimal]] = None


@dataclass
class QuarterlyPayment:
    """A quarterly estimated tax payment"""
    id: str
    org_id: str
    tax_year: int
    quarter: int
    due_date: date
    federal_amount: Decimal
    state_amount: Decimal
    total_amount: Decimal
    status: PaymentStatus
    scheduled_date: Optional[date] = None
    paid_date: Optional[date] = None
    confirmation_number: Optional[str] = None
    federal_voucher_generated: bool = False
    state_voucher_generated: bool = False


@dataclass
class TaxReport:
    """Generated tax report"""
    id: str
    org_id: str
    report_type: str
    tax_year: int
    generated_at: datetime
    file_path: str
    data: Dict[str, Any] = field(default_factory=dict)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 1: TAX CALCULATION ENGINE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TaxCalculationEngine:
    """
    PILLAR 1: REAL-TIME TAX CALCULATION ENGINE
    
    Calculates federal, state, and self-employment taxes in real-time.
    Every dollar that enters the system is instantly analyzed.
    """
    
    def __init__(self, tax_year: int = None):
        self.tax_year = tax_year or datetime.now().year
    
    def calculate_full_tax(
        self,
        gross_income: Decimal,
        deductions: Decimal,
        state: str,
        entity_type: TaxEntityType = TaxEntityType.SOLE_PROPRIETOR,
        filing_status: str = "single"
    ) -> TaxCalculationResult:
        """
        Calculate complete tax liability for given income.
        """
        
        # Calculate QBI deduction
        qbi_deduction = self._calculate_qbi_deduction(gross_income, deductions)
        
        # Calculate taxable income
        taxable_income = max(Decimal("0"), gross_income - deductions - qbi_deduction)
        
        # Calculate federal income tax
        federal_tax, federal_breakdown, marginal_rate = self._calculate_federal_tax(
            taxable_income, filing_status
        )
        
        # Calculate self-employment tax
        se_income = gross_income * SELF_EMPLOYMENT_INCOME_FACTOR
        se_tax = self._calculate_self_employment_tax(se_income)
        
        # Deduct half of SE tax from income tax calculation
        se_deduction = se_tax / 2
        
        # Calculate state tax
        state_tax = self._calculate_state_tax(taxable_income, state)
        
        # Total tax
        total_tax = federal_tax + state_tax + se_tax
        
        # Effective rate
        effective_rate = (total_tax / gross_income * 100) if gross_income > 0 else Decimal("0")
        
        # Recommended reserve with buffer
        base_reserve_rate = (total_tax / gross_income) if gross_income > 0 else Decimal("0.30")
        safety_buffer = Decimal("0.05")
        reserve_rate = min(base_reserve_rate + safety_buffer, Decimal("0.50"))
        recommended_reserve = gross_income * reserve_rate
        
        return TaxCalculationResult(
            gross_income=gross_income,
            total_deductions=deductions,
            qbi_deduction=qbi_deduction,
            taxable_income=taxable_income,
            self_employment_income=se_income,
            federal_income_tax=federal_tax.quantize(Decimal("0.01")),
            state_income_tax=state_tax.quantize(Decimal("0.01")),
            self_employment_tax=se_tax.quantize(Decimal("0.01")),
            total_tax=total_tax.quantize(Decimal("0.01")),
            effective_tax_rate=effective_rate.quantize(Decimal("0.01")),
            marginal_tax_rate=(marginal_rate * 100).quantize(Decimal("0.1")),
            recommended_reserve=recommended_reserve.quantize(Decimal("0.01")),
            reserve_percentage=(reserve_rate * 100).quantize(Decimal("0.1")),
            federal_breakdown=federal_breakdown,
            deduction_breakdown={"qbi": qbi_deduction, "business": deductions},
            tax_year=self.tax_year
        )
    
    def calculate_incremental_tax(
        self,
        income_amount: Decimal,
        ytd_income: Decimal,
        ytd_deductions: Decimal,
        state: str
    ) -> Dict[str, Decimal]:
        """
        Calculate tax on incremental income (for real-time reservation).
        Called every time money comes in.
        """
        
        # Tax on YTD income
        ytd_result = self.calculate_full_tax(ytd_income, ytd_deductions, state)
        
        # Tax on YTD + new income
        new_total = ytd_income + income_amount
        new_result = self.calculate_full_tax(new_total, ytd_deductions, state)
        
        # Incremental tax
        incremental_federal = new_result.federal_income_tax - ytd_result.federal_income_tax
        incremental_state = new_result.state_income_tax - ytd_result.state_income_tax
        incremental_se = new_result.self_employment_tax - ytd_result.self_employment_tax
        incremental_total = incremental_federal + incremental_state + incremental_se
        
        marginal_rate = (incremental_total / income_amount * 100) if income_amount > 0 else Decimal("0")
        
        return {
            "income_amount": income_amount,
            "federal_tax": incremental_federal.quantize(Decimal("0.01")),
            "state_tax": incremental_state.quantize(Decimal("0.01")),
            "self_employment_tax": incremental_se.quantize(Decimal("0.01")),
            "total_tax": incremental_total.quantize(Decimal("0.01")),
            "marginal_rate": marginal_rate.quantize(Decimal("0.1")),
            "recommended_reserve": (incremental_total * Decimal("1.10")).quantize(Decimal("0.01"))
        }
    
    def _calculate_federal_tax(
        self,
        taxable_income: Decimal,
        filing_status: str
    ) -> Tuple[Decimal, Dict[str, Decimal], Decimal]:
        """Calculate federal income tax using progressive brackets"""
        
        tax = Decimal("0")
        breakdown = {}
        prev_bracket = Decimal("0")
        marginal_rate = Decimal("0.10")
        
        for bracket_limit, rate in FEDERAL_TAX_BRACKETS_2026:
            if taxable_income <= prev_bracket:
                break
            
            taxable_in_bracket = min(taxable_income, bracket_limit) - prev_bracket
            if taxable_in_bracket > 0:
                tax_in_bracket = taxable_in_bracket * rate
                tax += tax_in_bracket
                breakdown[f"{int(rate * 100)}%_bracket"] = tax_in_bracket.quantize(Decimal("0.01"))
                marginal_rate = rate
            
            prev_bracket = bracket_limit
        
        return tax, breakdown, marginal_rate
    
    def _calculate_self_employment_tax(self, se_income: Decimal) -> Decimal:
        """Calculate self-employment tax (Social Security + Medicare)"""
        
        # Social Security (12.4%) - capped
        ss_taxable = min(se_income, SOCIAL_SECURITY_WAGE_BASE_2026)
        ss_tax = ss_taxable * Decimal("0.124")
        
        # Medicare (2.9%) - no cap
        medicare_tax = se_income * Decimal("0.029")
        
        # Additional Medicare (0.9%) on income over $200K
        additional_medicare = Decimal("0")
        if se_income > Decimal("200000"):
            additional_medicare = (se_income - Decimal("200000")) * Decimal("0.009")
        
        return ss_tax + medicare_tax + additional_medicare
    
    def _calculate_state_tax(self, taxable_income: Decimal, state: str) -> Decimal:
        """Calculate state income tax"""
        rate = STATE_TAX_RATES.get(state.upper(), Decimal("0.05"))
        return taxable_income * rate
    
    def _calculate_qbi_deduction(self, gross_income: Decimal, deductions: Decimal) -> Decimal:
        """Calculate Qualified Business Income deduction (Section 199A)"""
        qbi = gross_income - deductions
        if qbi <= 0:
            return Decimal("0")
        return (qbi * QBI_DEDUCTION_RATE).quantize(Decimal("0.01"))


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 2: INTELLIGENT RESERVE MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TaxReserveManager:
    """
    PILLAR 2: INTELLIGENT RESERVE MANAGEMENT
    
    Automatically reserves the right amount of taxes from every dollar earned.
    Manages quarterly buckets and ensures you're always funded.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, calc_engine: TaxCalculationEngine):
        self.db = db_pool
        self.calc = calc_engine
    
    async def process_income(
        self,
        org_id: str,
        business_id: str,
        amount: Decimal,
        income_type: IncomeType,
        profile: TaxProfile
    ) -> Dict[str, Any]:
        """
        Process incoming revenue and automatically reserve taxes.
        Called every time money comes into any of your businesses.
        """
        
        # Get YTD figures
        ytd = await self._get_ytd_figures(org_id, business_id)
        
        # Calculate incremental tax
        tax_breakdown = self.calc.calculate_incremental_tax(
            income_amount=amount,
            ytd_income=ytd["income"],
            ytd_deductions=ytd["deductions"],
            state=profile.state
        )
        
        # Determine reserve amount
        reserve_amount = tax_breakdown["recommended_reserve"]
        
        # Determine current quarter
        current_quarter = self._get_current_tax_quarter()
        
        # Update reserve bucket
        reserve = await self._update_reserve_bucket(
            org_id=org_id,
            business_id=business_id,
            quarter=current_quarter,
            additional_amount=reserve_amount,
            breakdown={
                "federal": tax_breakdown["federal_tax"],
                "state": tax_breakdown["state_tax"],
                "self_employment": tax_breakdown["self_employment_tax"]
            }
        )
        
        # Record the event
        await self._record_income_event(
            org_id=org_id,
            business_id=business_id,
            income_amount=amount,
            income_type=income_type,
            tax_breakdown=tax_breakdown,
            reserve_amount=reserve_amount
        )
        
        return {
            "income_amount": str(amount),
            "tax_breakdown": {k: str(v) for k, v in tax_breakdown.items()},
            "reserved_amount": str(reserve_amount),
            "available_amount": str(amount - reserve_amount),
            "reserve_status": reserve.status.value,
            "quarter": f"Q{current_quarter['quarter']} {current_quarter['year']}"
        }
    
    async def get_reserve_status(self, org_id: str) -> Dict[str, Any]:
        """Get comprehensive reserve status across all quarters"""
        
        current_year = datetime.now().year
        reserves = await self._get_all_reserves(org_id, current_year)
        
        total_required = Decimal("0")
        total_reserved = Decimal("0")
        quarters = []
        
        for reserve in reserves:
            total_required += reserve.required_amount
            total_reserved += reserve.reserved_amount
            
            funding_pct = (
                (reserve.reserved_amount / reserve.required_amount * 100)
                if reserve.required_amount > 0 else Decimal("100")
            )
            
            quarters.append({
                "quarter": f"Q{reserve.quarter}",
                "tax_year": reserve.tax_year,
                "due_date": reserve.due_date.isoformat(),
                "days_until_due": (reserve.due_date - date.today()).days,
                "required": str(reserve.required_amount),
                "reserved": str(reserve.reserved_amount),
                "funding_percentage": str(funding_pct.quantize(Decimal("0.1"))),
                "status": reserve.status.value,
                "payment_status": reserve.payment_status.value,
                "breakdown": {
                    "federal": str(reserve.federal_portion),
                    "state": str(reserve.state_portion),
                    "self_employment": str(reserve.se_tax_portion)
                }
            })
        
        overall_status = self._determine_overall_status(total_required, total_reserved)
        
        return {
            "tax_year": current_year,
            "total_required": str(total_required),
            "total_reserved": str(total_reserved),
            "surplus_deficit": str(total_reserved - total_required),
            "overall_status": overall_status.value,
            "overall_funding_percentage": str(
                (total_reserved / total_required * 100).quantize(Decimal("0.1"))
                if total_required > 0 else "100"
            ),
            "quarters": quarters
        }
    
    async def get_next_payment_due(self, org_id: str) -> Optional[Dict[str, Any]]:
        """Get details about the next upcoming quarterly payment"""
        
        today = date.today()
        current_year = today.year
        
        for quarter, (month, day) in QUARTERLY_DUE_DATES.items():
            year = current_year if quarter < 4 else current_year
            if quarter == 4:
                year = current_year + 1 if today.month > 1 else current_year
            
            due_date = date(year if quarter != 4 else year, month, day)
            
            if due_date > today:
                tax_year = year if quarter != 4 else year - 1
                reserve = await self._get_reserve_bucket(org_id, tax_year, quarter)
                
                return {
                    "quarter": f"Q{quarter}",
                    "tax_year": tax_year,
                    "due_date": due_date.isoformat(),
                    "days_until_due": (due_date - today).days,
                    "federal_amount": str(reserve.federal_portion) if reserve else "0",
                    "state_amount": str(reserve.state_portion) if reserve else "0",
                    "se_tax_amount": str(reserve.se_tax_portion) if reserve else "0",
                    "total_amount": str(reserve.required_amount) if reserve else "0",
                    "reserved_amount": str(reserve.reserved_amount) if reserve else "0",
                    "status": reserve.payment_status.value if reserve else "NOT_DUE",
                    "funding_status": reserve.status.value if reserve else "UNDERFUNDED"
                }
        
        return None
    
    def _get_current_tax_quarter(self) -> Dict[str, int]:
        """Determine current tax quarter"""
        today = date.today()
        
        if today.month <= 3:
            return {"year": today.year, "quarter": 1}
        elif today.month <= 5:
            return {"year": today.year, "quarter": 2}
        elif today.month <= 8:
            return {"year": today.year, "quarter": 3}
        else:
            return {"year": today.year, "quarter": 4}
    
    def _determine_overall_status(self, required: Decimal, reserved: Decimal) -> ReserveStatus:
        """Determine overall reserve status"""
        if required == 0:
            return ReserveStatus.FULLY_FUNDED
        
        ratio = reserved / required
        
        if ratio < Decimal("0.9"):
            return ReserveStatus.UNDERFUNDED
        elif ratio < Decimal("1.0"):
            return ReserveStatus.ADEQUATE
        elif ratio < Decimal("1.1"):
            return ReserveStatus.FULLY_FUNDED
        else:
            return ReserveStatus.OVERFUNDED
    
    async def _get_ytd_figures(self, org_id: str, business_id: str) -> Dict[str, Decimal]:
        """Get year-to-date income and deductions"""
        current_year = datetime.now().year
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as deductions
                FROM tax_events
                WHERE org_id = $1 
                AND (business_id = $2 OR $2 IS NULL)
                AND EXTRACT(YEAR FROM created_at) = $3
            """, org_id, business_id, current_year)
            
            return {
                "income": Decimal(str(row["income"])) if row else Decimal("0"),
                "deductions": Decimal(str(row["deductions"])) if row else Decimal("0")
            }
    
    async def _update_reserve_bucket(
        self,
        org_id: str,
        business_id: str,
        quarter: Dict[str, int],
        additional_amount: Decimal,
        breakdown: Dict[str, Decimal]
    ) -> TaxReserve:
        """Update or create a reserve bucket"""
        
        q = quarter["quarter"]
        year = quarter["year"]
        month, day = QUARTERLY_DUE_DATES[q]
        due_year = year if q < 4 else year + 1
        due_date = date(due_year, month, day)
        
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM tax_reserves
                WHERE org_id = $1 AND tax_year = $2 AND quarter = $3
            """, org_id, year, q)
            
            if row:
                new_reserved = Decimal(str(row["reserved_amount"])) + additional_amount
                new_required = (Decimal(str(row["required_amount"])) + 
                              breakdown["federal"] + breakdown["state"] + breakdown["self_employment"])
                
                status = self._determine_overall_status(new_required, new_reserved)
                
                await conn.execute("""
                    UPDATE tax_reserves SET
                        reserved_amount = $1, required_amount = $2,
                        federal_portion = federal_portion + $3,
                        state_portion = state_portion + $4,
                        se_tax_portion = se_tax_portion + $5,
                        status = $6, updated_at = $7
                    WHERE id = $8
                """, float(new_reserved), float(new_required),
                    float(breakdown["federal"]), float(breakdown["state"]),
                    float(breakdown["self_employment"]), status.value,
                    datetime.now(timezone.utc), row["id"])
                
                return TaxReserve(
                    id=row["id"], org_id=org_id, business_id=business_id,
                    tax_year=year, quarter=q, due_date=due_date,
                    required_amount=new_required, reserved_amount=new_reserved,
                    status=status, payment_status=PaymentStatus(row["payment_status"]),
                    federal_portion=Decimal(str(row["federal_portion"])) + breakdown["federal"],
                    state_portion=Decimal(str(row["state_portion"])) + breakdown["state"],
                    se_tax_portion=Decimal(str(row["se_tax_portion"])) + breakdown["self_employment"]
                )
            else:
                reserve_id = f"RES-{uuid.uuid4().hex[:12].upper()}"
                required = breakdown["federal"] + breakdown["state"] + breakdown["self_employment"]
                status = self._determine_overall_status(required, additional_amount)
                
                await conn.execute("""
                    INSERT INTO tax_reserves (
                        id, org_id, business_id, tax_year, quarter, due_date,
                        required_amount, reserved_amount, status, payment_status,
                        federal_portion, state_portion, se_tax_portion,
                        created_at, updated_at
                    ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
                """, reserve_id, org_id, business_id, year, q, due_date,
                    float(required), float(additional_amount), status.value,
                    PaymentStatus.NOT_DUE.value, float(breakdown["federal"]),
                    float(breakdown["state"]), float(breakdown["self_employment"]),
                    datetime.now(timezone.utc), datetime.now(timezone.utc))
                
                return TaxReserve(
                    id=reserve_id, org_id=org_id, business_id=business_id,
                    tax_year=year, quarter=q, due_date=due_date,
                    required_amount=required, reserved_amount=additional_amount,
                    status=status, payment_status=PaymentStatus.NOT_DUE,
                    federal_portion=breakdown["federal"],
                    state_portion=breakdown["state"],
                    se_tax_portion=breakdown["self_employment"]
                )
    
    async def _record_income_event(
        self, org_id: str, business_id: str, income_amount: Decimal,
        income_type: IncomeType, tax_breakdown: Dict, reserve_amount: Decimal
    ):
        """Record income event for audit trail"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO tax_events (
                    id, org_id, business_id, type, category, amount,
                    tax_breakdown, reserve_amount, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9)
            """, f"EVT-{uuid.uuid4().hex[:12].upper()}", org_id, business_id,
                "income", income_type.value, float(income_amount),
                json.dumps({k: str(v) for k, v in tax_breakdown.items()}),
                float(reserve_amount), datetime.now(timezone.utc))
    
    async def _get_all_reserves(self, org_id: str, year: int) -> List[TaxReserve]:
        """Get all reserves for a year"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM tax_reserves
                WHERE org_id = $1 AND tax_year = $2
                ORDER BY quarter
            """, org_id, year)
            return [self._row_to_reserve(row) for row in rows]
    
    async def _get_reserve_bucket(self, org_id: str, year: int, quarter: int) -> Optional[TaxReserve]:
        """Get specific reserve bucket"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT * FROM tax_reserves
                WHERE org_id = $1 AND tax_year = $2 AND quarter = $3
            """, org_id, year, quarter)
            return self._row_to_reserve(row) if row else None
    
    def _row_to_reserve(self, row) -> TaxReserve:
        """Convert DB row to TaxReserve"""
        return TaxReserve(
            id=row["id"], org_id=row["org_id"], business_id=row.get("business_id"),
            tax_year=row["tax_year"], quarter=row["quarter"], due_date=row["due_date"],
            required_amount=Decimal(str(row["required_amount"])),
            reserved_amount=Decimal(str(row["reserved_amount"])),
            paid_amount=Decimal(str(row.get("paid_amount", 0))),
            status=ReserveStatus(row["status"]),
            payment_status=PaymentStatus(row["payment_status"]),
            federal_portion=Decimal(str(row["federal_portion"])),
            state_portion=Decimal(str(row["state_portion"])),
            se_tax_portion=Decimal(str(row["se_tax_portion"])),
            created_at=row["created_at"], updated_at=row["updated_at"],
            paid_at=row.get("paid_at")
        )


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 3: MULTI-ENTITY TAX OPTIMIZATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class MultiEntityTaxOptimizer:
    """
    PILLAR 3: MULTI-ENTITY TAX OPTIMIZATION
    
    Track and optimize taxes across ALL your AI businesses.
    Consolidated view with per-business breakdown.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, calc_engine: TaxCalculationEngine):
        self.db = db_pool
        self.calc = calc_engine
    
    async def get_consolidated_tax_summary(self, org_id: str) -> Dict[str, Any]:
        """Get consolidated tax summary across all businesses"""
        
        businesses = await self._get_all_businesses(org_id)
        current_year = datetime.now().year
        
        consolidated = {
            "total_revenue": Decimal("0"),
            "total_expenses": Decimal("0"),
            "total_net_income": Decimal("0"),
            "total_tax_liability": Decimal("0"),
            "total_reserved": Decimal("0"),
        }
        
        business_summaries = []
        
        for biz in businesses:
            summary = await self._get_business_tax_summary(biz["id"], current_year)
            
            consolidated["total_revenue"] += summary["revenue"]
            consolidated["total_expenses"] += summary["expenses"]
            consolidated["total_net_income"] += summary["net_income"]
            consolidated["total_tax_liability"] += summary["tax_liability"]
            consolidated["total_reserved"] += summary["reserved"]
            
            funding_pct = (
                (summary["reserved"] / summary["tax_liability"] * 100)
                if summary["tax_liability"] > 0 else Decimal("100")
            )
            
            business_summaries.append({
                "business_id": biz["id"],
                "business_name": biz["name"],
                "revenue": str(summary["revenue"]),
                "expenses": str(summary["expenses"]),
                "net_income": str(summary["net_income"]),
                "tax_liability": str(summary["tax_liability"]),
                "reserved": str(summary["reserved"]),
                "funding_percentage": str(funding_pct.quantize(Decimal("0.1"))),
                "status": "✅ Funded" if funding_pct >= 100 else "⚠️ Underfunded"
            })
        
        overall_funding = (
            (consolidated["total_reserved"] / consolidated["total_tax_liability"] * 100)
            if consolidated["total_tax_liability"] > 0 else Decimal("100")
        )
        
        return {
            "tax_year": current_year,
            "consolidated": {
                "total_revenue": str(consolidated["total_revenue"]),
                "total_expenses": str(consolidated["total_expenses"]),
                "total_net_income": str(consolidated["total_net_income"]),
                "total_tax_liability": str(consolidated["total_tax_liability"]),
                "total_reserved": str(consolidated["total_reserved"]),
                "overall_funding_percentage": str(overall_funding.quantize(Decimal("0.1"))),
                "overall_status": "✅ Fully Funded" if overall_funding >= 100 else "⚠️ Action Needed"
            },
            "businesses": business_summaries,
            "business_count": len(businesses)
        }
    
    async def _get_all_businesses(self, org_id: str) -> List[Dict]:
        """Get all businesses for organization"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT id, name, status FROM businesses
                WHERE parent_id = $1 AND status = 'ACTIVE'
            """, org_id)
            return [dict(row) for row in rows]
    
    async def _get_business_tax_summary(self, business_id: str, year: int) -> Dict[str, Decimal]:
        """Get tax summary for a single business"""
        async with self.db.acquire() as conn:
            row = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as revenue,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expenses,
                    COALESCE(SUM(reserve_amount), 0) as reserved
                FROM tax_events
                WHERE business_id = $1 AND EXTRACT(YEAR FROM created_at) = $2
            """, business_id, year)
            
            revenue = Decimal(str(row["revenue"]))
            expenses = Decimal(str(row["expenses"]))
            net_income = revenue - expenses
            
            # Calculate tax liability
            result = self.calc.calculate_full_tax(revenue, expenses, "CA")
            
            return {
                "revenue": revenue,
                "expenses": expenses,
                "net_income": net_income,
                "tax_liability": result.total_tax,
                "reserved": Decimal(str(row["reserved"]))
            }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 4: DEDUCTION MAXIMIZER AI
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class DeductionMaximizerAI:
    """
    PILLAR 4: DEDUCTION MAXIMIZER AI
    
    AI-powered analysis to find and maximize all legal tax deductions.
    Scans your finances and suggests missed opportunities.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, calc_engine: TaxCalculationEngine):
        self.db = db_pool
        self.calc = calc_engine
    
    async def analyze_deduction_opportunities(
        self,
        org_id: str,
        profile: TaxProfile
    ) -> List[DeductionOpportunity]:
        """
        Analyze all potential deduction opportunities.
        Returns prioritized list of deductions you might be missing.
        """
        
        opportunities = []
        ytd_data = await self._get_ytd_financial_data(org_id)
        marginal_rate = Decimal("0.35")  # Estimated combined rate
        
        # Check each deduction category
        opps = []
        opps.extend(self._check_home_office(ytd_data, marginal_rate))
        opps.extend(self._check_health_insurance(ytd_data, marginal_rate))
        opps.extend(self._check_retirement(ytd_data, marginal_rate))
        opps.extend(self._check_equipment(ytd_data, marginal_rate))
        opps.extend(self._check_vehicle(ytd_data, marginal_rate))
        opps.extend(self._check_education(ytd_data, marginal_rate))
        opps.extend(self._check_software(ytd_data, marginal_rate))
        opps.extend(self._check_meals_entertainment(ytd_data, marginal_rate))
        
        # Sort by potential savings
        opps.sort(key=lambda x: x.potential_savings, reverse=True)
        
        # Calculate total potential savings
        total_potential = sum(o.potential_savings for o in opps)
        
        return {
            "opportunities": [self._opportunity_to_dict(o) for o in opps],
            "total_potential_savings": str(total_potential),
            "current_tax_efficiency_score": self._calculate_efficiency_score(ytd_data),
            "target_efficiency_score": 95,
            "recommendations_count": len(opps)
        }
    
    def _check_home_office(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check home office deduction"""
        if ytd_data.get("home_office", Decimal("0")) > 0:
            return []
        
        estimated_deduction = Decimal("3000")
        savings = (estimated_deduction * marginal_rate).quantize(Decimal("0.01"))
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="HOME_OFFICE",
            title="Home Office Deduction",
            description="Deduct a portion of rent/mortgage, utilities, insurance based on office square footage.",
            potential_savings=savings,
            confidence=Decimal("0.85"),
            action_required="Calculate home office square footage and housing costs",
            learn_more_url="https://www.irs.gov/businesses/small-businesses-self-employed/home-office-deduction",
            priority=1
        )]
    
    def _check_health_insurance(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check health insurance deduction"""
        if ytd_data.get("health_insurance", Decimal("0")) > 0:
            return []
        
        estimated_deduction = Decimal("6000")
        savings = (estimated_deduction * marginal_rate).quantize(Decimal("0.01"))
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="HEALTH_INSURANCE",
            title="Self-Employed Health Insurance Deduction",
            description="Deduct 100% of health insurance premiums for yourself and family.",
            potential_savings=savings,
            confidence=Decimal("0.90"),
            action_required="Add health insurance premiums as business expense",
            learn_more_url="https://www.irs.gov/taxtopics/tc502",
            priority=1
        )]
    
    def _check_retirement(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check retirement contribution deduction"""
        current = ytd_data.get("retirement", Decimal("0"))
        net_income = ytd_data.get("net_income", Decimal("0"))
        
        max_contribution = min(net_income * Decimal("0.25"), Decimal("69000"))
        available = max_contribution - current
        
        if available <= 0:
            return []
        
        savings = (available * marginal_rate).quantize(Decimal("0.01"))
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="RETIREMENT",
            title="SEP-IRA / Solo 401(k) Contribution",
            description=f"Contribute up to ${max_contribution:,.0f} (25% of net income). Currently: ${current:,.0f}",
            potential_savings=savings,
            confidence=Decimal("0.95"),
            action_required=f"Contribute ${available:,.0f} more to retirement account",
            learn_more_url="https://www.irs.gov/retirement-plans/plan-sponsor/sep-contribution-limits",
            priority=1
        )]
    
    def _check_equipment(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check Section 179 equipment deduction"""
        if ytd_data.get("equipment", Decimal("0")) > Decimal("5000"):
            return []
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="EQUIPMENT",
            title="Section 179 Equipment Deduction",
            description="Immediately expense business equipment: computers, furniture, software.",
            potential_savings=Decimal("500"),
            confidence=Decimal("0.70"),
            action_required="Consider equipment purchases before year-end",
            learn_more_url="https://www.irs.gov/newsroom/section-179-deduction",
            priority=2
        )]
    
    def _check_vehicle(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check vehicle/mileage deduction"""
        if ytd_data.get("vehicle", Decimal("0")) > 0:
            return []
        
        # Estimate 5,000 business miles at $0.67/mile
        estimated_deduction = Decimal("3350")
        savings = (estimated_deduction * marginal_rate).quantize(Decimal("0.01"))
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="VEHICLE",
            title="Vehicle/Mileage Deduction",
            description="Deduct business miles at $0.67/mile (2024) or actual vehicle expenses.",
            potential_savings=savings,
            confidence=Decimal("0.60"),
            action_required="Track business mileage using an app",
            learn_more_url="https://www.irs.gov/tax-professionals/standard-mileage-rates",
            priority=3
        )]
    
    def _check_education(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check education/training deduction"""
        if ytd_data.get("education", Decimal("0")) > 0:
            return []
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="EDUCATION",
            title="Professional Education Deduction",
            description="Deduct courses, conferences, books that improve business skills.",
            potential_savings=Decimal("350"),
            confidence=Decimal("0.75"),
            action_required="Track professional development expenses",
            priority=3
        )]
    
    def _check_software(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check software subscriptions"""
        current = ytd_data.get("software", Decimal("0"))
        
        if current > Decimal("2000"):
            return []
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="SOFTWARE",
            title="Software & SaaS Subscriptions",
            description="Ensure all business software subscriptions are tracked as expenses.",
            potential_savings=Decimal("300"),
            confidence=Decimal("0.80"),
            action_required="Audit all software subscriptions for business use",
            priority=3
        )]
    
    def _check_meals_entertainment(self, ytd_data: Dict, marginal_rate: Decimal) -> List[DeductionOpportunity]:
        """Check meals deduction"""
        if ytd_data.get("meals", Decimal("0")) > 0:
            return []
        
        return [DeductionOpportunity(
            id=f"OPP-{uuid.uuid4().hex[:8]}",
            category="MEALS",
            title="Business Meals Deduction",
            description="50% of business meals with clients/partners are deductible.",
            potential_savings=Decimal("200"),
            confidence=Decimal("0.65"),
            action_required="Track business meal receipts with purpose noted",
            priority=4
        )]
    
    def _calculate_efficiency_score(self, ytd_data: Dict) -> int:
        """Calculate tax efficiency score (0-100)"""
        score = 50  # Base score
        
        if ytd_data.get("home_office", 0) > 0:
            score += 10
        if ytd_data.get("health_insurance", 0) > 0:
            score += 15
        if ytd_data.get("retirement", 0) > 0:
            score += 15
        if ytd_data.get("equipment", 0) > 0:
            score += 5
        if ytd_data.get("software", 0) > 0:
            score += 5
        
        return min(score, 100)
    
    def _opportunity_to_dict(self, opp: DeductionOpportunity) -> Dict:
        """Convert opportunity to dict"""
        return {
            "id": opp.id,
            "category": opp.category,
            "title": opp.title,
            "description": opp.description,
            "potential_savings": str(opp.potential_savings),
            "confidence": str(opp.confidence),
            "action_required": opp.action_required,
            "learn_more_url": opp.learn_more_url,
            "priority": opp.priority
        }
    
    async def _get_ytd_financial_data(self, org_id: str) -> Dict[str, Decimal]:
        """Get YTD financial data by category"""
        current_year = datetime.now().year
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT category, SUM(amount) as total
                FROM tax_events
                WHERE org_id = $1 
                AND EXTRACT(YEAR FROM created_at) = $2
                AND type = 'expense'
                GROUP BY category
            """, org_id, current_year)
            
            result = {}
            category_map = {
                "HOME_OFFICE": "home_office",
                "HEALTH_INSURANCE": "health_insurance",
                "RETIREMENT_CONTRIBUTION": "retirement",
                "EQUIPMENT": "equipment",
                "SOFTWARE_SUBSCRIPTIONS": "software",
                "MEALS": "meals",
                "CAR_TRUCK": "vehicle",
                "EDUCATION": "education",
            }
            
            for row in rows:
                key = category_map.get(row["category"], row["category"].lower())
                result[key] = Decimal(str(row["total"]))
            
            # Get net income
            income_row = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) -
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as net
                FROM tax_events
                WHERE org_id = $1 AND EXTRACT(YEAR FROM created_at) = $2
            """, org_id, current_year)
            
            result["net_income"] = Decimal(str(income_row["net"])) if income_row else Decimal("0")
            
            return result


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 5: QUARTERLY PAYMENT AUTOMATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class QuarterlyPaymentManager:
    """
    PILLAR 5: QUARTERLY PAYMENT AUTOMATION
    
    Never miss a quarterly estimated tax payment.
    Reminders, voucher generation, and optional auto-pay.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, reserve_manager: TaxReserveManager):
        self.db = db_pool
        self.reserves = reserve_manager
    
    async def get_payment_schedule(self, org_id: str, year: int = None) -> Dict[str, Any]:
        """Get complete quarterly payment schedule"""
        
        year = year or datetime.now().year
        today = date.today()
        payments = []
        
        for quarter, (month, day) in QUARTERLY_DUE_DATES.items():
            due_year = year if quarter < 4 else year + 1
            due_date = date(due_year, month, day)
            
            reserve = await self.reserves._get_reserve_bucket(org_id, year, quarter)
            
            days_until = (due_date - today).days
            
            if days_until < 0:
                status = PaymentStatus.OVERDUE if not (reserve and reserve.paid_amount > 0) else PaymentStatus.PAID
            elif days_until <= 14:
                status = PaymentStatus.DUE_SOON
            elif days_until <= 45:
                status = PaymentStatus.UPCOMING
            else:
                status = PaymentStatus.NOT_DUE
            
            payments.append({
                "quarter": f"Q{quarter}",
                "tax_year": year,
                "due_date": due_date.isoformat(),
                "days_until_due": days_until,
                "federal_amount": str(reserve.federal_portion) if reserve else "0",
                "state_amount": str(reserve.state_portion) if reserve else "0",
                "total_amount": str(reserve.required_amount) if reserve else "0",
                "reserved": str(reserve.reserved_amount) if reserve else "0",
                "paid": str(reserve.paid_amount) if reserve else "0",
                "status": status.value,
                "funding_status": reserve.status.value if reserve else "UNDERFUNDED"
            })
        
        return {
            "tax_year": year,
            "payments": payments,
            "next_due": next((p for p in payments if p["status"] in ["UPCOMING", "DUE_SOON"]), None),
            "total_due_this_year": str(sum(
                Decimal(p["total_amount"]) for p in payments
            )),
            "total_paid_this_year": str(sum(
                Decimal(p["paid"]) for p in payments
            ))
        }
    
    async def schedule_auto_pay(
        self,
        org_id: str,
        quarter: int,
        year: int,
        days_before_due: int = 5
    ) -> Dict[str, Any]:
        """Schedule automatic payment for a quarter"""
        
        month, day = QUARTERLY_DUE_DATES[quarter]
        due_year = year if quarter < 4 else year + 1
        due_date = date(due_year, month, day)
        pay_date = due_date - timedelta(days=days_before_due)
        
        reserve = await self.reserves._get_reserve_bucket(org_id, year, quarter)
        
        if not reserve:
            return {"error": "No reserve found for this quarter"}
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO scheduled_tax_payments (
                    id, org_id, tax_year, quarter, due_date, scheduled_date,
                    federal_amount, state_amount, total_amount, status, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                ON CONFLICT (org_id, tax_year, quarter) DO UPDATE SET
                    scheduled_date = $6, status = $10
            """, f"PAY-{uuid.uuid4().hex[:12].upper()}", org_id, year, quarter,
                due_date, pay_date, float(reserve.federal_portion),
                float(reserve.state_portion), float(reserve.required_amount),
                PaymentStatus.SCHEDULED.value, datetime.now(timezone.utc))
        
        return {
            "quarter": f"Q{quarter} {year}",
            "due_date": due_date.isoformat(),
            "scheduled_date": pay_date.isoformat(),
            "federal_amount": str(reserve.federal_portion),
            "state_amount": str(reserve.state_portion),
            "total_amount": str(reserve.required_amount),
            "status": "SCHEDULED"
        }
    
    async def generate_voucher(
        self,
        org_id: str,
        quarter: int,
        year: int,
        voucher_type: str = "federal"  # "federal" or "state"
    ) -> Dict[str, Any]:
        """Generate payment voucher (1040-ES or state equivalent)"""
        
        reserve = await self.reserves._get_reserve_bucket(org_id, year, quarter)
        
        if not reserve:
            return {"error": "No reserve found for this quarter"}
        
        # Get taxpayer info
        profile = await self._get_tax_profile(org_id)
        
        voucher_data = {
            "voucher_type": f"1040-ES" if voucher_type == "federal" else f"{profile.state}-ES",
            "tax_year": year,
            "quarter": quarter,
            "due_date": reserve.due_date.isoformat(),
            "amount": str(reserve.federal_portion if voucher_type == "federal" else reserve.state_portion),
            "taxpayer_name": "[Your Name]",  # Would come from profile
            "taxpayer_ssn": "XXX-XX-XXXX",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "instructions": self._get_payment_instructions(voucher_type, profile.state)
        }
        
        return voucher_data
    
    def _get_payment_instructions(self, voucher_type: str, state: str) -> str:
        """Get payment instructions"""
        if voucher_type == "federal":
            return """
            FEDERAL ESTIMATED TAX PAYMENT OPTIONS:
            
            1. IRS Direct Pay (FREE): https://www.irs.gov/payments/direct-pay
            2. EFTPS (FREE): https://www.eftps.gov
            3. Credit/Debit Card (fees apply): https://www.irs.gov/payments/pay-taxes-by-credit-or-debit-card
            4. Mail check with Form 1040-ES voucher
            
            Make payable to: United States Treasury
            """
        else:
            return f"""
            STATE ESTIMATED TAX PAYMENT ({state}):
            
            Visit your state's tax website to make payment online.
            Most states accept electronic payments at no fee.
            """
    
    async def _get_tax_profile(self, org_id: str) -> TaxProfile:
        """Get tax profile for org"""
        # Would fetch from DB, using default for now
        return TaxProfile(org_id=org_id)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 6: TAX SCENARIO SIMULATOR
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TaxScenarioSimulator:
    """
    PILLAR 6: TAX SCENARIO SIMULATOR
    
    "What if" analysis for tax planning decisions.
    Compare different income/expense scenarios.
    """
    
    def __init__(self, calc_engine: TaxCalculationEngine):
        self.calc = calc_engine
    
    def simulate_scenario(
        self,
        name: str,
        annual_income: Decimal,
        annual_expenses: Decimal,
        state: str,
        additional_deductions: Decimal = Decimal("0"),
        entity_type: TaxEntityType = TaxEntityType.SOLE_PROPRIETOR
    ) -> TaxScenario:
        """Simulate a tax scenario"""
        
        total_deductions = annual_expenses + additional_deductions
        result = self.calc.calculate_full_tax(annual_income, total_deductions, state, entity_type)
        
        return TaxScenario(
            id=f"SCEN-{uuid.uuid4().hex[:8]}",
            name=name,
            description=f"Annual income: ${annual_income:,.0f}, Expenses: ${total_deductions:,.0f}",
            annual_income=annual_income,
            annual_expenses=annual_expenses,
            additional_deductions=additional_deductions,
            result=result
        )
    
    def compare_scenarios(
        self,
        scenario_a: TaxScenario,
        scenario_b: TaxScenario
    ) -> Dict[str, Any]:
        """Compare two tax scenarios"""
        
        if not scenario_a.result or not scenario_b.result:
            return {"error": "Both scenarios must have results"}
        
        a = scenario_a.result
        b = scenario_b.result
        
        return {
            "scenario_a": {
                "name": scenario_a.name,
                "income": str(scenario_a.annual_income),
                "total_tax": str(a.total_tax),
                "effective_rate": str(a.effective_tax_rate)
            },
            "scenario_b": {
                "name": scenario_b.name,
                "income": str(scenario_b.annual_income),
                "total_tax": str(b.total_tax),
                "effective_rate": str(b.effective_tax_rate)
            },
            "differences": {
                "income_difference": str(scenario_b.annual_income - scenario_a.annual_income),
                "tax_difference": str(b.total_tax - a.total_tax),
                "rate_difference": str(b.effective_tax_rate - a.effective_tax_rate),
                "federal_difference": str(b.federal_income_tax - a.federal_income_tax),
                "state_difference": str(b.state_income_tax - a.state_income_tax),
                "se_tax_difference": str(b.self_employment_tax - a.self_employment_tax)
            },
            "insights": self._generate_insights(scenario_a, scenario_b)
        }
    
    def project_annual_tax(
        self,
        ytd_income: Decimal,
        ytd_expenses: Decimal,
        months_elapsed: int,
        state: str
    ) -> Dict[str, Any]:
        """Project full year taxes based on YTD"""
        
        if months_elapsed <= 0:
            return {"error": "Invalid months elapsed"}
        
        # Simple linear projection
        monthly_income = ytd_income / months_elapsed
        monthly_expenses = ytd_expenses / months_elapsed
        
        projected_annual_income = monthly_income * 12
        projected_annual_expenses = monthly_expenses * 12
        
        result = self.calc.calculate_full_tax(
            projected_annual_income, projected_annual_expenses, state
        )
        
        return {
            "ytd": {
                "income": str(ytd_income),
                "expenses": str(ytd_expenses),
                "months": months_elapsed
            },
            "projected_annual": {
                "income": str(projected_annual_income),
                "expenses": str(projected_annual_expenses),
                "net_income": str(projected_annual_income - projected_annual_expenses)
            },
            "projected_tax": {
                "federal": str(result.federal_income_tax),
                "state": str(result.state_income_tax),
                "self_employment": str(result.self_employment_tax),
                "total": str(result.total_tax),
                "effective_rate": str(result.effective_tax_rate),
                "marginal_rate": str(result.marginal_tax_rate)
            },
            "quarterly_estimate": str((result.total_tax / 4).quantize(Decimal("0.01"))),
            "monthly_reserve_needed": str((result.total_tax / 12).quantize(Decimal("0.01")))
        }
    
    def _generate_insights(self, a: TaxScenario, b: TaxScenario) -> List[str]:
        """Generate insights from scenario comparison"""
        insights = []
        
        income_diff = b.annual_income - a.annual_income
        tax_diff = b.result.total_tax - a.result.total_tax
        
        if income_diff > 0:
            marginal_on_increase = (tax_diff / income_diff * 100).quantize(Decimal("0.1"))
            insights.append(
                f"The additional ${income_diff:,.0f} income would be taxed at ~{marginal_on_increase}% marginal rate"
            )
        
        if b.result.effective_tax_rate > Decimal("40"):
            insights.append(
                "Consider maximizing retirement contributions to reduce effective tax rate"
            )
        
        if b.result.self_employment_tax > Decimal("20000"):
            insights.append(
                "S-Corp election could potentially reduce self-employment tax burden"
            )
        
        return insights


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 7: YEAR-END REPORT GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TaxReportGenerator:
    """
    PILLAR 7: YEAR-END TAX REPORT GENERATOR
    
    Generate all reports needed for tax filing.
    Schedule C, 1099s, deduction summaries, and more.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, calc_engine: TaxCalculationEngine):
        self.db = db_pool
        self.calc = calc_engine
    
    async def generate_schedule_c_summary(
        self,
        org_id: str,
        business_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Generate Schedule C summary for a business"""
        
        data = await self._get_business_financials(org_id, business_id, year)
        
        return {
            "report_type": "Schedule C Summary",
            "tax_year": year,
            "business_id": business_id,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "part_i_income": {
                "line_1_gross_receipts": str(data["gross_receipts"]),
                "line_2_returns_allowances": "0",
                "line_3_subtotal": str(data["gross_receipts"]),
                "line_4_cost_of_goods_sold": "0",
                "line_5_gross_profit": str(data["gross_receipts"]),
                "line_6_other_income": "0",
                "line_7_gross_income": str(data["gross_receipts"])
            },
            "part_ii_expenses": data["expenses_by_category"],
            "line_28_total_expenses": str(data["total_expenses"]),
            "line_29_tentative_profit": str(data["net_profit"]),
            "line_31_net_profit_loss": str(data["net_profit"])
        }
    
    async def generate_expense_summary(
        self,
        org_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Generate expense summary by category"""
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT category, SUM(amount) as total, COUNT(*) as count
                FROM tax_events
                WHERE org_id = $1 
                AND EXTRACT(YEAR FROM created_at) = $2
                AND type = 'expense'
                GROUP BY category
                ORDER BY total DESC
            """, org_id, year)
        
        categories = []
        total = Decimal("0")
        
        for row in rows:
            amount = Decimal(str(row["total"]))
            total += amount
            categories.append({
                "category": row["category"],
                "amount": str(amount),
                "transaction_count": row["count"],
                "percentage": str((amount / total * 100).quantize(Decimal("0.1"))) if total > 0 else "0"
            })
        
        return {
            "report_type": "Expense Summary",
            "tax_year": year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "total_expenses": str(total),
            "categories": categories
        }
    
    async def generate_quarterly_payment_history(
        self,
        org_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Generate quarterly payment history"""
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM tax_reserves
                WHERE org_id = $1 AND tax_year = $2
                ORDER BY quarter
            """, org_id, year)
        
        payments = []
        total_paid = Decimal("0")
        
        for row in rows:
            paid = Decimal(str(row.get("paid_amount", 0)))
            total_paid += paid
            payments.append({
                "quarter": f"Q{row['quarter']}",
                "due_date": row["due_date"].isoformat(),
                "required": str(row["required_amount"]),
                "paid": str(paid),
                "paid_date": row.get("paid_at").isoformat() if row.get("paid_at") else None,
                "status": row["payment_status"]
            })
        
        return {
            "report_type": "Quarterly Payment History",
            "tax_year": year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "payments": payments,
            "total_paid": str(total_paid)
        }
    
    async def generate_complete_tax_package(
        self,
        org_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Generate complete tax preparation package"""
        
        # Get all businesses
        async with self.db.acquire() as conn:
            businesses = await conn.fetch("""
                SELECT id, name FROM businesses
                WHERE parent_id = $1 AND status = 'ACTIVE'
            """, org_id)
        
        package = {
            "report_type": "Complete Tax Package",
            "tax_year": year,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "schedule_c_summaries": [],
            "expense_summary": await self.generate_expense_summary(org_id, year),
            "quarterly_payments": await self.generate_quarterly_payment_history(org_id, year),
            "totals": {}
        }
        
        total_income = Decimal("0")
        total_expenses = Decimal("0")
        
        for biz in businesses:
            summary = await self.generate_schedule_c_summary(org_id, biz["id"], year)
            package["schedule_c_summaries"].append({
                "business_name": biz["name"],
                "summary": summary
            })
            total_income += Decimal(summary["part_i_income"]["line_7_gross_income"])
            total_expenses += Decimal(summary["line_28_total_expenses"])
        
        package["totals"] = {
            "total_gross_income": str(total_income),
            "total_expenses": str(total_expenses),
            "total_net_profit": str(total_income - total_expenses)
        }
        
        return package
    
    async def _get_business_financials(
        self,
        org_id: str,
        business_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Get business financial data for reports"""
        
        async with self.db.acquire() as conn:
            # Get totals
            totals = await conn.fetchrow("""
                SELECT 
                    COALESCE(SUM(CASE WHEN type = 'income' THEN amount ELSE 0 END), 0) as income,
                    COALESCE(SUM(CASE WHEN type = 'expense' THEN amount ELSE 0 END), 0) as expenses
                FROM tax_events
                WHERE org_id = $1 AND business_id = $2
                AND EXTRACT(YEAR FROM created_at) = $3
            """, org_id, business_id, year)
            
            # Get expenses by category
            expense_rows = await conn.fetch("""
                SELECT category, SUM(amount) as total
                FROM tax_events
                WHERE org_id = $1 AND business_id = $2
                AND EXTRACT(YEAR FROM created_at) = $3
                AND type = 'expense'
                GROUP BY category
            """, org_id, business_id, year)
        
        gross = Decimal(str(totals["income"]))
        expenses = Decimal(str(totals["expenses"]))
        
        expenses_by_cat = {}
        for row in expense_rows:
            expenses_by_cat[row["category"]] = str(row["total"])
        
        return {
            "gross_receipts": gross,
            "total_expenses": expenses,
            "net_profit": gross - expenses,
            "expenses_by_category": expenses_by_cat
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# QUANTUM TAX FORTRESS - MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class QuantumTaxFortress:
    """
    QUANTUM TAX FORTRESS - Main Service
    
    The complete AI-powered tax intelligence system.
    Combines all 7 pillars into one unified service.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        
        # Initialize all pillars
        self.calc_engine = TaxCalculationEngine()
        self.reserve_manager = TaxReserveManager(db_pool, self.calc_engine)
        self.multi_entity = MultiEntityTaxOptimizer(db_pool, self.calc_engine)
        self.deduction_ai = DeductionMaximizerAI(db_pool, self.calc_engine)
        self.quarterly_manager = QuarterlyPaymentManager(db_pool, self.reserve_manager)
        self.scenario_sim = TaxScenarioSimulator(self.calc_engine)
        self.report_gen = TaxReportGenerator(db_pool, self.calc_engine)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 1: Real-Time Tax Calculation
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    def calculate_tax(
        self,
        income: Decimal,
        deductions: Decimal,
        state: str
    ) -> TaxCalculationResult:
        """Calculate complete tax liability"""
        return self.calc_engine.calculate_full_tax(income, deductions, state)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 2: Reserve Management
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def process_income(
        self,
        org_id: str,
        business_id: str,
        amount: Decimal,
        income_type: IncomeType = IncomeType.BUSINESS_INCOME
    ) -> Dict[str, Any]:
        """Process income and automatically reserve taxes"""
        profile = TaxProfile(org_id=org_id)
        return await self.reserve_manager.process_income(
            org_id, business_id, amount, income_type, profile
        )
    
    async def get_reserve_status(self, org_id: str) -> Dict[str, Any]:
        """Get tax reserve status"""
        return await self.reserve_manager.get_reserve_status(org_id)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 3: Multi-Entity Optimization
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def get_consolidated_summary(self, org_id: str) -> Dict[str, Any]:
        """Get consolidated tax summary across all businesses"""
        return await self.multi_entity.get_consolidated_tax_summary(org_id)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 4: Deduction Maximizer
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def find_deduction_opportunities(self, org_id: str) -> Dict[str, Any]:
        """Find potential tax deduction opportunities"""
        profile = TaxProfile(org_id=org_id)
        return await self.deduction_ai.analyze_deduction_opportunities(org_id, profile)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 5: Quarterly Payments
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def get_payment_schedule(self, org_id: str, year: int = None) -> Dict[str, Any]:
        """Get quarterly payment schedule"""
        return await self.quarterly_manager.get_payment_schedule(org_id, year)
    
    async def schedule_auto_pay(
        self,
        org_id: str,
        quarter: int,
        year: int
    ) -> Dict[str, Any]:
        """Schedule automatic quarterly payment"""
        return await self.quarterly_manager.schedule_auto_pay(org_id, quarter, year)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 6: Scenario Simulation
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    def simulate_scenario(
        self,
        name: str,
        income: Decimal,
        expenses: Decimal,
        state: str
    ) -> TaxScenario:
        """Simulate a tax scenario"""
        return self.scenario_sim.simulate_scenario(name, income, expenses, state)
    
    def compare_scenarios(
        self,
        scenario_a: TaxScenario,
        scenario_b: TaxScenario
    ) -> Dict[str, Any]:
        """Compare two scenarios"""
        return self.scenario_sim.compare_scenarios(scenario_a, scenario_b)
    
    def project_annual_tax(
        self,
        ytd_income: Decimal,
        ytd_expenses: Decimal,
        months_elapsed: int,
        state: str
    ) -> Dict[str, Any]:
        """Project full year taxes"""
        return self.scenario_sim.project_annual_tax(
            ytd_income, ytd_expenses, months_elapsed, state
        )
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PILLAR 7: Report Generation
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def generate_tax_package(self, org_id: str, year: int) -> Dict[str, Any]:
        """Generate complete tax preparation package"""
        return await self.report_gen.generate_complete_tax_package(org_id, year)
    
    async def generate_schedule_c(
        self,
        org_id: str,
        business_id: str,
        year: int
    ) -> Dict[str, Any]:
        """Generate Schedule C summary"""
        return await self.report_gen.generate_schedule_c_summary(org_id, business_id, year)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional

app = FastAPI(
    title="Quantum Tax Fortress API",
    description="OMNI QUANTUM ELITE Tax Intelligence System",
    version="3.0.0"
)

# Initialize service (would use dependency injection in production)
# tax_fortress = QuantumTaxFortress(db_pool)


class CalculateTaxRequest(BaseModel):
    income: float
    deductions: float
    state: str = "CA"


class ProcessIncomeRequest(BaseModel):
    business_id: str
    amount: float
    income_type: str = "BUSINESS_INCOME"


class SimulateScenarioRequest(BaseModel):
    name: str
    income: float
    expenses: float
    state: str = "CA"


@app.get("/api/v1/tax/calculate")
async def calculate_tax(income: float, deductions: float, state: str = "CA"):
    """Calculate tax liability for given income"""
    engine = TaxCalculationEngine()
    result = engine.calculate_full_tax(
        Decimal(str(income)),
        Decimal(str(deductions)),
        state
    )
    return {
        "gross_income": str(result.gross_income),
        "taxable_income": str(result.taxable_income),
        "federal_tax": str(result.federal_income_tax),
        "state_tax": str(result.state_income_tax),
        "self_employment_tax": str(result.self_employment_tax),
        "total_tax": str(result.total_tax),
        "effective_rate": str(result.effective_tax_rate),
        "marginal_rate": str(result.marginal_tax_rate),
        "recommended_reserve": str(result.recommended_reserve),
        "reserve_percentage": str(result.reserve_percentage)
    }


@app.get("/api/v1/tax/reserve-status/{org_id}")
async def get_reserve_status(org_id: str):
    """Get tax reserve status for organization"""
    # Would call: return await tax_fortress.get_reserve_status(org_id)
    return {
        "status": "Implementation requires database connection",
        "org_id": org_id
    }


@app.get("/api/v1/tax/quarterly-schedule/{org_id}")
async def get_quarterly_schedule(org_id: str, year: Optional[int] = None):
    """Get quarterly payment schedule"""
    # Would call: return await tax_fortress.get_payment_schedule(org_id, year)
    return {
        "status": "Implementation requires database connection",
        "org_id": org_id
    }


@app.get("/api/v1/tax/deduction-opportunities/{org_id}")
async def get_deduction_opportunities(org_id: str):
    """Find potential tax deduction opportunities"""
    # Would call: return await tax_fortress.find_deduction_opportunities(org_id)
    return {
        "status": "Implementation requires database connection",
        "org_id": org_id
    }


@app.post("/api/v1/tax/simulate")
async def simulate_scenario(request: SimulateScenarioRequest):
    """Simulate a tax scenario"""
    simulator = TaxScenarioSimulator(TaxCalculationEngine())
    scenario = simulator.simulate_scenario(
        request.name,
        Decimal(str(request.income)),
        Decimal(str(request.expenses)),
        request.state
    )
    return {
        "name": scenario.name,
        "income": str(scenario.annual_income),
        "expenses": str(scenario.annual_expenses),
        "total_tax": str(scenario.result.total_tax),
        "effective_rate": str(scenario.result.effective_tax_rate),
        "marginal_rate": str(scenario.result.marginal_tax_rate)
    }


@app.get("/api/v1/tax/project-annual")
async def project_annual_tax(
    ytd_income: float,
    ytd_expenses: float,
    months_elapsed: int,
    state: str = "CA"
):
    """Project annual taxes based on YTD data"""
    simulator = TaxScenarioSimulator(TaxCalculationEngine())
    return simulator.project_annual_tax(
        Decimal(str(ytd_income)),
        Decimal(str(ytd_expenses)),
        months_elapsed,
        state
    )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4011)
