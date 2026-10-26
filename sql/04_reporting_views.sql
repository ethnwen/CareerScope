-- CareerScope: reporting views used by the analytical queries and Power BI.
-- Safe to run more than once (CREATE OR ALTER). Read-only.
-- Reliable = grade A to D (or an exact value with no grade) and not flagged as suspect (D1, D11, D13).
USE CareerScope;
GO

CREATE OR ALTER VIEW rpt.vw_latest_quarter AS
SELECT TOP (1) period_id, period_start, period_label
FROM dim.period
WHERE period_type = 'quarter'
ORDER BY period_start DESC;
GO

-- Vacancies and offered wages side by side. FULL OUTER JOIN keeps cells that have only one of the two.
CREATE OR ALTER VIEW rpt.vw_occupation_geo_period AS
SELECT COALESCE(v.period_id, w.period_id) AS period_id,
       COALESCE(v.geo_id, w.geo_id) AS geo_id,
       COALESCE(v.noc_id, w.noc_id) AS noc_id,
       v.vacancies,
       v.quality_grade AS vacancy_grade,
       w.offered_wage,
       w.quality_grade AS wage_grade,
       w.is_suspect AS wage_is_suspect,
       CASE WHEN v.quality_grade IN ('A', 'B', 'C', 'D', 'NONE') THEN 1 ELSE 0 END AS vacancy_is_reliable,
       CASE WHEN w.quality_grade IN ('A', 'B', 'C', 'D', 'NONE') AND w.is_suspect = 0 THEN 1 ELSE 0 END AS wage_is_reliable
FROM fact.vacancy_0444 AS v
FULL OUTER JOIN fact.offered_wage_0444 AS w
        ON w.period_id = v.period_id AND w.geo_id = v.geo_id AND w.noc_id = v.noc_id;
GO

-- National trend with change versus the same quarter a year earlier (data is not seasonally adjusted).
-- Joining on year and quarter, not on row position, keeps the missing Q2 and Q3 2020 from shifting comparisons.
-- D9: comparisons never use 2015-01 as the earlier quarter.
CREATE OR ALTER VIEW rpt.vw_national_trend AS
WITH base AS (
    SELECT p.period_start, p.period_year, p.period_quarter, p.period_label,
           v.vacancies, v.quality_grade AS vacancy_grade,
           w.offered_wage, w.quality_grade AS wage_grade
    FROM dim.period AS p
    CROSS JOIN (SELECT g.geo_id, o.noc_id
                FROM dim.geography AS g
                CROSS JOIN dim.occupation AS o
                WHERE g.geo_level = 'Canada' AND o.is_total = 1) AS k
    LEFT JOIN fact.vacancy_0444 AS v
           ON v.period_id = p.period_id AND v.geo_id = k.geo_id AND v.noc_id = k.noc_id
    LEFT JOIN fact.offered_wage_0444 AS w
           ON w.period_id = p.period_id AND w.geo_id = k.geo_id AND w.noc_id = k.noc_id
    WHERE p.period_type = 'quarter')
SELECT c.period_start, c.period_label, c.period_year, c.period_quarter,
       CASE WHEN c.period_start >= '2015-04-01' THEN 1 ELSE 0 END AS include_in_trend,
       c.vacancies, c.vacancy_grade, c.offered_wage, c.wage_grade,
       c.vacancies - y.vacancies AS vacancies_change_yoy,
       CASE WHEN y.vacancies > 0
            THEN CAST(100.0 * (c.vacancies - y.vacancies) / y.vacancies AS DECIMAL(7, 1)) END AS vacancies_pct_change_yoy,
       CAST(c.offered_wage - y.offered_wage AS DECIMAL(7, 2)) AS wage_change_yoy,
       CASE WHEN y.offered_wage > 0
            THEN CAST(100.0 * (c.offered_wage - y.offered_wage) / y.offered_wage AS DECIMAL(7, 1)) END AS wage_pct_change_yoy
