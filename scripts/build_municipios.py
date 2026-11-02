"""Gera a tabela de referencia dos municipios paulistas (IBGE).

Uso:
    python scripts/build_municipios.py
"""

from __future__ import annotations

import gzip
import json
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.idesp import IDESP_REFERENCE_FILE  # noqa: E402

URL = "https://servicodados.ibge.gov.br/api/v1/localidades/estados/SP/municipios"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)


def fetch_municipalities() -> list[dict[str, str]]:
    """Baixa a lista oficial de municipios de SP direto da API do IBGE."""
    request = urllib.request.Request(URL, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(request, timeout=60) as response:
        body = response.read()
    if body[:2] == b"\x1f\x8b":
        body = gzip.decompress(body)
    payload = json.loads(body.decode("utf-8"))

    rows = [
        {
            "cod_municipio": str(item["id"]).zfill(7),
            "municipio": item["nome"].strip(),
        }
        for item in payload
    ]
    return sorted(rows, key=lambda row: row["cod_municipio"])


def main() -> None:
    rows = fetch_municipalities()
    if len(rows) != 645:
        raise SystemExit(f"Esperados 645 municipios em SP, encontrados {len(rows)}.")

    IDESP_REFERENCE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with IDESP_REFERENCE_FILE.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write("cod_municipio,municipio\n")
        for row in rows:
            handle.write(f"{row['cod_municipio']},{row['municipio']}\n")

    print(f"Arquivo: {IDESP_REFERENCE_FILE} | {len(rows)} municipios")


if __name__ == "__main__":
    main()
