# ProdPulse AI di NiceGUI

Empat halaman ProdPulse AI dengan navigasi responsif dan sesi per tab. Seluruh permintaan HTTP ke FastAPI memakai `frontend/api_client.py`.

## Menjalankan aplikasi

Dari root `prodpulse-ai`, dengan Python 3.12 di PowerShell.

```powershell
py -3.12 -m venv frontend/nicegui_app/.venv
.\frontend\nicegui_app\.venv\Scripts\python.exe -m pip install -r frontend/nicegui_app/requirements.txt
$env:PRODPULSE_FRONTEND_MODE = "mock"
.\frontend\nicegui_app\.venv\Scripts\python.exe -m frontend.nicegui_app
```

Buka [ProdPulse AI](http://127.0.0.1:8502). Atur `PRODPULSE_NICEGUI_PORT` untuk menggunakan port lain.

Untuk memakai backend, jalankan FastAPI dan set `PRODPULSE_FRONTEND_MODE=api` serta `API_BASE_URL=http://localhost:8000` sebelum menjalankan NiceGUI. Mode API adalah default. Saat backend gagal merespons, halaman menampilkan pesan kesalahan.

## Perilaku dan handoff

| Halaman | Perilaku |
| --- | --- |
| Overview `/` | Mode mock menampilkan fixture historis 2025 dan filter 3, 6, atau 12 bulan. Mode API memakai ringkasan, status layanan, metadata model, dan hingga 12 estimasi tersimpan untuk grafik per tanggal. |
| Prediksi baru `/prediction` | Validasi melalui `PredictionRequest`, konversi persen ke rasio, draf per tab, perbandingan dengan target, dan tautan ke asisten. |
| Riwayat prediksi `/history` | Pagination API melalui `limit` dan `offset`. Filter departemen berlaku pada halaman yang sedang dimuat. Parameter `prediction_id` membuka detail tertentu. |
| AI Assistant `/assistant` | Konteks opsional melalui `prediction_id`. ID percakapan disimpan per konteks dalam tab yang sama. Bukti prediksi menaut ke riwayat. |

Label **MOCK DATA** berlaku untuk angka, estimasi, dan jawaban dari fixture. Draf, percakapan, dan prediksi mock disimpan dalam memori sesi dan hilang saat NiceGUI dimulai ulang. Foto garmen di banner adalah ilustrasi generatif. Logo menggunakan aset ProdPulse AI dengan aksen indigo. DM Sans dilayani secara lokal dan lisensinya tersedia di [assets/OFL-DM-Sans.txt](assets/OFL-DM-Sans.txt).

Kontrak analitik historis per tim dan opsi tim menunggu integrasi backend. Lihat [Integration Requirements](../docs/INTEGRATION_REQUIREMENTS.md).
