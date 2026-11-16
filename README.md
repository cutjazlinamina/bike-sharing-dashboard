# Bike Sharing Dashboard

Dashboard Streamlit untuk proyek analisis data Bike Sharing Dataset (Capital Bikeshare, Washington D.C., 2011-2012).

## Struktur Direktori

```
submission
├── dashboard
│   ├── main_data.csv          # data harian yang sudah dibersihkan
│   ├── main_data_hour.csv     # data per jam yang sudah dibersihkan
│   └── dashboard.py
├── data
│   ├── day.csv
│   └── hour.csv
├── notebook.ipynb
├── README.md
├── requirements.txt
└── url.txt
```

## Menjalankan Dashboard

1. Masuk ke folder proyek:

```
cd submission
```

2. (Opsional) Buat virtual environment:

```
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

3. Install library:

```
pip install -r requirements.txt
```

4. Jalankan dashboard:

```
streamlit run dashboard/dashboard.py
```

Dashboard akan terbuka di `http://localhost:8501`.

## Menjalankan Notebook

Jalankan `notebook.ipynb` dari folder `submission` agar jalur `data/day.csv` dan `data/hour.csv` terbaca. Menjalankan bagian Cleaning Data akan membuat ulang `dashboard/main_data.csv` dan `dashboard/main_data_hour.csv`.
