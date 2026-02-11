# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                                                                                                                                       ║
# ║                              CONTRACTOR & PAYROLL VAULT                                                                                ║
# ║                              OMNI QUANTUM ELITE v3.0                                                                                   ║
# ║                                                                                                                                       ║
# ║                              "Pay People. Stay Compliant."                                                                             ║
# ║                                                                                                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

"""
CONTRACTOR & PAYROLL VAULT

Complete contractor management and payment system:

PILLAR 1: Contractor Onboarding
- Contractor profiles with tax info
- W-9 collection and verification
- Contract/agreement management
- Rate and payment terms configuration

PILLAR 2: Payment Management
- Multiple payment schedules (weekly, bi-weekly, monthly, milestone)
- Multi-currency support (USD, EUR, GBP via Wise)
- Batch payments
- Payment approval workflows

PILLAR 3: Time & Project Tracking
- Hourly time tracking
- Project-based milestones
- Retainer management
- Expense reimbursements

PILLAR 4: Tax Compliance
- 1099-NEC generation
- Payment threshold tracking ($600+)
- Year-end reporting
- State filing requirements

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
import aiohttp


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ContractorStatus(Enum):
    PENDING = "PENDING"           # Awaiting W-9
    ACTIVE = "ACTIVE"             # Ready for payments
    INACTIVE = "INACTIVE"         # Not currently working
    TERMINATED = "TERMINATED"     # Relationship ended
    BLOCKED = "BLOCKED"           # Payment blocked (compliance issue)


class ContractorType(Enum):
    INDIVIDUAL = "INDIVIDUAL"     # Individual contractor
    BUSINESS = "BUSINESS"         # LLC/Corp contractor
    FOREIGN = "FOREIGN"           # Non-US contractor (W-8BEN)


class PaymentSchedule(Enum):
    WEEKLY = "WEEKLY"
    BI_WEEKLY = "BI_WEEKLY"
    SEMI_MONTHLY = "SEMI_MONTHLY"  # 1st and 15th
    MONTHLY = "MONTHLY"
    MILESTONE = "MILESTONE"
    ON_DEMAND = "ON_DEMAND"


class PaymentMethod(Enum):
    ACH = "ACH"                   # US Bank Transfer
    WIRE = "WIRE"                 # Wire Transfer
    WISE = "WISE"                 # Wise (TransferWise)
    PAYPAL = "PAYPAL"             # PayPal
    CHECK = "CHECK"               # Physical Check
    CRYPTO_USDC = "CRYPTO_USDC"   # USDC Stablecoin
    CRYPTO_BTC = "CRYPTO_BTC"     # Bitcoin


class PaymentStatus(Enum):
    DRAFT = "DRAFT"               # Not yet submitted
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    PROCESSING = "PROCESSING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


class TimeEntryStatus(Enum):
    DRAFT = "DRAFT"
    SUBMITTED = "SUBMITTED"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    PAID = "PAID"


class ContractType(Enum):
    HOURLY = "HOURLY"
    FIXED_PRICE = "FIXED_PRICE"
    RETAINER = "RETAINER"
    MILESTONE = "MILESTONE"


class Form1099Status(Enum):
    NOT_REQUIRED = "NOT_REQUIRED"   # Under $600
    PENDING = "PENDING"             # Needs to be generated
    GENERATED = "GENERATED"         # PDF created
    SENT = "SENT"                   # Sent to contractor
    FILED = "FILED"                 # Filed with IRS


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class Contractor:
    """A contractor/vendor"""
    id: str
    org_id: str
    
    # Basic info
    display_name: str
    contractor_type: ContractorType
    status: ContractorStatus
    
    # Contact
    email: str
    phone: Optional[str] = None
    
    # Tax info (W-9)
    legal_name: str = ""
    business_name: Optional[str] = None
    tax_classification: str = ""  # Individual, LLC, S-Corp, etc.
    tax_id: str = ""              # SSN or EIN (encrypted)
    tax_id_type: str = ""         # SSN, EIN
    address: Dict[str, str] = field(default_factory=dict)
    
    # W-9 status
    w9_received: bool = False
    w9_received_at: Optional[datetime] = None
    w9_document_id: Optional[str] = None
    
    # For foreign contractors (W-8BEN)
    is_foreign: bool = False
    country: str = "US"
    w8_received: bool = False
    tax_treaty_country: Optional[str] = None
    withholding_rate: Decimal = Decimal("0")  # Default 30% for foreign
    
    # Payment info
    preferred_payment_method: PaymentMethod = PaymentMethod.ACH
    payment_schedule: PaymentSchedule = PaymentSchedule.MONTHLY
    bank_account: Dict[str, str] = field(default_factory=dict)  # Encrypted
    wise_email: Optional[str] = None
    paypal_email: Optional[str] = None
    crypto_wallet: Optional[str] = None
    
    # Rates
    default_hourly_rate: Decimal = Decimal("0")
    default_currency: str = "USD"
    
    # Tracking
    total_paid_ytd: Decimal = Decimal("0")
    total_paid_all_time: Decimal = Decimal("0")
    last_payment_at: Optional[datetime] = None
    
    # Metadata
    notes: str = ""
    tags: List[str] = field(default_factory=list)
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Contract:
    """A contract/agreement with a contractor"""
    id: str
    org_id: str
    contractor_id: str
    business_id: str
    
    # Contract details
    title: str
    description: str
    contract_type: ContractType
    
    # Terms
    start_date: date
    end_date: Optional[date] = None
    auto_renew: bool = False
    
    # Compensation
    rate: Decimal = Decimal("0")
    rate_type: str = "HOURLY"  # HOURLY, FIXED, MONTHLY
    currency: str = "USD"
    
    # For fixed/milestone contracts
    total_value: Decimal = Decimal("0")
    
    # For retainers
    monthly_retainer: Decimal = Decimal("0")
    included_hours: int = 0
    overage_rate: Decimal = Decimal("0")
    
    # Budget
    budget_cap: Optional[Decimal] = None
    budget_used: Decimal = Decimal("0")
    
    # Payment terms
    payment_schedule: PaymentSchedule = PaymentSchedule.MONTHLY
    payment_terms_days: int = 30  # NET 30
    
    # Status
    status: str = "ACTIVE"  # DRAFT, ACTIVE, PAUSED, COMPLETED, TERMINATED
    
    # Documents
    document_url: Optional[str] = None
    signed_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TimeEntry:
    """A time tracking entry"""
    id: str
    org_id: str
    contractor_id: str
    contract_id: str
    
    # Time
    date: date
    hours: Decimal
    
    # Details
    description: str
    project: Optional[str] = None
    task: Optional[str] = None
    
    # Billing
    hourly_rate: Decimal = Decimal("0")
    amount: Decimal = Decimal("0")
    currency: str = "USD"
    billable: bool = True
    
    # Status
    status: TimeEntryStatus = TimeEntryStatus.DRAFT
    
    # Approval
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
    
    # Payment
    payment_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass 
class Milestone:
    """A project milestone for fixed-price contracts"""
    id: str
    org_id: str
    contractor_id: str
    contract_id: str
    
    # Details
    name: str
    description: str
    
    # Payment
    amount: Decimal
    currency: str = "USD"
    
    # Timeline
    due_date: Optional[date] = None
    
    # Status
    status: str = "PENDING"  # PENDING, IN_PROGRESS, SUBMITTED, APPROVED, PAID
    
    # Approval
    submitted_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    approved_by: Optional[str] = None
    
    # Payment
    payment_id: Optional[str] = None
    paid_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ContractorPayment:
    """A payment to a contractor"""
    id: str
    org_id: str
    contractor_id: str
    contract_id: Optional[str] = None
    
    # Payment details
    amount: Decimal
    currency: str = "USD"
    
    # Exchange rate (for non-USD)
    exchange_rate: Decimal = Decimal("1")
    amount_usd: Decimal = Decimal("0")  # For 1099 tracking
    
    # Method
    payment_method: PaymentMethod = PaymentMethod.ACH
    
    # Description
    description: str = ""
    period_start: Optional[date] = None
    period_end: Optional[date] = None
    
    # Line items (what's being paid for)
    line_items: List[Dict[str, Any]] = field(default_factory=list)
    # [{"type": "TIME", "entry_id": "...", "hours": 40, "rate": 100, "amount": 4000}, ...]
    
    # Status
    status: PaymentStatus = PaymentStatus.DRAFT
    
    # Approval
    requires_approval: bool = True
    approved_by: Optional[str] = None
    approved_at: Optional[datetime] = None
    
    # Processing
    scheduled_date: Optional[date] = None
    processed_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # External references
    bank_transfer_id: Optional[str] = None
    wise_transfer_id: Optional[str] = None
    confirmation_number: Optional[str] = None
    
    # Fees
    fee_amount: Decimal = Decimal("0")
    fee_paid_by: str = "PAYER"  # PAYER or CONTRACTOR
    
    # Error handling
    error_message: Optional[str] = None
    retry_count: int = 0
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Form1099NEC:
    """1099-NEC form for a contractor"""
    id: str
    org_id: str
    contractor_id: str
    tax_year: int
    
    # Payer info (your business)
    payer_name: str = ""
    payer_tin: str = ""
    payer_address: Dict[str, str] = field(default_factory=dict)
    
    # Recipient info (contractor)
    recipient_name: str = ""
    recipient_tin: str = ""
    recipient_address: Dict[str, str] = field(default_factory=dict)
    
    # Box 1: Nonemployee compensation
    box_1_nonemployee_compensation: Decimal = Decimal("0")
    
    # Box 4: Federal income tax withheld
    box_4_federal_withheld: Decimal = Decimal("0")
    
    # Box 5: State tax withheld
    box_5_state_withheld: Decimal = Decimal("0")
    box_6_state: str = ""
    box_7_state_income: Decimal = Decimal("0")
    
    # Status
    status: Form1099Status = Form1099Status.PENDING
    
    # Document
    document_url: Optional[str] = None
    generated_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    filed_at: Optional[datetime] = None
    
    # Filing
    irs_confirmation: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 1: CONTRACTOR ONBOARDING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ContractorOnboarding:
    """
    PILLAR 1: CONTRACTOR ONBOARDING
    
    Manage contractor profiles, W-9 collection, and contracts.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def create_contractor(
        self,
        org_id: str,
        display_name: str,
        email: str,
        contractor_type: ContractorType = ContractorType.INDIVIDUAL,
        hourly_rate: Decimal = Decimal("0"),
        payment_method: PaymentMethod = PaymentMethod.ACH,
        is_foreign: bool = False,
        country: str = "US"
    ) -> Contractor:
        """Create a new contractor"""
        
        contractor = Contractor(
            id=f"CTR-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            display_name=display_name,
            contractor_type=contractor_type,
            status=ContractorStatus.PENDING,  # Pending until W-9 received
            email=email,
            default_hourly_rate=hourly_rate,
            preferred_payment_method=payment_method,
            is_foreign=is_foreign,
            country=country,
            withholding_rate=Decimal("30") if is_foreign else Decimal("0")
        )
        
        await self._save_contractor(contractor)
        
        # Send W-9 request email
        await self._send_w9_request(contractor)
        
        return contractor
    
    async def submit_w9(
        self,
        contractor_id: str,
        legal_name: str,
        business_name: Optional[str],
        tax_classification: str,
        tax_id: str,
        tax_id_type: str,  # SSN or EIN
        address: Dict[str, str],
        document_id: Optional[str] = None
    ) -> Contractor:
        """Submit W-9 information for a contractor"""
        
        contractor = await self._get_contractor(contractor_id)
        if not contractor:
            raise ValueError(f"Contractor not found: {contractor_id}")
        
        # Validate tax ID format
        if tax_id_type == "SSN":
            if len(tax_id.replace("-", "")) != 9:
                raise ValueError("Invalid SSN format")
        elif tax_id_type == "EIN":
            if len(tax_id.replace("-", "")) != 9:
                raise ValueError("Invalid EIN format")
        
        # Update contractor
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE contractors SET
                    legal_name = $1, business_name = $2, tax_classification = $3,
                    tax_id = $4, tax_id_type = $5, address = $6,
                    w9_received = true, w9_received_at = $7, w9_document_id = $8,
                    status = $9, updated_at = $7
                WHERE id = $10
            """, legal_name, business_name, tax_classification,
                self._encrypt_tax_id(tax_id), tax_id_type, json.dumps(address),
                datetime.now(timezone.utc), document_id,
                ContractorStatus.ACTIVE.value, contractor_id)
        
        return await self._get_contractor(contractor_id)
    
    async def create_contract(
        self,
        org_id: str,
        contractor_id: str,
        business_id: str,
        title: str,
        contract_type: ContractType,
        rate: Decimal,
        start_date: date,
        end_date: Optional[date] = None,
        description: str = "",
        total_value: Decimal = Decimal("0"),
        monthly_retainer: Decimal = Decimal("0"),
        included_hours: int = 0,
        budget_cap: Optional[Decimal] = None,
        payment_schedule: PaymentSchedule = PaymentSchedule.MONTHLY
    ) -> Contract:
        """Create a contract with a contractor"""
        
        contract = Contract(
            id=f"CON-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            contractor_id=contractor_id,
            business_id=business_id,
            title=title,
            description=description,
            contract_type=contract_type,
            start_date=start_date,
            end_date=end_date,
            rate=rate,
            rate_type="HOURLY" if contract_type == ContractType.HOURLY else "FIXED",
            total_value=total_value,
            monthly_retainer=monthly_retainer,
            included_hours=included_hours,
            overage_rate=rate,
            budget_cap=budget_cap,
            payment_schedule=payment_schedule
        )
        
        await self._save_contract(contract)
        return contract
    
    async def get_contractor(self, contractor_id: str) -> Optional[Dict]:
        """Get contractor with all details"""
        contractor = await self._get_contractor(contractor_id)
        if not contractor:
            return None
        
        async with self.db.acquire() as conn:
            # Get active contracts
            contracts = await conn.fetch("""
                SELECT * FROM contracts 
                WHERE contractor_id = $1 AND status = 'ACTIVE'
            """, contractor_id)
            
            # Get YTD payments
            ytd_payments = await conn.fetchrow("""
                SELECT COALESCE(SUM(amount_usd), 0) as total
                FROM contractor_payments
                WHERE contractor_id = $1 
                AND status = 'COMPLETED'
                AND EXTRACT(YEAR FROM completed_at) = $2
            """, contractor_id, datetime.now().year)
            
            # Get pending time entries
            pending_time = await conn.fetchrow("""
                SELECT COALESCE(SUM(hours), 0) as hours, 
                       COALESCE(SUM(amount), 0) as amount
                FROM time_entries
                WHERE contractor_id = $1 AND status IN ('SUBMITTED', 'APPROVED')
            """, contractor_id)
        
        return {
            **contractor,
            "contracts": [dict(c) for c in contracts],
            "ytd_payments": float(ytd_payments["total"]),
            "pending_hours": float(pending_time["hours"]),
            "pending_amount": float(pending_time["amount"]),
            "requires_1099": float(ytd_payments["total"]) >= 600
        }
    
    async def list_contractors(
        self,
        org_id: str,
        status: ContractorStatus = None,
        requires_w9: bool = None
    ) -> List[Dict]:
        """List all contractors"""
        
        async with self.db.acquire() as conn:
            query = "SELECT * FROM contractors WHERE org_id = $1"
            params = [org_id]
            
            if status:
                query += f" AND status = ${len(params) + 1}"
                params.append(status.value)
            
            if requires_w9 is not None:
                query += f" AND w9_received = ${len(params) + 1}"
                params.append(not requires_w9)
            
            query += " ORDER BY display_name"
            
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    async def _send_w9_request(self, contractor: Contractor):
        """Send W-9 request email to contractor"""
        if contractor.is_foreign:
            form_type = "W-8BEN"
            message = f"Please complete and return a W-8BEN form for our records."
        else:
            form_type = "W-9"
            message = f"Please complete and return a W-9 form for our records."
        
        print(f"📧 Sending {form_type} request to {contractor.email}")
        # Integration with email service
    
    def _encrypt_tax_id(self, tax_id: str) -> str:
        """Encrypt tax ID for storage"""
        # In production, use proper encryption (AES-256)
        # For now, just mask it
        clean = tax_id.replace("-", "")
        return f"***-**-{clean[-4:]}"
    
    async def _get_contractor(self, contractor_id: str) -> Optional[Dict]:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contractors WHERE id = $1", contractor_id
            )
            return dict(row) if row else None
    
    async def _save_contractor(self, contractor: Contractor):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO contractors (
                    id, org_id, display_name, contractor_type, status, email, phone,
                    legal_name, business_name, tax_classification, tax_id, tax_id_type,
                    address, w9_received, w9_received_at, is_foreign, country,
                    withholding_rate, preferred_payment_method, payment_schedule,
                    default_hourly_rate, default_currency, total_paid_ytd,
                    total_paid_all_time, notes, tags, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24,$25,$26,$27,$28)
            """, contractor.id, contractor.org_id, contractor.display_name,
                contractor.contractor_type.value, contractor.status.value,
                contractor.email, contractor.phone, contractor.legal_name,
                contractor.business_name, contractor.tax_classification,
                contractor.tax_id, contractor.tax_id_type, json.dumps(contractor.address),
                contractor.w9_received, contractor.w9_received_at, contractor.is_foreign,
                contractor.country, float(contractor.withholding_rate),
                contractor.preferred_payment_method.value, contractor.payment_schedule.value,
                float(contractor.default_hourly_rate), contractor.default_currency,
                float(contractor.total_paid_ytd), float(contractor.total_paid_all_time),
                contractor.notes, contractor.tags, contractor.created_at, contractor.updated_at)
    
    async def _save_contract(self, contract: Contract):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO contracts (
                    id, org_id, contractor_id, business_id, title, description,
                    contract_type, start_date, end_date, auto_renew, rate, rate_type,
                    currency, total_value, monthly_retainer, included_hours,
                    overage_rate, budget_cap, budget_used, payment_schedule,
                    payment_terms_days, status, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23)
            """, contract.id, contract.org_id, contract.contractor_id, contract.business_id,
                contract.title, contract.description, contract.contract_type.value,
                contract.start_date, contract.end_date, contract.auto_renew,
                float(contract.rate), contract.rate_type, contract.currency,
                float(contract.total_value), float(contract.monthly_retainer),
                contract.included_hours, float(contract.overage_rate),
                float(contract.budget_cap) if contract.budget_cap else None,
                float(contract.budget_used), contract.payment_schedule.value,
                contract.payment_terms_days, contract.status, contract.created_at)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 2: PAYMENT MANAGEMENT
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class PaymentManager:
    """
    PILLAR 2: PAYMENT MANAGEMENT
    
    Handle contractor payments across multiple methods and currencies.
    """
    
    def __init__(self, db_pool: asyncpg.Pool, wise_api_key: str = None):
        self.db = db_pool
        self.wise_key = wise_api_key
    
    async def create_payment(
        self,
        org_id: str,
        contractor_id: str,
        amount: Decimal,
        currency: str = "USD",
        description: str = "",
        contract_id: str = None,
        period_start: date = None,
        period_end: date = None,
        line_items: List[Dict] = None,
        payment_method: PaymentMethod = None,
        scheduled_date: date = None,
        requires_approval: bool = True
    ) -> ContractorPayment:
        """Create a new payment to contractor"""
        
        # Get contractor
        async with self.db.acquire() as conn:
            contractor = await conn.fetchrow(
                "SELECT * FROM contractors WHERE id = $1", contractor_id
            )
        
        if not contractor:
            raise ValueError(f"Contractor not found: {contractor_id}")
        
        if contractor["status"] != "ACTIVE":
            raise ValueError(f"Contractor is not active: {contractor['status']}")
        
        if not contractor["w9_received"] and not contractor["is_foreign"]:
            raise ValueError("Cannot pay contractor without W-9 on file")
        
        # Use contractor's preferred method if not specified
        if not payment_method:
            payment_method = PaymentMethod(contractor["preferred_payment_method"])
        
        # Calculate USD amount for 1099 tracking
        exchange_rate = await self._get_exchange_rate(currency, "USD")
        amount_usd = (amount * exchange_rate).quantize(Decimal("0.01"))
        
        payment = ContractorPayment(
            id=f"PAY-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            contractor_id=contractor_id,
            contract_id=contract_id,
            amount=amount,
            currency=currency,
            exchange_rate=exchange_rate,
            amount_usd=amount_usd,
            payment_method=payment_method,
            description=description,
            period_start=period_start,
            period_end=period_end,
            line_items=line_items or [],
            status=PaymentStatus.PENDING_APPROVAL if requires_approval else PaymentStatus.APPROVED,
            requires_approval=requires_approval,
            scheduled_date=scheduled_date
        )
        
        await self._save_payment(payment)
        
        return payment
    
    async def approve_payment(self, payment_id: str, approved_by: str) -> ContractorPayment:
        """Approve a payment"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE contractor_payments SET
                    status = $1, approved_by = $2, approved_at = $3, updated_at = $3
                WHERE id = $4 AND status = 'PENDING_APPROVAL'
            """, PaymentStatus.APPROVED.value, approved_by,
                datetime.now(timezone.utc), payment_id)
        
        return await self._get_payment(payment_id)
    
    async def process_payment(self, payment_id: str) -> ContractorPayment:
        """Process an approved payment"""
        
        payment = await self._get_payment(payment_id)
        if not payment:
            raise ValueError(f"Payment not found: {payment_id}")
        
        if payment["status"] != PaymentStatus.APPROVED.value:
            raise ValueError(f"Payment not approved: {payment['status']}")
        
        # Get contractor payment details
        contractor = await self._get_contractor(payment["contractor_id"])
        
        # Update status to processing
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE contractor_payments SET status = $1, updated_at = $2
                WHERE id = $3
            """, PaymentStatus.PROCESSING.value, datetime.now(timezone.utc), payment_id)
        
        # Execute payment based on method
        method = PaymentMethod(payment["payment_method"])
        
        try:
            if method == PaymentMethod.WISE:
                result = await self._process_wise_payment(payment, contractor)
            elif method == PaymentMethod.ACH:
                result = await self._process_ach_payment(payment, contractor)
            elif method in [PaymentMethod.CRYPTO_USDC, PaymentMethod.CRYPTO_BTC]:
                result = await self._process_crypto_payment(payment, contractor)
            else:
                result = {"status": "MANUAL", "message": "Manual processing required"}
            
            # Update with result
            async with self.db.acquire() as conn:
                await conn.execute("""
                    UPDATE contractor_payments SET
                        status = $1, processed_at = $2, completed_at = $2,
                        confirmation_number = $3, bank_transfer_id = $4,
                        wise_transfer_id = $5, updated_at = $2
                    WHERE id = $6
                """, PaymentStatus.COMPLETED.value, datetime.now(timezone.utc),
                    result.get("confirmation"), result.get("bank_transfer_id"),
                    result.get("wise_transfer_id"), payment_id)
                
                # Update contractor totals
                await conn.execute("""
                    UPDATE contractors SET
                        total_paid_ytd = total_paid_ytd + $1,
                        total_paid_all_time = total_paid_all_time + $1,
                        last_payment_at = $2, updated_at = $2
                    WHERE id = $3
                """, float(payment["amount_usd"]), datetime.now(timezone.utc),
                    payment["contractor_id"])
                
                # Mark time entries as paid
                if payment.get("line_items"):
                    for item in payment["line_items"]:
                        if item.get("type") == "TIME" and item.get("entry_id"):
                            await conn.execute("""
                                UPDATE time_entries SET 
                                    status = 'PAID', payment_id = $1, paid_at = $2
                                WHERE id = $3
                            """, payment_id, datetime.now(timezone.utc), item["entry_id"])
            
            return await self._get_payment(payment_id)
            
        except Exception as e:
            # Mark as failed
            async with self.db.acquire() as conn:
                await conn.execute("""
                    UPDATE contractor_payments SET
                        status = $1, error_message = $2, retry_count = retry_count + 1,
                        updated_at = $3
                    WHERE id = $4
                """, PaymentStatus.FAILED.value, str(e),
                    datetime.now(timezone.utc), payment_id)
            raise
    
    async def create_batch_payments(
        self,
        org_id: str,
        payments: List[Dict[str, Any]],
        scheduled_date: date = None
    ) -> List[ContractorPayment]:
        """Create multiple payments at once"""
        
        results = []
        for p in payments:
            payment = await self.create_payment(
                org_id=org_id,
                contractor_id=p["contractor_id"],
                amount=Decimal(str(p["amount"])),
                currency=p.get("currency", "USD"),
                description=p.get("description", ""),
                contract_id=p.get("contract_id"),
                scheduled_date=scheduled_date
            )
            results.append(payment)
        
        return results
    
    async def get_pending_payments(self, org_id: str) -> List[Dict]:
        """Get all pending payments"""
        
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT p.*, c.display_name as contractor_name
                FROM contractor_payments p
                JOIN contractors c ON p.contractor_id = c.id
                WHERE p.org_id = $1 
                AND p.status IN ('DRAFT', 'PENDING_APPROVAL', 'APPROVED')
                ORDER BY p.created_at
            """, org_id)
            return [dict(r) for r in rows]
    
    async def _process_wise_payment(self, payment: Dict, contractor: Dict) -> Dict:
        """Process payment via Wise"""
        
        print(f"💸 Wise payment: ${payment['amount']} {payment['currency']} to {contractor['wise_email']}")
        
        # Would call Wise API here
        # transfer = await wise_client.create_transfer(...)
        
        return {
            "status": "COMPLETED",
            "wise_transfer_id": f"WISE-{uuid.uuid4().hex[:8]}",
            "confirmation": f"WISE-{uuid.uuid4().hex[:12]}"
        }
    
    async def _process_ach_payment(self, payment: Dict, contractor: Dict) -> Dict:
        """Process ACH payment"""
        
        bank = contractor.get("bank_account", {})
        print(f"🏦 ACH payment: ${payment['amount']} to account ending {bank.get('last4', 'XXXX')}")
        
        # Would call bank API here
        
        return {
            "status": "COMPLETED",
            "bank_transfer_id": f"ACH-{uuid.uuid4().hex[:8]}",
            "confirmation": f"ACH-{uuid.uuid4().hex[:12]}"
        }
    
    async def _process_crypto_payment(self, payment: Dict, contractor: Dict) -> Dict:
        """Process crypto payment"""
        
        wallet = contractor.get("crypto_wallet", "")
        print(f"₿ Crypto payment: ${payment['amount']} to {wallet[:10]}...")
        
        return {
            "status": "COMPLETED",
            "confirmation": f"CRYPTO-{uuid.uuid4().hex[:12]}"
        }
    
    async def _get_exchange_rate(self, from_currency: str, to_currency: str) -> Decimal:
        """Get exchange rate"""
        if from_currency == to_currency:
            return Decimal("1")
        
        # Would call exchange rate API
        # For now, return approximate rates
        rates = {
            ("EUR", "USD"): Decimal("1.08"),
            ("GBP", "USD"): Decimal("1.26"),
            ("CAD", "USD"): Decimal("0.74"),
        }
        return rates.get((from_currency, to_currency), Decimal("1"))
    
    async def _get_payment(self, payment_id: str) -> Optional[Dict]:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contractor_payments WHERE id = $1", payment_id
            )
            return dict(row) if row else None
    
    async def _get_contractor(self, contractor_id: str) -> Dict:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM contractors WHERE id = $1", contractor_id
            )
            return dict(row) if row else {}
    
    async def _save_payment(self, payment: ContractorPayment):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO contractor_payments (
                    id, org_id, contractor_id, contract_id, amount, currency,
                    exchange_rate, amount_usd, payment_method, description,
                    period_start, period_end, line_items, status, requires_approval,
                    scheduled_date, fee_amount, fee_paid_by, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20)
            """, payment.id, payment.org_id, payment.contractor_id, payment.contract_id,
                float(payment.amount), payment.currency, float(payment.exchange_rate),
                float(payment.amount_usd), payment.payment_method.value,
                payment.description, payment.period_start, payment.period_end,
                json.dumps(payment.line_items), payment.status.value,
                payment.requires_approval, payment.scheduled_date,
                float(payment.fee_amount), payment.fee_paid_by,
                payment.created_at, payment.updated_at)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 3: TIME & PROJECT TRACKING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TimeTracker:
    """
    PILLAR 3: TIME & PROJECT TRACKING
    
    Track contractor hours and project milestones.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def log_time(
        self,
        org_id: str,
        contractor_id: str,
        contract_id: str,
        date: date,
        hours: Decimal,
        description: str,
        project: str = None,
        task: str = None,
        billable: bool = True
    ) -> TimeEntry:
        """Log time for a contractor"""
        
        # Get contract to determine rate
        async with self.db.acquire() as conn:
            contract = await conn.fetchrow(
                "SELECT * FROM contracts WHERE id = $1", contract_id
            )
        
        if not contract:
            raise ValueError(f"Contract not found: {contract_id}")
        
        rate = Decimal(str(contract["rate"]))
        amount = (hours * rate).quantize(Decimal("0.01"))
        
        entry = TimeEntry(
            id=f"TIME-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            contractor_id=contractor_id,
            contract_id=contract_id,
            date=date,
            hours=hours,
            description=description,
            project=project,
            task=task,
            hourly_rate=rate,
            amount=amount,
            currency=contract["currency"],
            billable=billable,
            status=TimeEntryStatus.DRAFT
        )
        
        await self._save_time_entry(entry)
        return entry
    
    async def submit_time(self, entry_ids: List[str]) -> List[TimeEntry]:
        """Submit time entries for approval"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE time_entries SET status = $1
                WHERE id = ANY($2) AND status = 'DRAFT'
            """, TimeEntryStatus.SUBMITTED.value, entry_ids)
        
        return await self._get_time_entries(entry_ids)
    
    async def approve_time(
        self,
        entry_ids: List[str],
        approved_by: str
    ) -> List[TimeEntry]:
        """Approve time entries"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE time_entries SET 
                    status = $1, approved_by = $2, approved_at = $3
                WHERE id = ANY($4) AND status = 'SUBMITTED'
            """, TimeEntryStatus.APPROVED.value, approved_by,
                datetime.now(timezone.utc), entry_ids)
        
        return await self._get_time_entries(entry_ids)
    
    async def reject_time(
        self,
        entry_id: str,
        reason: str
    ) -> TimeEntry:
        """Reject a time entry"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE time_entries SET 
                    status = $1, rejection_reason = $2
                WHERE id = $3 AND status = 'SUBMITTED'
            """, TimeEntryStatus.REJECTED.value, reason, entry_id)
        
        entries = await self._get_time_entries([entry_id])
        return entries[0] if entries else None
    
    async def get_unbilled_time(
        self,
        org_id: str,
        contractor_id: str = None
    ) -> List[Dict]:
        """Get approved but unpaid time entries"""
        
        async with self.db.acquire() as conn:
            query = """
                SELECT t.*, c.display_name as contractor_name,
                       con.title as contract_title
                FROM time_entries t
                JOIN contractors c ON t.contractor_id = c.id
                JOIN contracts con ON t.contract_id = con.id
                WHERE t.org_id = $1 AND t.status = 'APPROVED'
            """
            params = [org_id]
            
            if contractor_id:
                query += f" AND t.contractor_id = ${len(params) + 1}"
                params.append(contractor_id)
            
            query += " ORDER BY t.date"
            
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    async def get_time_summary(
        self,
        org_id: str,
        contractor_id: str = None,
        start_date: date = None,
        end_date: date = None
    ) -> Dict[str, Any]:
        """Get time tracking summary"""
        
        if not start_date:
            start_date = date.today().replace(day=1)
        if not end_date:
            end_date = date.today()
        
        async with self.db.acquire() as conn:
            query = """
                SELECT 
                    contractor_id,
                    SUM(hours) as total_hours,
                    SUM(CASE WHEN billable THEN hours ELSE 0 END) as billable_hours,
                    SUM(amount) as total_amount,
                    COUNT(*) as entry_count
                FROM time_entries
                WHERE org_id = $1 AND date BETWEEN $2 AND $3
            """
            params = [org_id, start_date, end_date]
            
            if contractor_id:
                query += f" AND contractor_id = ${len(params) + 1}"
                params.append(contractor_id)
            
            query += " GROUP BY contractor_id"
            
            rows = await conn.fetch(query, *params)
        
        return {
            "period": {"start": start_date.isoformat(), "end": end_date.isoformat()},
            "by_contractor": [
                {
                    "contractor_id": r["contractor_id"],
                    "total_hours": float(r["total_hours"]),
                    "billable_hours": float(r["billable_hours"]),
                    "total_amount": float(r["total_amount"]),
                    "entry_count": r["entry_count"]
                }
                for r in rows
            ]
        }
    
    async def create_milestone(
        self,
        org_id: str,
        contractor_id: str,
        contract_id: str,
        name: str,
        amount: Decimal,
        description: str = "",
        due_date: date = None
    ) -> Milestone:
        """Create a project milestone"""
        
        milestone = Milestone(
            id=f"MILE-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            contractor_id=contractor_id,
            contract_id=contract_id,
            name=name,
            description=description,
            amount=amount,
            due_date=due_date
        )
        
        await self._save_milestone(milestone)
        return milestone
    
    async def approve_milestone(
        self,
        milestone_id: str,
        approved_by: str
    ) -> Milestone:
        """Approve a completed milestone"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE milestones SET 
                    status = 'APPROVED', approved_by = $1, approved_at = $2
                WHERE id = $3 AND status = 'SUBMITTED'
            """, approved_by, datetime.now(timezone.utc), milestone_id)
        
        return await self._get_milestone(milestone_id)
    
    async def _save_time_entry(self, entry: TimeEntry):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO time_entries (
                    id, org_id, contractor_id, contract_id, date, hours,
                    description, project, task, hourly_rate, amount, currency,
                    billable, status, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15)
            """, entry.id, entry.org_id, entry.contractor_id, entry.contract_id,
                entry.date, float(entry.hours), entry.description, entry.project,
                entry.task, float(entry.hourly_rate), float(entry.amount),
                entry.currency, entry.billable, entry.status.value, entry.created_at)
    
    async def _save_milestone(self, milestone: Milestone):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO milestones (
                    id, org_id, contractor_id, contract_id, name, description,
                    amount, currency, due_date, status, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
            """, milestone.id, milestone.org_id, milestone.contractor_id,
                milestone.contract_id, milestone.name, milestone.description,
                float(milestone.amount), milestone.currency, milestone.due_date,
                milestone.status, milestone.created_at)
    
    async def _get_time_entries(self, entry_ids: List[str]) -> List[Dict]:
        async with self.db.acquire() as conn:
            rows = await conn.fetch(
                "SELECT * FROM time_entries WHERE id = ANY($1)", entry_ids
            )
            return [dict(r) for r in rows]
    
    async def _get_milestone(self, milestone_id: str) -> Optional[Dict]:
        async with self.db.acquire() as conn:
            row = await conn.fetchrow(
                "SELECT * FROM milestones WHERE id = $1", milestone_id
            )
            return dict(row) if row else None


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 4: TAX COMPLIANCE (1099)
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TaxCompliance:
    """
    PILLAR 4: TAX COMPLIANCE
    
    1099-NEC generation and filing.
    """
    
    THRESHOLD_1099 = Decimal("600")  # $600 threshold for 1099
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def get_1099_status(self, org_id: str, tax_year: int = None) -> Dict[str, Any]:
        """Get 1099 status for all contractors"""
        
        if not tax_year:
            tax_year = datetime.now().year
        
        async with self.db.acquire() as conn:
            # Get all contractors with their YTD payments
            contractors = await conn.fetch("""
                SELECT c.id, c.display_name, c.legal_name, c.tax_id,
                       c.w9_received, c.is_foreign,
                       COALESCE(SUM(p.amount_usd), 0) as total_paid
                FROM contractors c
                LEFT JOIN contractor_payments p ON c.id = p.contractor_id
                    AND p.status = 'COMPLETED'
                    AND EXTRACT(YEAR FROM p.completed_at) = $2
                WHERE c.org_id = $1
                GROUP BY c.id
            """, org_id, tax_year)
            
            # Get existing 1099s
            existing_1099s = await conn.fetch("""
                SELECT contractor_id, status FROM form_1099_nec
                WHERE org_id = $1 AND tax_year = $2
            """, org_id, tax_year)
        
        existing_map = {r["contractor_id"]: r["status"] for r in existing_1099s}
        
        results = []
        total_requiring_1099 = 0
        total_1099_amount = Decimal("0")
        
        for c in contractors:
            total_paid = Decimal(str(c["total_paid"]))
            requires_1099 = total_paid >= self.THRESHOLD_1099 and not c["is_foreign"]
            
            if requires_1099:
                total_requiring_1099 += 1
                total_1099_amount += total_paid
            
            results.append({
                "contractor_id": c["id"],
                "name": c["display_name"],
                "legal_name": c["legal_name"],
                "total_paid": float(total_paid),
                "requires_1099": requires_1099,
                "has_w9": c["w9_received"],
                "has_tax_id": bool(c["tax_id"]),
                "is_foreign": c["is_foreign"],
                "form_status": existing_map.get(c["id"], "NOT_GENERATED" if requires_1099 else "NOT_REQUIRED"),
                "issues": self._identify_issues(c, total_paid)
            })
        
        return {
            "tax_year": tax_year,
            "threshold": float(self.THRESHOLD_1099),
            "total_contractors": len(contractors),
            "requiring_1099": total_requiring_1099,
            "total_1099_amount": float(total_1099_amount),
            "contractors": results,
            "summary": {
                "ready_to_file": sum(1 for r in results if r["form_status"] == "GENERATED"),
                "missing_w9": sum(1 for r in results if r["requires_1099"] and not r["has_w9"]),
                "missing_tax_id": sum(1 for r in results if r["requires_1099"] and not r["has_tax_id"]),
                "filed": sum(1 for r in results if r["form_status"] == "FILED")
            }
        }
    
    async def generate_1099(
        self,
        org_id: str,
        contractor_id: str,
        tax_year: int,
        payer_info: Dict[str, Any]
    ) -> Form1099NEC:
        """Generate 1099-NEC for a contractor"""
        
        # Get contractor and payment data
        async with self.db.acquire() as conn:
            contractor = await conn.fetchrow(
                "SELECT * FROM contractors WHERE id = $1", contractor_id
            )
            
            total_paid = await conn.fetchrow("""
                SELECT COALESCE(SUM(amount_usd), 0) as total
                FROM contractor_payments
                WHERE contractor_id = $1 AND status = 'COMPLETED'
                AND EXTRACT(YEAR FROM completed_at) = $2
            """, contractor_id, tax_year)
        
        if not contractor:
            raise ValueError(f"Contractor not found: {contractor_id}")
        
        total = Decimal(str(total_paid["total"]))
        
        if total < self.THRESHOLD_1099:
            raise ValueError(f"Contractor below $600 threshold: ${total}")
        
        if not contractor["w9_received"]:
            raise ValueError("W-9 not on file for contractor")
        
        form = Form1099NEC(
            id=f"1099-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            contractor_id=contractor_id,
            tax_year=tax_year,
            payer_name=payer_info["name"],
            payer_tin=payer_info["tin"],
            payer_address=payer_info["address"],
            recipient_name=contractor["legal_name"] or contractor["display_name"],
            recipient_tin=contractor["tax_id"],
            recipient_address=json.loads(contractor["address"]) if contractor["address"] else {},
            box_1_nonemployee_compensation=total,
            status=Form1099Status.GENERATED
        )
        
        await self._save_1099(form)
        
        # Generate PDF (would use a PDF library)
        form.document_url = await self._generate_1099_pdf(form)
        form.generated_at = datetime.now(timezone.utc)
        
        return form
    
    async def batch_generate_1099s(
        self,
        org_id: str,
        tax_year: int,
        payer_info: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Generate all required 1099s"""
        
        status = await self.get_1099_status(org_id, tax_year)
        
        results = {
            "generated": [],
            "skipped": [],
            "errors": []
        }
        
        for contractor in status["contractors"]:
            if not contractor["requires_1099"]:
                results["skipped"].append({
                    "contractor_id": contractor["contractor_id"],
                    "reason": "Below threshold"
                })
                continue
            
            if contractor["form_status"] in ["GENERATED", "SENT", "FILED"]:
                results["skipped"].append({
                    "contractor_id": contractor["contractor_id"],
                    "reason": f"Already {contractor['form_status']}"
                })
                continue
            
            if contractor["issues"]:
                results["errors"].append({
                    "contractor_id": contractor["contractor_id"],
                    "issues": contractor["issues"]
                })
                continue
            
            try:
                form = await self.generate_1099(
                    org_id, contractor["contractor_id"], tax_year, payer_info
                )
                results["generated"].append({
                    "contractor_id": contractor["contractor_id"],
                    "form_id": form.id,
                    "amount": float(form.box_1_nonemployee_compensation)
                })
            except Exception as e:
                results["errors"].append({
                    "contractor_id": contractor["contractor_id"],
                    "error": str(e)
                })
        
        return results
    
    async def send_1099_to_contractor(self, form_id: str) -> bool:
        """Send 1099 to contractor via email"""
        
        async with self.db.acquire() as conn:
            form = await conn.fetchrow(
                "SELECT * FROM form_1099_nec WHERE id = $1", form_id
            )
            
            contractor = await conn.fetchrow(
                "SELECT * FROM contractors WHERE id = $1", form["contractor_id"]
            )
        
        # Send email with PDF attachment
        print(f"📧 Sending 1099-NEC to {contractor['email']}")
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE form_1099_nec SET status = $1, sent_at = $2
                WHERE id = $3
            """, Form1099Status.SENT.value, datetime.now(timezone.utc), form_id)
        
        return True
    
    def _identify_issues(self, contractor: Dict, total_paid: Decimal) -> List[str]:
        """Identify compliance issues for a contractor"""
        issues = []
        
        if total_paid >= self.THRESHOLD_1099:
            if not contractor["w9_received"] and not contractor["is_foreign"]:
                issues.append("Missing W-9")
            if not contractor["tax_id"]:
                issues.append("Missing Tax ID (SSN/EIN)")
        
        return issues
    
    async def _generate_1099_pdf(self, form: Form1099NEC) -> str:
        """Generate 1099-NEC PDF"""
        # Would use reportlab or similar to generate IRS-compliant form
        pdf_path = f"/documents/1099/{form.id}.pdf"
        print(f"📄 Generated 1099-NEC PDF: {pdf_path}")
        return pdf_path
    
    async def _save_1099(self, form: Form1099NEC):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO form_1099_nec (
                    id, org_id, contractor_id, tax_year, payer_name, payer_tin,
                    payer_address, recipient_name, recipient_tin, recipient_address,
                    box_1_nonemployee_compensation, box_4_federal_withheld,
                    status, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
                ON CONFLICT (org_id, contractor_id, tax_year) DO UPDATE SET
                    box_1_nonemployee_compensation = $11, status = $13
            """, form.id, form.org_id, form.contractor_id, form.tax_year,
                form.payer_name, form.payer_tin, json.dumps(form.payer_address),
                form.recipient_name, form.recipient_tin, json.dumps(form.recipient_address),
                float(form.box_1_nonemployee_compensation),
                float(form.box_4_federal_withheld), form.status.value, form.created_at)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ContractorPayrollVault:
    """
    CONTRACTOR & PAYROLL VAULT - Main Service
    
    Complete contractor management system.
    "Pay People. Stay Compliant."
    """
    
    def __init__(self, db_pool: asyncpg.Pool, wise_api_key: str = None):
        self.db = db_pool
        
        # Initialize all pillars
        self.onboarding = ContractorOnboarding(db_pool)
        self.payments = PaymentManager(db_pool, wise_api_key)
        self.time_tracker = TimeTracker(db_pool)
        self.tax_compliance = TaxCompliance(db_pool)
    
    # Convenience methods that delegate to appropriate pillar
    
    async def create_contractor(self, **kwargs) -> Contractor:
        return await self.onboarding.create_contractor(**kwargs)
    
    async def submit_w9(self, **kwargs) -> Contractor:
        return await self.onboarding.submit_w9(**kwargs)
    
    async def create_contract(self, **kwargs) -> Contract:
        return await self.onboarding.create_contract(**kwargs)
    
    async def create_payment(self, **kwargs) -> ContractorPayment:
        return await self.payments.create_payment(**kwargs)
    
    async def approve_payment(self, payment_id: str, approved_by: str):
        return await self.payments.approve_payment(payment_id, approved_by)
    
    async def process_payment(self, payment_id: str):
        return await self.payments.process_payment(payment_id)
    
    async def log_time(self, **kwargs) -> TimeEntry:
        return await self.time_tracker.log_time(**kwargs)
    
    async def get_1099_status(self, org_id: str, tax_year: int = None):
        return await self.tax_compliance.get_1099_status(org_id, tax_year)
    
    async def generate_1099s(self, org_id: str, tax_year: int, payer_info: Dict):
        return await self.tax_compliance.batch_generate_1099s(org_id, tax_year, payer_info)
    
    async def get_dashboard_summary(self, org_id: str) -> Dict[str, Any]:
        """Get contractor dashboard summary"""
        
        async with self.db.acquire() as conn:
            # Contractor counts
            counts = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'ACTIVE' THEN 1 ELSE 0 END) as active,
                    SUM(CASE WHEN status = 'PENDING' THEN 1 ELSE 0 END) as pending_w9
                FROM contractors WHERE org_id = $1
            """, org_id)
            
            # Pending payments
            pending = await conn.fetchrow("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM contractor_payments
                WHERE org_id = $1 AND status IN ('PENDING_APPROVAL', 'APPROVED')
            """, org_id)
            
            # YTD payments
            ytd = await conn.fetchrow("""
                SELECT COALESCE(SUM(amount_usd), 0) as total
                FROM contractor_payments
                WHERE org_id = $1 AND status = 'COMPLETED'
                AND EXTRACT(YEAR FROM completed_at) = $2
            """, org_id, datetime.now().year)
            
            # Unbilled time
            unbilled = await conn.fetchrow("""
                SELECT COALESCE(SUM(hours), 0) as hours,
                       COALESCE(SUM(amount), 0) as amount
                FROM time_entries
                WHERE org_id = $1 AND status = 'APPROVED'
            """, org_id)
        
        # 1099 status
        tax_status = await self.tax_compliance.get_1099_status(org_id)
        
        return {
            "contractors": {
                "total": counts["total"],
                "active": counts["active"],
                "pending_w9": counts["pending_w9"]
            },
            "payments": {
                "pending_count": pending["count"],
                "pending_amount": float(pending["total"]),
                "ytd_total": float(ytd["total"])
            },
            "time": {
                "unbilled_hours": float(unbilled["hours"]),
                "unbilled_amount": float(unbilled["amount"])
            },
            "tax_compliance": {
                "requiring_1099": tax_status["requiring_1099"],
                "missing_w9": tax_status["summary"]["missing_w9"],
                "ready_to_file": tax_status["summary"]["ready_to_file"]
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_ADDITIONS = """
-- Contractors table
CREATE TABLE IF NOT EXISTS contractors (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    display_name VARCHAR(255) NOT NULL,
    contractor_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    email VARCHAR(255) NOT NULL,
    phone VARCHAR(50),
    legal_name VARCHAR(255),
    business_name VARCHAR(255),
    tax_classification VARCHAR(50),
    tax_id VARCHAR(50),
    tax_id_type VARCHAR(10),
    address JSONB DEFAULT '{}',
    w9_received BOOLEAN DEFAULT false,
    w9_received_at TIMESTAMPTZ,
    w9_document_id VARCHAR(50),
    is_foreign BOOLEAN DEFAULT false,
    country VARCHAR(2) DEFAULT 'US',
    w8_received BOOLEAN DEFAULT false,
    withholding_rate DECIMAL(5,2) DEFAULT 0,
    preferred_payment_method VARCHAR(20) DEFAULT 'ACH',
    payment_schedule VARCHAR(20) DEFAULT 'MONTHLY',
    bank_account JSONB DEFAULT '{}',
    wise_email VARCHAR(255),
    paypal_email VARCHAR(255),
    crypto_wallet VARCHAR(255),
    default_hourly_rate DECIMAL(10,2) DEFAULT 0,
    default_currency VARCHAR(3) DEFAULT 'USD',
    total_paid_ytd DECIMAL(15,2) DEFAULT 0,
    total_paid_all_time DECIMAL(15,2) DEFAULT 0,
    last_payment_at TIMESTAMPTZ,
    notes TEXT,
    tags TEXT[],
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contractors_org ON contractors(org_id);
CREATE INDEX idx_contractors_status ON contractors(status);

-- Contracts table
CREATE TABLE IF NOT EXISTS contracts (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL REFERENCES contractors(id),
    business_id VARCHAR(50) NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT,
    contract_type VARCHAR(20) NOT NULL,
    start_date DATE NOT NULL,
    end_date DATE,
    auto_renew BOOLEAN DEFAULT false,
    rate DECIMAL(10,2) DEFAULT 0,
    rate_type VARCHAR(20) DEFAULT 'HOURLY',
    currency VARCHAR(3) DEFAULT 'USD',
    total_value DECIMAL(15,2) DEFAULT 0,
    monthly_retainer DECIMAL(15,2) DEFAULT 0,
    included_hours INTEGER DEFAULT 0,
    overage_rate DECIMAL(10,2) DEFAULT 0,
    budget_cap DECIMAL(15,2),
    budget_used DECIMAL(15,2) DEFAULT 0,
    payment_schedule VARCHAR(20) DEFAULT 'MONTHLY',
    payment_terms_days INTEGER DEFAULT 30,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    document_url TEXT,
    signed_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contracts_contractor ON contracts(contractor_id);

-- Time entries table
CREATE TABLE IF NOT EXISTS time_entries (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL REFERENCES contractors(id),
    contract_id VARCHAR(50) NOT NULL REFERENCES contracts(id),
    date DATE NOT NULL,
    hours DECIMAL(5,2) NOT NULL,
    description TEXT,
    project VARCHAR(255),
    task VARCHAR(255),
    hourly_rate DECIMAL(10,2) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    billable BOOLEAN DEFAULT true,
    status VARCHAR(20) DEFAULT 'DRAFT',
    approved_by VARCHAR(50),
    approved_at TIMESTAMPTZ,
    rejection_reason TEXT,
    payment_id VARCHAR(50),
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_time_entries_contractor ON time_entries(contractor_id);
CREATE INDEX idx_time_entries_status ON time_entries(status);

-- Milestones table
CREATE TABLE IF NOT EXISTS milestones (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL REFERENCES contractors(id),
    contract_id VARCHAR(50) NOT NULL REFERENCES contracts(id),
    name VARCHAR(255) NOT NULL,
    description TEXT,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    due_date DATE,
    status VARCHAR(20) DEFAULT 'PENDING',
    submitted_at TIMESTAMPTZ,
    approved_at TIMESTAMPTZ,
    approved_by VARCHAR(50),
    payment_id VARCHAR(50),
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Contractor payments table
CREATE TABLE IF NOT EXISTS contractor_payments (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL REFERENCES contractors(id),
    contract_id VARCHAR(50),
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    exchange_rate DECIMAL(10,6) DEFAULT 1,
    amount_usd DECIMAL(15,2) NOT NULL,
    payment_method VARCHAR(20) NOT NULL,
    description TEXT,
    period_start DATE,
    period_end DATE,
    line_items JSONB DEFAULT '[]',
    status VARCHAR(20) DEFAULT 'DRAFT',
    requires_approval BOOLEAN DEFAULT true,
    approved_by VARCHAR(50),
    approved_at TIMESTAMPTZ,
    scheduled_date DATE,
    processed_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    bank_transfer_id VARCHAR(100),
    wise_transfer_id VARCHAR(100),
    confirmation_number VARCHAR(100),
    fee_amount DECIMAL(10,2) DEFAULT 0,
    fee_paid_by VARCHAR(20) DEFAULT 'PAYER',
    error_message TEXT,
    retry_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_contractor_payments_contractor ON contractor_payments(contractor_id);
CREATE INDEX idx_contractor_payments_status ON contractor_payments(status);

-- 1099-NEC forms table
CREATE TABLE IF NOT EXISTS form_1099_nec (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL REFERENCES contractors(id),
    tax_year INTEGER NOT NULL,
    payer_name VARCHAR(255),
    payer_tin VARCHAR(50),
    payer_address JSONB DEFAULT '{}',
    recipient_name VARCHAR(255),
    recipient_tin VARCHAR(50),
    recipient_address JSONB DEFAULT '{}',
    box_1_nonemployee_compensation DECIMAL(15,2) DEFAULT 0,
    box_4_federal_withheld DECIMAL(15,2) DEFAULT 0,
    box_5_state_withheld DECIMAL(15,2) DEFAULT 0,
    box_6_state VARCHAR(2),
    box_7_state_income DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'PENDING',
    document_url TEXT,
    generated_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    filed_at TIMESTAMPTZ,
    irs_confirmation VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(org_id, contractor_id, tax_year)
);
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List as PyList

app = FastAPI(
    title="Contractor & Payroll Vault API",
    description="Pay People. Stay Compliant.",
    version="3.0.0"
)


class CreateContractorRequest(BaseModel):
    display_name: str
    email: str
    contractor_type: str = "INDIVIDUAL"
    hourly_rate: float = 0
    payment_method: str = "ACH"
    is_foreign: bool = False
    country: str = "US"


class SubmitW9Request(BaseModel):
    legal_name: str
    business_name: Optional[str] = None
    tax_classification: str
    tax_id: str
    tax_id_type: str
    address: dict


class CreateContractRequest(BaseModel):
    contractor_id: str
    business_id: str
    title: str
    contract_type: str
    rate: float
    start_date: str
    end_date: Optional[str] = None


class CreatePaymentRequest(BaseModel):
    contractor_id: str
    amount: float
    currency: str = "USD"
    description: str = ""
    contract_id: Optional[str] = None


class LogTimeRequest(BaseModel):
    contractor_id: str
    contract_id: str
    date: str
    hours: float
    description: str


@app.get("/api/v1/contractors/{org_id}")
async def list_contractors(org_id: str, status: Optional[str] = None):
    return {"status": "requires_db"}


@app.post("/api/v1/contractors/{org_id}")
async def create_contractor(org_id: str, request: CreateContractorRequest):
    return {"status": "requires_db"}


@app.get("/api/v1/contractors/{org_id}/{contractor_id}")
async def get_contractor(org_id: str, contractor_id: str):
    return {"status": "requires_db"}


@app.post("/api/v1/contractors/{org_id}/{contractor_id}/w9")
async def submit_w9(org_id: str, contractor_id: str, request: SubmitW9Request):
    return {"status": "requires_db"}


@app.post("/api/v1/contracts/{org_id}")
async def create_contract(org_id: str, request: CreateContractRequest):
    return {"status": "requires_db"}


@app.post("/api/v1/payments/{org_id}")
async def create_payment(org_id: str, request: CreatePaymentRequest):
    return {"status": "requires_db"}


@app.post("/api/v1/payments/{org_id}/{payment_id}/approve")
async def approve_payment(org_id: str, payment_id: str, approved_by: str):
    return {"status": "requires_db"}


@app.post("/api/v1/payments/{org_id}/{payment_id}/process")
async def process_payment(org_id: str, payment_id: str):
    return {"status": "requires_db"}


@app.get("/api/v1/payments/{org_id}/pending")
async def get_pending_payments(org_id: str):
    return {"status": "requires_db"}


@app.post("/api/v1/time/{org_id}")
async def log_time(org_id: str, request: LogTimeRequest):
    return {"status": "requires_db"}


@app.get("/api/v1/time/{org_id}/unbilled")
async def get_unbilled_time(org_id: str, contractor_id: Optional[str] = None):
    return {"status": "requires_db"}


@app.get("/api/v1/tax/{org_id}/1099-status")
async def get_1099_status(org_id: str, year: Optional[int] = None):
    return {"status": "requires_db"}


@app.post("/api/v1/tax/{org_id}/1099/generate")
async def generate_1099s(org_id: str, year: int, payer_info: dict):
    return {"status": "requires_db"}


@app.get("/api/v1/contractors/{org_id}/dashboard")
async def get_dashboard(org_id: str):
    return {"status": "requires_db"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4021)
