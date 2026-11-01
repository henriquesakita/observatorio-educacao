"""Agregacoes e recortes usados pelo dashboard.

Todas as medias sao *simples* (cada municipio pesa igual). O Ideb oficial do
Brasil e da UF e ponderado pelo numero de alunos, portanto os numeros daqui
servem para comparar municipios, nao para substituir o indicador oficial.
"""

from __future__ import annotations

import pandas as pd

from .config import REFERENCE_IDEB


def scope(
    data: pd.DataFrame,
    etapa: str,
    rede: str = "Pública",
    ano: int | None = None,
    uf: str | None = None,
    regiao: str | None = None,
) -> pd.DataFrame:
    """Filtra o dataset por etapa, rede, ano e territorio."""
    mask = (data["etapa"] == etapa) & (data["rede"] == rede)
    if ano is not None:
        mask &= data["ano"] == ano
    if uf is not None:
        mask &= data["uf"] == uf
    if regiao is not None:
        mask &= data["regiao"] == regiao
    return data.loc[mask].copy()


def summary(frame: pd.DataFrame) -> dict[str, float | int | str | None]:
    """Indicadores-resumo de um recorte (normalmente um ano)."""
    valid = frame.dropna(subset=["ideb"])
    if valid.empty:
        return {
            "n_municipios": 0,
            "media": None,
            "mediana": None,
            "abaixo_referencia": None,
            "melhor_municipio": None,
            "melhor_ideb": None,
        }

    best = valid.loc[valid["ideb"].idxmax()]
    return {
        "n_municipios": int(valid["cod_municipio"].nunique()),
        "media": float(valid["ideb"].mean()),
        "mediana": float(valid["ideb"].median()),
        "abaixo_referencia": float((valid["ideb"] < REFERENCE_IDEB).mean()),
        "melhor_municipio": f"{best['municipio']} ({best['uf']})",
        "melhor_ideb": float(best["ideb"]),
    }


def evolution_by_region(frame: pd.DataFrame) -> pd.DataFrame:
    """Media simples do Ideb por regiao e ano."""
    grouped = (
        frame.dropna(subset=["ideb"])
        .groupby(["ano", "regiao"], as_index=False)
        .agg(media=("ideb", "mean"), municipios=("cod_municipio", "nunique"))
    )
    return grouped.sort_values(["ano", "regiao"], ignore_index=True)


def evolution_national(frame: pd.DataFrame) -> pd.DataFrame:
    """Media simples do Ideb por ano (todos os municipios com dado)."""
    grouped = (
        frame.dropna(subset=["ideb"])
        .groupby("ano", as_index=False)
        .agg(
            media=("ideb", "mean"),
            mediana=("ideb", "median"),
            municipios=("cod_municipio", "nunique"),
        )
    )
    return grouped.sort_values("ano", ignore_index=True)


def ranking(
    frame: pd.DataFrame,
    n: int = 10,
    best: bool = True,
    uf: str | None = None,
) -> pd.DataFrame:
    """Maiores (ou menores) Idebs de um recorte anual."""
    data = frame if uf is None else frame[frame["uf"] == uf]
    data = data.dropna(subset=["ideb"])
    data = data.sort_values(["ideb", "municipio"], ascending=[not best, True])
    return data.head(n)[["municipio", "uf", "regiao", "ideb", "ano"]].reset_index(
        drop=True
    )


def biggest_gains(
    frame: pd.DataFrame,
    start: int,
    end: int,
    n: int = 10,
    uf: str | None = None,
) -> pd.DataFrame:
    """Municipios com maior variacao de Ideb entre dois anos."""
    data = frame if uf is None else frame[frame["uf"] == uf]
    pivot = data.pivot_table(
        index=["cod_municipio", "municipio", "uf", "regiao"],
        columns="ano",
        values="ideb",
        aggfunc="first",
    )
    if start not in pivot.columns or end not in pivot.columns:
        return pd.DataFrame(columns=["municipio", "uf", "regiao", "inicio", "fim", "ganho"])

    pairs = pivot[[start, end]].dropna()
    result = pd.DataFrame(
        {
            "municipio": pairs.index.get_level_values("municipio"),
            "uf": pairs.index.get_level_values("uf"),
            "regiao": pairs.index.get_level_values("regiao"),
            "inicio": pairs[start].to_numpy(),
            "fim": pairs[end].to_numpy(),
        }
    )
    result["ganho"] = result["fim"] - result["inicio"]
    result = result.sort_values(["ganho", "municipio"], ascending=[False, True])
    return result.head(n).reset_index(drop=True)


def municipality_history(frame: pd.DataFrame, cod_municipio: str) -> pd.DataFrame:
    """Serie historica de um municipio, com medias de comparacao."""
    city = frame[frame["cod_municipio"] == cod_municipio]
    if city.empty:
        return pd.DataFrame()

    uf = city["uf"].iloc[0]
    regiao = city["regiao"].iloc[0]

    base = frame.dropna(subset=["ideb"])
    uf_mean = (
        base[base["uf"] == uf].groupby("ano")["ideb"].mean().rename("media_uf")
    )
    region_mean = (
        base[base["regiao"] == regiao].groupby("ano")["ideb"].mean().rename("media_regiao")
    )
    national_mean = base.groupby("ano")["ideb"].mean().rename("media_brasil")

    series = (
        city.set_index("ano")[
            [
                "ideb",
                "nota_media",
                "indicador_rendimento",
                "taxa_aprovacao",
                "nota_matematica",
                "nota_portugues",
                "meta",
            ]
        ]
        .join([uf_mean, region_mean, national_mean])
        .reset_index()
        .sort_values("ano")
    )
    series["municipio"] = city["municipio"].iloc[0]
    series["uf"] = uf
    series["regiao"] = regiao
    return series


def coverage(frame: pd.DataFrame) -> pd.DataFrame:
    """Percentual de municipios com Ideb divulgado, por ano."""
    total = frame["cod_municipio"].nunique()
    grouped = (
        frame.dropna(subset=["ideb"])
        .groupby("ano", as_index=False)
        .agg(municipios_com_ideb=("cod_municipio", "nunique"))
    )
    grouped["cobertura"] = grouped["municipios_com_ideb"] / total if total else 0.0
    return grouped
