# Listmonk Templates

All templates include HTML + inline CSS + responsive layout + plain-text fallback and support merge vars.

- invoice-delivery: {client_name}, {invoice_number}, {amount}, {download_link}, {payment_instructions}
- booking-confirmation: {client_name}, {event_type}, {datetime}, {meeting_link}, {prep_notes}
- welcome-client: {client_name}, {portal_url}, {first_steps}, {contact_info}
- password-reset: {reset_link}, {expiry}
- payment-received: {client_name}, {amount}, {invoice_number}, {receipt_link}
- invoice-overdue-reminder (gentle|firm|final): {client_name}, {invoice_number}, {amount}, {days_overdue}, {tone}
- backup-alert: {service}, {error}, {timestamp}
- daily-digest: {date}, {tasks_completed}, {revenue}, {alerts}, {pipeline_stats}
