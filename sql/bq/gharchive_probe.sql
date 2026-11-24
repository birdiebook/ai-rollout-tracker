-- max_gb: 0.001
-- Cost probe only (track B2): the cap is set so the workflow refuses after the dry run and logs the estimate.
-- One day of GH Archive with the columns the commit-trailer measure needs (type, repo.id, payload). Never meant to run.
SELECT COUNT(*) AS push_events,
       COUNTIF(REGEXP_CONTAINS(payload, r'(?i)co-authored-by:[^\n]*noreply@anthropic\.com')) AS claude_pushes,
       COUNT(DISTINCT repo.id) AS repos
FROM `githubarchive.day.20250901`
WHERE type = 'PushEvent'
