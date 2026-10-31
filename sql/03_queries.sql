-- ============================================================
-- SQL ANALYSIS QUERIES
-- Target DBMS : SQLite 3.x
-- Dataset     : Olist Brazilian E-Commerce (2016-2018)
-- Questions   : Q1-Q8
-- ============================================================

PRAGMA foreign_keys = ON;


-- ============================================================
-- VIEW 1: BASE VIEW - MOT DONG MOI DON HANG DA GIAO
-- Tong hop item va thanh toan truoc khi JOIN de tranh nhan doi.
-- ============================================================
DROP VIEW IF EXISTS v_review_order_features;
CREATE VIEW v_review_order_features AS
WITH ranked_reviews AS (
    SELECT
        review_id,
        order_id,
        review_score,
        review_creation_date,
        ROW_NUMBER() OVER (
            PARTITION BY order_id
            ORDER BY datetime(review_creation_date) DESC, review_id DESC
        ) AS review_rank
    FROM order_reviews
),
items_by_order AS (
    SELECT
        order_id,
        COUNT(*) AS item_count,
        COUNT(DISTINCT product_id) AS distinct_products,
        COUNT(DISTINCT seller_id) AS seller_count,
        SUM(price) AS total_item_price,
        SUM(freight_value) AS total_freight,
        SUM(item_total) AS item_total_sum,
        AVG(price) AS avg_item_price,
        SUM(CASE WHEN freight_value > 0 THEN 1 ELSE 0 END) > 1 AS multi_freight_item
    FROM order_items
    GROUP BY order_id
),
payments_by_order AS (
    SELECT
        order_id,
        SUM(payment_value) AS total_paid,
        COUNT(*) AS payment_count,
        MAX(payment_installments) AS max_installments,
        MAX(CASE WHEN payment_sequential = 1 THEN payment_type END) AS first_payment_type,
        SUM(CASE WHEN payment_type = 'voucher' THEN payment_value ELSE 0 END) AS voucher_value
    FROM order_payments
    GROUP BY order_id
),
seller_states_by_order AS (
    SELECT
        oi.order_id,
        SUM(CASE WHEN s.seller_state = c.customer_state THEN 1 ELSE 0 END) AS same_state_item_count,
        COUNT(*) AS seller_item_count
    FROM order_items oi
    JOIN orders o ON o.order_id = oi.order_id
    JOIN customers c ON c.customer_id = o.customer_id
    JOIN sellers s ON s.seller_id = oi.seller_id
    GROUP BY oi.order_id
)
SELECT
    o.order_id,
    c.customer_unique_id,
    c.customer_state,
    c.customer_city,
    date(o.order_purchase_timestamp) AS purchase_date,
    o.order_purchase_timestamp,
    o.order_delivered_customer_date,
    o.order_estimated_delivery_date,
    o.purchase_year_month,
    o.purchase_month,
    o.purchase_hour,
    o.delivery_days,
    o.estimated_days,
    o.delay_days,
    o.is_late,
    i.item_count,
    i.distinct_products,
    i.seller_count,
    i.total_item_price,
    i.total_freight,
    i.item_total_sum,
    i.avg_item_price,
    CASE
        WHEN i.total_item_price > 0
        THEN ROUND(100.0 * i.total_freight / i.total_item_price, 2)
        ELSE NULL
    END AS freight_to_price_pct,
    CASE
        WHEN ss.seller_item_count > 0
        THEN ROUND(100.0 * ss.same_state_item_count / ss.seller_item_count, 2)
        ELSE 0
    END AS same_state_item_pct,
    p.total_paid,
    p.payment_count,
    p.max_installments,
    p.first_payment_type,
    p.voucher_value,
    r.review_score,
    r.review_creation_date
FROM orders o
JOIN ranked_reviews r
  ON r.order_id = o.order_id AND r.review_rank = 1
