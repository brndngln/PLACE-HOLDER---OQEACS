SELECT pipeline, status, AVG(duration_seconds) AS avg_duration, COUNT(*) AS runs
FROM pipeline_runs
WHERE created_at > NOW() - INTERVAL '7 days'
GROUP BY pipeline, status
ORDER BY runs DESC;
