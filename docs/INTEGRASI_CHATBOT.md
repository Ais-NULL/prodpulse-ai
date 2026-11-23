# Menjalankan prediksi dan chat ProdPulse

Paket ini dipasang di root repo kelompok pada main 51f9df8 atau branch Ardika yang sudah mengambil commit tersebut. Isi ZIP menambahkan route serta service backend, menghubungkan assistant ke hasil MongoDB, dan menyertakan pengujian. Jika file backend atau assistant punya edit lokal, bandingkan dulu di PyCharm. Simpan .env yang berisi konfigurasi milikmu.

## Konfigurasi lokal

Dari terminal PowerShell di root, dengan venv aktif, pasang:
```powershell
python -m pip install -r requirements.txt -c docs/constraints-model.txt
```

Versi numerik mengikuti metadata training. Pengujian integrasi menggunakan Python 3.12. Kalau pip di interpreter lain gagal menyediakan wheel, buat environment terpisah menggunakan py -3.12 -m venv .venv312 lalu pilih .venv312 sebagai interpreter.

Isi .env lokal dengan LLM_PROVIDER=gemini, LLM_MODEL dan LLM_API_KEY yang sudah berhasil dipakai. Pakai PRODPULSE_FRONTEND_MODE=api, API_BASE_URL=http://127.0.0.1:8000, MONGODB_URI=mongodb://localhost:27017 dan MONGODB_DB_NAME=prodpulse_ai. Jika kelompok menggunakan Atlas, gunakan URI kelompok yang memiliki izin baca dan tulis. Untuk MongoDB lokal, nyalakan service MongoDB di Windows Services. Jalankan backend dari root agar path model sesuai.

## Menjalankan

Terminal pertama:
```powershell
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```

Terminal kedua, dari root dan venv yang sama:
```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
python -m streamlit run frontend/app.py
```

Health menampilkan db_status dan model_status. Saat keduanya ok, buka localhost:8501, pilih New Prediction. Coba tanggal 1 Desember 2026, sewing, tim 3, target 80, SMV 26.16 dan jumlah pekerja 59. Klik Buat estimasi. Hasil sekitar 83,46%. Simpan ID yang tampil. Klik Bahas prediksi dengan AI Assistant, lalu ketik “Tim ini mencapai target?”. Periksa ID sumber dan angka. Setelah refresh, buka Prediction History dan lihat prediksi yang sama. Label di dashboard bisa dibulatkan ke satu desimal.

Endpoint prediksi menyimpan snapshot input dan hasil inference. Chat membaca prediction_id dari MongoDB, mengirim pertanyaan ke Gemini untuk klasifikasi maksud, lalu memformat fakta terverifikasi dan menyimpan giliran percakapan. Bila DB atau inferensi gagal, backend memberikan error. Bila key/model Gemini bermasalah, chat mengembalikan status unavailable. Penyimpanan percakapan mengarsipkan giliran; model mengklasifikasikan pesan per giliran.

CSV hanya diperlukan bila menginginkan rata-rata historis UCI. Untuk itu taruh CSV di data/garments_worker_productivity.csv dan jalankan python -m scripts.import_uci. Fitur prediksi baru dapat langsung memakai model.joblib tanpa impor CSV.

## Pengujian

```powershell
python -m pip install mongomock
python -m pytest -q tests/test_chat_integrated.py
```

Tes mengoperasikan form Streamlit, backend HTTP sungguhan dan model asli. Database in-memory dan respons jaringan Gemini disimulasikan pada tes ini. Pada aplikasi biasa, mode api menggunakan MongoDB dan Gemini sesuai .env.
