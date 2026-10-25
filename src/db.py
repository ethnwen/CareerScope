"""Small helper for running read-only queries against the CareerScope database.

Uses Windows authentication on localhost. To use another server, set the environment
variable CAREERSCOPE_ODBC to a full ODBC connection string.
"""
import os
from decimal import Decimal

import pandas as pd

CONNECTION = os.environ.get("CAREERSCOPE_ODBC") or (
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=localhost;DATABASE=CareerScope;"
    "Trusted_Connection=yes;TrustServerCertificate=yes;")


def query_df(sql):
    """Run one SELECT and return a DataFrame. Decimal values become floats."""
    import pyodbc
    conn = pyodbc.connect(CONNECTION, autocommit=True)
    try:
        cur = conn.cursor()
        cur.execute(sql)
        columns = [c[0] for c in cur.description]
        rows = [tuple(float(v) if isinstance(v, Decimal) else v for v in row) for row in cur.fetchall()]
        return pd.DataFrame.from_records(rows, columns=columns)
    finally:
        conn.close()