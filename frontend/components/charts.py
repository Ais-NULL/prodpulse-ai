"""Productivity comparison from a validated prediction response."""

import plotly.graph_objects as go
import streamlit as st

from shared.contracts import PredictionResponse

NAVY = "#282735"
CORAL = "#F9876F"
GREEN = "#9BE198"
CHART_FONT = "Barlow Condensed, Oswald, Bahnschrift Condensed, Arial Narrow, Liberation Sans Narrow, sans-serif"


def show_comparison(result: PredictionResponse) -> None:
    values = [result.predicted_productivity, result.target_productivity]
    figure = go.Figure(
        go.Bar(
            x=values,
            y=["Estimasi", "Target"],
            orientation="h",
            marker_color=[NAVY, CORAL],
            width=0.40,
            hovertemplate="%{y}: %{x:.1%}<extra></extra>",
        )
    )
    figure.update_layout(
        height=184,
        margin={"l": 8, "r": 16, "t": 4, "b": 36},
        showlegend=False,
        xaxis={"tickformat": ".0%", "range": [0, max(1.0, *values) * 1.05], "fixedrange": True},
        yaxis={"autorange": "reversed", "automargin": True, "fixedrange": True},
        bargap=0.55,
        font={"family": CHART_FONT, "size": 13, "color": NAVY},
    )
    st.plotly_chart(figure, width="stretch", config={"displayModeBar": False})


def show_trend_chart(
    points: list[tuple[str, float]], *, source: str, unavailable: bool = False,
) -> None:
    if not points:
        message = "Data grafik belum dapat dimuat." if unavailable else "Belum ada prediksi tersimpan untuk membuat tren estimasi."
        st.html(f'<div class="pp-chart-empty">{message}</div>')
        return
    labels, values = zip(*points)
    figure = go.Figure(go.Scatter(
        x=labels, y=values, mode="lines+markers",
        line={"color": NAVY, "width": 2.7},
        marker={"color": CORAL, "size": 8},
        hovertemplate=f"%{{x}} · %{{y:.1%}}<extra>{source}</extra>",
    ))
    _overview_style(figure, height=168, background="#FFFFFF", category_stride=max(1, len(points) // 4))
    figure.update_yaxes(range=[min(.3, min(values) * .92), max(1.0, max(values) * 1.06)])
    st.plotly_chart(figure, theme=None, width="stretch", config={"displayModeBar": False})


def show_team_chart(
    points: list[tuple[str, float]], *, source: str, unavailable: bool = False,
) -> None:
    if not points:
        message = "Data grafik belum dapat dimuat." if unavailable else "Belum ada prediksi tersimpan untuk membuat rekap tim."
        st.html(f'<div class="pp-chart-empty pp-chart-empty--team">{message}</div>')
        return
    labels, values = zip(*points)
    figure = go.Figure(go.Bar(
        x=labels, y=values, marker_color=NAVY, width=.12,
        hovertemplate=f"%{{x}} · %{{y:.1%}}<extra>{source}</extra>",
    ))
    _overview_style(figure, height=234, background=GREEN)
    figure.update_xaxes(ticktext=[label.removeprefix("Tim ") for label in labels])
    figure.update_yaxes(
        range=[0, max(1.04, max(values) * 1.05)],
        tickmode="array", tickvals=[0, .25, .5, .75, 1],
    )
    st.plotly_chart(figure, theme=None, width="stretch", config={"displayModeBar": False})


def _overview_style(figure, *, height: int, background: str, category_stride: int = 1) -> None:
    labels = list(figure.data[0].x)
    figure.update_layout(
        height=height,
        paper_bgcolor=background,
        plot_bgcolor=background,
        margin={"l": 44, "r": 18, "t": 5, "b": 28},
        font={"family": CHART_FONT, "size": 13, "color": NAVY},
        showlegend=False,
    )
    figure.update_xaxes(
        showgrid=False, zeroline=False, fixedrange=True, type="category",
        tickmode="array", tickvals=labels[::category_stride],
    )
    figure.update_yaxes(showgrid=False, zeroline=False, nticks=5, tickformat=".0%", fixedrange=True)
