"""Load the processed tables into the CareerScope SQL Server database.

Run:  python src/load_database.py

Prerequisites: sql/01_create_database.sql and sql/02_create_tables.sql have been run.
The script refuses to load into tables that already contain rows. To reload from
scratch, rerun sql/02_create_tables.sql, which drops and rebuilds every table.

The connection uses Windows authentication on localhost. To use another server, set
the environment variable CAREERSCOPE_ODBC to a full ODBC connection string.
"""
import os
import sys
from datetime import date

import pandas as pd

from config import PROCESSED_DIR, get_logger

log = get_logger("load_database")

BATCH = 50_000
CONNECTION = os.environ.get("CAREERSCOPE_ODBC") or (
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=CareerScope;"
    "Trusted_Connection=yes;TrustServerCertificate=yes;")

DATA_TABLES = [
    "dim.period", "dim.geography", "dim.occupation", "dim.characteristic", "dim.occupation_0417",
    "fact.vacancy_0444", "fact.offered_wage_0444",
    "fact.char_vacancy_0443", "fact.char_vacancy_share_0443", "fact.char_offered_wage_0443",
    "fact.employee_wage_0417", "fact.employee_count_0417",
    "fact.availability_0444", "fact.availability_0443", "fact.availability_0417"]

# Tables whose rows must add up to the counts recorded by clean_data.py
FACT_GROUPS = {
    "14100444": ["fact.vacancy_0444", "fact.offered_wage_0444"],
    "14100443": ["fact.char_vacancy_0443", "fact.char_vacancy_share_0443", "fact.char_offered_wage_0443"],
    "14100417": ["fact.employee_wage_0417", "fact.employee_count_0417"]}
AVAILABILITY = {"14100444": "fact.availability_0444", "14100443": "fact.availability_0443",
                "14100417": "fact.availability_0417"}


# ------------------------------------------------------------------ helpers
def read(name, **kwargs):
    return pd.read_csv(PROCESSED_DIR / name, keep_default_na=False, na_values=[""],
                       low_memory=False, **kwargs)


def to_rows(df):
    """DataFrame to a list of plain-Python tuples, with missing values as None."""
    objects = df.astype(object)
    objects = objects.where(df.notna(), None)
    return list(objects.itertuples(index=False, name=None))


def as_int(series, name):
    rounded = series.round()
    if not (series == rounded).all():
        raise ValueError(f"{name}: found values that are not whole numbers")
    return rounded.astype("int64")


