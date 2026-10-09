# ADY291c-AI2107-Group2
#Hello
#my name is Tráng


### 📥 Bước 1: Chuẩn bị dữ liệu thô (Raw Data)
* **Việc làm:** Bạn tải 9 file CSV từ Kaggle về.
* **Nơi lưu:** Copy thẳng vào thư mục `data/raw/`.

### 🧹 Bước 2: Dọn rác - Tiền xử lý Nhịp 1 (Cleaning)
* **Việc làm:** Đọc dữ liệu, xóa dòng lỗi, điền chỗ trống (NaN), sửa lại định dạng ngày tháng/số.
* **Đầu ra:** Các bảng dữ liệu "sạch sẽ, con người đọc hiểu được". Lưu vào `data/processed/`.
* **Nơi code:** `notebooks/02_preprocessing.ipynb` và `scripts/clean/`.

### 🗄️ Bước 3: Đưa dữ liệu lên Database (SQL)
* **Việc làm:** Viết code SQL tạo bảng (Schema), nối các khóa (Primary Key - Foreign Key). Dùng Python đẩy các file sạch ở Bước 2 vào Database. Viết truy vấn tính toán doanh thu, giao hàng, RFM.
* **Đầu ra:** Một Database hoàn chỉnh sẵn sàng để truy vấn.
* **Nơi code:** Thư mục `sql/` và `scripts/database/`.

### 📊 Bước 4: Phân tích và Vẽ biểu đồ (EDA)
* **Việc làm:** Lấy dữ liệu từ Database ra để vẽ bản đồ khách hàng (Folium), vẽ biểu đồ xu hướng mua sắm, các phương thức thanh toán (Matplotlib/Seaborn).
* **Đầu ra:** Các hình ảnh biểu đồ trực quan (lưu vào `reports/figures/`).
* **Nơi code:** `notebooks/03_analysis_python.ipynb` và `04_visualization.ipynb`.

### 🤖 Bước 5: Tiền xử lý Nhịp 2 & Machine Learning
* **Việc làm:** Ép kiểu dữ liệu (chữ thành số), chuẩn hóa số liệu (Scale) để máy tính đọc được. Sau đó chạy thuật toán K-Means (Phân loại khách VIP/rời bỏ) hoặc Regression (Dự đoán điểm đánh giá).
* **Đầu ra:** Kết quả phân tích sâu của AI.
* **Nơi code:** `notebooks/05_regression_kmeans.ipynb` và `scripts/modeling/`.

### 🌐 Bước 6: Lên sóng Dashboard (Streamlit)
* **Việc làm:** Gom tất cả biểu đồ ở Bước 4 và kết quả AI ở Bước 5, nhúng lên một trang web tương tác (có menu chọn tháng, nút bấm filter,...).
* **Đầu ra:** Giao diện Dashboard chuyên nghiệp để demo cho thầy cô.
* **Nơi code:** `dashboard/app.py`.


