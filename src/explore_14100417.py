import pandas as pd

PATH = "data/raw/14100417-eng/14100417.csv"
cols = ["REF_DATE", "GEO", "Wages", "Type of work",
        "National Occupational Classification (NOC)", "Gender",
        "Age group", "UOM", "VALUE", "STATUS"]
df = pd.read_csv(PATH, encoding="utf-8-sig", usecols=cols, low_memory=False)
df = df.rename(columns={"National Occupational Classification (NOC)": "NOC"})

print("1. GENDER")
print(df["Gender"].value_counts().to_string())

print("\n2. AGE GROUP")
print(df["Age group"].value_counts().to_string())

print("\n3. ALL 59 NOC LABELS")
print(df["NOC"].drop_duplicates().to_string(index=False))

print("\n4. WAGES AND UNITS")
print(df.groupby(["Wages", "UOM"]).size().to_string())

print("\n5. STATUS vs HAS A VALUE (blank STATUS = NaN)")
print(df.assign(has_value=df["VALUE"].notna())
        .groupby("STATUS", dropna=False)["has_value"].agg(["size", "sum"]).to_string())

# Project slice: first-listed Gender and Age group are usually the totals.
g = df["Gender"].iloc[0]
a = df["Age group"].iloc[0]
print(f"\n6. SLICE: Gender={g!r}, Age group={a!r}, both full- and part-time")
sl = df[(df["Wages"] == "Average hourly wage rate")
        & (df["Type of work"] == "Both full- and part-time employees")
        & (df["Gender"] == g) & (df["Age group"] == a)].copy()
sl["has_value"] = sl["VALUE"].notna()
print("Share of cells with a value, by year (all provinces and occupations):")
print(sl.groupby("REF_DATE")["has_value"].mean().round(3).to_string())
print("\n2025 coverage by geography:")
print(sl[sl["REF_DATE"] == 2025].groupby("GEO")["has_value"]
        .agg(["sum", "count", "mean"]).round(3).to_string())