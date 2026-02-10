SELECT service_name, status, checked_at
FROM service_health
ORDER BY checked_at DESC
LIMIT 100;
