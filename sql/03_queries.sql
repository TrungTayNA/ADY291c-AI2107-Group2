-- ============================================================
-- SQL ANALYSIS QUERIES
-- Target DBMS : SQLite 3.x
-- Dataset     : Olist Brazilian E-Commerce (2016-2018)
-- Questions   : Q01-Q10
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
-- Q01: NGAY LE VA DIP DAC BIET CO LAM LUONG MUA TANG?
-- So sanh ngay dip dac biet voi ngay thuong cung nam.
-- ============================================================
WITH special_dates(special_date, special_name) AS (
    VALUES
        ('2016-01-01','Tet Duong lich'), ('2016-04-21','Le Quoc khanh Brazil'),
        ('2016-05-01','Quoc te Lao dong'), ('2016-09-07','Doc lap Brazil'),
        ('2016-10-12','Nha thien chua Our Lady'), ('2016-11-02','Le hon sau'),
        ('2016-11-15','Cong hoa Brazil'), ('2016-12-25','Giang sinh'),
        ('2016-02-08','Carnival'), ('2016-02-09','Carnival'),
        ('2016-03-25','Good Friday'), ('2016-05-26','Corpus Christi'),
        ('2016-11-25','Black Friday'),
        ('2017-01-01','Tet Duong lich'), ('2017-04-21','Le Quoc khanh Brazil'),
        ('2017-05-01','Quoc te Lao dong'), ('2017-09-07','Doc lap Brazil'),
        ('2017-10-12','Nha thien chua Our Lady'), ('2017-11-02','Le hon sau'),
        ('2017-11-15','Cong hoa Brazil'), ('2017-12-25','Giang sinh'),
        ('2017-02-27','Carnival'), ('2017-02-28','Carnival'),
        ('2017-04-14','Good Friday'), ('2017-06-15','Corpus Christi'),
        ('2017-11-24','Black Friday'),
        ('2018-01-01','Tet Duong lich'), ('2018-04-21','Le Quoc khanh Brazil'),
        ('2018-05-01','Quoc te Lao dong'), ('2018-09-07','Doc lap Brazil'),
        ('2018-10-12','Nha thien chua Our Lady'), ('2018-11-02','Le hon sau'),
        ('2018-11-15','Cong hoa Brazil'), ('2018-12-25','Giang sinh'),
        ('2018-02-12','Carnival'), ('2018-02-13','Carnival'),
        ('2018-03-30','Good Friday'), ('2018-05-31','Corpus Christi'),
        ('2018-11-23','Black Friday')
),
daily_orders AS (
    SELECT
        date(order_purchase_timestamp) AS purchase_date,
        COUNT(DISTINCT order_id) AS order_count
    FROM orders
    GROUP BY purchase_date
)
SELECT
    d.purchase_date,
    MIN(s.special_name) AS special_name,
    d.order_count,
    ROUND(100.0 * (d.order_count -
        (SELECT AVG(order_count) FROM daily_orders d2
         WHERE d2.purchase_date NOT IN (SELECT special_date FROM special_dates)
           AND substr(d2.purchase_date,1,4) = substr(d.purchase_date,1,4)))
        / NULLIF((SELECT AVG(order_count) FROM daily_orders d2
                  WHERE d2.purchase_date NOT IN (SELECT special_date FROM special_dates)
                    AND substr(d2.purchase_date,1,4) = substr(d.purchase_date,1,4)),0), 2) AS pct_vs_normal_days
FROM daily_orders d
LEFT JOIN special_dates s ON s.special_date = d.purchase_date
WHERE s.special_date IS NOT NULL
ORDER BY d.order_count DESC, d.purchase_date;

-- So sanh tong quat: ngay dac biet vs ngay thuong
WITH special_dates(special_date) AS (
    VALUES ('2016-01-01'), ('2016-04-21'), ('2016-05-01'), ('2016-09-07'),
           ('2016-10-12'), ('2016-11-02'), ('2016-11-15'), ('2016-12-25'),
           ('2016-02-08'), ('2016-02-09'), ('2016-03-25'), ('2016-05-26'), ('2016-11-25'),
           ('2017-01-01'), ('2017-04-21'), ('2017-05-01'), ('2017-09-07'),
           ('2017-10-12'), ('2017-11-02'), ('2017-11-15'), ('2017-12-25'),
           ('2017-02-27'), ('2017-02-28'), ('2017-04-14'), ('2017-06-15'), ('2017-11-24'),
           ('2018-01-01'), ('2018-04-21'), ('2018-05-01'), ('2018-09-07'),
           ('2018-10-12'), ('2018-11-02'), ('2018-11-15'), ('2018-12-25'),
           ('2018-02-12'), ('2018-02-13'), ('2018-03-30'), ('2018-05-31'), ('2018-11-23')
),
daily_orders AS (
    SELECT date(order_purchase_timestamp) purchase_date, COUNT(DISTINCT order_id) order_count
    FROM orders GROUP BY date(order_purchase_timestamp)
)
SELECT
    CASE WHEN EXISTS (
        SELECT 1 FROM special_dates s WHERE s.special_date = d.purchase_date
    ) THEN 'Ngay dac biet' ELSE 'Ngay thuong' END AS day_type,
    COUNT(*) AS day_count,
    ROUND(AVG(d.order_count), 2) AS avg_orders_per_day,
    MAX(d.order_count) AS max_orders_per_day
