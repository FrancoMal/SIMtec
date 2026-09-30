"""Rutas y constantes compartidas. Los datos crudos son SOLO LECTURA (carpeta compartida)."""
import os
from pathlib import Path


def _raw_dir() -> Path:
    """Carpeta de crudos: $SIMTEC_DATASET si está, si no G:\\SIMtec\\Dataset (Windows) o <repo>/Dataset."""
    if os.environ.get("SIMTEC_DATASET"):
        return Path(os.environ["SIMTEC_DATASET"])
    for d in (Path(r"G:\SIMtec\Dataset"), Path(__file__).resolve().parents[3] / "Dataset"):
        if d.is_dir():
            return d
    return Path(r"G:\SIMtec\Dataset")


# Carpeta compartida de datos crudos: NUNCA escribir acá.
RAW_DIR = _raw_dir()
RAW_SALES = RAW_DIR / "ranger_sales_arg_2024_2026.csv"
RAW_AGENDA = RAW_DIR / "ranger_service_agenda_arg_2024_2026 1.csv"

# Carpeta del proyecto (todo lo generado vive acá; data/ está en .gitignore).
PROJECT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_DIR / "data"
INTERIM_DIR = DATA_DIR / "interim"
PROCESSED_DIR = DATA_DIR / "processed"
REPORTS_DIR = PROJECT_DIR / "reports"
FIGURES_DIR = REPORTS_DIR / "figures"
MODELS_DIR = DATA_DIR / "models"

SALES_PARQUET = INTERIM_DIR / "sales.parquet"
AGENDA_PARQUET = INTERIM_DIR / "agenda.parquet"

for _d in (INTERIM_DIR, PROCESSED_DIR, FIGURES_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)
