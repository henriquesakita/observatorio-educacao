"""Elementos visuais compartilhados pelas duas bases do painel."""

from __future__ import annotations

import html

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

CUSTOM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] { font-family: 'Inter', sans-serif; }

.block-container { padding-top: 1.6rem; padding-bottom: 2rem; max-width: 1250px; }

.hero {
    background: linear-gradient(120deg, #0f3d3e 0%, #0f766e 55%, #0d9488 100%);
    border-radius: 18px;
    padding: 2rem 2.2rem 1.8rem 2.2rem;
    color: #ffffff;
    margin-bottom: 1.2rem;
    box-shadow: 0 12px 30px rgba(15, 61, 62, 0.18);
}
.hero.idesp {
    background: linear-gradient(120deg, #172554 0%, #1d4ed8 60%, #2563eb 100%);
    box-shadow: 0 12px 30px rgba(23, 37, 84, 0.22);
}
.hero .kicker {
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    opacity: 0.78;
    font-weight: 600;
}
.hero h1 { font-size: 2.35rem; margin: 0.35rem 0 0.45rem 0; font-weight: 800; letter-spacing: -0.02em; }
.hero p { font-size: 1.02rem; margin: 0; max-width: 820px; opacity: 0.92; line-height: 1.5; }
.hero .source { font-size: 0.78rem; margin-top: 0.9rem; opacity: 0.65; }

.insight {
    background: #f0fdfa;
    border-left: 4px solid #0d9488;
    border-radius: 10px;
    padding: 0.95rem 1.1rem;
    font-size: 0.95rem;
    line-height: 1.55;
    color: #134e4a;
    margin: 0.4rem 0 1.2rem 0;
}
.insight.idesp { background: #eff6ff; border-left-color: #2563eb; color: #1e3a8a; }
.insight strong { color: inherit; }

div[data-testid="stMetric"] {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 14px;
    padding: 0.9rem 1rem;
    box-shadow: 0 2px 10px rgba(15, 23, 42, 0.04);
}
div[data-testid="stMetricLabel"] p { font-size: 0.8rem; color: #64748b; font-weight: 500; }
div[data-testid="stMetricValue"] { color: #0f3d3e; font-weight: 700; }

.section-title { font-size: 1.15rem; font-weight: 700; color: #0f172a; margin: 0.4rem 0 0.2rem 0; }
.section-sub { font-size: 0.86rem; color: #64748b; margin-bottom: 0.6rem; }

.footer { font-size: 0.78rem; color: #94a3b8; text-align: center; margin-top: 2rem; }
.footer a { color: #0d9488; text-decoration: none; }

div[data-testid="stTabs"] button { font-weight: 600; }

[data-testid="stToolbar"] { visibility: hidden; }
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""


def fmt(value: float | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{decimals}f}".replace(".", ",")


def fmt_int(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float | None, decimals: int = 0) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.{decimals}f}%".replace(".", ",")


def style_fig(fig: go.Figure, height: int = 390, showlegend: bool = True) -> go.Figure:
    fig.update_layout(
        template="plotly_white",
        height=height,
        margin=dict(l=8, r=8, t=48, b=8),
        font=dict(family="Inter, sans-serif", size=12, color="#334155"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, title=None),
        showlegend=showlegend,
        hoverlabel=dict(bgcolor="white", font_size=12),
    )
    fig.update_xaxes(showgrid=False, linecolor="#e2e8f0")
    fig.update_yaxes(gridcolor="#f1f5f9", zeroline=False)
    return fig


def section(title: str, subtitle: str | None = None) -> None:
    st.markdown(f'<div class="section-title">{html.escape(title)}</div>', unsafe_allow_html=True)
    if subtitle:
        st.markdown(f'<div class="section-sub">{subtitle}</div>', unsafe_allow_html=True)


def insight(markup: str) -> None:
    st.markdown(f'<div class="insight">{markup}</div>', unsafe_allow_html=True)


def insight_idesp(markup: str) -> None:
    st.markdown(f'<div class="insight idesp">{markup}</div>', unsafe_allow_html=True)


def render_hero(
    kicker: str,
    title: str,
    description: str,
    source: str,
    variant: str = "",
) -> None:
    st.markdown(
        f"""
        <div class="hero {variant}">
            <div class="kicker">{kicker}</div>
            <h1>{title}</h1>
            <p>{description}</p>
            <div class="source">{source}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_footer(source_name: str, source_url: str) -> None:
    st.markdown(
        f'<div class="footer">Dados: <a href="{source_url}" target="_blank">{source_name}</a> · '
        'Análise e visualização: <a href="https://www.linkedin.com/in/henrique-sakita/" '
        'target="_blank">Henrique Sakita</a> · Código aberto sob licença MIT</div>',
        unsafe_allow_html=True,
    )
