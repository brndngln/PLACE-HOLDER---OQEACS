-- OMNI QUANTUM ELITE v3.0 - DATABASE SCHEMA
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE organizations (id VARCHAR(50) PRIMARY KEY, name VARCHAR(255), status VARCHAR(20) DEFAULT 'ACTIVE', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE businesses (id VARCHAR(50) PRIMARY KEY, parent_id VARCHAR(50), name VARCHAR(255), status VARCHAR(20) DEFAULT 'ACTIVE', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE bank_accounts (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), account_name VARCHAR(255), provider VARCHAR(50), account_type VARCHAR(50), cached_balance DECIMAL(15,2) DEFAULT 0, status VARCHAR(20) DEFAULT 'active', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE transactions (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), business_id VARCHAR(50), transaction_type VARCHAR(20), category VARCHAR(100), amount DECIMAL(15,2), created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE tax_reserves (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), business_id VARCHAR(50), tax_year INTEGER, quarter INTEGER, due_date DATE, required_amount DECIMAL(15,2) DEFAULT 0, reserved_amount DECIMAL(15,2) DEFAULT 0, paid_amount DECIMAL(15,2) DEFAULT 0, status VARCHAR(20) DEFAULT 'UNDERFUNDED', payment_status VARCHAR(20) DEFAULT 'NOT_DUE', federal_portion DECIMAL(15,2) DEFAULT 0, state_portion DECIMAL(15,2) DEFAULT 0, se_tax_portion DECIMAL(15,2) DEFAULT 0, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE tax_events (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), business_id VARCHAR(50), type VARCHAR(20), category VARCHAR(100), amount DECIMAL(15,2), tax_breakdown JSONB, reserve_amount DECIMAL(15,2), created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE transfers (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), mode VARCHAR(20), status VARCHAR(20), from_account_id VARCHAR(50), destinations JSONB, amount DECIMAL(15,2), created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE recurring_rules (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), name VARCHAR(255), status VARCHAR(20) DEFAULT 'DISABLED', destinations JSONB, next_run_at TIMESTAMPTZ, created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE alerts (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), severity VARCHAR(20), category VARCHAR(50), alert_type VARCHAR(100), title VARCHAR(500), message TEXT, details JSONB DEFAULT '{}', status VARCHAR(20) DEFAULT 'NEW', fingerprint VARCHAR(64), created_at TIMESTAMPTZ DEFAULT NOW(), resolved_at TIMESTAMPTZ);
CREATE TABLE notification_configs (org_id VARCHAR(50) PRIMARY KEY, email_enabled BOOLEAN DEFAULT true, email_addresses TEXT[], sms_enabled BOOLEAN DEFAULT true, phone_numbers TEXT[], mattermost_enabled BOOLEAN DEFAULT true, mattermost_webhook_url TEXT, omi_enabled BOOLEAN DEFAULT true, omi_device_id VARCHAR(100));
CREATE TABLE customers (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), business_id VARCHAR(50), name VARCHAR(255), status VARCHAR(20) DEFAULT 'ACTIVE', created_at TIMESTAMPTZ DEFAULT NOW());
CREATE TABLE subscriptions (id VARCHAR(50) PRIMARY KEY, org_id VARCHAR(50), business_id VARCHAR(50), customer_id VARCHAR(50), mrr DECIMAL(15,2) DEFAULT 0, status VARCHAR(20) DEFAULT 'ACTIVE', created_at TIMESTAMPTZ DEFAULT NOW());

-- Sample data
INSERT INTO organizations VALUES ('ORG-001', 'My AI Empire');
INSERT INTO businesses VALUES ('BIZ-001', 'ORG-001', 'AI SaaS Tool'), ('BIZ-002', 'ORG-001', 'AI API Service');
INSERT INTO bank_accounts VALUES ('ACC-001', 'ORG-001', 'Mercury', 'Mercury', 'business_checking', 50000), ('ACC-002', 'ORG-001', 'Wells Fargo', 'Wells Fargo', 'personal_checking', 10000);
INSERT INTO notification_configs VALUES ('ORG-001', true, ARRAY['owner@example.com'], true, ARRAY['+15551234567'], true, '', true, '');
