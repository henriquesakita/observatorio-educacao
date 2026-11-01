"""Download dos arquivos publicos do Ideb municipal (Inep)."""

from __future__ import annotations

import logging
import time
import urllib.request
import zipfile
from pathlib import Path

from .config import RAW_DIR

logger = logging.getLogger(__name__)

BASE_URL = "https://download.inep.gov.br/ideb/resultados"
ARCHIVE_TEMPLATE = "divulgacao_{stage}_municipios_{year}.zip"
XLSX_TEMPLATE = "divulgacao_{stage}_municipios_{year}.xlsx"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"
)
MAX_ATTEMPTS = 3
CHUNK_SIZE = 1024 * 1024


def _download(url: str, destination: Path) -> None:
    """Baixa um arquivo com User-Agent de navegador e tentativas extras.

    O servidor do Inep derruba conexoes sem User-Agent e, as vezes, sob carga.
    """
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                with open(destination, "wb") as target:
                    while chunk := response.read(CHUNK_SIZE):
                        target.write(chunk)
            return
        except Exception:
            destination.unlink(missing_ok=True)
            if attempt == MAX_ATTEMPTS:
                raise
            logger.warning("Falha no download (tentativa %s/%s). Retentando...", attempt, MAX_ATTEMPTS)
            time.sleep(2 * attempt)


def archive_url(stage_key: str, year: int) -> str:
    """Monta a URL do ZIP oficial de resultados por municipio."""
    return f"{BASE_URL}/{ARCHIVE_TEMPLATE.format(stage=stage_key, year=year)}"


def download_ideb_workbook(
    stage_key: str,
    year: int,
    dest_dir: Path | None = None,
    force: bool = False,
) -> Path:
    """Baixa e extrai a planilha do Ideb, devolvendo o caminho do .xlsx.

    O download e idempotente: se a planilha ja existe, nada e baixado.
    """
    dest_dir = Path(dest_dir or RAW_DIR)
    dest_dir.mkdir(parents=True, exist_ok=True)
    xlsx_path = dest_dir / XLSX_TEMPLATE.format(stage=stage_key, year=year)

    if xlsx_path.exists() and not force:
        logger.info("Planilha ja existe: %s", xlsx_path)
        return xlsx_path

    url = archive_url(stage_key, year)
    zip_path = dest_dir / ARCHIVE_TEMPLATE.format(stage=stage_key, year=year)
    logger.info("Baixando %s", url)
    _download(url, zip_path)

    with zipfile.ZipFile(zip_path) as archive:
        member = next(
            (
                name
                for name in archive.namelist()
                if name.endswith(".xlsx") and "municipios" in name
            ),
            None,
        )
        if member is None:
            raise FileNotFoundError(f"Nenhum .xlsx encontrado em {zip_path}")

        with archive.open(member) as source, open(xlsx_path, "wb") as target:
            target.write(source.read())

    zip_path.unlink(missing_ok=True)
    logger.info("Planilha salva em %s", xlsx_path)
    return xlsx_path
