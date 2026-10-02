"""Rutas y constantes compartidas. Los datos crudos son SOLO LECTURA (carpeta compartida)."""
import os
from pathlib import Path


def _raw_dir() -> Path:
    """Carpeta de crudos: $SIMTEC_DATASET si está; si no, el Dataset/ versionado del propio repo (lo que trae un clon,
    vía Git LFS); y recién después G:\\SIMtec\\Dataset, la carpeta compartida original."""
    if os.environ.get("SIMTEC_DATASET"):
        return Path(os.environ["SIMTEC_DATASET"])
    candidatas = (Path(__file__).resolve().parents[3] / "Dataset", Path(r"G:\SIMtec\Dataset"))
    for d in candidatas:
        if _tiene_datos(d):
            return d
    # ninguna tiene los datos: se devuelve la del repo para que el error diga dónde se los buscó
    return candidatas[0]


def _tiene_datos(d: Path) -> bool:
    """True si la carpeta tiene los dos CSV con datos reales. Un clon sin Git LFS trae punteros de ~130 bytes
    ("version https://git-lfs..."): esa carpeta no sirve y hay que seguir buscando."""
    for nombre in (_SALES, _AGENDA):
        p = d / nombre
        if not p.is_file() or p.stat().st_size < 1024:
            return False
    return True


_SALES = "ranger_sales_arg_2024_2026.csv"
_AGENDA = "ranger_service_agenda_arg_2024_2026 1.csv"  # con " 1": es el nombre con el que está en git


# Carpeta compartida de datos crudos: NUNCA escribir acá.
RAW_DIR = _raw_dir()
RAW_SALES = RAW_DIR / _SALES
RAW_AGENDA = RAW_DIR / _AGENDA

# Carpeta del proyecto (todo lo generado vive acá; data/ está en .gitignore).
PROJECT_DIR = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(os.environ.get("SIMTEC_OUTPUT_DIR", PROJECT_DIR)).resolve()
DATA_DIR = OUTPUT_DIR / "data"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = OUTPUT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = DATA_DIR / "models"

SALES_PARQUET = INTERIM_DIR / "sales.parquet"
AGENDA_PARQUET = INTERIM_DIR / "agenda.parquet"

for _d in (INTERIM_DIR, PROCESSED_DIR, FIGURES_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
