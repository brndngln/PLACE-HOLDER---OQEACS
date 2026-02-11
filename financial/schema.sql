-- OMNI QUANTUM ELITE v3.0 - FINANCIAL FORTRESS CANONICAL SCHEMA
-- Consolidated from all financial service SQL usage.

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Core business entities
CREATE TABLE IF NOT EXISTS businesses (
    id VARCHAR(50) PRIMARY KEY,
    parent_id VARCHAR(50),
    name VARCHAR(255) NOT NULL,
    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS bank_accounts (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    account_name VARCHAR(255) NOT NULL,
    provider VARCHAR(50),
    account_type VARCHAR(50),
    cached_balance DECIMAL(15,2) DEFAULT 0,
    balance_updated_at TIMESTAMPTZ,
    status VARCHAR(20) DEFAULT 'active',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS customers (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    business_id VARCHAR(50),
    name VARCHAR(255),
    email VARCHAR(255),
    phone VARCHAR(50),
    status VARCHAR(20) DEFAULT 'ACTIVE',

    -- revenue and health
    mrr DECIMAL(15,2) DEFAULT 0,
    ltv DECIMAL(15,2) DEFAULT 0,
    total_revenue DECIMAL(15,2) DEFAULT 0,
    total_invoiced DECIMAL(15,2) DEFAULT 0,
    total_paid DECIMAL(15,2) DEFAULT 0,
    total_outstanding DECIMAL(15,2) DEFAULT 0,
    health_score INTEGER DEFAULT 100,
    churn_risk VARCHAR(20) DEFAULT 'LOW',

    -- billing profile
    billing_email VARCHAR(255),
    billing_address JSONB DEFAULT '{}',
    tax_id VARCHAR(50),
    preferred_payment_method VARCHAR(20) DEFAULT 'STRIPE',
    stripe_customer_id VARCHAR(100),
    auto_charge_enabled BOOLEAN DEFAULT false,
    credit_balance DECIMAL(15,2) DEFAULT 0,
    payment_score INTEGER DEFAULT 100,
    avg_days_to_pay INTEGER DEFAULT 0,

    -- lifecycle
    segment VARCHAR(20) DEFAULT 'SMB',
    acquired_at TIMESTAMPTZ,
    churned_at TIMESTAMPTZ,
    last_activity TIMESTAMPTZ,
    suspended_at TIMESTAMPTZ,
    suspension_reason TEXT,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_customers_business FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS subscriptions (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,

    -- customer subscription fields (invoice engine)
    business_id VARCHAR(50),
    customer_id VARCHAR(50),
    mrr DECIMAL(15,2) DEFAULT 0,

    -- vendor subscription fields (expense engine)
    vendor_id VARCHAR(50),
    name VARCHAR(255),
    amount DECIMAL(15,2) DEFAULT 0,
    billing_cycle VARCHAR(20) DEFAULT 'MONTHLY',
    annual_cost DECIMAL(15,2) DEFAULT 0,
    usage_score INTEGER DEFAULT 100,
    renewal_date DATE,
    next_billing_date DATE,

    status VARCHAR(20) DEFAULT 'ACTIVE',
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_subscriptions_business FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL,
    CONSTRAINT fk_subscriptions_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS transactions (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    business_id VARCHAR(50),
    customer_id VARCHAR(50),
    transaction_type VARCHAR(20),
    category VARCHAR(100),
    amount DECIMAL(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_transactions_business FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL,
    CONSTRAINT fk_transactions_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE SET NULL
);

-- Tax fortress
CREATE TABLE IF NOT EXISTS tax_reserves (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    business_id VARCHAR(50),
    tax_year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    due_date DATE,
    required_amount DECIMAL(15,2) DEFAULT 0,
    reserved_amount DECIMAL(15,2) DEFAULT 0,
    paid_amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'UNDERFUNDED',
    payment_status VARCHAR(20) DEFAULT 'NOT_DUE',
    federal_portion DECIMAL(15,2) DEFAULT 0,
    state_portion DECIMAL(15,2) DEFAULT 0,
    se_tax_portion DECIMAL(15,2) DEFAULT 0,
    paid_at TIMESTAMPTZ,
    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_tax_reserves_org_year_quarter UNIQUE (org_id, tax_year, quarter),
    CONSTRAINT fk_tax_reserves_business FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS tax_events (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    business_id VARCHAR(50),
    type VARCHAR(20),
    category VARCHAR(100),
    amount DECIMAL(15,2),
    tax_breakdown JSONB,
    reserve_amount DECIMAL(15,2),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_tax_events_business FOREIGN KEY (business_id) REFERENCES businesses(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS scheduled_tax_payments (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    tax_year INTEGER NOT NULL,
    quarter INTEGER NOT NULL,
    due_date DATE NOT NULL,
    scheduled_date DATE,
    federal_amount DECIMAL(15,2) DEFAULT 0,
    state_amount DECIMAL(15,2) DEFAULT 0,
    total_amount DECIMAL(15,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'NOT_DUE',
    paid_date DATE,
    confirmation_number VARCHAR(100),
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT uq_scheduled_tax_payments_org_year_quarter UNIQUE (org_id, tax_year, quarter)
);

-- Alerts and notification preferences
CREATE TABLE IF NOT EXISTS alerts (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    severity VARCHAR(20),
    category VARCHAR(50),
    alert_type VARCHAR(100),
    title VARCHAR(500),
    message TEXT,
    details JSONB DEFAULT '{}',
    status VARCHAR(20) DEFAULT 'NEW',
    fingerprint VARCHAR(64),
    created_at TIMESTAMPTZ DEFAULT NOW(),
    resolved_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS notification_configs (
    org_id VARCHAR(50) PRIMARY KEY,
    email_enabled BOOLEAN DEFAULT true,
    email_addresses TEXT[],
    sms_enabled BOOLEAN DEFAULT true,
    phone_numbers TEXT[],
    mattermost_enabled BOOLEAN DEFAULT true,
    mattermost_webhook_url TEXT,
    omi_enabled BOOLEAN DEFAULT true,
    omi_device_id VARCHAR(100)
);

-- Invoice and collections
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
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_invoices_business FOREIGN KEY (business_id) REFERENCES businesses(id),
    CONSTRAINT fk_invoices_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS payments (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    invoice_id VARCHAR(50) NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_payments_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_payments_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
);

CREATE TABLE IF NOT EXISTS payment_links (
    token VARCHAR(64) PRIMARY KEY,
    invoice_id VARCHAR(50) NOT NULL,
    expires_at TIMESTAMPTZ NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_payment_links_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS dunning_events (
    id VARCHAR(50) PRIMARY KEY,
    invoice_id VARCHAR(50) NOT NULL,
    customer_id VARCHAR(50) NOT NULL,
    stage VARCHAR(20) NOT NULL,
    channel VARCHAR(20) NOT NULL,
    sent_at TIMESTAMPTZ NOT NULL,

    CONSTRAINT fk_dunning_invoice FOREIGN KEY (invoice_id) REFERENCES invoices(id) ON DELETE CASCADE,
    CONSTRAINT fk_dunning_customer FOREIGN KEY (customer_id) REFERENCES customers(id)
);

-- Contractor and payroll
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

CREATE TABLE IF NOT EXISTS contracts (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_contracts_contractor FOREIGN KEY (contractor_id) REFERENCES contractors(id)
);

CREATE TABLE IF NOT EXISTS time_entries (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL,
    contract_id VARCHAR(50) NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_time_entries_contractor FOREIGN KEY (contractor_id) REFERENCES contractors(id),
    CONSTRAINT fk_time_entries_contract FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

CREATE TABLE IF NOT EXISTS milestones (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL,
    contract_id VARCHAR(50) NOT NULL,
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_milestones_contractor FOREIGN KEY (contractor_id) REFERENCES contractors(id),
    CONSTRAINT fk_milestones_contract FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

CREATE TABLE IF NOT EXISTS contractor_payments (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL,
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
    updated_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_contractor_payments_contractor FOREIGN KEY (contractor_id) REFERENCES contractors(id),
    CONSTRAINT fk_contractor_payments_contract FOREIGN KEY (contract_id) REFERENCES contracts(id)
);

CREATE TABLE IF NOT EXISTS form_1099_nec (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50) NOT NULL,
    contractor_id VARCHAR(50) NOT NULL,
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

    CONSTRAINT uq_1099_org_contractor_year UNIQUE (org_id, contractor_id, tax_year),
    CONSTRAINT fk_1099_contractor FOREIGN KEY (contractor_id) REFERENCES contractors(id)
);

-- Expense intelligence
CREATE TABLE IF NOT EXISTS vendors (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50),
    name VARCHAR(255),
    normalized_name VARCHAR(255),
    category VARCHAR(50),
    is_subscription BOOLEAN DEFAULT false,
    total_spent DECIMAL(15,2) DEFAULT 0,
    transaction_count INTEGER DEFAULT 0,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS budgets (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50),
    name VARCHAR(255),
    category VARCHAR(50),
    department VARCHAR(100),
    amount DECIMAL(15,2),
    spent DECIMAL(15,2) DEFAULT 0,
    remaining DECIMAL(15,2) DEFAULT 0,
    percentage_used DECIMAL(5,2) DEFAULT 0,
    status VARCHAR(20) DEFAULT 'ON_TRACK',
    alert_threshold INTEGER DEFAULT 80,
    period_start DATE,
    period_end DATE,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS expenses (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50),
    date DATE,
    amount DECIMAL(15,2),
    description TEXT,
    category VARCHAR(50),
    vendor_id VARCHAR(50),
    vendor_name VARCHAR(255),
    department VARCHAR(100),
    tax_deductible BOOLEAN DEFAULT true,
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_expenses_vendor FOREIGN KEY (vendor_id) REFERENCES vendors(id) ON DELETE SET NULL
);

-- Customer intelligence
CREATE TABLE IF NOT EXISTS customer_events (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50),
    customer_id VARCHAR(50),
    event_type VARCHAR(100),
    event_data JSONB DEFAULT '{}',
    occurred_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_customer_events_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS mrr_changes (
    id VARCHAR(50) PRIMARY KEY,
    org_id VARCHAR(50),
    customer_id VARCHAR(50),
    old_mrr DECIMAL(15,2),
    new_mrr DECIMAL(15,2),
    change_type VARCHAR(20),
    changed_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_mrr_changes_customer FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
);

-- Bank reconciliation
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_bank_transactions_account FOREIGN KEY (account_id) REFERENCES bank_accounts(id) ON DELETE CASCADE
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_internal_transactions_account FOREIGN KEY (expected_account_id) REFERENCES bank_accounts(id) ON DELETE SET NULL
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_matches_bank_tx FOREIGN KEY (bank_transaction_id) REFERENCES bank_transactions(id) ON DELETE CASCADE,
    CONSTRAINT fk_matches_internal_tx FOREIGN KEY (internal_transaction_id) REFERENCES internal_transactions(id) ON DELETE CASCADE
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_discrepancies_account FOREIGN KEY (account_id) REFERENCES bank_accounts(id) ON DELETE SET NULL,
    CONSTRAINT fk_discrepancies_bank_tx FOREIGN KEY (bank_transaction_id) REFERENCES bank_transactions(id) ON DELETE SET NULL,
    CONSTRAINT fk_discrepancies_internal_tx FOREIGN KEY (internal_transaction_id) REFERENCES internal_transactions(id) ON DELETE SET NULL
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_reconciliation_runs_account FOREIGN KEY (account_id) REFERENCES bank_accounts(id) ON DELETE CASCADE
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
    created_at TIMESTAMPTZ DEFAULT NOW(),

    CONSTRAINT fk_stripe_payouts_bank_tx FOREIGN KEY (bank_transaction_id) REFERENCES bank_transactions(id) ON DELETE SET NULL
);

-- Indexes
CREATE INDEX IF NOT EXISTS idx_bank_accounts_org ON bank_accounts(org_id);
CREATE INDEX IF NOT EXISTS idx_bank_accounts_status ON bank_accounts(status);

CREATE INDEX IF NOT EXISTS idx_transactions_org_created ON transactions(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_transactions_type ON transactions(transaction_type);

CREATE INDEX IF NOT EXISTS idx_tax_reserves_org_year ON tax_reserves(org_id, tax_year);
CREATE INDEX IF NOT EXISTS idx_tax_events_org_created ON tax_events(org_id, created_at);

CREATE INDEX IF NOT EXISTS idx_alerts_org_status ON alerts(org_id, status);

CREATE INDEX IF NOT EXISTS idx_invoices_org ON invoices(org_id);
CREATE INDEX IF NOT EXISTS idx_invoices_customer ON invoices(customer_id);
CREATE INDEX IF NOT EXISTS idx_invoices_status ON invoices(status);
CREATE INDEX IF NOT EXISTS idx_invoices_due_date ON invoices(due_date);
CREATE INDEX IF NOT EXISTS idx_invoices_stripe_invoice_id ON invoices(stripe_invoice_id);

CREATE INDEX IF NOT EXISTS idx_payments_invoice ON payments(invoice_id);
CREATE INDEX IF NOT EXISTS idx_payments_org ON payments(org_id);

CREATE INDEX IF NOT EXISTS idx_dunning_invoice ON dunning_events(invoice_id);

CREATE INDEX IF NOT EXISTS idx_contractors_org ON contractors(org_id);
CREATE INDEX IF NOT EXISTS idx_contractors_status ON contractors(status);
CREATE INDEX IF NOT EXISTS idx_contracts_contractor ON contracts(contractor_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_contractor ON time_entries(contractor_id);
CREATE INDEX IF NOT EXISTS idx_time_entries_status ON time_entries(status);
CREATE INDEX IF NOT EXISTS idx_contractor_payments_contractor ON contractor_payments(contractor_id);
CREATE INDEX IF NOT EXISTS idx_contractor_payments_status ON contractor_payments(status);

CREATE INDEX IF NOT EXISTS idx_vendors_org ON vendors(org_id);
CREATE INDEX IF NOT EXISTS idx_expenses_org_date ON expenses(org_id, date);
CREATE INDEX IF NOT EXISTS idx_budgets_org ON budgets(org_id);

CREATE INDEX IF NOT EXISTS idx_customer_events_customer ON customer_events(customer_id, occurred_at);
CREATE INDEX IF NOT EXISTS idx_customers_org_status ON customers(org_id, status);
CREATE INDEX IF NOT EXISTS idx_customers_health ON customers(org_id, health_score);
CREATE INDEX IF NOT EXISTS idx_customers_acquired ON customers(org_id, acquired_at);
CREATE INDEX IF NOT EXISTS idx_mrr_changes_org_changed ON mrr_changes(org_id, changed_at);

CREATE INDEX IF NOT EXISTS idx_bank_transactions_account_date ON bank_transactions(account_id, date);
CREATE INDEX IF NOT EXISTS idx_bank_transactions_match ON bank_transactions(match_status);
CREATE INDEX IF NOT EXISTS idx_internal_transactions_org_date ON internal_transactions(org_id, date);
CREATE INDEX IF NOT EXISTS idx_transaction_matches_org ON transaction_matches(org_id);
CREATE INDEX IF NOT EXISTS idx_discrepancies_org_status ON discrepancies(org_id, status);
CREATE INDEX IF NOT EXISTS idx_reconciliation_runs_org_created ON reconciliation_runs(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_reconciliation_audit_org_created ON reconciliation_audit(org_id, created_at);
CREATE INDEX IF NOT EXISTS idx_stripe_payouts_org_arrival ON stripe_payouts(org_id, arrival_date);
