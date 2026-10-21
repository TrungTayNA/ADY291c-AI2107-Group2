"""
build_db.py - Tao olist.db tu CSV da xu ly
Pattern: Schema (conn1) → Load CSV staging (conn2) → Transform → Views

Cach chay: python scripts/database/build_db.py
"""

import sqlite3
import pandas as pd
import os
import re
import time

BASE_DIR   = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
PROCESSED  = os.path.join(BASE_DIR, "data", "processed")
SQL_DIR    = os.path.join(BASE_DIR, "sql")
DB_PATH    = os.path.join(BASE_DIR, "data", "olist.db")

CSV_MAP = {
    "stg_customers":          "clean_olist_customers_dataset.csv",
    "stg_orders":             "clean_olist_orders_dataset.csv",
    "stg_order_items":        "clean_olist_order_items_dataset.csv",
    "stg_order_payments":     "clean_olist_order_payments_dataset.csv",
    "stg_order_reviews":      "clean_olist_order_reviews_dataset.csv",
    "stg_products":           "clean_olist_products_dataset.csv",
    "stg_sellers":            "clean_olist_sellers_dataset.csv",
    "stg_geolocations":       "clean_olist_geolocation_dataset.csv",
    "stg_product_categories": "clean_product_category_name_translation.csv",
}

# Thứ tự INSERT theo FK dependency
TRANSFORM_ORDER = [
    "stg_product_categories",
    "stg_geolocations",
    "stg_sellers",
    "stg_customers",
    "stg_products",
    "stg_orders",
    "stg_order_items",
    "stg_order_payments",
    "stg_order_reviews",
]

def log(msg):
    print(msg, flush=True)

def read_sql(filename):
    path = os.path.join(SQL_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()

# ──────────────────────────────────────────────
# BƯỚC 0: Xoa DB cu, tao schema sach
# ──────────────────────────────────────────────
def step0_create_schema():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        log(f"Deleted: {DB_PATH}")

    # executescript() OK cho DDL-only (khong co data nao bi mat)
    conn = sqlite3.connect(DB_PATH)
    conn.executescript(read_sql("01_schema.sql"))
    conn.close()
    log("Schema created (conn closed cleanly)")

# ──────────────────────────────────────────────
# BƯỚC 1+2: Load CSV + Transform trong CUNG conn
# Key insight: pandas.to_sql va INSERT..SELECT
# phai chay trong cung connection de thay nhau
# KHONG dung executescript() sau khi pandas ghi
# ──────────────────────────────────────────────
def step1_load_staging(conn):
    log("\n[STEP 1] Load CSV -> Staging...")
    for table, csv_file in CSV_MAP.items():
        path = os.path.join(PROCESSED, csv_file)
        if not os.path.exists(path):
            log(f"  WARN: {csv_file} not found"); continue
        t0 = time.time()
        df = pd.read_csv(path, low_memory=False)
        # if_exists='replace' -> DROP + CREATE + INSERT trong cung conn
        df.to_sql(table, conn, if_exists="replace", index=False, chunksize=5000)
        log(f"  OK {table:32s} -> {len(df):>7,} rows ({time.time()-t0:.1f}s)")

def step2_transform(conn):
    log("\n[STEP 2] Transform Staging -> Relational...")
    sql = read_sql("02_load_data.sql")

    # Tach tung statement, BAN THUONG execute (khong dung executescript)
    cur = conn.cursor()
    stmts = [s.strip() for s in sql.split(";") if s.strip()]
    for stmt in stmts:
        clean = re.sub(r'--[^\n]*', '', stmt).strip()
        if not clean:
            continue
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            log(f"  WARN: {e} | {stmt[:50]}")
    conn.commit()
    log("  OK Transform done")

def step3_create_views(conn):
    log("\n[STEP 3] Create analytical views...")
    sql = read_sql("03_queries.sql")
    # Chi lay DROP VIEW / CREATE VIEW blocks
    view_stmts = re.findall(
        r'(DROP\s+VIEW\s+IF\s+EXISTS[^;]+;|CREATE\s+VIEW[^;]+;)',
        sql, re.DOTALL | re.IGNORECASE
    )
    cur = conn.cursor()
    for stmt in view_stmts:
        try:
            cur.execute(stmt)
        except sqlite3.OperationalError as e:
            log(f"  WARN: {e}")
    conn.commit()
    log(f"  OK {len(view_stmts)} view statements executed")

def step4_verify(conn):
    log("\n[STEP 4] Verify...")
    tables = ["customers","orders","order_items","order_payments",
              "order_reviews","products","sellers","product_categories","geolocations"]
    total = 0
    for t in tables:
        n = conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        total += n
        log(f"  [{t:25s}] {n:>8,}")
    log(f"\n  TOTAL relational: {total:,}")

    views = ["view_order_clean","v_sales_monthly","v_delivery_kpi",
             "v_category_performance","v_customer_rfm","v_seller_performance","v_payment_mix"]
    for v in views:
        try:
            n = conn.execute(f"SELECT COUNT(*) FROM {v}").fetchone()[0]
            log(f"  [view] {v:30s} {n:>8,}")
        except Exception as e:
            log(f"  [view] {v}: WARN {e}")

def main():
    log("="*60)
    log("  BUILD olist.db - ADY291c-AI2107-Group2")
    log("="*60)

    # Step 0: tao schema trong conn rieng, dong lai
    log("\n[STEP 0] Create schema...")
    step0_create_schema()
    log("  OK Schema done")

    # Steps 1-3: tat ca trong MOT connection
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA synchronous  = NORMAL")
    conn.execute("PRAGMA foreign_keys = OFF")  # OFF trong luc bulk load

    try:
        step1_load_staging(conn)
        step2_transform(conn)
        step3_create_views(conn)

        conn.execute("PRAGMA foreign_keys = ON")
        conn.commit()

        step4_verify(conn)

        size = os.path.getsize(DB_PATH) / 1024 / 1024
        log(f"\nDONE: {DB_PATH}")
        log(f"Size: {size:.1f} MB")
        log("="*60)

    except Exception as e:
        conn.rollback()
        log(f"ERROR: {e}")
        import traceback; traceback.print_exc()
    finally:
        conn.close()

if __name__ == "__main__":
    main()
