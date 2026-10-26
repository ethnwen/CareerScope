-- CareerScope: create schemas, tables, keys and constraints.
-- WARNING: this script drops and recreates every table, so any loaded data is deleted.
-- Run 01_create_database.sql first. Secondary indexes are added after loading (02b_create_indexes.sql).
USE CareerScope;
GO

IF SCHEMA_ID(N'dim') IS NULL EXEC(N'CREATE SCHEMA dim');
IF SCHEMA_ID(N'fact') IS NULL EXEC(N'CREATE SCHEMA fact');
IF SCHEMA_ID(N'rpt') IS NULL EXEC(N'CREATE SCHEMA rpt');
GO

DROP TABLE IF EXISTS
    fact.availability_0417, fact.availability_0443, fact.availability_0444,
    fact.employee_count_0417, fact.employee_wage_0417,
    fact.char_offered_wage_0443, fact.char_vacancy_share_0443, fact.char_vacancy_0443,
    fact.offered_wage_0444, fact.vacancy_0444;
DROP TABLE IF EXISTS
    dim.occupation_0417, dim.occupation, dim.characteristic, dim.geography,
    dim.period, dim.measure, dim.source;
GO

-- ---------------------------------------------------------------- dimensions
CREATE TABLE dim.source (
    source_table_id CHAR(8)       NOT NULL CONSTRAINT pk_source PRIMARY KEY,
    title           NVARCHAR(250) NOT NULL,
    survey          NVARCHAR(100) NOT NULL,
    frequency       VARCHAR(10)   NOT NULL CONSTRAINT ck_source_frequency CHECK (frequency IN ('quarterly', 'annual')),
    release_date    DATE          NOT NULL,
    downloaded_on   DATE          NOT NULL
);

CREATE TABLE dim.measure (
    measure_key  VARCHAR(40)   NOT NULL CONSTRAINT pk_measure PRIMARY KEY,
    measure_name NVARCHAR(100) NOT NULL,
    unit         NVARCHAR(40)  NOT NULL,
    concept      VARCHAR(20)   NOT NULL CONSTRAINT ck_measure_concept
                 CHECK (concept IN ('vacancy', 'offered_wage', 'employee_wage', 'employee_count')),
    definition   NVARCHAR(500) NOT NULL
);

CREATE TABLE dim.period (
    period_id      SMALLINT    IDENTITY(1, 1) NOT NULL CONSTRAINT pk_period PRIMARY KEY,
    period_type    VARCHAR(10) NOT NULL CONSTRAINT ck_period_type CHECK (period_type IN ('quarter', 'year')),
    period_start   DATE        NOT NULL,
    period_year    SMALLINT    NOT NULL,
    period_quarter TINYINT     NULL,
    period_label   VARCHAR(10) NOT NULL,
    CONSTRAINT uq_period UNIQUE (period_type, period_start),
    CONSTRAINT ck_period_quarter CHECK (
        (period_type = 'quarter' AND period_quarter BETWEEN 1 AND 4)
        OR (period_type = 'year' AND period_quarter IS NULL))
);

CREATE TABLE dim.geography (
    geo_id             SMALLINT     NOT NULL CONSTRAINT pk_geography PRIMARY KEY,
    geo_name           NVARCHAR(150) NOT NULL,
    sgc_code           VARCHAR(10)  NULL,
    parent_geo_id      SMALLINT     NULL CONSTRAINT fk_geography_parent REFERENCES dim.geography (geo_id),
    province_geo_id    SMALLINT     NULL CONSTRAINT fk_geography_province REFERENCES dim.geography (geo_id),
    geo_level          VARCHAR(20)  NOT NULL CONSTRAINT ck_geo_level
                       CHECK (geo_level IN ('Canada', 'Province/territory', 'Economic region')),
    is_combined_region BIT          NOT NULL,
    CONSTRAINT uq_geography_name UNIQUE (geo_name, geo_level)
);

