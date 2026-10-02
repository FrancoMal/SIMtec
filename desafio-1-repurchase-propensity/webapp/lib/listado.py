"""Columnas del listado completo, conservando los motivos SHAP del ranking."""
import pandas as pd


def tabla_completa(scores: pd.DataFrame, adicionales: bool = False) -> pd.DataFrame:
    columnas = {"customer_id": "customer_id", "vehicle_id": "vehicle_id", "fecha_scoring": "fecha",
                "prob_churn": "probabilidad", "segmento": "grupo", "driver_1": "motivo_SHAP_1",
                "driver_2": "motivo_SHAP_2", "driver_3": "motivo_SHAP_3"}
    if adicionales:
        columnas.update({"prioridad": "prioridad", "last_maint_dealer": "concesionario",
                         "vencimiento_estimado": "vencimiento_estimado", "cierre_horizonte": "cierre_horizonte",
                         "dias_restantes_horizonte": "dias_restantes", "tiene_turno_agendado": "turno_agendado",
                         "fecha_turno_agendado": "fecha_turno_agendado"})
        for i in (1, 2, 3):
            columnas[f"driver_{i}_feature"] = f"variable_SHAP_{i}"
            columnas[f"driver_{i}_shap"] = f"aporte_SHAP_{i}"
    tabla = scores.sort_values("prioridad")[list(columnas)].rename(columns=columnas).reset_index(drop=True)
    for c in ("fecha", "vencimiento_estimado", "cierre_horizonte", "fecha_turno_agendado"):
        if c in tabla:
            tabla[c] = pd.to_datetime(tabla[c]).dt.date
    return tabla


def filtrar(tabla: pd.DataFrame, grupo: str = "Todos", busqueda: str = "") -> pd.DataFrame:
    resultado = tabla if grupo == "Todos" else tabla[tabla["grupo"] == grupo]
    texto = busqueda.strip()
    if texto:
        resultado = resultado[resultado["customer_id"].astype("string").str.contains(texto, case=False, regex=False, na=False)
                              | resultado["vehicle_id"].astype("string").str.contains(texto, case=False, regex=False, na=False)]
    return resultado
