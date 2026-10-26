"""Validate the processed tables in data/processed.

Run:  python src/validate_data.py
Writes docs/validation_report.txt. Exit code 1 if any check FAILS.
FAIL = a structural rule is broken.
WARN = a Phase 1 expectation or a soft consistency rule did not hold (needs a look).
"""
import sys

import pandas as pd

from config import DOCS_DIR, PROCESSED_DIR, get_logger

log = get_logger("validate_data")
pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_rows", 200)
pd.set_option("display.max_colwidth", 70)

REPORT, RESULTS = [], []

KEYS = {
    "14100444": ["period_start", "geo_id", "noc_id", "measure"],
    "14100443": ["period_start", "geo_id", "noc_id", "char_id", "measure"],
    "14100417": ["period_start", "geo_id", "noc417_code", "type_of_work", "measure"],
}
VALID_GRADES = {"A", "B", "C", "D", "E", "NONE"}
EXPECTED_NOC_LEVELS = {0: 2, 1: 10, 2: 45, 3: 89, 4: 162, 5: 516}
# Plausibility bounds in dollars per hour (assumptions, so breaches are warnings)
SANITY = {"offered_wage_avg": (5, 200), "employee_wage_avg_hourly": (5, 200),
          "employee_wage_median_hourly": (5, 200)}
# Phase 1 counts for the files downloaded on 2026-10-22
BASELINE_0444 = {"rows_with_value": 1250123, "not_available": 2775542,
                 "suppressed": 268982, "unreliable": 1723849}
# Non-overlapping members of each 0443 dimension, and the dimension total
SETS = {"Type of work": [2, 3], "Education": [5, 6, 7, 10, 12, 13],
        "Experience": [18, 19, 20, 21, 22], "Type of position": [31, 32],
        "Continuity of recruitment": [48, 49]}
TOTAL_ID = {"Type of work": 1, "Education": 4, "Experience": 17,
            "Type of position": 30, "Continuity of recruitment": 47}


def say(text=""):
    print(text)
    REPORT.append(str(text))


def check(ok, name, detail="", level="FAIL"):
    status = "PASS" if bool(ok) else level
    RESULTS.append(status)
    say(f"[{status}] {name}" + (f": {detail}" if detail else ""))


def read_fact(table_id, **dtypes):
    return pd.read_csv(PROCESSED_DIR / f"fact_{table_id}.csv", dtype=dtypes or None,
                       keep_default_na=False, na_values=[""])


# ---------------------------------------------------------------- dimensions
def check_dimensions(geo, noc, char, cross):
    say("=== DIMENSION TABLES ===")
    check(geo["geo_id"].is_unique, "dim_geography: geo_id is unique")
    check(len(geo) == 83, "dim_geography: 83 geographies", f"found {len(geo)}", "WARN")
    parents = geo["parent_geo_id"].dropna()
    check(parents.isin(geo["geo_id"]).all(), "dim_geography: parents exist")
    levels = geo["geo_level"].value_counts().to_dict()
    check(levels == {"Economic region": 69, "Province/territory": 13, "Canada": 1},
          "dim_geography: 1 Canada, 13 provinces/territories, 69 economic regions", str(levels), "WARN")

    check(noc["noc_id"].is_unique, "dim_occupation: noc_id is unique")
    counts = noc["noc_level"].value_counts().sort_index().to_dict()
    check(counts == EXPECTED_NOC_LEVELS, "dim_occupation: level counts match NOC 2021", str(counts))
    check(noc["parent_noc_id"].dropna().isin(noc["noc_id"]).all(), "dim_occupation: parents exist")
    codes = noc.loc[noc["noc_code"].notna(), "noc_code"]
    check(codes.is_unique, "dim_occupation: occupation codes are unique")

    check(char["char_id"].is_unique, "dim_characteristic: char_id is unique")
    check(len(char) == 48, "dim_characteristic: 48 members", f"found {len(char)}", "WARN")
    check(char["parent_char_id"].dropna().isin(char["char_id"]).all(),
          "dim_characteristic: parents exist")
    check(cross["noc417_code"].is_unique, "dim_occupation_0417: codes are unique")


