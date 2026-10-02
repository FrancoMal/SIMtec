"""Cifras clave del modelo, leídas de las salidas ya generadas (no se calcula nada)."""
from __future__ import annotations

import json
import re

from lib.fuentes import csv, rutas, texto


def kpis() -> dict:
    r = rutas()
    cap = csv(r["models"] / "capacidad_LightGBM_calibrado.csv")
    met = csv(r["models"] / "metricas_test.csv").set_index("modelo")
    lift = csv(r["models"] / "lift_LightGBM_calibrado.csv")
    info = json.loads(texto(r["models"] / "info.json"))
    c20 = cap[cap["capacidad_pct"].round(2) == 0.2].iloc[0]
    resumen = texto(r["modelo"] / "resumen.md")
    m = re.search(r"([\d,]+) contactos/mes → recall ([\d.]+)%", resumen)
    corrida = re.search(r"Corrida: ([\d\- :]+)", resumen)
    return {
        "base": float(info["base_rate_test"]),
        "prec20": float(c20["precision"]), "recall20": float(c20["recall"]), "lift20": float(c20["lift"]),
        "contactos_mes": int(m.group(1).replace(",", "")) if m else None,
        "recall_mes": float(m.group(2)) / 100 if m else None,
        "auc": float(met.loc["LightGBM calibrado (isotónica)", "roc_auc"]),
        "auc_azar": float(met.loc["azar (prioridad uniforme, situación actual)", "roc_auc"]),
        "ece": float(met.loc["LightGBM calibrado (isotónica)", "ece"]),
        "decil1": float(lift.iloc[0]["tasa"]),
        "n_test": int(info["n_test"]), "train_end": info["split"]["train_end"],
        "test_desde": info["test_scoring_range"][0], "test_hasta": info["test_scoring_range"][1],
        "corrida": corrida.group(1).strip() if corrida else "",
    }
