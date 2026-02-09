# Business APIs Reference

## Financial Suite Overview

The Omni Quantum Elite financial suite consists of four microservices providing accounts management, invoicing, analytics, and customer relationship management. All services follow consistent conventions:

- **Authentication**: Bearer token via `Authorization: Bearer {token}` header
- **Content-Type**: `application/json`
- **Pagination**: `?page=1&per_page=20` query parameters
- **Filtering**: Field-based query parameters (e.g., `?status=active`)
- **Error format**: `{"error": {"code": "NOT_FOUND", "message": "..."}}`

---

## Financial — Accounts (System 26)

**Container**: `omni-accounts` | **Port**: 8701 | **Tier**: Business

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/accounts` | List accounts |
| POST | `/api/v1/accounts` | Create account |
| GET | `/api/v1/accounts/{id}` | Get account detail |
| PUT | `/api/v1/accounts/{id}` | Update account |
| DELETE | `/api/v1/accounts/{id}` | Archive account |
| GET | `/api/v1/accounts/{id}/transactions` | List account transactions |
| POST | `/api/v1/accounts/{id}/transactions` | Create transaction |
| GET | `/api/v1/accounts/{id}/balance` | Get current balance |
| GET | `/api/v1/chart-of-accounts` | Full chart of accounts |
| POST | `/api/v1/journal-entries` | Create journal entry |
| GET | `/api/v1/journal-entries` | List journal entries |
| GET | `/api/v1/reports/trial-balance` | Trial balance report |
| GET | `/api/v1/reports/balance-sheet` | Balance sheet |
| GET | `/api/v1/reports/income-statement` | Income statement |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Example: Create Account
```bash
curl -X POST http://omni-accounts:8701/api/v1/accounts \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Consulting Revenue",
    "type": "revenue",
    "code": "4010",
    "currency": "USD",
    "description": "Revenue from consulting engagements"
  }'
```

### Example: Create Journal Entry
```bash
curl -X POST http://omni-accounts:8701/api/v1/journal-entries \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "date": "2025-01-15",
    "description": "Client payment received",
    "entries": [
      {"account_id": "acc_001", "debit": 5000.00, "credit": 0},
      {"account_id": "acc_002", "debit": 0, "credit": 5000.00}
    ]
  }'
```

---

## Financial — Invoicing (System 27)

**Container**: `omni-invoicing` | **Port**: 8702 | **Tier**: Business

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/invoices` | List invoices |
| POST | `/api/v1/invoices` | Create invoice |
| GET | `/api/v1/invoices/{id}` | Get invoice detail |
| PUT | `/api/v1/invoices/{id}` | Update invoice |
| POST | `/api/v1/invoices/{id}/send` | Send invoice to client |
| POST | `/api/v1/invoices/{id}/mark-paid` | Mark invoice as paid |
| POST | `/api/v1/invoices/{id}/void` | Void an invoice |
| GET | `/api/v1/invoices/{id}/pdf` | Download invoice PDF |
| GET | `/api/v1/recurring` | List recurring invoices |
| POST | `/api/v1/recurring` | Create recurring invoice |
| GET | `/api/v1/payments` | List payments |
| POST | `/api/v1/payments` | Record payment |
| GET | `/api/v1/reports/aging` | Accounts receivable aging |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Example: Create Invoice
```bash
curl -X POST http://omni-invoicing:8702/api/v1/invoices \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "client_id": "cli_001",
    "due_date": "2025-02-15",
    "currency": "USD",
    "line_items": [
      {
        "description": "AI Coding System Setup — Phase 1",
        "quantity": 1,
        "unit_price": 15000.00,
        "tax_rate": 0.0
      },
      {
        "description": "Monthly platform hosting (January)",
        "quantity": 1,
        "unit_price": 2500.00,
        "tax_rate": 0.0
      }
    ],
    "notes": "Payment terms: Net 30"
  }'
```

### Invoice States
```
draft → sent → viewed → partial → paid
                 ↘ overdue ↗
draft → voided
```

---

## Financial — Analytics (System 28)

