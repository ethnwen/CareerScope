USE CareerScope;
GO
SELECT s.name + '.' + t.name AS table_name, SUM(p.row_count) AS row_count
FROM sys.dm_db_partition_stats AS p
JOIN sys.tables AS t ON t.object_id = p.object_id
JOIN sys.schemas AS s ON s.schema_id = t.schema_id
WHERE p.index_id IN (0, 1)
GROUP BY s.name, t.name
ORDER BY s.name, t.name;
GO