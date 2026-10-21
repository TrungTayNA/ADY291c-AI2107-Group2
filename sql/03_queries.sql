-- ============================================================
-- SQL DATA WRANGLING & ANALYTICS QUERIES
-- Target DBMS : SQLite 3.x
-- Dataset     : Olist Brazilian E-Commerce (2016-2018)
-- Nhóm        : ADY291c-AI2107-Group2
-- ============================================================

-- Tối ưu hoá bộ đệm & hiệu năng đọc cho SQLite
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA cache_size   = -64000;      -- 64MB Cache bộ nhớ
PRAGMA mmap_size    = 268435456;   -- 256MB Memory-mapped I/O
PRAGMA temp_store   = MEMORY;

-- ============================================================
-- PHẦN 1: KIỂM TRA THỐNG KÊ TỔNG QUAN (DB HEALTH CHECK)
-- ============================================================

-- 1.1 Thống kê số lượng bản ghi trên từng bảng
SELECT 'customers'          AS table_name, COUNT(*) AS total_rows FROM customers
UNION ALL
SELECT 'orders',                           COUNT(*) FROM orders
UNION ALL
SELECT 'order_items',                      COUNT(*) FROM order_items
UNION ALL
SELECT 'order_payments',                   COUNT(*) FROM order_payments
UNION ALL
SELECT 'order_reviews',                    COUNT(*) FROM order_reviews
UNION ALL
SELECT 'products',                         COUNT(*) FROM products
UNION ALL
SELECT 'sellers',                          COUNT(*) FROM sellers
UNION ALL
SELECT 'product_categories',              COUNT(*) FROM product_categories
UNION ALL
SELECT 'geolocations',                     COUNT(*) FROM geolocations;

-- 1.2 Phạm vi thời gian dữ liệu
SELECT
    MIN(order_purchase_timestamp) AS earliest_order,
    MAX(order_purchase_timestamp) AS latest_order,
    COUNT(DISTINCT purchase_year) AS num_years
FROM orders;

-- 1.3 Tỷ lệ đơn hàng trễ tổng thể
SELECT
    COUNT(*)                                         AS total_orders,
    SUM(is_late)                                     AS late_orders,
    ROUND(100.0 * SUM(is_late) / COUNT(*), 2)        AS late_rate_pct,
    ROUND(AVG(delivery_days), 2)                     AS avg_delivery_days,
    ROUND(AVG(delay_days), 2)                        AS avg_delay_days
FROM orders;


-- ============================================================
-- PHẦN 2: CHUẨN HÓA & TRÍCH XUẤT ĐẶC TRƯNG (CLEAN VIEW)
-- ============================================================

-- View tổng hợp (tương đương view_pr_clean của Group3)
-- Kết hợp các thực thể thành 1 view phẳng phục vụ tra cứu chi tiết
DROP VIEW IF EXISTS view_order_clean;
CREATE VIEW view_order_clean AS
SELECT
    -- Đơn hàng
    o.order_id,
    o.order_purchase_timestamp,
    o.purchase_year,
    o.purchase_month,
    o.purchase_year_month,
    CASE o.purchase_weekday
        WHEN 0 THEN 'Monday'   WHEN 1 THEN 'Tuesday'
        WHEN 2 THEN 'Wednesday'WHEN 3 THEN 'Thursday'
        WHEN 4 THEN 'Friday'   WHEN 5 THEN 'Saturday'
        ELSE 'Sunday'
    END AS purchase_weekday_name,
    o.purchase_hour,
    o.delivery_days,
    o.delay_days,
    o.is_late,

    -- Khách hàng
    cu.customer_unique_id,
    cu.customer_state,
    cu.customer_city,

    -- Sản phẩm & Danh mục
    p.product_id,
    COALESCE(cat.product_category_name_english,
             p.product_category_name, 'unknown') AS category_english,
    p.product_weight_g,
    p.product_volume_cm3,

    -- Người bán
    s.seller_id,
    s.seller_state,
    CASE WHEN cu.customer_state = s.seller_state THEN 1 ELSE 0 END AS same_state,

    -- Giá trị đơn hàng
    oi.price,
    oi.freight_value,
    oi.item_total,
    oi.is_price_outlier,

    -- Thanh toán
    pay.payment_type,
    pay.payment_value,
    pay.payment_installments,

    -- Đánh giá
    rv.review_score,
    rv.has_comment,
    COALESCE(rv.review_comment_message, 'No Comment') AS review_comment

