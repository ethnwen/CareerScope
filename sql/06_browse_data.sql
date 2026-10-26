USE CareerScope;
GO
SELECT TOP (10) geo_id, geo_name, geo_level FROM dim.geography ORDER BY geo_id;
SELECT TOP (10) noc_id, noc_code, noc_level, noc_title FROM dim.occupation ORDER BY noc_level, noc_id;
SELECT TOP (10) period_label, vacancies, vacancies_pct_change_yoy, offered_wage, wage_pct_change_yoy
FROM rpt.vw_national_trend ORDER BY period_start DESC;
SELECT TOP (10) geo_name, wage_reliable_pct, vacancy_reliable_pct
FROM rpt.vw_reliable_coverage_latest WHERE noc_level = 5 ORDER BY wage_reliable_pct DESC;
SELECT TOP (10) period_year, geo_name, hourly_wage
FROM rpt.vw_employee_wage
WHERE noc417_code = '00-95' AND type_of_work = 'all' AND measure_key = 'employee_wage_avg_hourly'
ORDER BY period_year DESC, geo_name;
GO