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

def run_query(conn, title, sql, max_rows=50):
    print("\n" + "=" * 70)
    print(f"📊 {title}")
    print("=" * 70)
    t0 = time.time()
    df = pd.read_sql_query(sql, conn)
    dt = time.time() - t0
    print(f"⏱️  Thời gian thực thi: {dt:.3f}s | Số dòng kết quả: {len(df)}")
    print(df.head(max_rows).to_string(index=False))
    if len(df) > max_rows:
        print(f"... còn {len(df) - max_rows} dòng, xem bảng đầy đủ trong báo cáo Markdown")
    return df


def export_report(reports):
    os.makedirs(os.path.dirname(REPORT_PATH), exist_ok=True)
    with open(REPORT_PATH, "w", encoding="utf-8") as f:
        f.write("# Báo cáo truy vấn SQL - Olist\n\n")
        for title, df in reports:
            f.write(f"## {title}\n\n")
            f.write(f"Số dòng kết quả: {len(df)}\n\n")
            f.write(df.to_markdown(index=False))
            f.write("\n\n")
    print(f"\nĐã xuất báo cáo SQL: {REPORT_PATH}")

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

    # BQ7: Phân bố review score
    q7 = """
    SELECT
        review_score,
        COUNT(*) AS order_count,
        ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM v_review_order_features), 2) AS percentage
    FROM v_review_order_features
    GROUP BY review_score
    ORDER BY review_score;
    """
    df7 = run_query(conn, "BQ7: PHÂN BỐ REVIEW SCORE Ở CẤP ĐƠN HÀNG", q7)
    reports.append(("BQ7: Phân bố Review Score", df7))

    # BQ8: Đơn trễ và đúng hạn/sớm
    q8 = """
    SELECT
        CASE WHEN is_late = 1 THEN 'Giao trễ'
             ELSE 'Đúng hạn hoặc sớm'
        END AS delivery_group,
        COUNT(*) AS order_count,
        ROUND(AVG(review_score), 2) AS avg_review_score,
        ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS low_score_rate_pct
    FROM v_review_order_features
    GROUP BY is_late;
    """
    df8 = run_query(conn, "BQ8: REVIEW SCORE THEO TRẠNG THÁI ĐÚNG HẠN/HAY TRỄ", q8)
    reports.append(("BQ8: Review theo Trạng thái Giao hàng", df8))

    # BQ9: Nhóm mức độ trễ theo ngày
    q9 = """
    SELECT
        CASE
            WHEN delay_days <= 0 THEN 'Sớm hoặc đúng hạn'
            WHEN delay_days <= 3 THEN 'Trễ 1-3 ngày'
            WHEN delay_days <= 7 THEN 'Trễ 4-7 ngày'
            ELSE 'Trễ trên 7 ngày'
        END AS delay_group,
        COUNT(*) AS order_count,
        ROUND(AVG(review_score), 2) AS avg_review_score
    FROM v_review_order_features
    WHERE delay_days IS NOT NULL
    GROUP BY delay_group
    ORDER BY MIN(delay_days);
    """
    df9 = run_query(conn, "BQ9: REVIEW SCORE THEO MỨC ĐỘ TRỄ", q9)
    reports.append(("BQ9: Review theo Mức độ Trễ", df9))

    # BQ10: Phí vận chuyển theo quartile
    q10 = """
    WITH freight_groups AS (
        SELECT
            review_score,
            total_freight,
            NTILE(4) OVER (ORDER BY total_freight) AS freight_quartile
        FROM v_review_order_features
        WHERE total_freight IS NOT NULL
    )
    SELECT
        freight_quartile,
        COUNT(*) AS order_count,
        ROUND(AVG(total_freight), 2) AS avg_freight,
        ROUND(AVG(review_score), 2) AS avg_review_score
    FROM freight_groups
    GROUP BY freight_quartile
    ORDER BY freight_quartile;
    """
    df10 = run_query(conn, "BQ10: REVIEW SCORE THEO PHÍ VẬN CHUYỂN", q10)
    reports.append(("BQ10: Review theo Phí vận chuyển", df10))

    # BQ11: Phức tạp giỏ hàng
    q11 = """
    SELECT
        CASE
            WHEN item_count = 1 THEN '1 mặt hàng'
            WHEN item_count BETWEEN 2 AND 3 THEN '2-3 mặt hàng'
            ELSE '4 mặt hàng trở lên'
        END AS basket_size,
        COUNT(*) AS order_count,
        ROUND(AVG(review_score), 2) AS avg_review_score
    FROM v_review_order_features
    WHERE item_count IS NOT NULL
    GROUP BY basket_size
    ORDER BY MIN(item_count);
    """
    df11 = run_query(conn, "BQ11: REVIEW SCORE THEO ĐỘ PHỨC TẠP ĐƠN HÀNG", q11)
    reports.append(("BQ11: Review theo Số mặt hàng", df11))

    # BQ12: Phương thức thanh toán đại diện
    q12 = """
    SELECT
        first_payment_type,
        COUNT(*) AS order_count,
        ROUND(AVG(review_score), 2) AS avg_review_score
    FROM v_review_order_features
    WHERE first_payment_type IS NOT NULL
    GROUP BY first_payment_type
    ORDER BY order_count DESC;
    """
    df12 = run_query(conn, "BQ12: REVIEW SCORE THEO PHƯƠNG THỨC THANH TOÁN", q12)
    reports.append(("BQ12: Review theo Thanh toán", df12))

    # BQ13: Điểm đánh giá theo bang
    q13 = """
    SELECT
        customer_state,
        COUNT(*) AS order_count,
        ROUND(AVG(review_score), 2) AS avg_review_score,
        ROUND(100.0 * SUM(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END) / COUNT(*), 2) AS low_score_rate_pct
    FROM v_review_order_features
    GROUP BY customer_state
    HAVING COUNT(*) >= 100
    ORDER BY low_score_rate_pct DESC;
    """
    df13 = run_query(conn, "BQ13: REVIEW SCORE THEO KHU VỰC KHÁCH HÀNG", q13)
    reports.append(("BQ13: Review theo Bang Khách hàng", df13))

    # BQ14: Dataset cấp đơn hàng cho model
    q14 = """
    SELECT
        review_score AS target,
        purchase_hour,
        customer_state,
        delivery_days,
        delay_days,
        is_late,
        item_count,
        distinct_products,
        seller_count,
        total_item_price,
        total_freight,
        total_paid,
        payment_count,
        max_installments,
        first_payment_type
    FROM v_review_order_features;
    """
    df14 = run_query(conn, "BQ14: DATASET FEATURES CẤP ĐƠN HÀNG CHO MODEL", q14, max_rows=20)
    reports.append(("BQ14: Dataset Features cho Model", df14))

    export_report(reports)
    conn.close()



if __name__ == "__main__":
    main()
