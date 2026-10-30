queries = {}

queries["Q01 - Ngay le va dip dac biet"] = """
WITH special_dates(special_date, special_name) AS (
    VALUES
        ('2016-02-08','Carnival'), ('2016-02-09','Carnival'),
        ('2016-11-25','Black Friday'), ('2016-12-25','Giang sinh'),
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
    WHERE purchase_date NOT IN (SELECT special_date FROM special_dates)
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
"""

queries["Q02 - Phat hien ngay dot bien"] = """
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
"""

queries["Q03 - Phan bo va mat can bang review_score"] = """
SELECT review_score,
       COUNT(*) AS order_count,
       ROUND(100.0 * COUNT(*) /
             (SELECT COUNT(*) FROM v_review_order_features), 2) AS percentage
FROM v_review_order_features
GROUP BY review_score
ORDER BY review_score;
"""

queries["Q04 - Don giao tre so voi dung han"] = """
SELECT CASE WHEN is_late = 1 THEN 'Giao tre'
            ELSE 'Dung han hoac som' END AS delivery_group,
       COUNT(*) AS order_count,
       ROUND(AVG(review_score), 2) AS avg_review_score,
       ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
GROUP BY is_late
ORDER BY delivery_group;
"""

queries["Q05 - Muc do tre theo ngay"] = """
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
"""

queries["Q06 - Phi ship va ty le phi/gia"] = """
WITH freight_quartiles AS (
    SELECT *, NTILE(4) OVER (ORDER BY total_freight) AS group_number
    FROM v_review_order_features
),
ratio_quartiles AS (
    SELECT *, NTILE(4) OVER (ORDER BY freight_to_price_pct) AS group_number
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
"""

queries["Q07 - Do phuc tap don hang"] = """
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
"""

queries["Q08 - Thanh toan va tra gop"] = """
SELECT first_payment_type AS payment_type,
       COUNT(*) AS order_count,
       ROUND(AVG(max_installments), 2) AS avg_installments,
       ROUND(AVG(review_score), 2) AS avg_review_score,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
WHERE first_payment_type IS NOT NULL
GROUP BY first_payment_type
ORDER BY order_count DESC;
"""

queries["Q09 - Xu huong review theo thang"] = """
SELECT purchase_year_month,
       COUNT(*) AS order_count,
       ROUND(AVG(review_score), 2) AS avg_review_score,
       ROUND(100.0 * AVG(CASE WHEN review_score >= 4 THEN 1 ELSE 0 END), 2) AS positive_pct,
       ROUND(100.0 * AVG(CASE WHEN review_score <= 2 THEN 1 ELSE 0 END), 2) AS low_score_pct
FROM v_review_order_features
GROUP BY purchase_year_month
ORDER BY purchase_year_month;
"""

queries["Q10 - Hai long theo bang/khu vuc"] = """
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
"""

print(f"Da chuan bi {len(queries)} truy van SQL")
