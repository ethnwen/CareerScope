"""Clean the raw Statistics Canada tables into analysis-ready files.

Reads data/raw (never modified) and writes data/processed:
  dim_*.csv                 dimension tables built from the metadata files
  fact_<table>.csv          one row per published value
  availability_<table>.csv  counts of every cell by availability status
  cleaning_summary.csv      one row per run

Run:  python src/clean_data.py                    (all tables)
      python src/clean_data.py --table 14100444   (one table)
"""
import argparse
import csv
import re
import sys
from datetime import datetime

import pandas as pd

from config import PROCESSED_DIR, RAW_DIR, get_logger

log = get_logger("clean_data")

CHUNK_ROWS = 500_000
NOC_COL = "National Occupational Classification"

# STATUS code -> availability group. Blank means a valid value with no grade.
STATUS_GROUP = {"": "value", "A": "value", "B": "value", "C": "value", "D": "value",
                "E": "value", "F": "unreliable", "x": "suppressed", "..": "not_available"}
GRADES = {"A", "B", "C", "D", "E"}

NOC_LEVEL_NAME = {0: "Total or unclassified", 1: "Broad category", 2: "Major group",
                  3: "Sub-major group", 4: "Minor group", 5: "Unit group"}
EXPECTED_NOC_LEVELS = {0: 2, 1: 10, 2: 45, 3: 89, 4: 162, 5: 516}
EXPECTED_ROWS = {"14100444": 6_018_496, "14100443": 67_508_672, "14100417": 6_098_004}

CHAR_ROOT_NAME = {1: "Type of work", 4: "Education", 14: "Certification",
                  17: "Experience", 23: "Duration", 30: "Type of position",
                  34: "Recruitment strategies", 47: "Continuity of recruitment"}
CHAR_SCOPE = {1: "in_scope", 4: "in_scope", 17: "in_scope", 30: "in_scope",
              47: "verify_first"}
CHAR_MAX_NOC_LEVEL = 3   # 0443 is kept for occupation levels 0 to 3 digits only

STATS_0444 = {1: ("job_vacancies", "Job vacancies"),
              5: ("offered_wage_avg", "Average offered hourly wage")}
STATS_0443 = {1: ("job_vacancies", "Job vacancies"),
              2: ("vacancy_share", "Proportion of job vacancies"),
              5: ("offered_wage_avg", "Average offered hourly wage")}
MEASURES_0417 = {"Average hourly wage rate": "employee_wage_avg_hourly",
                 "Median hourly wage rate": "employee_wage_median_hourly",
                 "Total employees, all wages": "employee_count"}
TYPE_OF_WORK_0417 = {"Both full- and part-time employees": "all",
                     "Full-time employees": "full_time",
                     "Part-time employees": "part_time"}
NOC_COL_0417 = "National Occupational Classification (NOC)"


# ---------------------------------------------------------------- dimensions
def read_member_table(meta_path, dimension_id):
    """Rows of one dimension from the member section of a StatCan metadata file."""
    members, in_members = [], False
    with open(meta_path, encoding="utf-8-sig", newline="") as f:
        for row in csv.reader(f):
            if row[:2] == ["Dimension ID", "Member Name"]:
                in_members = True
                continue
            if in_members:
                if not row:
                    break
                if row[0] == dimension_id:
                    members.append(row + [""] * (8 - len(row)))
    if not members:
        raise RuntimeError(f"No members found for dimension {dimension_id} in {meta_path}")
    return members


def to_int_or_none(text):
    return int(text) if text else None


def build_dim_geography():
    members = read_member_table(RAW_DIR / "14100444-eng" / "14100444_MetaData.csv", "1")
    records = []
    for r in members:
        geo_id, code, parent = int(r[3]), r[2].strip("[]"), to_int_or_none(r[4])
        if geo_id == 1:
            level = "Canada"
        elif geo_id <= 14:
            level = "Province/territory"
        else:
            level = "Economic region"
        records.append({
            "geo_id": geo_id, "geo_name": r[1], "sgc_code": code,
            "parent_geo_id": parent,
            "province_geo_id": geo_id if level == "Province/territory" else parent,
            "geo_level": level,
            "is_combined_region": level == "Economic region" and code == ""})
    df = pd.DataFrame(records)
    for col in ("parent_geo_id", "province_geo_id"):
        df[col] = df[col].astype("Int64")
    if len(df) != 83:
        log.warning("Expected 83 geographies, found %d", len(df))
    return df