JOIN customers c ON c.customer_id = o.customer_id
LEFT JOIN items_by_order i ON i.order_id = o.order_id
LEFT JOIN payments_by_order p ON p.order_id = o.order_id
LEFT JOIN seller_states_by_order ss ON ss.order_id = o.order_id
WHERE o.order_status = 'delivered'
  AND i.item_count IS NOT NULL;


-- ============================================================
-- Q1: PHAN BO REVIEW SCORE VA MAT CAN BANG LOP
-- ============================================================
SELECT
    review_score,
    COUNT(*) AS order_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM v_review_order_features), 2) AS percentage,
    ROUND(100.0 * SUM(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END)
          / COUNT(*), 2) AS positive_pct
FROM v_review_order_features
GROUP BY review_score
ORDER BY review_score;

SELECT
    CASE
        WHEN review_score <= 2 THEN 'Kem (1-2)'
        WHEN review_score = 3 THEN 'Trung binh (3)'
        ELSE 'Tot (4-5)'
    END AS score_group,
    COUNT(*) AS order_count,
    ROUND(100.0 * COUNT(*) / (SELECT COUNT(*) FROM v_review_order_features), 2) AS percentage
FROM v_review_order_features
GROUP BY score_group
ORDER BY MIN(review_score);


-- ============================================================
-- Q2: DON GIAO TRE CO REVIEW THAP HON DON DUNG HAN?
-- ============================================================
SELECT
    CASE WHEN is_late = 1 THEN 'Giao tre'
         ELSE 'Dung han hoac som' END AS delivery_group,
    COUNT(*) AS order_count,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
GROUP BY is_late
ORDER BY delivery_group;


-- ============================================================
-- Q3: MUC DO TRE 0; 1-3; 4-7; >7 NGAY
-- ============================================================
SELECT
    CASE
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


-- ============================================================
-- Q4: PHI VAN CHUYEN VA TY LE PHI/ GIA HANG CO ANH HUONG REVIEW?
-- ============================================================
WITH ship_fee_data AS (
    -- Chi giu hai cot can thiet: phi ship va review.
    SELECT total_freight AS metric_value, review_score
    FROM v_review_order_features
),
ship_fee_quartiles AS (
    -- NTILE(4): chia don theo phi ship tang dan thanh 4 nhom gan bang nhau.
    SELECT metric_value, review_score,
           NTILE(4) OVER (ORDER BY metric_value) AS quartile_number
    FROM ship_fee_data
),
ship_fee_ratio_data AS (
    SELECT freight_to_price_pct AS metric_value, review_score
    FROM v_review_order_features
    WHERE freight_to_price_pct IS NOT NULL
),
ship_fee_ratio_quartiles AS (
    -- NTILE(4): chia don theo ty le phi ship/gia hang tang dan.
    SELECT metric_value, review_score,
           NTILE(4) OVER (ORDER BY metric_value) AS quartile_number
    FROM ship_fee_ratio_data
),
ship_fee_summary AS (
    SELECT
        'Tong phi ship (BRL)' AS chi_so,
        CASE quartile_number
            WHEN 1 THEN '1 - 25% phi thap nhat'
            WHEN 2 THEN '2 - Tu 25%-50%'
            WHEN 3 THEN '3 - Tu 50%-75%'
            ELSE '4 - 25% phi cao nhat'
        END AS nhom_phi,
        quartile_number,
        COUNT(*) AS order_count,
        ROUND(AVG(metric_value), 2) AS gia_tri_trung_binh,
        ROUND(AVG(review_score), 2) AS review_trung_binh,
        ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS ty_le_review_1_2_pct
    FROM ship_fee_quartiles
    GROUP BY quartile_number
),
ship_fee_ratio_summary AS (
    SELECT
        'Ty le phi ship/gia hang (%)' AS chi_so,
        CASE quartile_number
            WHEN 1 THEN '1 - 25% ty le thap nhat'
            WHEN 2 THEN '2 - Tu 25%-50%'
            WHEN 3 THEN '3 - Tu 50%-75%'
            ELSE '4 - 25% ty le cao nhat'
        END AS nhom_phi,
        quartile_number,
        COUNT(*) AS order_count,
        ROUND(AVG(metric_value), 2) AS gia_tri_trung_binh,
        ROUND(AVG(review_score), 2) AS review_trung_binh,
        ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS ty_le_review_1_2_pct
    FROM ship_fee_ratio_quartiles
    GROUP BY quartile_number
)
SELECT * FROM ship_fee_summary
UNION ALL
SELECT * FROM ship_fee_ratio_summary
ORDER BY chi_so DESC, quartile_number;


