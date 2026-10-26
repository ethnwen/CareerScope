import sys
import pandas as pd

path = sys.argv[1]
df = pd.read_csv(path, encoding="utf-8-sig", low_memory=False)

print(f"\nFILE: {path}")
print(f"Shape: {df.shape}")
print("\nColumns and types:")
print(df.dtypes)
print("\nMissing values per column:")
print(df.isna().sum())
print(f"\nFully duplicated rows: {df.duplicated().sum()}")

if "REF_DATE" in df.columns:
    print("\nREF_DATE values:", sorted(df["REF_DATE"].astype(str).unique()))

# Status flags are important for suppression, so always show them
for col in ["STATUS", "SYMBOL", "UOM", "SCALAR_FACTOR"]:
    if col in df.columns:
        print(f"\n{col}:")
        print(df[col].value_counts(dropna=False).to_string())

# Every non-numeric column: list values if few, sample if many
for col in df.columns:
    if col in ("REF_DATE", "STATUS", "SYMBOL", "UOM", "SCALAR_FACTOR"):
        continue
    if not pd.api.types.is_numeric_dtype(df[col]):
        n = df[col].nunique()
        if n <= 60:
            print(f"\n{col} ({n} unique):")
            print(df[col].value_counts(dropna=False).to_string())
        else:
            print(f"\n{col}: {n} unique values, first 10:")
            print(df[col].drop_duplicates().head(10).to_string())

if "VALUE" in df.columns:
    print("\nVALUE summary:")
    print(df["VALUE"].describe())
    print("Negative values:", (df["VALUE"] < 0).sum())