def build_dim_occupation():
    members = read_member_table(RAW_DIR / "14100444-eng" / "14100444_MetaData.csv", "2")
    records = []
    for r in members:
        code = r[2].strip("[]")
        if code and not code.isdigit():
            raise RuntimeError(f"Unexpected occupation code: {r[2]}")
        records.append({
            "noc_id": int(r[3]), "noc_code": code, "noc_level": len(code),
            "noc_level_name": NOC_LEVEL_NAME[len(code)], "noc_title": r[1],
            "parent_noc_id": to_int_or_none(r[4]), "is_total": int(r[3]) == 1,
            "is_unclassified": r[1] == "Unclassified occupations"})
    df = pd.DataFrame(records)
    df["parent_noc_id"] = df["parent_noc_id"].astype("Int64")
    counts = df["noc_level"].value_counts().sort_index().to_dict()
    if counts != EXPECTED_NOC_LEVELS:
        raise RuntimeError(f"Occupation level counts changed: {counts}")
    return df


def build_dim_characteristic():
    members = read_member_table(RAW_DIR / "14100443-eng" / "14100443_MetaData.csv", "3")
    parent = {int(r[3]): to_int_or_none(r[4]) for r in members}

    def root_of(i):
        while parent[i] is not None:
            i = parent[i]
        return i

    records = []
    for r in members:
        cid = int(r[3])
        root = root_of(cid)
        records.append({
            "char_id": cid, "char_title": r[1].replace('"', ""),
            "parent_char_id": parent[cid], "root_char_id": root,
            "dimension": CHAR_ROOT_NAME.get(root, f"Unknown ({root})"),
            "is_dimension_total": parent[cid] is None,
            "is_terminated": r[5] == "t",
            "analysis_scope": CHAR_SCOPE.get(root, "out_of_scope")})
    df = pd.DataFrame(records)
    df["parent_char_id"] = df["parent_char_id"].astype("Int64")
    if len(df) != 48:
        log.warning("Expected 48 characteristic members, found %d", len(df))
    return df


def build_dimensions():
    dims = {"geo": build_dim_geography(), "noc": build_dim_occupation(),
            "char": build_dim_characteristic()}
    for name, df in dims.items():
        path = PROCESSED_DIR / f"dim_{ {'geo': 'geography', 'noc': 'occupation', 'char': 'characteristic'}[name] }.csv"
        df.to_csv(path, index=False)
        log.info("Wrote %s (%d rows)", path.name, len(df))
    return dims


# ------------------------------------------------------------------- helpers
def read_chunks(path, usecols):
    return pd.read_csv(path, encoding="utf-8-sig", usecols=usecols, dtype=str,
                       keep_default_na=False, chunksize=CHUNK_ROWS)


def split_coordinate(coord, parts_expected):
    parts = coord.str.split(".", expand=True)
    if parts.shape[1] != parts_expected:
        raise ValueError(f"COORDINATE has {parts.shape[1]} parts, expected {parts_expected}")
    return [parts[i].astype(int) for i in range(parts_expected)]


def classify(chunk):
    """Numeric value, availability group and quality grade for each row."""
    value = pd.to_numeric(chunk["VALUE"], errors="coerce")
    if ((chunk["VALUE"] != "") & value.isna()).any():
        raise ValueError("Non-numeric VALUE found")
    status = chunk["STATUS"]
    group = status.map(STATUS_GROUP)
    if group.isna().any():
        raise ValueError(f"Unknown STATUS codes: {sorted(status[group.isna()].unique())}")
    if (value.notna() != (group == "value")).any():
        raise ValueError("VALUE and STATUS disagree about whether a value exists")
    grade = status.where(status.isin(GRADES), "NONE")
    return value, group, grade


def period_info(ref, quarterly):
    """period_start (ISO date), year and quarter from REF_DATE text."""
    start, year, quarter = {}, {}, {}
    for r in ref.unique():
        if quarterly:
            if len(r) != 7 or int(r[5:7]) not in (1, 4, 7, 10):
                raise ValueError(f"Unexpected quarterly REF_DATE: {r}")
            y, m = int(r[:4]), int(r[5:7])
            start[r], quarter[r] = f"{y:04d}-{m:02d}-01", (m - 1) // 3 + 1
        else:
            y = int(r)
            start[r] = f"{y:04d}-01-01"
        year[r] = y
    return ref.map(start), ref.map(year), (ref.map(quarter) if quarterly else None)


