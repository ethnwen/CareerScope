# Data Source Inventory

Created in Phase 1 (data discovery). All Statistics Canada files were downloaded manually on 2026-10-22 as "entire table" CSV zips and are kept unmodified in `data/raw/`. Items marked "to verify" are not yet confirmed.

## Summary

| Source | Frequency | Reference period | Geography | Role in CareerScope |
|---|---|---|---|---|
| 14-10-0444-01 | Quarterly | 2015-01 to 2026-04 | Canada, provinces and territories, economic regions | Core: offered wages and vacancies |
| 14-10-0443-01 | Quarterly | 2015-01 to 2026-04 | Canada, provinces and territories | Characteristics: education, experience, type of work, type of position |
| 14-10-0417-01 | Annual | 1997 to 2025 | Canada, provinces | Core: historical employee wages |
| Job Bank wages | Annual | Yearly files, 2012 to 2025 | Economic regions, provinces, national | Deferred, not yet inspected |

## 14-10-0444-01: Job vacancies and average offered hourly wage by occupation (unit group), quarterly, unadjusted for seasonality

- Publisher and survey: Statistics Canada, Job Vacancy and Wage Survey (survey code 5217)
- URL: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410044401
- Release date: 2026-09-15. Download date: 2026-10-22.
- Local files: `data/raw/14100444-eng/14100444.csv` (about 1.2 GB, 6,018,496 rows, 16 columns) and `14100444_MetaData.csv`
- Reference period: 2015-01 to 2026-04, 44 quarters. REF_DATE is the first month of the quarter. Q2 and Q3 2020 are unavailable because operations were suspended during COVID-19.
- Geography: Canada, 13 provinces and territories, 69 economic regions (seven are combined regions with no DGUID).
- Occupations: NOC 2021 version 1.0. Data from 2023 Q4 were coded directly. Data from 2015 Q1 to 2023 Q3 were converted from earlier NOC versions.
- Measures: Job vacancies (Number), Average offered hourly wage (Dollars).
- The web page description says "last 5 quarters". That describes the default web view. The file holds the full history.
- Licence: to verify (Statistics Canada terms and conditions).
- Status: inspected. Core source.

## 14-10-0443-01: Job vacancies, proportion of job vacancies and average offered hourly wage by occupation and selected characteristics, quarterly, unadjusted for seasonality

- Publisher and survey: Statistics Canada, Job Vacancy and Wage Survey (survey code 5217)
- URL: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410044301
- Release date: 2026-09-15. Download date: 2026-10-22.
- Local files: `data/raw/14100443-eng/14100443.csv` (14,465 MB, 67,508,672 rows, 17 columns) and `14100443_MetaData.csv`. The file is too large to load whole, so it is read in chunks.
- Reference period: 2015-01 to 2026-04, same 44 quarters and same 2020 gap as 0444.
- Geography: Canada, 10 provinces, 3 territories (no economic regions).
- Occupations: same 824 NOC 2021 labels as 0444 (same conversion caveat).
- Characteristics: 48 members in 8 dimensions (see data dictionary). Four members are terminated.
- Measures: Job vacancies (Number), Proportion of job vacancies (Percent), Average offered hourly wage (Dollars; not published for recruitment strategies).
- Corrections: Q4 2023 estimates corrected on 2024-04-12.
- Licence: to verify (Statistics Canada terms and conditions).
- Status: inspected. Used for the characteristics analysis only.

## 14-10-0417-01: Employee wages by occupation, annual

- Publisher and survey: Statistics Canada, Labour Force Survey (not the Job Vacancy and Wage Survey)
- URL: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041701
- Release date: 2026-01-09. Download date: 2026-10-22.
- Local files: `data/raw/14100417-eng/14100417.csv` (6,098,004 rows, 19 columns) and `14100417_MetaData.csv`
- Reference period: 1997 to 2025, annual.
- Geography: Canada and the 10 provinces. Territories are excluded.
- Occupations: 59 NOC 2021 labels, many of them combined groups such as [11-14].
- Measures: average and median hourly and weekly wage (current dollars, not inflation adjusted), four gender wage ratios, total employees (persons in thousands).
- Replaces archived table 14-10-0340-01.
- Known break: processing changes in 2006 introduced a level shift in wage estimates. Use caution comparing before and after 2006.
- Licence: to verify (Statistics Canada terms and conditions).
- Status: inspected. Core source for the long-run wage analysis.

## Job Bank wages (Employment and Social Development Canada)

- URL: https://open.canada.ca/data/en/dataset/adad580f-76b0-4502-bd05-20c125de9116
- Content: minimum, median and maximum wage by occupation at regional level, and at provincial and national level for most occupations. One CSV per year, 2012 to 2025. The latest file is dated 2025-11-19.
- Update frequency: annual (maintenance listed as "as needed").
- Licence: Open Government Licence - Canada (verified on the dataset page).
- Status: not downloaded or inspected. Deferred. It would add a third wage concept and several yearly files that may use different NOC versions.
