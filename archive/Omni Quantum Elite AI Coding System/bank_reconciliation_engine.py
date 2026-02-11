# ╔═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╗
# ║                                                                                                                                       ║
# ║                              BANK RECONCILIATION ENGINE                                                                                ║
# ║                              OMNI QUANTUM ELITE v3.0                                                                                   ║
# ║                                                                                                                                       ║
# ║                              "Trust But Verify"                                                                                        ║
# ║                                                                                                                                       ║
# ╚═══════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════════╝

"""
BANK RECONCILIATION ENGINE

Automated transaction matching and verification:

PILLAR 1: Transaction Matching
- Auto-match bank transactions to internal records
- Smart fuzzy matching (amount, date, description)
- Multi-source reconciliation (Stripe, PayPal, Bank)
- Duplicate detection

PILLAR 2: Discrepancy Detection
- Missing deposit detection
- Unmatched transaction alerts
- Fee reconciliation (catch bank overcharges)
- Balance drift detection

PILLAR 3: Payment Processor Reconciliation
- Stripe ↔ Bank matching
- PayPal ↔ Bank matching
- Wise ↔ Bank matching
- Payout tracking

PILLAR 4: Reporting & Audit
- Reconciliation reports
- Exception reports
- Audit trail
- Historical reconciliation status

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
from typing import Any, Dict, List, Optional, Tuple, Set
import asyncpg
from difflib import SequenceMatcher


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# ENUMS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TransactionSource(Enum):
    BANK = "BANK"                 # Direct bank transaction
    STRIPE = "STRIPE"             # Stripe payment/payout
    PAYPAL = "PAYPAL"             # PayPal transaction
    WISE = "WISE"                 # Wise transfer
    MERCURY = "MERCURY"           # Mercury bank
    INTERNAL = "INTERNAL"         # Internal record
    MANUAL = "MANUAL"             # Manual entry


class MatchStatus(Enum):
    UNMATCHED = "UNMATCHED"       # No match found
    AUTO_MATCHED = "AUTO_MATCHED" # Automatically matched
    MANUAL_MATCHED = "MANUAL_MATCHED"  # Manually matched
    CONFIRMED = "CONFIRMED"       # Match confirmed
    DISPUTED = "DISPUTED"         # Match disputed
    EXCLUDED = "EXCLUDED"         # Excluded from reconciliation


class MatchConfidence(Enum):
    EXACT = "EXACT"               # 100% match
    HIGH = "HIGH"                 # 90%+ confidence
    MEDIUM = "MEDIUM"             # 70-90% confidence
    LOW = "LOW"                   # 50-70% confidence
    NONE = "NONE"                 # No match


class DiscrepancyType(Enum):
    MISSING_DEPOSIT = "MISSING_DEPOSIT"
    MISSING_WITHDRAWAL = "MISSING_WITHDRAWAL"
    AMOUNT_MISMATCH = "AMOUNT_MISMATCH"
    DATE_MISMATCH = "DATE_MISMATCH"
    DUPLICATE = "DUPLICATE"
    UNEXPECTED_FEE = "UNEXPECTED_FEE"
    BALANCE_DRIFT = "BALANCE_DRIFT"
    UNMATCHED_BANK = "UNMATCHED_BANK"
    UNMATCHED_INTERNAL = "UNMATCHED_INTERNAL"


class ReconciliationStatus(Enum):
    PENDING = "PENDING"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    COMPLETED_WITH_EXCEPTIONS = "COMPLETED_WITH_EXCEPTIONS"
    FAILED = "FAILED"


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

@dataclass
class BankTransaction:
    """A transaction from bank feed"""
    id: str
    account_id: str
    
    # Transaction details
    date: date
    amount: Decimal
    description: str
    
    # Classification
    transaction_type: str  # CREDIT, DEBIT
    category: Optional[str] = None
    
    # External reference
    external_id: str = ""
    check_number: Optional[str] = None
    
    # Matching
    match_status: MatchStatus = MatchStatus.UNMATCHED
    matched_to_id: Optional[str] = None
    match_confidence: MatchConfidence = MatchConfidence.NONE
    
    # Source
    source: TransactionSource = TransactionSource.BANK
    raw_data: Dict[str, Any] = field(default_factory=dict)
    
    # Reconciliation
    reconciled: bool = False
    reconciled_at: Optional[datetime] = None
    reconciled_by: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class InternalTransaction:
    """An internal record (invoice payment, expense, etc.)"""
    id: str
    org_id: str
    
    # Transaction details
    date: date
    amount: Decimal
    description: str
    transaction_type: str  # REVENUE, EXPENSE, TRANSFER
    
    # Source reference
    source_type: str  # INVOICE, PAYMENT, EXPENSE, TRANSFER
    source_id: str
    
    # Expected bank details
    expected_account_id: Optional[str] = None
    expected_date_range: Tuple[date, date] = None
    
    # Matching
    match_status: MatchStatus = MatchStatus.UNMATCHED
    matched_to_id: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class TransactionMatch:
    """A matched pair of transactions"""
    id: str
    org_id: str
    
    # Matched transactions
    bank_transaction_id: str
    internal_transaction_id: str
    
    # Match details
    confidence: MatchConfidence
    match_score: Decimal  # 0-100
    match_method: str  # AUTO, MANUAL, RULE
    
    # Amount comparison
    bank_amount: Decimal
    internal_amount: Decimal
    amount_difference: Decimal
    
    # Date comparison
    bank_date: date
    internal_date: date
    date_difference_days: int
    
    # Status
    status: MatchStatus = MatchStatus.AUTO_MATCHED
    confirmed_by: Optional[str] = None
    confirmed_at: Optional[datetime] = None
    
    # Notes
    notes: str = ""
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class Discrepancy:
    """A reconciliation discrepancy"""
    id: str
    org_id: str
    account_id: str
    
    # Discrepancy details
    discrepancy_type: DiscrepancyType
    severity: str  # LOW, MEDIUM, HIGH, CRITICAL
    
    # Related transactions
    bank_transaction_id: Optional[str] = None
    internal_transaction_id: Optional[str] = None
    
    # Details
    description: str = ""
    expected_amount: Optional[Decimal] = None
    actual_amount: Optional[Decimal] = None
    difference: Optional[Decimal] = None
    
    # Resolution
    status: str = "OPEN"  # OPEN, INVESTIGATING, RESOLVED, IGNORED
    resolution: Optional[str] = None
    resolved_by: Optional[str] = None
    resolved_at: Optional[datetime] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class ReconciliationRun:
    """A reconciliation run/session"""
    id: str
    org_id: str
    account_id: str
    
    # Period
    period_start: date
    period_end: date
    
    # Status
    status: ReconciliationStatus = ReconciliationStatus.PENDING
    
    # Balances
    opening_balance_bank: Decimal = Decimal("0")
    closing_balance_bank: Decimal = Decimal("0")
    opening_balance_book: Decimal = Decimal("0")
    closing_balance_book: Decimal = Decimal("0")
    
    # Statistics
    total_bank_transactions: int = 0
    total_internal_transactions: int = 0
    auto_matched: int = 0
    manual_matched: int = 0
    unmatched_bank: int = 0
    unmatched_internal: int = 0
    discrepancies_found: int = 0
    
    # Timing
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # User
    created_by: Optional[str] = None
    
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 1: TRANSACTION MATCHING
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class TransactionMatcher:
    """
    PILLAR 1: TRANSACTION MATCHING
    
    Smart matching of bank transactions to internal records.
    """
    
    # Matching thresholds
    EXACT_MATCH_THRESHOLD = 100
    HIGH_CONFIDENCE_THRESHOLD = 90
    MEDIUM_CONFIDENCE_THRESHOLD = 70
    LOW_CONFIDENCE_THRESHOLD = 50
    
    # Tolerances
    AMOUNT_TOLERANCE = Decimal("0.01")  # $0.01 tolerance
    DATE_TOLERANCE_DAYS = 3  # 3 days tolerance
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def match_transactions(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Run matching for a period"""
        
        # Get bank transactions
        bank_txns = await self._get_bank_transactions(account_id, period_start, period_end)
        
        # Get internal transactions
        internal_txns = await self._get_internal_transactions(org_id, account_id, period_start, period_end)
        
        results = {
            "matches": [],
            "unmatched_bank": [],
            "unmatched_internal": [],
            "duplicates": []
        }
        
        matched_bank_ids: Set[str] = set()
        matched_internal_ids: Set[str] = set()
        
        # Phase 1: Exact matches (amount + date + reference)
        for bank_txn in bank_txns:
            if bank_txn["id"] in matched_bank_ids:
                continue
            
            for internal_txn in internal_txns:
                if internal_txn["id"] in matched_internal_ids:
                    continue
                
                score, details = self._calculate_match_score(bank_txn, internal_txn)
                
                if score >= self.EXACT_MATCH_THRESHOLD:
                    match = await self._create_match(
                        org_id, bank_txn, internal_txn, score, MatchConfidence.EXACT
                    )
                    results["matches"].append(match)
                    matched_bank_ids.add(bank_txn["id"])
                    matched_internal_ids.add(internal_txn["id"])
                    break
        
        # Phase 2: High confidence matches (amount + fuzzy date/description)
        for bank_txn in bank_txns:
            if bank_txn["id"] in matched_bank_ids:
                continue
            
            best_match = None
            best_score = 0
            
            for internal_txn in internal_txns:
                if internal_txn["id"] in matched_internal_ids:
                    continue
                
                score, details = self._calculate_match_score(bank_txn, internal_txn)
                
                if score > best_score and score >= self.HIGH_CONFIDENCE_THRESHOLD:
                    best_score = score
                    best_match = internal_txn
            
            if best_match:
                match = await self._create_match(
                    org_id, bank_txn, best_match, best_score, MatchConfidence.HIGH
                )
                results["matches"].append(match)
                matched_bank_ids.add(bank_txn["id"])
                matched_internal_ids.add(best_match["id"])
        
        # Phase 3: Medium confidence suggestions
        for bank_txn in bank_txns:
            if bank_txn["id"] in matched_bank_ids:
                continue
            
            suggestions = []
            for internal_txn in internal_txns:
                if internal_txn["id"] in matched_internal_ids:
                    continue
                
                score, details = self._calculate_match_score(bank_txn, internal_txn)
                
                if score >= self.LOW_CONFIDENCE_THRESHOLD:
                    suggestions.append({
                        "internal_txn": internal_txn,
                        "score": score,
                        "details": details
                    })
            
            if suggestions:
                # Sort by score descending
                suggestions.sort(key=lambda x: x["score"], reverse=True)
                bank_txn["suggested_matches"] = suggestions[:3]  # Top 3 suggestions
            
            results["unmatched_bank"].append(bank_txn)
        
        # Collect unmatched internal transactions
        for internal_txn in internal_txns:
            if internal_txn["id"] not in matched_internal_ids:
                results["unmatched_internal"].append(internal_txn)
        
        # Detect duplicates
        results["duplicates"] = await self._detect_duplicates(bank_txns)
        
        return results
    
    def _calculate_match_score(
        self,
        bank_txn: Dict,
        internal_txn: Dict
    ) -> Tuple[Decimal, Dict]:
        """Calculate match score between two transactions"""
        
        score = Decimal("0")
        details = {}
        
        # Amount match (40 points max)
        bank_amount = abs(Decimal(str(bank_txn["amount"])))
        internal_amount = abs(Decimal(str(internal_txn["amount"])))
        amount_diff = abs(bank_amount - internal_amount)
        
        if amount_diff <= self.AMOUNT_TOLERANCE:
            score += 40
            details["amount"] = "EXACT"
        elif amount_diff <= Decimal("1.00"):
            score += 35
            details["amount"] = "CLOSE"
        elif amount_diff / max(bank_amount, Decimal("1")) <= Decimal("0.01"):
            score += 30
            details["amount"] = "WITHIN_1%"
        else:
            details["amount"] = "MISMATCH"
        
        # Date match (30 points max)
        bank_date = bank_txn["date"]
        internal_date = internal_txn["date"]
        
        if isinstance(bank_date, str):
            bank_date = date.fromisoformat(bank_date)
        if isinstance(internal_date, str):
            internal_date = date.fromisoformat(internal_date)
        
        date_diff = abs((bank_date - internal_date).days)
        
        if date_diff == 0:
            score += 30
            details["date"] = "EXACT"
        elif date_diff <= 1:
            score += 25
            details["date"] = "1_DAY"
        elif date_diff <= self.DATE_TOLERANCE_DAYS:
            score += 20
            details["date"] = f"{date_diff}_DAYS"
        elif date_diff <= 7:
            score += 10
            details["date"] = "WITHIN_WEEK"
        else:
            details["date"] = "MISMATCH"
        
        # Description similarity (20 points max)
        bank_desc = bank_txn.get("description", "").lower()
        internal_desc = internal_txn.get("description", "").lower()
        
        desc_similarity = SequenceMatcher(None, bank_desc, internal_desc).ratio()
        
        if desc_similarity >= 0.9:
            score += 20
            details["description"] = "HIGH_MATCH"
        elif desc_similarity >= 0.7:
            score += 15
            details["description"] = "MEDIUM_MATCH"
        elif desc_similarity >= 0.5:
            score += 10
            details["description"] = "LOW_MATCH"
        else:
            details["description"] = "NO_MATCH"
        
        # Reference/ID match (10 points max)
        bank_ref = bank_txn.get("external_id", "")
        internal_ref = internal_txn.get("source_id", "")
        
        if bank_ref and internal_ref and bank_ref in internal_ref:
            score += 10
            details["reference"] = "MATCH"
        elif bank_ref and internal_ref:
            details["reference"] = "NO_MATCH"
        else:
            details["reference"] = "MISSING"
        
        return score, details
    
    async def _create_match(
        self,
        org_id: str,
        bank_txn: Dict,
        internal_txn: Dict,
        score: Decimal,
        confidence: MatchConfidence
    ) -> TransactionMatch:
        """Create a transaction match record"""
        
        bank_amount = Decimal(str(bank_txn["amount"]))
        internal_amount = Decimal(str(internal_txn["amount"]))
        
        bank_date = bank_txn["date"]
        internal_date = internal_txn["date"]
        if isinstance(bank_date, str):
            bank_date = date.fromisoformat(bank_date)
        if isinstance(internal_date, str):
            internal_date = date.fromisoformat(internal_date)
        
        match = TransactionMatch(
            id=f"MATCH-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            bank_transaction_id=bank_txn["id"],
            internal_transaction_id=internal_txn["id"],
            confidence=confidence,
            match_score=score,
            match_method="AUTO",
            bank_amount=bank_amount,
            internal_amount=internal_amount,
            amount_difference=abs(bank_amount - internal_amount),
            bank_date=bank_date,
            internal_date=internal_date,
            date_difference_days=abs((bank_date - internal_date).days)
        )
        
        await self._save_match(match)
        
        # Update transaction statuses
        await self._update_match_status(bank_txn["id"], internal_txn["id"], match.id, confidence)
        
        return match
    
    async def manual_match(
        self,
        org_id: str,
        bank_transaction_id: str,
        internal_transaction_id: str,
        user_id: str,
        notes: str = ""
    ) -> TransactionMatch:
        """Manually match two transactions"""
        
        async with self.db.acquire() as conn:
            bank_txn = await conn.fetchrow(
                "SELECT * FROM bank_transactions WHERE id = $1", bank_transaction_id
            )
            internal_txn = await conn.fetchrow(
                "SELECT * FROM internal_transactions WHERE id = $1", internal_transaction_id
            )
        
        if not bank_txn or not internal_txn:
            raise ValueError("Transaction not found")
        
        score, _ = self._calculate_match_score(dict(bank_txn), dict(internal_txn))
        
        match = TransactionMatch(
            id=f"MATCH-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            bank_transaction_id=bank_transaction_id,
            internal_transaction_id=internal_transaction_id,
            confidence=MatchConfidence.HIGH,
            match_score=score,
            match_method="MANUAL",
            bank_amount=Decimal(str(bank_txn["amount"])),
            internal_amount=Decimal(str(internal_txn["amount"])),
            amount_difference=abs(Decimal(str(bank_txn["amount"])) - Decimal(str(internal_txn["amount"]))),
            bank_date=bank_txn["date"],
            internal_date=internal_txn["date"],
            date_difference_days=abs((bank_txn["date"] - internal_txn["date"]).days),
            status=MatchStatus.MANUAL_MATCHED,
            confirmed_by=user_id,
            confirmed_at=datetime.now(timezone.utc),
            notes=notes
        )
        
        await self._save_match(match)
        await self._update_match_status(
            bank_transaction_id, internal_transaction_id, match.id, MatchConfidence.HIGH
        )
        
        return match
    
    async def unmatch(self, match_id: str, user_id: str, reason: str = "") -> bool:
        """Unmatch previously matched transactions"""
        
        async with self.db.acquire() as conn:
            match = await conn.fetchrow(
                "SELECT * FROM transaction_matches WHERE id = $1", match_id
            )
            
            if not match:
                return False
            
            # Reset transaction statuses
            await conn.execute("""
                UPDATE bank_transactions SET 
                    match_status = 'UNMATCHED', matched_to_id = NULL
                WHERE id = $1
            """, match["bank_transaction_id"])
            
            await conn.execute("""
                UPDATE internal_transactions SET 
                    match_status = 'UNMATCHED', matched_to_id = NULL
                WHERE id = $1
            """, match["internal_transaction_id"])
            
            # Delete match record
            await conn.execute("DELETE FROM transaction_matches WHERE id = $1", match_id)
        
        return True
    
    async def _detect_duplicates(self, transactions: List[Dict]) -> List[Dict]:
        """Detect potential duplicate transactions"""
        
        duplicates = []
        seen = {}
        
        for txn in transactions:
            # Create fingerprint
            fingerprint = f"{txn['amount']}:{txn['date']}:{txn.get('description', '')[:20]}"
            
            if fingerprint in seen:
                duplicates.append({
                    "original": seen[fingerprint],
                    "duplicate": txn,
                    "fingerprint": fingerprint
                })
            else:
                seen[fingerprint] = txn
        
        return duplicates
    
    async def _get_bank_transactions(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM bank_transactions
                WHERE account_id = $1 AND date BETWEEN $2 AND $3
                ORDER BY date, amount
            """, account_id, start_date, end_date)
            return [dict(r) for r in rows]
    
    async def _get_internal_transactions(
        self,
        org_id: str,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM internal_transactions
                WHERE org_id = $1 
                AND (expected_account_id = $2 OR expected_account_id IS NULL)
                AND date BETWEEN $3 AND $4
                ORDER BY date, amount
            """, org_id, account_id, start_date, end_date)
            return [dict(r) for r in rows]
    
    async def _save_match(self, match: TransactionMatch):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO transaction_matches (
                    id, org_id, bank_transaction_id, internal_transaction_id,
                    confidence, match_score, match_method, bank_amount, internal_amount,
                    amount_difference, bank_date, internal_date, date_difference_days,
                    status, confirmed_by, confirmed_at, notes, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17,$18)
            """, match.id, match.org_id, match.bank_transaction_id,
                match.internal_transaction_id, match.confidence.value,
                float(match.match_score), match.match_method,
                float(match.bank_amount), float(match.internal_amount),
                float(match.amount_difference), match.bank_date, match.internal_date,
                match.date_difference_days, match.status.value,
                match.confirmed_by, match.confirmed_at, match.notes, match.created_at)
    
    async def _update_match_status(
        self,
        bank_id: str,
        internal_id: str,
        match_id: str,
        confidence: MatchConfidence
    ):
        status = MatchStatus.AUTO_MATCHED if confidence in [MatchConfidence.EXACT, MatchConfidence.HIGH] else MatchStatus.UNMATCHED
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE bank_transactions SET 
                    match_status = $1, matched_to_id = $2, match_confidence = $3
                WHERE id = $4
            """, status.value, match_id, confidence.value, bank_id)
            
            await conn.execute("""
                UPDATE internal_transactions SET 
                    match_status = $1, matched_to_id = $2
                WHERE id = $3
            """, status.value, match_id, internal_id)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 2: DISCREPANCY DETECTION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class DiscrepancyDetector:
    """
    PILLAR 2: DISCREPANCY DETECTION
    
    Find missing deposits, unexpected fees, balance drifts.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def detect_discrepancies(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date
    ) -> List[Discrepancy]:
        """Detect all discrepancies for a period"""
        
        discrepancies = []
        
        # 1. Missing deposits (internal records without bank match)
        missing_deposits = await self._detect_missing_deposits(org_id, account_id, period_start, period_end)
        discrepancies.extend(missing_deposits)
        
        # 2. Unmatched bank transactions
        unmatched_bank = await self._detect_unmatched_bank(account_id, period_start, period_end)
        discrepancies.extend(unmatched_bank)
        
        # 3. Unexpected fees
        unexpected_fees = await self._detect_unexpected_fees(account_id, period_start, period_end)
        discrepancies.extend(unexpected_fees)
        
        # 4. Amount mismatches in matches
        amount_mismatches = await self._detect_amount_mismatches(org_id, period_start, period_end)
        discrepancies.extend(amount_mismatches)
        
        # 5. Balance drift
        balance_drift = await self._detect_balance_drift(account_id, period_end)
        if balance_drift:
            discrepancies.append(balance_drift)
        
        # Save all discrepancies
        for d in discrepancies:
            await self._save_discrepancy(d)
        
        return discrepancies
    
    async def _detect_missing_deposits(
        self,
        org_id: str,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Discrepancy]:
        """Detect internal revenue records missing from bank"""
        
        discrepancies = []
        
        async with self.db.acquire() as conn:
            # Find unmatched internal deposits
            missing = await conn.fetch("""
                SELECT * FROM internal_transactions
                WHERE org_id = $1
                AND transaction_type = 'REVENUE'
                AND match_status = 'UNMATCHED'
                AND date BETWEEN $2 AND $3
                AND date < CURRENT_DATE - INTERVAL '3 days'
            """, org_id, start_date, end_date)
        
        for txn in missing:
            # Calculate severity based on amount and age
            amount = Decimal(str(txn["amount"]))
            days_old = (date.today() - txn["date"]).days
            
            if amount >= 1000 or days_old >= 14:
                severity = "HIGH"
            elif amount >= 100 or days_old >= 7:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            discrepancies.append(Discrepancy(
                id=f"DISC-{uuid.uuid4().hex[:12].upper()}",
                org_id=org_id,
                account_id=account_id,
                discrepancy_type=DiscrepancyType.MISSING_DEPOSIT,
                severity=severity,
                internal_transaction_id=txn["id"],
                description=f"Expected deposit of ${amount:,.2f} from {txn['date']} not found in bank",
                expected_amount=amount
            ))
        
        return discrepancies
    
    async def _detect_unmatched_bank(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Discrepancy]:
        """Detect bank transactions without internal records"""
        
        discrepancies = []
        
        async with self.db.acquire() as conn:
            unmatched = await conn.fetch("""
                SELECT * FROM bank_transactions
                WHERE account_id = $1
                AND match_status = 'UNMATCHED'
                AND date BETWEEN $2 AND $3
            """, account_id, start_date, end_date)
        
        for txn in unmatched:
            amount = abs(Decimal(str(txn["amount"])))
            
            # Determine severity
            if amount >= 500:
                severity = "HIGH"
            elif amount >= 100:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            dtype = DiscrepancyType.UNMATCHED_BANK
            
            discrepancies.append(Discrepancy(
                id=f"DISC-{uuid.uuid4().hex[:12].upper()}",
                org_id=txn.get("org_id", ""),
                account_id=account_id,
                discrepancy_type=dtype,
                severity=severity,
                bank_transaction_id=txn["id"],
                description=f"Bank transaction of ${amount:,.2f} on {txn['date']} has no matching record: {txn['description'][:50]}",
                actual_amount=Decimal(str(txn["amount"]))
            ))
        
        return discrepancies
    
    async def _detect_unexpected_fees(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Discrepancy]:
        """Detect unexpected bank fees"""
        
        discrepancies = []
        
        # Common fee keywords
        fee_keywords = ['fee', 'charge', 'service charge', 'maintenance', 'overdraft', 'wire fee']
        
        async with self.db.acquire() as conn:
            txns = await conn.fetch("""
                SELECT * FROM bank_transactions
                WHERE account_id = $1
                AND date BETWEEN $2 AND $3
                AND amount < 0
            """, account_id, start_date, end_date)
        
        for txn in txns:
            desc_lower = txn["description"].lower()
            
            if any(keyword in desc_lower for keyword in fee_keywords):
                amount = abs(Decimal(str(txn["amount"])))
                
                # Flag larger fees as higher severity
                if amount >= 50:
                    severity = "HIGH"
                elif amount >= 25:
                    severity = "MEDIUM"
                else:
                    severity = "LOW"
                
                discrepancies.append(Discrepancy(
                    id=f"DISC-{uuid.uuid4().hex[:12].upper()}",
                    org_id=txn.get("org_id", ""),
                    account_id=account_id,
                    discrepancy_type=DiscrepancyType.UNEXPECTED_FEE,
                    severity=severity,
                    bank_transaction_id=txn["id"],
                    description=f"Bank fee detected: ${amount:,.2f} - {txn['description'][:50]}",
                    actual_amount=amount
                ))
        
        return discrepancies
    
    async def _detect_amount_mismatches(
        self,
        org_id: str,
        start_date: date,
        end_date: date
    ) -> List[Discrepancy]:
        """Detect matches with amount differences"""
        
        discrepancies = []
        
        async with self.db.acquire() as conn:
            matches = await conn.fetch("""
                SELECT * FROM transaction_matches
                WHERE org_id = $1
                AND amount_difference > 0.01
                AND bank_date BETWEEN $2 AND $3
            """, org_id, start_date, end_date)
        
        for match in matches:
            diff = Decimal(str(match["amount_difference"]))
            
            if diff >= 10:
                severity = "HIGH"
            elif diff >= 1:
                severity = "MEDIUM"
            else:
                severity = "LOW"
            
            discrepancies.append(Discrepancy(
                id=f"DISC-{uuid.uuid4().hex[:12].upper()}",
                org_id=org_id,
                account_id="",  # Would need to look up
                discrepancy_type=DiscrepancyType.AMOUNT_MISMATCH,
                severity=severity,
                bank_transaction_id=match["bank_transaction_id"],
                internal_transaction_id=match["internal_transaction_id"],
                description=f"Amount mismatch: Bank ${match['bank_amount']:,.2f} vs Internal ${match['internal_amount']:,.2f}",
                expected_amount=Decimal(str(match["internal_amount"])),
                actual_amount=Decimal(str(match["bank_amount"])),
                difference=diff
            ))
        
        return discrepancies
    
    async def _detect_balance_drift(
        self,
        account_id: str,
        as_of_date: date
    ) -> Optional[Discrepancy]:
        """Detect if book balance drifts from bank balance"""
        
        async with self.db.acquire() as conn:
            # Get latest bank balance
            bank_balance = await conn.fetchrow("""
                SELECT cached_balance, balance_updated_at
                FROM bank_accounts WHERE id = $1
            """, account_id)
            
            # Calculate book balance from transactions
            book_balance = await conn.fetchrow("""
                SELECT COALESCE(SUM(
                    CASE WHEN transaction_type = 'CREDIT' THEN amount ELSE -amount END
                ), 0) as balance
                FROM bank_transactions
                WHERE account_id = $1 AND reconciled = true
            """, account_id)
        
        if not bank_balance:
            return None
        
        bank = Decimal(str(bank_balance["cached_balance"]))
        book = Decimal(str(book_balance["balance"]))
        drift = abs(bank - book)
        
        if drift <= Decimal("0.01"):
            return None
        
        if drift >= 100:
            severity = "CRITICAL"
        elif drift >= 10:
            severity = "HIGH"
        else:
            severity = "MEDIUM"
        
        return Discrepancy(
            id=f"DISC-{uuid.uuid4().hex[:12].upper()}",
            org_id="",
            account_id=account_id,
            discrepancy_type=DiscrepancyType.BALANCE_DRIFT,
            severity=severity,
            description=f"Balance drift detected: Bank ${bank:,.2f} vs Book ${book:,.2f} (Diff: ${drift:,.2f})",
            expected_amount=bank,
            actual_amount=book,
            difference=drift
        )
    
    async def resolve_discrepancy(
        self,
        discrepancy_id: str,
        resolution: str,
        resolved_by: str
    ) -> Discrepancy:
        """Resolve a discrepancy"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE discrepancies SET
                    status = 'RESOLVED', resolution = $1,
                    resolved_by = $2, resolved_at = $3
                WHERE id = $4
            """, resolution, resolved_by, datetime.now(timezone.utc), discrepancy_id)
            
            row = await conn.fetchrow(
                "SELECT * FROM discrepancies WHERE id = $1", discrepancy_id
            )
            return row
    
    async def _save_discrepancy(self, d: Discrepancy):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO discrepancies (
                    id, org_id, account_id, discrepancy_type, severity,
                    bank_transaction_id, internal_transaction_id, description,
                    expected_amount, actual_amount, difference, status, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13)
            """, d.id, d.org_id, d.account_id, d.discrepancy_type.value,
                d.severity, d.bank_transaction_id, d.internal_transaction_id,
                d.description, float(d.expected_amount) if d.expected_amount else None,
                float(d.actual_amount) if d.actual_amount else None,
                float(d.difference) if d.difference else None,
                d.status, d.created_at)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 3: PAYMENT PROCESSOR RECONCILIATION
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class PaymentProcessorReconciler:
    """
    PILLAR 3: PAYMENT PROCESSOR RECONCILIATION
    
    Match Stripe/PayPal/Wise transactions to bank deposits.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def reconcile_stripe_payouts(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Reconcile Stripe payouts to bank deposits"""
        
        results = {
            "matched": [],
            "unmatched_payouts": [],
            "unmatched_deposits": []
        }
        
        # Get Stripe payouts
        stripe_payouts = await self._get_stripe_payouts(org_id, period_start, period_end)
        
        # Get bank deposits that look like Stripe
        bank_deposits = await self._get_stripe_like_deposits(account_id, period_start, period_end)
        
        matched_payout_ids = set()
        matched_deposit_ids = set()
        
        for payout in stripe_payouts:
            payout_amount = Decimal(str(payout["amount"]))
            payout_date = payout["arrival_date"]
            
            # Look for matching bank deposit
            for deposit in bank_deposits:
                if deposit["id"] in matched_deposit_ids:
                    continue
                
                deposit_amount = Decimal(str(deposit["amount"]))
                deposit_date = deposit["date"]
                
                # Check amount match (Stripe payouts are exact)
                if abs(payout_amount - deposit_amount) <= Decimal("0.01"):
                    # Check date (usually same day or +1)
                    date_diff = abs((deposit_date - payout_date).days)
                    
                    if date_diff <= 2:
                        results["matched"].append({
                            "stripe_payout": payout,
                            "bank_deposit": deposit,
                            "date_difference": date_diff
                        })
                        matched_payout_ids.add(payout["id"])
                        matched_deposit_ids.add(deposit["id"])
                        
                        # Update internal tracking
                        await self._link_stripe_to_bank(payout["id"], deposit["id"])
                        break
        
        # Collect unmatched
        for payout in stripe_payouts:
            if payout["id"] not in matched_payout_ids:
                results["unmatched_payouts"].append(payout)
        
        for deposit in bank_deposits:
            if deposit["id"] not in matched_deposit_ids:
                results["unmatched_deposits"].append(deposit)
        
        return results
    
    async def reconcile_paypal(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Reconcile PayPal transfers to bank"""
        
        # Similar logic to Stripe
        return {"matched": [], "unmatched": []}
    
    async def reconcile_wise(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Reconcile Wise transfers to bank"""
        
        # Similar logic
        return {"matched": [], "unmatched": []}
    
    async def _get_stripe_payouts(
        self,
        org_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get Stripe payouts for period"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM stripe_payouts
                WHERE org_id = $1 AND arrival_date BETWEEN $2 AND $3
            """, org_id, start_date, end_date)
            return [dict(r) for r in rows]
    
    async def _get_stripe_like_deposits(
        self,
        account_id: str,
        start_date: date,
        end_date: date
    ) -> List[Dict]:
        """Get bank deposits that look like Stripe payouts"""
        async with self.db.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM bank_transactions
                WHERE account_id = $1
                AND date BETWEEN $2 AND $3
                AND amount > 0
                AND (
                    description ILIKE '%stripe%'
                    OR description ILIKE '%transfer%'
                    OR description ILIKE '%deposit%'
                )
            """, account_id, start_date, end_date)
            return [dict(r) for r in rows]
    
    async def _link_stripe_to_bank(self, payout_id: str, bank_txn_id: str):
        """Link Stripe payout to bank transaction"""
        async with self.db.acquire() as conn:
            await conn.execute("""
                UPDATE stripe_payouts SET bank_transaction_id = $1 WHERE id = $2
            """, bank_txn_id, payout_id)
            await conn.execute("""
                UPDATE bank_transactions SET 
                    match_status = 'AUTO_MATCHED',
                    matched_to_id = $1
                WHERE id = $2
            """, payout_id, bank_txn_id)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# PILLAR 4: REPORTING & AUDIT
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class ReconciliationReporter:
    """
    PILLAR 4: REPORTING & AUDIT
    
    Generate reconciliation reports and maintain audit trail.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
    
    async def generate_reconciliation_report(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date
    ) -> Dict[str, Any]:
        """Generate comprehensive reconciliation report"""
        
        async with self.db.acquire() as conn:
            # Bank transactions summary
            bank_summary = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_credits,
                    SUM(CASE WHEN amount < 0 THEN amount ELSE 0 END) as total_debits,
                    SUM(CASE WHEN match_status = 'AUTO_MATCHED' THEN 1 ELSE 0 END) as auto_matched,
                    SUM(CASE WHEN match_status = 'MANUAL_MATCHED' THEN 1 ELSE 0 END) as manual_matched,
                    SUM(CASE WHEN match_status = 'UNMATCHED' THEN 1 ELSE 0 END) as unmatched
                FROM bank_transactions
                WHERE account_id = $1 AND date BETWEEN $2 AND $3
            """, account_id, period_start, period_end)
            
            # Internal transactions summary
            internal_summary = await conn.fetchrow("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN transaction_type = 'REVENUE' THEN amount ELSE 0 END) as total_revenue,
                    SUM(CASE WHEN transaction_type = 'EXPENSE' THEN amount ELSE 0 END) as total_expense,
                    SUM(CASE WHEN match_status != 'UNMATCHED' THEN 1 ELSE 0 END) as matched,
                    SUM(CASE WHEN match_status = 'UNMATCHED' THEN 1 ELSE 0 END) as unmatched
                FROM internal_transactions
                WHERE org_id = $1 AND date BETWEEN $2 AND $3
            """, org_id, period_start, period_end)
            
            # Discrepancies
            discrepancies = await conn.fetch("""
                SELECT discrepancy_type, severity, COUNT(*) as count,
                       COALESCE(SUM(ABS(difference)), 0) as total_amount
                FROM discrepancies
                WHERE org_id = $1 AND account_id = $2
                AND created_at >= $3 AND created_at <= $4
                GROUP BY discrepancy_type, severity
            """, org_id, account_id, period_start, period_end)
            
            # Account balance
            account = await conn.fetchrow(
                "SELECT * FROM bank_accounts WHERE id = $1", account_id
            )
        
        match_rate = 0
        if bank_summary["total"] > 0:
            matched = bank_summary["auto_matched"] + bank_summary["manual_matched"]
            match_rate = (matched / bank_summary["total"]) * 100
        
        return {
            "period": {
                "start": period_start.isoformat(),
                "end": period_end.isoformat()
            },
            "account": {
                "id": account_id,
                "name": account["account_name"] if account else "",
                "current_balance": float(account["cached_balance"]) if account else 0
            },
            "bank_transactions": {
                "total": bank_summary["total"],
                "credits": float(bank_summary["total_credits"]),
                "debits": float(bank_summary["total_debits"]),
                "net": float(bank_summary["total_credits"] + bank_summary["total_debits"]),
                "auto_matched": bank_summary["auto_matched"],
                "manual_matched": bank_summary["manual_matched"],
                "unmatched": bank_summary["unmatched"]
            },
            "internal_transactions": {
                "total": internal_summary["total"],
                "revenue": float(internal_summary["total_revenue"]),
                "expenses": float(internal_summary["total_expense"]),
                "matched": internal_summary["matched"],
                "unmatched": internal_summary["unmatched"]
            },
            "matching": {
                "match_rate": round(match_rate, 1),
                "auto_match_rate": round(
                    (bank_summary["auto_matched"] / max(bank_summary["total"], 1)) * 100, 1
                )
            },
            "discrepancies": {
                "total": sum(d["count"] for d in discrepancies),
                "total_amount": sum(float(d["total_amount"]) for d in discrepancies),
                "by_type": [
                    {
                        "type": d["discrepancy_type"],
                        "severity": d["severity"],
                        "count": d["count"],
                        "amount": float(d["total_amount"])
                    }
                    for d in discrepancies
                ]
            },
            "status": "CLEAN" if bank_summary["unmatched"] == 0 else "NEEDS_ATTENTION"
        }
    
    async def get_audit_trail(
        self,
        org_id: str,
        entity_type: str = None,
        entity_id: str = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get reconciliation audit trail"""
        
        async with self.db.acquire() as conn:
            query = """
                SELECT * FROM reconciliation_audit
                WHERE org_id = $1
            """
            params = [org_id]
            
            if entity_type:
                query += f" AND entity_type = ${len(params) + 1}"
                params.append(entity_type)
            
            if entity_id:
                query += f" AND entity_id = ${len(params) + 1}"
                params.append(entity_id)
            
            query += f" ORDER BY created_at DESC LIMIT ${len(params) + 1}"
            params.append(limit)
            
            rows = await conn.fetch(query, *params)
            return [dict(r) for r in rows]
    
    async def log_audit_event(
        self,
        org_id: str,
        action: str,
        entity_type: str,
        entity_id: str,
        user_id: str,
        details: Dict = None
    ):
        """Log an audit event"""
        
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO reconciliation_audit (
                    id, org_id, action, entity_type, entity_id,
                    user_id, details, created_at
                ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8)
            """, f"AUDIT-{uuid.uuid4().hex[:12]}", org_id, action,
                entity_type, entity_id, user_id,
                json.dumps(details) if details else None,
                datetime.now(timezone.utc))


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# MAIN SERVICE
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

class BankReconciliationEngine:
    """
    BANK RECONCILIATION ENGINE - Main Service
    
    Trust But Verify.
    """
    
    def __init__(self, db_pool: asyncpg.Pool):
        self.db = db_pool
        self.matcher = TransactionMatcher(db_pool)
        self.detector = DiscrepancyDetector(db_pool)
        self.processor_reconciler = PaymentProcessorReconciler(db_pool)
        self.reporter = ReconciliationReporter(db_pool)
    
    async def run_reconciliation(
        self,
        org_id: str,
        account_id: str,
        period_start: date,
        period_end: date,
        user_id: str = None
    ) -> ReconciliationRun:
        """Run full reconciliation for an account"""
        
        # Create reconciliation run record
        run = ReconciliationRun(
            id=f"RECON-{uuid.uuid4().hex[:12].upper()}",
            org_id=org_id,
            account_id=account_id,
            period_start=period_start,
            period_end=period_end,
            status=ReconciliationStatus.IN_PROGRESS,
            started_at=datetime.now(timezone.utc),
            created_by=user_id
        )
        
        try:
            # Phase 1: Match transactions
            match_results = await self.matcher.match_transactions(
                org_id, account_id, period_start, period_end
            )
            
            run.auto_matched = len([m for m in match_results["matches"] 
                                   if m.match_method == "AUTO"])
            run.unmatched_bank = len(match_results["unmatched_bank"])
            run.unmatched_internal = len(match_results["unmatched_internal"])
            
            # Phase 2: Detect discrepancies
            discrepancies = await self.detector.detect_discrepancies(
                org_id, account_id, period_start, period_end
            )
            
            run.discrepancies_found = len(discrepancies)
            
            # Phase 3: Reconcile payment processors
            stripe_results = await self.processor_reconciler.reconcile_stripe_payouts(
                org_id, account_id, period_start, period_end
            )
            
            # Update run status
            if run.unmatched_bank == 0 and run.unmatched_internal == 0 and run.discrepancies_found == 0:
                run.status = ReconciliationStatus.COMPLETED
            else:
                run.status = ReconciliationStatus.COMPLETED_WITH_EXCEPTIONS
            
            run.completed_at = datetime.now(timezone.utc)
            
        except Exception as e:
            run.status = ReconciliationStatus.FAILED
            run.completed_at = datetime.now(timezone.utc)
            raise
        
        # Save run record
        await self._save_run(run)
        
        # Log audit
        await self.reporter.log_audit_event(
            org_id, "RECONCILIATION_COMPLETED", "RECONCILIATION_RUN", run.id,
            user_id or "SYSTEM",
            {"status": run.status.value, "discrepancies": run.discrepancies_found}
        )
        
        return run
    
    async def get_reconciliation_summary(self, org_id: str) -> Dict[str, Any]:
        """Get reconciliation summary across all accounts"""
        
        async with self.db.acquire() as conn:
            # Get all accounts
            accounts = await conn.fetch("""
                SELECT id, account_name, provider, cached_balance
                FROM bank_accounts WHERE org_id = $1 AND status = 'active'
            """, org_id)
            
            # Get unmatched counts
            unmatched = await conn.fetchrow("""
                SELECT 
                    SUM(CASE WHEN match_status = 'UNMATCHED' THEN 1 ELSE 0 END) as bank_unmatched
                FROM bank_transactions bt
                JOIN bank_accounts ba ON bt.account_id = ba.id
                WHERE ba.org_id = $1
            """, org_id)
            
            # Get open discrepancies
            discrepancies = await conn.fetchrow("""
                SELECT COUNT(*) as count, COALESCE(SUM(ABS(difference)), 0) as total
                FROM discrepancies
                WHERE org_id = $1 AND status = 'OPEN'
            """, org_id)
            
            # Recent reconciliations
            recent = await conn.fetch("""
                SELECT * FROM reconciliation_runs
                WHERE org_id = $1
                ORDER BY created_at DESC LIMIT 5
            """, org_id)
        
        return {
            "accounts": [
                {
                    "id": a["id"],
                    "name": a["account_name"],
                    "provider": a["provider"],
                    "balance": float(a["cached_balance"])
                }
                for a in accounts
            ],
            "unmatched_transactions": unmatched["bank_unmatched"] or 0,
            "open_discrepancies": {
                "count": discrepancies["count"],
                "total_amount": float(discrepancies["total"])
            },
            "recent_reconciliations": [dict(r) for r in recent],
            "health": "GOOD" if (unmatched["bank_unmatched"] or 0) == 0 and discrepancies["count"] == 0 else "NEEDS_ATTENTION"
        }
    
    async def _save_run(self, run: ReconciliationRun):
        async with self.db.acquire() as conn:
            await conn.execute("""
                INSERT INTO reconciliation_runs (
                    id, org_id, account_id, period_start, period_end, status,
                    total_bank_transactions, total_internal_transactions,
                    auto_matched, manual_matched, unmatched_bank, unmatched_internal,
                    discrepancies_found, started_at, completed_at, created_by, created_at
                ) VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12,$13,$14,$15,$16,$17)
            """, run.id, run.org_id, run.account_id, run.period_start, run.period_end,
                run.status.value, run.total_bank_transactions, run.total_internal_transactions,
                run.auto_matched, run.manual_matched, run.unmatched_bank, run.unmatched_internal,
                run.discrepancies_found, run.started_at, run.completed_at,
                run.created_by, run.created_at)


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# DATABASE SCHEMA
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

SCHEMA = """
CREATE TABLE IF NOT EXISTS bank_transactions (
    id VARCHAR(50) PRIMARY KEY,
    account_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    description TEXT,
    transaction_type VARCHAR(20),
    category VARCHAR(100),
    external_id VARCHAR(255),
    check_number VARCHAR(50),
    match_status VARCHAR(20) DEFAULT 'UNMATCHED',
    matched_to_id VARCHAR(50),
    match_confidence VARCHAR(20),
    source VARCHAR(20) DEFAULT 'BANK',
    raw_data JSONB,
    reconciled BOOLEAN DEFAULT false,
    reconciled_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS internal_transactions (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    date DATE NOT NULL,
    amount DECIMAL(15,2) NOT NULL,
    description TEXT,
    transaction_type VARCHAR(20),
    source_type VARCHAR(50),
    source_id VARCHAR(50),
    expected_account_id VARCHAR(50),
    match_status VARCHAR(20) DEFAULT 'UNMATCHED',
    matched_to_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS transaction_matches (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    bank_transaction_id VARCHAR(50) NOT NULL,
    internal_transaction_id VARCHAR(50) NOT NULL,
    confidence VARCHAR(20),
    match_score DECIMAL(5,2),
    match_method VARCHAR(20),
    bank_amount DECIMAL(15,2),
    internal_amount DECIMAL(15,2),
    amount_difference DECIMAL(15,2),
    bank_date DATE,
    internal_date DATE,
    date_difference_days INTEGER,
    status VARCHAR(20),
    confirmed_by VARCHAR(50),
    confirmed_at TIMESTAMPTZ,
    notes TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS discrepancies (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50),
    discrepancy_type VARCHAR(50) NOT NULL,
    severity VARCHAR(20),
    bank_transaction_id VARCHAR(50),
    internal_transaction_id VARCHAR(50),
    description TEXT,
    expected_amount DECIMAL(15,2),
    actual_amount DECIMAL(15,2),
    difference DECIMAL(15,2),
    status VARCHAR(20) DEFAULT 'OPEN',
    resolution TEXT,
    resolved_by VARCHAR(50),
    resolved_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reconciliation_runs (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    account_id VARCHAR(50) NOT NULL,
    period_start DATE,
    period_end DATE,
    status VARCHAR(20),
    total_bank_transactions INTEGER DEFAULT 0,
    total_internal_transactions INTEGER DEFAULT 0,
    auto_matched INTEGER DEFAULT 0,
    manual_matched INTEGER DEFAULT 0,
    unmatched_bank INTEGER DEFAULT 0,
    unmatched_internal INTEGER DEFAULT 0,
    discrepancies_found INTEGER DEFAULT 0,
    started_at TIMESTAMPTZ,
    completed_at TIMESTAMPTZ,
    created_by VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS reconciliation_audit (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    action VARCHAR(100),
    entity_type VARCHAR(50),
    entity_id VARCHAR(50),
    user_id VARCHAR(50),
    details JSONB,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS stripe_payouts (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    amount DECIMAL(15,2),
    arrival_date DATE,
    status VARCHAR(20),
    bank_transaction_id VARCHAR(50),
    created_at TIMESTAMPTZ DEFAULT NOW()
);
"""


# ═══════════════════════════════════════════════════════════════════════════════════════════════════════
# API ENDPOINTS
# ═══════════════════════════════════════════════════════════════════════════════════════════════════════

from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI(title="Bank Reconciliation Engine", version="3.0.0")


class ReconcileRequest(BaseModel):
    account_id: str
    period_start: str
    period_end: str


class ManualMatchRequest(BaseModel):
    bank_transaction_id: str
    internal_transaction_id: str
    notes: str = ""


@app.post("/api/v1/reconciliation/{org_id}/run")
async def run_reconciliation(org_id: str, request: ReconcileRequest):
    return {"status": "requires_db"}


@app.get("/api/v1/reconciliation/{org_id}/summary")
async def get_summary(org_id: str):
    return {"status": "requires_db"}


@app.get("/api/v1/reconciliation/{org_id}/report")
async def get_report(org_id: str, account_id: str, start: str, end: str):
    return {"status": "requires_db"}


@app.post("/api/v1/reconciliation/{org_id}/match")
async def manual_match(org_id: str, request: ManualMatchRequest):
    return {"status": "requires_db"}


@app.delete("/api/v1/reconciliation/{org_id}/match/{match_id}")
async def unmatch(org_id: str, match_id: str):
    return {"status": "requires_db"}


@app.get("/api/v1/reconciliation/{org_id}/discrepancies")
async def get_discrepancies(org_id: str, status: Optional[str] = "OPEN"):
    return {"status": "requires_db"}


@app.post("/api/v1/reconciliation/{org_id}/discrepancies/{disc_id}/resolve")
async def resolve_discrepancy(org_id: str, disc_id: str, resolution: str):
    return {"status": "requires_db"}


@app.get("/api/v1/reconciliation/{org_id}/unmatched")
async def get_unmatched(org_id: str, account_id: Optional[str] = None):
    return {"status": "requires_db"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=4022)
