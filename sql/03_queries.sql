-- ============================================================
-- SQL DATA WRANGLING & ANALYTICS QUERIES
-- Target DBMS : SQLite 3.x
-- Dataset     : Olist Brazilian E-Commerce (2016-2018)
-- Nhóm        : ADY291c-AI2107-Group2
-- ============================================================

PRAGMA foreign_keys = ON;

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
-- Kết hợp tất cả bảng thành 1 view phân tích đầy đủ
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
-- PHẦN 3: PHÂN TÍCH 5 CÂU HỎI KINH DOANH
-- ============================================================

-- ── Câu hỏi 1: Xu hướng doanh thu theo thời gian ────────────
-- Doanh thu tăng hay giảm? Tháng nào bán tốt nhất?
SELECT
    purchase_year_month,
    COUNT(DISTINCT order_id)          AS total_orders,
    ROUND(SUM(payment_value), 2)      AS total_revenue,
    ROUND(AVG(payment_value), 2)      AS avg_order_value
FROM view_order_clean
GROUP BY purchase_year_month
ORDER BY purchase_year_month;

-- ── Câu hỏi 2: Top 10 danh mục sản phẩm theo doanh thu ──────
-- Danh mục nào đóng góp nhiều nhất? So sánh doanh thu vs số đơn.
SELECT
    category_english,
    COUNT(DISTINCT order_id)         AS total_orders,
    ROUND(SUM(item_total), 2)        AS total_revenue,
    ROUND(AVG(price), 2)             AS avg_price,
    ROUND(AVG(review_score), 2)      AS avg_review_score
FROM view_order_clean
GROUP BY category_english
ORDER BY total_revenue DESC
LIMIT 10;

-- ── Câu hỏi 3: Phân tích giao hàng trễ theo bang ────────────
-- Bang nào có tỷ lệ trễ cao nhất? Thời gian giao hàng trung bình?
SELECT
    customer_state,
    COUNT(DISTINCT order_id)                          AS total_orders,
    SUM(is_late)                                      AS late_orders,
    ROUND(100.0 * SUM(is_late) / COUNT(*), 2)         AS late_rate_pct,
    ROUND(AVG(delivery_days), 2)                      AS avg_delivery_days,
    ROUND(AVG(delay_days), 2)                         AS avg_delay_days
FROM view_order_clean
GROUP BY customer_state
ORDER BY late_rate_pct DESC;

-- ── Câu hỏi 4: Phân bố review score & mức độ hài lòng ───────
-- Phân bố điểm đánh giá như thế nào? Liên quan tới trễ hàng?
SELECT
    review_score,
    COUNT(*)                                           AS total_reviews,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct,
    ROUND(AVG(is_late), 2)                             AS avg_late_rate,
    ROUND(AVG(delivery_days), 2)                       AS avg_delivery_days
FROM view_order_clean
WHERE review_score IS NOT NULL
GROUP BY review_score
ORDER BY review_score;

-- ── Câu hỏi 5: Phương thức thanh toán & hành vi mua sắm ──────
-- Credit card vs boleto ảnh hưởng tới giá trị đơn & trả góp?
SELECT
    payment_type,
    COUNT(DISTINCT order_id)                               AS total_orders,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2)     AS pct_of_total,
    ROUND(AVG(payment_value), 2)                           AS avg_payment_value,
    ROUND(AVG(payment_installments), 2)                    AS avg_installments,
    ROUND(AVG(review_score), 2)                            AS avg_review_score
FROM view_order_clean
WHERE payment_type IS NOT NULL
GROUP BY payment_type
ORDER BY total_orders DESC;


-- ============================================================
-- PHẦN 4: QUERIES HỖ TRỢ MÔ HÌNH ML (Notebook 05)
-- ============================================================

-- 4.1 Dữ liệu RFM cho K-Means Clustering
SELECT
    customer_unique_id,
    customer_state,
    -- Recency: số ngày kể từ lần mua cuối (tương đối)
    CAST(
        (julianday('2018-10-18') -
         julianday(MAX(order_purchase_timestamp))) AS INTEGER
    ) AS recency_days,
    -- Frequency: số đơn hàng
    COUNT(DISTINCT order_id)      AS frequency,
    -- Monetary: tổng chi tiêu
    ROUND(SUM(payment_value), 2)  AS monetary
FROM view_order_clean
GROUP BY customer_unique_id, customer_state
ORDER BY monetary DESC;

-- 4.2 Feature set cho Regression (dự đoán delay_days)
SELECT
    order_id,
    delivery_days,
    delay_days,
    is_late,
    -- Features
    purchase_month,
    purchase_hour,
    CAST(strftime('%w', order_purchase_timestamp) AS INTEGER) AS weekday,
    same_state,
    product_weight_g,
    product_volume_cm3,
    freight_value,
    price,
    payment_installments,
    review_score
FROM view_order_clean
WHERE delivery_days IS NOT NULL;

