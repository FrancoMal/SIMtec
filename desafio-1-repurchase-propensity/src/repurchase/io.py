"""Carga de los extractos crudos de Ford (CSV) y conversión a parquet tipado.

Decisiones:
- Se lee TODO como string primero y se tipa explícitamente: los CSV mezclan formatos de fecha
  (``YYYY-MM-DD`` y ``YYYY-MM-DD HH:MM:SS+00:00``) y hay códigos numéricos que son categorías
  (Region, DealerStateOrZone). Tipar a ciegas con pandas pierde información.
- Las fechas se normalizan a ``datetime64[ns]`` naive (todo viene en UTC 00:00, la zona no aporta).
- Se descartan las columnas 100% nulas (SalesType, ScheduleModalityCode, CancellationReason,
  Quicklane), documentándolo: no aportan y confunden.
- ModelName se strippea (viene con espacios de relleno a la derecha).
"""
from __future__ import annotations

import pandas as pd

from . import config

SALES_DATE_COLS = ["SalesDate", "DeliveryDate", "RegistrationDate", "WarrantyStartDate"]
AGENDA_DATE_COLS = [
    "ScheduleDate", "ScheduleDateTime", "EffectiveCheckinDate", "EffectiveCheckoutDate",
    "SurveyResponseDate", "WarrantyStartDate",
]
AGENDA_NUM_COLS = [
    "ScheduleTime", "ModelYear", "KM", "VehicleCurrentKM", "DaysInDealer", "WorkDaysInDealer",
    "EffectiveTerm", "ServiceMaintenance", "ServiceMonth", "ServiceDuration", "ServiceLaborCost",
    "ServiceFordFixedPrice", "ServicePriceDiscount", "SurveyStarRating",
]
ALL_NULL_COLS = {"SalesType", "ScheduleModalityCode", "CancellationReason", "Quicklane"}


def _read_raw(path) -> pd.DataFrame:
    return pd.read_csv(path, dtype=str, encoding="utf-8-sig", engine="pyarrow")


def _to_datetime(s: pd.Series) -> pd.Series:
    # Mezcla de 'YYYY-MM-DD' y 'YYYY-MM-DD HH:MM:SS+00:00' -> parseo por formato mixto.
    out = pd.to_datetime(s, errors="coerce", utc=True, format="mixed")
    return out.dt.tz_localize(None)


def load_sales_raw() -> pd.DataFrame:
    df = _read_raw(config.RAW_SALES)
    df = df.drop(columns=[c for c in df.columns if c in ALL_NULL_COLS])
    for c in SALES_DATE_COLS:
        df[c] = _to_datetime(df[c])
    df["ModelYear"] = pd.to_numeric(df["ModelYear"], errors="coerce").astype("Int64")
    df["ModelName"] = df["ModelName"].str.strip()
    return df


def load_agenda_raw() -> pd.DataFrame:
    df = _read_raw(config.RAW_AGENDA)
    df = df.drop(columns=[c for c in df.columns if c in ALL_NULL_COLS])
    for c in AGENDA_DATE_COLS:
        df[c] = _to_datetime(df[c])
    for c in AGENDA_NUM_COLS:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    for c in ["ServiceName", "ServiceType", "VehicleModelGroup", "ShortVehicleModelGroupTreated"]:
        df[c] = df[c].str.strip()
    return df


def build_interim(force: bool = False) -> None:
    """CSV crudo -> parquet tipado en data/interim (idempotente)."""
    if force or not config.SALES_PARQUET.exists():
        load_sales_raw().to_parquet(config.SALES_PARQUET, index=False)
    if force or not config.AGENDA_PARQUET.exists():
        load_agenda_raw().to_parquet(config.AGENDA_PARQUET, index=False)


def load_sales() -> pd.DataFrame:
    build_interim()
    return pd.read_parquet(config.SALES_PARQUET)


def load_agenda() -> pd.DataFrame:
    build_interim()
    return pd.read_parquet(config.AGENDA_PARQUET)


if __name__ == "__main__":
    build_interim(force=True)
    s, a = load_sales(), load_agenda()
    print("sales", s.shape, "agenda", a.shape)
    print(s.dtypes.to_string()); print(a.dtypes.to_string())
