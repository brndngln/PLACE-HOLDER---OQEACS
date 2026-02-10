SELECT id, client_name, status, quality_score, updated_at
FROM projects
ORDER BY updated_at DESC
LIMIT 100;
