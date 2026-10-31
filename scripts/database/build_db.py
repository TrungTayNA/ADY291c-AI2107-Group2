"""
build_db.py - Tao olist.db tu CSV da xu ly
Pattern: Staging -> Relational (3NF) -> Analytical Views

Cach chay: python scripts/database/build_db.py
"""

import sqlite3
import pandas as pd
import os
import re
import tempfile
import time

# Cau hinh duong dan
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED   = os.path.join(BASE_DIR, "data", "processed")
SQL_DIR     = os.path.join(BASE_DIR, "sql")
DB_PATH     = os.path.join(BASE_DIR, "scripts", "database", "olist.db")
TEMP_DB_PATH = DB_PATH + ".tmp"

CSV_MAP = {
    "stg_customers":          "clean_olist_customers.csv",
    "stg_orders":             "clean_olist_orders.csv",
    "stg_order_items":        "clean_olist_order_items.csv",
    "stg_order_payments":     "clean_olist_payments.csv",
    "stg_order_reviews":      "clean_olist_reviews.csv",
    "stg_products":            "clean_olist_products.csv",
    "stg_sellers":             "clean_olist_sellers.csv",
    "stg_geolocations":        "clean_olist_geolocation.csv",
    "stg_product_categories": "clean_olist_category_translation.csv",
}

STAGING_COLUMN_ALIASES = {
    "stg_orders": {"is_delayed": "is_late"},
    "stg_order_items": {"item_total_value": "item_total"},
    "stg_order_reviews": {"has_review_comment": "has_comment"},
}


def log(msg):
    print(msg, flush=True)


def validate_inputs():
    required_paths = [
        *(os.path.join(PROCESSED, filename) for filename in CSV_MAP.values()),
        os.path.join(SQL_DIR, "01_schema.sql"),
        os.path.join(SQL_DIR, "02_load_data.sql"),
        os.path.join(SQL_DIR, "03_queries.sql"),
    ]
    missing_paths = [path for path in required_paths if not os.path.isfile(path)]
    if missing_paths:
        missing_list = "\n".join(f"  - {path}" for path in missing_paths)
        raise FileNotFoundError(
            "Thiếu dữ liệu đầu vào hoặc file SQL cần thiết:\n"
            f"{missing_list}\n"
            "Hãy chạy Notebooks/02_preprocessing.ipynb trước, sau đó chạy lại "
            "scripts/database/build_db.py từ thư mục gốc dự án."
        )


def run_schema(conn, filename):
    """DDL (CREATE TABLE/INDEX/VIEW): executescript() - auto-commit la OK."""
    path = os.path.join(SQL_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    conn.executescript(sql)

def run_dml(conn, filename):
    """
    DML (INSERT...SELECT FROM staging): KHONG dung executescript() vi no
    tu phat COMMIT truoc khi chay -> staging data (vua ghi boi pandas
    trong cung connection) se khong thay.
    Dung cursor.execute() tung statement de giu trong cung transaction.
    """
    path = os.path.join(SQL_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        raw = f.read()

    statements = [s.strip() for s in raw.split(";") if s.strip()]
    cur = conn.cursor()
    for stmt in statements:
        statement = re.sub(r'--[^\n]*', '', stmt).strip()
        if not statement:
            continue
        cur.execute(statement)
    conn.commit()

def load_staging(conn):
    log("\n[STEP 1] Nap CSV vao Staging tables...")
    for table, csv_file in CSV_MAP.items():
        csv_path = os.path.join(PROCESSED, csv_file)
        t0 = time.time()
        df = pd.read_csv(csv_path, low_memory=False)
        df = df.rename(columns=STAGING_COLUMN_ALIASES.get(table, {}))
        df.to_sql(table, conn, if_exists="replace", index=False, chunksize=10000)
        log(f"  OK {table:32s} -> {len(df):>7,} rows  ({time.time()-t0:.1f}s)")

def transform(conn):
    log("\n[STEP 2] Transform Staging -> Relational tables...")
    run_dml(conn, "02_load_data.sql")
    log("  OK Transform hoan tat")

def create_views(conn):
    """Trich phan DROP/CREATE VIEW tu 03_queries.sql va tao view."""
    log("\n[STEP 3] Tao analytical views...")
    path = os.path.join(SQL_DIR, "03_queries.sql")
    with open(path, "r", encoding="utf-8") as f:
        sql = f.read()
    view_blocks = re.findall(
        r'(DROP\s+VIEW\s+IF\s+EXISTS[^;]+;|CREATE\s+VIEW[^;]+;)',
        sql, re.DOTALL | re.IGNORECASE
    )
    cur = conn.cursor()
    for stmt in view_blocks:
        cur.execute(stmt)
    conn.commit()
    log("  OK Views da tao")

def verify(conn):
    log("\n[STEP 4] Kiem tra ket qua...")
    tables = [
        "customers", "orders", "order_items",
        "order_payments", "order_reviews",
        "products", "sellers", "product_categories", "geolocations"
    ]
    total = 0
    for t in tables:
        count = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        total += count
        log(f"  [{t:25s}] {count:>7,} rows")
    log(f"\n  TOTAL: {total:,} ban ghi trong relational tables")

    # Kiem tra view
    for v in ["v_review_order_features", "v_model_features_at_purchase",
              "v_model_features_post_delivery", "v_sales_monthly", "v_delivery_kpi",
              "v_category_performance", "v_customer_rfm",
              "v_seller_performance", "v_payment_mix"]:
        n = conn.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
        log(f"  [view] {v:30s} {n:>7,} rows")

def main():
    log("=" * 60)
    log("  BUILD: olist.db - ADY291c-AI2107-Group2")
    log("=" * 60)

    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        log(f"Deleted old DB: {DB_PATH}")

    conn = sqlite3.connect(TEMP_DB_PATH)
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = NORMAL")
>>>>>>> fa95e692592dcfa598d8ed69b0eb58d17bde67ff

    try:
        conn = sqlite3.connect(temp_db_path)
        conn.execute("PRAGMA synchronous = NORMAL")

        log("\n[STEP 0] Tao schema...")
        run_schema(conn, "01_schema.sql")
        log("  OK Schema tao xong")

        load_staging(conn)
        transform(conn)
        create_views(conn)
        verify(conn)

        conn.commit()
        size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
        log(f"\nDONE! File: {DB_PATH}")
        log(f"Size : {size_mb:.1f} MB")
        log("=" * 60)

    except Exception as e:
        if conn is not None:
            conn.rollback()
            conn.close()
        log(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    main()
