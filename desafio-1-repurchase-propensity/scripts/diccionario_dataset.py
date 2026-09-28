"""Genera docs/diccionario_dataset_analitico.md: documentación columna por columna del dataset analítico
(data/processed/dataset_analitico.parquet) y del ranking (data/processed/scores_actuales.csv).

Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/diccionario_dataset.py
"""
from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from repurchase import explicabilidad as ex
from repurchase import features as ft

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "data" / "processed" / "dataset_analitico.parquet"
SC = ROOT / "data" / "processed" / "scores_actuales.csv"
OUT = ROOT / "docs" / "diccionario_dataset_analitico.md"
PARAMS = json.loads((ROOT / "config" / "params.json").read_text(encoding="utf8"))

# Columnas que no son features: identificadores, geometría de la ventana y etiquetas.
FIJAS = {
    "window_id": ("identificador", "id único de la ventana (vehículo + número de ventana)"),
    "vehicle_id": ("identificador", "id seudonimizado del vehículo (VIN hasheado)"),
    "customer_id": ("identificador", "cliente vigente del vehículo al momento del scoring (último turno anterior); nulo si no hay"),
    "window_n": ("identificador", "número de orden de la ventana dentro del vehículo"),
    "scoring_date": ("geometría", "fecha de scoring = apertura de la ventana (vencimiento − 30 días); ninguna feature usa datos posteriores"),
    "anchor_date": ("geometría", "fecha del ancla: último mantenimiento programado completado o inicio de garantía (primer service)"),
    "due_date": ("geometría", "vencimiento estimado = ancla + min(365 días, K_gen / tasa de uso); primer service: garantía + 300 días"),
    "due_time": ("geometría", "vencimiento que daría sólo la regla de tiempo (ancla + 365 días)"),
    "due_km": ("geometría", "vencimiento que daría sólo la regla de kilómetros (ancla + K_gen / tasa de uso)"),
    "history_days": ("geometría", "días de historia observable del vehículo en la agenda antes del scoring"),
    "warranty_start": ("identificador", "inicio de garantía (fecha de entrega); fallback DeliveryDate de ventas"),
    "sales_customer_id": ("identificador", "comprador según la base de ventas (nulo si el vehículo no se vendió en 2024-26)"),
    "sales_dealer_id": ("identificador", "concesionario de la venta"),
    "SalesDate": ("identificador", "fecha de venta"),
    "last_dealer_id": ("identificador", "concesionario del último turno anterior al scoring"),
    "label_churn": ("etiqueta", "TARGET: 1 si no hubo mantenimiento programado completado entre la apertura y el cierre del horizonte (vencimiento + 90 días); 0 si lo hubo"),
    "label_no_visit": ("etiqueta", "etiqueta secundaria: 1 si no hubo ninguna visita concluida a la red en el horizonte"),
    "status": ("etiqueta", "estado de la ventana: evaluable (etiquetada), censurada (horizonte abierto al corte), preempted, fuera_de_rango, futura"),
}
GRUPOS = [
    ("recencia", lambda c: c.startswith("days_since_")),
    ("frecuencia e intensidad", lambda c: c.startswith("n_") or c.endswith("_rate") or c in {"fordpass_share", "maint_per_year_observed"}),
    ("último turno / último mantenimiento", lambda c: c.startswith("last_") and c not in {"last_km"}),
    ("intervalos entre mantenimientos", lambda c: "interval" in c),
    ("encuestas", lambda c: "rating" in c or c == "n_surveys"),
    ("uso y kilometraje", lambda c: "km" in c),
    ("ciclo de vida", lambda c: c in {"generation", "model_year", "tma", "vehicle_age_days", "vehicle_age_years", "is_first_service", "months_observable", "k_gen"}),
    ("venta y cliente", lambda c: c in {"in_sales", "person_type", "business_unit", "sales_channel", "sales_state", "is_buyer", "same_dealer_as_sale", "fleet_size_sales", "n_vehicles_customer_agenda", "connected_status", "region"}),
    ("geometría de la ventana", lambda c: c in {"binding_rule", "anchor_type", "days_anchor_to_due", "days_to_due_at_scoring", "rate_source", "scoring_month"}),
]


def n(x: int) -> str:
    return f"{x:,}".replace(",", ".")


def pct(x: float) -> str:
    return f"{100 * x:.1f} %".replace(".", ",")


def grupo(c: str) -> str:
    for g, f in GRUPOS:
        if f(c):
            return g
    return "otras"


def tipo(s: pd.Series) -> str:
    d = str(s.dtype)
    if "datetime" in d:
        return "fecha"
    if d in ("str", "string", "object", "category"):
        return "categórica"
    if d.startswith("int") or d.startswith("Int"):
        return "entera"
    if d.startswith("float") or d.startswith("Float"):
        return "numérica"
    return d