def require(series, what):
    if series.isna().any():
        raise ValueError(f"Unmapped {what} found")


def note_pairs(seen, ids, labels):
    pairs = pd.DataFrame({"i": ids, "l": labels}).drop_duplicates()
    seen.update(zip(pairs["i"], pairs["l"]))


def verify_pairs(name, seen, expected):
    bad = sorted((int(i), l) for i, l in seen if expected.get(int(i)) != l)
    if bad:
        raise RuntimeError(f"{name} labels do not match the metadata, e.g. {bad[:3]}")
    log.info("%s labels match the metadata (%d distinct)", name, len(seen))


def expected_noc_labels(noc):
    return {int(r.noc_id): (f"{r.noc_title} [{r.noc_code}]" if r.noc_code else r.noc_title)
            for r in noc.itertuples()}


class Output:
    """Writes fact rows to a temporary file and accumulates availability counts."""

    def __init__(self, table_id):
        self.table_id = table_id
        self.started = datetime.now()
        self.fact_path = PROCESSED_DIR / f"fact_{table_id}.csv"
        self.avail_path = PROCESSED_DIR / f"availability_{table_id}.csv"
        self.tmp = self.fact_path.with_name(self.fact_path.name + ".tmp")
        self.tmp.unlink(missing_ok=True)
        self.header, self.avail = True, None
        self.rows_read = self.rows_written = 0

    def add(self, fact, avail_frame, keys):
        fact.to_csv(self.tmp, mode="a", header=self.header, index=False)
        self.header = False
        self.rows_written += len(fact)
        counts = avail_frame.groupby(keys).size()
        self.avail = counts if self.avail is None else self.avail.add(counts, fill_value=0)

    def progress(self, chunk_number):
        if chunk_number % 10 == 0:
            log.info("[%s] %s rows read, %s values kept so far", self.table_id,
                     f"{self.rows_read:,}", f"{self.rows_written:,}")

    def finish(self):
        if self.avail is None:
            raise RuntimeError(f"[{self.table_id}] no rows were in scope")
        self.tmp.replace(self.fact_path)
        avail = self.avail.round().astype("int64").rename("n_cells").reset_index()
        avail.to_csv(self.avail_path, index=False)
        groups = avail.groupby("status_group")["n_cells"].sum()
        expected = EXPECTED_ROWS[self.table_id]
        if self.rows_read != expected:
            log.warning("[%s] read %s rows, Phase 1 saw %s (the table may have been updated)",
                        self.table_id, f"{self.rows_read:,}", f"{expected:,}")
        return {"table_id": self.table_id,
                "finished_at": datetime.now().isoformat(timespec="seconds"),
                "rows_read": self.rows_read, "rows_in_scope": int(avail["n_cells"].sum()),
                "rows_with_value": self.rows_written,
                "not_available": int(groups.get("not_available", 0)),
                "suppressed": int(groups.get("suppressed", 0)),
                "unreliable": int(groups.get("unreliable", 0))}


