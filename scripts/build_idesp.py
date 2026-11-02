"""Gera os datasets do IDESP e do Saresp a partir das planilhas da Seduc-SP.

Uso:
    python scripts/build_idesp.py
    python scripts/build_idesp.py --force
"""

from __future__ import annotations

import argparse
import logging
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from observatorio.config import (  # noqa: E402
    IDESP_METAS_FILE,
    IDESP_PROCESSED_FILE,
    RAW_DIR,
    SARESP_PROCESSED_FILE,
)
from observatorio.idesp import (  # noqa: E402
    IDESP_HISTORY_URL,
    IDESP_META_URLS,
    IDESP_RECENT_URLS,
    SARESP_URLS,
    build_idesp,
    build_metas,
    build_saresp,
    load_municipality_reference,
    read_csv_flexible,
)
from observatorio.ingest import _download  # noqa: E402

logger = logging.getLogger(__name__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=Path, default=RAW_DIR / "idesp")
    parser.add_argument("--idesp-output", type=Path, default=IDESP_PROCESSED_FILE)
    parser.add_argument("--metas-output", type=Path, default=IDESP_METAS_FILE)
    parser.add_argument("--saresp-output", type=Path, default=SARESP_PROCESSED_FILE)
    parser.add_argument(
        "--force", action="store_true", help="Baixa novamente mesmo se o arquivo existir"
    )
    return parser.parse_args()


def fetch(url: str, raw_dir: Path, force: bool = False) -> Path:
    """Baixa um CSV do portal da Seduc, reaproveitando o arquivo local."""
    raw_dir.mkdir(parents=True, exist_ok=True)
    name = urllib.parse.unquote(url.rsplit("/", 1)[-1])
    destination = raw_dir / name
    if destination.exists() and not force:
        logger.info("Arquivo ja existe: %s", destination.name)
        return destination
    logger.info("Baixando %s", name)
    _download(url, destination)
    return destination


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    args = parse_args()
    raw_dir = args.raw_dir

    reference = load_municipality_reference()

    history = read_csv_flexible(fetch(IDESP_HISTORY_URL, raw_dir, args.force))
    recent = {
        year: read_csv_flexible(fetch(url, raw_dir, args.force))
        for year, url in IDESP_RECENT_URLS.items()
    }
    idesp = build_idesp(history, recent, reference)

    metas = build_metas(
        {
            year: read_csv_flexible(fetch(url, raw_dir, args.force))
            for year, url in IDESP_META_URLS.items()
        }
    )

    saresp = build_saresp(
        {
            year: read_csv_flexible(fetch(url, raw_dir, args.force))
            for year, url in SARESP_URLS.items()
        },
        reference,
    )

    for path, data in (
        (args.idesp_output, idesp),
        (args.metas_output, metas),
        (args.saresp_output, saresp),
    ):
        path.parent.mkdir(parents=True, exist_ok=True)
        data.to_csv(path, index=False, compression="gzip")
        size_mb = path.stat().st_size / 1024**2
        print(f"Arquivo: {path} | {len(data):,} linhas | {size_mb:.1f} MB")

    print("\nIDESP por etapa e ano:")
    print(idesp.groupby(["etapa", "ano"])["idesp"].count().unstack().to_string())
    print("\nMetas por etapa e ano:")
    print(metas.groupby(["etapa", "ano"])["meta"].count().unstack().to_string())
    print("\nSaresp por componente e ano:")
    print(saresp.groupby(["componente", "ano"])["medprof"].count().unstack().to_string())


if __name__ == "__main__":
    main()
