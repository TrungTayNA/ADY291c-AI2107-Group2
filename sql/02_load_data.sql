-- ============================================================
-- LOAD DATA: Staging → Relational Tables
-- Target DBMS: SQLite 3.x
-- Nhóm       : ADY291c-AI2107-Group2
-- Cách chạy  : python scripts/database/build_db.py
-- LƯU Ý     : Staging tables đã được pandas nạp sẵn (if_exists=replace)
--              KHÔNG xóa staging ở đây vì sẽ mất data trước khi INSERT
-- ============================================================

PRAGMA foreign_keys = OFF;

-- ============================================================
-- TRANSFORM STAGING → RELATIONAL TABLES
-- (chạy theo đúng thứ tự FK: category → geo → sellers/customers
--  → products → orders → items/payments/reviews)
-- ============================================================

-- 2.1 product_categories (không có FK phụ thuộc)
INSERT OR IGNORE INTO product_categories (
    product_category_name,
    product_category_name_english
)
SELECT
    product_category_name,
    product_category_name_english
FROM stg_product_categories
WHERE product_category_name IS NOT NULL;

-- 2.2 geolocations — 1 zip_code → lấy avg lat/lng đại diện
INSERT OR IGNORE INTO geolocations (
    zip_code_prefix, lat, lng, city, state
)
SELECT
    geolocation_zip_code_prefix,
    AVG(geolocation_lat),
    AVG(geolocation_lng),
    MAX(geolocation_city),
    MAX(geolocation_state)
FROM stg_geolocations
GROUP BY geolocation_zip_code_prefix;

-- 2.3 sellers
INSERT OR IGNORE INTO sellers (
    seller_id, seller_zip_code_prefix, seller_city, seller_state
)
SELECT
    seller_id,
    seller_zip_code_prefix,
    seller_city,
    seller_state
FROM stg_sellers
WHERE seller_id IS NOT NULL;

-- 2.4 customers
INSERT OR IGNORE INTO customers (
    customer_id, customer_unique_id,
    customer_zip_code_prefix, customer_city, customer_state
)
SELECT
    customer_id, customer_unique_id,
    customer_zip_code_prefix, customer_city, customer_state
FROM stg_customers
WHERE customer_id IS NOT NULL;

-- 2.5 products
INSERT OR IGNORE INTO products (
    product_id, product_category_name,
    product_name_length, product_description_length,
    product_photos_qty, product_weight_g,
    product_length_cm, product_height_cm,
    product_width_cm, product_volume_cm3
)
SELECT
    product_id, product_category_name,
    product_name_length, product_description_length,
    CAST(product_photos_qty AS INTEGER), product_weight_g,
    product_length_cm, product_height_cm,
    product_width_cm, product_volume_cm3
FROM stg_products
WHERE product_id IS NOT NULL;

-- 2.6 orders
INSERT OR IGNORE INTO orders (
    order_id, customer_id, order_status,
    order_purchase_timestamp, order_approved_at,
    order_delivered_carrier_date, order_delivered_customer_date,
    order_estimated_delivery_date,
    delivery_days, estimated_days, delay_days,
    is_late, purchase_year, purchase_month,
    purchase_year_month, purchase_weekday, purchase_hour
)
SELECT
    order_id, customer_id, order_status,
    order_purchase_timestamp, order_approved_at,
    order_delivered_carrier_date, order_delivered_customer_date,
    order_estimated_delivery_date,
    delivery_days, estimated_days, delay_days,
    CASE WHEN is_late = 'True' OR is_late = 1 THEN 1 ELSE 0 END,
    purchase_year, purchase_month,
    purchase_year_month, purchase_weekday, purchase_hour
FROM stg_orders
WHERE order_id IS NOT NULL
  AND customer_id IN (SELECT customer_id FROM customers);

-- 2.7 order_items
INSERT OR IGNORE INTO order_items (
    order_id, order_item_id, product_id, seller_id,
    shipping_limit_date, price, freight_value,
    is_price_outlier, item_total
)
SELECT
    order_id, order_item_id, product_id, seller_id,
    shipping_limit_date, price, freight_value,
    CASE WHEN is_price_outlier = 'True' OR is_price_outlier = 1 THEN 1 ELSE 0 END,
    item_total
FROM stg_order_items
WHERE order_id IN (SELECT order_id FROM orders);

-- 2.8 order_payments
INSERT OR IGNORE INTO order_payments (
    order_id, payment_sequential,
    payment_type, payment_installments, payment_value
)
SELECT
    order_id, payment_sequential,
    payment_type, payment_installments, payment_value
FROM stg_order_payments
WHERE order_id IN (SELECT order_id FROM orders);

-- 2.9 order_reviews
INSERT OR IGNORE INTO order_reviews (
    review_id, order_id, review_score,
    review_comment_title, review_comment_message,
    review_creation_date, review_answer_timestamp, has_comment
)
SELECT
    review_id, order_id, review_score,
    review_comment_title, review_comment_message,
    review_creation_date, review_answer_timestamp,
    CASE WHEN has_comment = 'True' OR has_comment = 1 THEN 1 ELSE 0 END
FROM stg_order_reviews
WHERE order_id IN (SELECT order_id FROM orders);

-- Bật lại FK sau khi import xong
PRAGMA foreign_keys = ON;
