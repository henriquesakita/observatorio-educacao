"""Dados do IDESP (Sao Paulo) e da proficiencia do Saresp.

O IDESP e o indicador da rede estadual paulista: combina a proficiencia dos
alunos no Saresp com o fluxo escolar (aprovacao). As planilhas publicadas pela
Seduc-SP trazem o resultado por escola; aqui elas sao empilhadas em formato
longo e agregadas por municipio e diretoria de ensino.

Todas as agregacoes do painel sao medias simples entre escolas (cada escola
pesa igual). O IDESP oficial do Estado e ponderado pelo numero de alunos.
"""

from __future__ import annotations

import io
import logging
import re
import unicodedata
from pathlib import Path

import pandas as pd

from .config import REFERENCE_DIR
from .transform import _to_number

logger = logging.getLogger(__name__)

IDESP_REFERENCE_FILE = REFERENCE_DIR / "municipios_sp.csv"

STAGES = {
    "Anos Iniciais": "ANOS INICIAIS",
    "Anos Finais": "ANOS FINAIS",
    "Ensino Médio": "ENSINO MEDIO",
}
STAGE_BY_NORMALIZED = {key: label for label, key in STAGES.items()}

MUNICIPALITY_ALIASES = {
    "EMBU": "EMBU DAS ARTES",
    "FLORINIA": "FLORINEA",
    "FLOR NEA": "FLORINEA",
    "IPAUCU": "IPAUSSU",
}

IDESP_HISTORY_URL = (
    "https://dados.educacao.sp.gov.br/sites/default/files/IDESP_Escolas_2007_2022.csv"
)
IDESP_RECENT_URLS = {
    2023: "https://dados.educacao.sp.gov.br/sites/default/files/IDESP_ESCOLA_2023_1.csv",
    2024: "https://dados.educacao.sp.gov.br/sites/default/files/IDESP_ESCOLA_2024.csv",
}
IDESP_META_URLS = {
    2019: "https://dados.educacao.sp.gov.br/sites/default/files/IDESP%20Metas%20por%20Escola%20-%202019_0.csv",
    2021: "https://dados.educacao.sp.gov.br/sites/default/files/IDESP%20Metas%20por%20Escola%202021.csv",
    2022: "https://dados.educacao.sp.gov.br/sites/default/files/IDESP%20Metas%20por%20Escola%202022.csv",
    2023: "https://dados.educacao.sp.gov.br/sites/default/files/Idesp%20Meta%20Por%20Escola%202023.csv",
    2024: "https://dados.educacao.sp.gov.br/sites/default/files/Idesp%20Meta%20Por%20Escola%202024_0.csv",
    2025: "https://dados.educacao.sp.gov.br/sites/default/files/Idesp%20Meta%20Por%20Escola%202025.csv",
}
SARESP_URLS = {
    2011: "https://dados.educacao.sp.gov.br/sites/default/files/2011_MedProf_DistrNivel_mun_0.csv",
    2012: "https://dados.educacao.sp.gov.br/sites/default/files/2012_MedProf_DistrNivel_mun_0.csv",
    2013: "https://dados.educacao.sp.gov.br/sites/default/files/2013_MedProf_DistrNivel_mun_0_0.csv",
    2014: "https://dados.educacao.sp.gov.br/sites/default/files/2014_MedProf_DistrNivel_mun_0_0.csv",
    2015: "https://dados.educacao.sp.gov.br/sites/default/files/2015_MedProf_DistrNivel_mun_0_0.csv",
    2016: "https://dados.educacao.sp.gov.br/sites/default/files/2016_MedProf_DistrNivel_mun_0.csv",
    2017: "https://dados.educacao.sp.gov.br/sites/default/files/2017_MedProf_DistrNivel_mun_0_0.csv",
    2018: "https://dados.educacao.sp.gov.br/sites/default/files/2018_MedProf_DistrNivel_mun_0.csv",
    2019: "https://dados.educacao.sp.gov.br/sites/default/files/2019_MedProf_DistrNivel_mun_0.csv",
    2021: "https://dados.educacao.sp.gov.br/sites/default/files/Profici%C3%AAncia_SARESP_2021_por_munic%C3%ADpio_0.csv",
    2022: "https://dados.educacao.sp.gov.br/sites/default/files/Profici%C3%AAncia%20do%20SARESP%20por%20munic%C3%ADpio%20de%202022_0.csv",
    2023: "https://dados.educacao.sp.gov.br/sites/default/files/Profici%C3%AAncia%20do%20SARESP%20por%20Municipio%20de%202023_0.csv",
    2024: "https://dados.educacao.sp.gov.br/sites/default/files/Profici%C3%AAncia%20do%20SARESP%20por%20Municipio%20de%202024_0.csv",
    2025: "https://dados.educacao.sp.gov.br/sites/default/files/Profici%C3%AAncia%20do%20SARESP%20por%20Municipio%20de%202025_0.csv",
}


