"""Explicabilidad: SHAP global (qué pesa) y local (por qué ESTE vehículo), con drivers en castellano."""
from __future__ import annotations

import numpy as np
import pandas as pd
import shap

NOMBRES = {
    "days_since_last_maint": "días desde el último mantenimiento",
    "days_since_last_appt": "días desde el último turno (cualquier tipo)",
    "days_since_last_visit": "días desde la última visita concluida",
    "days_since_last_noshow": "días desde el último no-show",
    "days_since_last_cancel": "días desde la última cancelación",
    "days_since_last_km": "días desde la última lectura de km",
    "days_since_last_survey": "días desde la última encuesta",
    "n_maint": "mantenimientos completados (historia observable)",
    "n_completed": "visitas concluidas (cualquier tipo)",
    "n_no_os": "turnos concluidos sin orden de servicio",
    "n_noshow": "no-shows previos",
    "n_cancel": "cancelaciones previas",
    "n_appts": "turnos previos (todos)",
    "n_recall": "recalls / campañas atendidas",
    "n_diag": "diagnósticos previos",
    "n_repair": "reparaciones previas",
    "n_guarantee": "servicios en garantía previos",
    "n_fordpass": "turnos por FordPass",
    "n_web_or_app": "turnos por canales digitales",
    "n_pud": "servicios con retiro y entrega",
    "n_mobile": "servicios móviles",
    "n_fixed_price": "servicios a precio fijo Ford",
    "n_reschedule": "reprogramaciones",
    "n_hard_cancel": "cancelaciones duras (sin reprogramar)",
    "n_return_visits": "visitas de retorno por el mismo problema",
    "n_towing": "remolques",
    "n_customer_changes": "cambios de cliente del vehículo",
    "n_dealer_changes": "cambios de concesionario",
    "last_status": "estado del último turno",
    "last_source": "canal del último turno",
    "last_dealer_zone": "zona del último concesionario",
    "last_days_in_dealer": "días en taller (último turno)",
    "last_maint_km": "km en el último mantenimiento",
    "last_maint_number": "n° del último service del plan",
    "last_maint_source": "canal del último mantenimiento",
    "last_maint_dealer": "concesionario del último mantenimiento",
    "last_maint_days_in_dealer": "días en taller (último mantenimiento)",
    "last_maint_fixed_price": "último mantenimiento a precio fijo",
    "last_maint_pud": "último mantenimiento con retiro y entrega",
    "last_maint_customer_waiting": "cliente esperó en el concesionario",
    "last_interval_days": "días entre los dos últimos mantenimientos",
    "last_interval_km": "km entre los dos últimos mantenimientos",
    "mean_interval_days": "intervalo medio entre mantenimientos",
    "std_interval_days": "regularidad (desvío del intervalo)",
    "n_intervals_known": "intervalos conocidos",
    "last_km": "último km registrado",
    "n_surveys": "encuestas respondidas",
    "min_rating": "peor calificación en encuestas",
    "last_rating": "última calificación (1-5)",
    "mean_rating": "calificación media",
    "generation": "generación (P375 / P703)",
    "model_year": "año modelo",
    "tma": "versión (TMA)",
    "connected_status": "estado de conectividad",
    "region": "región",
    "in_sales": "vendido 2024-2026 (en base de ventas)",
    "person_type": "tipo de persona (F/J)",
    "business_unit": "unidad de negocio (Blue/Pro)",
    "sales_channel": "canal de venta",
    "sales_state": "provincia de venta",
    "vehicle_age_days": "antigüedad del vehículo (días)",
    "vehicle_age_years": "antigüedad del vehículo (años)",
    "is_buyer": "el cliente actual es el comprador",
    "same_dealer_as_sale": "mismo concesionario que la venta",
    "months_observable": "meses de historia observable",
    "fleet_size_sales": "tamaño de flota (compras 2024-26)",
    "n_vehicles_customer_agenda": "vehículos del cliente vistos en agenda",
    "anchor_km": "km al inicio de la ventana",
    "km_rate_per_day": "uso (km/día)",
    "km_per_year": "uso (km/año)",
    "km_expected_at_scoring": "km estimados al scoring",
    "days_anchor_to_due": "días del último service al vencimiento",
    "binding_rule": "qué regla vence primero (km/tiempo)",
    "anchor_type": "tipo de ancla (1er service / siguiente)",
    "last_maint_late_days": "atraso del último intervalo vs. 12 meses",
    "noshow_rate": "tasa de no-show",
    "cancel_rate": "tasa de cancelación",
    "fordpass_share": "proporción de turnos por FordPass",
    "maint_per_year_observed": "mantenimientos por año observados",
    "scoring_month": "mes del scoring",
    "is_first_service": "es el primer service del vehículo",
    "k_gen": "intervalo del plan (km) según generación",
    "rate_source": "origen de la tasa de uso (individual / generación)",
    "last_maint_km_vs_plan": "km de atraso del último service vs. plan nominal",
    "last_interval_km_vs_k": "último intervalo en km relativo al plan",
    "days_to_due_at_scoring": "días hasta el vencimiento al scoring",
    "n_numbering_jumps": "services salteados (hechos fuera de la red)",
}