-- ============================================================
-- Q5: DO PHUC TAP DON HANG - SO SAN PHAM VA SO NGUOI BAN
-- ============================================================
SELECT
    CASE
        WHEN item_count = 1 THEN '1 mat hang'
        WHEN item_count BETWEEN 2 AND 3 THEN '2-3 mat hang'
        ELSE '4+ mat hang'
    END AS basket_group,
    CASE
        WHEN seller_count = 1 THEN '1 nguoi ban'
        ELSE 'Nhieu nguoi ban'
    END AS seller_group,
    COUNT(*) AS order_count,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
GROUP BY basket_group, seller_group
ORDER BY MIN(item_count), MIN(seller_count);


-- ============================================================
-- Q6: PHUONG THUC THANH TOAN VA SO KY TRA GOP
-- ============================================================
SELECT
    first_payment_type AS payment_type,
    COUNT(*) AS order_count,
    ROUND(AVG(max_installments), 2) AS avg_installments,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
WHERE first_payment_type IS NOT NULL
GROUP BY first_payment_type
ORDER BY order_count DESC;

SELECT
    CASE
        WHEN max_installments <= 1 THEN '1 ky / tra mot lan'
        WHEN max_installments BETWEEN 2 AND 6 THEN '2-6 ky'
        WHEN max_installments BETWEEN 7 AND 12 THEN '7-12 ky'
        ELSE 'Hon 12 ky'
    END AS installment_group,
    COUNT(*) AS order_count,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
WHERE max_installments IS NOT NULL
GROUP BY installment_group
ORDER BY MIN(max_installments);


-- ============================================================
-- Q7: XU HUONG REVIEW SCORE THEO THANG (22 THANG DU LIEU)
-- ============================================================
SELECT
    purchase_year_month,
    COUNT(*) AS order_count,
    ROUND(AVG(review_score), 2) AS avg_review_score,
    ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
GROUP BY purchase_year_month
ORDER BY purchase_year_month;


-- ============================================================
-- Q8: MUC DO HAI LONG THEO BANG/KHU VUC
-- Chi bao gom bang co toi thieu 100 don.
-- ============================================================
SELECT
    customer_state,
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


-- ============================================================
-- LEAKAGE-SAFE MODEL FEATURE VIEWS
-- PRE-DELIVERY: chi dung thong tin biet tai luc dat hang.
-- POST-DELIVERY: bo sung thong tin chi xuat hien sau khi giao.
-- ============================================================
DROP VIEW IF EXISTS v_model_features_at_purchase;
CREATE VIEW v_model_features_at_purchase AS
SELECT
    order_id,
    review_score AS target_review_score,
    purchase_hour,
    purchase_month,
    customer_state,
    item_count,
    distinct_products,
    seller_count,
    total_item_price,
    total_freight,
    freight_to_price_pct,
    total_paid,
    payment_count,
    max_installments,
    first_payment_type,
    voucher_value
FROM v_review_order_features;

DROP VIEW IF EXISTS v_model_features_post_delivery;
CREATE VIEW v_model_features_post_delivery AS
SELECT
    order_id,
    review_score AS target_review_score,
    purchase_hour,
    purchase_month,
    customer_state,
    item_count,
    distinct_products,
    seller_count,
    total_item_price,
    total_freight,
    freight_to_price_pct,
    total_paid,
    payment_count,
    max_installments,
    first_payment_type,
    voucher_value,
    delivery_days,
    estimated_days,
    delay_days,
    is_late,
    same_state_item_pct
FROM v_review_order_features;
