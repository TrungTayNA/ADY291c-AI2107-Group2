"""
run_ml.py — Chạy toàn bộ mô hình ML từ olist.db
Kết quả in ra console + lưu ảnh vào data/processed/
"""
import sqlite3
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')  # non-interactive backend (không cần display)
import matplotlib.pyplot as plt
import warnings
warnings.filterwarnings('ignore')

from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.metrics import r2_score, mean_squared_error, mean_absolute_error

DB_PATH  = 'data/olist.db'
OUT_DIR  = 'data/processed'
PALETTE  = ['#2196F3', '#FF9800', '#4CAF50', '#E91E63']
SEG_COLORS = {'Champion':'#2196F3','Loyal':'#4CAF50','At Risk':'#FF9800','New/Occasional':'#E91E63'}

conn = sqlite3.connect(DB_PATH)
print(f'Connected: {DB_PATH}')

# ──────────────────────────────────────────────
# PHẦN 1: K-MEANS CLUSTERING (RFM)
# ──────────────────────────────────────────────
print('\n=== PART 1: K-MEANS CLUSTERING ===')

rfm = pd.read_sql_query("""
    SELECT
        customer_unique_id,
        customer_state,
        CAST(julianday('2018-10-18') - julianday(MAX(order_purchase_timestamp)) AS INTEGER) AS recency_days,
        COUNT(DISTINCT order_id)     AS frequency,
        ROUND(SUM(payment_value),2)  AS monetary
    FROM view_order_clean
    GROUP BY customer_unique_id, customer_state
""", conn)

print(f'Customers: {len(rfm):,}')

# Cap outlier 99.5th
cap = rfm['monetary'].quantile(0.995)
rfm_clean = rfm[rfm['monetary'] <= cap].copy()
print(f'After outlier cap: {len(rfm_clean):,} (removed {len(rfm)-len(rfm_clean):,})')

features = ['recency_days', 'frequency', 'monetary']
scaler = StandardScaler()
X_scaled = scaler.fit_transform(rfm_clean[features])

# Elbow + Silhouette
K_RANGE = range(2, 9)
inertias, silhouettes = [], []
for k in K_RANGE:
    km = KMeans(n_clusters=k, random_state=42, n_init=10)
    labels = km.fit_predict(X_scaled)
    inertias.append(km.inertia_)
    sil = silhouette_score(X_scaled, labels, sample_size=5000, random_state=42)
    silhouettes.append(sil)
    print(f'  k={k}  Inertia={km.inertia_:,.0f}  Silhouette={sil:.4f}')

fig, axes = plt.subplots(1, 2, figsize=(13, 4))
axes[0].plot(K_RANGE, inertias, 'o-', color=PALETTE[0], linewidth=2)
axes[0].set_title('Elbow Method'); axes[0].set_xlabel('k'); axes[0].set_ylabel('Inertia'); axes[0].grid(alpha=0.3)
axes[1].plot(K_RANGE, silhouettes, 's-', color=PALETTE[1], linewidth=2)
best_k = list(K_RANGE)[silhouettes.index(max(silhouettes))]
axes[1].axvline(best_k, color='red', linestyle='--', label=f'Best k={best_k}')
axes[1].set_title('Silhouette Score'); axes[1].set_xlabel('k'); axes[1].legend(); axes[1].grid(alpha=0.3)
plt.suptitle('K-Means: Chon so cum toi uu', fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUT_DIR}/kmeans_elbow.png', bbox_inches='tight')
plt.close()
print(f'\nBest k = {best_k}  (saved kmeans_elbow.png)')

# Final K-Means với k=4
K_FINAL = 4
km_final = KMeans(n_clusters=K_FINAL, random_state=42, n_init=20)
rfm_clean['cluster'] = km_final.fit_predict(X_scaled)
sil_final = silhouette_score(X_scaled, rfm_clean['cluster'], sample_size=5000, random_state=42)
print(f'K-Means k={K_FINAL}: Inertia={km_final.inertia_:,.0f}  Silhouette={sil_final:.4f}')

# Profile & gán nhãn
profile = rfm_clean.groupby('cluster')[features].mean().round(2)
profile['count'] = rfm_clean.groupby('cluster').size()
profile['pct']   = (profile['count'] / len(rfm_clean) * 100).round(1)
profile = profile.sort_values('monetary', ascending=False)
labels_biz = ['Champion', 'Loyal', 'At Risk', 'New/Occasional']
profile['segment'] = labels_biz
seg_map = profile['segment'].to_dict()
rfm_clean['segment'] = rfm_clean['cluster'].map(seg_map)

