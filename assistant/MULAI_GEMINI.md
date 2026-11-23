# ProdPulse AI · Gemini
Ekstrak isi ZIP ke root checkout prodpulse-ai pada branch feature/ardika-chatbot. Folder assistant/, shared/, examples/ dan tests/ akan sejajar. Paket memakai kontrak dan fixture dari checkout tim.

Di terminal PowerShell root proyek gunakan Python 3.12 atau ganti dengan 3.11 jika tersedia.
```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-contract.txt "python-dotenv>=1,<2"
if (!(Test-Path .env)) { Copy-Item .env.example .env }
```

Isi LLM_PROVIDER=gemini, LLM_MODEL=gemini-3.1-flash-lite, dan LLM_API_KEY di .env lokal. Buat key lewat https://aistudio.google.com/apikey. Jika model belum tersedia di akun, masukkan ID model teks yang mendukung generateContent dan JSON terstruktur.

```powershell
.\.venv\Scripts\python.exe -m pytest -q tests/test_contracts.py tests/test_assistant.py
.\.venv\Scripts\python.exe -m assistant.demo
```

Ketik “Tim ini diperkirakan mencapai target nggak?” dan periksa angka 74%, target 80%, gap 6 poin persentase dan evidence ID. Gemini mengklasifikasikan pertanyaan. Service menyusun jawaban numerik menggunakan field fixture. Riwayat tim dan registri model belum dihubungkan. Untuk mengetes ID yang hilang, jalankan python -m assistant.demo --id missing. Untuk keluar ketik /exit.

Untuk Rendi, panggil assistant.service.chat(request, get_prediction_by_id=reader) dari route sinkron. request adalah ChatRequest. reader mengembalikan PredictionResponse, mapping v1, atau None. Hasilnya ChatResponse. Aplikasi backend perlu memuat .env saat startup. Hanya pertanyaan dan petunjuk klasifikasi dikirim ke Gemini.
