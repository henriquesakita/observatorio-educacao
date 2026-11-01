"""Dashboard do Observatorio da Educacao (Streamlit)."""

from __future__ import annotations

import html
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from observatorio.config import (
    DEFAULT_YEAR,
    END_YEAR,
    PROCESSED_FILE,
    REFERENCE_IDEB,
    REGION_COLORS,
    REGIONS,
    SOURCE_NAME,
    SOURCE_URL,
    STAGES,
    START_YEAR,
    UF_NAMES,
    YEARS,
)
from observatorio.metrics import (
    biggest_gains,
    evolution_by_region,
    evolution_national,
    municipality_history,
    ranking,
    scope,
    summary,
)

st.set_page_config(
    page_title="Observatório da Educação",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

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
.hero .kicker {
    font-size: 0.72rem;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    opacity: 0.78;
    font-weight: 600;
}
.hero h1 { font-size: 2.35rem; margin: 0.35rem 0 0.45rem 0; font-weight: 800; letter-spacing: -0.02em; }
.hero p { font-size: 1.02rem; margin: 0; max-width: 780px; opacity: 0.92; line-height: 1.5; }
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
.insight strong { color: #0f3d3e; }

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


# ---------------------------------------------------------------------------
# Carregamento e formatacao
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Carregando dados do Ideb...")
def load_data(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path, dtype={"cod_municipio": str})
    data["cod_municipio"] = data["cod_municipio"].str.zfill(7)
    return data


def fmt(value: float | None, decimals: int = 2) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value:.{decimals}f}".replace(".", ",")


def fmt_int(value: float | int | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{int(value):,}".replace(",", ".")


def fmt_pct(value: float | None) -> str:
    if value is None or pd.isna(value):
        return "—"
    return f"{value * 100:.0f}%".replace(".", ",")


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


# ---------------------------------------------------------------------------
# Blocos da interface
# ---------------------------------------------------------------------------


def render_hero() -> None:
    st.markdown(
        """
        <div class="hero">
            <div class="kicker">Dados públicos · Educação básica</div>
            <h1>Observatório da Educação</h1>
            <p>Como a aprendizagem e a aprovação evoluíram nos 5.570 municípios brasileiros?
            Um recorte do Ideb de 2005 a 2025, por etapa, rede e território.</p>
            <div class="source">Fonte: INEP/Saeb — planilhas de divulgação do Ideb municipal (edição 2025)</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_sidebar(data: pd.DataFrame) -> dict:
    st.sidebar.markdown("### Filtros")
    etapa = st.sidebar.radio("Etapa", list(STAGES), index=0)

    disponiveis = [n for n in ["Pública", "Estadual", "Municipal", "Federal"] if n in set(data["rede"])]
    rede = st.sidebar.selectbox("Rede de ensino", disponiveis, index=0)

    ano = st.sidebar.select_slider(
        "Ano",
        options=YEARS,
        value=DEFAULT_YEAR,
        format_func=lambda y: str(y),
    )

    uf_options = ["Todos"] + sorted(data["uf"].dropna().unique())
    uf_label = st.sidebar.selectbox(
        "Unidade da federação",
        uf_options,
        index=0,
        format_func=lambda uf: "Brasil (todos)" if uf == "Todos" else f"{uf} — {UF_NAMES.get(uf, uf)}",
    )
    uf = None if uf_label == "Todos" else uf_label

    st.sidebar.divider()
    st.sidebar.caption(
        "Médias simples entre municípios com resultado divulgado. "
        "Não substituem o Ideb oficial, que é ponderado por alunos."
    )
    st.sidebar.markdown(f"[Fonte oficial]({SOURCE_URL})")

    return {"etapa": etapa, "rede": rede, "ano": ano, "uf": uf}


def render_kpis(historico: pd.DataFrame, atual: pd.DataFrame, ano: int, uf: str | None) -> None:
    info = summary(atual)
    base = historico[historico["ano"] == START_YEAR]
    base_mean = base["ideb"].mean() if not base.empty else None
    variacao = None if info["media"] is None or base_mean is None else info["media"] - base_mean

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Municípios com resultado", fmt_int(info["n_municipios"]), help="Municípios com Ideb divulgado no recorte.")
    c2.metric(
        f"Ideb médio em {ano}",
        fmt(info["media"]),
        delta=None if variacao is None else f"{variacao:+.2f} vs {START_YEAR}".replace(".", ","),
        help="Média simples do Ideb entre os municípios do recorte.",
    )
    c3.metric(
        "Abaixo de 6,0",
        fmt_pct(info["abaixo_referencia"]),
        help="Percentual de municípios com Ideb abaixo de 6,0 (referência de leitura, não meta oficial).",
    )
    c4.metric(
        "Maior Ideb do recorte",
        fmt(info["melhor_ideb"]),
        delta=info["melhor_municipio"] or None,
        delta_color="off",
        help="Município com maior Ideb no ano selecionado.",
    )

    if info["media"] is None:
        st.warning("Não há resultados divulgados para esta combinação de filtros.")
        return

    territorio = "no Brasil" if uf is None else f"em {UF_NAMES.get(uf, uf)}"
    comparacao = (
        ""
        if base_mean is None
        else " Isso representa <strong>"
        + f"{variacao:+.2f}".replace(".", ",")
        + f"</strong> em relação a {START_YEAR}."
    )
    st.markdown(
        f"""
        <div class="insight">
            Em <strong>{ano}</strong>, a média simples do Ideb {territorio} foi
            <strong>{fmt(info['media'])}</strong>, considerando <strong>{fmt_int(info['n_municipios'])}
            municípios</strong> com resultado.{comparacao}
            <strong>{fmt_pct(info['abaixo_referencia'])}</strong> dos municípios ficaram abaixo de 6,0.
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_panorama(data: pd.DataFrame, filters: dict) -> None:
    etapa, rede, ano, uf = filters["etapa"], filters["rede"], filters["ano"], filters["uf"]
    historico = scope(data, etapa, rede, uf=uf)

    col_a, col_b = st.columns([1.35, 1])

    with col_a:
        st.markdown('<div class="section-title">Evolução por região</div>', unsafe_allow_html=True)
        st.markdown(
            '<div class="section-sub">Média simples do Ideb dos municípios com resultado em cada edição.</div>',
            unsafe_allow_html=True,
        )
        if uf is None:
            serie = evolution_by_region(historico)
            fig = px.line(
                serie,
                x="ano",
                y="media",
                color="regiao",
                markers=True,
                color_discrete_map=REGION_COLORS,
                labels={"ano": "Edição do Ideb", "media": "Ideb médio", "regiao": "Região"},
            )
        else:
            nacional = evolution_national(historico)
            fig = px.line(
                nacional,
                x="ano",
                y="media",
                markers=True,
                labels={"ano": "Edição do Ideb", "media": "Ideb médio"},
            )
            fig.update_traces(line_color="#0d9488", line_width=3)
            fig.update_layout(title=f"Média dos municípios de {uf}")
        fig.update_traces(marker=dict(size=7))
        style_fig(fig, height=400)
        fig.update_yaxes(range=[3.5, 7.5])
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_b:
        st.markdown('<div class="section-title">Distribuição por região</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-sub">Cada ponto é um município com Ideb em {ano}.</div>',
            unsafe_allow_html=True,
        )
        atual = scope(data, etapa, rede, ano=ano, uf=uf)
        atual = atual.dropna(subset=["ideb"])
        if atual.empty:
            st.info("Sem dados para o ano selecionado.")
        elif uf is None:
            fig = px.box(
                atual,
                x="regiao",
                y="ideb",
                color="regiao",
                points="all",
                color_discrete_map=REGION_COLORS,
                labels={"regiao": "", "ideb": "Ideb"},
                category_orders={"regiao": REGIONS},
            )
            fig.update_traces(marker=dict(size=4, opacity=0.45), line_width=1.5)
            fig.add_hline(
                y=REFERENCE_IDEB,
                line_dash="dot",
                line_color="#94a3b8",
                annotation_text="6,0",
                annotation_position="top left",
            )
            style_fig(fig, height=400, showlegend=False)
            fig.update_xaxes(tickangle=-20)
        else:
            fig = px.histogram(
                atual,
                x="ideb",
                nbins=22,
                labels={"ideb": "Ideb", "count": "Municípios"},
                color_discrete_sequence=["#0d9488"],
            )
            fig.add_vline(
                x=REFERENCE_IDEB,
                line_dash="dot",
                line_color="#94a3b8",
                annotation_text="6,0",
                annotation_position="top",
            )
            style_fig(fig, height=400, showlegend=False)
            fig.update_yaxes(title="Municípios")
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.divider()
    if uf is None:
        st.markdown('<div class="section-title">Ranking das unidades da federação</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="section-sub">Média simples do Ideb dos municípios de cada UF em {ano}.</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown(
            f'<div class="section-title">Municípios de {UF_NAMES.get(uf, uf)}</div>',
            unsafe_allow_html=True,
        )
        st.markdown(
            f'<div class="section-sub">Quinze maiores Idebs do estado em {ano}.</div>',
            unsafe_allow_html=True,
        )

    atual = scope(data, etapa, rede, ano=ano, uf=uf).dropna(subset=["ideb"])
    if atual.empty:
        st.info("Sem dados para montar o ranking.")
        return

    if uf is None:
        tabela = (
            atual.groupby("uf", as_index=False)
            .agg(ideb=("ideb", "mean"), municipios=("cod_municipio", "nunique"))
            .sort_values("ideb", ascending=True)
            .tail(15)
        )
        tabela["rotulo"] = tabela["uf"] + " · " + tabela["uf"].map(UF_NAMES)
        rotulo_legenda = "Ideb médio"
        limite_x = max(tabela["ideb"].max() + 0.9, 7.5)
    else:
        tabela = atual.nlargest(15, "ideb").sort_values("ideb", ascending=True)
        tabela["rotulo"] = tabela["municipio"]
        rotulo_legenda = "Ideb"
        limite_x = min(tabela["ideb"].max() + 0.8, 10.8)

    fig = px.bar(
        tabela,
        x="ideb",
        y="rotulo",
        orientation="h",
        text=tabela["ideb"].map(lambda v: fmt(v)),
        labels={"ideb": rotulo_legenda, "rotulo": ""},
        color="ideb",
        color_continuous_scale=["#ccfbf1", "#0d9488"],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(coloraxis_showscale=False)
    fig.add_vline(x=REFERENCE_IDEB, line_dash="dot", line_color="#94a3b8")
    style_fig(fig, height=430, showlegend=False)
    fig.update_xaxes(range=[0, limite_x])
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})


def render_ranking(data: pd.DataFrame, filters: dict) -> None:
    etapa, rede, ano, uf = filters["etapa"], filters["rede"], filters["ano"], filters["uf"]
    atual = scope(data, etapa, rede, ano=ano, uf=uf).dropna(subset=["ideb"])

    tipo = st.radio(
        "O que mostrar",
        ["Melhores Idebs", "Menores Idebs", "Maiores avanços desde 2005"],
        horizontal=True,
        label_visibility="collapsed",
    )

    if tipo == "Maiores avanços desde 2005":
        tabela = biggest_gains(scope(data, etapa, rede, uf=uf), START_YEAR, ano, n=15)
        if tabela.empty:
            st.info("Não há municípios com resultado nos dois anos comparados.")
            return
        exibir = tabela.rename(
            columns={"municipio": "Município", "uf": "UF", "inicio": str(START_YEAR), "fim": str(ano), "ganho": "Ganho"}
        )
        fig = px.bar(
            tabela.sort_values("ganho"),
            x="ganho",
            y="municipio",
            orientation="h",
            text=tabela.sort_values("ganho")["ganho"].map(lambda v: f"{v:+.1f}".replace(".", ",")),
            labels={"ganho": "Variação do Ideb", "municipio": ""},
            color="ganho",
            color_continuous_scale=["#ccfbf1", "#0f766e"],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(coloraxis_showscale=False)
        eixo_x = [min(-0.5, float(tabela["ganho"].min()) - 0.3), float(tabela["ganho"].max()) + 0.8]
        st.markdown(
            f'<div class="section-sub">Municípios com maior variação entre {START_YEAR} e {ano} '
            "(apenas quem tem resultado nos dois anos).</div>",
            unsafe_allow_html=True,
        )
    else:
        melhores = tipo == "Melhores Idebs"
        tabela = ranking(atual, n=15, best=melhores, uf=None)
        exibir = tabela.rename(columns={"municipio": "Município", "uf": "UF", "regiao": "Região", "ideb": "Ideb", "ano": "Ano"})
        ordem = tabela.sort_values("ideb")
        fig = px.bar(
            ordem,
            x="ideb",
            y="municipio",
            orientation="h",
            text=ordem["ideb"].map(lambda v: fmt(v)),
            labels={"ideb": "Ideb", "municipio": ""},
            color="ideb",
            color_continuous_scale=["#ccfbf1", "#0f766e"] if melhores else ["#fee2e2", "#b91c1c"],
        )
        fig.update_traces(textposition="outside", cliponaxis=False)
        fig.update_layout(coloraxis_showscale=False)
        eixo_x = [0, 10.8]
        st.markdown(
            f'<div class="section-sub">{tipo} entre os municípios do recorte em {ano}.</div>',
            unsafe_allow_html=True,
        )

    style_fig(fig, height=520, showlegend=False)
    fig.update_xaxes(range=eixo_x)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.dataframe(exibir, width="stretch", hide_index=True)

    csv = atual.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar recorte em CSV",
        data=csv,
        file_name=f"ideb_{etapa.lower().replace(' ', '_')}_{rede.lower()}_{ano}.csv",
        mime="text/csv",
    )


def render_municipio(data: pd.DataFrame, filters: dict) -> None:
    etapa, rede, ano, uf = filters["etapa"], filters["rede"], filters["ano"], filters["uf"]
    base = scope(data, etapa, rede, uf=uf)

    opcoes = (
        base[["cod_municipio", "municipio", "uf"]]
        .drop_duplicates()
        .sort_values(["uf", "municipio"])
        .reset_index(drop=True)
    )
    opcoes["rotulo"] = opcoes["municipio"] + " — " + opcoes["uf"]

    if opcoes.empty:
        st.info("Não há municípios para esta combinação de filtros.")
        return

    padrao = opcoes[opcoes["municipio"].eq("São Paulo") & opcoes["uf"].eq("SP")]
    com_dado = set(base.loc[base["ano"] == ano, "cod_municipio"].dropna())
    if not padrao.empty and padrao["cod_municipio"].iloc[0] in com_dado:
        indice = int(padrao.index[0])
    elif com_dado:
        indice = int(opcoes.index[opcoes["cod_municipio"].isin(com_dado)][0])
    else:
        indice = 0
    rotulo = st.selectbox("Município", opcoes["rotulo"].tolist(), index=indice)
    codigo = opcoes.loc[opcoes["rotulo"] == rotulo, "cod_municipio"].iloc[0]

    serie = municipality_history(scope(data, etapa, rede), codigo)
    if serie.empty:
        st.info("Sem série histórica para este município.")
        return

    nome = serie["municipio"].iloc[0]
    uf_cidade = serie["uf"].iloc[0]
    regiao = serie["regiao"].iloc[0]
    linha = serie[serie["ano"] == ano]
    ideb_ano = linha["ideb"].iloc[0] if not linha.empty else None
    inicio = serie[serie["ano"] == START_YEAR]["ideb"]
    variacao = None if inicio.empty or pd.isna(ideb_ano) else ideb_ano - inicio.iloc[0]

    ranking_uf = (
        scope(data, etapa, rede, ano=ano, uf=uf_cidade)
        .dropna(subset=["ideb"])
        .sort_values("ideb", ascending=False)
        .reset_index(drop=True)
    )
    posicao = ranking_uf.index[ranking_uf["cod_municipio"] == codigo]
    posicao_txt = f"{posicao[0] + 1}º de {len(ranking_uf)}" if len(posicao) else "—"

    c1, c2, c3 = st.columns(3)
    c1.metric(f"Ideb em {ano}", fmt(ideb_ano))
    c2.metric(f"Variação {START_YEAR}–{ano}", "—" if variacao is None else f"{variacao:+.2f}".replace(".", ","))
    c3.metric(f"Posição em {uf_cidade}", posicao_txt)

    st.markdown(
        f'<div class="section-sub" style="margin-top:0.8rem">{html.escape(nome)} ({uf_cidade}) · região {regiao} · '
        f"rede {rede.lower()} · {etapa.lower()}</div>",
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=serie["ano"],
            y=serie["ideb"],
            mode="lines+markers",
            name=nome,
            line=dict(color="#0f766e", width=3.5),
            marker=dict(size=9),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=serie["ano"], y=serie["media_uf"], mode="lines", name=f"Média {uf_cidade}",
            line=dict(color="#f59e0b", width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=serie["ano"], y=serie["media_regiao"], mode="lines", name=f"Média {regiao}",
            line=dict(color="#94a3b8", width=1.8, dash="dot"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=serie["ano"], y=serie["media_brasil"], mode="lines", name="Média Brasil",
            line=dict(color="#cbd5e1", width=1.5, dash="dot"),
        )
    )
    fig.add_hline(y=REFERENCE_IDEB, line_dash="dot", line_color="#e2e8f0")
    style_fig(fig, height=430)
    fig.update_yaxes(range=[2.5, 8.5])
    fig.update_layout(title="Trajetória do município e referências")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.markdown('<div class="section-title">Composição do Ideb</div>', unsafe_allow_html=True)
    st.markdown(
        '<div class="section-sub">O Ideb é o produto entre a nota padronizada do Saeb (N) e o indicador de rendimento (P).</div>',
        unsafe_allow_html=True,
    )
    comp = serie.melt(
        id_vars="ano",
        value_vars=["nota_media", "indicador_rendimento"],
        var_name="indicador",
        value_name="valor",
    ).dropna(subset=["valor"])
    if comp.empty:
        st.info("Componentes não divulgados para este município.")
    else:
        comp["indicador"] = comp["indicador"].map(
            {"nota_media": "Nota média (N)", "indicador_rendimento": "Rendimento (P)"}
        )
        fig2 = px.line(
            comp,
            x="ano",
            y="valor",
            color="indicador",
            markers=True,
            labels={"ano": "Edição", "valor": "", "indicador": ""},
            color_discrete_map={"Nota média (N)": "#0d9488", "Rendimento (P)": "#f59e0b"},
        )
        style_fig(fig2, height=300)
        fig2.update_yaxes(range=[0, 7])
        st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})


def render_metodo(data: pd.DataFrame) -> None:
    st.markdown(
        f"""
        ### De onde vêm os dados

        Os números vêm das planilhas de divulgação do **Ideb municipal**, publicadas pelo
        [Inep]({SOURCE_URL}) com base no **Saeb {DEFAULT_YEAR}** e no **Censo Escolar {DEFAULT_YEAR}**.
        O projeto baixa os arquivos oficiais, limpa as planilhas e mantém um recorte tratado
        no repositório. O download é reprodutível com `python scripts/build_dataset.py`.

        ### Como o Ideb é calculado

        ```
        Ideb = N × P
        ```

        - **N**: nota média padronizada do Saeb em Língua Portuguesa e Matemática.
        - **P**: indicador de rendimento, calculado a partir das taxas de aprovação.

        O indicador varia de 0 a 10. Neste painel, `N` aparece como *nota média* e `P` como
        *rendimento*.

        ### O que este painel mostra — e o que não mostra

        - As médias são **simples entre municípios**: cada município pesa igual. O Ideb oficial
          do Brasil e das UFs é ponderado pelo número de alunos, então os valores daqui **não
          substituem** o indicador oficial.
        - A rede **Pública** agrega as redes estadual, municipal e federal. Para evitar dupla
          contagem, as análises usam uma rede por vez.
        - O Inep não divulga o Ideb quando há **poucos participantes** no Saeb ou quando a
          escola solicita não divulgação. Por isso o número de municípios varia entre anos.
        - O Ideb de **2021** reflete o contexto da pandemia de Covid-19 e deve ser lido com
          cautela.
        - O primeiro ciclo de metas terminou em 2021; as edições seguintes **não têm metas
          oficiais** fixadas.
        - A referência de **6,0** usada no painel é apenas uma linha de leitura, não uma meta
          oficial do Inep.

        ### Pipeline

        `download (INEP) → limpeza (pandas) → dataset tidy → dashboard (Streamlit + Plotly)`

        O repositório inclui testes automatizados para a transformação e para as agregações,
        além de integração contínua no GitHub Actions.
        """
    )

    st.divider()
    st.caption(
        f"Base carregada: {fmt_int(len(data))} linhas · "
        f"{fmt_int(data['cod_municipio'].nunique())} municípios · "
        f"edições de {START_YEAR} a {END_YEAR} · "
        f"última edição disponível: {DEFAULT_YEAR}."
    )


def main() -> None:
    st.markdown(CUSTOM_CSS, unsafe_allow_html=True)
    render_hero()

    if not Path(PROCESSED_FILE).exists():
        st.error(
            "Dataset processado não encontrado. Rode `python scripts/build_dataset.py` "
            "para baixar e tratar as planilhas do Inep."
        )
        st.stop()

    data = load_data(PROCESSED_FILE)
    filters = render_sidebar(data)

    historico = scope(data, filters["etapa"], filters["rede"], uf=filters["uf"])
    atual = scope(data, filters["etapa"], filters["rede"], ano=filters["ano"], uf=filters["uf"])

    render_kpis(historico, atual, filters["ano"], filters["uf"])

    abas = st.tabs(["Panorama", "Ranking", "Município", "Método"])
    with abas[0]:
        render_panorama(data, filters)
    with abas[1]:
        render_ranking(data, filters)
    with abas[2]:
        render_municipio(data, filters)
    with abas[3]:
        render_metodo(data)

    st.markdown(
        f'<div class="footer">Dados: <a href="{SOURCE_URL}" target="_blank">{SOURCE_NAME}</a> · '
        "Análise e visualização: Henrique Sakita · Código aberto sob licença MIT</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