print('\nProfile:')
print(profile[['count','pct','recency_days','frequency','monetary']].to_string())

# Scatter plots
color_list = [SEG_COLORS[s] for s in rfm_clean['segment']]
fig, axes = plt.subplots(1, 3, figsize=(16, 5))
axes[0].scatter(rfm_clean['recency_days'], rfm_clean['monetary'], c=color_list, alpha=0.3, s=5)
axes[0].set_xlabel('Recency (days)'); axes[0].set_ylabel('Monetary'); axes[0].set_title('Recency vs Monetary')
axes[1].scatter(rfm_clean['frequency'], rfm_clean['monetary'], c=color_list, alpha=0.3, s=5)
axes[1].set_xlabel('Frequency'); axes[1].set_ylabel('Monetary'); axes[1].set_title('Frequency vs Monetary')
seg_counts = rfm_clean['segment'].value_counts()
axes[2].pie(seg_counts, labels=seg_counts.index, colors=[SEG_COLORS[s] for s in seg_counts.index], autopct='%1.1f%%', startangle=140)
axes[2].set_title('Customer Segments')
from matplotlib.patches import Patch
legend_els = [Patch(facecolor=c, label=s) for s, c in SEG_COLORS.items()]
fig.legend(handles=legend_els, loc='lower center', ncol=4, fontsize=9)
plt.suptitle('K-Means RFM Customer Segmentation', fontweight='bold')
plt.tight_layout(rect=[0, 0.07, 1, 1])
plt.savefig(f'{OUT_DIR}/kmeans_segments.png', bbox_inches='tight')
plt.close()
print('Saved: kmeans_segments.png')

# Summary bar chart
summary = rfm_clean.groupby('segment').agg(
    so_luong=('customer_unique_id','count'),
    recency_tb=('recency_days','mean'),
    frequency_tb=('frequency','mean'),
    monetary_tb=('monetary','mean'),
    monetary_total=('monetary','sum')
).round(2)
summary['pct_khach']    = (summary['so_luong'] / summary['so_luong'].sum() * 100).round(1)
summary['pct_doanh_thu']= (summary['monetary_total'] / summary['monetary_total'].sum() * 100).round(1)
summary = summary.sort_values('monetary_tb', ascending=False)

fig, ax = plt.subplots(figsize=(9, 4))
bars = ax.bar(summary.index, summary['pct_doanh_thu'], color=[SEG_COLORS[s] for s in summary.index], edgecolor='white')
ax.bar_label(bars, fmt='%.1f%%', padding=3)
ax.set_ylabel('% Doanh thu'); ax.set_title('Dong gop Doanh Thu theo Phan Khuc', fontweight='bold')
ax.set_ylim(0, summary['pct_doanh_thu'].max() * 1.25); ax.grid(axis='y', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_DIR}/kmeans_revenue_by_segment.png', bbox_inches='tight')
plt.close()
print('Saved: kmeans_revenue_by_segment.png')

# ──────────────────────────────────────────────
# PHẦN 2: LINEAR REGRESSION
# ──────────────────────────────────────────────
print('\n=== PART 2: LINEAR REGRESSION ===')

FEATURES = ['delivery_days','delay_days','is_late','price','freight_value',
            'payment_installments','purchase_month','purchase_hour',
            'same_state','product_weight_g','product_volume_cm3']
TARGET = 'review_score'

df_reg = pd.read_sql_query(f"""
    SELECT {TARGET}, {', '.join(FEATURES)}
    FROM view_order_clean
    WHERE {TARGET} IS NOT NULL AND delivery_days IS NOT NULL
""", conn).dropna()

print(f'Regression data: {len(df_reg):,} rows')
print(f"review_score distribution:\n{df_reg[TARGET].value_counts().sort_index().to_string()}")

# Correlation
corr = df_reg[FEATURES + [TARGET]].corr()[[TARGET]].drop(TARGET).sort_values(TARGET)
fig, ax = plt.subplots(figsize=(8, 5))
colors_c = ['#E53935' if v < 0 else '#2196F3' for v in corr[TARGET]]
bars = ax.barh(corr.index, corr[TARGET], color=colors_c, edgecolor='white')
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('Pearson Correlation'); ax.set_title('Tuong quan voi review_score', fontweight='bold')
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_DIR}/regression_correlation.png', bbox_inches='tight')
plt.close()
print('Saved: regression_correlation.png')

