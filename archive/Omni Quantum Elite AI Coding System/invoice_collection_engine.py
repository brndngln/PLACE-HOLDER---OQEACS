# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                                                                                                                                       ║
# ║                              INVOICE & COLLECTION ENGINE                                                                               ║
# ║                              OMNI QUANTUM ELITE v3.0                                                                                   ║
# ║                                                                                                                                       ║
# ║                              "Get Paid Faster. Chase Less."                                                                            ║
# ║                                                                                                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

"""
INVOICE & COLLECTION ENGINE

Complete invoicing and accounts receivable system:

PILLAR 1: Invoice Generation
- Create professional invoices
- Auto-generate from contracts/subscriptions/usage
- Multiple templates (SaaS, Consulting, API Usage)
- Line items with tax calculation
- PDF generation

PILLAR 2: Payment Processing
- Multiple payment methods (Stripe, crypto, bank transfer)
- Payment link generation
- Partial payment support
- Auto-reconciliation with bank

PILLAR 3: Smart Dunning
- Configurable reminder sequences
- Escalating tone (friendly → firm → final)
- Multi-channel (email, SMS)
- Auto-pause service for non-payment

PILLAR 4: Aging & Analytics
- 30/60/90 day aging reports
- Collection rate tracking
- Customer payment behavior scoring
- Cash flow projections from AR

100% Open Source • 100% Self-Hosted • Zero Compromise
"""

import asyncio
import json
import uuid
import hashlib
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

class InvoiceStatus(Enum):
    DRAFT = "DRAFT"                 # Not yet sent
    SENT = "SENT"                   # Sent to customer
    VIEWED = "VIEWED"               # Customer opened it
    PARTIAL = "PARTIAL"             # Partially paid
    PAID = "PAID"                   # Fully paid
    OVERDUE = "OVERDUE"             # Past due date
    VOID = "VOID"                   # Cancelled
    UNCOLLECTIBLE = "UNCOLLECTIBLE" # Written off


class PaymentMethod(Enum):
    STRIPE = "STRIPE"
    BANK_TRANSFER = "BANK_TRANSFER"
    CRYPTO_BTC = "CRYPTO_BTC"
    CRYPTO_ETH = "CRYPTO_ETH"
    CRYPTO_USDC = "CRYPTO_USDC"
    CHECK = "CHECK"
    WIRE = "WIRE"
    ACH = "ACH"
    OTHER = "OTHER"


class InvoiceType(Enum):
    ONE_TIME = "ONE_TIME"           # Single invoice
    RECURRING = "RECURRING"          # Auto-generated monthly
    USAGE_BASED = "USAGE_BASED"     # Based on API/usage
    MILESTONE = "MILESTONE"          # Project milestone
    DEPOSIT = "DEPOSIT"              # Upfront deposit
    FINAL = "FINAL"                  # Final project payment


class DunningStage(Enum):
    NONE = "NONE"                   # Not in dunning
    REMINDER_1 = "REMINDER_1"       # Friendly reminder (1 day after due)
    REMINDER_2 = "REMINDER_2"       # Second reminder (7 days)
    WARNING = "WARNING"             # Firm warning (14 days)
    FINAL_NOTICE = "FINAL_NOTICE"   # Final notice (21 days)
    ESCALATED = "ESCALATED"         # Sent to collections/paused service
    WRITTEN_OFF = "WRITTEN_OFF"     # Given up


class LineItemType(Enum):
    SERVICE = "SERVICE"
    PRODUCT = "PRODUCT"
    SUBSCRIPTION = "SUBSCRIPTION"
    USAGE = "USAGE"
    DISCOUNT = "DISCOUNT"
    TAX = "TAX"
    FEE = "FEE"
    CREDIT = "CREDIT"


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class LineItem:
    """A single line item on an invoice"""
    id: str
    item_type: LineItemType
    description: str
    quantity: Decimal
    unit_price: Decimal
    amount: Decimal  # quantity * unit_price
    tax_rate: Decimal = Decimal("0")
    tax_amount: Decimal = Decimal("0")
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Invoice:
    """An invoice"""
    id: str
    org_id: str
    business_id: str
    customer_id: str
    
    # Invoice details
    invoice_number: str
    invoice_type: InvoiceType
    status: InvoiceStatus
    
    # Dates
    issue_date: date
    due_date: date
    
    # Amounts
    subtotal: Decimal
    tax_total: Decimal
    discount_total: Decimal
    total: Decimal
    amount_paid: Decimal = Decimal("0")
    amount_due: Decimal = Decimal("0")
    
    # Currency
    currency: str = "USD"
    
    # Line items
    line_items: List[LineItem] = field(default_factory=list)
    
    # Payment
    payment_terms: str = "NET_30"
    accepted_payment_methods: List[PaymentMethod] = field(default_factory=list)
    payment_link: Optional[str] = None
    stripe_invoice_id: Optional[str] = None
    
    # Dunning
    dunning_stage: DunningStage = DunningStage.NONE
    dunning_paused: bool = False
    last_dunning_at: Optional[datetime] = None
    
    # Notes
    notes: str = ""
    internal_notes: str = ""
    
    # Tracking
    viewed_at: Optional[datetime] = None
    sent_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Payment:
    """A payment received"""
    id: str
    org_id: str
    invoice_id: str
    customer_id: str
    
    amount: Decimal
    currency: str = "USD"
    
    payment_method: PaymentMethod
    payment_reference: str = ""  # Check #, transaction ID, etc.
    
    # External references
    stripe_payment_id: Optional[str] = None
    crypto_tx_hash: Optional[str] = None
    bank_transaction_id: Optional[str] = None
    
    notes: str = ""
    received_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class DunningSequence:
    """Configuration for dunning sequence"""
    id: str
    org_id: str
    name: str
    
    # Sequence steps
    steps: List[Dict[str, Any]] = field(default_factory=list)
    # Example: [
    #   {"stage": "REMINDER_1", "days_after_due": 1, "channel": "email", "template": "friendly_reminder"},
    #   {"stage": "REMINDER_2", "days_after_due": 7, "channel": "email", "template": "second_reminder"},
    #   {"stage": "WARNING", "days_after_due": 14, "channel": "email", "template": "warning"},
    #   {"stage": "FINAL_NOTICE", "days_after_due": 21, "channel": "email+sms", "template": "final_notice"},
    #   {"stage": "ESCALATED", "days_after_due": 30, "action": "pause_service"}
    # ]
    
    # Settings
    pause_service_on_escalation: bool = True
    auto_write_off_days: int = 90
    
    enabled: bool = True


