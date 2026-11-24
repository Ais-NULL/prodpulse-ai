"""Run the four-page NiceGUI frontend."""

import os
from pathlib import Path

from nicegui import app, ui

from frontend.nicegui_app.assistant import assistant_page
from frontend.nicegui_app.history import history_page
from frontend.nicegui_app.overview import overview_page
from frontend.nicegui_app.prediction import prediction_page
from frontend.nicegui_app.shell import ASSISTANT, HISTORY, OVERVIEW, PREDICTION

assets = Path(__file__).resolve().parent / "assets"
for filename in ("garment-floor.webp", "prodpulse-indigo.webp", "dm-sans.ttf", "thread-pattern.webp"):
    app.add_static_file(url_path=f"/ui-assets/{filename}", local_file=assets / filename)

for path, title, render in (
    (OVERVIEW, "Overview", overview_page),
    (PREDICTION, "Prediksi baru", prediction_page),
    (HISTORY, "Riwayat prediksi", history_page),
    (ASSISTANT, "AI Assistant", assistant_page),
):
    ui.page(path, title=f"{title} · ProdPulse AI", language="id")(render)

ui.run(
    title="ProdPulse AI",
    host="127.0.0.1",
    port=int(os.getenv("PRODPULSE_NICEGUI_PORT", os.getenv("PRODPULSE_PREVIEW_PORT", "8502"))),
    show=False,
    reload=False,
)
