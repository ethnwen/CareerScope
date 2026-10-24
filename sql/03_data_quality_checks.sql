-- CareerScope: data-quality and reconciliation checks run inside SQL Server.
-- Each check compares a SQL result with a figure verified earlier in Python
-- (docs/findings.md and docs/validation_report.txt). Read-only.
USE CareerScope;
GO

DROP TABLE IF EXISTS #checks;
CREATE TABLE #checks (
    check_id   INT IDENTITY(1, 1) PRIMARY KEY,
    area       VARCHAR(20)    NOT NULL,
    check_name NVARCHAR(160)  NOT NULL,
    expected   DECIMAL(18, 2) NOT NULL,
    actual     DECIMAL(18, 2) NULL,
    status AS (CASE WHEN actual = expected THEN 'PASS' ELSE 'FAIL' END)
);
GO

-- 1. Structure: periods and the 2020 gap (window function over dates)
INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'structure', N'Quarters in dim.period', 44, COUNT(*)
FROM dim.period WHERE period_type = 'quarter'
UNION ALL
SELECT 'structure', N'Years in dim.period', 29, COUNT(*)
FROM dim.period WHERE period_type = 'year';
GO

WITH q AS (
    SELECT period_start,
           LAG(period_start) OVER (ORDER BY period_start) AS previous_start
    FROM dim.period
    WHERE period_type = 'quarter')
INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'structure', N'Gaps between consecutive quarters (Q2 and Q3 2020 are missing)', 1,
       SUM(CASE WHEN DATEDIFF(MONTH, previous_start, period_start) > 3 THEN 1 ELSE 0 END)
FROM q;
GO

-- 2. Coverage and quality counts (0444)
INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'coverage', N'0444 offered wage values in 2026-04', 22440, COUNT(*)
FROM fact.offered_wage_0444 AS w
JOIN dim.period AS p ON p.period_id = w.period_id
WHERE p.period_type = 'quarter' AND p.period_start = '2026-04-01'
UNION ALL
SELECT 'coverage', N'0444 vacancy values in 2026-04', 12317, COUNT(*)
FROM fact.vacancy_0444 AS v
JOIN dim.period AS p ON p.period_id = v.period_id
WHERE p.period_type = 'quarter' AND p.period_start = '2026-04-01'
UNION ALL
SELECT 'coverage', N'0444 vacancy values in 2015-01 (excluded from trends)', 277, COUNT(*)
FROM fact.vacancy_0444 AS v
JOIN dim.period AS p ON p.period_id = v.period_id
WHERE p.period_type = 'quarter' AND p.period_start = '2015-01-01'
UNION ALL
SELECT 'coverage', N'0444 offered wage values graded A', 329966, COUNT(*)
FROM fact.offered_wage_0444 WHERE quality_grade = 'A'
UNION ALL
SELECT 'coverage', N'0444 vacancy values graded E', 203260, COUNT(*)
FROM fact.vacancy_0444 WHERE quality_grade = 'E'
UNION ALL
SELECT 'coverage', N'0444 true zero vacancy counts', 6578, COUNT(*)
FROM fact.vacancy_0444 WHERE vacancies = 0;
GO

-- 3. Reconciliation with the Python figures (joins on dimensions, no hard-coded IDs)
DECLARE @canada SMALLINT = (SELECT geo_id FROM dim.geography WHERE geo_level = 'Canada');
DECLARE @total_occ SMALLINT = (SELECT noc_id FROM dim.occupation WHERE is_total = 1);
DECLARE @alberta SMALLINT = (SELECT geo_id FROM dim.geography
                             WHERE geo_name = 'Alberta' AND geo_level = 'Province/territory');

INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'reconcile', N'Canada total vacancies, 2026-04', 548400, v.vacancies
FROM fact.vacancy_0444 AS v
JOIN dim.period AS p ON p.period_id = v.period_id
WHERE v.geo_id = @canada AND v.noc_id = @total_occ
  AND p.period_type = 'quarter' AND p.period_start = '2026-04-01'
