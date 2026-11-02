from __future__ import annotations

import pandas as pd
import pytest

from observatorio.config import (
    IDESP_METAS_FILE,
    IDESP_PROCESSED_FILE,
    SARESP_PROCESSED_FILE,
)
from observatorio.idesp import (
    attach_municipalities,
    build_idesp,
    build_saresp,
    compare_with_ideb,
    evolution_state,
    gains_escolas,
    meta_status,
    normalize_name,
    read_csv_flexible,
    saresp_evolution,
    saresp_ranking,
    scope,
    summary,
    tidy_idesp_history,
    tidy_idesp_metas,
    tidy_idesp_recent,
    tidy_saresp,
)


@pytest.fixture(scope="module")
def reference() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "cod_municipio": ["3500105", "3516101", "3520905"],
            "municipio": ["Adamantina", "Florínea", "Ipaussu"],
            "chave": ["ADAMANTINA", "FLORINEA", "IPAUSSU"],
        }
    )


@pytest.fixture()
def idesp_long() -> pd.DataFrame:
    rows = []
    for ano, base in [(2019, 4.0), (2021, 3.0), (2022, 5.0)]:
        for cod, escola, valor in [
            ("35000001", "Escola A", base + 1),
            ("35000002", "Escola B", base),
            ("35000003", "Escola C", base - 1),
        ]:
            rows.append(
                {
                    "ano": ano,
                    "etapa": "Anos Iniciais",
                    "cod_escola": cod,
                    "cod_inep": cod,
                    "escola": escola,
                    "diretoria": "ADAMANTINA",
                    "municipio": "Adamantina",
                    "cod_municipio": "3500105",
                    "idesp": valor,
                }
            )
    return pd.DataFrame(rows)


def test_normalize_name_ignores_accents_case_and_punctuation() -> None:
    assert normalize_name("Florínea") == "FLORINEA"
    assert normalize_name("  São  Paulo ") == "SAO PAULO"
    assert normalize_name("Embu-Guaçu") == "EMBU GUACU"
    assert normalize_name("Flor?Nea") == "FLOR NEA"


def test_attach_municipalities_resolves_aliases(reference: pd.DataFrame) -> None:
    frame = pd.DataFrame(
        {"municipio": ["FLORINIA", "IPAUCU", "EMBU", "Cidade Nova"]}
    )
    resultado = attach_municipalities(frame, reference)
    assert resultado["cod_municipio"].tolist()[:2] == ["3516101", "3520905"]
    assert resultado["municipio"].iloc[0] == "Florínea"
    # Nomes sem correspondência oficial continuam legíveis e sem código.
    assert pd.isna(resultado["cod_municipio"].iloc[3])
    assert resultado["municipio"].iloc[3] == "Cidade Nova"


def test_tidy_idesp_history_melts_years() -> None:
    raw = pd.DataFrame(
        {
            "CODIGO CIE": ["1", "2"],
            "CODIGO INEP": ["35000001", "35000002"],
            "DIRETORIA": ["ADAMANTINA", "ADAMANTINA"],
            "ESCOLA": ["A", "B"],
            "MUNICIPIO": ["ADAMANTINA", "ADAMANTINA"],
            "NIVEL ENSINO": ["ANOS INICIAIS", "ENSINO MEDIO"],
            "2007": ["3,5", "-"],
            "2009": ["4,0", "2,5"],
        }
    )
    resultado = tidy_idesp_history(raw)
    assert len(resultado) == 4
    assert set(resultado["etapa"]) == {"Anos Iniciais", "Ensino Médio"}
    assert resultado["idesp"].tolist() == ["3,5", "-", "4,0", "2,5"]


def test_build_idesp_combines_history_and_recent(reference: pd.DataFrame) -> None:
    history = pd.DataFrame(
        {
            "CODIGO CIE": ["1"],
            "CODIGO INEP": ["35000001"],
            "DIRETORIA": ["ADAMANTINA"],
            "ESCOLA": ["A"],
            "MUNICIPIO": ["ADAMANTINA"],
            "NIVEL ENSINO": ["ANOS INICIAIS"],
            "2007": ["3,5"],
        }
    )
    recent = pd.DataFrame(
        {
            "ANO": ["2024"],
            "CODIGO_ESCOLA": ["1"],
            "CODIGO_INEP": ["35000001"],
            "NOME_DIRETORIA": ["ADAMANTINA"],
            "NOME_ESCOLA": ["A"],
            "NOME_MUNICIPIO": ["ADAMANTINA"],
            "ANOS_INICIAIS": ["5,5"],
        }
    )
    resultado = build_idesp(history, {2024: recent}, reference)
    assert resultado["ano"].tolist() == [2007, 2024]
    assert resultado["idesp"].tolist() == pytest.approx([3.5, 5.5])
    assert resultado["cod_municipio"].tolist() == ["3500105", "3500105"]


