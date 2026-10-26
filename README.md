# CareerScope: Canadian Labour Market Analytics

An end-to-end analytics project that compares Canadian occupations using official Statistics Canada data: offered wages, job vacancies, employee wages and job characteristics. It provides descriptive evidence for career exploration. It does not predict salaries or hiring.

**Status:** the data pipeline, SQL Server database, validation, exploratory analysis and quality-rule sensitivity analysis are complete. The Power BI report is in progress.

## Pipeline

Statistics Canada tables -> Python download check -> cleaning and validation -> SQL Server (schemas dim, fact, rpt) -> SQL checks, views and queries -> analysis -> Power BI (in progress)

## Skills demonstrated

Python (pandas, SciPy, pyodbc), T-SQL and SQL Server (normalized schema, constraints, indexes, views, window functions, CTEs), PowerShell automation, data validation and reconciliation across tools, Git, technical documentation.

## Data sources

- Table 14-10-0444-01, job vacancies and average offered hourly wage by occupation, quarterly: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410044401
- Table 14-10-0443-01, job vacancies by occupation and selected characteristics, quarterly: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410044301
- Table 14-10-0417-01, employee wages by occupation, annual: https://www150.statcan.gc.ca/t1/tbl1/en/tv.action?pid=1410041701

Contains information licensed under the Statistics Canada Open Licence. This project is not endorsed by Statistics Canada. The data files are large and are not stored in this repository.

## Repository

- `src/`: Python modules for download checks, cleaning, validation, loading and analysis
- `sql/`: database, tables, indexes, data-quality checks, reporting views and analytical queries
- `notebooks/`: exploratory analysis
- `docs/`: findings, data dictionary, validation reports, figures and data-discovery notes

## Reproduce

1. Install Python 3.13, SQL Server (tested on 2025 Developer edition) and ODBC Driver 18 for SQL Server.
2. `pip install -r requirements.txt`
3. `python src/download_data.py`, then `python src/clean_data.py`, then `python src/validate_data.py`
4. Run `sql/01_create_database.sql` and `sql/02_create_tables.sql`, then `python src/load_database.py`
5. Run `sql/02b_create_indexes.sql`, `03_data_quality_checks.sql`, `04_reporting_views.sql` and `05_analytical_queries.sql`
6. `python src/analysis_01_quality_rule.py` and `python src/analysis_02_matched_trends.py`

## Selected findings (details and caveats in `docs/findings.md`)

- Canada, all occupations, 2026 Q2: 548,400 reported vacancies and an average offered wage of $28.55.
- Across 312 unit groups with reliable values, offered wage and vacancy counts have a weak negative rank correlation (-0.27). Its size depends on the quality rule used.
- Coverage is the main limit: only about a third of wage cells and a sixth of vacancy cells carry a published value, so every ranking reports how many occupations stand behind it.

## Limitations

Offered wages are advertised minimums, not actual pay. Vacancy counts are reported vacancies, not total jobs or hiring chances. Employee wages and offered wages are different measures and are never combined.