# ---------------------------------------------------------------------------
# Leitura e normalizacao
# ---------------------------------------------------------------------------


def normalize_name(value: object) -> str:
    """Compara nomes de municipios sem acento, caixa ou pontuacao."""
    text = unicodedata.normalize("NFKD", str(value))
    text = text.encode("ascii", "ignore").decode("ascii").upper()
    return re.sub(r"[^A-Z0-9]+", " ", text).strip()


def read_csv_flexible(path: str | Path) -> pd.DataFrame:
    """Le CSV do portal da Seduc, que varia entre UTF-8 e Latin-1."""
    raw = Path(path).read_bytes()
    text = None
    for encoding in ("utf-8-sig", "latin-1"):
        try:
            text = raw.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    if text is None:
        raise UnicodeDecodeError("utf-8", b"", 0, 1, f"Codificacao desconhecida: {path}")

    sample = text[:20000]
    separator = ";" if sample.count(";") >= sample.count(",") else ","
    return pd.read_csv(io.StringIO(text), sep=separator, dtype=str)


def load_municipality_reference(path: str | Path = IDESP_REFERENCE_FILE) -> pd.DataFrame:
    """Tabela oficial dos 645 municipios paulistas (codigo IBGE e nome)."""
    reference = pd.read_csv(path, dtype={"cod_municipio": str})
    reference["municipio"] = reference["municipio"].astype(str).str.strip()
    reference["chave"] = reference["municipio"].map(normalize_name)
    return reference[["cod_municipio", "municipio", "chave"]]


def attach_municipalities(
    frame: pd.DataFrame, reference: pd.DataFrame
) -> pd.DataFrame:
    """Adiciona o codigo IBGE a partir do nome do municipio."""
    data = frame.copy()
    data["chave"] = (
        data["municipio"].map(normalize_name).replace(MUNICIPALITY_ALIASES)
    )
    data = data.merge(
        reference.rename(columns={"municipio": "municipio_oficial"}),
        on="chave",
        how="left",
    )
    data["municipio"] = data["municipio_oficial"].fillna(
        data["municipio"].str.title()
    )
    data["cod_municipio"] = data["cod_municipio"].astype("string").str.zfill(7)
    return data.drop(columns=["chave", "municipio_oficial"])


def _clean_code(series: pd.Series) -> pd.Series:
    return series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def _stage_from_column(column: str) -> str | None:
    key = re.sub(r"[^A-Z0-9]+", " ", column.upper()).strip()
    return STAGE_BY_NORMALIZED.get(key)


# ---------------------------------------------------------------------------
# IDESP por escola
# ---------------------------------------------------------------------------


def tidy_idesp_history(raw: pd.DataFrame) -> pd.DataFrame:
    """Converte a planilha 2007-2022 (uma linha por escola e nivel)."""
    data = raw.rename(
        columns={
            "CODIGO CIE": "cod_escola",
            "CODIGO INEP": "cod_inep",
            "DIRETORIA": "diretoria",
            "ESCOLA": "escola",
            "MUNICIPIO": "municipio",
            "NIVEL ENSINO": "nivel",
        }
    )
    year_columns = [c for c in data.columns if re.fullmatch(r"\d{4}", str(c))]
    data = data.melt(
        id_vars=["cod_escola", "cod_inep", "diretoria", "escola", "municipio", "nivel"],
        value_vars=year_columns,
        var_name="ano",
        value_name="idesp",
    )
    data["etapa"] = data["nivel"].map(
        lambda value: STAGE_BY_NORMALIZED.get(
            re.sub(r"[^A-Z0-9]+", " ", str(value).upper()).strip()
        )
    )
    return data.drop(columns="nivel")