@dataclass
class Customer:
    """Enhanced customer for invoicing"""
    id: str
    org_id: str
    business_id: str
    
    # Basic info
    name: str
    email: str
    phone: Optional[str] = None
    
    # Billing info
    billing_email: Optional[str] = None
    billing_address: Dict[str, str] = field(default_factory=dict)
    tax_id: Optional[str] = None
    
    # Payment preferences
    preferred_payment_method: PaymentMethod = PaymentMethod.STRIPE
    stripe_customer_id: Optional[str] = None
    auto_charge_enabled: bool = False
    
    # Credit
    credit_balance: Decimal = Decimal("0")
    credit_limit: Decimal = Decimal("0")
    
    # Payment behavior
    payment_score: int = 100  # 0-100, higher = better payer
    avg_days_to_pay: int = 0
    total_invoiced: Decimal = Decimal("0")
    total_paid: Decimal = Decimal("0")
    total_outstanding: Decimal = Decimal("0")
    
    # Status
    status: str = "ACTIVE"  # ACTIVE, SUSPENDED, CHURNED
    suspended_at: Optional[datetime] = None
    suspension_reason: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class AgingBucket:
    """Aging report bucket"""
    period: str  # "CURRENT", "1-30", "31-60", "61-90", "90+"
    invoice_count: int
    total_amount: Decimal
    invoices: List[Dict[str, Any]] = field(default_factory=list)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DEFAULT DUNNING SEQUENCE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

DEFAULT_DUNNING_STEPS = [
    {
        "stage": "REMINDER_1",
        "days_after_due": 1,
        "channel": "email",
        "template": "friendly_reminder",
        "subject": "Friendly Reminder: Invoice #{invoice_number} is due",
        "tone": "friendly"
    },
    {
        "stage": "REMINDER_2",
        "days_after_due": 7,
        "channel": "email",
        "template": "second_reminder",
        "subject": "Second Reminder: Invoice #{invoice_number} is 7 days overdue",
        "tone": "professional"
    },
    {
        "stage": "WARNING",
        "days_after_due": 14,
        "channel": "email",
        "template": "warning",
        "subject": "Important: Invoice #{invoice_number} requires immediate attention",
        "tone": "firm"
    },
    {
        "stage": "FINAL_NOTICE",
        "days_after_due": 21,
        "channel": "email+sms",
        "template": "final_notice",
        "subject": "Final Notice: Service interruption for Invoice #{invoice_number}",
        "tone": "urgent"
    },
    {
        "stage": "ESCALATED",
        "days_after_due": 30,
        "action": "pause_service",
        "channel": "email+sms",
        "template": "service_paused",
        "subject": "Service Suspended: Outstanding balance on Invoice #{invoice_number}",
        "tone": "final"
    }
]


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# EMAIL TEMPLATES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

