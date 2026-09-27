"""Capa de negocio: segmentos accionables, capacidad de contacto y ROI con supuestos explícitos.

Nada de esto es "verdad revelada": son supuestos declarados y parametrizados (config/negocio.json) para que
Ford los reemplace por sus números reales. Lo importante es la lógica: contactar a alguien vale
p(churn) × uplift × valor, y cuesta el contacto; el modelo sirve para ordenar por p(churn).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

SEGMENTOS = ["Alto", "Medio", "Bajo"]

ACCION = {
    "Alto": "Llamado del concesionario (asesor de service) dentro de las 48 h + oferta concreta (precio fijo / turno con retiro y entrega).",
    "Medio": "Recordatorio personalizado por FordPass/WhatsApp con turno sugerido y beneficio liviano; segundo toque a los 10 días si no agenda.",
    "Bajo": "Recordatorio estándar automático (Service Reminder). No gastar capacidad de contacto humano.",
}


def segmentar_por_capacidad(p: pd.Series, top_alto: float = 0.2, top_medio: float = 0.3) -> pd.Series:
    """Segmentos por ranking dentro de la población scoreada: los `top_alto` de mayor riesgo = Alto, etc."""
    r = p.rank(ascending=False, method="first") / len(p)
    seg = np.where(r <= top_alto, "Alto", np.where(r <= top_alto + top_medio, "Medio", "Bajo"))
    return pd.Series(pd.Categorical(seg, categories=SEGMENTOS), index=p.index)


def segmentar_por_umbral(p: pd.Series, umbral_alto: float, umbral_medio: float) -> pd.Series:
    seg = np.where(p >= umbral_alto, "Alto", np.where(p >= umbral_medio, "Medio", "Bajo"))
    return pd.Series(pd.Categorical(seg, categories=SEGMENTOS), index=p.index)


def resumen_segmentos(df: pd.DataFrame, seg_col: str = "segmento", y_col: str = "label_churn", p_col: str = "p") -> pd.DataFrame:
    g = df.groupby(seg_col, observed=True)
    out = g.agg(n=(p_col, "size"), p_media=(p_col, "mean"))
    if y_col in df and df[y_col].notna().any():
        out["tasa_churn"] = g[y_col].mean()
        out["churners"] = g[y_col].sum()
        out["share_churners"] = out["churners"] / df[y_col].sum()
    out["share"] = out["n"] / len(df)
    out["accion"] = [ACCION[s] for s in out.index]
    return out.reset_index().rename(columns={seg_col: "segmento"})


def umbral_rentable(valor_retencion: float, uplift: float, costo_contacto: float) -> float:
    """p mínima para que contactar tenga valor esperado positivo: p × uplift × valor > costo."""
    return costo_contacto / (uplift * valor_retencion)


def roi_por_capacidad(df: pd.DataFrame, supuestos: dict, capacidades=(0.1, 0.2, 0.3, 0.5), p_col="p",
                      y_col="label_churn") -> pd.DataFrame:
    """Compara contactar al X % de mayor score (modelo) vs. el mismo X % elegido al azar (situación actual).

    Supuestos: uplift = fracción de churners que el contacto recupera; valor_retencion = margen de un
    mantenimiento + valor futuro atribuible (repuestos, siguiente service, lealtad); costo_contacto por
    contacto humano. Se usan los churners OBSERVADOS en test para no depender de la calibración.
    """
    u = supuestos["uplift_contacto"]; v = supuestos["valor_retencion_usd"]; c = supuestos["costo_contacto_usd"]
    d = df[[p_col, y_col]].dropna().sort_values(p_col, ascending=False).reset_index(drop=True)
    total_churn = d[y_col].sum(); base = d[y_col].mean()
    rows = []
    for cap in capacidades:
        k = int(round(cap * len(d)))
        churn_modelo = d.iloc[:k][y_col].sum()
        churn_azar = base * k
        rec_modelo = churn_modelo * u * v; rec_azar = churn_azar * u * v; costo = k * c
        rows.append({
            "capacidad_pct": cap, "contactos": k,
            "churners_alcanzados_modelo": int(churn_modelo), "churners_alcanzados_azar": round(churn_azar),
            "recall_modelo": churn_modelo / total_churn, "recall_azar": churn_azar / total_churn,
            "services_recuperados_modelo": churn_modelo * u, "services_recuperados_azar": churn_azar * u,
            "valor_modelo_usd": rec_modelo, "valor_azar_usd": rec_azar, "costo_contacto_usd": costo,
            "beneficio_neto_modelo_usd": rec_modelo - costo, "beneficio_neto_azar_usd": rec_azar - costo,
            "ganancia_incremental_usd": rec_modelo - rec_azar,
            "roi_modelo": (rec_modelo - costo) / costo if costo else np.nan,
        })
    return pd.DataFrame(rows)


def sensibilidad_roi(df: pd.DataFrame, supuestos: dict, capacidad: float = 0.2,
                     uplifts=(0.05, 0.10, 0.15, 0.25), valores=(100, 200, 300, 500)) -> pd.DataFrame:
    rows = []
    for u in uplifts:
        for v in valores:
            s = {**supuestos, "uplift_contacto": u, "valor_retencion_usd": v}
            r = roi_por_capacidad(df, s, capacidades=(capacidad,)).iloc[0]
            rows.append({"uplift": u, "valor_retencion_usd": v, "ganancia_incremental_usd": r["ganancia_incremental_usd"],
                         "beneficio_neto_modelo_usd": r["beneficio_neto_modelo_usd"], "roi_modelo": r["roi_modelo"]})
    return pd.DataFrame(rows)
