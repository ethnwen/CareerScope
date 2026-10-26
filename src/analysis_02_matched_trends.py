"""Step 4.2: matched-panel trends (like-for-like comparisons between quarters).

Only occupation groups with a reliable value in BOTH quarters are compared, so changing
coverage cannot masquerade as change. Reliable = grades A to D or ungraded, not suspect.
Run:  python src/analysis_02_matched_trends.py
Writes docs/matched_panel_trends.txt
"""
import numpy as np
import pandas as pd
from scipy import stats

from config import DOCS_DIR
from db import query_df

pd.set_option("display.width", 220)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 60)

GRADES = {"A", "B", "C", "D", "NONE"}
MIN_BASE_VACANCIES = 200   # assumption: ignore percent changes from a smaller starting count
FIVE = ["Canada", "Ontario", "Quebec", "British Columbia", "Alberta"]
COMPARISONS = [
    # (title, base quarter, new quarter, occupation level, geographies)
    ("Year over year, unit groups", "2025Q2", "2026Q2", 5, ["Canada"]),
    ("Year over year, major groups", "2025Q2", "2026Q2", 2, FIVE),
    ("Peak to latest, major groups", "2022Q2", "2026Q2", 2, FIVE),
]
LABELS = sorted({q for c in COMPARISONS for q in (c[1], c[2])})
LEVEL_NAMES = {2: "major groups", 5: "unit groups"}

DATA_SQL = f"""
SELECT g.geo_name, o.noc_code, o.noc_title, o.noc_level, p.period_label,
       x.vacancies, x.vacancy_grade, x.offered_wage, x.wage_grade, x.wage_is_suspect
FROM rpt.vw_occupation_geo_period AS x
JOIN dim.period AS p ON p.period_id = x.period_id AND p.period_type = 'quarter'
JOIN dim.geography AS g ON g.geo_id = x.geo_id
JOIN dim.occupation AS o ON o.noc_id = x.noc_id
WHERE g.geo_level IN ('Canada', 'Province/territory') AND o.noc_level IN (2, 5)
  AND p.period_label IN ({", ".join("'" + q + "'" for q in LABELS)})
"""
TOTAL_SQL = f"""
SELECT period_label, vacancies, offered_wage
FROM rpt.vw_national_trend
WHERE period_label IN ({", ".join("'" + q + "'" for q in LABELS)})
"""
SIZE_SQL = "SELECT noc_level, COUNT(*) AS n_groups FROM dim.occupation WHERE noc_level IN (2, 5) GROUP BY noc_level"

LINES = []


def out(text=""):
    print(text)
    LINES.append(str(text))


def load():
    data = query_df(DATA_SQL)
    for column in ("vacancies", "offered_wage"):
        data[column] = pd.to_numeric(data[column])
    data["wage_is_suspect"] = data["wage_is_suspect"].map(lambda v: bool(v) if v is not None and v == v else False)
    data["wage_ok"] = data["offered_wage"].notna() & data["wage_grade"].isin(GRADES) & ~data["wage_is_suspect"]
    data["vac_ok"] = data["vacancies"].notna() & data["vacancy_grade"].isin(GRADES)
    totals = query_df(TOTAL_SQL)
    for column in ("vacancies", "offered_wage"):
        totals[column] = pd.to_numeric(totals[column])
    sizes = query_df(SIZE_SQL).set_index("noc_level")["n_groups"].astype(int)
    return data, totals.set_index("period_label"), sizes


def matched(data, geo, level, base, new, measure):
    value, ok = ("offered_wage", "wage_ok") if measure == "wage" else ("vacancies", "vac_ok")
    sub = data[(data["geo_name"] == geo) & (data["noc_level"] == level) & data[ok]]
    a = sub[sub["period_label"] == base][["noc_code", "noc_title", value]]
    b = sub[sub["period_label"] == new][["noc_code", value]]
    m = a.merge(b, on="noc_code", suffixes=("_base", "_new"))
    m = m.rename(columns={f"{value}_base": "base", f"{value}_new": "new"})
    floor = MIN_BASE_VACANCIES if measure == "vac" else 0
    m = m[m["base"] > floor].copy()
    m["change"] = m["new"] - m["base"]
    m["pct_change"] = 100 * m["change"] / m["base"]
    return m


def summarize(m, size):
    if m.empty:
        return {"matched groups": 0}
    return {"matched groups": len(m), "share of groups": round(100 * len(m) / size, 1),
            "median % change": round(m["pct_change"].median(), 1),
            "25th pct": round(m["pct_change"].quantile(0.25), 1),
            "75th pct": round(m["pct_change"].quantile(0.75), 1),
            "% rising": round(100 * (m["change"] > 0).mean(), 1),
            "% falling": round(100 * (m["change"] < 0).mean(), 1)}


def movers(m, label, unit):
    show = ["noc_code", "noc_title", "base", "new", "pct_change"]
    out(f"  Largest increases in {label}:")
    out(m.nlargest(5, "pct_change")[show].round(1).to_string(index=False))
    out(f"  Largest decreases in {label}:")
    out(m.nsmallest(5, "pct_change")[show].round(1).to_string(index=False))


def main():
    data, totals, sizes = load()
    out("Step 4.2: matched-panel trends")
    out(f"Rule: grades A to D or ungraded, not suspect, in BOTH quarters. Vacancy changes need a base count above {MIN_BASE_VACANCIES}.")
    out(f"Rows read: {len(data):,}")
    out("\nPublished Canada totals for reference (all occupations):")
    out(totals.sort_index().to_string())
    for base, new in sorted({(c[1], c[2]) for c in COMPARISONS}):
        if base in totals.index and new in totals.index:
            v = 100 * (totals.loc[new, "vacancies"] / totals.loc[base, "vacancies"] - 1)
            w = 100 * (totals.loc[new, "offered_wage"] / totals.loc[base, "offered_wage"] - 1)
            out(f"  {base} to {new}: vacancies {v:+.1f}%, offered wage {w:+.1f}%")

    for title, base, new, level, geos in COMPARISONS:
        out(f"\n=== {title}: {base} to {new} ({LEVEL_NAMES[level]}, {sizes[level]} groups) ===")
        rows = []
        for geo in geos:
            for measure in ("wage", "vac"):
                m = matched(data, geo, level, base, new, measure)
                rows.append({"geography": geo, "measure": measure, **summarize(m, sizes[level])})
        out(pd.DataFrame(rows).set_index(["geography", "measure"]).to_string())

        for geo in geos:
            m = matched(data, geo, level, base, new, "wage")
            if len(m) > 10:
                top_base = set(m.nlargest(10, "base")["noc_code"])
                top_new = set(m.nlargest(10, "new")["noc_code"])
                rho = float(stats.spearmanr(m["base"], m["new"])[0])
                q = lambda s: "/".join(f"{x:.2f}" for x in s.quantile([0.25, 0.5, 0.75]))
                out(f"  Wage ranking stability, {geo}: rank correlation {rho:.2f}, top-10 overlap {len(top_base & top_new)} of 10, "
                    f"wage 25th/50th/75th percentile {q(m['base'])} then {q(m['new'])}")

        if geos[0] == "Canada":
            for measure, label in (("wage", "offered wage"), ("vac", "vacancies")):
                m = matched(data, "Canada", level, base, new, measure)
                if len(m) >= 10:
                    movers(m, f"{label} (Canada, {LEVEL_NAMES[level]})", level)

    (DOCS_DIR / "matched_panel_trends.txt").write_text("\n".join(LINES), encoding="utf-8")
    out("\nSaved docs/matched_panel_trends.txt")


if __name__ == "__main__":
    main()