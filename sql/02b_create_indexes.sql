-- CareerScope: secondary indexes, created after loading.
-- Safe to run more than once. Primary keys already exist from 02_create_tables.sql.
USE CareerScope;
GO

DROP INDEX IF EXISTS ix_occupation_level ON dim.occupation;
DROP INDEX IF EXISTS ix_occupation_parent ON dim.occupation;
DROP INDEX IF EXISTS ix_geography_level ON dim.geography;
DROP INDEX IF EXISTS ix_geography_parent ON dim.geography;
DROP INDEX IF EXISTS ix_characteristic_root ON dim.characteristic;
DROP INDEX IF EXISTS ix_vac0444_noc ON fact.vacancy_0444;
DROP INDEX IF EXISTS ix_wage0444_noc ON fact.offered_wage_0444;
DROP INDEX IF EXISTS ix_cvac_char ON fact.char_vacancy_0443;
DROP INDEX IF EXISTS ix_cshare_char ON fact.char_vacancy_share_0443;
DROP INDEX IF EXISTS ix_cwage_char ON fact.char_offered_wage_0443;
DROP INDEX IF EXISTS ix_ewage_geo ON fact.employee_wage_0417;
DROP INDEX IF EXISTS ix_ecount_noc ON fact.employee_count_0417;
GO

-- Dimensions: filter by level, walk the hierarchy
CREATE INDEX ix_occupation_level ON dim.occupation (noc_level) INCLUDE (noc_code, noc_title, parent_noc_id);
CREATE INDEX ix_occupation_parent ON dim.occupation (parent_noc_id);
CREATE INDEX ix_geography_level ON dim.geography (geo_level) INCLUDE (geo_name, province_geo_id);
CREATE INDEX ix_geography_parent ON dim.geography (parent_geo_id);
CREATE INDEX ix_characteristic_root ON dim.characteristic (root_char_id);

-- Facts: follow one occupation (and characteristic) across regions and time
CREATE INDEX ix_vac0444_noc ON fact.vacancy_0444 (noc_id, geo_id, period_id)
    INCLUDE (vacancies, quality_grade);
CREATE INDEX ix_wage0444_noc ON fact.offered_wage_0444 (noc_id, geo_id, period_id)
    INCLUDE (offered_wage, quality_grade, is_suspect);
CREATE INDEX ix_cvac_char ON fact.char_vacancy_0443 (char_id, geo_id, noc_id, period_id)
    INCLUDE (vacancies, quality_grade);
CREATE INDEX ix_cshare_char ON fact.char_vacancy_share_0443 (char_id, geo_id, noc_id, period_id)
    INCLUDE (vacancy_share, quality_grade);
CREATE INDEX ix_cwage_char ON fact.char_offered_wage_0443 (char_id, geo_id, noc_id, period_id)
    INCLUDE (offered_wage, quality_grade, is_suspect);
CREATE INDEX ix_ewage_geo ON fact.employee_wage_0417 (geo_id, noc417_code, measure_key, period_id)
    INCLUDE (type_of_work, hourly_wage, is_suspect);
CREATE INDEX ix_ecount_noc ON fact.employee_count_0417 (noc417_code, geo_id, period_id)
    INCLUDE (type_of_work, employees_thousands);
GO

SELECT s.name + '.' + t.name AS table_name, COUNT(*) AS indexes_including_primary_key
FROM sys.indexes AS i
JOIN sys.tables AS t ON t.object_id = i.object_id
JOIN sys.schemas AS s ON s.schema_id = t.schema_id
WHERE i.index_id > 0
GROUP BY s.name, t.name
ORDER BY s.name, t.name;
GO