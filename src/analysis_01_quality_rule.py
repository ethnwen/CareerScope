"""Step 4.1: how sensitive are the rankings and coverage to the quality rule (decision D1)?

Reads the reporting views in SQL Server, so run the SQL steps first.
Run:  python src/analysis_01_quality_rule.py
Writes docs/sensitivity_quality_rule.txt

Three rules are compared for the latest quarter:
  strict  = grades A to C
  current = grades A to D (the project rule)
  loose   = grades A to E
Values with no grade (exact zeros and totals) always count as reliable, and values
flagged as suspect never do. The rule changes which groups are included, not their values.
"""
import numpy as np
import pandas as pd
from scipy import stats

from config import DOCS_DIR
from db import query_df

pd.set_option("display.width", 200)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 70)

RULES = {
    "strict (A to C)": {"A", "B", "C", "NONE"},
    "current (A to D)": {"A", "B", "C", "D", "NONE"},
    "loose (A to E)": {"A", "B", "C", "D", "E", "NONE"},
}
SHORT = {"strict (A to C)": "A-C", "current (A to D)": "A-D", "loose (A to E)": "A-E"}
CURRENT = "current (A to D)"
LOOSE = "loose (A to E)"
THRESHOLD = 50.0   # decision D10: share of groups with a value that counts as well covered

DATA_SQL = """
SELECT g.geo_name, o.noc_code, o.noc_title, o.noc_level,
       x.vacancies, x.vacancy_grade, x.offered_wage, x.wage_grade, x.wage_is_suspect
FROM rpt.vw_occupation_geo_period AS x
JOIN rpt.vw_latest_quarter AS lq ON lq.period_id = x.period_id
JOIN dim.geography AS g ON g.geo_id = x.geo_id
JOIN dim.occupation AS o ON o.noc_id = x.noc_id
WHERE g.geo_level IN ('Canada', 'Province/territory') AND o.noc_level BETWEEN 1 AND 5
"""
SIZE_SQL = """
SELECT noc_level, COUNT(*) AS n_groups
FROM dim.occupation
WHERE noc_level BETWEEN 1 AND 5
GROUP BY noc_level
"""
PERIOD_SQL = "SELECT period_label FROM rpt.vw_latest_quarter"

LINES = []


def out(text=""):
    print(text)
    LINES.append(str(text))


def load():
    data = query_df(DATA_SQL)
    for column in ("vacancies", "offered_wage"):
        data[column] = pd.to_numeric(data[column])
    data["wage_is_suspect"] = data["wage_is_suspect"].map(lambda v: bool(v) if v is not None and v == v else False)
    sizes = query_df(SIZE_SQL).set_index("noc_level")["n_groups"].astype(int)
    label = str(query_df(PERIOD_SQL).iloc[0, 0])
    return data, sizes, label


def wage_ok(frame, grades):
    return frame["offered_wage"].notna() & frame["wage_grade"].isin(grades) & ~frame["wage_is_suspect"]


def vac_ok(frame, grades):
    return frame["vacancies"].notna() & frame["vacancy_grade"].isin(grades)


def coverage(data, sizes, level):
    rows = []
    for geo, frame in data[data["noc_level"] == level].groupby("geo_name"):
        row = {"geography": geo}
        for rule, grades in RULES.items():
            row[f"wage {SHORT[rule]}"] = 100 * wage_ok(frame, grades).sum() / sizes[level]
        for rule, grades in RULES.items():
            row[f"vac {SHORT[rule]}"] = 100 * vac_ok(frame, grades).sum() / sizes[level]
        rows.append(row)
    table = pd.DataFrame(rows).set_index("geography").round(1)
    return table.sort_values("wage A-D", ascending=False)


def coverage_section(data, sizes):
    for level, label in ((2, "major groups"), (5, "unit groups")):
        table = coverage(data, sizes, level)
        out(f"\nCoverage at the {label} level: percent of the {sizes[level]} groups with a usable value")
        out(table.to_string())
        for measure in ("wage", "vac"):
            for short in SHORT.values():
                meets = list(table.index[table[f"{measure} {short}"] >= THRESHOLD])
                out(f"  {measure} {short}: {len(meets)} geographies reach {THRESHOLD:.0f}%: {', '.join(meets)}")


def ranking_section(data):
    can = data[(data["geo_name"] == "Canada") & (data["noc_level"] == 5)].copy()
    out("\nCanada, unit groups: effect of the rule on what is included and on the wage-vacancy correlation")
    tops, rows = {}, []
    for rule, grades in RULES.items():
        w, v = wage_ok(can, grades), vac_ok(can, grades)
        both = can[w & v & (can["vacancies"] > 0)]
        rho = float(stats.spearmanr(both["vacancies"], both["offered_wage"])[0]) if len(both) > 2 else np.nan
        rows.append({"rule": rule, "groups with wage": int(w.sum()), "groups with vacancies": int(v.sum()),
                     "groups with both": len(both), "spearman rho": round(rho, 2)})
        tops[(rule, "wage")] = can[w].sort_values(["offered_wage", "noc_code"], ascending=[False, True]).head(10)
        tops[(rule, "vac")] = can[v].sort_values(["vacancies", "noc_code"], ascending=[False, True]).head(10)
    table = pd.DataFrame(rows).set_index("rule")
    out(table.to_string())
    current = table.loc[CURRENT]
    matches = current["groups with both"] == 312 and current["spearman rho"] == -0.27
    out(f"Check against the notebook and SQL result (312 groups, rho -0.27): "
        f"{'MATCHES' if matches else 'DIFFERS, investigate before using these results'}")

    for kind, column, grade, title in (("wage", "offered_wage", "wage_grade", "offered wage"),
                                       ("vac", "vacancies", "vacancy_grade", "vacancies")):
        base = set(tops[(CURRENT, kind)]["noc_code"])
        out(f"\nTop 10 unit groups by {title}: overlap with the current rule")
        for rule in RULES:
            if rule == CURRENT:
                continue
            other = tops[(rule, kind)]
            out(f"  {rule}: {len(base & set(other['noc_code']))} of 10 are the same")
            entrants = other[~other["noc_code"].isin(base)]
            if len(entrants):
                out("  Groups in this top 10 but not in the current top 10:")
                out(entrants[["noc_code", "noc_title", column, grade]].to_string(index=False))

    out("\nGroups that only appear when grade E is allowed")
    for kind, column, label in (("wage", "offered_wage", "offered wage"), ("vac", "vacancies", "vacancy")):
        ok = wage_ok if kind == "wage" else vac_ok
        loose = can[ok(can, RULES[LOOSE])]
        current_rows = can[ok(can, RULES[CURRENT])]
        only_e = loose[~loose.index.isin(current_rows.index)]
        share = 100 * only_e[column].sum() / loose[column].sum() if kind == "vac" else np.nan
        text = f"  {label}: {len(only_e)} of {len(loose)} usable unit groups are grade E only"
        if kind == "vac":
            text += f"; they hold {only_e[column].sum():,.0f} vacancies, {share:.1f}% of the vacancy total in the loose set"
        out(text)


def main():
    data, sizes, label = load()
    out(f"Step 4.1: sensitivity to the quality rule. Latest quarter: {label}")
    out(f"Rows read: {len(data):,}. Occupation groups per level: {sizes.to_dict()}")
    coverage_section(data, sizes)
    ranking_section(data)
    (DOCS_DIR / "sensitivity_quality_rule.txt").write_text("\n".join(LINES), encoding="utf-8")
    out("\nSaved docs/sensitivity_quality_rule.txt")


if __name__ == "__main__":
    main()