CREATE TABLE dim.occupation (
    noc_id          SMALLINT      NOT NULL CONSTRAINT pk_occupation PRIMARY KEY,
    noc_code        VARCHAR(5)    NULL,
    noc_level       TINYINT       NOT NULL CONSTRAINT ck_noc_level CHECK (noc_level BETWEEN 0 AND 5),
    noc_level_name  VARCHAR(30)   NOT NULL,
    noc_title       NVARCHAR(300) NOT NULL,
    parent_noc_id   SMALLINT      NULL CONSTRAINT fk_occupation_parent REFERENCES dim.occupation (noc_id),
    is_total        BIT           NOT NULL,
    is_unclassified BIT           NOT NULL
);
CREATE UNIQUE INDEX ux_occupation_code ON dim.occupation (noc_code) WHERE noc_code IS NOT NULL;

CREATE TABLE dim.characteristic (
    char_id            SMALLINT      NOT NULL CONSTRAINT pk_characteristic PRIMARY KEY,
    char_title         NVARCHAR(150) NOT NULL,
    parent_char_id     SMALLINT      NULL CONSTRAINT fk_characteristic_parent REFERENCES dim.characteristic (char_id),
    root_char_id       SMALLINT      NOT NULL,
    dimension          VARCHAR(40)   NOT NULL,
    is_dimension_total BIT           NOT NULL,
    is_terminated      BIT           NOT NULL,
    analysis_scope     VARCHAR(15)   NOT NULL CONSTRAINT ck_char_scope
                       CHECK (analysis_scope IN ('in_scope', 'verify_first', 'out_of_scope'))
);

CREATE TABLE dim.occupation_0417 (
    noc417_code       VARCHAR(40)   NOT NULL CONSTRAINT pk_occupation_0417 PRIMARY KEY,
    noc417_label      NVARCHAR(250) NOT NULL,
    kind              VARCHAR(10)   NOT NULL CONSTRAINT ck_occ0417_kind CHECK (kind IN ('single', 'combined')),
    noc_id_0444       SMALLINT      NULL CONSTRAINT fk_occ0417_noc REFERENCES dim.occupation (noc_id),
    name_matches_0444 BIT           NOT NULL
);
GO

-- --------------------------------------------- facts: offered wages and vacancies (0444)
CREATE TABLE fact.vacancy_0444 (
    period_id     SMALLINT   NOT NULL CONSTRAINT fk_vac0444_period REFERENCES dim.period (period_id),
    geo_id        SMALLINT   NOT NULL CONSTRAINT fk_vac0444_geo REFERENCES dim.geography (geo_id),
    noc_id        SMALLINT   NOT NULL CONSTRAINT fk_vac0444_noc REFERENCES dim.occupation (noc_id),
    vacancies     INT        NOT NULL CONSTRAINT ck_vac0444_value CHECK (vacancies >= 0),
    quality_grade VARCHAR(4) NOT NULL CONSTRAINT ck_vac0444_grade CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'E', 'NONE')),
    CONSTRAINT pk_vac0444 PRIMARY KEY (period_id, geo_id, noc_id)
);

CREATE TABLE fact.offered_wage_0444 (
    period_id      SMALLINT     NOT NULL CONSTRAINT fk_wage0444_period REFERENCES dim.period (period_id),
    geo_id         SMALLINT     NOT NULL CONSTRAINT fk_wage0444_geo REFERENCES dim.geography (geo_id),
    noc_id         SMALLINT     NOT NULL CONSTRAINT fk_wage0444_noc REFERENCES dim.occupation (noc_id),
    offered_wage   DECIMAL(7,2) NOT NULL CONSTRAINT ck_wage0444_value CHECK (offered_wage >= 0),
    quality_grade  VARCHAR(4)   NOT NULL CONSTRAINT ck_wage0444_grade CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'E', 'NONE')),
    is_suspect     BIT          NOT NULL,
    suspect_reason VARCHAR(30)  NULL,
    CONSTRAINT ck_wage0444_suspect CHECK ((is_suspect = 1 AND suspect_reason IS NOT NULL)
                                          OR (is_suspect = 0 AND suspect_reason IS NULL)),
    CONSTRAINT pk_wage0444 PRIMARY KEY (period_id, geo_id, noc_id)
);

