# ProdPulse AI Frontend

Dashboard Streamlit untuk estimasi produktivitas tim garmen sebelum shift. Setiap halaman menampilkan label **DEMO / Academic Prototype**.

Versi NiceGUI mencakup keempat halaman dan berjalan pada port 8502. Lihat [cara menjalankan NiceGUI](nicegui_app/README.md).

## Menjalankan aplikasi

Dari root proyek, aktifkan virtual environment Python 3.11+ dan pasang dependensi frontend.

```powershell
python -m pip install -r frontend/requirements.txt
$env:PRODPULSE_FRONTEND_MODE = "mock"
Set-Location frontend
python -m streamlit run app.py --server.port 8501
```

Buka `http://localhost:8501`. Jalankan perintah Streamlit dari `frontend/` agar konfigurasi tema lokal ikut dimuat.

Mode **MOCK DATA** memakai fixture historis 2025 yang deterministik serta respons prediksi dan chat untuk menguji antarmuka. Data historis, tren bulanan, dan rekap per tim berasal dari kumpulan fixture yang sama. Prediksi baru dalam mode ini disimpan di memori sesi dan menggunakan estimasi tetap dari contoh kontrak.

Untuk mode API, set `PRODPULSE_FRONTEND_MODE=api` dan `API_BASE_URL=http://localhost:8000` sebelum memulai Streamlit. Variabel proses mendahului nilai di `.env` root proyek. Mode API adalah default.

## Redesain dan struktur

Acuan adalah area aplikasi di `design/reference/prodpulse-ui-reference.png`. Desain lama memakai sidebar lebar, tiga KPI, dan palet biru-teal. Redesain memakai rail navy, topbar putih, latar mint, font display condensed, empat strip KPI, dan dua baris utama dengan kolom sekitar 1:3. Bingkai luar ilustrasi dilepas agar seluruh viewport dapat dipakai. Topbar mencari nama halaman, panel notifikasi menampilkan kesehatan sistem, dan avatar menandai operator demo.

| File | Tanggung jawab |
|---|---|
| `app.py`, `components/shell.py` | Navigasi, rail responsif, pencarian halaman, status dan bantuan |
| `styles.css`, `.streamlit/config.toml` | Token navy/mint/coral/hijau, gaya native dan layout |
| `pages/overview.py`, `components/dashboard.py`, `components/charts.py`, `components/presentation.py` | Empat KPI, panel status, aksi, judul, dan grafik Plotly |
| `pages/prediction.py`, `pages/history.py`, `pages/assistant.py`, `components/prediction_result.py` | Form dan draf sesi, filter dan pilihan riwayat, hasil, chat dan bukti |
| `mock_api.py`, `mock_analytics.py` | Fixture terisolasi yang hanya ditampilkan dalam mode mock |
| `../tests/test_frontend_smoke.py` | Tes kontrak UI, sumber data, pagination, filter, bukti dan state gagal |

Custom CSS memakai kelas `pp-*` dan kontainer Streamlit dengan `key="pp_*"`. Selector internal yang diperiksa di Chromium mencakup rail dan tombolnya, header dan toolbar native, kolom serta kontainer utama, tombol Material, grup selectbox/BaseWeb, trigger popover, dan permukaan form/chat. Fallback condensed memakai Bahnschrift Condensed atau Arial Narrow, dengan fallback sans-serif. Periksa kembali selector layout ketika menaikkan versi Streamlit.

## Integrasi

Data API memakai schema bersama dan melewati `api_client.py`. Overview menampilkan versi dari `GET /api/v1/models/active` sebagai KPI keempat, status dari `GET /health`, dan KPI historis dari `GET /api/v1/analytics/overview`. Form, riwayat, detail bukti, serta chat tetap memakai endpoint prediksi dan chat yang terdokumentasi.

Filter departemen dan urutan tabel berlaku pada halaman riwayat yang sedang dimuat. Pagination API mempertahankan `limit` dan `offset`. Draf, konteks, percakapan, dan `conversation_id` disimpan untuk sesi Streamlit. Saat sumber bertipe prediksi dipilih dalam chat, riwayat mengambil detail berdasarkan ID dari API.

FastAPI lokal belum dapat dijangkau. Grafik mode API meringkas maksimal 12 prediksi dari halaman pertama riwayat berdasarkan tanggal produksi dan tim. Analitik historis tetap menunggu skema API. Kebutuhan skema dan handoff untuk Faiz/Rendi ada di [Integration Requirements](docs/INTEGRATION_REQUIREMENTS.md).

## Verifikasi

Jalankan dari root proyek.

```powershell
python -m pytest -q
```

- 27 tes otomatis lulus, termasuk 6 tes kontrak starter kit. Mode API diuji dengan stub HTTP. Tes memastikan grafik fixture hanya dirender dalam mode mock.
- Chromium memverifikasi pencarian, status, bantuan, rail, quick action, form, filter riwayat, serta alur chat dan bukti. Alur desktop yang diuji bebas dari error dan peringatan console.
- Screenshot Overview diambil pada 1440 × 900 dan 390 × 844. Rail desktop terukur 104 px, topbar 84 px, dan awal panel grafik sejajar dengan KPI kedua. Layout diperiksa pada tablet 900 px, keempat halaman pada 390 px, dan Overview pada 320 px serta landscape 667 px.
