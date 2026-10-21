-- ============================================================
-- DATABASE SCHEMA: OLIST E-COMMERCE ANALYSIS
-- Target DBMS : SQLite 3.x
-- Architecture: Staging → Relational (3NF) → Views
-- Nhóm        : ADY291c-AI2107-Group2
-- ============================================================

PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;   -- tăng hiệu năng ghi đồng thời

-- ============================================================
-- PHẦN 1: BẢNG STAGING (1-1 với CSV processed, import nhanh)
-- ============================================================

CREATE TABLE IF NOT EXISTS stg_customers (
    customer_id              TEXT,
    customer_unique_id       TEXT,
    customer_zip_code_prefix INTEGER,
    customer_city            TEXT,
    customer_state           TEXT
);

CREATE TABLE IF NOT EXISTS stg_orders (
    order_id                      TEXT,
    customer_id                   TEXT,
    order_status                  TEXT,
    order_purchase_timestamp      TEXT,
    order_approved_at             TEXT,
    order_delivered_carrier_date  TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,
    delivery_days                 REAL,
    estimated_days                REAL,
    delay_days                    INTEGER,
    is_late                       INTEGER,   -- 0/1 (SQLite không có BOOL)
    purchase_year                 INTEGER,
    purchase_month                INTEGER,
    purchase_year_month           TEXT,
    purchase_weekday              INTEGER,
    purchase_hour                 INTEGER
);

CREATE TABLE IF NOT EXISTS stg_order_items (
    order_id         TEXT,
    order_item_id    INTEGER,
    product_id       TEXT,
    seller_id        TEXT,
    shipping_limit_date TEXT,
    price            REAL,
    freight_value    REAL,
    is_price_outlier INTEGER,   -- 0/1
    item_total       REAL
);

CREATE TABLE IF NOT EXISTS stg_order_payments (
    order_id              TEXT,
    payment_sequential    INTEGER,
    payment_type          TEXT,
    payment_installments  INTEGER,
    payment_value         REAL
);

CREATE TABLE IF NOT EXISTS stg_order_reviews (
    review_id               TEXT,
    order_id                TEXT,
    review_score            INTEGER,
    review_comment_title    TEXT,
    review_comment_message  TEXT,
    review_creation_date    TEXT,
    review_answer_timestamp TEXT,
    has_comment             INTEGER   -- 0/1
);

CREATE TABLE IF NOT EXISTS stg_products (
    product_id                 TEXT,
    product_category_name      TEXT,
    product_name_length        REAL,
    product_description_length REAL,
    product_photos_qty         REAL,
    product_weight_g           REAL,
    product_length_cm          REAL,
    product_height_cm          REAL,
    product_width_cm           REAL,
    product_volume_cm3         REAL
);

CREATE TABLE IF NOT EXISTS stg_sellers (
    seller_id               TEXT,
    seller_zip_code_prefix  INTEGER,
    seller_city             TEXT,
    seller_state            TEXT
);

CREATE TABLE IF NOT EXISTS stg_geolocations (
    geolocation_zip_code_prefix INTEGER,
    geolocation_lat             REAL,
    geolocation_lng             REAL,
    geolocation_city            TEXT,
    geolocation_state           TEXT
);

CREATE TABLE IF NOT EXISTS stg_product_categories (
    product_category_name         TEXT,
    product_category_name_english TEXT
);


-- ============================================================
-- PHẦN 2: BẢNG QUAN HỆ CHUẨN HÓA (3NF)
-- ============================================================

-- ------------------------------------------------------------
-- 2.1 PRODUCT_CATEGORIES — Bảng tra cứu danh mục sản phẩm
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS product_categories (
    product_category_name         TEXT PRIMARY KEY,
    product_category_name_english TEXT NOT NULL
);

-- ------------------------------------------------------------
-- 2.2 GEOLOCATIONS — Bảng tra cứu mã bưu chính / toạ độ
-- (1 zip_code → 1 bản ghi đại diện trung bình lat/lng)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS geolocations (
    zip_code_prefix INTEGER PRIMARY KEY,
    lat             REAL,
    lng             REAL,
    city            TEXT,
    state           TEXT
);