-- ------------------------------------------------- facts: job characteristics (0443)
CREATE TABLE fact.char_vacancy_0443 (
    period_id     SMALLINT   NOT NULL CONSTRAINT fk_cvac_period REFERENCES dim.period (period_id),
    geo_id        SMALLINT   NOT NULL CONSTRAINT fk_cvac_geo REFERENCES dim.geography (geo_id),
    noc_id        SMALLINT   NOT NULL CONSTRAINT fk_cvac_noc REFERENCES dim.occupation (noc_id),
    char_id       SMALLINT   NOT NULL CONSTRAINT fk_cvac_char REFERENCES dim.characteristic (char_id),
    vacancies     INT        NOT NULL CONSTRAINT ck_cvac_value CHECK (vacancies >= 0),
    quality_grade VARCHAR(4) NOT NULL CONSTRAINT ck_cvac_grade CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'E', 'NONE')),
    CONSTRAINT pk_cvac PRIMARY KEY (period_id, geo_id, noc_id, char_id)
);

CREATE TABLE fact.char_vacancy_share_0443 (
    period_id     SMALLINT     NOT NULL CONSTRAINT fk_cshare_period REFERENCES dim.period (period_id),
    geo_id        SMALLINT     NOT NULL CONSTRAINT fk_cshare_geo REFERENCES dim.geography (geo_id),
    noc_id        SMALLINT     NOT NULL CONSTRAINT fk_cshare_noc REFERENCES dim.occupation (noc_id),
    char_id       SMALLINT     NOT NULL CONSTRAINT fk_cshare_char REFERENCES dim.characteristic (char_id),
    vacancy_share DECIMAL(5,1) NOT NULL CONSTRAINT ck_cshare_value CHECK (vacancy_share BETWEEN 0 AND 100),
    quality_grade VARCHAR(4)   NOT NULL CONSTRAINT ck_cshare_grade CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'E', 'NONE')),
    CONSTRAINT pk_cshare PRIMARY KEY (period_id, geo_id, noc_id, char_id)
);

CREATE TABLE fact.char_offered_wage_0443 (
    period_id      SMALLINT     NOT NULL CONSTRAINT fk_cwage_period REFERENCES dim.period (period_id),
    geo_id         SMALLINT     NOT NULL CONSTRAINT fk_cwage_geo REFERENCES dim.geography (geo_id),
    noc_id         SMALLINT     NOT NULL CONSTRAINT fk_cwage_noc REFERENCES dim.occupation (noc_id),
    char_id        SMALLINT     NOT NULL CONSTRAINT fk_cwage_char REFERENCES dim.characteristic (char_id),
    offered_wage   DECIMAL(7,2) NOT NULL CONSTRAINT ck_cwage_value CHECK (offered_wage >= 0),
    quality_grade  VARCHAR(4)   NOT NULL CONSTRAINT ck_cwage_grade CHECK (quality_grade IN ('A', 'B', 'C', 'D', 'E', 'NONE')),
    is_suspect     BIT          NOT NULL,
    suspect_reason VARCHAR(30)  NULL,
    CONSTRAINT ck_cwage_suspect CHECK ((is_suspect = 1 AND suspect_reason IS NOT NULL)
                                       OR (is_suspect = 0 AND suspect_reason IS NULL)),
    CONSTRAINT pk_cwage PRIMARY KEY (period_id, geo_id, noc_id, char_id)
);

