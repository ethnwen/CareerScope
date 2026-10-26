"""Phase 2 checks for the open items in docs/project_scope.md, section 6.

Run:  python src/phase2_checks.py
Output is printed and saved to docs/phase2_checks.txt
"""
import numpy as np
import pandas as pd

from config import DOCS_DIR, RAW_DIR

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 40)
pd.set_option("display.max_rows", 500)
pd.set_option("display.max_colwidth", 110)

P444 = RAW_DIR / "14100444-eng" / "14100444.csv"
P417 = RAW_DIR / "14100417-eng" / "14100417.csv"
OUT = open(DOCS_DIR / "phase2_checks.txt", "w", encoding="utf-8")


def out(text=""):
    print(text)
    OUT.write(str(text) + "\n")


def load_0444():
    cols = ["REF_DATE", "GEO", "National Occupational Classification",
            "Statistics", "VALUE", "STATUS", "COORDINATE"]
    d = pd.read_csv(P444, encoding="utf-8-sig", usecols=cols, low_memory=False)
    d = d.rename(columns={"National Occupational Classification": "NOC"})
    d["geo_id"] = d["COORDINATE"].str.split(".", n=1).str[0].astype(int)
    noc = pd.DataFrame({"NOC": d["NOC"].unique()})
    noc["code"] = noc["NOC"].str.extract(r"\[(\d+)\]\s*$")[0]
    noc["digits"] = noc["code"].str.len().fillna(0).astype(int)
    d = d.merge(noc[["NOC", "digits"]], on="NOC", how="left")
    return d, noc


def load_0417():
    cols = ["REF_DATE", "GEO", "Wages", "Type of work",
            "National Occupational Classification (NOC)", "Gender", "Age group",
            "VALUE", "STATUS", "COORDINATE"]
    c = pd.read_csv(P417, encoding="utf-8-sig", usecols=cols, low_memory=False)
    return c.rename(columns={"National Occupational Classification (NOC)": "NOC"})


def check_2015(d):
    out("A. 2015-01: WHY SO FEW VACANCY VALUES?")
    first4 = ["2015-01", "2015-04", "2015-07", "2015-10"]
    vac = d[(d["Statistics"] == "Job vacancies") & d["REF_DATE"].isin(first4)]
    out(pd.crosstab(vac["REF_DATE"], vac["STATUS"]).to_string())
    for q in first4[:2]:
        s = vac[(vac["REF_DATE"] == q) & vac["VALUE"].notna()]
        out(f"{q}: values by occupation digits: {s['digits'].value_counts().sort_index().to_dict()}")
        out(f"{q}: values by geography: Canada={(s['geo_id'] == 1).sum()}, "
            f"province/territory={s['geo_id'].between(2, 14).sum()}, "
            f"economic region={(s['geo_id'] >= 15).sum()}")
    t = d[(d["geo_id"] == 1) & (d["NOC"] == "Total, all occupations")
          & (d["Statistics"] == "Job vacancies")].sort_values("REF_DATE").head(6)
    out("Canada, total occupations, job vacancies, first six quarters:")
    out(t[["REF_DATE", "VALUE", "STATUS"]].to_string(index=False))


def check_provinces(d):
    out("\nB. COVERAGE IN 2026-04 BY GEOGRAPHY (share of occupation cells with a value)")
    lat = d[(d["REF_DATE"] == "2026-04") & d["geo_id"].between(1, 14) & (d["digits"] > 0)].copy()
    lat["stat"] = lat["Statistics"].map({"Average offered hourly wage": "wage",
                                         "Job vacancies": "vac"})
    lat["reliable_A_D"] = lat["STATUS"].isin(["A", "B", "C", "D"])
    lat["any_A_E"] = lat["VALUE"].notna()
    for flag, title in [("reliable_A_D", "grades A to D only"),
                        ("any_A_E", "any published value (A to E)")]:
        table = (lat.groupby(["GEO", "stat", "digits"])[flag].mean()
                    .unstack(["stat", "digits"]).round(2))
        out(f"\n{title}. Columns: measure, then occupation digits "
            "(1 = broad category ... 5 = unit group)")
        out(table.to_string())


def check_0417(c):
    out("\nC. 0417: TRUE ZEROS BY MEASURE")
    out((c["VALUE"] == 0).groupby(c["Wages"]).sum().to_string())
    out("\nD. 0417: DUPLICATE KEYS")
    key = ["REF_DATE", "GEO", "Wages", "Type of work", "NOC", "Gender", "Age group"]
    out(f"By dimension key: {c.duplicated(key).sum()}")
    out(f"By (REF_DATE, COORDINATE): {c.duplicated(['REF_DATE', 'COORDINATE']).sum()}")


def check_crosswalk(c, noc):
    out("\nE. DRAFT CROSSWALK: 0417 occupation labels vs 0444 codes")
    labels = pd.DataFrame({"label417": c["NOC"].unique()})
    parts = labels["label417"].str.extract(r"^(.*?)\s*\[([^\]]+)\]\s*$")
    labels["name417"] = parts[0]
    labels["code417"] = parts[1].fillna("")
    labels["kind"] = np.where(labels["code417"].str.fullmatch(r"\d+"), "single", "combined")

    n444 = noc.dropna(subset=["code"]).copy()
    n444["name444"] = n444["NOC"].str.extract(r"^(.*?)\s*\[")[0]
    cross = labels.merge(n444[["code", "name444", "digits"]],
                         left_on="code417", right_on="code", how="left")
    cross["same_name"] = (cross["name417"].str.strip().str.lower()
                          == cross["name444"].str.strip().str.lower())
    out(cross[["code417", "kind", "digits", "same_name", "name417", "name444"]]
        .to_string(index=False))
    out(f"\nLabels in 0417: {len(cross)}. Single codes: {(cross['kind'] == 'single').sum()}. "
        f"Combined: {(cross['kind'] == 'combined').sum()}.")
    out(f"Single codes that exist in 0444: {cross['digits'].notna().sum()}. "
        f"Of those with identical names: {cross['same_name'].sum()}.")

    matched = set(cross.loc[cross["digits"].notna(), "code417"])
    gap = n444[n444["digits"].isin([1, 2]) & ~n444["code"].isin(matched)]
    out("\n0444 broad categories and major groups with NO identical code in 0417:")
    out(gap[["code", "digits", "name444"]].sort_values("code").to_string(index=False))


def main():
    d, noc = load_0444()
    check_2015(d)
    check_provinces(d)
    c = load_0417()
    check_0417(c)
    check_crosswalk(c, noc)
    out(f"\nSaved to {DOCS_DIR / 'phase2_checks.txt'}")
    OUT.close()


if __name__ == "__main__":
    main()