# Data Dictionary (initial, Phase 1)

Based on inspection of the three Statistics Canada files and their metadata. "Verified" means checked against the downloaded files. "To verify" means still open.

## 1. Columns shared by the Statistics Canada files

| Column | Meaning |
|---|---|
| REF_DATE | Period. 0444 and 0443: YYYY-MM, the first month of the quarter (2026-04 is Q2 2026). 0417: YYYY. |
| GEO | Geography name. Not a unique key in 0444 (see section 3). |
| DGUID | Geography identifier. Blank for the seven combined economic regions in 0444. |
| Dimension columns | Table specific (sections 3 to 5). |
| UOM, UOM_ID | Unit of measure. |
| SCALAR_FACTOR, SCALAR_ID | Always "units" and 0. No rescaling needed. |
| VECTOR, COORDINATE | Series identifiers. COORDINATE is a dot-separated list of member IDs. |
| VALUE | Numeric value. Empty when STATUS says unavailable, suppressed or too unreliable. |
| STATUS | Quality grade or flag (section 2). |
| SYMBOL | Empty in all three tables. Dropped during cleaning and documented. |
| TERMINATED | "t" marks a discontinued series. Used only in 0443. |
| DECIMALS | Display precision. |

## 2. STATUS and missing data

| STATUS | Meaning | Has a value? |
|---|---|---|
| A, B, C, D, E | Quality grades: excellent, very good, good, acceptable, use with caution | Yes (0444, 0443). Not used in 0417. |
| F | Too unreliable to be published | No |
| x | Suppressed to meet confidentiality requirements | No |
| .. | Not available for the period | No |
| blank | No flag | Yes (verified in 0443 and 0417). Never occurs in 0444. |

Rules:
- A blank STATUS is a valid value, not a missing one. Do not treat it as NaN.
- Missing, suppressed and zero are three different things. In 0444 there are 6,578 true zeros, all vacancy counts and no wages. Zeros in 0443 and 0417: to verify.
- In 0443, blank STATUS appears on vacancy counts and proportions only. In the Canada totals the blank rows are the 100.0% totals. The remaining blank vacancy rows: to verify.

## 3. Geography and occupation (0444 and 0443)

- COORDINATE layout. 0444: geography.occupation.statistic. 0443: geography.occupation.characteristic.statistic. Verified from sample rows such as 1.1.19.5.
- Statistic IDs: 1 = Job vacancies, 5 = Average offered hourly wage (from the 0444 metadata). In 0443 the rows ending in .2 are Proportion of job vacancies (observed in the data).
- Geography member ID (first part of COORDINATE) in 0444: 1 = Canada, 2 to 14 = provinces and territories, 15 and above = economic regions (69).
- Geography name collision (0444): Prince Edward Island, Yukon, Northwest Territories and Nunavut each appear twice, once as a province or territory and once as an economic region, with the same GEO name. Verified: 290,048 duplicate rows on a name key, 0 on the coordinate key. Key by COORDINATE, never by name.
- Occupation classification: NOC 2021 version 1.0. The bracketed code at the end of the label gives the level.

| Digits | Level | Labels (verified) |
|---|---|---|
| none | "Total, all occupations" and "Unclassified occupations" | 2 |
| 1 | Broad occupational category | 10 |
| 2 | Major group | 45 |
| 3 | Sub-major group | 89 |
| 4 | Minor group | 162 |
| 5 | Unit group | 516 |

- The same name can appear at several levels (for example "Legislative and senior managers" at 2, 3 and 4 digits). Key by code. Never sum across levels, because each level contains the ones below it.
- Parent-child relationships are in the Member ID and Parent Member ID columns of the metadata file. The dimension tables will be built from them.

## 4. Job vacancy characteristics (0443)

Eight dimensions, each with an "all" total. Members are keyed by their ID (third part of COORDINATE). Labels are not unique: "Constantly recruiting" exists as ID 29 (old, terminated) and ID 48 (current).

