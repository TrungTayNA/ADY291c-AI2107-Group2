"""
run_queries.py - Chay 10 cau truy van SQL Q01-Q10 va xuat bao cao Markdown.
Nhom: ADY291c-AI2107-Group2
"""

import os
import sqlite3
import sys
import time
from pathlib import Path

import pandas as pd


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "data" / "olist.db"
SQL_PATH = BASE_DIR / "sql" / "03_queries.sql"
REPORT_PATH = BASE_DIR / "data" / "processed" / "sql_business_report.md"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA cache_size = -64000")
    conn.execute("PRAGMA mmap_size = 268435456")
    conn.execute("PRAGMA temp_store = MEMORY")
    return conn


def run_query(conn, title, sql, max_rows=50):
    print("\n" + "=" * 70)
    print(f"{title}")
    print("=" * 70)

    started_at = time.time()
    df = pd.read_sql_query(sql, conn)
    elapsed = time.time() - started_at

    print(f"Thoi gian thuc hien: {elapsed:.3f}s | So dong: {len(df)}")
    print(df.head(max_rows).to_string(index=False))
    if len(df) > max_rows:
        print(f"... con {len(df) - max_rows} dong trong bao cao Markdown")
    return df




def initialize_views(conn):
    if not SQL_PATH.exists():
        raise FileNotFoundError(f"Khong tim thay {SQL_PATH}")
    conn.executescript(SQL_PATH.read_text(encoding="utf-8"))


