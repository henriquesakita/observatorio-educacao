"""Base IDESP — rede estadual de São Paulo.

O IDESP combina o desempenho dos alunos no Saresp com o fluxo escolar. Esta
seção reúne os resultados por escola (2007–2024), as metas oficiais por escola
(2019–2025) e as médias de proficiência do Saresp por município (2011–2025).
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from observatorio.config import (
    IDESP_METAS_FILE,
    IDESP_PROCESSED_FILE,
    PROCESSED_FILE,
    SARESP_PROCESSED_FILE,
)
from observatorio.idesp import (
    STAGES,
    compare_with_ideb,
    evolution_state,
    gains_escolas,
    meta_status,
    municipality_history,
    ranking_escolas,
    ranking_municipios,
    saresp_comparison,
    saresp_evolution,
    saresp_ranking,
    school_history,
    scope,
    summary,
)
from observatorio.ui import (
    fmt,
    fmt_int,
    fmt_pct,
    insight_idesp,
    render_footer,
    render_hero,
    section,
    style_fig,
)

AZUL = "#2563eb"
AZUL_ESCURO = "#1e3a8a"
AMBAR = "#f59e0b"
CINZA = "#94a3b8"

FONTE = "Seduc-SP — IDESP por escola e Saresp"
FONTE_URL = "https://dados.educacao.sp.gov.br/search/type/dataset"
SARESP_URL = "https://saresp.fde.sp.gov.br/ConsultaRede.aspx?opc=1&tipo=Rede%20Estadual"

# A publicacao do Saresp de 2014 cobre apenas 183 municipios e distorce a serie.
SARESP_ANOS_PARCIAIS = {2014}


# ---------------------------------------------------------------------------
# Carregamento
# ---------------------------------------------------------------------------


@st.cache_data(show_spinner="Carregando dados do IDESP...")
def load_idesp(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path, dtype={"cod_municipio": str, "cod_inep": str})
    data["cod_municipio"] = data["cod_municipio"].str.zfill(7)
    return data


@st.cache_data(show_spinner="Carregando metas do IDESP...")
def load_metas(path: str | Path) -> pd.DataFrame:
    return pd.read_csv(path, dtype={"cod_inep": str})


@st.cache_data(show_spinner="Carregando dados do Saresp...")
def load_saresp(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path, dtype={"cod_municipio": str})
    data["cod_municipio"] = data["cod_municipio"].str.zfill(7)
    return data


@st.cache_data(show_spinner="Carregando Ideb para comparação...")
def load_ideb(path: str | Path) -> pd.DataFrame:
    data = pd.read_csv(path, dtype={"cod_municipio": str})
    data["cod_municipio"] = data["cod_municipio"].str.zfill(7)
    return data


# ---------------------------------------------------------------------------
# Filtros
# ---------------------------------------------------------------------------


def render_sidebar(idesp: pd.DataFrame) -> dict:
    st.sidebar.markdown("### Filtros")
    etapa = st.sidebar.radio("Etapa", list(STAGES), index=0)
    anos = sorted(int(a) for a in idesp.loc[idesp["etapa"] == etapa, "ano"].unique())

    ano = st.sidebar.select_slider(
        "Ano",
        options=anos,
        value=anos[-1],
        format_func=lambda y: str(y),
    )
    if etapa == "Ensino Médio":
        st.sidebar.caption(
            "O IDESP do ensino médio é publicado até 2022. As edições de 2023 e 2024 "
            "trazem apenas anos iniciais e finais."
        )

    diretorias = sorted(idesp["diretoria"].dropna().unique())
    escolha = st.sidebar.selectbox("Diretoria de ensino", ["Todas"] + diretorias)
    diretoria = None if escolha == "Todas" else escolha

    st.sidebar.divider()
    st.sidebar.caption(
        "Médias simples entre escolas da rede estadual. Não substituem o IDESP "
        "oficial do Estado, que é ponderado pelo número de alunos."
    )
    st.sidebar.markdown(f"[Portal de dados da Seduc-SP]({FONTE_URL})")

    return {
        "etapa": etapa,
        "ano": ano,
        "anos": anos,
        "inicio": anos[0],
        "diretoria": diretoria,
    }


# ---------------------------------------------------------------------------
# Indicadores
# ---------------------------------------------------------------------------


def render_kpis(idesp: pd.DataFrame, metas: pd.DataFrame, filtros: dict) -> None:
    etapa, ano, diretoria = filtros["etapa"], filtros["ano"], filtros["diretoria"]
    frame = scope(idesp, etapa, diretoria=diretoria)
    atual = frame[frame["ano"] == ano]
    info = summary(atual)

    inicio = filtros["inicio"]
    base = frame.loc[frame["ano"] == inicio, "idesp"].mean()
    variacao = None if info["media"] is None else info["media"] - base

    status = meta_status(idesp, metas, ano, etapa)
    if diretoria is not None:
        status = status[status["diretoria"] == diretoria]

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(
        "Escolas com resultado",
        fmt_int(info["n_escolas"]),
        help=f"Escolas da rede estadual com IDESP divulgado em {ano}.",
    )
    c2.metric(
        f"IDESP médio em {ano}",
        fmt(info["media"]),
        delta=None if variacao is None else f"{variacao:+.2f} vs {inicio}".replace(".", ","),
        help="Média simples do IDESP entre as escolas do recorte.",
    )
    if status.empty:
        c3.metric(
            "IDESP mediano",
            fmt(info["mediana"]),
            help="Metade das escolas fica abaixo deste valor. Metas oficiais só existem a partir de 2019.",
        )
    else:
        c3.metric(
            "Escolas que atingiram a meta",
            fmt_pct(status["atingiu"].mean()),
            help=f"Percentual de escolas com resultado igual ou superior à meta oficial de {ano} (tolerância de 0,05).",
        )
    c4.metric(
        "Maior IDESP do recorte",
        fmt(info["melhor_idesp"]),
        delta=info["melhor_escola"] or None,
        delta_color="off",
        help="Escola com maior IDESP no ano selecionado.",
    )

    if info["media"] is None:
        st.warning("Não há resultados divulgados para esta combinação de filtros.")
        return

    recorte = "da rede estadual" if diretoria is None else f"da diretoria de {diretoria.title()}"
    comparacao = (
        ""
        if variacao is None
        else f" Isso representa <strong>{variacao:+.2f}</strong> em relação a {inicio}."
    ).replace(".", ",")
    meta_texto = (
        ""
        if status.empty
        else f" <strong>{fmt_pct(status['atingiu'].mean())}</strong> das escolas atingiram a meta oficial do ano."
    )
    insight_idesp(
        f"Em <strong>{ano}</strong>, as <strong>{fmt_int(info['n_escolas'])} escolas</strong> "
        f"{recorte} na etapa de {etapa.lower()} tiveram IDESP médio de "
        f"<strong>{fmt(info['media'])}</strong>.{comparacao}{meta_texto} "
        f"A maior nota foi <strong>{fmt(info['melhor_idesp'])}</strong>, "
        f"em {info['melhor_escola']}."
    )


# ---------------------------------------------------------------------------
# Abas
# ---------------------------------------------------------------------------


def render_panorama(idesp: pd.DataFrame, filtros: dict) -> None:
    etapa, ano = filtros["etapa"], filtros["ano"]
    atual = scope(idesp, etapa, ano=ano).dropna(subset=["idesp"])

    col_a, col_b = st.columns([1.3, 1])
    with col_a:
        section(
            "Evolução do IDESP por etapa",
            "Média simples entre escolas da rede estadual em cada edição.",
        )
        evolucao = evolution_state(idesp)
        fig = px.line(
            evolucao,
            x="ano",
            y="media",
            color="etapa",
            markers=True,
            labels={"ano": "Edição", "media": "IDESP médio", "etapa": "Etapa"},
            color_discrete_map={
                "Anos Iniciais": AZUL,
                "Anos Finais": AMBAR,
                "Ensino Médio": AZUL_ESCURO,
            },
        )
        fig.update_traces(marker=dict(size=6), line=dict(width=2.5))
        style_fig(fig, height=400)
        fig.update_yaxes(range=[0, max(6.0, float(evolucao["media"].max()) + 0.6)])
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_b:
        section(
            "Distribuição das escolas",
            f"Cada escola de {etapa.lower()} com resultado em {ano}.",
        )
        if atual.empty:
            st.info("Sem dados para o ano selecionado.")
        else:
            fig = px.histogram(
                atual,
                x="idesp",
                nbins=24,
                labels={"idesp": "IDESP", "count": "Escolas"},
                color_discrete_sequence=[AZUL],
            )
            media, mediana = atual["idesp"].mean(), atual["idesp"].median()
            fig.add_vline(
                x=media,
                line_dash="dash",
                line_color=AMBAR,
                annotation_text=f"média {fmt(media)}",
                annotation_position="top",
            )
            fig.add_vline(
                x=mediana,
                line_dash="dot",
                line_color=CINZA,
                annotation_text=f"mediana {fmt(mediana)}",
                annotation_position="bottom",
            )
            style_fig(fig, height=400, showlegend=False)
            fig.update_yaxes(title="Escolas")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.divider()
    section(
        "Diretorias de ensino",
        f"IDESP médio das escolas de {etapa.lower()} em {ano}, por diretoria.",
    )
    escolha = st.radio(
        "Ordenação",
        ["Melhores diretorias", "Diretorias com menor IDESP"],
        horizontal=True,
        label_visibility="collapsed",
    )
    tabela = (
        scope(idesp, etapa, ano=ano)
        .dropna(subset=["idesp"])
        .groupby("diretoria", as_index=False)
        .agg(idesp=("idesp", "mean"), escolas=("cod_inep", "nunique"))
    )
    if tabela.empty:
        st.info("Sem dados para montar o ranking de diretorias.")
        return
    melhores = escolha == "Melhores diretorias"
    tabela = tabela.sort_values("idesp", ascending=not melhores).head(15)
    tabela = tabela.sort_values("idesp")
    fig = px.bar(
        tabela,
        x="idesp",
        y="diretoria",
        orientation="h",
        text=tabela["idesp"].map(lambda v: fmt(v)),
        labels={"idesp": "IDESP médio", "diretoria": ""},
        color="idesp",
        color_continuous_scale=["#dbeafe", AZUL] if melhores else ["#fee2e2", "#b91c1c"],
    )
    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(coloraxis_showscale=False)
    style_fig(fig, height=520, showlegend=False)
    fig.update_xaxes(range=[0, float(tabela["idesp"].max()) + 1])
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(
        "Cada diretoria agrega as escolas estaduais de vários municípios. "
        "Médias simples entre escolas, sem ponderação por alunos."
    )

    _render_comparacao_ideb(idesp, filtros)


def _render_comparacao_ideb(idesp: pd.DataFrame, filtros: dict) -> None:
    etapa, ano = filtros["etapa"], filtros["ano"]
    st.divider()
    section(
        "IDESP × Ideb da rede estadual",
        "Municípios paulistas: IDESP médio das escolas estaduais contra o Ideb oficial da mesma rede.",
    )
    if not Path(PROCESSED_FILE).exists():
        st.caption("A base do Ideb não está disponível neste ambiente.")
        return

    ideb = load_ideb(PROCESSED_FILE)
    anos_ideb = sorted(
        int(a)
        for a in ideb.loc[
            (ideb["etapa"] == etapa) & (ideb["rede"] == "Estadual") & (ideb["uf"] == "SP"),
            "ano",
        ].unique()
    )
    proximos = [a for a in anos_ideb if abs(a - ano) <= 2]
    if not proximos:
        st.info(
            f"O Ideb não tem edição próxima de {ano} para esta etapa. As bases são "
            "comparadas apenas quando as edições estão a até dois anos de distância."
        )
        return

    ano_ideb = min(proximos, key=lambda a: (abs(a - ano), a))
    comparacao = compare_with_ideb(idesp, ideb, ano_ideb, etapa)
    if comparacao.empty:
        st.info("Não há municípios com resultado nas duas bases neste recorte.")
        return

    if ano_ideb != ano:
        st.caption(
            f"Comparação com a edição do Ideb de {ano_ideb}, a mais próxima de {ano} "
            "nas duas bases."
        )

    correlacao = comparacao[["idesp", "ideb_oficial"]].corr().iloc[0, 1]
    fig = px.scatter(
        comparacao,
        x="ideb_oficial",
        y="idesp",
        hover_name="municipio",
        labels={"ideb_oficial": "Ideb oficial (rede estadual)", "idesp": "IDESP médio das escolas"},
        color_discrete_sequence=[AZUL],
    )
    fig.update_traces(marker=dict(size=9, opacity=0.7, line=dict(width=1, color="white")))
    limite = [
        min(comparacao["ideb_oficial"].min(), comparacao["idesp"].min()) - 0.5,
        max(comparacao["ideb_oficial"].max(), comparacao["idesp"].max()) + 0.5,
    ]
    fig.add_trace(
        go.Scatter(
            x=limite,
            y=limite,
            mode="lines",
            name="Mesmo valor",
            line=dict(color=CINZA, width=1.5, dash="dot"),
            hoverinfo="skip",
        )
    )
    style_fig(fig, height=430)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.caption(
        f"Correlação entre os dois indicadores: r = {fmt(correlacao)} "
        f"({len(comparacao)} municípios). O IDESP e o Ideb usam escalas e metodologias "
        "diferentes; a comparação é apenas exploratória."
    )


def render_ranking(idesp: pd.DataFrame, filtros: dict) -> None:
    etapa, ano, diretoria, inicio = (
        filtros["etapa"],
        filtros["ano"],
        filtros["diretoria"],
        filtros["inicio"],
    )
    recorte = scope(idesp, etapa, diretoria=diretoria)
    atual = recorte[recorte["ano"] == ano].dropna(subset=["idesp"])
    rotulo_ganhos = f"Maiores avanços desde {inicio}"

    tipo = st.radio(
        "O que mostrar",
        ["Melhores escolas", "Escolas com menor IDESP", "Melhores municípios", rotulo_ganhos],
        horizontal=True,
        label_visibility="collapsed",
    )

    if tipo == rotulo_ganhos:
        tabela = gains_escolas(recorte, inicio, ano, n=15)
        if tabela.empty:
            st.info("Não há escolas com resultado nos dois anos comparados.")
            return
        ordem = tabela.sort_values("ganho")
        fig = px.bar(
            ordem,
            x="ganho",
            y="escola",
            orientation="h",
            text=ordem["ganho"].map(lambda v: f"{v:+.1f}".replace(".", ",")),
            labels={"ganho": "Variação do IDESP", "escola": ""},
            color="ganho",
            color_continuous_scale=["#dbeafe", AZUL_ESCURO],
            hover_data={"municipio": True, "inicio": ":.2f", "fim": ":.2f"},
        )
        exibir = tabela.rename(
            columns={
                "escola": "Escola",
                "municipio": "Município",
                "diretoria": "Diretoria",
                "inicio": str(inicio),
                "fim": str(ano),
                "ganho": "Ganho",
            }
        )
        legenda = (
            f"Escolas com maior variação de IDESP entre {inicio} e {ano} "
            "(apenas quem tem resultado nos dois anos)."
        )
        limite = [min(-0.5, float(tabela["ganho"].min()) - 0.3), float(tabela["ganho"].max()) + 0.8]
    elif tipo == "Melhores municípios":
        tabela = ranking_municipios(atual, n=15, best=True)
        if tabela.empty:
            st.info("Sem dados para o ano selecionado.")
            return
        ordem = tabela.sort_values("idesp")
        fig = px.bar(
            ordem,
            x="idesp",
            y="municipio",
            orientation="h",
            text=ordem["idesp"].map(lambda v: fmt(v)),
            labels={"idesp": "IDESP médio", "municipio": ""},
            color="idesp",
            color_continuous_scale=["#dbeafe", AZUL],
        )
        exibir = tabela.rename(
            columns={"municipio": "Município", "idesp": "IDESP médio", "escolas": "Escolas"}
        )
        legenda = f"Municípios com maior IDESP médio em {ano}."
        limite = [0, float(tabela["idesp"].max()) + 1]
    else:
        melhores = tipo == "Melhores escolas"
        tabela = ranking_escolas(atual, n=15, best=melhores)
        if tabela.empty:
            st.info("Sem dados para o ano selecionado.")
            return
        ordem = tabela.sort_values("idesp")
        fig = px.bar(
            ordem,
            x="idesp",
            y="escola",
            orientation="h",
            text=ordem["idesp"].map(lambda v: fmt(v)),
            labels={"idesp": "IDESP", "escola": ""},
            color="idesp",
            color_continuous_scale=["#dbeafe", AZUL] if melhores else ["#fee2e2", "#b91c1c"],
            hover_data={"municipio": True, "diretoria": True},
        )
        exibir = tabela.rename(
            columns={
                "escola": "Escola",
                "municipio": "Município",
                "diretoria": "Diretoria",
                "idesp": "IDESP",
                "ano": "Ano",
            }
        )
        legenda = f"{tipo} de {etapa.lower()} em {ano}."
        limite = [0, 10.8]

    fig.update_traces(textposition="outside", cliponaxis=False)
    fig.update_layout(coloraxis_showscale=False)
    style_fig(fig, height=520, showlegend=False)
    fig.update_xaxes(range=limite)
    section("Ranking", legenda)
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
    st.dataframe(exibir, width="stretch", hide_index=True)

    csv = atual.to_csv(index=False).encode("utf-8")
    st.download_button(
        "Baixar recorte em CSV",
        data=csv,
        file_name=f"idesp_{STAGES[etapa].lower()}_{ano}.csv",
        mime="text/csv",
    )


def render_municipio(idesp: pd.DataFrame, metas: pd.DataFrame, filtros: dict) -> None:
    etapa, ano, diretoria = filtros["etapa"], filtros["ano"], filtros["diretoria"]
    base = scope(idesp, etapa, diretoria=diretoria)

    opcoes = (
        base[["cod_municipio", "municipio"]]
        .drop_duplicates()
        .sort_values("municipio")
        .reset_index(drop=True)
    )
    if opcoes.empty:
        st.info("Não há municípios para esta combinação de filtros.")
        return

    padrao = opcoes.index[opcoes["municipio"].eq("Presidente Prudente")]
    com_dado = set(base.loc[base["ano"] == ano, "cod_municipio"].dropna())
    if len(padrao) and opcoes.loc[padrao[0], "cod_municipio"] in com_dado:
        indice = int(padrao[0])
    elif com_dado:
        candidatos = opcoes.index[opcoes["cod_municipio"].isin(com_dado)]
        indice = int(candidatos[0]) if len(candidatos) else 0
    else:
        indice = 0
    rotulo = st.selectbox("Município", opcoes["municipio"].tolist(), index=indice)
    codigo = opcoes.loc[opcoes["municipio"] == rotulo, "cod_municipio"].iloc[0]

    serie = municipality_history(scope(idesp, etapa, diretoria=diretoria), codigo)
    if serie.empty:
        st.info("Sem série histórica para este município.")
        return

    nome = serie["municipio"].iloc[0]
    linha = serie[serie["ano"] == ano]
    valor = linha["idesp"].iloc[0] if not linha.empty else None
    inicio = filtros["inicio"]
    inicial = serie.loc[serie["ano"] == inicio, "idesp"]
    variacao = None if inicial.empty or valor is None else valor - inicial.iloc[0]

    ranking_estado = (
        scope(idesp, etapa, ano=ano)
        .dropna(subset=["idesp", "cod_municipio"])
        .groupby(["cod_municipio", "municipio"], as_index=False)["idesp"]
        .mean()
        .sort_values("idesp", ascending=False)
        .reset_index(drop=True)
    )
    posicao = ranking_estado.index[ranking_estado["cod_municipio"] == codigo]
    posicao_txt = f"{posicao[0] + 1}º de {len(ranking_estado)}" if len(posicao) else "—"

    escolas = scope(idesp, etapa, ano=ano, cod_municipio=codigo)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(f"IDESP em {ano}", fmt(valor))
    c2.metric(
        f"Variação {inicio}–{ano}",
        "—" if variacao is None else f"{variacao:+.2f}".replace(".", ","),
    )
    c3.metric("Posição no estado", posicao_txt)
    c4.metric("Escolas com resultado", fmt_int(escolas["cod_inep"].nunique()))

    st.markdown(
        f'<div class="section-sub" style="margin-top:0.8rem">{nome} · '
        f"diretoria de {str(serie['diretoria'].iloc[0]).title()} · "
        f"rede estadual · {etapa.lower()}</div>",
        unsafe_allow_html=True,
    )

    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=serie["ano"],
            y=serie["idesp"],
            mode="lines+markers",
            name=nome,
            line=dict(color=AZUL, width=3.5),
            marker=dict(size=9),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=serie["ano"],
            y=serie["media_diretoria"],
            mode="lines",
            name="Média da diretoria",
            line=dict(color=AMBAR, width=2, dash="dash"),
        )
    )
    fig.add_trace(
        go.Scatter(
            x=serie["ano"],
            y=serie["media_estado"],
            mode="lines",
            name="Média do estado",
            line=dict(color=CINZA, width=1.8, dash="dot"),
        )
    )
    style_fig(fig, height=430)
    valores = serie[["idesp", "media_diretoria", "media_estado"]].to_numpy().ravel()
    valores = valores[~pd.isna(valores)]
    if valores.size:
        fig.update_yaxes(range=[0, min(10, valores.max() + 0.6)])
    fig.update_layout(title="Trajetória do município e referências")
    st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.divider()
    section(
        "Escolas do município",
        f"Resultado de {ano} e situação em relação à meta oficial.",
    )
    tabela = escolas[
        ["escola", "diretoria", "idesp", "cod_inep"]
    ].sort_values("idesp", ascending=False)
    metas_ano = metas[(metas["ano"] == ano) & (metas["etapa"] == etapa)][
        ["cod_inep", "meta"]
    ]
    tabela = tabela.merge(metas_ano, on="cod_inep", how="left")
    tabela["diferenca"] = tabela["idesp"] - tabela["meta"]
    tabela["situacao"] = "—"
    com_meta = tabela["meta"].notna()
    tabela.loc[com_meta, "situacao"] = "Abaixo da meta"
    tabela.loc[com_meta & (tabela["diferenca"] >= -0.05), "situacao"] = "Atingiu a meta"

    exibir = tabela.assign(
        idesp=tabela["idesp"].map(fmt),
        meta=tabela["meta"].map(fmt),
        diferenca=tabela["diferenca"].map(lambda v: "—" if pd.isna(v) else f"{v:+.2f}".replace(".", ",")),
        escola=tabela["escola"].str.title(),
        diretoria=tabela["diretoria"].str.title(),
    ).rename(
        columns={
            "escola": "Escola",
            "diretoria": "Diretoria",
            "idesp": "IDESP",
            "meta": "Meta oficial",
            "diferenca": "Diferença",
            "situacao": "Situação",
        }
    )
    st.dataframe(
        exibir[["Escola", "Diretoria", "IDESP", "Meta oficial", "Diferença", "Situação"]],
        width="stretch",
        hide_index=True,
    )

    with st.expander("Ver a trajetória de uma escola"):
        opcoes_escola = tabela.sort_values("escola")[["cod_inep", "escola"]].drop_duplicates()
        rotulos = {
            row.cod_inep: row.escola.title() for row in opcoes_escola.itertuples()
        }
        codigo_escola = st.selectbox(
            "Escola",
            list(rotulos),
            format_func=lambda c: rotulos[c],
            key=f"escola_{codigo}",
        )
        historico = school_history(scope(idesp, etapa), codigo_escola)
        if historico.empty:
            st.info("Sem série histórica para esta escola.")
        else:
            fig2 = go.Figure()
            fig2.add_trace(
                go.Scatter(
                    x=historico["ano"],
                    y=historico["idesp"],
                    mode="lines+markers",
                    name=historico["escola"].iloc[0].title(),
                    line=dict(color=AZUL, width=3),
                    marker=dict(size=8),
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=historico["ano"],
                    y=historico["media_municipio"],
                    mode="lines",
                    name="Média do município",
                    line=dict(color=AMBAR, width=2, dash="dash"),
                )
            )
            fig2.add_trace(
                go.Scatter(
                    x=historico["ano"],
                    y=historico["media_estado"],
                    mode="lines",
                    name="Média do estado",
                    line=dict(color=CINZA, width=1.8, dash="dot"),
                )
            )
            style_fig(fig2, height=380)
            fig2.update_yaxes(range=[0, 10.5])
            st.plotly_chart(fig2, width="stretch", config={"displayModeBar": False})


def render_metas(idesp: pd.DataFrame, metas: pd.DataFrame, filtros: dict) -> None:
    etapa = filtros["etapa"]
    anos_meta = sorted(
        set(metas.loc[metas["etapa"] == etapa, "ano"].astype(int))
        & set(idesp.loc[idesp["etapa"] == etapa, "ano"].astype(int))
    )
    if not anos_meta:
        st.info("Não há metas oficiais publicadas para esta etapa.")
        return

    ano = st.selectbox(
        "Ano da meta",
        anos_meta,
        index=anos_meta.index(filtros["ano"]) if filtros["ano"] in anos_meta else len(anos_meta) - 1,
        key=f"meta_{etapa}_{filtros['ano']}_{filtros['diretoria']}",
        help="A aba de metas tem ano próprio; por padrão, segue o ano da barra lateral quando há meta publicada.",
    )
    dados = meta_status(idesp, metas, int(ano), etapa)
    if filtros["diretoria"] is not None:
        dados = dados[dados["diretoria"] == filtros["diretoria"]]
    if dados.empty:
        st.info("Sem escolas com resultado e meta neste recorte.")
        return

    cobertura = len(dados) / max(
        1, len(scope(idesp, etapa, ano=int(ano), diretoria=filtros["diretoria"]))
    )
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Escolas comparadas", fmt_int(len(dados)))
    c2.metric("Atingiram a meta", fmt_pct(dados["atingiu"].mean()))
    c3.metric(
        "Diferença média",
        f"{dados['diferenca'].mean():+.2f}".replace(".", ","),
        help="IDESP realizado menos a meta oficial, em média.",
    )
    c4.metric(
        "Maior distância positiva",
        f"{dados['diferenca'].max():+.2f}".replace(".", ","),
        delta=dados.loc[dados["diferenca"].idxmax(), "escola"].title(),
        delta_color="off",
    )
    st.caption(
        f"{fmt_pct(cobertura)} das escolas com resultado em {ano} têm meta publicada. "
        "A comparação considera tolerância de 0,05 ponto."
    )

    col_a, col_b = st.columns([1.15, 1])
    with col_a:
        section("Meta oficial × resultado", "Cada ponto é uma escola; a linha tracejada marca meta igual ao resultado.")
        fig = px.scatter(
            dados,
            x="meta",
            y="idesp",
            color="atingiu",
            hover_name="escola",
            hover_data={"municipio": True, "diretoria": True},
            labels={"meta": "Meta oficial", "idesp": "IDESP realizado", "atingiu": "Atingiu"},
            color_discrete_map={True: AZUL, False: "#dc2626"},
        )
        fig.update_traces(marker=dict(size=7, opacity=0.6))
        limite = [
            min(dados["meta"].min(), dados["idesp"].min()) - 0.4,
            max(dados["meta"].max(), dados["idesp"].max()) + 0.4,
        ]
        fig.add_trace(
            go.Scatter(
                x=limite,
                y=limite,
                mode="lines",
                name="Meta = resultado",
                line=dict(color=CINZA, width=1.5, dash="dot"),
                hoverinfo="skip",
            )
        )
        style_fig(fig, height=430)
        st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_b:
        section("Cumprimento por diretoria", "% de escolas que atingiram a meta, entre as diretorias com mais escolas.")
        por_diretoria = (
            dados.groupby("diretoria", as_index=False)
            .agg(atingiu=("atingiu", "mean"), escolas=("cod_inep", "nunique"))
            .query("escolas >= 5")
        )
        if por_diretoria.empty:
            st.info("Poucas escolas por diretoria neste recorte.")
        else:
            por_diretoria = por_diretoria.sort_values("atingiu", ascending=True).tail(15)
            fig = px.bar(
                por_diretoria,
                x="atingiu",
                y="diretoria",
                orientation="h",
                text=por_diretoria["atingiu"].map(lambda v: fmt_pct(v)),
                labels={"atingiu": "% que atingiu a meta", "diretoria": ""},
                color="atingiu",
                color_continuous_scale=["#fee2e2", AZUL],
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(coloraxis_showscale=False)
            style_fig(fig, height=430, showlegend=False)
            fig.update_xaxes(range=[0, 1.06], tickformat=".0%")
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.divider()
    section("Maiores distâncias em relação à meta", "Escolas com resultado mais distante da meta oficial no ano.")
    piores = dados.nsmallest(15, "diferenca")[
        ["escola", "municipio", "diretoria", "idesp", "meta", "diferenca"]
    ]
    exibir = piores.assign(
        escola=piores["escola"].str.title(),
        diretoria=piores["diretoria"].str.title(),
        idesp=piores["idesp"].map(fmt),
        meta=piores["meta"].map(fmt),
        diferenca=piores["diferenca"].map(lambda v: f"{v:+.2f}".replace(".", ",")),
    ).rename(
        columns={
            "escola": "Escola",
            "municipio": "Município",
            "diretoria": "Diretoria",
            "idesp": "IDESP",
            "meta": "Meta",
            "diferenca": "Diferença",
        }
    )
    st.dataframe(exibir, width="stretch", hide_index=True)
    st.download_button(
        "Baixar metas e resultados em CSV",
        data=dados.to_csv(index=False).encode("utf-8"),
        file_name=f"idesp_metas_{STAGES[etapa].lower()}_{ano}.csv",
        mime="text/csv",
    )


def render_saresp(saresp: pd.DataFrame, filtros: dict) -> None:
    section(
        "Proficiência do Saresp",
        "Médias municipais por série e componente. O Saresp é a avaliação que alimenta o IDESP. "
        "Esta aba tem filtros próprios e não segue a etapa escolhida na barra lateral.",
    )
    redes = [r for r in ["Estadual", "Municipal"] if r in set(saresp["rede"])]
    rede = st.radio("Rede", redes, horizontal=True, index=0)

    componentes = sorted(saresp.loc[saresp["rede"] == rede, "componente"].dropna().unique())
    componente = st.selectbox("Componente", componentes, index=componentes.index("Língua Portuguesa") if "Língua Portuguesa" in componentes else 0)

    anos_parciais = SARESP_ANOS_PARCIAIS & set(saresp["ano"].unique())
    completo = saresp[~saresp["ano"].isin(anos_parciais)]

    series = sorted(
        completo.loc[
            (completo["rede"] == rede) & (completo["componente"] == componente), "serie"
        ]
        .dropna()
        .unique()
    )
    serie_escolhida = "9º ano EF" if "9º ano EF" in series else series[0]
    serie_filtro = st.selectbox("Série", series, index=series.index(serie_escolhida))

    evolucao = saresp_evolution(completo, componente, rede)
    col_a, col_b = st.columns([1.3, 1])
    with col_a:
        section("Evolução da proficiência", f"{componente} — média dos municípios por série.")
        if evolucao.empty:
            st.info("Sem série histórica para este componente.")
        else:
            fig = px.line(
                evolucao,
                x="ano",
                y="media",
                color="serie",
                markers=True,
                labels={"ano": "Edição", "media": "Proficiência média", "serie": "Série"},
            )
            fig.update_traces(marker=dict(size=5), line=dict(width=2.2))
            style_fig(fig, height=400)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    with col_b:
        anos_disponiveis = sorted(
            int(a)
            for a in completo.loc[
                (completo["rede"] == rede)
                & (completo["componente"] == componente)
                & (completo["serie"] == serie_filtro),
                "ano",
            ].unique()
        )
        ano = st.selectbox("Ano do ranking", anos_disponiveis, index=len(anos_disponiveis) - 1)
        escolha = st.radio(
            "Ranking",
            ["Melhores municípios", "Menores médias"],
            horizontal=True,
            label_visibility="collapsed",
        )
        melhores = escolha == "Melhores municípios"
        ranking = saresp_ranking(
            completo, int(ano), serie_filtro, componente, rede=rede, n=12, best=melhores
        )
        section(
            "Ranking de municípios",
            f"{serie_filtro} · {componente} · {ano} · rede {rede.lower()}.",
        )
        if ranking.empty:
            st.info("Sem dados para este recorte.")
        else:
            ordem = ranking.sort_values("medprof")
            fig = px.bar(
                ordem,
                x="medprof",
                y="municipio",
                orientation="h",
                text=ordem["medprof"].map(lambda v: fmt(v, 0)),
                labels={"medprof": "Proficiência média", "municipio": ""},
                color="medprof",
                color_continuous_scale=["#dbeafe", AZUL] if melhores else ["#fee2e2", "#b91c1c"],
            )
            fig.update_traces(textposition="outside", cliponaxis=False)
            fig.update_layout(coloraxis_showscale=False)
            style_fig(fig, height=470, showlegend=False)
            fig.update_xaxes(range=[0, float(ranking["medprof"].max()) + 45])
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})

    st.divider()
    col_c, col_d = st.columns([1.2, 1])
    with col_c:
        section(
            "Língua Portuguesa × Matemática",
            f"Cada ponto é um município em {ano} ({serie_filtro}, rede {rede.lower()}).",
        )
        comparacao = saresp_comparison(completo, int(ano), serie_filtro, rede=rede)
        if comparacao.empty:
            st.info("Sem dados dos dois componentes para este recorte.")
        else:
            correlacao = comparacao[["Língua Portuguesa", "Matemática"]].corr().iloc[0, 1]
            fig = px.scatter(
                comparacao,
                x="Língua Portuguesa",
                y="Matemática",
                hover_name="municipio",
                labels={"Língua Portuguesa": "Língua Portuguesa", "Matemática": "Matemática"},
                color_discrete_sequence=[AZUL],
            )
            fig.update_traces(marker=dict(size=8, opacity=0.65, line=dict(width=1, color="white")))
            fig.add_vline(x=comparacao["Língua Portuguesa"].mean(), line_dash="dot", line_color=CINZA)
            fig.add_hline(y=comparacao["Matemática"].mean(), line_dash="dot", line_color=CINZA)
            style_fig(fig, height=400)
            st.plotly_chart(fig, width="stretch", config={"displayModeBar": False})
            st.caption(
                f"Correlação entre as médias municipais: r = {fmt(correlacao)} "
                f"({len(comparacao)} municípios). As linhas pontilhadas marcam as médias do estado."
            )

    with col_d:
        section("O que observar", "Limites da série publicada.")
        st.markdown(
            """
            - O Saresp é aplicado anualmente, mas **2020 não teve edição** por causa da pandemia.
            - A publicação de **2014** cobre apenas 183 municípios e foi **omitida** dos gráficos.
            - As edições de **2023 a 2025** não trazem o **ensino médio**; por isso a série do EM termina em 2022.
            - A partir de 2022 o portal também publica a rede **municipal**; aqui a rede é sempre escolhida explicitamente.
            - A proficiência é uma **média municipal**, não uma nota por aluno, e usa a escala do Saresp (não vai de 0 a 10).
            """
        )
        st.markdown(f"[Consulta oficial do Saresp]({SARESP_URL})")
        st.caption(
            f"Base: {fmt_int(len(saresp))} registros municipais, "
            f"de {int(saresp['ano'].min())} a {int(saresp['ano'].max())}."
        )


def render_metodo(idesp: pd.DataFrame, metas: pd.DataFrame, saresp: pd.DataFrame, filtros: dict) -> None:
    etapa = filtros["etapa"]
    anos = filtros["anos"]
    st.markdown(
        f"""
        ### De onde vêm os dados

        Os resultados por escola, as metas e as médias do Saresp vêm do
        [portal de dados abertos da Seduc-SP]({FONTE_URL}) e da
        [consulta pública do Saresp]({SARESP_URL}). O projeto baixa os arquivos oficiais,
        empilha as edições em um formato único e mantém as bases tratadas no repositório.
        O download é reprodutível com `python scripts/build_idesp.py`.

        As três bases usadas nesta seção:

        | Base | Conteúdo | Cobertura |
        | --- | --- | --- |
        | IDESP por escola | Resultado do indicador por escola e etapa | 2007–2024 (sem 2020) |
        | Metas por escola | Meta oficial anual por escola e etapa | 2019–2025 (sem 2020) |
        | Proficiência do Saresp | Média municipal por série e componente | 2011–2025 (sem 2020) |

        ### Como o IDESP é calculado

        ```
        IDESP = proficiência padronizada × indicador de fluxo
        ```

        - A **proficiência** vem do Saresp em Língua Portuguesa e Matemática.
        - O **fluxo** considera aprovação, reprovação e abandono.
        - O indicador vai de 0 a 10 e é calculado separadamente para anos iniciais,
          anos finais e ensino médio.

        ### O que este painel mostra — e o que não mostra

        - As médias são **simples entre escolas**: cada escola pesa igual. O IDESP oficial do
          Estado é ponderado pelo número de alunos, então os valores daqui **não substituem**
          o indicador oficial.
        - O painel cobre apenas a **rede estadual paulista**. Escolas municipais, privadas e
          federais não entram no IDESP.
        - O IDESP usa a **escola** como unidade. Quando uma escola oferece mais de uma etapa,
          ela aparece uma vez em cada etapa.
        - O IDESP do **ensino médio** termina em **2022** nas publicações por escola.
        - As **metas** oficiais por escola começam em 2019; antes disso não há meta para
          comparar. A comparação usa tolerância de 0,05 ponto.
        - O Saresp de **2014** foi publicado com apenas 183 municípios e é omitido das séries.
        - A proficiência do Saresp **não é** uma nota de 0 a 10: é a escala do próprio exame.
        - O IDESP e o Ideb são indicadores diferentes, com metodologias e escalas distintas.
          A comparação entre eles é apenas exploratória.

        ### Pipeline

        `download (Seduc-SP) → limpeza (pandas) → dataset tidy → dashboard (Streamlit + Plotly)`

        O repositório inclui testes automatizados para a transformação e para as agregações,
        além de integração contínua no GitHub Actions.
        """
    )

    st.divider()
    section("Cobertura da base", "Escolas com resultado por etapa e edição.")
    cobertura = (
        idesp.groupby(["ano", "etapa"], as_index=False)
        .agg(escolas=("cod_inep", "nunique"), municipios=("cod_municipio", "nunique"))
        .pivot(index="ano", columns="etapa", values="escolas")
        .fillna(0)
        .astype(int)
    )
    cobertura.index.name = "Ano"
    st.dataframe(cobertura, width="stretch")

    st.caption(
        f"Base carregada: {fmt_int(len(idesp))} resultados de escolas · "
        f"{fmt_int(idesp['cod_inep'].nunique())} escolas · "
        f"{fmt_int(idesp['cod_municipio'].nunique())} municípios · "
        f"{fmt_int(len(metas))} metas · {fmt_int(len(saresp))} médias do Saresp · "
        f"etapa selecionada: {etapa.lower()}, edições de {anos[0]} a {anos[-1]}."
    )


# ---------------------------------------------------------------------------
# Entrada da seção
# ---------------------------------------------------------------------------


def render() -> None:
    render_hero(
        kicker="Dados públicos · Rede estadual de São Paulo",
        title="IDESP e Saresp",
        description=(
            "O Índice de Desenvolvimento da Educação do Estado de São Paulo combina "
            "proficiência no Saresp e fluxo escolar. Explore resultados por escola, "
            "metas oficiais e a evolução da aprendizagem nos municípios paulistas."
        ),
        source="Fonte: Seduc-SP — IDESP por escola, metas por escola e proficiência do Saresp",
        variant="idesp",
    )

    ausentes = [
        path
        for path in (IDESP_PROCESSED_FILE, IDESP_METAS_FILE, SARESP_PROCESSED_FILE)
        if not Path(path).exists()
    ]
    if ausentes:
        st.error(
            "Bases do IDESP não encontradas. Rode `python scripts/build_idesp.py` "
            "para baixar e tratar as planilhas da Seduc-SP."
        )
        st.stop()

    idesp = load_idesp(IDESP_PROCESSED_FILE)
    metas = load_metas(IDESP_METAS_FILE)
    saresp = load_saresp(SARESP_PROCESSED_FILE)

    filtros = render_sidebar(idesp)
    render_kpis(idesp, metas, filtros)

    abas = st.tabs(["Panorama", "Ranking", "Município", "Metas", "Saresp", "Método"])
    with abas[0]:
        render_panorama(idesp, filtros)
    with abas[1]:
        render_ranking(idesp, filtros)
    with abas[2]:
        render_municipio(idesp, metas, filtros)
    with abas[3]:
        render_metas(idesp, metas, filtros)
    with abas[4]:
        render_saresp(saresp, filtros)
    with abas[5]:
        render_metodo(idesp, metas, saresp, filtros)

    render_footer(FONTE, FONTE_URL)