-- ------------------------------------------------------ facts: employee wages (0417)
CREATE TABLE fact.employee_wage_0417 (
    period_id      SMALLINT     NOT NULL CONSTRAINT fk_ewage_period REFERENCES dim.period (period_id),
    geo_id         SMALLINT     NOT NULL CONSTRAINT fk_ewage_geo REFERENCES dim.geography (geo_id),
    noc417_code    VARCHAR(40)  NOT NULL CONSTRAINT fk_ewage_noc REFERENCES dim.occupation_0417 (noc417_code),
    type_of_work   VARCHAR(10)  NOT NULL CONSTRAINT ck_ewage_work CHECK (type_of_work IN ('all', 'full_time', 'part_time')),
    measure_key    VARCHAR(40)  NOT NULL CONSTRAINT fk_ewage_measure REFERENCES dim.measure (measure_key),
    hourly_wage    DECIMAL(7,2) NOT NULL CONSTRAINT ck_ewage_value CHECK (hourly_wage > 0),
    is_suspect     BIT          NOT NULL,
    suspect_reason VARCHAR(30)  NULL,
    CONSTRAINT ck_ewage_suspect CHECK ((is_suspect = 1 AND suspect_reason IS NOT NULL)
                                       OR (is_suspect = 0 AND suspect_reason IS NULL)),
    CONSTRAINT pk_ewage PRIMARY KEY (period_id, geo_id, noc417_code, type_of_work, measure_key)
);

CREATE TABLE fact.employee_count_0417 (
    period_id           SMALLINT      NOT NULL CONSTRAINT fk_ecount_period REFERENCES dim.period (period_id),
    geo_id              SMALLINT      NOT NULL CONSTRAINT fk_ecount_geo REFERENCES dim.geography (geo_id),
    noc417_code         VARCHAR(40)   NOT NULL CONSTRAINT fk_ecount_noc REFERENCES dim.occupation_0417 (noc417_code),
    type_of_work        VARCHAR(10)   NOT NULL CONSTRAINT ck_ecount_work CHECK (type_of_work IN ('all', 'full_time', 'part_time')),
    employees_thousands DECIMAL(10,1) NOT NULL CONSTRAINT ck_ecount_value CHECK (employees_thousands >= 0),
    CONSTRAINT pk_ecount PRIMARY KEY (period_id, geo_id, noc417_code, type_of_work)
);

-- -------------------------------------------------------------- coverage (availability)
CREATE TABLE fact.availability_0444 (
    period_id    SMALLINT    NOT NULL CONSTRAINT fk_av0444_period REFERENCES dim.period (period_id),
    geo_id       SMALLINT    NOT NULL CONSTRAINT fk_av0444_geo REFERENCES dim.geography (geo_id),
    noc_level    TINYINT     NOT NULL CONSTRAINT ck_av0444_level CHECK (noc_level BETWEEN 0 AND 5),
    measure_key  VARCHAR(40) NOT NULL CONSTRAINT fk_av0444_measure REFERENCES dim.measure (measure_key),
    status_group VARCHAR(15) NOT NULL CONSTRAINT ck_av0444_status
                 CHECK (status_group IN ('value', 'not_available', 'suppressed', 'unreliable')),
    n_cells      INT         NOT NULL CONSTRAINT ck_av0444_n CHECK (n_cells > 0),
    CONSTRAINT pk_av0444 PRIMARY KEY (period_id, geo_id, noc_level, measure_key, status_group)
);

CREATE TABLE fact.availability_0443 (
    period_id    SMALLINT    NOT NULL CONSTRAINT fk_av0443_period REFERENCES dim.period (period_id),
    geo_id       SMALLINT    NOT NULL CONSTRAINT fk_av0443_geo REFERENCES dim.geography (geo_id),
    noc_level    TINYINT     NOT NULL CONSTRAINT ck_av0443_level CHECK (noc_level BETWEEN 0 AND 5),
    char_id      SMALLINT    NOT NULL CONSTRAINT fk_av0443_char REFERENCES dim.characteristic (char_id),
    measure_key  VARCHAR(40) NOT NULL CONSTRAINT fk_av0443_measure REFERENCES dim.measure (measure_key),
    status_group VARCHAR(15) NOT NULL CONSTRAINT ck_av0443_status
                 CHECK (status_group IN ('value', 'not_available', 'suppressed', 'unreliable')),
    n_cells      INT         NOT NULL CONSTRAINT ck_av0443_n CHECK (n_cells > 0),
    CONSTRAINT pk_av0443 PRIMARY KEY (period_id, geo_id, noc_level, char_id, measure_key, status_group)
);

