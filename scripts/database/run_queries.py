"""
run_queries.py — Thực thi và xuất kết quả phân tích 6 câu hỏi kinh doanh từ olist.db
Nhóm: ADY291c-AI2107-Group2
"""

import os
import sys
import sqlite3
import pandas as pd
import time

sys.stdout.reconfigure(encoding='utf-8')
sys.stderr.reconfigure(encoding='utf-8')

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DB_PATH = os.path.join(BASE_DIR, "data", "olist.db")
REPORT_PATH = os.path.join(BASE_DIR, "data", "processed", "sql_business_report.md")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA cache_size = -64000;")
    conn.execute("PRAGMA mmap_size = 268435456;")
    conn.execute("PRAGMA temp_store = MEMORY;")
    conn.execute("PRAGMA query_only = ON;")
    return conn

def run_query(conn, title, sql):
    print("\n" + "=" * 70)
    print(f"📊 {title}")
    print("=" * 70)
    t0 = time.time()
    df = pd.read_sql_query(sql, conn)
    dt = time.time() - t0
    print(f"⏱️  Thời gian thực thi: {dt:.3f}s | Số dòng kết quả: {len(df)}")
    print(df.to_string(index=False))
    return df

def main():
    if not os.path.exists(DB_PATH):
        print(f"❌ Không tìm thấy database tại: {DB_PATH}")
        return

    conn = get_connection()
    required_tables = (
        "customers",
        "orders",
        "order_items",
        "order_payments",
        "order_reviews",
        "products",
        "sellers",
    )
    empty_tables = [
        table
        for table in required_tables
        if conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0
    ]
    if empty_tables:
        conn.close()
        print(
            "❌ Database chưa có đủ dữ liệu "
            f"(bảng rỗng: {', '.join(empty_tables)}). "
            "Hãy chạy `python scripts\\database\\build_db.py` trước."
        )
        return

    reports = []

    print("🚀 BẮT ĐẦU TRUY VẤN DỮ LIỆU KINH DOANH TỪ OLIST.DB...")

    # BQ1: Doanh thu theo tháng
    q1 = """
    SELECT
        purchase_year_month,
        total_orders,
        total_revenue,
        avg_order_value,
        ROUND(total_revenue - LAG(total_revenue) OVER (ORDER BY purchase_year_month), 2) AS revenue_growth_mom
    FROM v_sales_monthly
    ORDER BY purchase_year_month;
    """
    df1 = run_query(conn, "BQ1: XU HƯỚNG TĂNG TRƯỞNG DOANH THU THEO THÁNG", q1)
    reports.append(("BQ1: Xu hướng Doanh thu theo Tháng", df1))

    # BQ2: Top 10 danh mục
    q2 = """
    SELECT
        category_english,
        total_orders,
        total_revenue,
        avg_price,
        avg_review_score,
        ROUND(100.0 * total_revenue / (SELECT SUM(total_revenue) FROM v_category_performance), 2) AS revenue_share_pct
    FROM v_category_performance
    ORDER BY total_revenue DESC
    LIMIT 10;
    """
    df2 = run_query(conn, "BQ2: TOP 10 DANH MỤC SẢN PHẨM THEO DOANH THU", q2)
    reports.append(("BQ2: Top 10 Danh mục Doanh thu", df2))

    # BQ3: Tỷ lệ giao trễ theo bang
    q3 = """
    SELECT
        customer_state,
        total_orders,
        late_orders,
        late_rate_pct,
        avg_delivery_days,
        avg_delay_days
    FROM v_delivery_kpi
    ORDER BY late_rate_pct DESC
    LIMIT 10;
    """
    df3 = run_query(conn, "BQ3: CHẤT LƯỢNG GIAO HÀNG & TỶ LỆ TRỄ (TOP 10 BANG TRỄ NHẤT)", q3)
    reports.append(("BQ3: Tỷ lệ Trễ theo Bang", df3))

    # BQ4: Review score vs Giao trễ
    q4 = """
    SELECT
        rv.review_score,
        COUNT(*)                                           AS total_reviews,
        ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct_of_reviews,
        ROUND(AVG(o.is_late) * 100.0, 2)                  AS late_rate_pct,
        ROUND(AVG(o.delivery_days), 2)                     AS avg_delivery_days,
        ROUND(AVG(o.delay_days), 2)                        AS avg_delay_days
    FROM orders o
    JOIN order_reviews rv ON o.order_id = rv.order_id
    GROUP BY rv.review_score
    ORDER BY rv.review_score;
    """
    df4 = run_query(conn, "BQ4: ẢNH HƯỞNG CỦA ĐỘ TRỄ GIAO HÀNG TỚI REVIEW SCORE", q4)
    reports.append(("BQ4: Review Score vs Trễ hạn", df4))

    # BQ5: Phương thức thanh toán
    q5 = """
    SELECT
        payment_type,
        total_transactions,
        pct_of_total,
        avg_value,
        avg_installments
    FROM v_payment_mix
    ORDER BY total_transactions DESC;
    """
    df5 = run_query(conn, "BQ5: CƠ CẤU PHƯƠNG THỨC THANH TOÁN & TRẢ GÓP", q5)
    reports.append(("BQ5: Phương thức Thanh toán", df5))

    # BQ6: Logistics cùng bang vs khác bang
    q6 = """
    SELECT
        CASE WHEN cu.customer_state = s.seller_state THEN 'Cùng Bang (Same State)' ELSE 'Khác Bang (Cross State)' END AS shipping_type,
        COUNT(DISTINCT oi.order_id)           AS total_orders,
        ROUND(AVG(oi.freight_value), 2)       AS avg_freight_fee,
        ROUND(AVG(o.delivery_days), 2)        AS avg_delivery_days,
        ROUND(100.0 * SUM(o.is_late) / COUNT(*), 2) AS late_rate_pct
    FROM order_items oi
    JOIN orders o   ON oi.order_id = o.order_id
    JOIN customers cu ON o.customer_id = cu.customer_id
    JOIN sellers s    ON oi.seller_id = s.seller_id
    WHERE o.delivery_days IS NOT NULL
    GROUP BY shipping_type;
    """
    df6 = run_query(conn, "BQ6: SO SÁNH LOGISTICS CÙNG BANG VS KHÁC BANG", q6)
    reports.append(("BQ6: Logistics Cùng Bang vs Khác Bang", df6))

    conn.close()

    # Xuất file báo cáo Markdown tổng hợp
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# 📈 Báo cáo Kết quả Phân tích Dữ liệu SQL (Business Insights)\n\n")
        f.write("**Dự án:** Phân tích Dữ liệu Thương mại Điện tử Olist (Brazil)\n")
        f.write("**Nguồn:** `data/olist.db` | **Nhóm:** ADY291c-AI2107-Group2\n\n---\n\n")
        for title, df in reports:
            f.write(f"### {title}\n\n")
            f.write(df.to_markdown(index=False))
            f.write("\n\n---\n\n")
    print(f"\n✅ Đã lưu toàn bộ báo cáo phân tích ra: {REPORT_PATH}")

if __name__ == "__main__":
    main()
