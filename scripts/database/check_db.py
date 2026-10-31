import sqlite3

conn = sqlite3.connect('data/olist.db')

print('=== TABLES ===')
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall()
for row in tables:
    cnt = conn.execute(f'SELECT COUNT(*) FROM [{row[0]}]').fetchone()[0]
    print(f'  {row[0]:35s} {cnt:>8,}')

print()
print('=== VIEWS ===')
views = conn.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name").fetchall()
for row in views:
    cnt = conn.execute(f'SELECT COUNT(*) FROM [{row[0]}]').fetchone()[0]
    print(f'  {row[0]:35s} {cnt:>8,}')

print()
print('=== INDEXES ===')
idxs = conn.execute("SELECT name FROM sqlite_master WHERE type='index' AND name NOT LIKE 'sqlite_%' ORDER BY name").fetchall()
for row in idxs:
    print(f'  {row[0]}')

print()
print('=== DATA INTEGRITY ===')
checks = [
    ('Orphan order_items (no parent order)',
     'SELECT COUNT(*) FROM order_items WHERE order_id NOT IN (SELECT order_id FROM orders)'),
    ('Orphan order_payments (no parent order)',
     'SELECT COUNT(*) FROM order_payments WHERE order_id NOT IN (SELECT order_id FROM orders)'),
    ('Orphan order_reviews (no parent order)',
     'SELECT COUNT(*) FROM order_reviews WHERE order_id NOT IN (SELECT order_id FROM orders)'),
    ('Orders without review',
     'SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_id NOT IN (SELECT order_id FROM order_reviews)'),
    ('Orders without payment',
     'SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_id NOT IN (SELECT order_id FROM order_payments)'),
    ('Orders without items',
     'SELECT COUNT(DISTINCT order_id) FROM orders WHERE order_id NOT IN (SELECT order_id FROM order_items)'),
    ('Products with unknown category',
     "SELECT COUNT(*) FROM products WHERE product_category_name = 'unknown'"),
    ('Null delivery_days in orders',
     'SELECT COUNT(*) FROM orders WHERE delivery_days IS NULL'),
]
for label, sql in checks:
    val = conn.execute(sql).fetchone()[0]
    status = 'OK' if val == 0 else f'WARN: {val:,}'
    print(f'  {label:45s} {status}')

print()
print('=== VIEW SAMPLES ===')
print('v_sales_monthly (top 5):')
import pandas as pd
df = pd.read_sql('SELECT * FROM v_sales_monthly ORDER BY purchase_year_month LIMIT 5', conn)
print(df.to_string(index=False))

print()
print('v_payment_mix:')
df2 = pd.read_sql('SELECT * FROM v_payment_mix', conn)
print(df2.to_string(index=False))

conn.close()
print('\nDone.')

