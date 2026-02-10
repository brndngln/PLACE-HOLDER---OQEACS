SELECT collection, COUNT(*) AS entries
FROM knowledge_entries
GROUP BY collection
ORDER BY entries DESC;
