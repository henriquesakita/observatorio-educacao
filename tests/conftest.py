from __future__ import annotations

import pandas as pd
import pytest


@pytest.fixture()
def tiny_data() -> pd.DataFrame:
    rows = [
        # municipio A: sobe de 4,0 para 6,0
        ("1100015", "Alfa", "RO", "Norte", "Anos Iniciais", "Pública", 2005, 4.0, 3.0, 0.75, 200.0, 190.0, 3.9),
        ("1100015", "Alfa", "RO", "Norte", "Anos Iniciais", "Pública", 2025, 6.0, 5.0, 0.90, 250.0, 240.0, 5.9),
        # municipio B: cai de 5,0 para 4,5
        ("1100023", "Beta", "RO", "Norte", "Anos Iniciais", "Pública", 2005, 5.0, 4.0, 0.80, 220.0, 210.0, 4.8),
        ("1100023", "Beta", "RO", "Norte", "Anos Iniciais", "Pública", 2025, 4.5, 3.5, 0.70, 230.0, 200.0, 4.4),
        # municipio C: sem dado em 2005, sobe em 2025
        ("1200013", "Gama", "AC", "Norte", "Anos Iniciais", "Pública", 2025, 5.5, 4.5, 0.85, 240.0, 220.0, 5.3),
        # mesma cidade em outra rede (nao deve entrar na rede Publica)
        ("1100015", "Alfa", "RO", "Norte", "Anos Iniciais", "Municipal", 2025, 3.0, 2.5, 0.60, 180.0, 170.0, 2.9),
    ]
    columns = [
        "cod_municipio",
        "municipio",
        "uf",
        "regiao",
        "etapa",
        "rede",
        "ano",
        "ideb",
        "taxa_aprovacao",
        "indicador_rendimento",
        "nota_matematica",
        "nota_portugues",
        "nota_media",
    ]
    frame = pd.DataFrame(rows, columns=columns)
    frame["meta"] = pd.NA
    return frame
