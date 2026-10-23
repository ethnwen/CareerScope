import pandas as pd

PATH = "data/raw/14100444-eng/14100444.csv"
cols = ["REF_DATE", "GEO", "DGUID", "National Occupational Classification",
        "Statistics", "VALUE", "STATUS", "COORDINATE"]
df = pd.read_csv(PATH, encoding="utf-8-sig", usecols=cols, low_memory=False)
df = df.rename(columns={"National Occupational Classification": "NOC"})

# Geography level from the geography member ID (first part of COORDINATE)
coords = pd.DataFrame({"COORDINATE": df["COORDINATE"].unique()})
p = coords["COORDINATE"].str.split(".", expand=True).astype(int)
coords["geo_id"] = p[0]
coords["geo_level"] = "Economic region"
coords.loc[coords["geo_id"] == 1, "geo_level"] = "Canada"
coords.loc[coords["geo_id"].between(2, 14), "geo_level"] = "Province/territory"
df = df.merge(coords, on="COORDINATE", how="left")

# Occupation level from digits in the bracketed code
noc = pd.DataFrame({"NOC": df["NOC"].unique()})
noc["noc_code"] = noc["NOC"].str.extract(r"\[(\d+)\]\s*$")[0]
noc["noc_digits"] = noc["noc_code"].str.len().fillna(0).astype(int)
df = df.merge(noc[["NOC", "noc_digits"]], on="NOC", how="left")

print("1. GEOGRAPHY: distinct members and GEO names per level")
print(df.groupby("geo_level").agg(members=("geo_id", "nunique"),
                                  names=("GEO", "nunique")).to_string())

print("\n2. OCCUPATION LEVELS (0 = no bracketed code)")
print(noc["noc_digits"].value_counts().sort_index().to_string())
print("Labels with no code:")
print(noc[noc["noc_digits"] == 0]["NOC"].to_string(index=False))

print("\n3. STATUS vs HAS A VALUE")
print(df.groupby("STATUS")["VALUE"].agg(rows="size", with_value="count").to_string())
print(pd.crosstab(df["Statistics"], df["STATUS"]).to_string())

print("\n4. VALUES PER QUARTER, BY MEASURE")
print(df[df["VALUE"].notna()]
        .groupby(["REF_DATE", "Statistics"]).size().unstack().to_string())

print("\n5. LATEST QUARTER (2026-04): CELLS WITH A VALUE")
latest = df[df["REF_DATE"] == "2026-04"].copy()
latest["has_value"] = latest["VALUE"].notna()
print(latest.groupby(["Statistics", "geo_level", "noc_digits"])
            ["has_value"].agg(["sum", "count", "mean"]).round(3).to_string())

print("\n6. TRUE ZEROS BY MEASURE")
print(df[df["VALUE"] == 0].groupby("Statistics").size().to_string())

print("\n7. DUPLICATE CHECKS")
print("By name key (REF_DATE, GEO, NOC, Statistics):",
      df.duplicated(["REF_DATE", "GEO", "NOC", "Statistics"]).sum())
print("By coordinate key (REF_DATE, COORDINATE):",
      df.duplicated(["REF_DATE", "COORDINATE"]).sum())