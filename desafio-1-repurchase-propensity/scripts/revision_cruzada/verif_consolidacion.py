"""Chequeo corto del consolidador de la revisión cruzada (docs/04_revision_cruzada.md, Anexo B).

Resuelve la única refutación del bloque "artefacto_y_comparacion" con un cálculo independiente: sobre los 9.322
vehículos-mes que ambos modelos scorearon en abr-jul 2026, ¿la ventaja de fable en ROC-AUC y en lift@10 % es
significativa? Bootstrap por cliente (300 réplicas, semilla 7) de la diferencia fable − astra, con las dos etiquetas.

Insumos (solo lectura): data/models/revision_cruzada_mensual/test_scored.parquet (score isotónico de fable con la
etiqueta mensual, generado por 02_comparacion_misma_etiqueta.py) y test_predicciones.parquet de astra.
Salida: reports/revision_cruzada/verif_consolidacion.md. No toca nada de astra ni data/.
Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/verif_consolidacion.py
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
ASTRA = Path(r"G:\SIMtec-astra\desafio-1-repurchase-propensity")
OUT = ROOT / "reports" / "revision_cruzada"
LABEL = "label_churn"
lines: list[str] = []


def log(s: str = "") -> None:
    print(s, flush=True); lines.append(s)


def lift_monthly(df: pd.DataFrame, p_col: str, y_col: str, frac: float = 0.1) -> float:
    """Capacidad del 10 % por mes de scoring, redondeo hacia arriba (misma regla que astra y que el informe 02)."""
    caught = contacted = 0
    for _, g in df.groupby(df["scoring_date"].dt.to_period("M")):
        k = int(np.ceil(len(g) * frac)); top = g.sort_values(p_col, ascending=False, kind="mergesort").head(k)
        caught += top[y_col].sum(); contacted += k
    return (caught / contacted) / df[y_col].mean()


ts = pd.read_parquet(ROOT / "data/models/revision_cruzada_mensual/test_scored.parquet")
at = pd.read_parquet(ASTRA / "data/processed/test_predicciones.parquet")[["vehicle_id", "scoring_date", "score", "target"]]
at["vehicle_id"] = at["vehicle_id"].astype(str).str.strip()
ts["vehicle_id"] = ts["vehicle_id"].astype(str)
both = ts.merge(at.rename(columns={"score": "p_astra", "target": "y_astra"}), on=["vehicle_id", "scoring_date"],
                how="inner", validate="one_to_one")

log("# Chequeo del consolidador: AUC y lift@10 % sobre los vehículos-mes comunes\n")
log(f"Test mensual de fable: {len(ts):,} ventanas; test de astra: {len(at):,}; comunes (merge 1:1 por vehicle_id + scoring_date): {len(both):,}.\n")
log("| etiqueta | AUC fable | AUC astra | ΔAUC | lift@10 % fable | lift@10 % astra | Δlift |")
log("|---|---|---|---|---|---|---|")
for ycol, nm in [(LABEL, "de fable"), ("y_astra", "de astra")]:
    auc_f, auc_a = roc_auc_score(both[ycol], both["p_lgbm_cal"]), roc_auc_score(both[ycol], both["p_astra"])
    l_f, l_a = lift_monthly(both, "p_lgbm_cal", ycol), lift_monthly(both, "p_astra", ycol)
    log(f"| {nm} | {auc_f:.4f} | {auc_a:.4f} | {auc_f - auc_a:+.4f} | {l_f:.4f} | {l_a:.4f} | {l_f - l_a:+.4f} |")

rng = np.random.default_rng(7)
cl = both["customer_id"].fillna(both["vehicle_id"]).astype(str).values
groups = pd.Series(np.arange(len(both))).groupby(cl).apply(lambda s: s.values)
keys = np.array(list(groups.index)); idx_by = groups.values
B = 300
res: dict[str, list[float]] = {k: [] for k in ["ΔAUC etiqueta fable", "ΔAUC etiqueta astra", "Δlift@10 % etiqueta fable", "Δlift@10 % etiqueta astra"]}
for _ in range(B):
    pick = rng.integers(0, len(keys), len(keys))
    s = both.iloc[np.concatenate([idx_by[p] for p in pick])]
    res["ΔAUC etiqueta fable"].append(roc_auc_score(s[LABEL], s["p_lgbm_cal"]) - roc_auc_score(s[LABEL], s["p_astra"]))
    res["ΔAUC etiqueta astra"].append(roc_auc_score(s["y_astra"], s["p_lgbm_cal"]) - roc_auc_score(s["y_astra"], s["p_astra"]))
    res["Δlift@10 % etiqueta fable"].append(lift_monthly(s, "p_lgbm_cal", LABEL) - lift_monthly(s, "p_astra", LABEL))
    res["Δlift@10 % etiqueta astra"].append(lift_monthly(s, "p_lgbm_cal", "y_astra") - lift_monthly(s, "p_astra", "y_astra"))
log(f"\nBootstrap por cliente ({B} réplicas, {len(keys):,} clientes, semilla 7) de la diferencia fable − astra:\n")
log("| diferencia | media | IC95 |")
log("|---|---|---|")
for k, v in res.items():
    a = np.array(v)
    log(f"| {k} | {a.mean():+.3f} | [{np.percentile(a, 2.5):+.3f}, {np.percentile(a, 97.5):+.3f}] |")
log("\nLectura: la ventaja de fable en ROC-AUC es significativa con las dos etiquetas; en lift@10 % los IC incluyen 0, "
    "así que el \"1,24 vs 1,20\" del documento (medido sobre poblaciones distintas) no se sostiene como ventaja sobre los "
    "mismos vehículos-mes. Coincide con verif_artefacto_y_comparacion.md.")
(OUT / "verif_consolidacion.md").write_text("\n".join(lines), encoding="utf8")
print("\nguardado en", OUT / "verif_consolidacion.md")
