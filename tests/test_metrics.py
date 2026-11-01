from __future__ import annotations

import pandas as pd
import pytest

from observatorio.metrics import (
    biggest_gains,
    coverage,
    evolution_by_region,
    evolution_national,
    municipality_history,
    ranking,
    scope,
    summary,
)


def test_scope_filters_by_network_and_year(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública", ano=2025)
    assert len(frame) == 3
    assert set(frame["rede"]) == {"Pública"}
    assert set(frame["ano"]) == {2025}


def test_scope_filters_by_uf(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública", uf="RO")
    assert set(frame["uf"]) == {"RO"}
    assert len(frame) == 4


def test_summary_ignores_missing_ideb(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública", ano=2025)
    info = summary(frame)
    assert info["n_municipios"] == 3
    assert info["media"] == pytest.approx((6.0 + 4.5 + 5.5) / 3)
    assert info["mediana"] == pytest.approx(5.5)
    assert info["abaixo_referencia"] == pytest.approx(2 / 3)
    assert info["melhor_municipio"] == "Alfa (RO)"


def test_summary_empty_frame(tiny_data: pd.DataFrame) -> None:
    info = summary(tiny_data.iloc[0:0])
    assert info["n_municipios"] == 0
    assert info["media"] is None


def test_ranking_best_and_worst(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública", ano=2025)
    best = ranking(frame, n=2, best=True)
    worst = ranking(frame, n=2, best=False)
    assert best["municipio"].tolist() == ["Alfa", "Gama"]
    assert worst["municipio"].tolist() == ["Beta", "Gama"]


def test_biggest_gains_requires_both_years(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública")
    gains = biggest_gains(frame, 2005, 2025, n=5)
    assert gains["municipio"].tolist() == ["Alfa", "Beta"]
    assert gains.iloc[0]["ganho"] == pytest.approx(2.0)
    assert gains.iloc[1]["ganho"] == pytest.approx(-0.5)


def test_evolution_by_region(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública")
    serie = evolution_by_region(frame)
    # Norte aparece em 2005 e 2025; AC e RO pertencem a regiao Norte.
    assert len(serie) == 2
    norte_2025 = serie[(serie["ano"] == 2025) & (serie["regiao"] == "Norte")]
    assert norte_2025["media"].iloc[0] == pytest.approx((6.0 + 4.5 + 5.5) / 3)


def test_evolution_national_counts(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública")
    serie = evolution_national(frame)
    assert serie.set_index("ano").loc[2005, "municipios"] == 2
    assert serie.set_index("ano").loc[2025, "municipios"] == 3


def test_municipality_history_has_reference_means(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública")
    serie = municipality_history(frame, "1100015")
    assert serie["ideb"].tolist() == [4.0, 6.0]
    assert serie["media_uf"].notna().all()
    assert serie["media_brasil"].notna().all()
    assert serie["municipio"].iloc[0] == "Alfa"


def test_municipality_history_unknown_code(tiny_data: pd.DataFrame) -> None:
    assert municipality_history(tiny_data, "9999999").empty


def test_coverage(tiny_data: pd.DataFrame) -> None:
    frame = scope(tiny_data, "Anos Iniciais", "Pública")
    table = coverage(frame)
    assert table.set_index("ano").loc[2005, "municipios_com_ideb"] == 2
    assert table.set_index("ano").loc[2025, "cobertura"] == 1.0
