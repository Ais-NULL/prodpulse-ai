# Dataset — ProdPulse AI

## Sumber & Lisensi
- **Nama Dataset:** Productivity Prediction of Garment Employees (UCI #597)
- **Tautan:** https://archive.ics.uci.edu/dataset/597/productivity+prediction+of+garment+employees
- **DOI:** https://doi.org/10.24432/C51S6D
- **Lisensi:** Creative Commons Attribution 4.0 International (CC BY 4.0)

## Aturan Penggunaan di Proyek
- File CSV mentah (`garments_worker_productivity.csv`) disimpan secara lokal di folder `data/` dan tidak di-commit ke repository (diabaikan melalui `.gitignore`).
- Seluruh proses pembersihan dan pemetaan nama kolom wajib menggunakan fungsi tunggal di `shared/normalization.py`.
- Hanya 6 fitur pre-shift yang digunakan untuk model MVP (`department`, `team_id`, `target_productivity`, `smv_minutes`, `worker_count`, dan `day_of_week`).