FROM base AS c
LEFT JOIN base AS y
       ON y.period_year = c.period_year - 1
      AND y.period_quarter = c.period_quarter
      AND y.period_start >= '2015-04-01';
GO

-- Share of occupation groups with a reliable value, latest quarter, by geography and occupation level (rule D10).
CREATE OR ALTER VIEW rpt.vw_reliable_coverage_latest AS
WITH level_sizes AS (
    SELECT noc_level, COUNT(*) AS n_groups
    FROM dim.occupation
    WHERE noc_level > 0
    GROUP BY noc_level),
vac AS (
    SELECT v.geo_id, o.noc_level, COUNT(*) AS n_reliable
    FROM fact.vacancy_0444 AS v
    JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = v.period_id
    JOIN dim.occupation AS o ON o.noc_id = v.noc_id
    WHERE o.noc_level > 0 AND v.quality_grade IN ('A', 'B', 'C', 'D', 'NONE')
    GROUP BY v.geo_id, o.noc_level),
wage AS (
    SELECT w.geo_id, o.noc_level, COUNT(*) AS n_reliable
    FROM fact.offered_wage_0444 AS w
    JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = w.period_id
    JOIN dim.occupation AS o ON o.noc_id = w.noc_id
    WHERE o.noc_level > 0 AND w.quality_grade IN ('A', 'B', 'C', 'D', 'NONE') AND w.is_suspect = 0
    GROUP BY w.geo_id, o.noc_level)
SELECT g.geo_id, g.geo_name, g.geo_level, s.noc_level, s.n_groups,
       COALESCE(vac.n_reliable, 0) AS vacancy_reliable_groups,
       CAST(100.0 * COALESCE(vac.n_reliable, 0) / s.n_groups AS DECIMAL(5, 1)) AS vacancy_reliable_pct,
       COALESCE(wage.n_reliable, 0) AS wage_reliable_groups,
       CAST(100.0 * COALESCE(wage.n_reliable, 0) / s.n_groups AS DECIMAL(5, 1)) AS wage_reliable_pct,
       CASE WHEN 2 * COALESCE(vac.n_reliable, 0) >= s.n_groups THEN 1 ELSE 0 END AS vacancy_meets_50pct_rule,
       CASE WHEN 2 * COALESCE(wage.n_reliable, 0) >= s.n_groups THEN 1 ELSE 0 END AS wage_meets_50pct_rule
FROM dim.geography AS g
CROSS JOIN level_sizes AS s
LEFT JOIN vac ON vac.geo_id = g.geo_id AND vac.noc_level = s.noc_level
LEFT JOIN wage ON wage.geo_id = g.geo_id AND wage.noc_level = s.noc_level
WHERE g.geo_level IN ('Canada', 'Province/territory');
GO

-- Employee wages (0417) with readable labels. These are actual wages, never combined with offered wages.
CREATE OR ALTER VIEW rpt.vw_employee_wage AS
SELECT p.period_year, g.geo_name, c.noc417_code, c.noc417_label, c.kind AS group_kind,
       e.type_of_work, m.measure_name, e.measure_key, e.hourly_wage, e.is_suspect,
       CASE WHEN p.period_year >= 2006 THEN 'from 2006' ELSE 'before 2006' END AS lfs_processing_era
FROM fact.employee_wage_0417 AS e
JOIN dim.period AS p ON p.period_id = e.period_id
JOIN dim.geography AS g ON g.geo_id = e.geo_id
JOIN dim.occupation_0417 AS c ON c.noc417_code = e.noc417_code
JOIN dim.measure AS m ON m.measure_key = e.measure_key;
GO

SELECT s.name + '.' + v.name AS view_name FROM sys.views AS v
JOIN sys.schemas AS s ON s.schema_id = v.schema_id
WHERE s.name = 'rpt' ORDER BY v.name;
GO