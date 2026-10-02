"""Transformaciones de evidencia del modelo, sin mezclar datasets ni inventar métricas."""
from __future__ import annotations

from datetime import datetime
import math

import pandas as pd


MODELO_PRINCIPAL = "LightGBM calibrado (isotónica)"


def fila_modelo(metricas: pd.DataFrame) -> dict:
    if "modelo" not in metricas:
        return {}
    filas = metricas[metricas["modelo"].eq(MODELO_PRINCIPAL)]
    return filas.iloc[0].to_dict() if len(filas) else {}


def duracion(segundos) -> str:
    try:
        s = float(segundos)
    except (TypeError, ValueError):
        return "Sin registro"
    if not math.isfinite(s) or s < 0:
        return "Sin registro"
    if s < 60:
        return f"{s:.1f} s".replace(".", ",")
    minutos, resto = divmod(round(s), 60)
    if minutos < 60:
        return f"{minutos} min {resto:02d} s"
    horas, minutos = divmod(minutos, 60)
    return f"{horas} h {minutos:02d} min"


def telemetria_del_modelo(tiempos: dict, modelo_mtime: float) -> bool:
    """El modelo tiene que haberse escrito dentro de esta corrida completa."""
    if tiempos.get("estado") != "completo":
        return False
    try:
        inicio = datetime.fromisoformat(tiempos["inicio"]).timestamp()
        fin = datetime.fromisoformat(tiempos["fin"]).timestamp()
    except (KeyError, TypeError, ValueError):
        return False
    return inicio - 1 <= modelo_mtime <= fin + 1


def tabla_shap(globales: pd.DataFrame) -> pd.DataFrame:
    """Usa la magnitud exacta en log-odds, nunca el proxy en puntos porcentuales."""
    if not {"feature", "mean_abs_shap_logodds"}.issubset(globales.columns):
        return pd.DataFrame(columns=["Variable", "Código", "SHAP absoluto medio"])
    tabla = globales.copy()
    tabla["SHAP absoluto medio"] = pd.to_numeric(tabla["mean_abs_shap_logodds"], errors="coerce")
    tabla["Variable"] = tabla["nombre"].fillna(tabla["feature"]) if "nombre" in tabla else tabla["feature"]
    tabla["Código"] = tabla["feature"]
    return (tabla[["Variable", "Código", "SHAP absoluto medio"]]
            .dropna(subset=["SHAP absoluto medio"])
            .sort_values("SHAP absoluto medio", ascending=False, kind="stable").reset_index(drop=True))


def soporte_temporal(info: dict) -> pd.DataFrame:
    split = info.get("split", {})
    test = info.get("test_scoring_range", [])
    def siguiente(valor):
        fecha = pd.to_datetime(valor, errors="coerce")
        return (fecha + pd.Timedelta(days=1)).strftime("%d/%m/%Y") if pd.notna(fecha) else "Sin registro"
    def fecha(valor):
        f = pd.to_datetime(valor, errors="coerce")
        return f.strftime("%d/%m/%Y") if pd.notna(f) else "Sin registro"
    return pd.DataFrame([
        {"Período": "Entrenamiento", "Fechas de scoring": f"Hasta {fecha(split.get('train_end'))}",
         "Ventanas": info.get("n_train"), "Tasa de abandono": info.get("base_rate_train")},
        {"Período": "Validación y calibración",
         "Fechas de scoring": f"{siguiente(split.get('train_end'))} a {fecha(split.get('valid_end'))}",
         "Ventanas": info.get("n_valid"), "Tasa de abandono": info.get("base_rate_valid")},
        {"Período": "Test",
         "Fechas de scoring": f"{fecha(test[0])} a {fecha(test[1])}" if len(test) == 2 else "Sin registro",
         "Ventanas": info.get("n_test"), "Tasa de abandono": info.get("base_rate_test")},
    ])


def cruces_horizonte(ventanas: pd.DataFrame, info: dict) -> pd.DataFrame:
    """Audita ventanas que cruzan cortes; no equivale a medir sesgo causal o leakage total."""
    columnas = ["Corte", "Ventanas del período", "Horizontes que cruzan", "Proporción"]
    if not {"status", "scoring_date", "horizon_end"}.issubset(ventanas):
        return pd.DataFrame(columns=columnas)
    evaluables = ventanas[ventanas.status.eq("evaluable")]
    scoring = pd.to_datetime(evaluables.scoring_date, errors="coerce")
    horizonte = pd.to_datetime(evaluables.horizon_end, errors="coerce")
    split = info.get("split", {})
    train = pd.to_datetime(split.get("train_end"), errors="coerce")
    valid = pd.to_datetime(split.get("valid_end"), errors="coerce")
    if pd.isna(train) or pd.isna(valid):
        return pd.DataFrame(columns=columnas)
    rows = []
    for etiqueta, fecha, mascara in [("Entrenamiento / validación", train, scoring.le(train)),
                                     ("Validación / test", valid, scoring.gt(train) & scoring.le(valid))]:
        n = int(mascara.sum())
        cruces = int((mascara & horizonte.gt(fecha)).sum())
        rows.append({"Corte": etiqueta, "Ventanas del período": n, "Horizontes que cruzan": cruces,
                     "Proporción": cruces / n if n else None})
    return pd.DataFrame(rows, columns=columnas)
