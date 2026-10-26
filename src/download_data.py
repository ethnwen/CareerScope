"""Download Statistics Canada tables into data/raw without overwriting raw files.

Run:  python src/download_data.py
Add --hash to record a SHA-256 checksum of each data file (slow for the 14 GB table).
"""
import argparse
import csv
import hashlib
import sys
import zipfile
from datetime import datetime

import requests

from config import RAW_DIR, TABLES, get_logger

log = get_logger("download_data")
MB = 1024 * 1024
MANIFEST = RAW_DIR / "download_manifest.csv"
MANIFEST_FIELDS = ["checked_at", "table_id", "action", "csv_bytes", "csv_modified",
                   "start_period", "end_period", "archive_status", "sha256"]


def read_csv_header(path):
    with open(path, encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f))


def read_metadata_summary(path):
    """The first two rows of a StatCan metadata file describe the table."""
    with open(path, encoding="utf-8-sig", newline="") as f:
        reader = csv.reader(f)
        header = next(reader)
        values = next(reader)
    return dict(zip(header, values))


def sha256_of(path):
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while block := f.read(8 * MB):
            digest.update(block)
    return digest.hexdigest()


def download_zip(url, dest):
    part = dest.with_name(dest.name + ".part")
    log.info("Downloading %s", url)
    with requests.get(url, stream=True, timeout=60) as response:
        response.raise_for_status()
        total = int(response.headers.get("Content-Length", 0))
        done, next_report = 0, 100 * MB
        with open(part, "wb") as out:
            for block in response.iter_content(MB):
                out.write(block)
                done += len(block)
                if done >= next_report:
                    of_total = f" of {total // MB} MB" if total else ""
                    log.info("  %d MB downloaded%s", done // MB, of_total)
                    next_report += 100 * MB
    part.replace(dest)
    log.info("Saved %s (%d MB)", dest.name, dest.stat().st_size // MB)


def extract_zip(zip_path, extract_dir):
    temp_dir = extract_dir.with_name(extract_dir.name + ".extracting")
    for folder in (extract_dir, temp_dir):
        if folder.exists():
            raise RuntimeError(
                f"{folder} already exists but looks incomplete. Inspect it and "
                "delete it manually if safe. This script never deletes raw data.")
    log.info("Extracting %s", zip_path.name)
    with zipfile.ZipFile(zip_path) as z:
        z.extractall(temp_dir)
    temp_dir.rename(extract_dir)


def process_table(table_id, info, want_hash):
    extract_dir = RAW_DIR / f"{table_id}-eng"
    data_csv = extract_dir / f"{table_id}.csv"
    meta_csv = extract_dir / f"{table_id}_MetaData.csv"
    zip_path = RAW_DIR / f"{table_id}-eng.zip"
    ok = True

    if data_csv.exists() and meta_csv.exists():
        action = "already present"
        log.info("[%s] files already present, not downloading", table_id)
    else:
        if zip_path.exists():
            action = "extracted existing zip"
        else:
            action = "downloaded and extracted"
            download_zip(info["url"], zip_path)
        if not zipfile.is_zipfile(zip_path):
            raise RuntimeError(f"{zip_path} is not a valid zip file")
        extract_zip(zip_path, extract_dir)
        if not (data_csv.exists() and meta_csv.exists()):
            raise RuntimeError(f"Expected files missing after extraction in {extract_dir}")

    stat = data_csv.stat()
    log.info("[%s] data file %s (%.1f MB)", table_id, data_csv.name, stat.st_size / MB)

    actual = read_csv_header(data_csv)
    expected = info["columns"]
    if actual != expected:
        ok = False
        log.error("[%s] unexpected columns. Missing: %s. Extra: %s", table_id,
                  [c for c in expected if c not in actual],
                  [c for c in actual if c not in expected])
    else:
        log.info("[%s] column names match the expected layout", table_id)

    meta = {}
    try:
        meta = read_metadata_summary(meta_csv)
    except (StopIteration, OSError) as error:
        log.warning("[%s] could not read the metadata summary: %s", table_id, error)
    start = meta.get("Start Reference Period", "")
    end = meta.get("End Reference Period", "")
    status = meta.get("Archive Status", "")
    log.info("[%s] metadata: %s to %s | %s", table_id, start, end, status)
    if status and not status.upper().startswith("CURRENT"):
        log.warning("[%s] table is not marked CURRENT", table_id)

    digest = sha256_of(data_csv) if want_hash else ""

    new_file = not MANIFEST.exists()
    with open(MANIFEST, "a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=MANIFEST_FIELDS)
        if new_file:
            writer.writeheader()
        writer.writerow({
            "checked_at": datetime.now().isoformat(timespec="seconds"),
            "table_id": table_id,
            "action": action,
            "csv_bytes": stat.st_size,
            "csv_modified": datetime.fromtimestamp(stat.st_mtime).isoformat(timespec="seconds"),
            "start_period": start,
            "end_period": end,
            "archive_status": status,
            "sha256": digest,
        })
    return ok


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--hash", action="store_true", help="record SHA-256 of each data file")
    args = parser.parse_args()

    RAW_DIR.mkdir(parents=True, exist_ok=True)
    failures = []
    for table_id, info in TABLES.items():
        try:
            if not process_table(table_id, info, args.hash):
                failures.append(table_id)
        except (requests.RequestException, RuntimeError, zipfile.BadZipFile, OSError) as error:
            log.error("[%s] failed: %s", table_id, error)
            failures.append(table_id)

    if failures:
        log.error("Finished with problems in: %s", ", ".join(failures))
        sys.exit(1)
    log.info("All tables checked successfully")


if __name__ == "__main__":
    main()