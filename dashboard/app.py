import os
import numpy as np
import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Olist E-Commerce Data Science Presentation",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRO_DIR = os.path.join(BASE_DIR, "data", "processed")
FIG_DIR = os.path.join(BASE_DIR, "reports", "figures")

st.markdown(
    """
    <style>
    .main-header {
        background: linear-gradient(135deg, #0f172a 0%, #1e3a8a 60%, #2563eb 100%);
        color: white;
        padding: 1.6rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.2rem;
        box-shadow: 0 8px 24px rgba(15, 23, 42, 0.18);
    }
    .main-header h1 {
        margin: 0;
        font-size: 2rem;
        font-weight: 800;
        color: #ffffff;
    }
    .main-header p {
        margin: 0.4rem 0 0 0;
        font-size: 1rem;
        color: #cbd5e1;
    }
    .kpi-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-left: 5px solid #2563eb;
        border-radius: 12px;
        padding: 1rem 1.2rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
        margin-bottom: 0.8rem;
    }
    .kpi-title {
        font-size: 0.82rem;
        font-weight: 600;
        text-transform: uppercase;
        color: #64748b;
        margin-bottom: 0.25rem;
    }
    .kpi-value {
        font-size: 1.55rem;
        font-weight: 800;
        color: #0f172a;
    }
    .kpi-sub {
        font-size: 0.8rem;
        color: #059669;
        margin-top: 0.2rem;
    }
    .slide-box {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 14px;
        padding: 1.25rem 1.5rem;
        margin-bottom: 1rem;
    }
    .speaker-note {
        background: #fffbeb;
        border-left: 4px solid #f59e0b;
        padding: 0.9rem 1.2rem;
        border-radius: 8px;
        font-size: 0.95rem;
        color: #78350f;
        margin-top: 0.8rem;
    }
    .badge {
        display: inline-block;
        padding: 0.2rem 0.65rem;
        border-radius: 999px;
        font-size: 0.78rem;
        font-weight: 700;
        background: #dbeafe;
        color: #1e40af;
        margin-right: 0.4rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner="Đang tải dữ liệu đã làm sạch...")
def load_data():
    master_path = os.path.join(PRO_DIR, "olist_master.csv")
    master = pd.read_csv(
        master_path,
        dtype={"customer_zip_code_prefix": str, "seller_zip_code_prefix": str},
        parse_dates=["order_purchase_timestamp"],
    )
    orders = (
        master.groupby("order_id", as_index=False)
        .agg(
            customer_unique_id=("customer_unique_id", "first"),
            customer_state=("customer_state", "first"),
            customer_zip_code_prefix=("customer_zip_code_prefix", "first"),
            purchase_ts=("order_purchase_timestamp", "first"),
            year_month=("purchase_year_month", "first"),
            purchase_year=("purchase_year", "first"),
            weekday=("purchase_weekday", "first"),
            hour=("purchase_hour", "first"),
            n_items=("order_item_id", "count"),
            product_value=("price", "sum"),
            freight_value=("freight_value", "sum"),
            payment_total=("payment_total", "first"),
            payment_type=("payment_type", "first"),
            payment_installments=("payment_installments", "first"),
            delivery_days=("delivery_days", "first"),
            estimated_days=("estimated_days", "first"),
            delay_days=("delay_days", "first"),
            is_late=("is_late", "first"),
            review_score=("review_score", "first"),
            same_state=("same_state", "all"),
        )
    )
    return master, orders


master, orders = load_data()

# ======================== SIDEBAR NAVIGATION & FILTERS ========================
with st.sidebar:
    st.markdown("## 🎓 ADY201m - Group 2")
    st.caption("Dự án Khoa học Dữ liệu: Phân tích TMĐT Olist Brazil (2016–2018)")
    mode = st.radio(
        "Chế độ hiển thị",
        ["🎤 Chế độ Thuyết trình (Từng Slide)", "📊 Chế độ Dashboard Tương tác"],
        index=0,
    )
    show_notes = st.toggle("Hiện gợi ý lời thuyết trình (Speaker Notes)", value=True)
    st.divider()
    st.markdown("### 🔍 Bộ lọc dữ liệu động")
    years = sorted(orders["purchase_year"].dropna().unique().tolist())
    sel_years = st.multiselect("Năm mua hàng", years, default=years)
    all_states = sorted(orders["customer_state"].dropna().unique().tolist())
    sel_states = st.multiselect("Bang khách hàng (để trống = tất cả)", all_states, default=[])
    late_filter = st.selectbox(
        "Trạng thái giao hàng",
        ["Tất cả đơn", "Chỉ đơn đúng hạn", "Chỉ đơn giao trễ"],
        index=0,
    )

# Apply filters
f_orders = orders[orders["purchase_year"].isin(sel_years)].copy()
if sel_states:
    f_orders = f_orders[f_orders["customer_state"].isin(sel_states)]
if late_filter == "Chỉ đơn đúng hạn":
    f_orders = f_orders[~f_orders["is_late"]]
elif late_filter == "Chỉ đơn giao trễ":
    f_orders = f_orders[f_orders["is_late"]]

f_master = master[master["order_id"].isin(set(f_orders["order_id"]))].copy()

# ======================== HEADER & KPI BAR ========================
st.markdown(
    """
    <div class="main-header">
        <h1>🇧🇷 Phân Tích Dữ Liệu Thương Mại Điện Tử Olist (Brazil, 2016–2018)</h1>
        <p>Quy trình Data Science hoàn chỉnh: 01. EDA &rarr; 02. Tiền xử lý &rarr; 03. Phân tích Thống kê &rarr; 04. Trực quan hoá &amp; Đề xuất Chiến lược</p>
    </div>
    """,
    unsafe_allow_html=True,
)


def render_kpi_row(df_ord, df_mst):
    c1, c2, c3, c4, c5, c6 = st.columns(6)
    total_orders = len(df_ord)
    unique_cust = df_ord["customer_unique_id"].nunique()
    rev = df_ord["product_value"].sum()
    aov = df_ord["payment_total"].mean() if total_orders else 0
    avg_score = df_ord["review_score"].mean() if total_orders else 0
    late_pct = df_ord["is_late"].mean() * 100 if total_orders else 0

    kpis = [
        (c1, "Tổng số đơn hàng", f"{total_orders:,}", f"{df_mst.shape[0]:,} sản phẩm"),
        (c2, "Khách hàng duy nhất", f"{unique_cust:,}", f"{df_mst['seller_id'].nunique():,} người bán"),
        (c3, "Doanh thu hàng hoá", f"{rev:,.0f} BRL", f"Tổng TT: {df_ord['payment_total'].sum():,.0f} BRL"),
        (c4, "Giá trị đơn TB (AOV)", f"{aov:,.2f} BRL", f"Ship TB: {df_ord['freight_value'].mean():,.2f} BRL"),
        (c5, "Điểm Review TB", f"{avg_score:.2f} ★", f"Trung vị giao: {df_ord['delivery_days'].median():.1f} ngày"),
        (c6, "Tỷ lệ giao trễ", f"{late_pct:.2f}%", "Đúng hạn: {:.2f}%".format(100 - late_pct)),
    ]
    for col, title, val, sub in kpis:
        with col:
            st.markdown(
                f"""
                <div class="kpi-card">
                    <div class="kpi-title">{title}</div>
                    <div class="kpi-value">{val}</div>
                    <div class="kpi-sub">{sub}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )


