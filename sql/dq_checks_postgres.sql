-- Data-quality checks for routine facility reports (PostgreSQL)
-- Expects a table: facility_reports(district text, facility_id text, period date,
--   anc1_visits int, deliveries int, malaria_tested int, malaria_positive int,
--   submitted_at timestamp, deadline timestamp)
-- `period` is the first day of the reporting month.

-- 1. Completeness: expected facility-months with no report
WITH facilities AS (SELECT DISTINCT district, facility_id FROM facility_reports),
periods AS (SELECT DISTINCT period FROM facility_reports),
expected AS (SELECT f.district, f.facility_id, p.period FROM facilities f CROSS JOIN periods p)
SELECT e.district, e.facility_id, e.period, 'completeness' AS check_name, 'report missing' AS detail
FROM expected e
LEFT JOIN facility_reports r USING (facility_id, period)
WHERE r.facility_id IS NULL

UNION ALL
-- 2. Timeliness: submitted after the deadline
SELECT district, facility_id, period, 'timeliness',
       EXTRACT(DAY FROM submitted_at - deadline)::int || ' days late'
FROM facility_reports
WHERE submitted_at > deadline

UNION ALL
-- 3. Internal consistency rules
SELECT district, facility_id, period, 'consistency', 'malaria_positive > malaria_tested'
FROM facility_reports
WHERE malaria_positive > malaria_tested

UNION ALL
-- 4. Zero reporting: every indicator is 0
SELECT district, facility_id, period, 'zero_report', 'all indicators reported as 0'
FROM facility_reports
WHERE COALESCE(anc1_visits,0) = 0 AND COALESCE(deliveries,0) = 0
  AND COALESCE(malaria_tested,0) = 0 AND COALESCE(malaria_positive,0) = 0

UNION ALL
-- 5. Outliers (modified z-score on anc1_visits, per facility)
SELECT district, facility_id, period, 'outlier',
       'anc1_visits: modified z=' || ROUND(mz::numeric, 1)
FROM (
  SELECT r.*, 0.6745 * (r.anc1_visits - s.med) / NULLIF(s.mad, 0) AS mz
  FROM facility_reports r
  JOIN (
    SELECT m.facility_id, m.med,
           percentile_cont(0.5) WITHIN GROUP (ORDER BY ABS(r2.anc1_visits - m.med)) AS mad
    FROM (SELECT facility_id,
                 percentile_cont(0.5) WITHIN GROUP (ORDER BY anc1_visits) AS med
          FROM facility_reports GROUP BY facility_id) m
    JOIN facility_reports r2 USING (facility_id)
    GROUP BY m.facility_id, m.med
  ) s USING (facility_id)
) z
WHERE ABS(mz) > 3.5;
