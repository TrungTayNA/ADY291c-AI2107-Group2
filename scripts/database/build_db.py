"""
build_db.py - Tao olist.db tu CSV da xu ly
Pattern: Staging -> Relational (3NF) -> Analytical Views

Cach chay: python scripts/database/build_db.py
"""

import sqlite3
import pandas as pd
import os
import re
import time

# Cau hinh duong dan
BASE_DIR    = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED   = os.path.join(BASE_DIR, "data", "processed")
SQL_DIR     = os.path.join(BASE_DIR, "sql")
DB_PATH     = os.path.join(BASE_DIR, "scripts", "database", "olist.db")
TEMP_DB_PATH = DB_PATH + ".tmp"

CSV_MAP = {
    "stg_customers":         "clean_olist_customers_dataset.csv",
    "stg_orders":            "clean_olist_orders_dataset.csv",
    "stg_order_items":       "clean_olist_order_items_dataset.csv",
    "stg_order_payments":    "clean_olist_order_payments_dataset.csv",
    "stg_order_reviews":     "clean_olist_order_reviews_dataset.csv",
    "stg_products":          "clean_olist_products_dataset.csv",
    "stg_sellers":           "clean_olist_sellers_dataset.csv",
    "stg_geolocations":      "clean_olist_geolocation_dataset.csv",
    "stg_product_categories":"clean_product_category_name_translation.csv",
}

def log(msg):
    print(msg, flush=True)

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
        clean = re.sub(r'--[^\n]*', '', stmt).strip()
        if not clean:
            continue
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            log(f"  [WARN] {e} | {stmt[:60]}")
    conn.commit()

def load_staging(conn):
    log("\n[STEP 1] Nap CSV vao Staging tables...")
    for table, csv_file in CSV_MAP.items():
        csv_path = os.path.join(PROCESSED, csv_file)
        if not os.path.exists(csv_path):
            log(f"  WARN: Khong tim thay: {csv_file}")
            continue
        t0 = time.time()
        df = pd.read_csv(csv_path, low_memory=False)
        # Ghi vao cung connection -> cung transaction voi phan transform
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
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            log(f"  [WARN] {e}")
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
    for v in ["view_order_clean", "v_sales_monthly", "v_delivery_kpi",
              "v_category_performance", "v_customer_rfm",
              "v_seller_performance", "v_payment_mix"]:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
            log(f"  [view] {v:30s} {n:>7,} rows")
        except sqlite3.OperationalError as e:
            log(f"  [WARN] {v}: {e}")

def main():
    log("=" * 60)
    log("  BUILD: olist.db - ADY291c-AI2107-Group2")
    log("=" * 60)

    for path in (TEMP_DB_PATH, TEMP_DB_PATH + "-shm", TEMP_DB_PATH + "-wal"):
        if os.path.exists(path):
            os.remove(path)

    conn = sqlite3.connect(TEMP_DB_PATH)
    conn.execute("PRAGMA journal_mode = DELETE")
    conn.execute("PRAGMA synchronous = NORMAL")

    try:
        log("\n[STEP 0] Tao schema...")
        run_schema(conn, "01_schema.sql")
        log("  OK Schema tao xong")

        load_staging(conn)
        transform(conn)
        create_views(conn)
        verify(conn)

        conn.commit()
        conn.close()
        conn = None

        replaced = False
        for attempt in range(20):
            try:
                os.replace(TEMP_DB_PATH, DB_PATH)
                replaced = True
                break
            except PermissionError:
                if attempt == 19:
                    raise RuntimeError(
                        f"Cannot replace {DB_PATH}: the database is locked by another process. "
                        "Close Streamlit, database viewers, Python scripts, or VS Code SQLite extensions, then run build_db.py again."
                    )
                log(f"  Database is locked; retrying replacement ({attempt + 1}/20)...")
                time.sleep(0.25)

        if not replaced:
            raise RuntimeError("Database replacement failed")

        size_mb = os.path.getsize(DB_PATH) / 1024 / 1024
        log(f"\nDONE! File: {DB_PATH}")
        log(f"Size : {size_mb:.1f} MB")
        log("=" * 60)

    except Exception as e:
        conn.rollback()
        log(f"\nERROR: {e}")
        import traceback; traceback.print_exc()
        raise
    finally:
        if conn is not None:
            conn.close()

if __name__ == "__main__":
    main()
