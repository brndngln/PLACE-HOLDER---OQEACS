SELECT timestamp, actor_id, action, resource_type, resource_id
FROM audit_events
WHERE timestamp > NOW() - INTERVAL '24 hours'
ORDER BY timestamp DESC;