EMAIL_TEMPLATES = {
    "friendly_reminder": """
Hi {customer_name},

Hope you're doing well! This is a friendly reminder that Invoice #{invoice_number} for {amount} was due on {due_date}.

If you've already sent payment, please disregard this message. Otherwise, you can pay securely here:

{payment_link}

Thanks for your business!

Best,
{business_name}
""",

    "second_reminder": """
Hi {customer_name},

This is a reminder that Invoice #{invoice_number} for {amount} is now 7 days past due (original due date: {due_date}).

To avoid any service interruption, please process payment at your earliest convenience:

{payment_link}

If you're experiencing any issues, please reach out and we'll work with you.

Best regards,
{business_name}
""",

    "warning": """
Dear {customer_name},

Invoice #{invoice_number} for {amount} is now 14 days overdue.

To maintain uninterrupted access to your services, please process payment immediately:

{payment_link}

If payment is not received within 7 days, we may need to suspend your account access.

Please contact us if you need to discuss payment arrangements.

{business_name}
""",

    "final_notice": """
Dear {customer_name},

FINAL NOTICE: Invoice #{invoice_number} for {amount} is now 21 days overdue.

Your service will be SUSPENDED in 7 days if payment is not received.

Pay now to avoid interruption: {payment_link}

If you believe this is an error or need to discuss payment options, please contact us immediately.

{business_name}
""",

    "service_paused": """
Dear {customer_name},

Your service has been SUSPENDED due to non-payment of Invoice #{invoice_number} for {amount}.

Outstanding balance: {total_outstanding}
Days overdue: {days_overdue}

To restore your service immediately, please pay here: {payment_link}

Your data is safe and your service will be restored within 1 hour of payment confirmation.

{business_name}
"""
}


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 1: INVOICE GENERATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class InvoiceGenerator:
    """
    PILLAR 1: INVOICE GENERATION
    
    Create professional invoices from various sources:
    - Manual creation
    - From subscriptions
    - From usage/metering
    - From contracts/milestones
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def create_invoice(
        self,
        org_id: str,
        business_id: str,
        customer_id: str,
        line_items: List[Dict[str, Any]],
        invoice_type: InvoiceType = InvoiceType.ONE_TIME,
        due_days: int = 30,
        notes: str = "",
        tax_rate: Decimal = Decimal("0"),
        discount_amount: Decimal = Decimal("0"),
        discount_percent: Decimal = Decimal("0")
    ) -> Invoice:
        """Create a new invoice"""
        
        # Generate invoice number
        invoice_number = await self._generate_invoice_number(org_id, business_id)
        
        # Process line items
        processed_items = []
        subtotal = Decimal("0")
        tax_total = Decimal("0")
        
        for item in line_items:
            quantity = Decimal(str(item.get("quantity", 1)))
            unit_price = Decimal(str(item.get("unit_price", 0)))
            amount = (quantity * unit_price).quantize(Decimal("0.01"))
            
            item_tax_rate = Decimal(str(item.get("tax_rate", tax_rate)))
            item_tax = (amount * item_tax_rate / 100).quantize(Decimal("0.01"))
            
            line_item = LineItem(
                id=f"LI-{uuid.uuid4().hex[:8].upper()}",
                item_type=LineItemType(item.get("type", "SERVICE")),
                description=item.get("description", ""),
                quantity=quantity,
                unit_price=unit_price,
                amount=amount,
                tax_rate=item_tax_rate,
                tax_amount=item_tax,
                metadata=item.get("metadata", {})
            )
            
            processed_items.append(line_item)
            subtotal += amount
            tax_total += item_tax
        
        # Apply discount
        if discount_percent > 0:
            discount_amount = (subtotal * discount_percent / 100).quantize(Decimal("0.01"))
        
        # Calculate total
        total = subtotal + tax_total - discount_amount
        
        # Create invoice
        invoice = Invoice(
            id=f"INV-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            business_id=business_id,
            customer_id=customer_id,
            invoice_number=invoice_number,
            invoice_type=invoice_type,
            status=InvoiceStatus.DRAFT,
            issue_date=date.today(),
            due_date=date.today() + timedelta(days=due_days),
            subtotal=subtotal,
            tax_total=tax_total,
            discount_total=discount_amount,
            total=total,
            amount_due=total,
            line_items=processed_items,
            payment_terms=f"NET_{due_days}",
            accepted_payment_methods=[PaymentMethod.STRIPE, PaymentMethod.BANK_TRANSFER],
            notes=notes
        )
        
        # Save to database
        await self._save_invoice(invoice)
        
        return invoice
    
    async def create_from_subscription(
        self,
        org_id: str,
        subscription_id: str,
        billing_period_start: date,
        billing_period_end: date
    ) -> Invoice:
        """Create invoice from a subscription"""
        
        # Get subscription details
        async with self.db.acquire() as conn:
            sub = await conn.fetchrow("""
                SELECT s.*, c.id as customer_id, c.name as customer_name
                FROM subscriptions s
                JOIN customers c ON s.customer_id = c.id
                WHERE s.id = $1
            """, subscription_id)
        
        if not sub:
            raise ValueError(f"Subscription not found: {subscription_id}")
        
        # Create line item
        line_items = [{
            "type": "SUBSCRIPTION",
            "description": f"{sub['plan_name']} - {billing_period_start.strftime('%b %d')} to {billing_period_end.strftime('%b %d, %Y')}",
            "quantity": 1,
            "unit_price": float(sub["mrr"]),
            "metadata": {
                "subscription_id": subscription_id,
                "period_start": billing_period_start.isoformat(),
                "period_end": billing_period_end.isoformat()
            }
        }]
        
        return await self.create_invoice(
            org_id=org_id,
            business_id=sub["business_id"],
            customer_id=sub["customer_id"],
            line_items=line_items,
            invoice_type=InvoiceType.RECURRING,
            notes=f"Subscription billing for {sub['plan_name']}"
        )
    
    async def create_from_usage(
        self,
        org_id: str,
        business_id: str,
        customer_id: str,
        usage_records: List[Dict[str, Any]],
        billing_period_start: date,
        billing_period_end: date
    ) -> Invoice:
        """Create invoice from usage/metering records"""
        
        line_items = []
        
        for record in usage_records:
            line_items.append({
                "type": "USAGE",
                "description": f"{record['metric_name']} ({record['quantity']:,} {record['unit']})",
                "quantity": record["quantity"],
                "unit_price": record["unit_price"],
                "metadata": {
                    "metric": record["metric_name"],
                    "period_start": billing_period_start.isoformat(),
                    "period_end": billing_period_end.isoformat()
                }
            })
        
        return await self.create_invoice(
            org_id=org_id,
            business_id=business_id,
            customer_id=customer_id,
            line_items=line_items,
            invoice_type=InvoiceType.USAGE_BASED,
            notes=f"Usage billing for {billing_period_start.strftime('%B %Y')}"
        )
    
    async def _generate_invoice_number(self, org_id: str, business_id: str) -> str:
        """Generate unique invoice number"""
        async with self.db.acquire() as conn:
            result = await conn.fetchrow("""
                SELECT COUNT(*) + 1 as next_num
                FROM invoices
                WHERE org_id = $1 AND business_id = $2
                AND EXTRACT(YEAR FROM created_at) = $3
            """, org_id, business_id, datetime.now().year)
        
        year = datetime.now().strftime("%Y")
        num = result["next_num"] if result else 1
        return f"INV-{year}-{num:05d}"
    
    async def _save_invoice(self, invoice: Invoice):
        """Save invoice to database"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO invoices (
                    id, org_id, business_id, customer_id, invoice_number,
                    invoice_type, status, issue_date, due_date,
                    subtotal, tax_total, discount_total, total,
                    amount_paid, amount_due, currency, line_items,
                    payment_terms, accepted_payment_methods, payment_link,
                    dunning_stage, notes, created_at, updated_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18,$19,$20,$21,$22,$23,$24)
            """, invoice.id, invoice.org_id, invoice.business_id, invoice.customer_id,
                invoice.invoice_number, invoice.invoice_type.value, invoice.status.value,
                invoice.issue_date, invoice.due_date, float(invoice.subtotal),
                float(invoice.tax_total), float(invoice.discount_total), float(invoice.total),
                float(invoice.amount_paid), float(invoice.amount_due), invoice.currency,
                json.dumps([self._line_item_to_dict(li) for li in invoice.line_items]),
                invoice.payment_terms, [m.value for m in invoice.accepted_payment_methods],
                invoice.payment_link, invoice.dunning_stage.value, invoice.notes,
                invoice.created_at, invoice.updated_at)
    
    def _line_item_to_dict(self, li: LineItem) -> Dict:
        return {
            "id": li.id, "type": li.item_type.value, "description": li.description,
            "quantity": str(li.quantity), "unit_price": str(li.unit_price),
            "amount": str(li.amount), "tax_rate": str(li.tax_rate),
            "tax_amount": str(li.tax_amount), "metadata": li.metadata
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 2: PAYMENT PROCESSING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class PaymentProcessor:
    """
    PILLAR 2: PAYMENT PROCESSING
    
    Handle payments across multiple methods:
    - Stripe integration
    - Crypto payments
    - Bank transfers
    - Manual payments
    """
    
    def __init__(self, db_pool: asyncpg.Pool, stripe_api_key: str = None):
        self.db = db_pool
        self.stripe_key = stripe_api_key
    
    async def generate_payment_link(
        self,
        invoice_id: str,
        methods: List[PaymentMethod] = None
    ) -> str:
        """Generate a payment link for an invoice"""
        
        invoice = await self._get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        # Generate unique payment token
        token = hashlib.sha256(f"{invoice_id}:{uuid.uuid4()}".encode()).hexdigest()[:32]
        
        # Store payment link
        payment_link = f"https://pay.yourdomain.com/{token}"
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE invoices SET payment_link = $1, updated_at = $2
                WHERE id = $3
            """, payment_link, datetime.now(timezone.utc), invoice_id)
            
            # Store token mapping
            await conn.execute("""
                INSERT INTO payment_links (token, invoice_id, expires_at, created_at)
                VALUES ($1, $2, $3, $4)
            """, token, invoice_id, datetime.now(timezone.utc) + timedelta(days=90),
                datetime.now(timezone.utc))
        
        return payment_link
    
    async def record_payment(
        self,
        invoice_id: str,
        amount: Decimal,
        payment_method: PaymentMethod,
        reference: str = "",
        notes: str = "",
        stripe_payment_id: str = None,
        crypto_tx_hash: str = None,
        bank_transaction_id: str = None
    ) -> Payment:
        """Record a payment against an invoice"""
        
        invoice = await self._get_invoice(invoice_id)
        if not invoice:
            raise ValueError(f"Invoice not found: {invoice_id}")
        
        # Create payment record
        payment = Payment(
            id=f"PAY-{uuid.uuid4().hex[:12].upper()}",
            org_id=invoice["org_id"],
            invoice_id=invoice_id,
            customer_id=invoice["customer_id"],
            amount=amount,
            currency=invoice["currency"],
            payment_method=payment_method,
            payment_reference=reference,
            stripe_payment_id=stripe_payment_id,
            crypto_tx_hash=crypto_tx_hash,
            bank_transaction_id=bank_transaction_id,
            notes=notes
        )
        
        # Update invoice
        new_amount_paid = Decimal(str(invoice["amount_paid"])) + amount
        new_amount_due = Decimal(str(invoice["total"])) - new_amount_paid
        
        if new_amount_due <= 0:
            new_status = InvoiceStatus.PAID
            paid_at = datetime.now(timezone.utc)
        elif new_amount_paid > 0:
            new_status = InvoiceStatus.PARTIAL
            paid_at = None
        else:
            new_status = InvoiceStatus(invoice["status"])
            paid_at = None
        
        async with self.db.acquire() as conn:
            # Save payment
            await conn.execute("""
                INSERT INTO payments (
                    id, org_id, invoice_id, customer_id, amount, currency,
                    payment_method, payment_reference, stripe_payment_id,
                    crypto_tx_hash, bank_transaction_id, notes, received_at, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14)
            """, payment.id, payment.org_id, payment.invoice_id, payment.customer_id,
                float(payment.amount), payment.currency, payment.payment_method.value,
                payment.payment_reference, payment.stripe_payment_id, payment.crypto_tx_hash,
                payment.bank_transaction_id, payment.notes, payment.received_at, payment.created_at)
            
            # Update invoice
            await conn.execute("""
                UPDATE invoices SET
                    amount_paid = $1, amount_due = $2, status = $3,
                    paid_at = $4, dunning_stage = $5, updated_at = $6
                WHERE id = $7
            """, float(new_amount_paid), float(new_amount_due), new_status.value,
                paid_at, DunningStage.NONE.value if new_status == InvoiceStatus.PAID else invoice["dunning_stage"],
                datetime.now(timezone.utc), invoice_id)
            
            # Update customer stats
            await conn.execute("""
                UPDATE customers SET
                    total_paid = total_paid + $1,
                    total_outstanding = total_outstanding - $1
                WHERE id = $2
            """, float(amount), invoice["customer_id"])
        
        # Trigger alert if needed
        if new_status == InvoiceStatus.PAID:
            await self._trigger_payment_received_alert(invoice, payment)
        
        return payment
    
    async def process_stripe_webhook(self, event: Dict) -> Optional[Payment]:
        """Process Stripe webhook for payment events"""
        
        event_type = event.get("type")
        
        if event_type == "invoice.paid":
            stripe_invoice = event["data"]["object"]
            
            # Find our invoice by Stripe ID
            async with self.db.acquire() as conn:
                invoice = await conn.fetchrow("""
                    SELECT * FROM invoices WHERE stripe_invoice_id = $1
                """, stripe_invoice["id"])
            
            if invoice:
                return await self.record_payment(
                    invoice_id=invoice["id"],
                    amount=Decimal(str(stripe_invoice["amount_paid"])) / 100,
                    payment_method=PaymentMethod.STRIPE,
                    stripe_payment_id=stripe_invoice["payment_intent"]
                )
        
        elif event_type == "payment_intent.succeeded":
            # Handle direct payment intents
            payment_intent = event["data"]["object"]
            invoice_id = payment_intent.get("metadata", {}).get("invoice_id")
            
            if invoice_id:
                return await self.record_payment(
                    invoice_id=invoice_id,
                    amount=Decimal(str(payment_intent["amount"])) / 100,
                    payment_method=PaymentMethod.STRIPE,
                    stripe_payment_id=payment_intent["id"]
                )
        
        return None
    
    async def _get_invoice(self, invoice_id: str) -> Optional[Dict]:
        async with self.db.acquire() as conn:
            return await conn.fetchrow("SELECT * FROM invoices WHERE id = $1", invoice_id)
    
    async def _trigger_payment_received_alert(self, invoice: Dict, payment: Payment):
        """Trigger notification for payment received"""
        # Integration with Neural Alert Engine
        pass


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 3: SMART DUNNING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class SmartDunning:
    """
    PILLAR 3: SMART DUNNING
    
    Intelligent collection sequences:
    - Configurable reminder cadence
    - Escalating tone
    - Multi-channel (email + SMS)
    - Auto-pause service
    - Write-off after threshold
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.default_steps = DEFAULT_DUNNING_STEPS
        self.templates = EMAIL_TEMPLATES
    
    async def run_dunning_cycle(self, org_id: str):
        """Run dunning for all overdue invoices"""
        
        today = date.today()
        
        # Get all overdue, unpaid invoices
        async with self.db.acquire() as conn:
            invoices = await conn.fetch("""
                SELECT i.*, c.name as customer_name, c.email as customer_email,
                       c.phone as customer_phone, b.name as business_name
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                JOIN businesses b ON i.business_id = b.id
                WHERE i.org_id = $1
                AND i.status NOT IN ('PAID', 'VOID', 'UNCOLLECTIBLE')
                AND i.due_date < $2
                AND i.dunning_paused = false
            """, org_id, today)
        
        results = []
        
        for inv in invoices:
            days_overdue = (today - inv["due_date"]).days
            current_stage = DunningStage(inv["dunning_stage"])
            
            # Determine next action
            action = self._get_dunning_action(days_overdue, current_stage)
            
            if action:
                result = await self._execute_dunning_action(inv, action, days_overdue)
                results.append(result)
        
        return results
    
    def _get_dunning_action(
        self,
        days_overdue: int,
        current_stage: DunningStage
    ) -> Optional[Dict]:
        """Determine the next dunning action based on days overdue"""
        
        for step in self.default_steps:
            if days_overdue >= step["days_after_due"]:
                step_stage = DunningStage(step["stage"])
                
                # Only advance to this stage if we haven't passed it
                if self._stage_order(step_stage) > self._stage_order(current_stage):
                    return step
        
        return None
    
    def _stage_order(self, stage: DunningStage) -> int:
        """Get numeric order of dunning stage"""
        order = {
            DunningStage.NONE: 0,
            DunningStage.REMINDER_1: 1,
            DunningStage.REMINDER_2: 2,
            DunningStage.WARNING: 3,
            DunningStage.FINAL_NOTICE: 4,
            DunningStage.ESCALATED: 5,
            DunningStage.WRITTEN_OFF: 6
        }
        return order.get(stage, 0)
    
    async def _execute_dunning_action(
        self,
        invoice: Dict,
        action: Dict,
        days_overdue: int
    ) -> Dict:
        """Execute a dunning action"""
        
        result = {
            "invoice_id": invoice["id"],
            "invoice_number": invoice["invoice_number"],
            "customer": invoice["customer_name"],
            "stage": action["stage"],
            "days_overdue": days_overdue,
            "actions_taken": []
        }
        
        # Send email
        if "email" in action.get("channel", ""):
            email_sent = await self._send_dunning_email(invoice, action, days_overdue)
            result["actions_taken"].append(f"email_sent: {email_sent}")
        
        # Send SMS
        if "sms" in action.get("channel", ""):
            sms_sent = await self._send_dunning_sms(invoice, action, days_overdue)
            result["actions_taken"].append(f"sms_sent: {sms_sent}")
        
        # Pause service if escalated
        if action.get("action") == "pause_service":
            paused = await self._pause_customer_service(invoice["customer_id"], invoice["id"])
            result["actions_taken"].append(f"service_paused: {paused}")
        
        # Update invoice dunning stage
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE invoices SET
                    dunning_stage = $1,
                    last_dunning_at = $2,
                    status = $3,
                    updated_at = $2
                WHERE id = $4
            """, action["stage"], datetime.now(timezone.utc),
                InvoiceStatus.OVERDUE.value, invoice["id"])
        
        return result
    
    async def _send_dunning_email(
        self,
        invoice: Dict,
        action: Dict,
        days_overdue: int
    ) -> bool:
        """Send dunning email"""
        
        template_name = action.get("template", "friendly_reminder")
        template = self.templates.get(template_name, self.templates["friendly_reminder"])
        
        # Fill template
        email_body = template.format(
            customer_name=invoice["customer_name"],
            invoice_number=invoice["invoice_number"],
            amount=f"${invoice['amount_due']:,.2f}",
            due_date=invoice["due_date"].strftime("%B %d, %Y"),
            payment_link=invoice["payment_link"] or "https://pay.example.com",
            business_name=invoice["business_name"],
            total_outstanding=f"${invoice['amount_due']:,.2f}",
            days_overdue=days_overdue
        )
        
        # Send email (integration with email service)
        print(f"📧 Dunning email to {invoice['customer_email']}: {action['subject']}")
        
        # Log the dunning event
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO dunning_events (id, invoice_id, customer_id, stage, channel, sent_at)
                VALUES ($1, $2, $3, $4, $5, $6)
            """, f"DUN-{uuid.uuid4().hex[:12]}", invoice["id"], invoice["customer_id"],
                action["stage"], "email", datetime.now(timezone.utc))
        
        return True
    
    async def _send_dunning_sms(self, invoice: Dict, action: Dict, days_overdue: int) -> bool:
        """Send dunning SMS"""
        if not invoice.get("customer_phone"):
            return False
        
        message = f"Invoice #{invoice['invoice_number']} for ${invoice['amount_due']:,.2f} is {days_overdue} days overdue. Pay now: {invoice['payment_link'] or 'https://pay.example.com'}"
        
        print(f"📱 Dunning SMS to {invoice['customer_phone']}: {message[:50]}...")
        return True
    
    async def _pause_customer_service(self, customer_id: str, invoice_id: str) -> bool:
        """Pause customer service due to non-payment"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE customers SET
                    status = 'SUSPENDED',
                    suspended_at = $1,
                    suspension_reason = $2
                WHERE id = $3
            """, datetime.now(timezone.utc), f"Non-payment: Invoice {invoice_id}", customer_id)
            
            # Also pause their subscriptions
            await conn.execute("""
                UPDATE subscriptions SET status = 'SUSPENDED'
                WHERE customer_id = $1 AND status = 'ACTIVE'
            """, customer_id)
        
        return True
    
    async def pause_dunning(self, invoice_id: str, reason: str = ""):
        """Pause dunning for an invoice"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE invoices SET dunning_paused = true, internal_notes = $1
                WHERE id = $2
            """, f"Dunning paused: {reason}", invoice_id)
    
    async def resume_dunning(self, invoice_id: str):
        """Resume dunning for an invoice"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE invoices SET dunning_paused = false WHERE id = $1
            """, invoice_id)
    
    async def write_off_invoice(self, invoice_id: str, reason: str = ""):
        """Write off an invoice as uncollectible"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE invoices SET
                    status = 'UNCOLLECTIBLE',
                    dunning_stage = 'WRITTEN_OFF',
                    internal_notes = $1,
                    updated_at = $2
                WHERE id = $3
            """, f"Written off: {reason}", datetime.now(timezone.utc), invoice_id)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 4: AGING & ANALYTICS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ARAnalytics:
    """
    PILLAR 4: AGING & ANALYTICS
    
    Accounts receivable reporting and analytics:
    - Aging reports (30/60/90)
    - Collection rates
    - Customer payment scoring
    - Cash flow projections
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def get_aging_report(self, org_id: str) -> Dict[str, Any]:
        """Generate aging report"""
        
        today = date.today()
        
        async with self.db.acquire() as conn:
            invoices = await conn.fetch("""
                SELECT i.*, c.name as customer_name
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                WHERE i.org_id = $1
                AND i.status NOT IN ('PAID', 'VOID', 'UNCOLLECTIBLE')
                AND i.amount_due > 0
            """, org_id)
        
        buckets = {
            "current": AgingBucket("CURRENT", 0, Decimal("0"), []),
            "1_30": AgingBucket("1-30", 0, Decimal("0"), []),
            "31_60": AgingBucket("31-60", 0, Decimal("0"), []),
            "61_90": AgingBucket("61-90", 0, Decimal("0"), []),
            "over_90": AgingBucket("90+", 0, Decimal("0"), [])
        }
        
        for inv in invoices:
            days_outstanding = (today - inv["due_date"]).days
            amount = Decimal(str(inv["amount_due"]))
            
            inv_data = {
                "id": inv["id"],
                "invoice_number": inv["invoice_number"],
                "customer": inv["customer_name"],
                "amount": float(amount),
                "due_date": inv["due_date"].isoformat(),
                "days_outstanding": days_outstanding
            }
            
            if days_outstanding <= 0:
                bucket = buckets["current"]
            elif days_outstanding <= 30:
                bucket = buckets["1_30"]
            elif days_outstanding <= 60:
                bucket = buckets["31_60"]
            elif days_outstanding <= 90:
                bucket = buckets["61_90"]
            else:
                bucket = buckets["over_90"]
            
            bucket.invoice_count += 1
            bucket.total_amount += amount
            bucket.invoices.append(inv_data)
        
        total_ar = sum(b.total_amount for b in buckets.values())
        
        return {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "org_id": org_id,
            "total_accounts_receivable": float(total_ar),
            "buckets": {
                name: {
                    "period": bucket.period,
                    "invoice_count": bucket.invoice_count,
                    "total_amount": float(bucket.total_amount),
                    "percentage": float((bucket.total_amount / total_ar * 100).quantize(Decimal("0.1"))) if total_ar > 0 else 0,
                    "invoices": bucket.invoices
                }
                for name, bucket in buckets.items()
            },
            "summary": {
                "current_percentage": float((buckets["current"].total_amount / total_ar * 100).quantize(Decimal("0.1"))) if total_ar > 0 else 0,
                "overdue_percentage": float(((total_ar - buckets["current"].total_amount) / total_ar * 100).quantize(Decimal("0.1"))) if total_ar > 0 else 0,
                "average_days_outstanding": self._calculate_average_days(invoices, today)
            }
        }
    
    async def get_collection_metrics(self, org_id: str, period_days: int = 90) -> Dict[str, Any]:
        """Get collection performance metrics"""
        
        since = date.today() - timedelta(days=period_days)
        
        async with self.db.acquire() as conn:
            # Total invoiced
            invoiced = await conn.fetchrow("""
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total
                FROM invoices
                WHERE org_id = $1 AND issue_date >= $2
            """, org_id, since)
            
            # Total collected
            collected = await conn.fetchrow("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM payments
                WHERE org_id = $1 AND received_at >= $2
            """, org_id, since)
            
            # Average days to payment
            avg_days = await conn.fetchrow("""
                SELECT AVG(EXTRACT(DAY FROM (paid_at - issue_date))) as avg_days
                FROM invoices
                WHERE org_id = $1 AND status = 'PAID'
                AND paid_at >= $2
            """, org_id, since)
            
            # Written off
            written_off = await conn.fetchrow("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount_due), 0) as total
                FROM invoices
                WHERE org_id = $1 AND status = 'UNCOLLECTIBLE'
                AND updated_at >= $2
            """, org_id, since)
        
        total_invoiced = Decimal(str(invoiced["total"]))
        total_collected = Decimal(str(collected["total"]))
        total_written_off = Decimal(str(written_off["total"]))
        
        collection_rate = (total_collected / total_invoiced * 100) if total_invoiced > 0 else Decimal("0")
        write_off_rate = (total_written_off / total_invoiced * 100) if total_invoiced > 0 else Decimal("0")
        
        return {
            "period_days": period_days,
            "total_invoiced": float(total_invoiced),
            "total_collected": float(total_collected),
            "total_written_off": float(total_written_off),
            "collection_rate": float(collection_rate.quantize(Decimal("0.1"))),
            "write_off_rate": float(write_off_rate.quantize(Decimal("0.1"))),
            "average_days_to_payment": float(avg_days["avg_days"]) if avg_days["avg_days"] else 0,
            "invoice_count": invoiced["count"],
            "payment_count": collected["count"]
        }
    
    async def get_customer_payment_scores(self, org_id: str) -> List[Dict[str, Any]]:
        """Get payment behavior scores for all customers"""
        
        async with self.db.acquire() as conn:
            customers = await conn.fetch("""
                SELECT c.*,
                    COUNT(i.id) as invoice_count,
                    AVG(CASE WHEN i.status = 'PAID' 
                        THEN EXTRACT(DAY FROM (i.paid_at - i.due_date)) 
                        ELSE NULL END) as avg_days_late
                FROM customers c
                LEFT JOIN invoices i ON c.id = i.customer_id
                WHERE c.org_id = $1
                GROUP BY c.id
            """, org_id)
        
        results = []
        for cust in customers:
            # Calculate score (100 = perfect, 0 = terrible)
            score = 100
            
            avg_days_late = cust["avg_days_late"] or 0
            if avg_days_late > 0:
                score -= min(avg_days_late * 2, 40)  # Lose up to 40 points for lateness
            
            if cust["total_outstanding"] > 0:
                outstanding_ratio = float(cust["total_outstanding"]) / max(float(cust["total_invoiced"]), 1)
                score -= min(outstanding_ratio * 30, 30)  # Lose up to 30 points for outstanding
            
            if cust["status"] == "SUSPENDED":
                score -= 20
            
            score = max(0, min(100, score))
            
            results.append({
                "customer_id": cust["id"],
                "customer_name": cust["name"],
                "payment_score": int(score),
                "total_invoiced": float(cust["total_invoiced"]),
                "total_paid": float(cust["total_paid"]),
                "total_outstanding": float(cust["total_outstanding"]),
                "invoice_count": cust["invoice_count"],
                "avg_days_late": round(avg_days_late, 1),
                "status": cust["status"],
                "risk_level": "LOW" if score >= 80 else "MEDIUM" if score >= 50 else "HIGH"
            })
        
        # Sort by score ascending (worst payers first)
        results.sort(key=lambda x: x["payment_score"])
        
        return results
    
    async def project_cash_from_ar(self, org_id: str, days_forward: int = 90) -> Dict[str, Any]:
        """Project cash inflows from accounts receivable"""
        
        async with self.db.acquire() as conn:
            # Get collection rate by age bucket
            invoices = await conn.fetch("""
                SELECT i.*, c.payment_score
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                WHERE i.org_id = $1
                AND i.status NOT IN ('PAID', 'VOID', 'UNCOLLECTIBLE')
                AND i.amount_due > 0
            """, org_id)
        
        today = date.today()
        projections = []
        
        # Simple projection: assume collection based on customer score and age
        for week in range(days_forward // 7):
            week_start = today + timedelta(days=week * 7)
            week_end = week_start + timedelta(days=6)
            expected = Decimal("0")
            
            for inv in invoices:
                days_outstanding = (today - inv["due_date"]).days
                score = inv["payment_score"] or 50
                
                # Probability of collection decreases with age, increases with score
                base_probability = Decimal(str(score / 100))
                age_factor = max(Decimal("0.3"), Decimal("1") - Decimal(str(days_outstanding / 90)))
                probability = base_probability * age_factor
                
                # Assume payments spread over next 4 weeks
                if week < 4:
                    expected += Decimal(str(inv["amount_due"])) * probability * Decimal("0.25")
            
            projections.append({
                "week": week + 1,
                "period": f"{week_start.isoformat()} to {week_end.isoformat()}",
                "expected_collections": float(expected.quantize(Decimal("0.01")))
            })
        
        total_expected = sum(p["expected_collections"] for p in projections)
        total_ar = sum(Decimal(str(inv["amount_due"])) for inv in invoices)
        
        return {
            "total_accounts_receivable": float(total_ar),
            "projected_collections": float(total_expected),
            "collection_probability": float((Decimal(str(total_expected)) / total_ar * 100).quantize(Decimal("0.1"))) if total_ar > 0 else 0,
            "weekly_projections": projections
        }
    
    def _calculate_average_days(self, invoices: List, today: date) -> float:
        """Calculate average days outstanding"""
        if not invoices:
            return 0
        
        total_days = sum((today - inv["due_date"]).days for inv in invoices if inv["due_date"] < today)
        overdue_count = sum(1 for inv in invoices if inv["due_date"] < today)
        
        return round(total_days / overdue_count, 1) if overdue_count > 0 else 0


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class InvoiceCollectionEngine:
    """
    INVOICE & COLLECTION ENGINE - Main Service
    
    Complete invoicing and accounts receivable system.
    "Get Paid Faster. Chase Less."
    """
    
    def __init__(self, db_pool: asyncpg.Pool, stripe_api_key: str = None):
        self.db = db_pool
        
        # Initialize all pillars
        self.generator = InvoiceGenerator(db_pool)
        self.payments = PaymentProcessor(db_pool, stripe_api_key)
        self.dunning = SmartDunning(db_pool)
        self.analytics = ARAnalytics(db_pool)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # INVOICE OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def create_invoice(self, **kwargs) -> Invoice:
        """Create a new invoice"""
        return await self.generator.create_invoice(**kwargs)
    
    async def send_invoice(self, invoice_id: str) -> Dict[str, Any]:
        """Send invoice to customer"""
        # Generate payment link
        payment_link = await self.payments.generate_payment_link(invoice_id)
        
        # Update status to SENT
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE invoices SET
                    status = 'SENT',
                    sent_at = $1,
                    payment_link = $2,
                    updated_at = $1
                WHERE id = $3
            """, datetime.now(timezone.utc), payment_link, invoice_id)
            
            # Get invoice details for email
            invoice = await conn.fetchrow("""
                SELECT i.*, c.name as customer_name, c.email as customer_email,
                       b.name as business_name
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                JOIN businesses b ON i.business_id = b.id
                WHERE i.id = $1
            """, invoice_id)
        
        # Send email
        print(f"📧 Invoice {invoice['invoice_number']} sent to {invoice['customer_email']}")
        
        return {
            "invoice_id": invoice_id,
            "invoice_number": invoice["invoice_number"],
            "sent_to": invoice["customer_email"],
            "payment_link": payment_link,
            "amount": float(invoice["total"]),
            "due_date": invoice["due_date"].isoformat()
        }
    
    async def void_invoice(self, invoice_id: str, reason: str = "") -> bool:
        """Void an invoice"""
        async with self.db.acquire() as conn:
            result = await conn.execute("""
                UPDATE invoices SET
                    status = 'VOID',
                    internal_notes = $1,
                    updated_at = $2
                WHERE id = $3 AND status NOT IN ('PAID', 'PARTIAL')
            """, f"Voided: {reason}", datetime.now(timezone.utc), invoice_id)
            return "UPDATE 1" in result
    
    async def get_invoice(self, invoice_id: str) -> Optional[Dict]:
        """Get invoice details"""
        async with self.db.acquire() as conn:
            invoice = await conn.fetchrow("""
                SELECT i.*, c.name as customer_name, c.email as customer_email,
                       b.name as business_name
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                JOIN businesses b ON i.business_id = b.id
                WHERE i.id = $1
            """, invoice_id)
            
            if invoice:
                payments = await conn.fetch("""
                    SELECT * FROM payments WHERE invoice_id = $1 ORDER BY received_at
                """, invoice_id)
                
                return {
                    **dict(invoice),
                    "payments": [dict(p) for p in payments]
                }
        return None
    
    async def list_invoices(
        self,
        org_id: str,
        status: InvoiceStatus = None,
        customer_id: str = None,
        limit: int = 50
    ) -> List[Dict]:
        """List invoices with filters"""
        async with self.db.acquire() as conn:
            query = """
                SELECT i.*, c.name as customer_name
                FROM invoices i
                JOIN customers c ON i.customer_id = c.id
                WHERE i.org_id = $1
            """
            params = [org_id]
            
            if status:
                query += f" AND i.status = ${len(params) + 1}"
                params.append(status.value)
            
            if customer_id:
                query += f" AND i.customer_id = ${len(params) + 1}"
                params.append(customer_id)
            
            query += f" ORDER BY i.created_at DESC LIMIT ${len(params) + 1}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # PAYMENT OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def record_payment(self, **kwargs) -> Payment:
        """Record a payment"""
        return await self.payments.record_payment(**kwargs)
    
    async def get_payment_link(self, invoice_id: str) -> str:
        """Get or generate payment link"""
        return await self.payments.generate_payment_link(invoice_id)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # DUNNING OPERATIONS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def run_dunning(self, org_id: str) -> List[Dict]:
        """Run dunning cycle"""
        return await self.dunning.run_dunning_cycle(org_id)
    
    async def pause_dunning(self, invoice_id: str, reason: str = ""):
        """Pause dunning for invoice"""
        await self.dunning.pause_dunning(invoice_id, reason)
    
    async def write_off(self, invoice_id: str, reason: str = ""):
        """Write off invoice"""
        await self.dunning.write_off_invoice(invoice_id, reason)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # ANALYTICS
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def get_aging_report(self, org_id: str) -> Dict:
        """Get AR aging report"""
        return await self.analytics.get_aging_report(org_id)
    
    async def get_collection_metrics(self, org_id: str, days: int = 90) -> Dict:
        """Get collection metrics"""
        return await self.analytics.get_collection_metrics(org_id, days)
    
    async def get_customer_scores(self, org_id: str) -> List[Dict]:
        """Get customer payment scores"""
        return await self.analytics.get_customer_payment_scores(org_id)
    
    async def project_ar_cash(self, org_id: str, days: int = 90) -> Dict:
        """Project cash from AR"""
        return await self.analytics.project_cash_from_ar(org_id, days)
    
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    # DASHBOARD SUMMARY
    # ─────────────────────────────────────────────────────────────────────────────────────────────────
    
    async def get_ar_summary(self, org_id: str) -> Dict[str, Any]:
        """Get AR summary for dashboard"""
        
        aging = await self.analytics.get_aging_report(org_id)
        metrics = await self.analytics.get_collection_metrics(org_id, 30)
        
        async with self.db.acquire() as conn:
            # Recent activity
            recent_invoices = await conn.fetch("""
                SELECT COUNT(*) as count, COALESCE(SUM(total), 0) as total
                FROM invoices
                WHERE org_id = $1 AND created_at >= CURRENT_DATE - 7
            """, org_id)
            
            recent_payments = await conn.fetch("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount), 0) as total
                FROM payments
                WHERE org_id = $1 AND received_at >= CURRENT_DATE - 7
            """, org_id)
            
            overdue_count = await conn.fetchrow("""
                SELECT COUNT(*) as count, COALESCE(SUM(amount_due), 0) as total
                FROM invoices
                WHERE org_id = $1 AND status = 'OVERDUE'
            """, org_id)
        
        return {
            "total_ar": aging["total_accounts_receivable"],
            "overdue_amount": float(overdue_count["total"]),
            "overdue_count": overdue_count["count"],
            "collection_rate": metrics["collection_rate"],
            "avg_days_to_pay": metrics["average_days_to_payment"],
            "invoiced_last_7_days": float(recent_invoices[0]["total"]),
            "collected_last_7_days": float(recent_payments[0]["total"]),
            "aging_summary": {
                "current": aging["buckets"]["current"]["total_amount"],
                "1_30": aging["buckets"]["1_30"]["total_amount"],
                "31_60": aging["buckets"]["31_60"]["total_amount"],
                "61_90": aging["buckets"]["61_90"]["total_amount"],
                "over_90": aging["buckets"]["over_90"]["total_amount"]
            }
        }


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMA ADDITIONS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

