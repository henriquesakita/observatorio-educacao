"""Leitura e limpeza das planilhas do Ideb municipal.

As planilhas do Inep tem uma linha de titulo, uma de cabecalho composto e
diversas linhas de notas no rodape. O codigo le a partir da linha de nomes
tecnicos (``SG_UF``, ``CO_MUNICIPIO``...) e mantem apenas municipios reais.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pandas as pd

from .config import STAGES, UF_CODES, UF_TO_REGION

logger = logging.getLogger(__name__)

HEADER_ROW = 9
OBSERVED_YEAR_PATTERN = re.compile(r"^VL_OBSERVADO_(\d{4})$")


def _observed_years(columns: pd.Index) -> list[int]:
    """Detecta as edicoes presentes na planilha pelas colunas de Ideb."""
    years = {
        int(match.group(1))
        for column in columns
        if (match := OBSERVED_YEAR_PATTERN.match(str(column)))
    }
    return sorted(years)

NUMERIC_COLUMNS = {
    "ideb": "VL_OBSERVADO_{year}",
    "taxa_aprovacao": "VL_APROVACAO_{year}_SI_4",
    "indicador_rendimento": "VL_INDICADOR_REND_{year}",
    "nota_matematica": "VL_NOTA_MATEMATICA_{year}",
    "nota_portugues": "VL_NOTA_PORTUGUES_{year}",
    "nota_media": "VL_NOTA_MEDIA_{year}",
    "meta": "VL_PROJECAO_{year}",
}

FINAL_COLUMNS = [
    "ano",
    "etapa",
    "uf",
    "regiao",
    "cod_municipio",
    "municipio",
    "rede",
    "ideb",
    "taxa_aprovacao",
    "indicador_rendimento",
    "nota_matematica",
    "nota_portugues",
    "nota_media",
    "meta",
]


def _to_number(series: pd.Series) -> pd.Series:
    """Converte texto numerico do Inep em float, tratando '-' como ausente."""
    text = series.astype("string").str.strip()
    text = text.replace({"-": pd.NA, "": pd.NA})
    text = text.str.replace(",", ".", regex=False)
    return pd.to_numeric(text, errors="coerce")


def read_ideb_workbook(path: str | Path, etapa: str) -> pd.DataFrame:
    """Le uma planilha municipal e devolve dados no formato longo (tidy)."""
    if etapa not in STAGES:
        raise ValueError(f"Etapa invalida: {etapa!r}. Use uma de {list(STAGES)}")

    raw = pd.read_excel(path, header=HEADER_ROW, dtype={"CO_MUNICIPIO": str})

    # Remove rodapes, notas e linhas sem codigo de municipio.
    raw = raw[raw["SG_UF"].isin(UF_CODES)].copy()
    raw["CO_MUNICIPIO"] = raw["CO_MUNICIPIO"].astype(str).str.strip().str.zfill(7)
    raw["NO_MUNICIPIO"] = raw["NO_MUNICIPIO"].astype(str).str.strip()
    raw["REDE"] = raw["REDE"].astype(str).str.strip()

    frames: list[pd.DataFrame] = []
    for year in _observed_years(raw.columns):
        frame = pd.DataFrame(
            {
                "ano": year,
                "uf": raw["SG_UF"],
                "cod_municipio": raw["CO_MUNICIPIO"],
                "municipio": raw["NO_MUNICIPIO"],
                "rede": raw["REDE"],
            }
        )
        for target, template in NUMERIC_COLUMNS.items():
            column = template.format(year=year)
            frame[target] = (
                _to_number(raw[column])
                if column in raw.columns
                else pd.Series(pd.NA, index=raw.index, dtype="Float64")
            )
        frames.append(frame)

    data = pd.concat(frames, ignore_index=True)
    data["etapa"] = etapa
    data["regiao"] = data["uf"].map(UF_TO_REGION)

    # Descarta linhas em que o Inep nao divulgou nenhum indicador.
    indicators = [
        "ideb",
        "taxa_aprovacao",
        "indicador_rendimento",
        "nota_matematica",
        "nota_portugues",
        "nota_media",
    ]
    data = data.dropna(subset=indicators, how="all")

    data["ano"] = data["ano"].astype("int16")
    for column in indicators + ["meta"]:
        data[column] = data[column].astype("float64")

    data = data[FINAL_COLUMNS].sort_values(
        ["ano", "uf", "municipio", "rede"], ignore_index=True
    )
    return data


def build_dataset(raw_paths_by_stage: dict[str, str | Path]) -> pd.DataFrame:
    """Le as planilhas de cada etapa e empilha em um unico DataFrame."""
    frames = [
        read_ideb_workbook(path, etapa) for etapa, path in raw_paths_by_stage.items()
    ]
    data = pd.concat(frames, ignore_index=True)
    logger.info(
        "Dataset montado: %s linhas, %s municipios, anos %s-%s",
        len(data),
        data["cod_municipio"].nunique(),
        data["ano"].min(),
        data["ano"].max(),
    )
    return data