# ------------------------------------------------------------- table cleaners
def clean_0417(dims):
    table = "14100417"
    path = RAW_DIR / "14100417-eng" / "14100417.csv"
    geo = dims["geo"]
    geo_by_name = dict(zip(geo.loc[geo.geo_id <= 14, "geo_name"],
                           geo.loc[geo.geo_id <= 14, "geo_id"]))
    out, labels417 = Output(table), {}
    cols = ["REF_DATE", "GEO", "Wages", "Type of work", NOC_COL_0417, "Gender",
            "Age group", "VALUE", "STATUS"]
    for n, chunk in enumerate(read_chunks(path, cols)):
        out.rows_read += len(chunk)
        keep = ((chunk["Gender"] == "Total - Gender")
                & (chunk["Age group"] == "15 years and over")
                & chunk["Wages"].isin(MEASURES_0417)
                & chunk["Type of work"].isin(TYPE_OF_WORK_0417))
        chunk = chunk.loc[keep]
        if chunk.empty:
            continue
        for label in set(chunk[NOC_COL_0417].unique()) - labels417.keys():
            m = re.match(r"^(.*?)\s*\[([^\]]+)\]\s*$", label)
            if not m:
                raise ValueError(f"No code found in occupation label: {label}")
            labels417[label] = (m.group(2), m.group(1))
        value, group, grade = classify(chunk)
        geo_id = chunk["GEO"].map(geo_by_name)
        measure = chunk["Wages"].map(MEASURES_0417)
        work = chunk["Type of work"].map(TYPE_OF_WORK_0417)
        code = chunk[NOC_COL_0417].map({k: v[0] for k, v in labels417.items()})
        for series, what in ((geo_id, "geography"), (measure, "measure"), (work, "type of work")):
            require(series, what)
        period, year, _ = period_info(chunk["REF_DATE"], False)
        has_value = value.notna()
        fact = pd.DataFrame({"period_start": period, "year": year,
                             "geo_id": geo_id.astype(int), "noc417_code": code,
                             "type_of_work": work, "measure": measure,
                             "value": value, "quality_grade": grade}).loc[has_value]
        avail = pd.DataFrame({"period_start": period, "geo_id": geo_id.astype(int),
                              "type_of_work": work, "measure": measure,
                              "status_group": group})
        out.add(fact, avail, ["period_start", "geo_id", "type_of_work", "measure",
                              "status_group"])
        out.progress(n)

    noc = dims["noc"]
    by_code = dict(zip(noc.loc[noc.noc_code != "", "noc_code"],
                       zip(noc.loc[noc.noc_code != "", "noc_id"],
                           noc.loc[noc.noc_code != "", "noc_title"])))
    rows = []
    for label, (code, name) in labels417.items():
        single = code.isdigit()
        match = by_code.get(code) if single else None
        rows.append({"noc417_code": code, "noc417_label": name,
                     "kind": "single" if single else "combined",
                     "noc_id_0444": match[0] if match else None,
                     "name_matches_0444": bool(match and match[1] == name)})
    cross = pd.DataFrame(rows).sort_values("noc417_code")
    cross["noc_id_0444"] = cross["noc_id_0444"].astype("Int64")
    cross.to_csv(PROCESSED_DIR / "dim_occupation_0417.csv", index=False)
    log.info("Crosswalk: %d labels, %d single, %d combined, %d matched to 0444 with identical names",
             len(cross), (cross.kind == "single").sum(), (cross.kind == "combined").sum(),
             cross.name_matches_0444.sum())
    return out.finish()


def clean_0444(dims):
    table = "14100444"
    path = RAW_DIR / "14100444-eng" / "14100444.csv"
    noc = dims["noc"]
    noc_level = dict(zip(noc["noc_id"], noc["noc_level"]))
    expected_geo = dict(zip(dims["geo"]["geo_id"], dims["geo"]["geo_name"]))
    out, seen_geo, seen_noc, seen_stat = Output(table), set(), set(), set()
    measure_of = {i: key for i, (key, _) in STATS_0444.items()}
    cols = ["REF_DATE", "GEO", NOC_COL, "Statistics", "VALUE", "STATUS", "COORDINATE"]
    for n, chunk in enumerate(read_chunks(path, cols)):
        out.rows_read += len(chunk)
        geo_id, noc_id, stat_id = split_coordinate(chunk["COORDINATE"], 3)
        note_pairs(seen_geo, geo_id, chunk["GEO"])
        note_pairs(seen_noc, noc_id, chunk[NOC_COL])
        note_pairs(seen_stat, stat_id, chunk["Statistics"])
        value, group, grade = classify(chunk)
        period, year, quarter = period_info(chunk["REF_DATE"], True)
        measure, level = stat_id.map(measure_of), noc_id.map(noc_level)
        require(measure, "statistic")
        require(level, "occupation")
        has_value = value.notna()
        fact = pd.DataFrame({"period_start": period, "year": year, "quarter": quarter,
                             "geo_id": geo_id, "noc_id": noc_id, "measure": measure,
                             "value": value, "quality_grade": grade}).loc[has_value]
        avail = pd.DataFrame({"period_start": period, "geo_id": geo_id,
                              "noc_level": level, "measure": measure,
                              "status_group": group})
        out.add(fact, avail, ["period_start", "geo_id", "noc_level", "measure",
                              "status_group"])
        out.progress(n)
    verify_pairs("0444 geography", seen_geo, expected_geo)
    verify_pairs("0444 occupation", seen_noc, expected_noc_labels(noc))
    verify_pairs("0444 statistic", seen_stat, {i: l for i, (_, l) in STATS_0444.items()})
    return out.finish()


