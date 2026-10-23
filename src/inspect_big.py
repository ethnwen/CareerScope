import sys
from collections import Counter
import pandas as pd

path = sys.argv[1]
SKIP = {"VECTOR", "COORDINATE", "DGUID", "VALUE"}   # too many unique values to count
counters = {}
columns = None
n_rows = 0
n_with_value = 0

reader = pd.read_csv(path, encoding="utf-8-sig", dtype=str,
                     keep_default_na=False, chunksize=200_000)

for chunk in reader:
    if columns is None:
        columns = list(chunk.columns)
    n_rows += len(chunk)
    n_with_value += pd.to_numeric(chunk["VALUE"], errors="coerce").notna().sum()
    for col in chunk.columns:
        if col in SKIP:
            continue
        counters.setdefault(col, Counter()).update(chunk[col].value_counts().to_dict())

print(f"FILE: {path}")
print(f"Rows: {n_rows}")
print(f"Rows with a numeric VALUE: {n_with_value}")
print(f"Columns: {columns}")

for col, counter in counters.items():
    n = len(counter)
    print(f"\n{col} ({n} unique):")
    if n <= 60:
        for key in sorted(counter):
            print(f"   {key!r}: {counter[key]}")
    else:
        print("   first 10 by frequency:")
        for key, cnt in counter.most_common(10):
            print(f"   {key!r}: {cnt}")