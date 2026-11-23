# Log Eksperimen Machine Learning — ProdPulse AI

**Owner:** Barra (`feature/barra-ml`)  
**Dataset:** Productivity Prediction of Garment Employees — UCI #597 (DOI: `10.24432/C51S6D`, CC BY 4.0)  
**Kontrak Schema:** `v1.0`

## 1. Audit Data & Kebijakan EDA
- **Jumlah Observasi:** 1.197 baris data historis produksi garmen.
- **Normalisasi Kategori:** Ditemukan *typo* `"sweing"` dan spasi berlebih pada kolom `department`; seluruhnya dinormalisasi menjadi `"sewing"` dan `"finishing"` melalui `shared/normalization.py`.
- **Missing Values:** Kolom `wip` memiliki nilai hilang yang signifikan, namun dikecualikan dari model MVP karena bukan fitur *pre-shift* yang terverifikasi. Enam fitur *pre-shift* utama lengkap tanpa nilai kosong pada dataset asal, tetap dilindungi `SimpleImputer` di dalam pipeline.
- **Nilai Ekstrem & Pecahan:**
  - `actual_productivity` mengandung nilai $> 1.0$; dipertahankan tanpa *clipping* sesuai kontrak ilmiah.
  - `no_of_workers` (`worker_count`) mengandung nilai pecahan (mis. `30.5`); dipertahankan sebagai `float`.
- **Pencegahan Data Leakage:** Fitur pasca-shift (`over_time`, `incentive`, `idle_time`, `idle_men`, `no_of_style_change`, `wip`) tidak digunakan. Pembagian data dilakukan secara kronologis berbasis tanggal unik (`production_date`) sehingga baris pada tanggal yang sama tidak terpecah antar-split.

## 2. Konfigurasi Model & Reprodusibilitas
- **Fitur Input (6 fitur tetap):** `department`, `team_id`, `target_productivity`, `smv_minutes`, `worker_count`, `day_of_week` (turunan).
- **Preprocessing:** `ColumnTransformer` (`StandardScaler` + `SimpleImputer(median)` untuk numerik; `OneHotEncoder(handle_unknown="ignore")` + `SimpleImputer(most_frequent)` untuk kategorikal), di-*fit* hanya pada data training.
- **Random State:** `42`
- **Rasio Split Kronologis:** 70% Train, 15% Validation, 15% Holdout Test (berdasarkan urutan tanggal unik).

## 3. Hasil Evaluasi Komparatif

| Model | Split | MAE | RMSE | R² |
|---|---|---|---|---|
| `dummy-mean-v1` (Baseline) | Validation | 0.134914 | 0.192398 | -0.207176 |
| `ridge-v1` | Validation | 0.127795 | 0.181979 | -0.079971 |
| **`rf-v1` (Terpilih)** | **Validation** | **0.114092** | **0.164605** | **0.116400** |
| `dummy-mean-v1` (Baseline) | Holdout Test | 0.113468 | 0.157344 | -0.031337 |
| `ridge-v1` | Holdout Test | 0.092994 | 0.137029 | 0.217785 |
| **`rf-v1` (Terpilih)** | **Holdout Test** | **0.095776** | **0.129510** | **0.301274** |

## 4. Kesimpulan Eksperimen
- Model `rf-v1` (`RandomForestRegressor`, `n_estimators=200`, `max_depth=8`, `min_samples_leaf=3`) dipilih sebagai model aktif karena menghasilkan RMSE terendah pada data validasi (`0.164605`) dan holdout test (`0.129510`), serta meningkatkan R² menjadi `0.301274` dibandingkan baseline maupun regresi linear.
- Nilai R² sebesar `0.301` mencerminkan batas alami prediksi *pre-shift-only* tanpa variabel gangguan selama shift berlangsung.