# ADY291c_AI2107_GROUP2

## Overview

This project analyzes the Olist Brazilian e-commerce dataset using Python, SQL, and Streamlit.

## Data
Bộ dữ liệu được sử dụng: [Brazilian E-Commerce Public Dataset by Olist](https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce)

## Python setup (Windows)

The project targets Python 3.15 or newer. Install Python 3.15 with the official Python Install Manager, then create a virtual environment from the repository root:

```powershell
py install 3.15
py -3.15 --version
py -3.15 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

In VS Code, select the `.venv` interpreter and choose its Python kernel when opening a notebook.

Run commands from the repository root so the scripts can find the `data` and `sql` directories:

```powershell
# Start the Streamlit dashboard
streamlit run dashboard\app.py

# Rebuild the SQLite database from cleaned CSV files
.\.venv\Scripts\python.exe scripts\database\build_db.py

# Run the SQL business queries (requires scripts\database\olist.db)
python scripts\database\run_queries.py

# Run the machine-learning analysis (requires scripts\database\olist.db)
python scripts\modeling\run_ml.py
```

`build_db.py` replaces the existing `data\olist.db`. The cleaned CSV files must be present in `data\processed` before running it. The dashboard reads `data\processed\olist_master.csv`.

## Team Members
- Phùng Văn Tráng - HE200218
- Nguyễn Văn Khanh - HE200414
- Lê Quốc Trung - HE204010

## Technologies
- Python
- Pandas, NumPy
- Scikit-learn
- Matplotlib, Seaborn