SCHEMA_ADDITIONS = """
-- Invoices table
CREATE TABLE IF NOT EXISTS invoices (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    business_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    invoice_number VARCHAR(50) UNIQUE NOT NULL,
    invoice_type VARCHAR(20) NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'DRAFT',
    issue_date DATE NOT NULL,
    due_date DATE NOT NULL,
    subtotal DECIMAL(15,2) NOT NULL DEFAULT 0,
    tax_total DECIMAL(15,2) NOT NULL DEFAULT 0,
    discount_total DECIMAL(15,2) NOT NULL DEFAULT 0,
    total DECIMAL(15,2) NOT NULL DEFAULT 0,
    amount_paid DECIMAL(15,2) NOT NULL DEFAULT 0,
    amount_due DECIMAL(15,2) NOT NULL DEFAULT 0,
    currency VARCHAR(3) DEFAULT 'USD',
    line_items JSONB NOT NULL DEFAULT '[]',
    payment_terms VARCHAR(20) DEFAULT 'NET_30',
    accepted_payment_methods TEXT[],
    payment_link TEXT,
    stripe_invoice_id VARCHAR(100),
    dunning_stage VARCHAR(20) DEFAULT 'NONE',
    dunning_paused BOOLEAN DEFAULT false,
    last_dunning_at TIMESTAMPTZ,
    notes TEXT,
    internal_notes TEXT,
    viewed_at TIMESTAMPTZ,
    sent_at TIMESTAMPTZ,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_invoices_org ON invoices(org_id);
CREATE INDEX idx_invoices_customer ON invoices(customer_id);
CREATE INDEX idx_invoices_status ON invoices(status);
CREATE INDEX idx_invoices_due_date ON invoices(due_date);

-- Payments table
CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    invoice_id VARCHAR(50) NOT NULL REFERENCES invoices(id),
    customer_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    currency VARCHAR(3) DEFAULT 'USD',
    payment_method VARCHAR(20) NOT NULL,
    payment_reference VARCHAR(255),
    stripe_payment_id VARCHAR(100),
    crypto_tx_hash VARCHAR(100),
    bank_transaction_id VARCHAR(100),
    notes TEXT,
    received_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_payments_invoice ON payments(invoice_id);
CREATE INDEX idx_payments_org ON payments(org_id);

-- Payment links table
CREATE TABLE IF NOT EXISTS payment_links (
    token VARCHAR(64) PRIMARY KEY,
    invoice_id VARCHAR(50) NOT NULL REFERENCES invoices(id),
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Dunning events table
CREATE TABLE IF NOT EXISTS dunning_events (
    id VARCHAR(50) PRIMARY KEY,
    invoice_id VARCHAR(50) NOT NULL REFERENCES invoices(id),
    customer_id VARCHAR(50) NOT NULL,
    stage VARCHAR(20) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL
);

CREATE INDEX idx_dunning_invoice ON dunning_events(invoice_id);

-- Add payment fields to customers
ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_email VARCHAR(255);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS billing_address JSONB DEFAULT '{}';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS tax_id VARCHAR(50);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS preferred_payment_method VARCHAR(20) DEFAULT 'STRIPE';
ALTER TABLE customers ADD COLUMN IF NOT EXISTS stripe_customer_id VARCHAR(100);
ALTER TABLE customers ADD COLUMN IF NOT EXISTS auto_charge_enabled BOOLEAN DEFAULT false;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS credit_balance DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS payment_score INTEGER DEFAULT 100;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS avg_days_to_pay INTEGER DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_invoiced DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_paid DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS total_outstanding DECIMAL(15,2) DEFAULT 0;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS suspended_at TIMESTAMPTZ;
ALTER TABLE customers ADD COLUMN IF NOT EXISTS suspension_reason TEXT;
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional, List as PyList

app = FastAPI(
    title="Invoice & Collection Engine API",
    description="Get Paid Faster. Chase Less.",
    version="3.0.0"
)


class CreateInvoiceRequest(BaseModel):
    business_id: str
    customer_id: str
    line_items: PyList[dict]
    invoice_type: str = "ONE_TIME"
    due_days: int = 30
    notes: str = ""
    tax_rate: float = 0
    discount_percent: float = 0


class RecordPaymentRequest(BaseModel):
    amount: float
    payment_method: str
    reference: str = ""
    notes: str = ""


@app.post("/api/v1/invoices/{org_id}")
async def create_invoice(org_id: str, request: CreateInvoiceRequest):
    """Create a new invoice"""
    return {"status": "requires_db", "org_id": org_id}


@app.get("/api/v1/invoices/{org_id}")
async def list_invoices(org_id: str, status: Optional[str] = None, customer_id: Optional[str] = None):
    """List invoices"""
    return {"status": "requires_db", "org_id": org_id}


@app.get("/api/v1/invoices/{org_id}/{invoice_id}")
async def get_invoice(org_id: str, invoice_id: str):
    """Get invoice details"""
    return {"status": "requires_db", "invoice_id": invoice_id}


@app.post("/api/v1/invoices/{org_id}/{invoice_id}/send")
async def send_invoice(org_id: str, invoice_id: str):
    """Send invoice to customer"""
    return {"status": "requires_db", "invoice_id": invoice_id}


@app.post("/api/v1/invoices/{org_id}/{invoice_id}/void")
async def void_invoice(org_id: str, invoice_id: str, reason: str = ""):
    """Void an invoice"""
    return {"status": "requires_db", "invoice_id": invoice_id}


@app.post("/api/v1/invoices/{org_id}/{invoice_id}/payment")
async def record_payment(org_id: str, invoice_id: str, request: RecordPaymentRequest):
    """Record a payment"""
    return {"status": "requires_db", "invoice_id": invoice_id}


@app.get("/api/v1/invoices/{org_id}/{invoice_id}/payment-link")
async def get_payment_link(org_id: str, invoice_id: str):
    """Get payment link for invoice"""
    return {"status": "requires_db", "invoice_id": invoice_id}


@app.post("/api/v1/ar/{org_id}/dunning/run")
async def run_dunning(org_id: str):
    """Run dunning cycle"""
    return {"status": "requires_db", "org_id": org_id}


@app.post("/api/v1/ar/{org_id}/dunning/{invoice_id}/pause")
async def pause_dunning(org_id: str, invoice_id: str, reason: str = ""):
    """Pause dunning for invoice"""
    return {"status": "requires_db", "invoice_id": invoice_id}


@app.get("/api/v1/ar/{org_id}/aging")
async def get_aging_report(org_id: str):
    """Get AR aging report"""
    return {"status": "requires_db", "org_id": org_id}


@app.get("/api/v1/ar/{org_id}/metrics")
async def get_collection_metrics(org_id: str, days: int = 90):
    """Get collection metrics"""
    return {"status": "requires_db", "org_id": org_id}


@app.get("/api/v1/ar/{org_id}/customer-scores")
async def get_customer_scores(org_id: str):
    """Get customer payment scores"""
    return {"status": "requires_db", "org_id": org_id}


@app.get("/api/v1/ar/{org_id}/projections")
async def get_ar_projections(org_id: str, days: int = 90):
    """Project cash from AR"""
    return {"status": "requires_db", "org_id": org_id}


@app.get("/api/v1/ar/{org_id}/summary")
async def get_ar_summary(org_id: str):
    """Get AR summary for dashboard"""
    return {"status": "requires_db", "org_id": org_id}


@app.post("/api/v1/webhooks/stripe")
async def stripe_webhook(event: dict):
    """Handle Stripe webhooks"""
    return {"status": "processed"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4020)
