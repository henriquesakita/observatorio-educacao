from __future__ import annotations

import pandas as pd
import pytest

from observatorio.config import PROCESSED_FILE, UF_CODES
from observatorio.transform import _to_number


def test_to_number_handles_dash_and_comma() -> None:
    values = pd.Series(["5.7", "-", "6,2", "", None])
    result = _to_number(values)
    assert result.iloc[0] == pytest.approx(5.7)
    assert pd.isna(result.iloc[1])
    assert result.iloc[2] == pytest.approx(6.2)
    assert pd.isna(result.iloc[3])
    assert pd.isna(result.iloc[4])


@pytest.fixture(scope="module")
def processed() -> pd.DataFrame:
    if not PROCESSED_FILE.exists():
        pytest.skip("Dataset processado ausente; rode scripts/build_dataset.py")
    return pd.read_csv(PROCESSED_FILE, dtype={"cod_municipio": str})


def test_processed_schema(processed: pd.DataFrame) -> None:
    expected = {
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
    }
    assert expected.issubset(processed.columns)
    assert set(processed["etapa"]) == {"Anos Iniciais", "Anos Finais"}


def test_processed_has_no_duplicate_keys(processed: pd.DataFrame) -> None:
    keys = ["ano", "etapa", "cod_municipio", "rede"]
    assert not processed.duplicated(subset=keys).any()


def test_processed_ufs_are_valid(processed: pd.DataFrame) -> None:
    assert set(processed["uf"]).issubset(set(UF_CODES))
    assert processed["regiao"].notna().all()


def test_ideb_is_product_of_components(processed: pd.DataFrame) -> None:
    frame = processed.dropna(subset=["ideb", "nota_media", "indicador_rendimento"])
    diferenca = (frame["nota_media"] * frame["indicador_rendimento"] - frame["ideb"]).abs()
    # O Inep arredonda o Ideb divulgado para uma casa decimal.
    assert diferenca.max() <= 0.06


def test_ideb_range(processed: pd.DataFrame) -> None:
    ideb = processed["ideb"].dropna()
    assert ideb.between(0, 10).all()


def test_latest_year_has_national_coverage(processed: pd.DataFrame) -> None:
    latest = processed[processed["ano"] == processed["ano"].max()]
    assert latest["cod_municipio"].nunique() > 5500
