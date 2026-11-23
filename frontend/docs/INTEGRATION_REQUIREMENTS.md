# Integrasi dashboard ProdPulse AI

Overview memakai `GET /health`, `GET /api/v1/analytics/overview`, dan `GET /api/v1/models/active`. KPI keempat memakai versi model karena kontrak ringkasan belum memuat angka ketercapaian target. Filter departemen di riwayat berlaku untuk halaman yang dimuat melalui `limit` dan `offset`.

## Data yang dibutuhkan dari Rendi dan Faiz

| Panel | Kebutuhan untuk integrasi |
|---|---|
| Productivity trend | Pilih endpoint historis yang resmi. Sepakati agregasi produktivitas aktual per periode, urutan periode, satuan rasio, rentang tanggal, dan semantik periode tanpa data. |
| Team productivity | Konfirmasi skema `GET /api/v1/analytics/teams`. Sepakati identitas tim dan departemen, periode agregasi, mean aktual dalam rasio, serta keadaan kosong. |
| Formulir | Konfirmasi skema `GET /api/v1/meta/options`, terutama hubungan ID tim dan departemen. |

Sediakan OpenAPI dan contoh respons berisi data, kosong, dan gagal. Setelah skema disepakati, validasi respons di `frontend/api_client.py` dan teruskan pasangan label serta nilai ke komponen Plotly. Saat ini grafik mode API memakai sampel maksimal 12 estimasi dari halaman pertama riwayat prediksi. Grafik riwayat aktual menunggu skema tersebut. Mode `mock` memakai fixture deterministik berlabel **MOCK DATA**, dengan KPI historis, grafik bulanan, dan rekap tim yang dihitung dari kumpulan fixture yang sama.

Integrasi langsung belum teruji karena FastAPI lokal pada port 8000 tidak dapat dijangkau. Tes UI mode API memakai stub transport yang mengikuti skema bersama.
