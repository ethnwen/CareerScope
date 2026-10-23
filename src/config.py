"""Shared paths, table definitions and logging setup for the CareerScope pipeline."""
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = PROJECT_ROOT / "data" / "raw"
PROCESSED_DIR = PROJECT_ROOT / "data" / "processed"
DOCS_DIR = PROJECT_ROOT / "docs"
LOG_DIR = PROJECT_ROOT / "logs"

_TAIL = ["UOM", "UOM_ID", "SCALAR_FACTOR", "SCALAR_ID", "VECTOR",
         "COORDINATE", "VALUE", "STATUS", "SYMBOL", "TERMINATED", "DECIMALS"]

# Column layouts observed during Phase 1 inspection. If Statistics Canada
# changes a layout, download_data.py reports it instead of failing silently.
TABLES = {
    "14100444": {
        "name": "Job vacancies and average offered hourly wage by occupation (unit group), quarterly",
        "url": "https://www150.statcan.gc.ca/n1/tbl/csv/14100444-eng.zip",
        "columns": ["REF_DATE", "GEO", "DGUID", "National Occupational Classification",
                    "Statistics"] + _TAIL,
    },
    "14100443": {
        "name": "Job vacancies by occupation and selected characteristics, quarterly",
        "url": "https://www150.statcan.gc.ca/n1/tbl/csv/14100443-eng.zip",
        "columns": ["REF_DATE", "GEO", "DGUID", "National Occupational Classification",
                    "Job vacancy characteristics", "Statistics"] + _TAIL,
    },
    "14100417": {
        "name": "Employee wages by occupation, annual",
        "url": "https://www150.statcan.gc.ca/n1/tbl/csv/14100417-eng.zip",
        "columns": ["REF_DATE", "GEO", "DGUID", "Wages", "Type of work",
                    "National Occupational Classification (NOC)", "Gender",
                    "Age group"] + _TAIL,
    },
}


def get_logger(name):
    """Log to the console and to logs/pipeline.log."""
    LOG_DIR.mkdir(exist_ok=True)
    logger = logging.getLogger(name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)
    fmt = logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s",
                            "%Y-%m-%d %H:%M:%S")
    file_handler = logging.FileHandler(LOG_DIR / "pipeline.log", encoding="utf-8")
    file_handler.setFormatter(fmt)
    console = logging.StreamHandler()
    console.setFormatter(fmt)
    logger.addHandler(file_handler)
    logger.addHandler(console)
    return logger