UNION ALL
SELECT 'reconcile', N'Canada total offered wage, 2026-04', 28.55, w.offered_wage
FROM fact.offered_wage_0444 AS w
JOIN dim.period AS p ON p.period_id = w.period_id
WHERE w.geo_id = @canada AND w.noc_id = @total_occ
  AND p.period_type = 'quarter' AND p.period_start = '2026-04-01'
UNION ALL
SELECT 'reconcile', N'Canada total offered wage, 2015-04 (first trend quarter)', 18.70, w.offered_wage
FROM fact.offered_wage_0444 AS w
JOIN dim.period AS p ON p.period_id = w.period_id
WHERE w.geo_id = @canada AND w.noc_id = @total_occ
  AND p.period_type = 'quarter' AND p.period_start = '2015-04-01'
UNION ALL
SELECT 'reconcile', N'Peak Canada total vacancies (2022-04)', 1032215, MAX(v.vacancies)
FROM fact.vacancy_0444 AS v
WHERE v.geo_id = @canada AND v.noc_id = @total_occ
UNION ALL
SELECT 'reconcile', N'Lowest Canada total vacancies after the 2022-04 peak (2025-10)', 469840, MIN(v.vacancies)
FROM fact.vacancy_0444 AS v
JOIN dim.period AS p ON p.period_id = v.period_id
WHERE v.geo_id = @canada AND v.noc_id = @total_occ
  AND p.period_type = 'quarter' AND p.period_start > '2022-04-01'
UNION ALL
SELECT 'reconcile', N'0417 Canada average hourly wage, 2025, all occupations', 36.40, e.hourly_wage
FROM fact.employee_wage_0417 AS e
JOIN dim.period AS p ON p.period_id = e.period_id
WHERE e.geo_id = @canada AND e.noc417_code = '00-95' AND e.type_of_work = 'all'
  AND e.measure_key = 'employee_wage_avg_hourly' AND p.period_type = 'year' AND p.period_year = 2025
UNION ALL
SELECT 'reconcile', N'0417 Alberta average hourly wage, 1997', 14.80, e.hourly_wage
FROM fact.employee_wage_0417 AS e
JOIN dim.period AS p ON p.period_id = e.period_id
WHERE e.geo_id = @alberta AND e.noc417_code = '00-95' AND e.type_of_work = 'all'
  AND e.measure_key = 'employee_wage_avg_hourly' AND p.period_type = 'year' AND p.period_year = 1997
UNION ALL
SELECT 'reconcile', N'0417 Alberta average hourly wage, 2025', 37.35, e.hourly_wage
FROM fact.employee_wage_0417 AS e
JOIN dim.period AS p ON p.period_id = e.period_id
WHERE e.geo_id = @alberta AND e.noc417_code = '00-95' AND e.type_of_work = 'all'
  AND e.measure_key = 'employee_wage_avg_hourly' AND p.period_type = 'year' AND p.period_year = 2025
UNION ALL
SELECT 'reconcile', N'0443 education shares sum to 100 (Canada, all occupations, 2026-04)', 100.00, CAST(SUM(s.vacancy_share) AS DECIMAL(18, 2))
FROM fact.char_vacancy_share_0443 AS s
JOIN dim.period AS p ON p.period_id = s.period_id
WHERE s.geo_id = @canada AND s.noc_id = @total_occ AND s.char_id IN (5, 6, 7, 10, 12, 13)
  AND p.period_type = 'quarter' AND p.period_start = '2026-04-01';

-- 4. Cross-table consistency: 0444 and 0443 must agree on all-occupation totals
INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'cross-table', N'0444 vs 0443 vacancy pairs compared', 611, COUNT(*)
FROM fact.vacancy_0444 AS a
JOIN fact.char_vacancy_0443 AS b
  ON b.period_id = a.period_id AND b.geo_id = a.geo_id AND b.noc_id = a.noc_id AND b.char_id = 1