def test_tidy_idesp_recent_handles_stage_columns() -> None:
    raw = pd.DataFrame(
        {
            "ANO": ["2024", "2024"],
            "CODIGO_ESCOLA": ["1", "2"],
            "CODIGO_INEP": ["35000001", "35000002"],
            "NOME_DIRETORIA": ["ADAMANTINA", "ADAMANTINA"],
            "NOME_ESCOLA": ["A", "B"],
            "NOME_MUNICIPIO": ["ADAMANTINA", "ADAMANTINA"],
            "ANOS_INICIAIS": ["5,5", None],
            "ANOS_FINAIS": ["4,5", "3,0"],
        }
    )
    resultado = tidy_idesp_recent(raw, 2024)
    assert set(resultado["etapa"]) == {"Anos Iniciais", "Anos Finais"}
    assert resultado["ano"].unique().tolist() == [2024]


def test_tidy_idesp_metas_reads_stage_columns() -> None:
    raw = pd.DataFrame(
        {
            "CODIGO_INEP": ["35000001"],
            "NOME_ESCOLA": ["A"],
            "NOME_DIRETORIA": ["ADAMANTINA"],
            "NOME_MUNICIPIO": ["ADAMANTINA"],
            "ANOS_INICIAIS": ["5,0"],
            "ANOS_FINAIS": ["4,0"],
        }
    )
    resultado = tidy_idesp_metas(raw, 2024)
    assert resultado["meta"].tolist() == [4.0, 5.0]
    assert resultado["ano"].unique().tolist() == [2024]


def test_tidy_saresp_normalizes_series_and_components() -> None:
    raw = pd.DataFrame(
        {
            "NomeDepBol": ["Rede Estadual", "Rede Estadual", "Rede Estadual"],
            "MUN": ["ADAMANTINA", "ADAMANTINA", "ADAMANTINA"],
            "SERIE_ANO": ["9º Ano EF", "EM-3ª série", "9º Ano EF"],
            "periodo": ["GERAL", "GERAL", "MANHA"],
            "ds_comp": ["LÍNGUA PORTUGUESA", "MATEMÁTICA", "MATEMÁTICA"],
            "medprof": ["250,5", "280,0", "999,0"],
        }
    )
    resultado = tidy_saresp(raw, 2019)
    assert resultado["rede"].tolist() == ["Estadual", "Estadual"]
    assert resultado["serie"].tolist() == ["9º ano EF", "3ª série EM"]
    assert resultado["componente"].tolist() == ["Língua Portuguesa", "Matemática"]
    assert resultado["medprof"].tolist() == [250.5, 280.0]


def test_build_saresp_attaches_municipality(reference: pd.DataFrame) -> None:
    raw = pd.DataFrame(
        {
            "NomeDepBol": ["Rede Estadual"],
            "MUN": ["FLORINIA"],
            "SERIE_ANO": ["5º Ano EF"],
            "periodo": ["GERAL"],
            "ds_comp": ["LÍNGUA PORTUGUESA"],
            "medprof": ["210,0"],
        }
    )
    resultado = build_saresp({2024: raw}, reference)
    assert resultado.loc[0, "cod_municipio"] == "3516101"
    assert resultado.loc[0, "municipio"] == "Florínea"


def test_read_csv_flexible_handles_latin1_and_semicolon(tmp_path) -> None:
    path = tmp_path / "base.csv"
    path.write_bytes("cod;nome\n1;São Paulo\n".encode("latin-1"))
    resultado = read_csv_flexible(path)
    assert list(resultado.columns) == ["cod", "nome"]
    assert resultado.loc[0, "nome"] == "São Paulo"


def test_summary_and_evolution(idesp_long: pd.DataFrame) -> None:
    recorte = scope(idesp_long, "Anos Iniciais", ano=2022)
    info = summary(recorte)
    assert info["n_escolas"] == 3
    assert info["media"] == pytest.approx(5.0)
    assert info["mediana"] == pytest.approx(5.0)
    assert info["melhor_idesp"] == pytest.approx(6.0)

    evolucao = evolution_state(idesp_long)
    assert evolucao["media"].tolist() == [4.0, 3.0, 5.0]
    assert evolucao["escolas"].tolist() == [3, 3, 3]


def test_gains_and_meta_status(
    idesp_long: pd.DataFrame, reference: pd.DataFrame
) -> None:
    ganhos = gains_escolas(idesp_long, 2019, 2022, n=3)
    assert len(ganhos) == 3
    assert ganhos["ganho"].tolist() == pytest.approx([1.0, 1.0, 1.0])
    assert set(ganhos["cod_inep"]) == {"35000001", "35000002", "35000003"}

    metas = pd.DataFrame(
        {
            "ano": [2022, 2022, 2022],
            "etapa": ["Anos Iniciais"] * 3,
            "cod_inep": ["35000001", "35000002", "35000003"],
            "meta": [5.0, 5.0, 5.0],
        }
    )
    status = meta_status(idesp_long, metas, 2022, "Anos Iniciais")
    assert status["atingiu"].tolist() == [True, True, False]
    assert status["diferenca"].tolist() == pytest.approx([1.0, 0.0, -1.0])