**Container**: `omni-analytics` | **Port**: 8703 | **Tier**: Business

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/dashboard` | Executive dashboard summary |
| GET | `/api/v1/revenue` | Revenue over time |
| GET | `/api/v1/revenue/by-client` | Revenue breakdown by client |
| GET | `/api/v1/revenue/by-service` | Revenue breakdown by service |
| GET | `/api/v1/expenses` | Expense tracking |
| GET | `/api/v1/expenses/by-category` | Expense breakdown by category |
| GET | `/api/v1/profit-loss` | Profit & loss statement |
| GET | `/api/v1/cash-flow` | Cash flow analysis |
| GET | `/api/v1/kpis` | Key performance indicators |
| GET | `/api/v1/forecasts` | Revenue/expense forecasts |
| POST | `/api/v1/reports/custom` | Generate custom report |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Query Parameters (common)
| Parameter | Type | Description |
|-----------|------|-------------|
| `start_date` | string | Period start (YYYY-MM-DD) |
| `end_date` | string | Period end (YYYY-MM-DD) |
| `granularity` | string | `daily`, `weekly`, `monthly`, `quarterly` |
| `currency` | string | Currency code (default: USD) |

### Example: Revenue by Client
```bash
curl "http://omni-analytics:8703/api/v1/revenue/by-client?start_date=2025-01-01&end_date=2025-03-31&granularity=monthly" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Example: KPIs
```bash
curl http://omni-analytics:8703/api/v1/kpis \
  -H "Authorization: Bearer ${TOKEN}"
```

### KPI Response
```json
{
  "period": "2025-Q1",
  "mrr": 45000.00,
  "arr": 540000.00,
  "churn_rate": 0.02,
  "ltv": 120000.00,
  "cac": 5000.00,
  "gross_margin": 0.78,
  "net_revenue_retention": 1.15,
  "outstanding_receivables": 32000.00,
  "avg_days_to_pay": 28
}
```

---

## Financial — CRM (System 29)

**Container**: `omni-crm` | **Port**: 8704 | **Tier**: Business

### Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/v1/clients` | List clients |
| POST | `/api/v1/clients` | Create client |
| GET | `/api/v1/clients/{id}` | Get client detail |
| PUT | `/api/v1/clients/{id}` | Update client |
| DELETE | `/api/v1/clients/{id}` | Archive client |
| GET | `/api/v1/clients/{id}/contacts` | List client contacts |
| POST | `/api/v1/clients/{id}/contacts` | Add contact |
| GET | `/api/v1/clients/{id}/projects` | List client projects |
| POST | `/api/v1/projects` | Create project |
| GET | `/api/v1/projects/{id}` | Get project detail |
| PUT | `/api/v1/projects/{id}` | Update project |
| GET | `/api/v1/projects/{id}/tasks` | List project tasks |
| POST | `/api/v1/projects/{id}/tasks` | Create task |
| GET | `/api/v1/pipeline` | Sales pipeline overview |
| POST | `/api/v1/pipeline/opportunities` | Create opportunity |
| GET | `/api/v1/activities` | Activity log |
| POST | `/api/v1/activities` | Log activity |
| GET | `/health` | Health check |
| GET | `/metrics` | Prometheus metrics |

### Example: Create Client
```bash
curl -X POST http://omni-crm:8704/api/v1/clients \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Acme Corp",
    "industry": "Technology",
    "website": "https://acme.example.com",
    "billing_email": "billing@acme.example.com",
    "currency": "USD",
    "payment_terms_days": 30,
    "tags": ["enterprise", "ai-platform"]
  }'
```

### Example: Sales Pipeline
```bash
curl http://omni-crm:8704/api/v1/pipeline \
  -H "Authorization: Bearer ${TOKEN}"
```

### Pipeline Response
```json
{
  "stages": [
    {"name": "Lead", "count": 12, "value": 180000.00},
    {"name": "Qualified", "count": 8, "value": 240000.00},
    {"name": "Proposal", "count": 5, "value": 175000.00},
    {"name": "Negotiation", "count": 3, "value": 120000.00},
    {"name": "Closed Won", "count": 15, "value": 450000.00}
  ],
  "total_pipeline_value": 715000.00,
  "weighted_value": 382500.00,
  "avg_deal_size": 35000.00,
  "avg_close_days": 45
}
```

---

## Cross-Service Integration

### Accounts ↔ Invoicing
When an invoice is marked as paid, the Invoicing service posts a journal entry to Accounts automatically via internal webhook.

### CRM ↔ Invoicing
Creating an invoice from a CRM project pre-fills client details and line items from the project scope.

### Analytics ← All
Analytics aggregates data from Accounts, Invoicing, and CRM via periodic sync (every 15 minutes).

### Webhook Events
All financial services emit webhook events to Integration Hub (`omni-integration-hub:8900`):

| Event | Source | Description |
|-------|--------|-------------|
| `invoice.created` | Invoicing | New invoice created |
| `invoice.paid` | Invoicing | Invoice marked paid |
| `payment.received` | Invoicing | Payment recorded |
| `client.created` | CRM | New client added |
| `project.status_changed` | CRM | Project status updated |
| `account.transaction` | Accounts | New transaction posted |

---

*Last updated: 2025-01-01 | All business APIs require authentication and return JSON responses.*