FROM daily_orders d
GROUP BY day_type
ORDER BY avg_orders_per_day DESC;


-- ============================================================
-- Q02: PHAT HIEN NGAY DOT BIEN (SPIKE DETECTION)
-- So voi trung binh 28 ngay truoc, nguong canh bao >= 50% va >= 1.5 z-score.
-- ============================================================
WITH daily_orders AS (
    SELECT date(order_purchase_timestamp) AS purchase_date,
           COUNT(DISTINCT order_id) AS order_count
    FROM orders
    GROUP BY date(order_purchase_timestamp)
),
baseline AS (
    SELECT
        purchase_date,
        order_count,
        AVG(order_count) OVER (
            ORDER BY purchase_date ROWS BETWEEN 28 PRECEDING AND 1 PRECEDING
        ) AS prior_28d_avg
    FROM daily_orders
)
SELECT
    purchase_date,
    order_count,
    ROUND(prior_28d_avg, 2) AS prior_28d_avg,
    ROUND(100.0 * (order_count - prior_28d_avg) / NULLIF(prior_28d_avg, 0), 2) AS spike_pct
FROM baseline
WHERE prior_28d_avg IS NOT NULL
  AND order_count >= 1.50 * prior_28d_avg
ORDER BY spike_pct DESC, purchase_date;


-- ============================================================
-- Q03: PHAN BO REVIEW SCORE VA MAT CAN BANG LOP
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
-- Q04: DON GIAO TRE CO REVIEW THAP HON DON DUNG HAN?
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
-- Q05: MUC DO TRE 0; 1-3; 4-7; >7 NGAY
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
-- Q06: PHI VAN CHUYEN VA TY LE PHI/ GIA HANG CO ANH HUONG REVIEW?
-- ============================================================
WITH freight_quartiles AS (
    SELECT total_freight, review_score,
           NTILE(4) OVER (ORDER BY total_freight) AS freight_quartile
    FROM v_review_order_features
),
ratio_quartiles AS (
    SELECT freight_to_price_pct, review_score,
           NTILE(4) OVER (ORDER BY freight_to_price_pct) AS ratio_quartile
    FROM v_review_order_features
    WHERE freight_to_price_pct IS NOT NULL
)
SELECT
    'Tong phi van chuyen' AS loai_chi_phi,
    CASE freight_quartile
        WHEN 1 THEN 'Nhom 1 - Thap nhat'
        WHEN 2 THEN 'Nhom 2 - Thap'
        WHEN 3 THEN 'Nhom 3 - Cao'
        ELSE 'Nhom 4 - Cao nhat'
    END AS muc_phi,
    freight_quartile AS nhom_so,
    COUNT(*) AS order_count,
    ROUND(AVG(total_freight), 2) AS gia_tri_trung_binh,
    ROUND(AVG(review_score), 2) AS review_trung_binh,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS ty_le_review_1_2_pct
FROM freight_quartiles
GROUP BY freight_quartile
UNION ALL
SELECT
    'Ty le phi ship / gia hang' AS loai_chi_phi,
    CASE ratio_quartile
        WHEN 1 THEN 'Nhom 1 - Thap nhat'
        WHEN 2 THEN 'Nhom 2 - Thap'
        WHEN 3 THEN 'Nhom 3 - Cao'
        ELSE 'Nhom 4 - Cao nhat'
    END AS muc_phi,
    ratio_quartile AS nhom_so,
    COUNT(*) AS order_count,
    ROUND(AVG(freight_to_price_pct), 2) AS gia_tri_trung_binh,
    ROUND(AVG(review_score), 2) AS review_trung_binh,
    ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS ty_le_review_1_2_pct
FROM ratio_quartiles
GROUP BY ratio_quartile
ORDER BY loai_chi_phi, nhom_so;


-- ============================================================
-- Q07: DO PHUC TAP DON HANG - SO SAN PHAM VA SO NGUOI BAN
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
-- Q08: PHUONG THUC THANH TOAN VA SO KY TRA GOP
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
-- Q09: XU HUONG REVIEW SCORE THEO THANG (22 THANG DU LIEU)
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
-- Q10: MUC DO HAI LONG THEO BANG/KHU VUC
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
