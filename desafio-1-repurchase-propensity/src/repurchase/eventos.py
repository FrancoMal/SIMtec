"""Agenda a nivel TURNO (schedule_id) y definición preliminar de "mantenimiento programado completado".

Hechos verificados sobre el extracto crudo (2026-09-15):
- Una fila de la agenda = un ítem de servicio dentro de un turno. 380k turnos tienen 1 ítem, 95k tienen 2,
  etc. Las columnas que varían dentro de un schedule_id son casi exclusivamente las Service* (nombre, tipo,
  precio). StatusARG/fechas/km son de nivel turno (varían en <5 casos).
- Hay 19.554 filas totalmente duplicadas -> se eliminan.
- StatusARG: (60) Concluido, (90) Concluido sin OS, (80) No asistio, (70) Cancelado, (30) Agendado, (40) En progreso.
- ServiceType == 'Mantenimiento' incluye 'N° Maintenance service' / 'Nª Maintenance review' (con
  ServiceMaintenance = número de service y ServiceMonth = 12*n) y también 'Guarantee' (garantía, NO es
  mantenimiento programado). Campañas/recalls van aparte.

Definición preliminar (a validar en el EDA): un turno es un *mantenimiento programado completado* si
StatusARG == '(60) Concluido' y al menos un ítem tiene ServiceMaintenance no nulo.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .io import load_agenda

CUTOFF = pd.Timestamp("2026-08-25")  # última fecha con eventos efectivos (checkout / survey)

APPT_LEVEL_COLS = [
    "vehicle_id", "customer_id", "dealer_id", "Region", "DealerStateOrZone", "ScheduleDate",
    "ScheduleDateTime", "StatusARG", "ScheduleSource", "IsReschedule", "ScheduleReturn",
    "ShortVehicleModelGroupTreated", "ModelYear", "TMA", "KM", "VehicleCurrentKM",
    "EffectiveCheckinDate", "EffectiveCheckoutDate", "DaysInDealer", "WorkDaysInDealer", "EffectiveTerm",
    "NeededTowing", "CustomerWaiting", "PickupDeliveryService", "MobileService", "SurveyStarRating",
    "SurveyResponseDate", "WarrantyStartDate", "ConnectedStatusARG",
]


def _first_non_null(s: pd.Series):
    idx = s.first_valid_index()
    return s.loc[idx] if idx is not None else np.nan


def appointments(agenda: pd.DataFrame | None = None) -> pd.DataFrame:
    """Colapsa la agenda a una fila por schedule_id con flags de qué ítems incluía el turno."""
    a = load_agenda() if agenda is None else agenda
    a = a.drop_duplicates()
    a = a.sort_values(["schedule_id", "ServiceMaintenance"], na_position="last")

    is_maint_item = a["ServiceMaintenance"].notna() | a["ServiceName"].fillna("").str.contains(
        r"Maintenance (?:service|review)", regex=True
    )
    st = a["ServiceType"].fillna("")
    items = pd.DataFrame({
        "schedule_id": a["schedule_id"],
        "item_maint": is_maint_item,
        "item_maint_number": a["ServiceMaintenance"].where(is_maint_item),
        "item_recall": st.str.lower().eq("campañas de servicio"),
        "item_diag": st.eq("Diagnóstico"),
        "item_repair": st.eq("Reparación"),
        "item_guarantee": a["ServiceName"].fillna("").eq("Guarantee"),
        "item_fixed_price": a["ServiceFordFixedPriceFlag"].eq("Y"),
        "item_pud": a["PickupDeliveryService"].eq("Yes"),
        "item_mobile": a["MobileService"].eq("Yes"),
    })
    agg = items.groupby("schedule_id", sort=False).agg(
        n_items=("item_maint", "size"),
        has_maint=("item_maint", "any"),
        maint_number=("item_maint_number", "min"),
        has_recall=("item_recall", "any"),
        has_diag=("item_diag", "any"),
        has_repair=("item_repair", "any"),
        has_guarantee=("item_guarantee", "any"),
        has_fixed_price=("item_fixed_price", "any"),
        has_pud=("item_pud", "any"),
        has_mobile=("item_mobile", "any"),
    )
    # Nivel turno: primera fila no nula por columna (las columnas de nivel turno no varían dentro del turno).
    head = a.groupby("schedule_id", sort=False)[APPT_LEVEL_COLS].first()
    appt = head.join(agg).reset_index()
    appt["completed"] = appt["StatusARG"].eq("(60) Concluido")
    appt["completed_no_os"] = appt["StatusARG"].eq("(90) Concluido sin OS")
    appt["no_show"] = appt["StatusARG"].eq("(80) No asistio")
    appt["cancelled"] = appt["StatusARG"].eq("(70) Cancelado")
    appt["pending"] = appt["StatusARG"].isin(["(30) Agendado", "(40) En progreso"])
    appt["is_completed_maintenance"] = appt["completed"] & appt["has_maint"]
    # Fecha efectiva del evento: check-in si existe y es coherente con el turno (hay check-ins de 2001 y
    # otros a meses de distancia del turno), si no la fecha del turno.
    gap = (appt["EffectiveCheckinDate"] - appt["ScheduleDate"]).dt.days
    checkin_ok = appt["EffectiveCheckinDate"].where(gap.between(-45, 45))
    appt["event_date"] = checkin_ok.fillna(appt["ScheduleDate"])
    return appt.sort_values(["vehicle_id", "event_date", "schedule_id"]).reset_index(drop=True)


if __name__ == "__main__":
    ap = appointments()
    print(ap.shape)
    print(ap["StatusARG"].value_counts().to_string())
    print("completed maintenance:", ap["is_completed_maintenance"].sum())
    print(ap[["n_items", "has_maint", "has_recall", "has_diag", "has_repair", "has_guarantee"]].mean().round(3).to_string())
