"""Constantes e caminhos do projeto."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
PROCESSED_FILE = PROCESSED_DIR / "ideb_municipios.csv.gz"
REFERENCE_DIR = DATA_DIR / "reference"

# IDESP / Saresp (rede estadual de Sao Paulo).
IDESP_PROCESSED_FILE = PROCESSED_DIR / "idesp_escolas.csv.gz"
IDESP_METAS_FILE = PROCESSED_DIR / "idesp_metas.csv.gz"
SARESP_PROCESSED_FILE = PROCESSED_DIR / "saresp_municipios.csv.gz"

# Edicao mais recente divulgada pelo Inep (Saeb 2025).
DEFAULT_YEAR = 2025
YEARS = list(range(2005, DEFAULT_YEAR + 1, 2))
START_YEAR = YEARS[0]
END_YEAR = YEARS[-1]

STAGES = {
    "Anos Iniciais": "anos_iniciais",
    "Anos Finais": "anos_finais",
    "Ensino Médio": "ensino_medio",
}

# Primeira edicao divulgada por municipio em cada etapa. O Ideb do ensino
# medio passou a ter recorte municipal apenas em 2017.
FIRST_YEAR_BY_STAGE = {
    "anos_iniciais": 2005,
    "anos_finais": 2005,
    "ensino_medio": 2017,
}


def years_for(etapa: str) -> list[int]:
    """Edicoes do Ideb disponiveis para uma etapa (rotulo ou chave interna)."""
    stage_key = STAGES.get(etapa, etapa)
    first_year = FIRST_YEAR_BY_STAGE.get(stage_key, START_YEAR)
    return [year for year in YEARS if year >= first_year]

NETWORKS = ["Pública", "Estadual", "Municipal", "Federal"]

REGIONS = ["Norte", "Nordeste", "Centro-Oeste", "Sudeste", "Sul"]

UF_TO_REGION = {
    "AC": "Norte",
    "AM": "Norte",
    "AP": "Norte",
    "PA": "Norte",
    "RO": "Norte",
    "RR": "Norte",
    "TO": "Norte",
    "AL": "Nordeste",
    "BA": "Nordeste",
    "CE": "Nordeste",
    "MA": "Nordeste",
    "PB": "Nordeste",
    "PE": "Nordeste",
    "PI": "Nordeste",
    "RN": "Nordeste",
    "SE": "Nordeste",
    "DF": "Centro-Oeste",
    "GO": "Centro-Oeste",
    "MS": "Centro-Oeste",
    "MT": "Centro-Oeste",
    "ES": "Sudeste",
    "MG": "Sudeste",
    "RJ": "Sudeste",
    "SP": "Sudeste",
    "PR": "Sul",
    "RS": "Sul",
    "SC": "Sul",
}

UF_CODES = sorted(UF_TO_REGION)

UF_NAMES = {
    "AC": "Acre",
    "AL": "Alagoas",
    "AM": "Amazonas",
    "AP": "Amapá",
    "BA": "Bahia",
    "CE": "Ceará",
    "DF": "Distrito Federal",
    "ES": "Espírito Santo",
    "GO": "Goiás",
    "MA": "Maranhão",
    "MG": "Minas Gerais",
    "MS": "Mato Grosso do Sul",
    "MT": "Mato Grosso",
    "PA": "Pará",
    "PB": "Paraíba",
    "PE": "Pernambuco",
    "PI": "Piauí",
    "PR": "Paraná",
    "RJ": "Rio de Janeiro",
    "RN": "Rio Grande do Norte",
    "RO": "Rondônia",
    "RR": "Roraima",
    "RS": "Rio Grande do Sul",
    "SC": "Santa Catarina",
    "SE": "Sergipe",
    "SP": "São Paulo",
    "TO": "Tocantins",
}

# Nota de corte usada apenas como referencia de leitura, nao como meta oficial.
REFERENCE_IDEB = 6.0

SOURCE_NAME = "INEP/Saeb — Ideb municipal"
SOURCE_URL = "https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados"

REGION_COLORS = {
    "Norte": "#15803d",
    "Nordeste": "#dc2626",
    "Centro-Oeste": "#d97706",
    "Sudeste": "#2563eb",
    "Sul": "#7c3aed",
}