WHERE a.noc_id = @total_occ AND a.geo_id <= 14
UNION ALL
SELECT 'cross-table', N'0444 vs 0443 vacancy pairs that differ by more than 5', 0, COUNT(*)
FROM fact.vacancy_0444 AS a
JOIN fact.char_vacancy_0443 AS b
  ON b.period_id = a.period_id AND b.geo_id = a.geo_id AND b.noc_id = a.noc_id AND b.char_id = 1
WHERE a.noc_id = @total_occ AND a.geo_id <= 14 AND ABS(a.vacancies - b.vacancies) > 5
UNION ALL
SELECT 'cross-table', N'0444 vs 0443 wage pairs compared', 616, COUNT(*)
FROM fact.offered_wage_0444 AS a
JOIN fact.char_offered_wage_0443 AS b
  ON b.period_id = a.period_id AND b.geo_id = a.geo_id AND b.noc_id = a.noc_id AND b.char_id = 1
WHERE a.noc_id = @total_occ AND a.geo_id <= 14
UNION ALL
SELECT 'cross-table', N'0444 vs 0443 wage pairs that differ by more than 0.05', 0, COUNT(*)
FROM fact.offered_wage_0444 AS a
JOIN fact.char_offered_wage_0443 AS b
  ON b.period_id = a.period_id AND b.geo_id = a.geo_id AND b.noc_id = a.noc_id AND b.char_id = 1
WHERE a.noc_id = @total_occ AND a.geo_id <= 14 AND ABS(a.offered_wage - b.offered_wage) > 0.05;
GO

-- 5. Hierarchy: published children must not exceed their parent beyond rounding (CTE)
WITH child_totals AS (
    SELECT v.period_id, v.geo_id, o.parent_noc_id AS noc_id,
           SUM(CAST(v.vacancies AS BIGINT)) AS child_total, COUNT(*) AS n_children
    FROM fact.vacancy_0444 AS v
    JOIN dim.occupation AS o ON o.noc_id = v.noc_id
    WHERE o.parent_noc_id IS NOT NULL
    GROUP BY v.period_id, v.geo_id, o.parent_noc_id)
INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'hierarchy', N'Parent cells tested (vacancies by occupation level)', 264533, COUNT(*)
FROM child_totals AS c
JOIN fact.vacancy_0444 AS p
  ON p.period_id = c.period_id AND p.geo_id = c.geo_id AND p.noc_id = c.noc_id
UNION ALL
SELECT 'hierarchy', N'Parent cells where children exceed the parent beyond rounding', 0,
       SUM(CASE WHEN c.child_total - p.vacancies > 5 * (c.n_children + 1) THEN 1 ELSE 0 END)
FROM child_totals AS c
JOIN fact.vacancy_0444 AS p
  ON p.period_id = c.period_id AND p.geo_id = c.geo_id AND p.noc_id = c.noc_id;
GO

-- 6. Suspect-value flags
INSERT INTO #checks (area, check_name, expected, actual)
SELECT 'flags', N'Flagged suspect wages in 0443', 17, COUNT(*)
FROM fact.char_offered_wage_0443 WHERE is_suspect = 1
UNION ALL
SELECT 'flags', N'Flagged suspect wages in 0444', 0, COUNT(*)
FROM fact.offered_wage_0444 WHERE is_suspect = 1
UNION ALL
SELECT 'flags', N'Flagged suspect wages in 0417', 0, COUNT(*)
FROM fact.employee_wage_0417 WHERE is_suspect = 1;
GO

SELECT check_id, area, check_name, expected, actual, status FROM #checks ORDER BY check_id;

SELECT SUM(CASE WHEN status = 'PASS' THEN 1 ELSE 0 END) AS passed,
       SUM(CASE WHEN status = 'FAIL' THEN 1 ELSE 0 END) AS failed
FROM #checks;
GO
