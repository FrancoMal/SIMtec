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



def tabla_contactos(contactos: pd.DataFrame, adicionales: bool = False) -> pd.DataFrame:
    """Conserva probabilidad y SHAP de la etapa 1 y el orden explícito de la etapa 2."""
    orden = contactos.sort_values(["orden_contacto", "customer_id", "vehicle_id"], na_position="last",
                                 kind="stable").reset_index(drop=True)
    tabla = tabla_completa(orden.assign(prioridad=range(len(orden))), adicionales)
    for campo in ("orden_contacto", "estado_contacto", "seleccionado", "en_espera", "motivos_operativos",
                  "n_vehiculos_cliente", "vehiculos_cliente", "grupos_cliente", "representante"):
        tabla[campo] = orden[campo].values
    if adicionales:
        for campo in ("shap_accionable", "vinculo_reciente"):
            tabla[campo] = orden[campo].values
        # La prioridad original no es el nuevo orden de contacto.
        tabla["prioridad"] = orden["prioridad"].values
    return tabla
