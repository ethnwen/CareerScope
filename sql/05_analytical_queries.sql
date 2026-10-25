-- CareerScope: analytical queries answering the research questions.
-- Read-only. Reliable = grade A to D (or exact value with no grade), not suspect.
-- Expected results (from docs/findings.md) are noted beside each query.
USE CareerScope;
GO

-- Q1. Highest offered wages, Canada, unit groups, latest quarter.
-- Expect: 00012 $94.50, 00015 $87.50, 31110 Dentists $83.15 ...
SELECT TOP (10) o.noc_code, o.noc_title, x.offered_wage, x.wage_grade, x.vacancies
FROM rpt.vw_occupation_geo_period AS x
JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = x.period_id
JOIN dim.geography AS g ON g.geo_id = x.geo_id AND g.geo_level = 'Canada'
JOIN dim.occupation AS o ON o.noc_id = x.noc_id AND o.noc_level = 5
WHERE x.wage_is_reliable = 1
ORDER BY x.offered_wage DESC;
GO

-- Q2. Most reported vacancies, Canada, unit groups, latest quarter.
-- Expect: registered nurses 31301 with 17,275 vacancies near the top of the reliable list.
SELECT TOP (10) o.noc_code, o.noc_title, x.vacancies, x.vacancy_grade, x.offered_wage
FROM rpt.vw_occupation_geo_period AS x
JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = x.period_id
JOIN dim.geography AS g ON g.geo_id = x.geo_id AND g.geo_level = 'Canada'
JOIN dim.occupation AS o ON o.noc_id = x.noc_id AND o.noc_level = 5
WHERE x.vacancy_is_reliable = 1
ORDER BY x.vacancies DESC;
GO

-- Q3. One occupation across provinces. LEFT JOIN keeps provinces with no published value (shown as NULL).
-- Change @noc_code to explore another occupation (2-digit major group, for example '31' or '72').
DECLARE @noc_code VARCHAR(5) = '31';   -- Professional occupations in health
SELECT g.geo_name, x.vacancies, x.vacancy_grade, x.offered_wage, x.wage_grade,
       CASE WHEN x.wage_is_reliable = 1 THEN 'reliable'
            WHEN x.offered_wage IS NULL THEN 'not published'
            ELSE 'low quality or suspect' END AS wage_status
FROM dim.geography AS g
CROSS JOIN (SELECT noc_id FROM dim.occupation WHERE noc_code = @noc_code) AS o
CROSS JOIN rpt.vw_latest_quarter AS lq
LEFT JOIN rpt.vw_occupation_geo_period AS x
       ON x.geo_id = g.geo_id AND x.noc_id = o.noc_id AND x.period_id = lq.period_id
WHERE g.geo_level IN ('Canada', 'Province/territory')
ORDER BY x.offered_wage DESC;
GO

-- Q4. Where is there enough reliable data at unit-group level (rule D10)?
-- Expect the wage rule to be met only by Canada, Ontario, Quebec and British Columbia; Alberta is just under 50%.
SELECT geo_name, wage_reliable_groups, n_groups, wage_reliable_pct, wage_meets_50pct_rule,
       vacancy_reliable_pct, vacancy_meets_50pct_rule
FROM rpt.vw_reliable_coverage_latest
WHERE noc_level = 5
ORDER BY wage_reliable_pct DESC;
GO

-- Q5a. Latest eight quarters with year-over-year change.
SELECT TOP (8) period_label, vacancies, vacancies_pct_change_yoy, offered_wage, wage_pct_change_yoy
FROM rpt.vw_national_trend
WHERE include_in_trend = 1
ORDER BY period_start DESC;
GO

-- Q5b. Extremes of year-over-year change.
-- Expect: vacancies +62.8 (2021Q4) and -25.6 (2023Q3); wage +8.5 (2022Q4) and +0.8 (2017Q3).
SELECT 'highest vacancy change' AS metric, t.period_label, t.vacancies_pct_change_yoy AS pct_change
FROM (SELECT TOP (1) WITH TIES period_label, vacancies_pct_change_yoy FROM rpt.vw_national_trend
      WHERE include_in_trend = 1 AND vacancies_pct_change_yoy IS NOT NULL
      ORDER BY vacancies_pct_change_yoy DESC) AS t
UNION ALL
SELECT 'lowest vacancy change', t.period_label, t.vacancies_pct_change_yoy
FROM (SELECT TOP (1) WITH TIES period_label, vacancies_pct_change_yoy FROM rpt.vw_national_trend
      WHERE include_in_trend = 1 AND vacancies_pct_change_yoy IS NOT NULL
      ORDER BY vacancies_pct_change_yoy ASC) AS t
UNION ALL
SELECT 'highest offered wage change', t.period_label, t.wage_pct_change_yoy
FROM (SELECT TOP (1) WITH TIES period_label, wage_pct_change_yoy FROM rpt.vw_national_trend
      WHERE include_in_trend = 1 AND wage_pct_change_yoy IS NOT NULL
      ORDER BY wage_pct_change_yoy DESC) AS t
UNION ALL
SELECT 'lowest offered wage change', t.period_label, t.wage_pct_change_yoy
FROM (SELECT TOP (1) WITH TIES period_label, wage_pct_change_yoy FROM rpt.vw_national_trend
      WHERE include_in_trend = 1 AND wage_pct_change_yoy IS NOT NULL
      ORDER BY wage_pct_change_yoy ASC) AS t;
