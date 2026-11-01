"""Gera o dataset processado a partir das planilhas publicas do Inep.

Uso:
    python scripts/build_dataset.py
    python scripts/build_dataset.py --year 2025 --force
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.config import (  # noqa: E402
    DEFAULT_YEAR,
    PROCESSED_FILE,
    RAW_DIR,
    STAGES,
)
from observatorio.ingest import download_ideb_workbook  # noqa: E402
from observatorio.transform import build_dataset  # noqa: E402


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--year", type=int, default=DEFAULT_YEAR, help="Edicao do Ideb")
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR)
    parser.add_argument("--output", type=Path, default=PROCESSED_FILE)
    parser.add_argument(
        "--force", action="store_true", help="Baixa novamente mesmo se o arquivo existir"
    )
    return parser.parse_args()


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = parse_args()

    paths = {
        etapa: download_ideb_workbook(stage, args.year, args.raw_dir, force=args.force)
        for etapa, stage in STAGES.items()
    }
    data = build_dataset(paths)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    data.to_csv(args.output, index=False, compression="gzip")
    size_mb = args.output.stat().st_size / 1024**2

    print(f"Arquivo: {args.output}")
    print(f"Linhas: {len(data):,} | Municipios: {data['cod_municipio'].nunique():,}")
    print(f"Anos: {data['ano'].min()}-{data['ano'].max()} | Tamanho: {size_mb:.1f} MB")
    print("\nCobertura de Ideb por etapa (ultimo ano):")
    last = data[data["ano"] == args.year]
    print(last.groupby("etapa")["ideb"].agg(["count", "mean"]).round(2).to_string())


if __name__ == "__main__":
    main()
