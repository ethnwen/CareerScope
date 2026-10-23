"""List 0443 offered-wage values outside 5 to 200 dollars per hour, with context."""
import pandas as pd

from config import DOCS_DIR, PROCESSED_DIR

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 30)
pd.set_option("display.max_colwidth", 55)

fact = pd.read_csv(PROCESSED_DIR / "fact_14100443.csv", keep_default_na=False, na_values=[""])
geo = pd.read_csv(PROCESSED_DIR / "dim_geography.csv", dtype={"sgc_code": str})
noc = pd.read_csv(PROCESSED_DIR / "dim_occupation.csv", dtype={"noc_code": str})
char = pd.read_csv(PROCESSED_DIR / "dim_characteristic.csv")

wage = fact[fact["measure"] == "offered_wage_avg"]
out = wage[(wage["value"] < 5) | (wage["value"] > 200)].copy()

key = ["period_start", "geo_id", "noc_id"]
all_types = (wage[wage["char_id"] == 1][key + ["value"]]
             .rename(columns={"value": "wage_all_types"}))
vac = (fact[fact["measure"] == "job_vacancies"][key + ["char_id", "value"]]
       .rename(columns={"value": "vacancies"}))
typical = (wage.groupby(["geo_id", "noc_id", "char_id"])["value"].median()
           .rename("median_all_quarters").reset_index())

out = (out.merge(geo[["geo_id", "geo_name"]], on="geo_id")
          .merge(noc[["noc_id", "noc_code", "noc_title"]], on="noc_id")
          .merge(char[["char_id", "char_title"]], on="char_id")
          .merge(all_types, on=key, how="left")
          .merge(vac, on=key + ["char_id"], how="left")
          .merge(typical, on=["geo_id", "noc_id", "char_id"], how="left"))

cols = ["period_start", "geo_name", "noc_code", "noc_title", "char_title", "value",
        "quality_grade", "wage_all_types", "vacancies", "median_all_quarters"]
text = out.sort_values("value")[cols].to_string(index=False)
print(text)
(DOCS_DIR / "wage_outliers.txt").write_text(text, encoding="utf-8")