# Train/test split & regression
X = df_reg[FEATURES]; y = df_reg[TARGET]
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
scaler_r = StandardScaler()
X_train_s = scaler_r.fit_transform(X_train)
X_test_s  = scaler_r.transform(X_test)

lr = LinearRegression()
lr.fit(X_train_s, y_train)
y_pred = lr.predict(X_test_s)

r2   = r2_score(y_test, y_pred)
mae  = mean_absolute_error(y_test, y_pred)
rmse = np.sqrt(mean_squared_error(y_test, y_pred))
cv_r2 = cross_val_score(LinearRegression(), X_train_s, y_train, cv=5, scoring='r2')

print(f'\nR2={r2:.4f}  MAE={mae:.4f}  RMSE={rmse:.4f}')
print(f'5-fold CV R2: {cv_r2.mean():.4f} +/- {cv_r2.std():.4f}')

# Coefficients
coef_df = pd.DataFrame({'feature': FEATURES, 'coefficient': lr.coef_}).sort_values('coefficient')
fig, ax = plt.subplots(figsize=(9, 5))
colors_co = ['#E53935' if v < 0 else '#2196F3' for v in coef_df['coefficient']]
bars = ax.barh(coef_df['feature'], coef_df['coefficient'], color=colors_co, edgecolor='white')
ax.axvline(0, color='black', linewidth=0.8)
ax.set_xlabel('He so hoi quy (chuan hoa)'); ax.set_title(f'Linear Regression Coefficients | R2={r2:.4f}', fontweight='bold')
ax.grid(axis='x', alpha=0.3)
plt.tight_layout()
plt.savefig(f'{OUT_DIR}/regression_coefficients.png', bbox_inches='tight')
plt.close()
print('Saved: regression_coefficients.png')

# Residuals
residuals = y_test.values - y_pred
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
jitter = np.random.normal(0, 0.1, len(y_test))
axes[0].scatter(y_pred, y_test.values + jitter, alpha=0.08, s=4, color=PALETTE[0])
mn, mx = float(y_pred.min()), float(y_pred.max())
axes[0].plot([mn, mx], [mn, mx], 'r--', linewidth=1.5)
axes[0].set_xlabel('Predicted'); axes[0].set_ylabel('Actual'); axes[0].set_title(f'Actual vs Predicted | R2={r2:.4f}')
axes[0].grid(alpha=0.3)
axes[1].hist(residuals, bins=40, color=PALETTE[1], edgecolor='white', alpha=0.85)
axes[1].axvline(0, color='red', linestyle='--')
axes[1].set_xlabel('Residual'); axes[1].set_ylabel('Count')
axes[1].set_title(f'Residuals | MAE={mae:.4f}, RMSE={rmse:.4f}')
axes[1].grid(alpha=0.3)
plt.suptitle('Linear Regression Evaluation', fontweight='bold')
plt.tight_layout()
plt.savefig(f'{OUT_DIR}/regression_evaluation.png', bbox_inches='tight')
plt.close()
print('Saved: regression_evaluation.png')

# ──────────────────────────────────────────────
# TỔNG KẾT
# ──────────────────────────────────────────────
print('\n' + '='*60)
print('  KET QUA MO HINH HOC MAY — OLIST E-COMMERCE')
print('='*60)
print(f'\n[K-Means] k={K_FINAL} | Silhouette={sil_final:.4f} | Inertia={km_final.inertia_:,.0f}')
for seg, row in summary.iterrows():
    print(f'  [{seg:16s}] {row["so_luong"]:>6,} KH | R={row["recency_tb"]:>5.0f}d | F={row["frequency_tb"]:.2f} | M=R${row["monetary_tb"]:>7.2f} | {row["pct_doanh_thu"]}% DT')

print(f'\n[Regression] R2={r2:.4f} | MAE={mae:.4f} | RMSE={rmse:.4f} | CV={cv_r2.mean():.4f}+-{cv_r2.std():.4f}')
top_neg = coef_df.iloc[0]
top_pos = coef_df.iloc[-1]
print(f'  Anh huong tieu cuc nhat : {top_neg["feature"]} (coef={top_neg["coefficient"]:.3f})')
print(f'  Anh huong tich cuc nhat : {top_pos["feature"]} (coef={top_pos["coefficient"]:.3f})')
print('='*60)

conn.close()
print('\nDone. DB connection closed.')
