import re
import pandas as pd

PATH = "data/raw/14100443-eng/14100443.csv"
NOC = "National Occupational Classification"
CHAR = "Job vacancy characteristics"
USE = ["REF_DATE", "GEO", NOC, CHAR, "Statistics", "VALUE", "STATUS",
       "TERMINATED", "COORDINATE"]
TERR = {"Yukon", "Northwest Territories", "Nunavut"}
LATEST = "2026-04"

digit_cache = {}
def noc_digits(series):
    for label in series.unique():
        if label not in digit_cache:
            m = re.search(r"\[(\d+)\]\s*$", label)
            digit_cache[label] = len(m.group(1)) if m else 0
    return series.map(digit_cache)

def add(acc, new):
    return new if acc is None else acc.add(new, fill_value=0)

status_acc = term_acc = cov_acc = None
nat_rows = []

reader = pd.read_csv(PATH, encoding="utf-8-sig", usecols=USE, dtype=str,
                     keep_default_na=False, chunksize=500_000)
for i, chunk in enumerate(reader):
    if i % 20 == 0:
        print(f"...chunk {i}", file=__import__("sys").stderr)
    chunk["has_value"] = pd.to_numeric(chunk["VALUE"], errors="coerce").notna()

    status_acc = add(status_acc, chunk.groupby(["Statistics", "STATUS"]).size())

    t = chunk[chunk["TERMINATED"] == "t"]
    if len(t):
        term_acc = add(term_acc, t.groupby(CHAR).size())

    lat = chunk[chunk["REF_DATE"] == LATEST].copy()
    if len(lat):
        lat["noc_digits"] = noc_digits(lat[NOC])
        lat["geo_type"] = "Province"
        lat.loc[lat["GEO"] == "Canada", "geo_type"] = "Canada"
        lat.loc[lat["GEO"].isin(TERR), "geo_type"] = "Territory"
        cov_acc = add(cov_acc, lat.groupby(["Statistics", "geo_type", "noc_digits"])
                                  ["has_value"].agg(["sum", "count"]))
        nat = lat[(lat["GEO"] == "Canada") & (lat[NOC] == "Total, all occupations")]
        if len(nat):
            nat_rows.append(nat[["COORDINATE", CHAR, "Statistics", "VALUE", "STATUS"]])

print("A. STATUS BY STATISTIC (blank = value with no quality grade)")
print(status_acc.unstack(fill_value=0).astype(int).to_string())

print("\nB. TERMINATED SERIES ('t') BY CHARACTERISTIC")
print(term_acc.astype(int).to_string() if term_acc is not None else "none")

print(f"\nC. COVERAGE IN {LATEST}: cells with a value, by statistic, geography type, occupation digits")
cov_acc["share"] = (cov_acc["sum"] / cov_acc["count"]).round(3)
cov_acc[["sum", "count"]] = cov_acc[["sum", "count"]].astype(int)
print(cov_acc.to_string())

print(f"\nD. CANADA, TOTAL ALL OCCUPATIONS, {LATEST}: every characteristic")
nat = pd.concat(nat_rows).sort_values([CHAR, "Statistics"])
print(nat.to_string(index=False))