-- ------------------------------------------------------------
-- 2.3 CUSTOMERS — Khách hàng
-- customer_id   : mã phiên (1 người mua nhiều lần = nhiều customer_id)
-- customer_unique_id : mã thực sự của người dùng
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS customers (
    customer_id              TEXT PRIMARY KEY,
    customer_unique_id       TEXT NOT NULL,
    customer_zip_code_prefix INTEGER,
    customer_city            TEXT,
    customer_state           TEXT,
    FOREIGN KEY (customer_zip_code_prefix)
        REFERENCES geolocations(zip_code_prefix) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- 2.4 SELLERS — Người bán
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS sellers (
    seller_id              TEXT PRIMARY KEY,
    seller_zip_code_prefix INTEGER,
    seller_city            TEXT,
    seller_state           TEXT,
    FOREIGN KEY (seller_zip_code_prefix)
        REFERENCES geolocations(zip_code_prefix) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- 2.5 PRODUCTS — Sản phẩm
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS products (
    product_id                 TEXT PRIMARY KEY,
    product_category_name      TEXT,
    product_name_length        REAL,
    product_description_length REAL,
    product_photos_qty         INTEGER,
    product_weight_g           REAL,
    product_length_cm          REAL,
    product_height_cm          REAL,
    product_width_cm           REAL,
    product_volume_cm3         REAL,
    FOREIGN KEY (product_category_name)
        REFERENCES product_categories(product_category_name) ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- 2.6 ORDERS — Đơn hàng (trung tâm của star schema)
-- Giữ lại cột engineered (delivery_days, is_late, ...) để
-- tối ưu query phân tích — Denormalization có kiểm soát.
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS orders (
    order_id                      TEXT PRIMARY KEY,
    customer_id                   TEXT NOT NULL,
    order_status                  TEXT NOT NULL DEFAULT 'delivered',
    order_purchase_timestamp      TEXT NOT NULL,
    order_approved_at             TEXT,
    order_delivered_carrier_date  TEXT,
    order_delivered_customer_date TEXT,
    order_estimated_delivery_date TEXT,
    -- Cột tính toán (engineered features từ preprocessing)
    delivery_days                 REAL,
    estimated_days                REAL,
    delay_days                    INTEGER DEFAULT 0,
    is_late                       INTEGER DEFAULT 0 CHECK(is_late IN (0, 1)),
    purchase_year                 INTEGER,
    purchase_month                INTEGER,
    purchase_year_month           TEXT,
    purchase_weekday              INTEGER,
    purchase_hour                 INTEGER,
    FOREIGN KEY (customer_id)
        REFERENCES customers(customer_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 2.7 ORDER_ITEMS — Chi tiết sản phẩm trong đơn hàng
-- Composite PK: 1 đơn có thể gồm nhiều sản phẩm
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_items (
    order_id         TEXT    NOT NULL,
    order_item_id    INTEGER NOT NULL,
    product_id       TEXT    NOT NULL,
    seller_id        TEXT    NOT NULL,
    shipping_limit_date TEXT,
    price            REAL    NOT NULL DEFAULT 0,
    freight_value    REAL    NOT NULL DEFAULT 0,
    is_price_outlier INTEGER DEFAULT 0 CHECK(is_price_outlier IN (0, 1)),
    item_total       REAL    NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, order_item_id),
    FOREIGN KEY (order_id)   REFERENCES orders(order_id)   ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES products(product_id) ON DELETE SET NULL,
    FOREIGN KEY (seller_id)  REFERENCES sellers(seller_id)  ON DELETE SET NULL
);

-- ------------------------------------------------------------
-- 2.8 ORDER_PAYMENTS — Thanh toán (1 đơn có thể nhiều lần TT)
-- Composite PK: (order_id, payment_sequential)
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_payments (
    order_id             TEXT    NOT NULL,
    payment_sequential   INTEGER NOT NULL,
    payment_type         TEXT    NOT NULL,
    payment_installments INTEGER DEFAULT 1,
    payment_value        REAL    NOT NULL DEFAULT 0,
    PRIMARY KEY (order_id, payment_sequential),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

-- ------------------------------------------------------------
-- 2.9 ORDER_REVIEWS — Đánh giá của khách hàng
-- ------------------------------------------------------------
CREATE TABLE IF NOT EXISTS order_reviews (
    review_id               TEXT    PRIMARY KEY,
    order_id                TEXT    NOT NULL,
    review_score            INTEGER NOT NULL CHECK(review_score BETWEEN 1 AND 5),
    review_comment_title    TEXT    DEFAULT 'No Title',
    review_comment_message  TEXT    DEFAULT 'No Comment',
    review_creation_date    TEXT,
    review_answer_timestamp TEXT,
    has_comment             INTEGER DEFAULT 0 CHECK(has_comment IN (0, 1)),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);


-- ============================================================
-- PHẦN 3: INDEX TỐI ƯU HOÁ TRUY VẤN
-- ============================================================

-- orders → tra cứu theo khách, thời gian, trạng thái trễ
CREATE INDEX IF NOT EXISTS idx_orders_customer    ON orders(customer_id);
CREATE INDEX IF NOT EXISTS idx_orders_purchase_ts ON orders(order_purchase_timestamp);
CREATE INDEX IF NOT EXISTS idx_orders_year_month  ON orders(purchase_year_month);
CREATE INDEX IF NOT EXISTS idx_orders_is_late     ON orders(is_late);

-- order_items → JOIN phổ biến nhất
CREATE INDEX IF NOT EXISTS idx_items_order    ON order_items(order_id);
CREATE INDEX IF NOT EXISTS idx_items_product  ON order_items(product_id);
CREATE INDEX IF NOT EXISTS idx_items_seller   ON order_items(seller_id);

-- order_payments → aggregate theo order
CREATE INDEX IF NOT EXISTS idx_payments_order ON order_payments(order_id);
CREATE INDEX IF NOT EXISTS idx_payments_type  ON order_payments(payment_type);

-- order_reviews → JOIN + filter theo score
CREATE INDEX IF NOT EXISTS idx_reviews_order ON order_reviews(order_id);
CREATE INDEX IF NOT EXISTS idx_reviews_score ON order_reviews(review_score);

-- products → JOIN với category
CREATE INDEX IF NOT EXISTS idx_products_category ON products(product_category_name);

-- customers/sellers → JOIN với geolocation
CREATE INDEX IF NOT EXISTS idx_customers_zip ON customers(customer_zip_code_prefix);
CREATE INDEX IF NOT EXISTS idx_customers_state ON customers(customer_state);
CREATE INDEX IF NOT EXISTS idx_sellers_state ON sellers(seller_state);


-- ============================================================
-- PHẦN 4: ANALYTICAL VIEWS (Tầng phân tích)
-- ============================================================

-- View 1: Doanh thu theo tháng
CREATE VIEW IF NOT EXISTS v_sales_monthly AS
SELECT
    o.purchase_year_month,
    o.purchase_year,
    o.purchase_month,
    COUNT(DISTINCT o.order_id)     AS total_orders,
    ROUND(SUM(p.payment_value), 2) AS total_revenue,
    ROUND(AVG(p.payment_value), 2) AS avg_order_value
FROM orders o
JOIN order_payments p ON o.order_id = p.order_id
GROUP BY o.purchase_year_month, o.purchase_year, o.purchase_month;

-- View 2: KPI giao hàng theo bang khách hàng
CREATE VIEW IF NOT EXISTS v_delivery_kpi AS
SELECT
    cu.customer_state,
    COUNT(*)                                          AS total_orders,
    SUM(o.is_late)                                    AS late_orders,
    ROUND(100.0 * SUM(o.is_late) / COUNT(*), 2)       AS late_rate_pct,
    ROUND(AVG(o.delivery_days), 2)                    AS avg_delivery_days,
    ROUND(AVG(o.delay_days), 2)                       AS avg_delay_days
FROM orders o
JOIN customers cu ON o.customer_id = cu.customer_id
GROUP BY cu.customer_state;

-- View 3: Doanh thu + review theo danh mục sản phẩm
CREATE VIEW IF NOT EXISTS v_category_performance AS
SELECT
    COALESCE(cat.product_category_name_english, pr.product_category_name) AS category_english,
    COUNT(DISTINCT oi.order_id)              AS total_orders,
    SUM(oi.item_total)                       AS total_revenue,
    ROUND(AVG(oi.price), 2)                  AS avg_price,
    ROUND(AVG(rv.review_score), 2)           AS avg_review_score
FROM order_items oi
JOIN products pr     ON oi.product_id = pr.product_id
LEFT JOIN product_categories cat ON pr.product_category_name = cat.product_category_name
LEFT JOIN order_reviews rv       ON oi.order_id = rv.order_id
GROUP BY 1;

-- View 4: RFM cơ bản cho phân khúc khách hàng (dùng cho K-Means)
CREATE VIEW IF NOT EXISTS v_customer_rfm AS
SELECT
    cu.customer_unique_id,
    cu.customer_state,
    MAX(o.order_purchase_timestamp)          AS last_purchase_date,
    COUNT(DISTINCT o.order_id)               AS frequency,
    ROUND(SUM(p.payment_value), 2)           AS monetary
FROM customers cu
JOIN orders o         ON cu.customer_id = o.customer_id
JOIN order_payments p ON o.order_id = p.order_id
GROUP BY cu.customer_unique_id, cu.customer_state;

-- View 5: Hiệu năng người bán
CREATE VIEW IF NOT EXISTS v_seller_performance AS
SELECT
    s.seller_id,
    s.seller_state,
    COUNT(DISTINCT oi.order_id)      AS total_orders,
    ROUND(SUM(oi.item_total), 2)     AS total_revenue,
    ROUND(AVG(rv.review_score), 2)   AS avg_review_score,
    ROUND(AVG(o.delay_days), 2)      AS avg_delay_days
FROM sellers s
JOIN order_items oi  ON s.seller_id = oi.seller_id
JOIN orders o        ON oi.order_id = o.order_id
LEFT JOIN order_reviews rv ON o.order_id = rv.order_id
GROUP BY s.seller_id, s.seller_state;

-- View 6: Phân bố phương thức thanh toán
CREATE VIEW IF NOT EXISTS v_payment_mix AS
SELECT
    payment_type,
    COUNT(*)                                           AS total_transactions,
    ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER(), 2) AS pct_of_total,
    ROUND(AVG(payment_value), 2)                       AS avg_value,
    ROUND(AVG(payment_installments), 2)                AS avg_installments
FROM order_payments
GROUP BY payment_type;