class Loader:
    def __init__(self, conn):
        self.conn = conn
        self.loaded = {}
        self.period_ids = {}

    def insert(self, table, df, columns):
        rows = to_rows(df[columns])
        sql = (f"INSERT INTO {table} ({', '.join(columns)}) "
               f"VALUES ({', '.join(['?'] * len(columns))})")
        cur = self.conn.cursor()
        cur.fast_executemany = True
        for start in range(0, len(rows), BATCH):
            cur.executemany(sql, rows[start:start + BATCH])
        self.conn.commit()
        cur.close()
        self.loaded[table] = self.loaded.get(table, 0) + len(rows)
        log.info("Loaded %s rows into %s", f"{len(rows):,}", table)

    def scalar(self, sql):
        cur = self.conn.cursor()
        cur.execute(sql)
        value = cur.fetchone()[0]
        cur.close()
        return value

    def check_empty(self):
        busy = {t: self.scalar(f"SELECT COUNT_BIG(*) FROM {t}") for t in DATA_TABLES}
        busy = {t: n for t, n in busy.items() if n}
        if busy:
            raise RuntimeError(
                "These tables already contain rows: " + ", ".join(f"{t} ({n:,})" for t, n in busy.items())
                + ". Rerun sql/02_create_tables.sql to rebuild the empty tables, then run this script again.")

    # ------------------------------------------------------------ dimensions
    def load_periods(self, quarters, years):
        rows = []
        for text in sorted(quarters):
            d = date.fromisoformat(text)
            q = (d.month - 1) // 3 + 1
            rows.append(("quarter", d, d.year, q, f"{d.year}Q{q}"))
        for text in sorted(years):
            d = date.fromisoformat(text)
            rows.append(("year", d, d.year, None, str(d.year)))
        cur = self.conn.cursor()
        cur.executemany("INSERT INTO dim.period (period_type, period_start, period_year, period_quarter, "
                        "period_label) VALUES (?, ?, ?, ?, ?)", rows)
        self.conn.commit()
        cur.execute("SELECT period_id, period_type, period_start FROM dim.period")
        for period_id, period_type, start in cur.fetchall():
            self.period_ids.setdefault(period_type, {})[start.isoformat()] = int(period_id)
        cur.close()
        self.loaded["dim.period"] = len(rows)
        log.info("Loaded %d rows into dim.period (%d quarters, %d years)", len(rows), len(quarters), len(years))

    def with_period(self, df, kind, label):
        out = df.copy()
        out["period_id"] = out["period_start"].map(self.period_ids[kind])
        if out["period_id"].isna().any():
            raise ValueError(f"{label}: some periods are missing from dim.period")
        out["period_id"] = out["period_id"].astype("int64")
        return out

    def load_dimensions(self):
        geo = read("dim_geography.csv", dtype={"sgc_code": str}).sort_values("geo_id")
        self.insert("dim.geography", geo, ["geo_id", "geo_name", "sgc_code", "parent_geo_id",
                                           "province_geo_id", "geo_level", "is_combined_region"])
        noc = read("dim_occupation.csv", dtype={"noc_code": str}).sort_values(["noc_level", "noc_id"])
        self.insert("dim.occupation", noc, ["noc_id", "noc_code", "noc_level", "noc_level_name", "noc_title",
                                            "parent_noc_id", "is_total", "is_unclassified"])
        char = read("dim_characteristic.csv").sort_values("char_id")
        self.insert("dim.characteristic", char, ["char_id", "char_title", "parent_char_id", "root_char_id",
                                                 "dimension", "is_dimension_total", "is_terminated",
                                                 "analysis_scope"])
        cross = read("dim_occupation_0417.csv", dtype={"noc417_code": str})
        self.insert("dim.occupation_0417", cross, ["noc417_code", "noc417_label", "kind", "noc_id_0444",
                                                   "name_matches_0444"])

    # ----------------------------------------------------------------- facts
    def load_0444(self):
        f = self.with_period(read("fact_14100444.csv"), "quarter", "0444")
        unknown = set(f["measure"]) - {"job_vacancies", "offered_wage_avg"}
        if unknown:
            raise ValueError(f"0444: unexpected measures {unknown}")
        vac = f[f["measure"] == "job_vacancies"].copy()
        vac["vacancies"] = as_int(vac["value"], "0444 vacancies")
        self.insert("fact.vacancy_0444", vac, ["period_id", "geo_id", "noc_id", "vacancies", "quality_grade"])
        wage = f[f["measure"] == "offered_wage_avg"].copy()
        wage["offered_wage"] = wage["value"].round(2)
        self.insert("fact.offered_wage_0444", wage, ["period_id", "geo_id", "noc_id", "offered_wage",
                                                     "quality_grade", "is_suspect", "suspect_reason"])

    def load_0443(self):
        f = self.with_period(read("fact_14100443.csv"), "quarter", "0443")
        unknown = set(f["measure"]) - {"job_vacancies", "vacancy_share", "offered_wage_avg"}
        if unknown:
            raise ValueError(f"0443: unexpected measures {unknown}")
        key = ["period_id", "geo_id", "noc_id", "char_id"]
        vac = f[f["measure"] == "job_vacancies"].copy()
        vac["vacancies"] = as_int(vac["value"], "0443 vacancies")
        self.insert("fact.char_vacancy_0443", vac, key + ["vacancies", "quality_grade"])
        share = f[f["measure"] == "vacancy_share"].copy()
        share["vacancy_share"] = share["value"].round(1)
        self.insert("fact.char_vacancy_share_0443", share, key + ["vacancy_share", "quality_grade"])
        wage = f[f["measure"] == "offered_wage_avg"].copy()
        wage["offered_wage"] = wage["value"].round(2)
        self.insert("fact.char_offered_wage_0443", wage, key + ["offered_wage", "quality_grade",
                                                                "is_suspect", "suspect_reason"])

    def load_0417(self):
        f = self.with_period(read("fact_14100417.csv", dtype={"noc417_code": str}), "year", "0417")
        wage_keys = {"employee_wage_avg_hourly", "employee_wage_median_hourly"}
        unknown = set(f["measure"]) - wage_keys - {"employee_count"}
        if unknown:
            raise ValueError(f"0417: unexpected measures {unknown}")
        key = ["period_id", "geo_id", "noc417_code", "type_of_work"]
        wage = f[f["measure"].isin(wage_keys)].copy()
        wage["measure_key"] = wage["measure"]
        wage["hourly_wage"] = wage["value"].round(2)
        self.insert("fact.employee_wage_0417", wage, key + ["measure_key", "hourly_wage",
                                                           "is_suspect", "suspect_reason"])
        count = f[f["measure"] == "employee_count"].copy()
        count["employees_thousands"] = count["value"].round(1)
        self.insert("fact.employee_count_0417", count, key + ["employees_thousands"])

    def load_availability(self):
        specs = {
            "14100444": ("fact.availability_0444", "quarter",
                         ["period_id", "geo_id", "noc_level", "measure_key", "status_group", "n_cells"]),
            "14100443": ("fact.availability_0443", "quarter",
                         ["period_id", "geo_id", "noc_level", "char_id", "measure_key", "status_group", "n_cells"]),
            "14100417": ("fact.availability_0417", "year",
                         ["period_id", "geo_id", "type_of_work", "measure_key", "status_group", "n_cells"])}
        for table_id, (table, kind, columns) in specs.items():
            a = self.with_period(read(f"availability_{table_id}.csv"), kind, table)
            a = a.rename(columns={"measure": "measure_key"})
            self.insert(table, a, columns)

    # ---------------------------------------------------------- verification
    def verify(self):
        log.info("Verifying row counts against the cleaning summary")
        summary = (pd.read_csv(PROCESSED_DIR / "cleaning_summary.csv", dtype={"table_id": str})
                   .drop_duplicates("table_id", keep="last").set_index("table_id"))
        problems = []
        for table in DATA_TABLES:
            in_db = int(self.scalar(f"SELECT COUNT_BIG(*) FROM {table}"))
            if in_db != self.loaded[table]:
                problems.append(f"{table}: {in_db:,} rows in the database, {self.loaded[table]:,} loaded")
        for table_id, tables in FACT_GROUPS.items():
            total = sum(int(self.scalar(f"SELECT COUNT_BIG(*) FROM {t}")) for t in tables)
            expected = int(summary.loc[table_id, "rows_with_value"])
            status = "OK" if total == expected else "MISMATCH"
            log.info("[%s] fact rows in SQL %s, expected %s: %s", table_id, f"{total:,}", f"{expected:,}", status)
            if total != expected:
                problems.append(f"{table_id}: {total:,} fact rows, expected {expected:,}")
            cells = int(self.scalar(f"SELECT COALESCE(SUM(CAST(n_cells AS BIGINT)), 0) FROM {AVAILABILITY[table_id]}"))
            expected_cells = int(summary.loc[table_id, "rows_in_scope"])
            status = "OK" if cells == expected_cells else "MISMATCH"
            log.info("[%s] availability cells in SQL %s, expected %s: %s",
                     table_id, f"{cells:,}", f"{expected_cells:,}", status)
            if cells != expected_cells:
                problems.append(f"{table_id}: {cells:,} availability cells, expected {expected_cells:,}")
        return problems


def connect():
    import pyodbc
    return pyodbc.connect(CONNECTION, autocommit=False)


def main():
    conn = None
    try:
        conn = connect()
        loader = Loader(conn)
        loader.check_empty()
        quarters = (set(read("availability_14100444.csv")["period_start"])
                    | set(read("availability_14100443.csv")["period_start"]))
        years = set(read("availability_14100417.csv")["period_start"])
        loader.load_periods(quarters, years)
        loader.load_dimensions()
        loader.load_0444()
        loader.load_0443()
        loader.load_0417()
        loader.load_availability()
        problems = loader.verify()
    except Exception as error:
        log.exception("Load stopped: %s", error)
        if conn is not None:
            conn.rollback()
        sys.exit(1)
    finally:
        if conn is not None:
            conn.close()

    if problems:
        for problem in problems:
            log.error("Check failed: %s", problem)
        sys.exit(1)
    log.info("Load finished: all row counts match")


if __name__ == "__main__":
    main()