# ------------------------------------------------------------- generic checks
def check_fact_basics(table_id, fact):
    say(f"\n--- {table_id}: structure and values ---")
    check(len(fact) > 0, f"{table_id}: fact table is not empty", f"{len(fact):,} rows")
    dups = int(fact.duplicated(KEYS[table_id]).sum())
    check(dups == 0, f"{table_id}: composite key is unique", f"{dups:,} duplicates on {KEYS[table_id]}")
    check(not fact["value"].isna().any(), f"{table_id}: no missing values in the fact table")
    check((fact["value"] >= 0).all(), f"{table_id}: no negative values")
    bad = ~fact["quality_grade"].isin(VALID_GRADES)
    check(not bad.any(), f"{table_id}: quality grades are valid",
          str(sorted(fact.loc[bad, "quality_grade"].unique())))
    has_flags = {"is_suspect", "suspect_reason"} <= set(fact.columns)
    check(has_flags, f"{table_id}: suspect-flag columns are present")
    for measure, (lo, hi) in SANITY.items():
        mask = fact["measure"] == measure
        if has_flags and mask.any():
            values = fact.loc[mask, "value"]
            outside = (values < lo) | (values > hi)
            flagged = fact.loc[mask, "is_suspect"]
            unflagged = int((outside & ~flagged).sum())
            check(unflagged == 0,
                  f"{table_id}: {measure} values outside {lo} to {hi} are all flagged",
                  f"{int(outside.sum())} outside the bounds, {unflagged} unflagged")
            check(int(outside.sum()) == int(flagged.sum()),
                  f"{table_id}: {measure} flag count equals the out-of-range count",
                  f"{int(flagged.sum())} flagged", "WARN")
    shares = fact.loc[fact["measure"] == "vacancy_share", "value"]
    if len(shares):
        check(shares.between(0, 100).all(), f"{table_id}: vacancy_share is between 0 and 100")


def check_availability(table_id, fact, avail, row):
    say(f"\n--- {table_id}: availability and completeness ---")
    check(int(avail["n_cells"].sum()) == int(row["rows_in_scope"]),
          f"{table_id}: availability cells equal rows in scope", f"{int(row['rows_in_scope']):,}")
    n_value = int(avail.loc[avail["status_group"] == "value", "n_cells"].sum())
    check(n_value == len(fact), f"{table_id}: fact rows equal availability 'value' cells",
          f"{len(fact):,} vs {n_value:,}")
    for group in ("not_available", "suppressed", "unreliable"):
        n = int(avail.loc[avail["status_group"] == group, "n_cells"].sum())
        check(n == int(row[group]), f"{table_id}: {group} count matches the cleaning summary", f"{n:,}")
    periods = sorted(avail["period_start"].unique())
    say(f"Periods in scope: {len(periods)} ({periods[0]} to {periods[-1]})")
    if table_id != "14100417":
        check(len(periods) == 44 and "2020-04-01" not in periods and "2020-07-01" not in periods,
              f"{table_id}: 44 quarters, with Q2 and Q3 2020 absent", level="WARN")


def report_zeros_and_blank_grades(table_id, fact):
    say(f"\n--- {table_id}: true zeros and ungraded (blank STATUS) values ---")
    zeros = fact[fact["value"] == 0]
    say("Zero values by measure and grade:")
    say(zeros.groupby(["measure", "quality_grade"]).size().to_string() if len(zeros) else "none")
    none = fact[fact["quality_grade"] == "NONE"]
    say(f"Values with no quality grade (blank STATUS): {len(none):,}")
    if len(none):
        for measure, sub in none.groupby("measure"):
            say(f"  {measure}: {len(sub):,} rows, {int((sub['value'] == 0).sum()):,} zeros, "
                f"min {sub['value'].min()}, max {sub['value'].max()}, "
                f"{int((sub['value'] == 100).sum()):,} equal to 100")
    if table_id == "14100444":
        check(len(none) == 0, "14100444: no blank-STATUS values (Phase 1 expectation)", level="WARN")
    if table_id == "14100417":
        check(fact["quality_grade"].eq("NONE").all(),
              "14100417: every value is ungraded (no A to E grades in this table)", level="WARN")