GO

-- Q6. Offered wage, vacancies and share by education requirement (Canada, all occupations, latest quarter).
-- Expect $20.90 for no minimum education up to $48.85 above a bachelor's. Trade and college sit inside
-- "Non-university certificate or diploma", so do not add them to it (see parent_char_id).
SELECT c.char_id, c.parent_char_id, c.char_title, w.offered_wage, v.vacancies, s.vacancy_share
FROM dim.characteristic AS c
CROSS JOIN rpt.vw_latest_quarter AS lq
CROSS JOIN (SELECT geo_id FROM dim.geography WHERE geo_level = 'Canada') AS g
CROSS JOIN (SELECT noc_id FROM dim.occupation WHERE is_total = 1) AS o
LEFT JOIN fact.char_offered_wage_0443 AS w
       ON w.char_id = c.char_id AND w.period_id = lq.period_id AND w.geo_id = g.geo_id AND w.noc_id = o.noc_id
LEFT JOIN fact.char_vacancy_0443 AS v
       ON v.char_id = c.char_id AND v.period_id = lq.period_id AND v.geo_id = g.geo_id AND v.noc_id = o.noc_id
LEFT JOIN fact.char_vacancy_share_0443 AS s
       ON s.char_id = c.char_id AND s.period_id = lq.period_id AND s.geo_id = g.geo_id AND s.noc_id = o.noc_id
WHERE c.dimension = 'Education' AND c.is_dimension_total = 0
ORDER BY w.offered_wage;
GO

-- Q7. Rank correlation between offered wage and vacancies, computed in SQL (window functions, tie-adjusted ranks).
-- Expect 312 unit groups and rho = -0.27, the same as the Python result.
WITH paired AS (
    SELECT x.noc_id, CAST(x.offered_wage AS FLOAT) AS wage, CAST(x.vacancies AS FLOAT) AS vacancies
    FROM rpt.vw_occupation_geo_period AS x
    JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = x.period_id
    JOIN dim.geography AS g ON g.geo_id = x.geo_id AND g.geo_level = 'Canada'
    JOIN dim.occupation AS o ON o.noc_id = x.noc_id AND o.noc_level = 5
    WHERE x.wage_is_reliable = 1 AND x.vacancy_is_reliable = 1 AND x.vacancies > 0),
ranked AS (
    SELECT noc_id,
           RANK() OVER (ORDER BY wage) + (COUNT(*) OVER (PARTITION BY wage) - 1) / 2.0 AS wage_rank,
           RANK() OVER (ORDER BY vacancies) + (COUNT(*) OVER (PARTITION BY vacancies) - 1) / 2.0 AS vac_rank
    FROM paired),
rk AS (
    SELECT CAST(wage_rank AS FLOAT) AS wr, CAST(vac_rank AS FLOAT) AS vr FROM ranked)
SELECT COUNT(*) AS unit_groups,
       ROUND((COUNT(*) * SUM(wr * vr) - SUM(wr) * SUM(vr))
             / (SQRT(COUNT(*) * SUM(wr * wr) - POWER(SUM(wr), 2))
                * SQRT(COUNT(*) * SUM(vr * vr) - POWER(SUM(vr), 2))), 2) AS spearman_rho
FROM rk;
GO

-- Q8. Quarters where fewer than 12% of vacancy cells have a value (GROUP BY with HAVING).
-- Expect 2015Q1 (about 0.4%), 2015Q2 to 2015Q4 and 2016Q1.
SELECT p.period_label, a.measure_key,
       CAST(100.0 * SUM(CASE WHEN a.status_group = 'value' THEN a.n_cells ELSE 0 END) / SUM(a.n_cells)
            AS DECIMAL(5, 1)) AS pct_cells_with_value
FROM fact.availability_0444 AS a
JOIN dim.period AS p ON p.period_id = a.period_id
WHERE a.measure_key = 'job_vacancies'
GROUP BY p.period_start, p.period_label, a.measure_key
HAVING 100.0 * SUM(CASE WHEN a.status_group = 'value' THEN a.n_cells ELSE 0 END) / SUM(a.n_cells) < 12
ORDER BY p.period_start;
GO

-- Q9. Duplicate names across geography levels. Expect 4 rows: Prince Edward Island, Yukon,
-- Northwest Territories and Nunavut. This is why facts join on IDs and never on names.
SELECT geo_name, COUNT(*) AS n_geographies, STRING_AGG(geo_level, ', ') AS levels
FROM dim.geography
GROUP BY geo_name
HAVING COUNT(*) > 1
ORDER BY geo_name;
GO

-- Q10. NULL handling: unit groups in Canada (latest quarter) with a published wage but no vacancy count, and so on.
SELECT t.availability, COUNT(*) AS unit_groups
FROM (SELECT CASE WHEN x.vacancies IS NOT NULL AND x.offered_wage IS NOT NULL THEN '1 both published'
                  WHEN x.offered_wage IS NOT NULL THEN '2 wage only'
                  ELSE '3 vacancies only' END AS availability
      FROM rpt.vw_occupation_geo_period AS x
      JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = x.period_id
      JOIN dim.geography AS g ON g.geo_id = x.geo_id AND g.geo_level = 'Canada'
      JOIN dim.occupation AS o ON o.noc_id = x.noc_id AND o.noc_level = 5) AS t
GROUP BY t.availability
ORDER BY t.availability;
GO