def main() -> None:
    df = pd.read_parquet(DS)
    ev = df[df["status"].eq("evaluable")] if "status" in df else df
    lines = []
    w = PARAMS.get("ventana", PARAMS)
    lines += [
        "# Diccionario del dataset analítico",
        "",
        "Generado por `scripts/diccionario_dataset.py` a partir de `data/processed/dataset_analitico.parquet` (salida de `scripts/run_pipeline.py`).",
        "",
        "## Qué es",
        "",
        "- **Unidad de observación**: una fila por vehículo × ventana de mantenimiento. La ventana se abre 30 días antes del vencimiento estimado y el horizonte cierra 90 días después. El cliente vigente es un atributo de la fila.",
        f"- **Filas**: {n(len(df))} ventanas, {n(df['vehicle_id'].nunique())} vehículos. Evaluables (con etiqueta): {n(len(ev))}; churn = {pct(ev['label_churn'].mean())}.",
        f"- **Columnas**: {df.shape[1]} ({len([c for c in df.columns if c not in FIJAS])} columnas de features, de las que el modelo usa 86: `connected_status` se excluye por ser una foto; + {len(FIJAS)} identificadores, geometría y etiquetas).",
        "- **Regla de oro**: toda feature se calcula sólo con turnos de fecha anterior a `scoring_date` y encuestas respondidas antes (uniones as-of estrictas, `src/repurchase/features.py`). Nunca se usan `KM` ni `ConnectedStatusARG` de la agenda (son fotos a la fecha de extracción) ni turnos futuros.",
        f"- **Parámetros de la ventana** (`config/params.json`): {json.dumps(w, ensure_ascii=False)}.",
        "- **Split temporal** (`config/params.json` → `split`): entrenamiento con ventanas abiertas hasta el 30/09/2025, calibración oct-dic 2025, test ene-mar 2026 (horizonte cerrado 30 días antes del corte 25/08/2026).",
        "- **Cómo se construye**: `src/repurchase/eventos.py` (agenda → turnos, evento `mant_completado`), `ventanas.py` (anclas, vencimiento, apertura, horizonte, etiqueta y censura), `features.py` (features as-of). Reproducible con `scripts/run_pipeline.py`.",
        "",
        "## Identificadores, geometría de la ventana y etiquetas",
        "",
        "| Columna | Tipo | Rol | Descripción | % nulos |",
        "|---|---|---|---|---:|",
    ]
    for c in df.columns:
        if c in FIJAS:
            rol, desc = FIJAS[c]
            lines.append(f"| `{c}` | {tipo(df[c])} | {rol} | {desc} | {pct(df[c].isna().mean())} |")
    lines += ["", "## Features (todas calculadas con información anterior a `scoring_date`)", ""]
    feats = [c for c in df.columns if c not in FIJAS]
    tabla = pd.DataFrame({"col": feats, "grupo": [grupo(c) for c in feats]})
    orden = [g for g, _ in GRUPOS] + ["otras"]
    for g in orden:
        cols = tabla.loc[tabla["grupo"].eq(g), "col"].tolist()
        if not cols:
            continue
        lines += [f"### {g.capitalize()}", "", "| Columna | Tipo | Significado | % nulos | Nota |", "|---|---|---|---:|---|"]
        for c in cols:
            nota = "categórica nativa en LightGBM" if c in ft.CATEGORICAL else ""
            if c == "connected_status":
                nota = "EXCLUIDA del modelo (exclude_snapshot): es una foto a la fecha de extracción; queda en el dataset sólo para la ablación"
            if "nulo" not in nota and df[c].isna().mean() > 0.3:
                nota = (nota + "; " if nota else "") + "nulo = sin registro en la red antes del scoring"
            lines.append(f"| `{c}` | {tipo(df[c])} | {ex.NOMBRES.get(c, c)} | {pct(df[c].isna().mean())} | {nota} |")
        lines.append("")

    sc = pd.read_csv(SC, nrows=5)
    OUTPUT = {
        "window_id": "id de la ventana", "vehicle_id": "id seudonimizado del vehículo", "customer_id": "id seudonimizado del cliente vigente",
        "fecha_apertura_ventana": "apertura de la ventana (vencimiento − 30 días)", "vencimiento_estimado": "vencimiento estimado del service",
        "cierre_horizonte": "fin del horizonte (vencimiento + 90 días)", "poblacion_actual": "en_ventana (ya abierta) o abre_en_30_dias",
        "fecha_scoring": "fecha en que se calculó el score (corte de datos)", "dias_restantes_horizonte": "días que quedan hasta el cierre del horizonte",
        "dias_en_ventana": "días transcurridos desde la apertura", "prob_churn": "probabilidad calibrada (0-1) de no completar el mantenimiento en el horizonte",
        "segmento": "Alto / Medio / Bajo según score y capacidad de contacto (20 % / 30 % / 50 %)",
        "tiene_turno_agendado": "ya tiene un turno futuro en la agenda (regla operativa: sale de la lista de contacto)",
        "fecha_turno_agendado": "fecha de ese turno", "driver_1": "principal driver en lenguaje llano, con dirección (↑/↓ riesgo)",
        "driver_2": "segundo driver", "driver_3": "tercer driver", "driver_1_feature": "nombre técnico de la feature del driver 1",
        "driver_1_shap": "contribución SHAP del driver 1 (log-odds)", "prioridad": "ranking (1 = contactar primero): segmento, luego probabilidad",
    }
    lines += ["## Ranking priorizado (`data/processed/scores_actuales.csv`)", "",
              "Una fila por vehículo en ventana o que entra en los próximos 30 días al corte. Incluye el output mínimo de la ficha (ids, fecha de scoring, probabilidad, segmento, drivers) más las columnas de contexto que muestra el dashboard. `scores_actuales_por_usuario.parquet` es la vista consolidada por cliente (sus vehículos en ventana y el peor score).", "",
              "| Columna | Descripción |", "|---|---|"]
    for c in sc.columns:
        d = OUTPUT.get(c)
        if d is None:
            base = c.replace("driver_2_", "driver_1_").replace("driver_3_", "driver_1_")
            d = OUTPUT.get(base, ex.NOMBRES.get(c, "atributo de contexto al scoring (misma definición que la feature homónima)"))
            if base != c:
                d = d.replace("driver 1", c[7]).replace("driver_1", c[:8])
        lines.append(f"| `{c}` | {d} |")
    OUT.write_text("\n".join(lines) + "\n", encoding="utf8")
    print("escrito", OUT, f"({len(feats)} features documentadas, {sum(c not in ex.NOMBRES for c in feats)} sin nombre en castellano)")


if __name__ == "__main__":
    main()