AGENDA_STATIC = {"tma", "region", "generation", "model_year", "last_maint_dealer", "last_dealer_zone", "last_source",
                 "last_status", "last_maint_source", "last_km", "last_maint_km", "km_rate_per_day", "km_per_year",
                 "last_maint_number", "days_since_last_maint", "days_since_last_appt", "days_since_last_visit"}


def nombre(f: str) -> str:
    return NOMBRES.get(f, f)


def shap_values(booster, X: pd.DataFrame) -> np.ndarray:
    expl = shap.TreeExplainer(booster)
    sv = expl.shap_values(X)
    if isinstance(sv, list):  # versiones viejas devuelven [neg, pos]
        sv = sv[1]
    return np.asarray(sv)


def global_importance(sv: np.ndarray, X: pd.DataFrame) -> pd.DataFrame:
    # En log-odds; se convierte a "puntos porcentuales aproximados" alrededor del promedio para comunicar.
    mean_abs = np.abs(sv).mean(axis=0)
    df = pd.DataFrame({"feature": X.columns, "mean_abs_shap_logodds": mean_abs})
    df["nombre"] = df["feature"].map(nombre)
    df["mean_abs_shap"] = df["mean_abs_shap_logodds"] * 25  # ≈ dp/dlogodds en p=0.5 (0.25) × 100 pp
    return df.sort_values("mean_abs_shap", ascending=False).reset_index(drop=True)


def _fmt_value(v) -> str:
    if v is None or (isinstance(v, float) and np.isnan(v)):
        return "sin dato"
    if isinstance(v, (int, np.integer)):
        return f"{int(v)}"
    if isinstance(v, (float, np.floating)):
        return f"{v:,.0f}" if abs(v) >= 100 else f"{v:.2f}".rstrip("0").rstrip(".")
    return str(v)


def local_drivers(sv: np.ndarray, X: pd.DataFrame, top: int = 3) -> pd.DataFrame:
    """Por fila: los `top` drivers con mayor |SHAP|, como texto legible + columnas separadas."""
    cols = list(X.columns)
    out = {f"driver_{i+1}": [] for i in range(top)}
    out.update({f"driver_{i+1}_feature": [] for i in range(top)})
    out.update({f"driver_{i+1}_shap": [] for i in range(top)})
    absv = np.abs(sv)
    order = np.argsort(-absv, axis=1)[:, :top]
    Xv = X.to_numpy(dtype=object)
    for r in range(sv.shape[0]):
        for i in range(top):
            j = order[r, i]
            val = Xv[r, j]
            s = sv[r, j]
            direction = "↑ riesgo" if s > 0 else "↓ riesgo"
            txt = _fmt_value(val)
            if txt == "sin dato":
                # Un valor faltante de una feature de la agenda significa que el vehículo nunca pasó por la red
                # (o no tiene esa lectura): decirlo en lenguaje de negocio, no como "NaN".
                txt = "sin registro en la red" if cols[j] in AGENDA_STATIC else "sin dato"
            out[f"driver_{i+1}"].append(f"{nombre(cols[j])} = {txt} ({direction})")
            out[f"driver_{i+1}_feature"].append(cols[j])
            out[f"driver_{i+1}_shap"].append(float(s))
    return pd.DataFrame(out, index=X.index)