FROM orders o
JOIN customers  cu  ON o.customer_id   = cu.customer_id
JOIN order_items oi ON o.order_id      = oi.order_id
JOIN products   p   ON oi.product_id   = p.product_id
JOIN sellers    s   ON oi.seller_id    = s.seller_id
LEFT JOIN product_categories cat ON p.product_category_name = cat.product_category_name
LEFT JOIN order_payments pay     ON o.order_id = pay.order_id AND pay.payment_sequential = 1
LEFT JOIN order_reviews  rv      ON o.order_id = rv.order_id;


-- ============================================================
-- PHẦN 3: PHÂN TÍCH 6 CÂU HỎI KINH DOANH TRỌNG TÂM (BUSINESS QUERIES)
-- ============================================================

-- ── Câu hỏi 1: Xu hướng tăng trưởng doanh thu & đơn hàng theo tháng ──
-- Doanh thu tăng trưởng ra sao theo thời gian? Tháng nào đạt đỉnh?
-- Sử dụng View v_sales_monthly tối ưu hóa aggregation
SELECT
    purchase_year_month,
    purchase_year,
    purchase_month,
    total_orders,
    total_revenue,
    avg_order_value,
    ROUND(total_revenue - LAG(total_revenue) OVER (ORDER BY purchase_year_month), 2) AS revenue_growth_mom
FROM v_sales_monthly
ORDER BY purchase_year_month;

-- ── Câu hỏi 2: Top 10 danh mục sản phẩm đóng góp doanh thu lớn nhất ──
-- Danh mục nào là "ngựa chiến" (hero category)? Điểm review trung bình?
-- Sử dụng View v_category_performance
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

-- ── Câu hỏi 3: Đánh giá chất lượng giao hàng & tỷ lệ trễ theo bang ──
-- Bang nào có tỷ lệ trễ đơn cao nhất? Thời gian giao hàng trung bình?
-- Sử dụng View v_delivery_kpi
SELECT
    customer_state,
    total_orders,
    late_orders,
    late_rate_pct,
    avg_delivery_days,
    avg_delay_days
FROM v_delivery_kpi
ORDER BY late_rate_pct DESC;

-- ── Câu hỏi 4: Tương quan giữa độ trễ giao hàng và điểm hài lòng (Review Score) ──
-- Khách hàng đánh giá thế nào khi đơn hàng bị giao trễ?
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

-- ── Câu hỏi 5: Cơ cấu phương thức thanh toán & hành vi trả góp ──
-- Khách chuộng hình thức nào nhất? Tỷ lệ trả góp và giá trị đơn?
-- Sử dụng View v_payment_mix
SELECT
    payment_type,
    total_transactions,
    pct_of_total,
    avg_value,
    avg_installments
FROM v_payment_mix
ORDER BY total_transactions DESC;

-- ── Câu hỏi 6: Tác động của Logistics nội bang (Same State vs Different State) ──
-- Mua cùng bang vs khác bang ảnh hưởng thế nào đến phí ship và thời gian nhận?
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


-- ============================================================
-- PHẦN 4: TRUY VẤN DỮ LIỆU ĐẶC TRƯNG CHO MACHINE LEARNING
-- ============================================================

-- 4.1 Dữ liệu RFM hoàn chỉnh cho K-Means Customer Clustering
-- Sử dụng trực tiếp View v_customer_rfm đã chuẩn hóa
SELECT
    customer_unique_id,
    customer_state,
    CAST(
        julianday('2018-10-18') - julianday(last_purchase_date)
    AS INTEGER) AS recency_days,
    frequency,
    monetary
FROM v_customer_rfm
ORDER BY monetary DESC
LIMIT 20;

-- 4.2 Feature set chuẩn bị cho Regression (dự đoán review_score & delay_days)
SELECT
    o.order_id,
    rv.review_score,
    o.delivery_days,
    o.delay_days,
    o.is_late,
    o.purchase_month,
    o.purchase_hour,
    o.purchase_weekday,
    oi.price,
    oi.freight_value,
    pay.payment_installments,
    p.product_weight_g,
    p.product_volume_cm3,
    CASE WHEN cu.customer_state = s.seller_state THEN 1 ELSE 0 END AS same_state
FROM orders o
JOIN customers cu   ON o.customer_id = cu.customer_id
JOIN order_items oi ON o.order_id = oi.order_id
JOIN products p     ON oi.product_id = p.product_id
JOIN sellers s      ON oi.seller_id = s.seller_id
JOIN order_reviews rv ON o.order_id = rv.order_id
LEFT JOIN order_payments pay ON o.order_id = pay.order_id AND pay.payment_sequential = 1
WHERE o.delivery_days IS NOT NULL
  AND rv.review_score IS NOT NULL
LIMIT 10;