def clean_0443(dims):
    table = "14100443"
    path = RAW_DIR / "14100443-eng" / "14100443.csv"
    noc, char, geo = dims["noc"], dims["char"], dims["geo"]
    noc_level = dict(zip(noc["noc_id"], noc["noc_level"]))
    keep_chars = set(char.loc[char.analysis_scope.isin(["in_scope", "verify_first"]), "char_id"])
    expected_char = dict(zip(char["char_id"], char["char_title"]))
    geo_by_name = dict(zip(geo.loc[geo.geo_id <= 14, "geo_name"],
                           geo.loc[geo.geo_id <= 14, "geo_id"]))
    measure_of = {i: key for i, (key, _) in STATS_0443.items()}
    log.info("[%s] keeping %d characteristic members and occupation levels 0 to %d",
             table, len(keep_chars), CHAR_MAX_NOC_LEVEL)
    out, seen_noc, seen_char, seen_stat = Output(table), set(), set(), set()
    cols = ["REF_DATE", "GEO", NOC_COL, "Job vacancy characteristics", "Statistics",
            "VALUE", "STATUS", "COORDINATE"]
    for n, chunk in enumerate(read_chunks(path, cols)):
        out.rows_read += len(chunk)
        _, noc_all, char_all, stat_all = split_coordinate(chunk["COORDINATE"], 4)
        level_all = noc_all.map(noc_level)
        require(level_all, "occupation")
        keep = char_all.isin(keep_chars) & (level_all <= CHAR_MAX_NOC_LEVEL)
        if not keep.any():
            out.progress(n)
            continue
        chunk = chunk.loc[keep]
        noc_id, char_id, stat_id, level = (s.loc[keep] for s in
                                           (noc_all, char_all, stat_all, level_all))
        geo_id = chunk["GEO"].map(geo_by_name)
        measure = stat_id.map(measure_of)
        require(geo_id, "geography")
        require(measure, "statistic")
        note_pairs(seen_noc, noc_id, chunk[NOC_COL])
        note_pairs(seen_char, char_id,
                   chunk["Job vacancy characteristics"].str.replace('"', "", regex=False))
        note_pairs(seen_stat, stat_id, chunk["Statistics"])
        value, group, grade = classify(chunk)
        period, year, quarter = period_info(chunk["REF_DATE"], True)
        has_value = value.notna()
        fact = pd.DataFrame({"period_start": period, "year": year, "quarter": quarter,
                             "geo_id": geo_id.astype(int), "noc_id": noc_id,
                             "char_id": char_id, "measure": measure, "value": value,
                             "quality_grade": grade}).loc[has_value]
        avail = pd.DataFrame({"period_start": period, "geo_id": geo_id.astype(int),
                              "noc_level": level, "char_id": char_id,
                              "measure": measure, "status_group": group})
        out.add(fact, avail, ["period_start", "geo_id", "noc_level", "char_id",
                              "measure", "status_group"])
        out.progress(n)
    verify_pairs("0443 occupation", seen_noc, expected_noc_labels(noc))
    verify_pairs("0443 characteristic", seen_char, expected_char)
    verify_pairs("0443 statistic", seen_stat, {i: l for i, (_, l) in STATS_0443.items()})
    return out.finish()


RUNNERS = {"14100417": clean_0417, "14100444": clean_0444, "14100443": clean_0443}


def write_summary(summary):
    path = PROCESSED_DIR / "cleaning_summary.csv"
    new_file = not path.exists()
    with open(path, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(summary))
        if new_file:
            writer.writeheader()
        writer.writerow(summary)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--table", choices=list(RUNNERS) + ["all"], default="all")
    args = parser.parse_args()
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    try:
        dims = build_dimensions()
        for table_id in (list(RUNNERS) if args.table == "all" else [args.table]):
            summary = RUNNERS[table_id](dims)
            write_summary(summary)
            log.info("[%s] done: %s rows read, %s in scope, %s values written",
                     table_id, f"{summary['rows_read']:,}",
                     f"{summary['rows_in_scope']:,}", f"{summary['rows_with_value']:,}")
    except (RuntimeError, ValueError, OSError, KeyError) as error:
        log.exception("Cleaning stopped: %s", error)
        sys.exit(1)


if __name__ == "__main__":
    main()