def test_saresp_metrics() -> None:
    data = pd.DataFrame(
        {
            "ano": [2023, 2023, 2023, 2023],
            "rede": ["Estadual"] * 4,
            "cod_municipio": ["3500105", "3500105", "3516101", "3516101"],
            "municipio": ["Adamantina", "Adamantina", "Florínea", "Florínea"],
            "serie": ["9º ano EF"] * 4,
            "componente": ["Língua Portuguesa", "Matemática"] * 2,
            "medprof": [240.0, 250.0, 260.0, 270.0],
        }
    )
    evolucao = saresp_evolution(data, "Matemática", "Estadual")
    assert evolucao["media"].tolist() == [260.0]

    ranking = saresp_ranking(data, 2023, "9º ano EF", "Matemática", rede="Estadual", n=1)
    assert ranking["municipio"].tolist() == ["Florínea"]
    assert ranking["medprof"].tolist() == [270.0]


def test_compare_with_ideb_uses_same_network() -> None:
    idesp = pd.DataFrame(
        {
            "ano": [2023, 2023],
            "etapa": ["Anos Iniciais", "Anos Iniciais"],
            "cod_escola": ["1", "2"],
            "cod_inep": ["35000001", "35000002"],
            "escola": ["A", "B"],
            "diretoria": ["ADAMANTINA", "ADAMANTINA"],
            "municipio": ["Adamantina", "Adamantina"],
            "cod_municipio": ["3500105", "3500105"],
            "idesp": [6.0, 4.0],
        }
    )
    ideb = pd.DataFrame(
        {
            "ano": [2023, 2023],
            "etapa": ["Anos Iniciais", "Anos Iniciais"],
            "rede": ["Estadual", "Municipal"],
            "uf": ["SP", "SP"],
            "cod_municipio": ["3500105", "3500105"],
            "ideb": [5.5, 7.0],
        }
    )
    resultado = compare_with_ideb(idesp, ideb, 2023, "Anos Iniciais")
    assert resultado.loc[0, "idesp"] == pytest.approx(5.0)
    assert resultado.loc[0, "ideb_oficial"] == pytest.approx(5.5)
    assert resultado.loc[0, "diferenca"] == pytest.approx(-0.5)


@pytest.fixture(scope="module")
def processed() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    if not all(
        path.exists()
        for path in (IDESP_PROCESSED_FILE, IDESP_METAS_FILE, SARESP_PROCESSED_FILE)
    ):
        pytest.skip("Bases do IDESP ausentes; rode scripts/build_idesp.py")
    idesp = pd.read_csv(IDESP_PROCESSED_FILE, dtype={"cod_municipio": str, "cod_inep": str})
    metas = pd.read_csv(IDESP_METAS_FILE, dtype={"cod_inep": str})
    saresp = pd.read_csv(SARESP_PROCESSED_FILE, dtype={"cod_municipio": str})
    return idesp, metas, saresp


def test_processed_idesp_schema_and_coverage(processed) -> None:
    idesp, _, _ = processed
    assert {
        "ano",
        "etapa",
        "cod_inep",
        "escola",
        "diretoria",
        "municipio",
        "cod_municipio",
        "idesp",
    }.issubset(idesp.columns)
    assert idesp["ano"].min() == 2007
    assert idesp["ano"].max() == 2024
    assert 2020 not in set(idesp["ano"])
    assert idesp["cod_municipio"].nunique() == 644
    assert idesp["idesp"].between(0, 10).all()
    assert not idesp.duplicated(subset=["ano", "etapa", "cod_inep"]).any()
    ensino_medio = idesp[idesp["etapa"] == "Ensino Médio"]
    assert ensino_medio["ano"].max() == 2022


def test_processed_metas_cover_official_years(processed) -> None:
    _, metas, _ = processed
    assert sorted(metas["ano"].unique()) == [2019, 2021, 2022, 2023, 2024, 2025]
    assert metas["meta"].between(0, 10).all()
    assert not metas.duplicated(subset=["ano", "etapa", "cod_inep"]).any()
    assert metas[metas["ano"] == 2024]["etapa"].nunique() == 2


def test_processed_saresp_schema_and_coverage(processed) -> None:
    _, _, saresp = processed
    assert {
        "ano",
        "rede",
        "cod_municipio",
        "municipio",
        "serie",
        "componente",
        "medprof",
    }.issubset(saresp.columns)
    assert saresp["ano"].min() == 2011
    assert saresp["ano"].max() == 2025
    assert 2020 not in set(saresp["ano"])
    assert saresp["cod_municipio"].nunique() == 645
    assert set(saresp["rede"]) <= {"Estadual", "Municipal"}
    assert saresp["medprof"].between(0, 500).all()
    assert not saresp.duplicated(
        subset=["ano", "rede", "cod_municipio", "serie", "componente"]
    ).any()