def tidy_idesp_recent(raw: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Converte as planilhas de 2023 e 2024 (colunas por etapa)."""
    columns = {
        "CODIGO_ESCOLA": "cod_escola",
        "CODIGO_INEP": "cod_inep",
        "NOME_DIRETORIA": "diretoria",
        "NOME_ESCOLA": "escola",
        "NOME_MUNICIPIO": "municipio",
    }
    stage_columns = {
        "ANOS_INICIAIS": "Anos Iniciais",
        "ANOS_FINAIS": "Anos Finais",
        "ENSINO_MEDIO": "Ensino Médio",
    }
    available = {
        column: label for column, label in stage_columns.items() if column in raw.columns
    }
    data = raw.rename(columns=columns).melt(
        id_vars=["cod_escola", "cod_inep", "diretoria", "escola", "municipio"],
        value_vars=list(available),
        var_name="etapa",
        value_name="idesp",
    )
    data["etapa"] = data["etapa"].map(available)
    data["ano"] = ano
    return data


def _clean_idesp(frame: pd.DataFrame) -> pd.DataFrame:
    data = frame.copy()
    data["ano"] = pd.to_numeric(data["ano"], errors="coerce").astype("Int16")
    data["idesp"] = _to_number(data["idesp"])
    data["cod_escola"] = _clean_code(data["cod_escola"])
    data["cod_inep"] = _clean_code(data["cod_inep"])
    for column in ("escola", "diretoria", "municipio"):
        data[column] = data[column].astype("string").str.strip()
    data = data.dropna(subset=["ano", "etapa", "idesp"])
    data["ano"] = data["ano"].astype("int16")
    data = data.drop_duplicates(subset=["ano", "etapa", "cod_inep"])
    columns = [
        "ano",
        "etapa",
        "cod_escola",
        "cod_inep",
        "escola",
        "diretoria",
        "municipio",
        "cod_municipio",
        "idesp",
    ]
    return data[columns].sort_values(
        ["ano", "etapa", "municipio", "escola"], ignore_index=True
    )


def build_idesp(
    history: pd.DataFrame,
    recent_by_year: dict[int, pd.DataFrame],
    reference: pd.DataFrame,
) -> pd.DataFrame:
    """Empilha todas as edicoes do IDESP em formato longo."""
    frames = [tidy_idesp_history(history)]
    frames += [
        tidy_idesp_recent(raw, ano) for ano, raw in recent_by_year.items()
    ]
    data = pd.concat(frames, ignore_index=True)
    data = attach_municipalities(data, reference)
    data = _clean_idesp(data)
    logger.info(
        "IDESP montado: %s linhas, %s escolas, %s municipios, anos %s-%s",
        len(data),
        data["cod_inep"].nunique(),
        data["cod_municipio"].nunique(),
        data["ano"].min(),
        data["ano"].max(),
    )
    return data


# ---------------------------------------------------------------------------
# Metas do IDESP
# ---------------------------------------------------------------------------


def tidy_idesp_metas(raw: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Converte a planilha anual de metas por escola em formato longo."""
    rename = {
        "CODIGO CIE": "cod_escola",
        "CODIGO_ESCOLA": "cod_escola",
        "CODIGO INEP": "cod_inep",
        "CODIGO_INEP": "cod_inep",
        "ESCOLA": "escola",
        "NOME_ESCOLA": "escola",
        "DIRETORIA": "diretoria",
        "NOME_DIRETORIA": "diretoria",
        "MUNICIPIO": "municipio",
        "NOME_MUNICIPIO": "municipio",
    }
    data = raw.rename(columns=rename)
    stage_columns = {
        "ANOS_INICIAIS": "Anos Iniciais",
        "ANOS_FINAIS": "Anos Finais",
        "ENSINO_MEDIO": "Ensino Médio",
        "ANOS INICIAIS": "Anos Iniciais",
        "ANOS FINAIS": "Anos Finais",
        "ENSINO MEDIO": "Ensino Médio",
    }
    available = {
        column: label for column, label in stage_columns.items() if column in data.columns
    }
    long = data.melt(
        id_vars=["cod_inep", "escola", "diretoria", "municipio"],
        value_vars=list(available),
        var_name="etapa",
        value_name="meta",
    )
    long["etapa"] = long["etapa"].map(available)
    long["ano"] = ano
    long["meta"] = _to_number(long["meta"])
    long["cod_inep"] = _clean_code(long["cod_inep"])
    long = long.dropna(subset=["meta"])
    long["meta"] = long["meta"].astype("float64")
    return long[["ano", "etapa", "cod_inep", "meta"]].sort_values(
        ["ano", "etapa", "cod_inep"], ignore_index=True
    )


def build_metas(raw_by_year: dict[int, pd.DataFrame]) -> pd.DataFrame:
    """Empilha as metas anuais por escola."""
    frames = [tidy_idesp_metas(raw, ano) for ano, raw in raw_by_year.items()]
    data = pd.concat(frames, ignore_index=True)
    logger.info(
        "Metas montadas: %s linhas, anos %s-%s",
        len(data),
        data["ano"].min(),
        data["ano"].max(),
    )
    return data


# ---------------------------------------------------------------------------
# Proficiencia do Saresp
# ---------------------------------------------------------------------------

COMPONENT_LABELS = {
    "LINGUA PORTUGUESA": "Língua Portuguesa",
    "MATEMATICA": "Matemática",
    "CIENCIAS": "Ciências",
    "GEOGRAFIA": "Geografia",
    "HISTORIA": "História",
}


def _normalize_series(value: object) -> str | None:
    text = normalize_name(value)
    match = re.search(r"(\d+)\s*(?:O|A|º|ª)?\s*ANO\s*EF", text)
    if match:
        return f"{match.group(1)}º ano EF"
    if "EM" in text or "3" in text:
        return "3ª série EM"
    return None


def tidy_saresp(raw: pd.DataFrame, ano: int) -> pd.DataFrame:
    """Normaliza a planilha municipal do Saresp (medias de proficiencia)."""
    columns = {str(c).strip().upper(): c for c in raw.columns}

    def pick(*names: str) -> str | None:
        for name in names:
            if name in columns:
                return columns[name]
        return None

    rede = pick("NOMEDEPBOL", "DEPBOL")
    municipio = pick("MUN", "MUNICIPIO")
    serie = pick("SERIE_ANO")
    periodo = pick("PERIODO")
    componente = pick("DS_COMP")
    nota = pick("MEDPROF")

    missing = [
        label
        for label, column in {
            "rede": rede,
            "municipio": municipio,
            "serie": serie,
            "periodo": periodo,
            "componente": componente,
            "medprof": nota,
        }.items()
        if column is None
    ]
    if missing:
        raise ValueError(f"Colunas ausentes no Saresp {ano}: {missing}")

    data = pd.DataFrame(
        {
            "ano": ano,
            "rede": raw[rede].astype(str).str.replace("Rede ", "", regex=False).str.strip(),
            "serie": raw[serie].map(_normalize_series),
            "periodo": raw[periodo].astype(str).str.strip(),
            "componente": raw[componente]
            .map(normalize_name)
            .map(COMPONENT_LABELS),
            "municipio": raw[municipio].astype(str).str.strip(),
            "medprof": _to_number(raw[nota]),
        }
    )
    data = data[data["periodo"].str.upper().str.contains("GERAL", na=False)]
    data = data.dropna(subset=["serie", "componente", "medprof"])
    data["ano"] = data["ano"].astype("int16")
    return data[["ano", "rede", "municipio", "serie", "componente", "medprof"]]


def build_saresp(
    raw_by_year: dict[int, pd.DataFrame], reference: pd.DataFrame
) -> pd.DataFrame:
    """Empilha as medias de proficiencia do Saresp por municipio."""
    frames = [tidy_saresp(raw, ano) for ano, raw in raw_by_year.items()]
    data = pd.concat(frames, ignore_index=True)
    data = attach_municipalities(data, reference)
    data["cod_municipio"] = data["cod_municipio"].astype("string")
    data = data.dropna(subset=["cod_municipio"])
    data["cod_municipio"] = data["cod_municipio"].str.zfill(7)
    logger.info(
        "Saresp montado: %s linhas, %s municipios, anos %s-%s",
        len(data),
        data["cod_municipio"].nunique(),
        data["ano"].min(),
        data["ano"].max(),
    )
    return data[
        [
            "ano",
            "rede",
            "cod_municipio",
            "municipio",
            "serie",
            "componente",
            "medprof",
        ]
    ].sort_values(["ano", "serie", "componente", "municipio"], ignore_index=True)


# ---------------------------------------------------------------------------
# Metricas usadas pelo painel
# ---------------------------------------------------------------------------


def scope(
    data: pd.DataFrame,
    etapa: str | None = None,
    ano: int | None = None,
    diretoria: str | None = None,
    cod_municipio: str | None = None,
    cod_inep: str | None = None,
) -> pd.DataFrame:
    """Filtra o dataset do IDESP por etapa, ano e territorio."""
    mask = pd.Series(True, index=data.index)
    if etapa is not None:
        mask &= data["etapa"] == etapa
    if ano is not None:
        mask &= data["ano"] == ano
    if diretoria is not None:
        mask &= data["diretoria"] == diretoria
    if cod_municipio is not None:
        mask &= data["cod_municipio"] == cod_municipio
    if cod_inep is not None:
        mask &= data["cod_inep"] == cod_inep
    return data.loc[mask].copy()


def summary(frame: pd.DataFrame, reference: float = 6.0) -> dict[str, object]:
    """Indicadores-resumo de um recorte anual do IDESP."""
    valid = frame.dropna(subset=["idesp"])
    if valid.empty:
        return {
            "n_escolas": 0,
            "n_municipios": 0,
            "media": None,
            "mediana": None,
            "abaixo_referencia": None,
            "melhor_escola": None,
            "melhor_idesp": None,
        }
    best = valid.loc[valid["idesp"].idxmax()]
    return {
        "n_escolas": int(valid["cod_inep"].nunique()),
        "n_municipios": int(valid["cod_municipio"].nunique()),
        "media": float(valid["idesp"].mean()),
        "mediana": float(valid["idesp"].median()),
        "abaixo_referencia": float((valid["idesp"] < reference).mean()),
        "melhor_escola": f"{best['escola'].title()} ({best['municipio']})",
        "melhor_idesp": float(best["idesp"]),
    }


def evolution_state(data: pd.DataFrame) -> pd.DataFrame:
    """Media simples do IDESP por etapa e ano."""
    grouped = (
        data.dropna(subset=["idesp"])
        .groupby(["ano", "etapa"], as_index=False)
        .agg(media=("idesp", "mean"), escolas=("cod_inep", "nunique"))
    )
    return grouped.sort_values(["ano", "etapa"], ignore_index=True)


def evolution_by_diretoria(data: pd.DataFrame, etapa: str) -> pd.DataFrame:
    """Media simples do IDESP por diretoria de ensino ao longo dos anos."""
    frame = scope(data, etapa)
    grouped = (
        frame.dropna(subset=["idesp"])
        .groupby(["ano", "diretoria"], as_index=False)
        .agg(media=("idesp", "mean"), escolas=("cod_inep", "nunique"))
    )
    return grouped.sort_values(["ano", "diretoria"], ignore_index=True)


def ranking_municipios(
    frame: pd.DataFrame, n: int = 15, best: bool = True
) -> pd.DataFrame:
    """Municipios com maior (ou menor) IDESP medio no recorte."""
    grouped = (
        frame.dropna(subset=["idesp"])
        .groupby(["cod_municipio", "municipio"], as_index=False)
        .agg(idesp=("idesp", "mean"), escolas=("cod_inep", "nunique"))
    )
    grouped = grouped.sort_values(["idesp", "municipio"], ascending=[not best, True])
    return grouped.head(n).reset_index(drop=True)


def ranking_escolas(
    frame: pd.DataFrame, n: int = 15, best: bool = True
) -> pd.DataFrame:
    """Escolas com maior (ou menor) IDESP no recorte."""
    data = frame.dropna(subset=["idesp"]).sort_values(
        ["idesp", "escola"], ascending=[not best, True]
    )
    return data.head(n)[
        ["escola", "municipio", "diretoria", "idesp", "ano"]
    ].reset_index(drop=True)


def _gains(
    frame: pd.DataFrame, keys: list[str], start: int, end: int
) -> pd.DataFrame:
    data = frame.dropna(subset=["idesp"])
    pivot = data.pivot_table(
        index=keys, columns="ano", values="idesp", aggfunc="mean"
    )
    if start not in pivot.columns or end not in pivot.columns:
        return pd.DataFrame(columns=keys + ["inicio", "fim", "ganho"])
    pairs = pivot[[start, end]].dropna()
    result = pairs.reset_index()
    result = result.rename(columns={start: "inicio", end: "fim"})
    result["ganho"] = result["fim"] - result["inicio"]
    return result.sort_values(["ganho", "inicio"], ascending=[False, False])


def gains_municipios(
    frame: pd.DataFrame, start: int, end: int, n: int = 15
) -> pd.DataFrame:
    """Maior variacao do IDESP medio municipal entre dois anos."""
    return _gains(frame, ["cod_municipio", "municipio"], start, end).head(n).reset_index(
        drop=True
    )


def gains_escolas(
    frame: pd.DataFrame, start: int, end: int, n: int = 15
) -> pd.DataFrame:
    """Maior variacao do IDESP de uma escola entre dois anos."""
    result = _gains(
        frame, ["cod_inep", "escola", "municipio", "diretoria"], start, end
    )
    return result.head(n).reset_index(drop=True)


def municipality_history(frame: pd.DataFrame, cod_municipio: str) -> pd.DataFrame:
    """Serie do municipio com referencias do estado e da diretoria."""
    city = frame[frame["cod_municipio"] == cod_municipio]
    if city.empty:
        return pd.DataFrame()

    diretoria = city["diretoria"].mode()
    diretoria = diretoria.iloc[0] if not diretoria.empty else None
    base = frame.dropna(subset=["idesp"])

    series = (
        city.groupby("ano", as_index=False)
        .agg(
            idesp=("idesp", "mean"),
            escolas=("cod_inep", "nunique"),
            municipio=("municipio", "first"),
            diretoria=("diretoria", "first"),
        )
        .set_index("ano")
    )
    state = base.groupby("ano")["idesp"].mean().rename("media_estado")
    if diretoria is not None:
        diretoria_mean = (
            base[base["diretoria"] == diretoria]
            .groupby("ano")["idesp"]
            .mean()
            .rename("media_diretoria")
        )
    else:
        diretoria_mean = pd.Series(dtype="float64", name="media_diretoria")
    return series.join([state, diretoria_mean]).reset_index().sort_values("ano")


def school_history(frame: pd.DataFrame, cod_inep: str) -> pd.DataFrame:
    """Serie de uma escola com referencias do municipio e do estado."""
    school = frame[frame["cod_inep"] == cod_inep]
    if school.empty:
        return pd.DataFrame()

    cod_municipio = school["cod_municipio"].iloc[0]
    city = frame[frame["cod_municipio"] == cod_municipio].dropna(subset=["idesp"])
    state = frame.dropna(subset=["idesp"])

    series = school.set_index("ano")[["idesp", "escola", "municipio", "diretoria"]]
    city_mean = city.groupby("ano")["idesp"].mean().rename("media_municipio")
    state_mean = state.groupby("ano")["idesp"].mean().rename("media_estado")
    return series.join([city_mean, state_mean]).reset_index().sort_values("ano")


def meta_status(
    results: pd.DataFrame, metas: pd.DataFrame, ano: int, etapa: str
) -> pd.DataFrame:
    """Compara o resultado de cada escola com a meta oficial do ano."""
    result = scope(results, etapa, ano=ano)[
        ["cod_inep", "escola", "municipio", "diretoria", "idesp"]
    ]
    target = metas[(metas["ano"] == ano) & (metas["etapa"] == etapa)][
        ["cod_inep", "meta"]
    ]
    data = result.merge(target, on="cod_inep", how="inner").dropna(
        subset=["idesp", "meta"]
    )
    data["atingiu"] = data["idesp"] >= data["meta"] - 0.05
    data["diferenca"] = data["idesp"] - data["meta"]
    return data


def saresp_evolution(
    data: pd.DataFrame, componente: str, rede: str | None = None
) -> pd.DataFrame:
    """Proficiencia media do Saresp por serie e ano."""
    frame = data[data["componente"] == componente]
    if rede is not None:
        frame = frame[frame["rede"] == rede]
    grouped = (
        frame.dropna(subset=["medprof"])
        .groupby(["ano", "serie"], as_index=False)
        .agg(media=("medprof", "mean"), municipios=("cod_municipio", "nunique"))
    )
    return grouped.sort_values(["ano", "serie"], ignore_index=True)


def saresp_ranking(
    data: pd.DataFrame,
    ano: int,
    serie: str,
    componente: str,
    rede: str | None = None,
    n: int = 15,
    best: bool = True,
) -> pd.DataFrame:
    """Municipios com maior (ou menor) proficiencia media no Saresp."""
    frame = data[
        (data["ano"] == ano)
        & (data["serie"] == serie)
        & (data["componente"] == componente)
    ]
    if rede is not None:
        frame = frame[frame["rede"] == rede]
    grouped = (
        frame.dropna(subset=["medprof"])
        .groupby(["cod_municipio", "municipio"], as_index=False)
        .agg(medprof=("medprof", "mean"))
    )
    grouped = grouped.sort_values(
        ["medprof", "municipio"], ascending=[not best, True]
    )
    return grouped.head(n).reset_index(drop=True)


def saresp_comparison(
    data: pd.DataFrame,
    ano: int,
    serie: str,
    rede: str | None = None,
) -> pd.DataFrame:
    """Compara a media municipal em Lingua Portuguesa e Matematica."""
    frame = data[(data["ano"] == ano) & (data["serie"] == serie)]
    if rede is not None:
        frame = frame[frame["rede"] == rede]
    pivot = frame.pivot_table(
        index=["cod_municipio", "municipio"],
        columns="componente",
        values="medprof",
        aggfunc="mean",
    )
    if not {"Língua Portuguesa", "Matemática"}.issubset(pivot.columns):
        return pd.DataFrame()
    return pivot[["Língua Portuguesa", "Matemática"]].dropna().reset_index()


def compare_with_ideb(
    idesp: pd.DataFrame,
    ideb: pd.DataFrame,
    ano: int,
    etapa: str,
) -> pd.DataFrame:
    """Compara o IDESP municipal (rede estadual) com o Ideb da mesma rede."""
    local = (
        scope(idesp, etapa, ano=ano)
        .dropna(subset=["idesp", "cod_municipio"])
        .groupby(["cod_municipio", "municipio"], as_index=False)
        .agg(idesp=("idesp", "mean"), escolas=("cod_inep", "nunique"))
    )
    reference = ideb[
        (ideb["ano"] == ano)
        & (ideb["etapa"] == etapa)
        & (ideb["rede"] == "Estadual")
        & (ideb["uf"] == "SP")
    ][["cod_municipio", "ideb"]].rename(columns={"ideb": "ideb_oficial"})
    data = local.merge(reference, on="cod_municipio", how="inner").dropna(
        subset=["idesp", "ideb_oficial"]
    )
    data["diferenca"] = data["idesp"] - data["ideb_oficial"]
    return data.sort_values("idesp", ascending=False, ignore_index=True)
