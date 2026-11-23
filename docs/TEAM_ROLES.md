# ProdPulse AI — Pembagian Tugas Kelompok 4 (Revisi 2026-11-23)

| Anggota | Role | Folder utama | Deliverable |
|---|---|---|---|
| Altaf | Frontend Developer & UI/UX | `frontend/` | Streamlit dashboard, form, history, chat UI, API client, smoke test |
| Barra | ML Engineer & Dataset | `ml/`, `data/` | EDA, model training/evaluation, artefak model, inference |
| Rendi | Backend & MongoDB Engineer | `backend/` | FastAPI, MongoDB, analytics, prediction services, API test |
| Faiz | System Integrator, Contract Owner & QA | `shared/`, `tests/`, konfigurasi proyek | Pydantic schema v1, kontrak JSON/API, integrasi, contract/E2E tests, QA report |
| Ardika | AI Chatbot Engineer | `assistant/` | LLM assistant berbasis data read-only, response grounding, assistant tests |

## Aturan kerja

1. Nama field, endpoint, tipe dan satuan disepakati di `shared/contracts.py`/README; jangan buat sinonim pada modul lain.
2. Faiz menjaga kontrak dan review PR terkait API/schema; Rendi bertanggung jawab implementasi endpoint.
3. Altaf mengonsumsi FastAPI melalui `frontend/api_client.py`, tidak langsung mengakses DB, model ML atau LLM.
4. Barra mengekspor `predict_productivity(request: PredictionRequest) -> float`; Rendi yang memanggilnya.
5. Ardika memakai layanan read-only yang disediakan Rendi; jangan membuat angka prediksi sendiri.
6. Tiap owner menulis unit test sendiri; Faiz menjalankan contract/integration/E2E QA dan mengembalikan bug ke owner terkait.
7. Seluruh anggota berkontribusi pada jurnal, laporan eksperimen, dan demo.

## Branch Git

- `feature/altaf-frontend`
- `feature/barra-ml`
- `feature/rendi-api`
- `feature/faiz-integration-qa`
- `feature/ardika-chatbot`
