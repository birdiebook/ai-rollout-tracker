-- max_gb: 5
-- Smoke test for keyless BigQuery auth: one day of PyPI downloads for one package (aggregate count only).
SELECT DATE(timestamp) AS day, file.project AS project, COUNT(*) AS downloads
FROM `bigquery-public-data.pypi.file_downloads`
WHERE DATE(timestamp) = '2026-11-01' AND file.project = 'anthropic'
GROUP BY day, project
