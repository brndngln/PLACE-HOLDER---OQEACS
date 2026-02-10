SELECT status, COUNT(*) AS invoices, SUM(total_amount) AS total_amount
FROM invoices
GROUP BY status
ORDER BY status;