QUERIES = [
    (
        "Q01: Ngay le va dip dac biet co lam luong mua tang?",
        """
        WITH special_dates(special_date, special_name) AS (
            VALUES
                ('2017-02-27','Carnival'), ('2017-02-28','Carnival'),
                ('2017-11-24','Black Friday'), ('2017-12-25','Giang sinh'),
                ('2018-02-12','Carnival'), ('2018-02-13','Carnival'),
                ('2018-03-30','Good Friday'), ('2018-05-31','Corpus Christi'),
                ('2018-11-23','Black Friday'), ('2018-12-25','Giang sinh')
        ),
        daily_orders AS (
            SELECT date(order_purchase_timestamp) AS purchase_date,
                   COUNT(DISTINCT order_id) AS order_count
            FROM orders
            GROUP BY date(order_purchase_timestamp)
        ),
        normal_by_year AS (
            SELECT substr(purchase_date, 1, 4) AS purchase_year,
                   AVG(order_count) AS avg_order_count
            FROM daily_orders
            WHERE purchase_date NOT IN (
                SELECT special_date FROM special_dates
            )
            GROUP BY substr(purchase_date, 1, 4)
        )
        SELECT d.purchase_date,
               s.special_name,
               d.order_count,
               ROUND(n.avg_order_count, 2) AS avg_normal_orders,
               ROUND(100.0 * (d.order_count - n.avg_order_count)
                     / NULLIF(n.avg_order_count, 0), 2) AS pct_vs_normal_days
        FROM daily_orders d
        JOIN special_dates s ON s.special_date = d.purchase_date
        JOIN normal_by_year n
          ON n.purchase_year = substr(d.purchase_date, 1, 4)
        ORDER BY d.order_count DESC, d.purchase_date;
        """,
    ),
    (
        "Q02: Phat hien ngay dot bien doanh so",
        """
        WITH daily_orders AS (
            SELECT date(order_purchase_timestamp) AS purchase_date,
                   COUNT(DISTINCT order_id) AS order_count
            FROM orders
            GROUP BY date(order_purchase_timestamp)
        ),
        baseline AS (
            SELECT purchase_date,
                   order_count,
                   AVG(order_count) OVER (
                       ORDER BY purchase_date
                       ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
                   ) AS prior_28d_avg
            FROM daily_orders
        )
        SELECT purchase_date,
               order_count,
               ROUND(prior_28d_avg, 2) AS prior_28d_avg,
               ROUND(100.0 * (order_count - prior_28d_avg)
                     / NULLIF(prior_28d_avg, 0), 2) AS spike_pct
        FROM baseline
        WHERE prior_28d_avg IS NOT NULL
          AND order_count >= 1.50 * prior_28d_avg
        ORDER BY spike_pct DESC, purchase_date;
        """,
    ),
    (
        "Q03: Phan bo review_score va mat can bang lop",
        """
        SELECT review_score,
               COUNT(*) AS order_count,
               ROUND(100.0 * COUNT(*) /
                     (SELECT COUNT(*) FROM v_review_order_features), 2) AS percentage
        FROM v_review_order_features
        GROUP BY review_score
        ORDER BY review_score;
        """,
    ),
    (
        "Q04: Don giao tre co review thap hon don dung han?",
        """
        SELECT CASE WHEN is_late = 1 THEN 'Giao tre'
                    ELSE 'Dung han hoac som' END AS delivery_group,
               COUNT(*) AS order_count,
               ROUND(AVG(review_score), 2) AS avg_review_score,
               ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
               ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
        FROM v_review_order_features
        GROUP BY is_late
        ORDER BY delivery_group;
        """,
    ),
    (
        "Q05: Muc do tre 1-3 ngay, 4-7 ngay va tren 7 ngay",
        """
        SELECT CASE
                   WHEN delay_days <= 0 THEN 'Som hoac dung han'
                   WHEN delay_days <= 3 THEN 'Tre 1-3 ngay'
                   WHEN delay_days <= 7 THEN 'Tre 4-7 ngay'
                   ELSE 'Tre tren 7 ngay'
               END AS delay_group,
               COUNT(*) AS order_count,
               ROUND(AVG(review_score), 2) AS avg_review_score,
               ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct
        FROM v_review_order_features
        WHERE delay_days IS NOT NULL
        GROUP BY delay_group
        ORDER BY MIN(CASE
                         WHEN delay_days <= 0 THEN 0
                         WHEN delay_days <= 3 THEN 1
                         WHEN delay_days <= 7 THEN 2
                         ELSE 3 END);
        """,
    ),
    (
        "Q06: Phi van chuyen va ty le phi/gia hang anh huong review?",
        """
        WITH freight_quartiles AS (
            SELECT *,
                   NTILE(4) OVER (ORDER BY total_freight) AS group_number
            FROM v_review_order_features
        ),
        ratio_quartiles AS (
            SELECT *,
                   NTILE(4) OVER (ORDER BY freight_to_price_pct) AS group_number
            FROM v_review_order_features
            WHERE freight_to_price_pct IS NOT NULL
        )
        SELECT 'Tong phi ship' AS metric,
               group_number,
               COUNT(*) AS order_count,
               ROUND(AVG(total_freight), 2) AS avg_value,
               ROUND(AVG(review_score), 2) AS avg_review_score
        FROM freight_quartiles
        GROUP BY group_number
        UNION ALL
        SELECT 'Ty le phi/gia hang' AS metric,
               group_number,
               COUNT(*) AS order_count,
               ROUND(AVG(freight_to_price_pct), 2) AS avg_value,
               ROUND(AVG(review_score), 2) AS avg_review_score
        FROM ratio_quartiles
        GROUP BY group_number
        ORDER BY metric, group_number;
        """,
    ),
    (
        "Q07: Do phuc tap don hang theo mat hang va nguoi ban",
        """
        SELECT CASE
                   WHEN item_count = 1 THEN '1 mat hang'
                   WHEN item_count BETWEEN 2 AND 3 THEN '2-3 mat hang'
                   ELSE '4+ mat hang'
               END AS basket_group,
               CASE WHEN seller_count = 1 THEN '1 nguoi ban'
                    ELSE 'Nhieu nguoi ban' END AS seller_group,
               COUNT(*) AS order_count,
               ROUND(AVG(review_score), 2) AS avg_review_score,
               ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
        FROM v_review_order_features
        GROUP BY basket_group, seller_group
        ORDER BY MIN(item_count), MIN(seller_count);
        """,
    ),
    (
        "Q08: Phuong thuc thanh toan va so ky tra gop lien quan review?",
        """
        SELECT first_payment_type AS payment_type,
               COUNT(*) AS order_count,
               ROUND(AVG(max_installments), 2) AS avg_installments,
               ROUND(AVG(review_score), 2) AS avg_review_score,
               ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
        FROM v_review_order_features
        WHERE first_payment_type IS NOT NULL
        GROUP BY first_payment_type
        ORDER BY order_count DESC;
        """,
    ),
    (
        "Q09: Xu huong review_score theo thang",
        """
        SELECT purchase_year_month,
               COUNT(*) AS order_count,
               ROUND(AVG(review_score), 2) AS avg_review_score,
               ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
               ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
        FROM v_review_order_features
        GROUP BY purchase_year_month
        ORDER BY purchase_year_month;
        """,
    ),
    (
        "Q10: Phan hoa muc do hai long theo bang/khu vuc",
        """
        SELECT customer_state,
               COUNT(*) AS order_count,
               ROUND(AVG(review_score), 2) AS avg_review_score,
               ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
               ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct,
               ROUND(AVG(is_late) * 100.0, 2) AS late_rate_pct,
               ROUND(AVG(delivery_days), 2) AS avg_delivery_days
        FROM v_review_order_features
        GROUP BY customer_state
        HAVING COUNT(*) >= 100
        ORDER BY avg_review_score ASC, low_score_pct DESC;
        """,
    ),
]


def main():
    if not DB_PATH.exists():
        print(f"Khong tim thay database: {DB_PATH}")
        print("Hay chay: python scripts\\database\\build_db.py")
        return

    conn = get_connection()
    required_tables = (
        "customers", "orders", "order_items", "order_payments",
        "order_reviews", "products", "sellers",
    )
    empty_tables = [
        table for table in required_tables
        if conn.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0] == 0
    ]
    if empty_tables:
        conn.close()
        print("Database chua co du du lieu: " + ", ".join(empty_tables))
        print("Hay chay: python scripts\\database\\build_db.py")
        return

    initialize_views(conn)

    reports = []
    print("BAT DAU 10 CÂU TRUY VAN SQL Q01-Q10...")
    for title, sql in QUERIES:
        reports.append((title, run_query(conn, title, sql)))

    
    conn.close()


if __name__ == "__main__":
    main()
