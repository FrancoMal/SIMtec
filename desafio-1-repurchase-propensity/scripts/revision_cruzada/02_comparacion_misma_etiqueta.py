"""Revisión cruzada: ¿cuánto de la diferencia entre soluciones es la etiqueta y cuánto el modelo?

Entrena el pipeline de fable (mismas anclas/vencimientos y mismas 86 features) con la ETIQUETA MENSUAL de astra
(scoring el 1° del mes del vencimiento, horizonte = fin de mes, sin margen) y evalúa en abr-jul 2026 con la misma
capacidad (10 % por mes) que astra. Si el resultado es parecido a 0,673 / 1,20, la diferencia entre trabajos es la
definición del target, no la calidad del modelo. También evalúa el ranking de fable con horizontes de 60 y 90 días
desde el 1° del mes (las sensibilidades que astra reporta: 1,41 y 1,56).

Salida: reports/revision_cruzada/02_comparacion_misma_etiqueta.md (+ csv). No toca data/processed ni data/models.
Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/02_comparacion_misma_etiqueta.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.features import build_features  # noqa: E402
from repurchase.io import load_sales  # noqa: E402
from repurchase.modelo import LABEL, SplitConfig, run_training  # noqa: E402
from repurchase.ventanas import WindowParams, build_windows, maintenance_events  # noqa: E402

OUT = config.REPORTS_DIR / "revision_cruzada"
OUT.mkdir(parents=True, exist_ok=True)
ASTRA = Path(r"G:\SIMtec-astra\desafio-1-repurchase-propensity")
lines = []


def log(s=""):
    print(s, flush=True); lines.append(s)


def lift_monthly(df, p_col, y_col, frac=0.1):
    """Capacidad del 10 % por mes de scoring, redondeo hacia arriba (misma regla que astra)."""
    caught = contacted = 0
    for _, g in df.groupby(df["scoring_date"].dt.to_period("M")):
        k = int(np.ceil(len(g) * frac)); top = g.sort_values(p_col, ascending=False).head(k)
        caught += top[y_col].sum(); contacted += k
    return (caught / contacted) / df[y_col].mean()


cfg = json.loads((config.PROJECT_DIR / "config/params.json").read_text(encoding="utf8"))
appt = appointments(); sales = load_sales()
p = WindowParams.from_dict({**cfg["ventana"], "label_mode": "mes_calendario", "label_margin_days": 0})
log("# Comparación con la misma etiqueta (mensual, de astra)\n")
log(f"Parámetros: {json.dumps(p.to_dict(), ensure_ascii=False)}")
w = build_windows(appt, sales, p, cutoff=pd.Timestamp("2026-07-31"))  # astra observa hasta el 1/8 exclusivo
ev = w[w["status"] == "evaluable"].copy()
log(f"\nVentanas evaluables con etiqueta mensual: {len(ev):,}; churn {ev[LABEL].mean():.3f}")
log(ev.groupby(ev["scoring_date"].dt.to_period("Q"))[LABEL].agg(["size", "mean"]).round(3).to_markdown())

feat = build_features(ev, appt, sales).merge(ev[["window_id", LABEL, "horizon_end", "next_maint_date"]], on="window_id")
split = SplitConfig(train_end="2025-11-30", valid_end="2026-03-31")   # test = abr-jul 2026, como astra
res = run_training(feat, split, out_dir=config.MODELS_DIR / "revision_cruzada_mensual", exclude_snapshot=True)
ts = res["test_scored"].copy()
ts = ts.merge(feat[["window_id", "due_date", "next_maint_date", "vehicle_id"]].rename(columns={"vehicle_id": "vid"}), on="window_id")
y = ts[LABEL].values; pc = ts["p_lgbm_cal"].values
log("\n## Resultado del pipeline de fable con la etiqueta mensual (test abr-jul 2026)\n")
log(f"n = {len(ts):,}; churn {y.mean():.3f}; ROC-AUC {roc_auc_score(y, pc):.3f}; AP {average_precision_score(y, pc):.3f}; "
    f"lift@10 % (por mes) {lift_monthly(ts, 'p_lgbm_cal', LABEL):.3f}; lift@20 % {lift_monthly(ts, 'p_lgbm_cal', LABEL, .2):.3f}")
log(f"Regresión logística de fable, misma etiqueta: ROC-AUC {roc_auc_score(y, ts['p_logreg']):.3f}; lift@10 % {lift_monthly(ts, 'p_logreg', LABEL):.3f}")
log("Referencia astra (su test abr-jul 2026, n = 23.740, churn 0,782): ROC-AUC 0,673; AP 0,877; lift@10 % 1,20 (IC95 1,18-1,22).")
mon = ts.groupby(ts["scoring_date"].dt.to_period("M")).apply(
    lambda g: pd.Series({"n": len(g), "churn": g[LABEL].mean(), "roc_auc": roc_auc_score(g[LABEL], g["p_lgbm_cal"]),
                         "lift10": lift_monthly(g, "p_lgbm_cal", LABEL)}))
log("\nPor mes:\n" + mon.round(3).to_markdown())

# Sensibilidad: el mismo ranking mensual evaluado con horizontes de 60 y 90 días desde el 1° del mes (como astra)
maint = maintenance_events(appt, p)[["vehicle_id", "event_date"]]
for h in (60, 90):
    end = ts["scoring_date"] + pd.Timedelta(days=h)
    ok = end <= pd.Timestamp("2026-08-01")
    d = ts[ok].copy()
    j = d[["window_id", "vid", "scoring_date"]].merge(maint.rename(columns={"vehicle_id": "vid"}), on="vid", how="left")
    hit = j[(j["event_date"] >= j["scoring_date"]) & (j["event_date"] < j["scoring_date"] + pd.Timedelta(days=h))]["window_id"].unique()
    d["y_h"] = (~d["window_id"].isin(hit)).astype(float)
    log(f"\nHorizonte {h} d desde el 1° (n={len(d):,}, churn {d['y_h'].mean():.3f}): ROC-AUC {roc_auc_score(d['y_h'], d['p_lgbm_cal']):.3f}; "
        f"lift@10 % {lift_monthly(d, 'p_lgbm_cal', 'y_h'):.3f}   (astra: 60 d churn 0,638 / lift 1,41; 90 d churn 0,558 / lift 1,56)")

# Comparación directa en los vehículos-mes que ambos scorearon: ¿quién ordena mejor el MISMO conjunto?
at = pd.read_parquet(ASTRA / "data/processed/test_predicciones.parquet")[["vehicle_id", "scoring_date", "score", "target"]]
both = ts.merge(at.rename(columns={"vehicle_id": "vid", "score": "p_astra", "target": "y_astra"}), on=["vid", "scoring_date"], how="inner")
if len(both):
    log(f"\n## Vehículos-mes scoreados por ambos en abr-jul 2026: {len(both):,}\n")
    log(f"Etiquetas coinciden en {(both[LABEL] == both['y_astra']).mean():.1%} de los casos (difieren por mismo-usuario, Guarantee y vencimientos distintos).")
    for name, col in [("fable (LightGBM calibrado)", "p_lgbm_cal"), ("astra (LightGBM_31 calibrado)", "p_astra")]:
        log(f"- {name}: con la etiqueta de fable ROC-AUC {roc_auc_score(both[LABEL], both[col]):.3f}, lift@10 % {lift_monthly(both, col, LABEL):.3f}; "
            f"con la etiqueta de astra ROC-AUC {roc_auc_score(both['y_astra'], both[col]):.3f}, lift@10 % {lift_monthly(both, col, 'y_astra'):.3f}")
    log(f"Correlación de Spearman entre los dos scores: {both[['p_lgbm_cal', 'p_astra']].corr(method='spearman').iloc[0, 1]:.3f}")

(OUT / "02_comparacion_misma_etiqueta.md").write_text("\n".join(lines), encoding="utf8")
mon.to_csv(OUT / "02_por_mes.csv")
print("guardado en", OUT)