render_kpi_row(f_orders, f_master)


def speaker_box(text: str):
    if show_notes:
        st.markdown(
            f'<div class="speaker-note">🎙️ <b>Gợi ý thuyết trình:</b> {text}</div>',
            unsafe_allow_html=True,
        )


def show_saved_or_plot(fig_filename: str, caption: str):
    path = os.path.join(FIG_DIR, fig_filename)
    if os.path.exists(path):
        st.image(path, caption=caption, use_container_width=True)
    else:
        st.warning(f"Không tìm thấy {fig_filename}")


# ======================== SLIDE RENDERERS ========================
def slide_01_overview():
    st.subheader("📌 Phần 1: Tổng quan Dự án & Khám phá Dữ liệu Gốc (Notebook 01 - EDA)")
    col1, col2 = st.columns([1.15, 1])
    with col1:
        st.markdown(
            """
            <div class="slide-box">
            <span class="badge">Notebook 01</span> <b>Bối cảnh & Cấu trúc 9 bảng dữ liệu gốc</b>
            <ul>
                <li><b>Nguồn dữ liệu:</b> Hệ sinh thái thương mại điện tử Olist tại Brazil giai đoạn <b>2016–2018</b>, gồm <b>9 bảng CSV</b> trong <code>data/raw/</code> liên kết qua <code>order_id</code>, <code>customer_id</code>, <code>product_id</code>, <code>seller_id</code> và <code>zip_code_prefix</code>.</li>
                <li><b>Quy mô dữ liệu thô:</b> 99,441 đơn hàng · 112,650 dòng sản phẩm · 103,886 dòng thanh toán · 99,224 đánh giá · 1,000,163 dòng toạ độ địa lý.</li>
                <li><b>Phát hiện trọng yếu từ EDA:</b>
                    <ul>
                        <li><b>97.02%</b> đơn hàng ở trạng thái <code>delivered</code> (nhưng có 8 đơn thiếu ngày giao thực tế).</li>
                        <li><b>775 đơn</b> không có sản phẩm (<code>items</code>) và <b>1 đơn</b> không có bản ghi thanh toán.</li>
                        <li>Phân phối giá lệch phải mạnh: ngưỡng IQR trên là <b>277.40 BRL</b> với <b>8,427 sản phẩm (7.48%)</b> vượt ngưỡng — đây là hàng giá trị cao thật, <b>không phải lỗi nhập liệu</b>.</li>
                        <li>Bảng <code>geolocation</code> có <b>26.18%</b> dòng trùng lặp (~52.6 dòng/zip) và <b>42 toạ độ</b> nằm ngoài lãnh thổ Brazil.</li>
                    </ul>
                </li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with col2:
        eda_summary = pd.DataFrame(
            [
                ("orders", "99,441", "0", "2,98% thiếu ngày giao; cột ngày dạng chuỗi"),
                ("items", "112,650", "0", "7.48% giá > 277.40 BRL (ngoại lai thật)"),
                ("payments", "103,886", "0", "3 dòng not_defined, 9 dòng = 0 BRL, 2 dòng 0 kỳ"),
                ("reviews", "99,224", "0", "547 đơn >1 review; 88.3% thiếu tiêu đề"),
                ("products", "32,951", "0", "610 SP thiếu danh mục; sai chính tả 'lenght'"),
                ("customers", "99,441", "0", "Zip code mất số 0 đầu nếu đọc kiểu số"),
                ("sellers", "3,095", "0", "Cần chuẩn hoá tên thành phố / bang"),
                ("geolocation", "1,000,163", "261,831", "52.6 dòng/zip; 42 điểm ngoài lãnh thổ Brazil"),
                ("category", "71", "0", "Thiếu bản dịch tiếng Anh cho 2 danh mục"),
            ],
            columns=["Bảng", "Số dòng gốc", "Dòng trùng", "Vấn đề phát hiện trong EDA"],
        )
        st.dataframe(eda_summary, use_container_width=True, hide_index=True)

    speaker_box(
        "Ở Giai đoạn 1 (Notebook 01), nhóm tiến hành kiểm tra toàn diện 9 bảng dữ liệu gốc với hơn 1,5 triệu bản ghi. "
        "Điểm quan trọng nhất nhóm phát hiện là giá sản phẩm lệch phải (7.48% vượt ngưỡng IQR 277.40 BRL), "
        "nhưng đây là các mặt hàng đắt tiền thật trên sàn. Vì vậy ở bước tiếp theo nhóm quyết định gắn cờ thay vì cắt giá để bảo toàn doanh thu thực tế."
    )


def slide_02_preprocessing():
    st.subheader("🧹 Phần 2: Quy trình Làm sạch & Tiền xử lý Dữ liệu (Notebook 02)")
    c1, c2 = st.columns([1.05, 1])
    with c1:
        st.markdown(
            """
            <div class="slide-box">
            <span class="badge">Notebook 02</span> <b>6 Bước Làm Sạch &amp; Đồng Bộ Khoá</b>
            <ol>
                <li><b>Bảo toàn Zip Code:</b> Đọc mã bưu chính dạng <code>str</code> và chuẩn hoá đủ 5 ký tự bằng <code>.str.zfill(5)</code>.</li>
                <li><b>Làm sạch chuyên sâu từng bảng:</b>
                    <ul>
                        <li><b>Orders:</b> Ép kiểu 5 cột datetime, lọc đơn <code>delivered</code> có ngày giao hợp lệ (&ge; ngày mua).</li>
                        <li><b>Items:</b> Tạo cờ <code>is_price_outlier</code> (8,427 dòng &gt; 277.40 BRL) và <code>item_total = price + freight_value</code> — <b>không cắt giá</b>.</li>
                        <li><b>Payments &amp; Reviews:</b> Loại bỏ <code>not_defined</code> / giá trị 0; giữ 1 review mới nhất/đơn + tạo cờ <code>has_comment</code>.</li>
                        <li><b>Products &amp; Category:</b> Sửa lỗi chính tả <code>lenght &rarr; length</code>, điền <code>unknown</code> cho danh mục trống, bổ sung bản dịch cho <code>pc_gamer</code> và <code>portateis_cozinha...</code>.</li>
                        <li><b>Geolocation:</b> Lọc khung toạ độ lãnh thổ Brazil và gom nhóm còn <b>1 toạ độ trung bình / zip</b> (giảm từ 1,000,163 xuống 19,011 dòng).</li>
                    </ul>
                </li>
                <li><b>Đồng bộ khoá ngoại:</b> Loại bỏ toàn bộ bản ghi mồ côi giữa các bảng.</li>
                <li><b>Feature Engineering:</b> Tạo <code>delivery_days</code>, <code>estimated_days</code>, <code>delay_days</code>, <code>is_late</code>, <code>product_volume_cm3</code>, <code>same_state</code>.</li>
                <li><b>Kiểm định tự động:</b> Vượt qua <b>14/14 bài kiểm tra</b> bằng <code>assert</code>, xuất 9 bảng sạch + <code>olist_master.csv</code> (<b>110,186 dòng &times; 49 cột</b>).</li>
            </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with c2:
        clean_comp = pd.DataFrame(
            [
                ("orders", 99441, 96469, 97.01, "Chỉ giữ đơn delivered đồng bộ khoá"),
                ("items", 112650, 110186, 97.81, "Gắn cờ ngoại lai giá, không cắt giá"),
                ("payments", 103886, 100739, 96.97, "Loại giá trị 0 / not_defined"),
                ("reviews", 99224, 95823, 96.57, "1 review mới nhất cho mỗi đơn"),
                ("products", 32951, 32214, 97.76, "Điền median kích thước, tạo volume_cm3"),
                ("customers", 99441, 96469, 97.01, "Chuẩn hoá zip 5 số, city/state"),
                ("sellers", 3095, 2970, 95.96, "Đồng bộ theo các đơn hợp lệ"),
                ("geolocation", 1000163, 19011, 1.90, "Gộp 1 toạ độ trung bình / mã zip"),
                ("category", 71, 74, 104.23, "Thêm 3 bản dịch thiếu & unknown"),
                ("olist_master", np.nan, 110186, np.nan, "Bảng tổng hợp 49 cột sẵn sàng phân tích"),
            ],
            columns=["Bảng", "Dòng gốc (Raw)", "Dòng sạch (Clean)", "Giữ lại (%)", "Ghi chú xử lý"],
        )
        st.dataframe(clean_comp, use_container_width=True, hide_index=True)
        st.success("✅ Tất cả 14/14 điều kiện kiểm định chất lượng dữ liệu (Data Quality Checks) đều ĐẠT 100%.")

    speaker_box(
        "Ở Giai đoạn 2 (Notebook 02), nhóm khắc phục triệt để các hạn chế của code cũ: không dùng IQR capping làm sai lệch doanh thu, "
        "đồng bộ khoá ngoại giữa cả 9 bảng để không còn bản ghi mồ côi, rút gọn bảng Geolocation từ 1 triệu dòng xuống 19 nghìn mã zip duy nhất, "
        "và hợp nhất thành bảng olist_master.csv gồm 110,186 dòng và 49 cột."
    )


def slide_03_growth_and_time():
    st.subheader("📈 Phần 3: Tăng trưởng Doanh thu & Thời điểm Mua sắm (Notebook 03 & 04)")
    c1, c2 = st.columns(2)
    with c1:
        show_saved_or_plot("01_monthly_revenue.png", "Doanh thu và số đơn hàng theo tháng (01/2017 – 08/2018)")
        st.markdown(
            """
            - **Tăng trưởng bứt phá:** So sánh cùng kỳ tháng 1–8, doanh thu năm 2018 đạt **7,217,172 BRL**, tăng **+141.1%** so với năm 2017 (**2,993,277 BRL**).
            - **Đỉnh doanh thu lịch sử:** Tháng **11/2017 (Black Friday)** đạt **987,648 BRL** với **7,288 đơn hàng** (tăng +52.6% so với tháng 10/2017).
            """
        )
    with c2:
        show_saved_or_plot("02_weekday_hour_heatmap.png", "Ma trận nhiệt số đơn hàng theo Thứ × Giờ")
        st.markdown(
            """
            - **Theo ngày trong tuần:** Mua sắm sôi động nhất vào đầu tuần (**Thứ Hai: 15,701 đơn**, **Thứ Ba: 15,502 đơn**) và giảm mạnh vào **Thứ Bảy (10,555 đơn)**.
            - **Theo khung giờ:** Đỉnh cao điểm lúc **16h chiều**; khung giờ **10h–21h chiếm 75.6%** tổng lượng đơn, trong khi **0h–6h sáng chỉ chiếm 5.3%**.
            """
        )
    speaker_box(
        "Biểu đồ bên trái cho thấy tốc độ tăng trưởng hơn 141% theo năm của Olist và sức bật mạnh mẽ của sự kiện Black Friday tháng 11/2017. "
        "Biểu đồ nhiệt bên phải chỉ ra hành vi mua sắm tập trung vào giờ hành chính và buổi tối các ngày đầu tuần — đây là cơ sở để lên lịch chạy Flash Sale và phân bổ ngân sách quảng cáo."
    )


def slide_04_category_and_payment():
    st.subheader("🛍️ Phần 4: Phân tích Pareto Danh mục & Hành vi Thanh toán (Notebook 03 & 04)")
    c1, c2 = st.columns([1.15, 1])
    with c1:
        show_saved_or_plot("03_category_pareto.png", "Top 20 danh mục sản phẩm & Đường cong Pareto luỹ kế")
        cat_df = (
            f_master.groupby("product_category_name_english", as_index=False)
            .agg(
                revenue=("price", "sum"),
                n_items=("order_item_id", "count"),
                avg_price=("price", "mean"),
                avg_score=("review_score", "mean"),
            )
            .sort_values("revenue", ascending=False)
        )
        cat_df["share_%"] = (cat_df["revenue"] / cat_df["revenue"].sum() * 100).round(2)
        cat_df["cum_%"] = cat_df["share_%"].cumsum().round(2)
        st.dataframe(cat_df.head(8), use_container_width=True, hide_index=True)
    with c2:
        show_saved_or_plot("08_payment.png", "Tỷ trọng phương thức thanh toán & Số kỳ trả góp thẻ tín dụng")
        st.markdown(
            """
            <div class="slide-box">
            <b>Insight Danh mục &amp; Thanh toán:</b>
            <ul>
                <li><b>Quy luật Pareto 80/20:</b> Chỉ <b>18/74 danh mục (24%)</b> đóng góp tới <b>80% tổng doanh thu</b>.</li>
                <li><b>Top 5 ngành hàng dẫn đầu:</b> <code>health_beauty</code> (9.33%), <code>watches_gifts</code> (8.82%), <code>bed_bath_table</code> (7.74%), <code>sports_leisure</code> (7.22%), <code>computers_accessories</code> (6.72%).</li>
                <li><b>Thẻ tín dụng thống trị:</b> Chiếm <b>75.48%</b> tổng số đơn, tiếp theo là <code>boleto</code> (19.89%), <code>voucher</code> (3.09%) và <code>debit_card</code> (1.54%).</li>
                <li><b>Ưa chuộng trả góp:</b> Có tới <b>67.9%</b> đơn thẻ tín dụng chọn trả góp từ 2 kỳ trở lên; số kỳ càng cao thì giá trị đơn trung bình (AOV) càng lớn (nhóm &gt;10 kỳ có AOV <b>377.45 BRL</b> so với 1 kỳ chỉ <b>110.27 BRL</b>).</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
    speaker_box(
        "Phân tích Pareto khẳng định 24% danh mục tạo ra 80% doanh thu cho toàn sàn. "
        "Về thanh toán, khách hàng Brazil đặc biệt ưa chuộng trả góp qua thẻ tín dụng: gần 68% đơn thẻ tín dụng trả góp nhiều kỳ, và chính sách trả góp giúp tăng gấp 3 lần giá trị giỏ hàng."
    )


def slide_05_geography_and_logistics():
    st.subheader("🗺️ Phần 5: Phân bố Địa lý & Hiệu quả Giao vận (Notebook 03 & 04)")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        show_saved_or_plot("04_state_orders_delivery.png", "Số đơn hàng và Số ngày giao trung bình theo Bang")
        st.markdown(
            """
            - **Tập trung tại Đông Nam:** Ba bang **SP (42.0%), RJ (12.8%), MG (11.8%)** chiếm tới **66.5%** tổng lượng đơn toàn quốc.
            - **Bất bình đẳng hạ tầng logistics:** Bang **SP** giao trung bình chỉ **8.8 ngày** (trễ 4.2%), trong khi các bang miền Bắc như **AP (27.2 ngày)**, **RR (29.4 ngày)** mất gần 1 tháng; các bang Đông Bắc như **AL (trễ 21.4%)**, **MA (trễ 17.5%)** có tỷ lệ giao trễ rất cao.
            - **Lợi thế nội bang (`same_state`):** Đơn mua từ người bán cùng bang (chiếm 35.8% đơn) giao trung bình **7.95 ngày** (phí ship 15.22 BRL), nhanh gần gấp đôi so với đơn khác bang (**15.13 ngày**, phí ship 26.99 BRL).
            """
        )
    with c2:
        show_saved_or_plot("05_delivery_map.png", "Bản đồ thời gian giao hàng theo toạ độ Zip Code (99.7% đơn)")
    speaker_box(
        "Bản đồ không gian địa lý cho thấy sự phân cực rõ rệt giữa vùng Đông Nam/Nam (màu xanh - giao nhanh 8 đến 12 ngày) và vùng Bắc/Đông Bắc (màu cam/đỏ - giao từ 20 đến gần 30 ngày). "
        "Đặc biệt, giao dịch nội bang rút ngắn một nửa thời gian vận chuyển từ 15.1 ngày xuống 7.95 ngày."
    )


def slide_06_statistical_tests():
    st.subheader("🧪 Phần 6: Kiểm định Thống kê — Giao hàng trễ & Điểm Review (Notebook 03 & 04)")
    c1, c2 = st.columns([1.15, 1])
    with c1:
        show_saved_or_plot("06_late_vs_review.png", "Phân bố số sao và Điểm review trung bình theo mức độ trễ")
        show_saved_or_plot("07_delivery_days_hist.png", "Phân phối số ngày giao hàng thực tế vs dự kiến")
    with c2:
        st.markdown(
            """
            <div class="slide-box">
            <span class="badge">Hypothesis Testing</span> <b>Kết quả 3 Kiểm định Thống kê (&alpha; = 0.05)</b>
            <ul>
                <li><b>So sánh thực nghiệm:</b>
                    <ul>
                        <li>Đơn <b>Đúng hạn</b> (93.23%): Điểm TB = <b>4.29 ★</b> | Tỷ lệ 5★ = <b>61.97%</b> | Tỷ lệ &le;2★ = <b>9.22%</b></li>
                        <li>Đơn <b>Giao trễ</b> (6.77%): Điểm TB = <b>2.27 ★</b> | Tỷ lệ 5★ = <b>17.77%</b> | Tỷ lệ &le;2★ = <b>60.95%</b></li>
                    </ul>
                </li>
                <li><b>1. Mann-Whitney U Test:</b> <i>U</i> = 1.07 &times; 10<sup>8</sup>, <i>p</i> &lt; 0.0001 &rarr; <b>Bác bỏ <i>H</i><sub>0</sub></b> (đơn trễ có điểm đánh giá thấp hơn có ý nghĩa thống kê).</li>
                <li><b>2. Chi-square Test:</b> &chi;<sup>2</sup> = 13,864.5, <i>p</i> &lt; 0.0001 &rarr; <b>Bác bỏ <i>H</i><sub>0</sub></b> (giao trễ làm tăng nguy cơ bị 1–2 sao gấp <b>6.6 lần</b>).</li>
                <li><b>3. Tương quan Spearman:</b> &rho; = &minus;0.235, <i>p</i> &lt; 0.0001 &rarr; Thời gian giao hàng càng dài, điểm hài lòng càng giảm.</li>
            </ul>
            </div>
            """,
            unsafe_allow_html=True,
        )
        rv = f_orders.dropna(subset=["review_score"]).copy()
        bins = [-np.inf, 0, 3, 7, 14, np.inf]
        labels = ["Đúng/sớm hạn", "Trễ 1–3 ngày", "Trễ 4–7 ngày", "Trễ 8–14 ngày", "Trễ > 14 ngày"]
        rv["Nhóm trễ"] = pd.cut(rv["delay_days"], bins=bins, labels=labels)
        delay_tbl = (
            rv.groupby("Nhóm trễ", observed=True)
            .agg(
                Số_đơn=("order_id", "count"),
                Điểm_TB=("review_score", "mean"),
                Tỷ_lệ_1_2_sao=("review_score", lambda s: (s <= 2).mean() * 100),
            )
            .round(2)
            .reset_index()
        )
        st.dataframe(delay_tbl, use_container_width=True, hide_index=True)

    speaker_box(
        "Đây là phát hiện quan trọng nhất của dự án: dù tỷ lệ giao trễ toàn sàn chỉ chiếm 6.77%, nhưng khi đơn hàng bị trễ, điểm review trung bình sụt giảm nghiêm trọng từ 4.29 sao xuống 2.27 sao, "
        "và hơn 60% khách hàng đánh giá 1–2 sao. Chỉ cần trễ từ 4–7 ngày, điểm trung bình đã rơi xuống 2.11 sao."
    )


def slide_07_retention_and_recommendations():
    st.subheader("🎯 Phần 7: Tương quan Đa biến, Tỷ lệ Mua lại & Đề xuất Chiến lược")
    c1, c2 = st.columns([1, 1.15])
    with c1:
        show_saved_or_plot("09_correlation.png", "Ma trận tương quan Spearman giữa các biến mức đơn hàng")
        freq = f_orders.groupby("customer_unique_id").agg(
            n_orders=("order_id", "count"), spend=("payment_total", "sum")
        )
        rep = freq["n_orders"] > 1
        st.info(
            f"🔄 **Khách hàng quay lại (Customer Retention):** Chỉ **{rep.mean()*100:.2f}%** ({rep.sum():,}/{len(freq):,} khách) mua từ 2 lần trở lên, "
            f"nhưng nhóm này chi tiêu trung bình **{freq.loc[rep, 'spend'].mean():,.2f} BRL** — cao gần gấp đôi khách mua 1 lần (**{freq.loc[~rep, 'spend'].mean():,.2f} BRL**)."
        )
    with c2:
        st.markdown(
            """
            <div class="slide-box">
            <span class="badge">Actionable Insights</span> <b>5 Đề xuất Chiến lược Dựa trên Dữ liệu</b>
            <ol>
                <li><b>Tối ưu SLA Giao vận &amp; Dự báo Ngày giao (Ưu tiên #1):</b>
                    Cập nhật thuật toán ước tính ngày giao (<code>estimated_delivery_date</code>) sát thực tế cho các tuyến liên bang tới RJ, BA, AL, MA; cảnh báo sớm các đơn có nguy cơ trễ &gt;3 ngày để gửi voucher xin lỗi chủ động trước khi khách đánh giá 1 sao.</li>
                <li><b>Ưu tiên Hiển thị Người bán Nội bang (Local Routing):</b>
                    Tích hợp tiêu chí <code>same_state</code> vào thuật toán tìm kiếm sản phẩm để tăng tỷ lệ đơn nội bang (hiện 35.8%), giúp giảm một nửa thời gian giao (7.95 ngày vs 15.13 ngày) và giảm 44% phí vận chuyển.</li>
                <li><b>Mở rộng Kho Vệ tinh &amp; Tuyển Seller ngoài Đông Nam:</b>
                    Tập trung tuyển mới seller tại vùng Đông Bắc và miền Nam để giảm phụ thuộc vào cụm SP–RJ–MG (66.5% đơn).</li>
                <li><b>Tập trung Nguồn lực vào 18 Ngành hàng Pareto &amp; Trả góp:</b>
                    Đẩy mạnh gói trả góp 0% lãi suất cho các đơn trên 150 BRL ở 18 danh mục chủ lực (đặc biệt dịp Black Friday tháng 11).</li>
                <li><b>Chiến dịch Giữ chân Khách hàng (Retention Marketing):</b>
                    Triển khai chuỗi email/voucher tự động sau 14–30 ngày kể từ đơn giao thành công đầu tiên nhằm nâng tỷ lệ mua lại từ mức 3.00% hiện tại.</li>
            </ol>
            </div>
            """,
            unsafe_allow_html=True,
        )
    speaker_box(
        "Tổng kết lại, bài toán lớn nhất của Olist không nằm ở thu hút đơn mới mà ở trải nghiệm giao vận liên bang và tỷ lệ giữ chân khách hàng (chỉ 3%). "
        "5 giải pháp nhóm đề xuất đều bám sát các con số kiểm định từ dữ liệu và có thể áp dụng trực tiếp vào vận hành."
    )


# ======================== RENDER BY MODE ========================
SLIDES = [
    ("Slide 1 · Tổng quan & EDA (Notebook 01)", slide_01_overview),
    ("Slide 2 · Tiền xử lý & Làm sạch (Notebook 02)", slide_02_preprocessing),
    ("Slide 3 · Tăng trưởng & Thời điểm Mua (Notebook 03–04)", slide_03_growth_and_time),
    ("Slide 4 · Danh mục Pareto & Thanh toán (Notebook 03–04)", slide_04_category_and_payment),
    ("Slide 5 · Địa lý & Giao vận (Notebook 03–04)", slide_05_geography_and_logistics),
    ("Slide 6 · Kiểm định Thống kê: Trễ hạn & Review (Notebook 03–04)", slide_06_statistical_tests),
    ("Slide 7 · Tương quan, Mua lại & Đề xuất Chiến lược", slide_07_retention_and_recommendations),
]

if mode.startswith("🎤"):
    if "slide_idx" not in st.session_state:
        st.session_state.slide_idx = 0

    nav1, nav2, nav3 = st.columns([1, 3, 1])
    with nav1:
        if st.button("⬅️ Slide trước", use_container_width=True, disabled=st.session_state.slide_idx == 0):
            st.session_state.slide_idx -= 1
            st.rerun()
    with nav2:
        selected_title = st.selectbox(
            "Chọn Slide thuyết trình",
            [s[0] for s in SLIDES],
            index=st.session_state.slide_idx,
            label_visibility="collapsed",
        )
        st.session_state.slide_idx = [s[0] for s in SLIDES].index(selected_title)
    with nav3:
        if st.button(
            "Slide tiếp ➡️",
            use_container_width=True,
            disabled=st.session_state.slide_idx == len(SLIDES) - 1,
        ):
            st.session_state.slide_idx += 1
            st.rerun()

    st.progress((st.session_state.slide_idx + 1) / len(SLIDES))
    SLIDES[st.session_state.slide_idx][1]()
else:
    tabs = st.tabs([s[0].split("·")[1].strip() for s in SLIDES])
    for tab, (_, render_fn) in zip(tabs, SLIDES):
        with tab:
            render_fn()