# ------------------------------------------------------------------ 0443 only
def check_0443_consistency(f443):
    say("\n--- 14100443: additivity within each characteristic dimension ---")
    shares = f443[f443["measure"] == "vacancy_share"]
    counts = f443[f443["measure"] == "job_vacancies"]
    keys = ["period_start", "geo_id", "noc_id"]

    total_rows = shares[shares["char_id"].isin(TOTAL_ID.values())]
    off = int(((total_rows["value"] - 100).abs() > 0.05).sum())
    check(off == 0, "dimension totals have a share of 100", f"{len(total_rows):,} tested, {off} off", "WARN")

    for dim, members in SETS.items():
        sub = shares[shares["char_id"].isin(members)]
        grouped = sub.groupby(keys).agg(n=("value", "size"), total=("value", "sum")).reset_index()
        full = grouped[grouped["n"] == len(members)]
        dev = (full["total"] - 100).abs()
        bad = int((dev > 0.5).sum())
        check(bad == 0, f"shares sum to 100 within 0.5 points: {dim}",
              f"{len(full):,} complete sets, {bad} failures, worst deviation "
              f"{dev.max() if len(dev) else 0:.2f}", "WARN")

        tot = counts[counts["char_id"] == TOTAL_ID[dim]][keys + ["value"]].rename(
            columns={"value": "total_value"})
        csub = counts[counts["char_id"].isin(members)].groupby(keys).agg(
            n=("value", "size"), s=("value", "sum")).reset_index()
        merged = csub.merge(tot, on=keys)
        tol = 5 * (len(members) + 1)
        over = int((merged["s"] - merged["total_value"] > tol).sum())
        complete = merged[merged["n"] == len(members)]
        off_c = int(((complete["s"] - complete["total_value"]).abs() > tol).sum())
        check(over == 0 and off_c == 0, f"counts add up to the total within {tol}: {dim}",
              f"{len(merged):,} tested, {over} exceed the total, "
              f"{off_c} of {len(complete):,} complete sets differ", "WARN")

    say("\n--- 14100443: first and last quarter with data, per characteristic "
        "(Canada, all occupations, job vacancies) ---")


def report_char_history(f443, char):
    sub = f443[(f443["geo_id"] == 1) & (f443["noc_id"] == 1) & (f443["measure"] == "job_vacancies")]
    hist = sub.groupby("char_id").agg(first=("period_start", "min"), last=("period_start", "max"),
                                      quarters=("period_start", "nunique"))
    table = char.set_index("char_id")[["dimension", "char_title"]].join(hist, how="inner")
    say(table.to_string())


# ------------------------------------------------------------------ 0444 only
def check_additivity(name, df, id_col, parents, group_keys):
    """df has group_keys, id_col and value. parents has id_col and parent."""
    kids = df.merge(parents, on=id_col)
    agg = kids.groupby(group_keys + ["parent"]).agg(
        child_sum=("value", "sum"), n=("value", "size")).reset_index()
    par = df[group_keys + [id_col, "value"]].rename(columns={id_col: "parent", "value": "parent_value"})
    merged = agg.merge(par, on=group_keys + ["parent"])
    merged["excess"] = merged["child_sum"] - merged["parent_value"]
    bad = merged[merged["excess"] > 5 * (merged["n"] + 1)]
    check(len(bad) == 0, f"{name}: published children never exceed the parent",
          f"{len(merged):,} parent cells tested, {len(bad):,} violations, "
          f"worst excess {merged['excess'].max() if len(merged) else 0}", "WARN")
    if len(bad):
        say(bad.sort_values("excess", ascending=False).head(5).to_string(index=False))


def check_0444_hierarchy(f444, geo, noc):
    say("\n--- 14100444: hierarchy additivity (job vacancies) ---")
    vac = f444[f444["measure"] == "job_vacancies"][["period_start", "geo_id", "noc_id", "value"]]
    noc_parents = noc[["noc_id", "parent_noc_id"]].dropna().astype(int).rename(
        columns={"parent_noc_id": "parent"})
    check_additivity("occupation hierarchy", vac, "noc_id", noc_parents, ["period_start", "geo_id"])
    total_occ = vac[vac["noc_id"] == 1][["period_start", "geo_id", "value"]]
    geo_parents = geo[["geo_id", "parent_geo_id"]].dropna().astype(int).rename(
        columns={"parent_geo_id": "parent"})
    check_additivity("geography hierarchy (all occupations)", total_occ, "geo_id",
                     geo_parents, ["period_start"])


def check_cross_table(f444, f443):
    say("\n--- Cross-table reconciliation: 0444 vs 0443 (all occupations, same geography and quarter) ---")
    measures = ["job_vacancies", "offered_wage_avg"]
    a = f444[(f444["geo_id"] <= 14) & (f444["noc_id"] == 1) & f444["measure"].isin(measures)][
        ["period_start", "geo_id", "measure", "value"]]
    b = f443[(f443["char_id"] == 1) & (f443["noc_id"] == 1) & f443["measure"].isin(measures)][
        ["period_start", "geo_id", "measure", "value"]]
    m = a.merge(b, on=["period_start", "geo_id", "measure"], suffixes=("_0444", "_0443"))
    m["diff"] = (m["value_0444"] - m["value_0443"]).abs()
    for measure, tol in (("job_vacancies", 5), ("offered_wage_avg", 0.05)):
        s = m[m["measure"] == measure]
        bad = s[s["diff"] > tol]
        check(len(bad) == 0, f"0444 and 0443 agree on {measure} (tolerance {tol})",
              f"{len(s):,} pairs compared, {len(bad):,} differ, max difference "
              f"{s['diff'].max() if len(s) else 0}", "WARN")
        if len(bad):
            say(bad.sort_values("diff", ascending=False).head(5).to_string(index=False))