| Dimension (root ID) | Member IDs and structure | In scope |
|---|---|---|
| Type of work (1) | 2 Full-time, 3 Part-time (30 hours or more per week is full-time) | Yes |
| Education (4) | 5 No minimum, 6 High school, 7 Non-university certificate or diploma (contains 8 Trade and 9 College/CEGEP), 10 University certificate below bachelor's, 12 Bachelor's, 13 Above bachelor's | Yes |
| Experience (17) | 18 Less than 1 year, 19 1 to under 3, 20 3 to under 5, 21 5 to under 8, 22 8 years or more | Yes |
| Type of position (30) | 31 Permanent, 32 Temporary (contains 33 Seasonal) | Yes |
| Continuity of recruitment (47) | 48 Constantly recruiting, 49 Not constantly recruiting | To verify start quarter |
| Duration (23) | 24 to 27, 28 (90 days or more, contains 45 and 46), 29 old Constantly recruiting (terminated) | No. Definition changed in Q1 2020 (Note 15). |
| Certification (14) | 15, 16 | No. Terminated. |
| Recruitment strategies (34) | 35 to 44. Multiple responses allowed. No wage data. | No |

Rules for combining:
- Only add non-overlapping members of one dimension. In Education that is 5, 6, 7, 10, 12, 13. Adding 8 and 9 to 7 double counts.
- Proportions are the share of all vacancies in the quarter, except Seasonal (33), which is the share of Temporary vacancies.
- Validation baseline (Canada, total occupations, 2026-04, checked in Phase 1): non-overlapping proportions in each in-scope dimension sum to 100%, and counts sum to 548,400 within rounding. Counts appear rounded to the nearest 5.

## 5. Employee wages (0417)

| Dimension | Members |
|---|---|
| Wages | 9: average and median hourly wage rate, average and median weekly wage rate, four gender wage ratios, total employees |
| Type of work | 3: both full- and part-time, full-time, part-time |
| Gender | 3: Total, Men+, Women+ (sex before 2022, gender from 2022, combined) |
| Age group | 4: 15 and over, 15 to 24, 25 to 54, 55 and over |
| NOC | 59 labels, many of them overlapping combined groups, for example [11-14] and [10, 20, 30, 40, 50] |
| Geography | 11: Canada and 10 provinces |

- Units: current dollars (not inflation adjusted), ratio, persons in thousands.
- STATUS has only blank, ".." and "x". Blank means a valid value. There are no quality grades.
- Planned slice for the analysis: average and median hourly wage, both full- and part-time, Total gender, 15 years and over.
- Key uniqueness for this table: to verify in Phase 2.

## 6. Measure catalogue

| measure_key | Source | Unit | Definition and caveat |
|---|---|---|---|
| offered_wage_avg | 0444, 0443 | Dollars per hour | Average hourly wage offered for vacant positions. Excludes overtime, tips, commissions, bonuses. For advertised ranges, the lowest value is reported. It is not actual pay. |
| job_vacancies | 0444, 0443 | Number | Vacant jobs on the first day of the month where the employer is actively recruiting outside the organization. Not total jobs and not a hiring probability. |
| vacancy_share | 0443 | Percent | Share of all vacancies in the quarter. Seasonal is a share of Temporary. Never sum or average across occupations without weighting. |
| employee_wage_avg_hourly, employee_wage_median_hourly | 0417 | Current dollars | Usual wage at main job before deductions, including tips, commissions and bonuses. Not inflation adjusted. Level shift in 2006. |
| employee_count | 0417 | Persons in thousands | Employees in the category, rounded to the nearest hundred. |

Offered wages and employee wages are different concepts and are never combined in one series.

## 7. Planned derived columns

geo_id, geo_level, noc_code, noc_level, char_id, char_dimension, status_group (value_ok, not_available, suppressed, unreliable), quality_grade, period_start_date, quarter_label, measure_key, source_table_id.