CREATE TABLE fact.availability_0417 (
    period_id    SMALLINT    NOT NULL CONSTRAINT fk_av0417_period REFERENCES dim.period (period_id),
    geo_id       SMALLINT    NOT NULL CONSTRAINT fk_av0417_geo REFERENCES dim.geography (geo_id),
    type_of_work VARCHAR(10) NOT NULL CONSTRAINT ck_av0417_work CHECK (type_of_work IN ('all', 'full_time', 'part_time')),
    measure_key  VARCHAR(40) NOT NULL CONSTRAINT fk_av0417_measure REFERENCES dim.measure (measure_key),
    status_group VARCHAR(15) NOT NULL CONSTRAINT ck_av0417_status
                 CHECK (status_group IN ('value', 'not_available', 'suppressed', 'unreliable')),
    n_cells      INT         NOT NULL CONSTRAINT ck_av0417_n CHECK (n_cells > 0),
    CONSTRAINT pk_av0417 PRIMARY KEY (period_id, geo_id, type_of_work, measure_key, status_group)
);
GO

-- ------------------------------------------------------------------ reference data
INSERT INTO dim.source (source_table_id, title, survey, frequency, release_date, downloaded_on) VALUES
('14100444', N'Job vacancies and average offered hourly wage by occupation (unit group), quarterly, unadjusted for seasonality',
 N'Job Vacancy and Wage Survey', 'quarterly', '2026-09-15', '2026-10-22'),
('14100443', N'Job vacancies, proportion of job vacancies and average offered hourly wage by occupation and selected characteristics, quarterly, unadjusted for seasonality',
 N'Job Vacancy and Wage Survey', 'quarterly', '2026-09-15', '2026-10-22'),
('14100417', N'Employee wages by occupation, annual',
 N'Labour Force Survey', 'annual', '2026-01-09', '2026-10-22');

INSERT INTO dim.measure (measure_key, measure_name, unit, concept, definition) VALUES
('job_vacancies', N'Job vacancies', N'Number', 'vacancy',
 N'Vacant jobs on the first day of the month where the employer is actively recruiting outside the organization. Not total jobs and not a hiring probability.'),
('vacancy_share', N'Proportion of job vacancies', N'Percent', 'vacancy',
 N'Share of all vacancies in the quarter. Seasonal is a share of temporary vacancies.'),
('offered_wage_avg', N'Average offered hourly wage', N'Dollars per hour', 'offered_wage',
 N'Average hourly wage offered for vacant positions. Excludes overtime, tips, commissions and bonuses. The lowest value of an advertised range is reported. Not actual pay.'),
('employee_wage_avg_hourly', N'Average hourly wage of employees', N'Current dollars per hour', 'employee_wage',
 N'Usual wage at the main job before deductions, including tips, commissions and bonuses. Not inflation adjusted. Level shift in 2006.'),
('employee_wage_median_hourly', N'Median hourly wage of employees', N'Current dollars per hour', 'employee_wage',
 N'Median usual wage at the main job before deductions, including tips, commissions and bonuses. Not inflation adjusted. Level shift in 2006.'),
('employee_count', N'Number of employees', N'Persons in thousands', 'employee_count',
 N'Employees in the category, rounded to the nearest hundred.');
GO

SELECT COUNT(*) AS tables_created
FROM sys.tables
WHERE schema_id IN (SCHEMA_ID(N'dim'), SCHEMA_ID(N'fact'));   -- expect 17
GO