# ----------------------------------------------------------------------- main
def main():
    geo = pd.read_csv(PROCESSED_DIR / "dim_geography.csv", dtype={"sgc_code": str})
    noc = pd.read_csv(PROCESSED_DIR / "dim_occupation.csv", dtype={"noc_code": str})
    char = pd.read_csv(PROCESSED_DIR / "dim_characteristic.csv")
    cross = pd.read_csv(PROCESSED_DIR / "dim_occupation_0417.csv", dtype={"noc417_code": str})
    summary = (pd.read_csv(PROCESSED_DIR / "cleaning_summary.csv", dtype={"table_id": str})
               .drop_duplicates("table_id", keep="last").set_index("table_id"))

    check_dimensions(geo, noc, char, cross)
    say("\n=== FACT TABLES ===")

    f444 = read_fact("14100444")
    check_fact_basics("14100444", f444)
    avail = pd.read_csv(PROCESSED_DIR / "availability_14100444.csv")
    check_availability("14100444", f444, avail, summary.loc["14100444"])
    for key, expected in BASELINE_0444.items():
        actual = len(f444) if key == "rows_with_value" else int(summary.loc["14100444", key])
        check(actual == expected, f"14100444: matches Phase 1 count for {key}", f"{actual:,}", "WARN")
    grid = len(geo) * len(noc) * avail["period_start"].nunique() * avail["measure"].nunique()
    check(grid == int(avail["n_cells"].sum()), "14100444: availability covers the full grid",
          f"expected {grid:,}", "WARN")
    check(f444["geo_id"].isin(geo["geo_id"]).all(), "14100444: all geo_id exist in dim_geography")
    check(f444["noc_id"].isin(noc["noc_id"]).all(), "14100444: all noc_id exist in dim_occupation")
    report_zeros_and_blank_grades("14100444", f444)
    check_0444_hierarchy(f444, geo, noc)

    f443 = read_fact("14100443")
    check_fact_basics("14100443", f443)
    avail = pd.read_csv(PROCESSED_DIR / "availability_14100443.csv")
    check_availability("14100443", f443, avail, summary.loc["14100443"])
    grid = (avail["char_id"].nunique() * int((noc["noc_level"] <= 3).sum()) * avail["geo_id"].nunique()
            * avail["period_start"].nunique() * avail["measure"].nunique())
    check(grid == int(avail["n_cells"].sum()), "14100443: availability covers the full in-scope grid",
          f"expected {grid:,}", "WARN")
    check(f443["geo_id"].isin(geo["geo_id"]).all(), "14100443: all geo_id exist in dim_geography")
    check(f443["noc_id"].isin(noc["noc_id"]).all(), "14100443: all noc_id exist in dim_occupation")
    check(f443["char_id"].isin(char["char_id"]).all(), "14100443: all char_id exist in dim_characteristic")
    report_zeros_and_blank_grades("14100443", f443)
    check_0443_consistency(f443)
    report_char_history(f443, char)
    check_cross_table(f444, f443)
    del f443, f444

    f417 = read_fact("14100417", noc417_code=str)
    check_fact_basics("14100417", f417)
    avail = pd.read_csv(PROCESSED_DIR / "availability_14100417.csv")
    check_availability("14100417", f417, avail, summary.loc["14100417"])
    grid = (avail["geo_id"].nunique() * len(cross) * avail["period_start"].nunique()
            * avail["measure"].nunique() * avail["type_of_work"].nunique())
    check(grid == int(avail["n_cells"].sum()), "14100417: availability covers the full in-scope grid",
          f"expected {grid:,}", "WARN")
    check(f417["geo_id"].isin(geo.loc[geo["geo_id"] <= 11, "geo_id"]).all(),
          "14100417: geographies are Canada and provinces only")
    check(f417["noc417_code"].isin(cross["noc417_code"]).all(),
          "14100417: all occupation codes exist in the crosswalk")
    report_zeros_and_blank_grades("14100417", f417)

    n_fail, n_warn, n_pass = (RESULTS.count(x) for x in ("FAIL", "WARN", "PASS"))
    say(f"\nSUMMARY: {n_pass} passed, {n_warn} warnings, {n_fail} failed")
    (DOCS_DIR / "validation_report.txt").write_text("\n".join(REPORT), encoding="utf-8")
    log.info("Validation finished: %d passed, %d warnings, %d failed", n_pass, n_warn, n_fail)
    sys.exit(1 if n_fail else 0)


if __name__ == "__main__":
    main()