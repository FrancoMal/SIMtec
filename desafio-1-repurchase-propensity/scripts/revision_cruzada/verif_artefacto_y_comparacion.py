"""Verificación escéptica del bloque 'artefacto_y_comparacion' de docs/04_revision_cruzada.md (secciones 2.2 y 4).

Afirmaciones que se intentan refutar con código independiente:
 (a) Test de astra: churn 75,6 % (vencimiento días 0-5) → 81,7 % (días 26-31); ordenar sólo por días al vencimiento
     da ROC-AUC 0,538 y lift@10 % 1,053; Spearman(score, días al vencimiento) 0,094.
 (b) Pipeline de fable con etiqueta mensual: ROC-AUC 0,730, lift@10 % 1,24 (n=25.612, abr-jul 2026); sobre 9.322
     vehículos-mes comunes fable 0,689 vs astra 0,646. Se verifica que la comparación es justa (mismos meses, misma
     regla de capacidad, sin leakage en el split, merge correcto) y si la ventaja sobrevive a (i) el desempate de los
     scores isotónicos, (ii) entrenar con el período de astra (jul-24..ago-25), (iii) quitar features que astra eligió
     no usar (dealer, TMA, encuestas).

Sólo escribe en reports/revision_cruzada/ (informe) y en el scratchpad (modelos re-entrenados). Astra es solo lectura.
Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/verif_artefacto_y_comparacion.py
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr
from sklearn.metrics import average_precision_score, roc_auc_score

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import appointments  # noqa: E402
from repurchase.features import build_features  # noqa: E402
from repurchase.io import load_sales  # noqa: E402
from repurchase.modelo import LABEL, SplitConfig, run_training  # noqa: E402
from repurchase.ventanas import WindowParams, build_windows  # noqa: E402

ASTRA = Path(r"G:\SIMtec-astra\desafio-1-repurchase-propensity")
OUT = config.REPORTS_DIR / "revision_cruzada"
SCRATCH = Path(os.environ.get("VERIF_SCRATCH", r"F:\Caches\Temp\claude\G--SIMtec-fable\28dff193-8508-4393-8dee-77ce51636f75\scratchpad")) / "verif_modelos"
SCRATCH.mkdir(parents=True, exist_ok=True)
T0 = time.time()
lines: list[str] = []


def log(s=""):
    print(f"[{time.time() - T0:6.0f}s] {s}" if s else "", flush=True)
    lines.append(s)


# ----------------------------------------------------------------------------------------------------------------
# Lift con capacidad 10 % por mes (redondeo hacia arriba), con tres reglas de desempate
# ----------------------------------------------------------------------------------------------------------------
def lift_monthly(df, p_col, y_col, frac=0.1, tie="arbitrario", tiebreak_col=None):
    """tie='arbitrario': como el script 02 (sort_values sin desempate); 'raw': desempata por tiebreak_col;
    'esperado': las filas empatadas en el umbral entran con peso fraccional (valor esperado bajo desempate al azar)."""
    caught = contacted = 0.0
    for _, g in df.groupby(pd.to_datetime(df["scoring_date"]).dt.to_period("M")):
        k = int(np.ceil(len(g) * frac))
        if tie == "arbitrario":
            top = g.sort_values(p_col, ascending=False).head(k)
            caught += top[y_col].sum()
        elif tie == "raw":
            top = g.sort_values([p_col, tiebreak_col], ascending=[False, False]).head(k)
            caught += top[y_col].sum()
        else:
            s = g.sort_values(p_col, ascending=False)
            thr = s[p_col].iloc[k - 1]
            above = g[g[p_col] > thr]; tied = g[g[p_col] == thr]
            w = (k - len(above)) / len(tied)
            caught += above[y_col].sum() + w * tied[y_col].sum()
        contacted += k
    return (caught / contacted) / df[y_col].mean()


def lift_global(df, p_col, y_col, frac=0.1):
    """Top 10 % del total (como hizo el script 01 para la regla de calendario), desempate arbitrario."""
    k = int(np.ceil(len(df) * frac)); top = df.sort_values(p_col, ascending=False).head(k)
    return top[y_col].mean() / df[y_col].mean()


# ================================================================================================================
# A. Artefacto de calendario en el test de astra
# ================================================================================================================
log("# Verificación bloque 'artefacto_y_comparacion' (docs/04 §2.2 y §4)\n")
log("## A. Artefacto de calendario en el test de astra (`test_predicciones.parquet`)\n")
at = pd.read_parquet(ASTRA / "data/processed/test_predicciones.parquet")
at["scoring_date"] = pd.to_datetime(at["scoring_date"]).astype("datetime64[ns]")
at["due_date"] = pd.to_datetime(at["due_date"]).astype("datetime64[ns]")
log(f"Filas: {len(at):,}; meses: {sorted(at['scoring_date'].dt.strftime('%Y-%m').unique())}; target nulo: {at['target'].isna().sum()}; "
    f"duplicados (vehicle_id, scoring_date): {at.duplicated(['vehicle_id', 'scoring_date']).sum()}")
# ¿el vencimiento tiene componente horaria? (astra proyecta días fraccionales)
frac_time = (at["due_date"] != at["due_date"].dt.normalize()).mean()
at["dias"] = (at["due_date"] - at["scoring_date"]).dt.days           # como el script 01 (trunca)
at["dias_astra"] = at["dias_al_vencimiento"]                           # columna propia de astra (float)
log(f"Vencimientos con hora no-medianoche: {frac_time:.1%}. Rango de días al vencimiento (truncado): {at['dias'].min()}..{at['dias'].max()}; "
    f"|dias − dias_al_vencimiento de astra| máx = {(at['dias'] - at['dias_astra']).abs().max():.3f} (la columna de astra es float; truncar no cambia el orden entre días distintos)")
assert at["dias"].between(0, 30).all(), "hay vencimientos fuera del mes de scoring"
at["bucket"] = pd.cut(at["dias"], [-1, 5, 10, 15, 20, 25, 31], labels=["0-5", "6-10", "11-15", "16-20", "21-25", "26-31"])
tab = at.groupby("bucket", observed=True).agg(ventanas=("row_id", "size"), churn=("target", "mean"), score_medio=("score", "mean"))
log("\nChurn por posición del vencimiento en el mes (días desde el 1°; '0' = vence el 1°):\n")
log(tab.round(4).to_markdown())
# la misma tabla con 'día del mes' (1-31) para aclarar la etiqueta "días 1-5" del documento
at["dom"] = at["due_date"].dt.day
tab_dom = at.groupby(pd.cut(at["dom"], [0, 5, 10, 15, 20, 25, 31], labels=["1-5", "6-10", "11-15", "16-20", "21-25", "26-31"]), observed=True)["target"].agg(["size", "mean"])
log("\nMisma tabla por DÍA DEL MES del vencimiento (1 = primer día):\n")
log(tab_dom.round(4).to_markdown())
# también por mes de scoring (¿es estable?)
tab_m = at.pivot_table(index=at["scoring_date"].dt.strftime("%Y-%m"), columns="bucket", values="target", aggfunc="mean", observed=True)
log("\nChurn por bucket y mes de scoring:\n")
log(tab_m.round(3).to_markdown())

auc_model = roc_auc_score(at["target"], at["score"])
auc_cal = roc_auc_score(at["target"], at["dias"])
auc_cal_f = roc_auc_score(at["target"], at["dias_astra"])
rho, _ = spearmanr(at["score"], at["dias"])
rho_f, _ = spearmanr(at["score"], at["dias_astra"])
log(f"\nROC-AUC modelo astra: {auc_model:.4f} (astra reporta 0,6733). ROC-AUC 'días al vencimiento' (entero): {auc_cal:.4f}; con la columna float de astra: {auc_cal_f:.4f}.")
log(f"Spearman(score, días entero): {rho:.4f}; Spearman(score, días float de astra): {rho_f:.4f}.")
per_month_auc = at.groupby(at["scoring_date"].dt.strftime("%Y-%m")).apply(lambda g: roc_auc_score(g["target"], g["dias"]))
log(f"ROC-AUC de la regla de calendario por mes: {per_month_auc.round(3).to_dict()}")
# Lift de la regla de calendario: como lo calculó el script 01 (top 10 % global, desempate arbitrario) y como dice el
# documento (10 % por mes, redondeo hacia arriba), con desempate arbitrario y con valor esperado (los días son enteros:
# los empates en el umbral son masivos)
at["y"] = at["target"]
l_glob = lift_global(at, "dias", "y")
l_mes_arb = lift_monthly(at, "dias", "y", tie="arbitrario")
l_mes_ev = lift_monthly(at, "dias", "y", tie="esperado")
l_mes_evf = lift_monthly(at, "dias_astra", "y", tie="esperado")
l_model_mes = lift_monthly(at, "score", "y", tie="esperado")
l_model_glob = lift_global(at, "score", "y")
log(f"\nLift@10 % regla de calendario: global/arbitrario (script 01) {l_glob:.4f}; por mes/arbitrario {l_mes_arb:.4f}; "
    f"por mes/valor esperado {l_mes_ev:.4f}; por mes con la columna float de astra (sin empates) {l_mes_evf:.4f}.")
log(f"Lift@10 % modelo astra: por mes {l_model_mes:.4f} (astra reporta 1,2016); global {l_model_glob:.4f}.")
for m, g in at.groupby(at["scoring_date"].dt.strftime("%Y-%m")):
    k = int(np.ceil(len(g) * .1)); s = g.sort_values("dias", ascending=False); thr = s["dias"].iloc[k - 1]
    log(f"  {m}: k={k}, umbral={thr} días, estrictamente arriba {(g['dias'] > thr).sum()}, empatados {(g['dias'] == thr).sum()}")
# ¿Cuánto del AUC del modelo se explica por el calendario? AUC del modelo dentro de cada bucket (control por calendario)
auc_in = at.groupby("bucket", observed=True).apply(lambda g: roc_auc_score(g["target"], g["score"]))
log(f"\nROC-AUC del modelo de astra DENTRO de cada bucket de calendario (si fuera calendario puro, caería a 0,5): {auc_in.round(3).to_dict()}")

# ================================================================================================================
# B. Comparación con la misma etiqueta
# ================================================================================================================
log("\n## B. Comparación con la misma etiqueta mensual\n")
# --- B.1 protocolo de astra, releído de su código y su parquet
av = pd.read_parquet(ASTRA / "data/processed/ventanas.parquet")
av["scoring_date"] = pd.to_datetime(av["scoring_date"]).astype("datetime64[ns]")
d = av["scoring_date"]
av["split"] = np.select([d.between("2024-07-01", "2025-08-01"), d.between("2025-10-01", "2025-11-01"),
                         d.between("2026-01-01", "2026-02-01"), d.between("2026-04-01", "2026-07-01"), d.eq("2026-08-01")],
                        ["train", "valid", "calibration", "test", "demo"], default="embargo")
sp = av.groupby("split").agg(n=("row_id", "size"), desde=("scoring_date", "min"), hasta=("scoring_date", "max"), con_label=("target", lambda s: s.notna().sum()))
log("Particiones de astra (src/modeling.py::split_name aplicado a su ventanas.parquet):\n")
log(sp.to_markdown())
log("\nAstra: LightGBM_31 (300 árboles fijos) ajustado en train jul-24..ago-25; selección por AP en oct-nov 25; calibración sigmoide en ene-feb 26; "
    "sep-25, dic-25 y mar-26 en embargo; test abr-jul 26 con capacidad 10 % por mes (ceil).")

# --- B.2 lo que el informe 02 dejó en data/models/revision_cruzada_mensual
M02 = config.MODELS_DIR / "revision_cruzada_mensual"
info02 = json.loads((M02 / "info.json").read_text(encoding="utf8"))
ts02 = pd.read_parquet(M02 / "test_scored.parquet")
ts02["scoring_date"] = pd.to_datetime(ts02["scoring_date"]).astype("datetime64[ns]")
log(f"\nInforme 02 (artefactos guardados): split {info02['split']}, n_train {info02['n_train']:,} (churn {info02['base_rate_train']:.3f}), "
    f"n_valid {info02['n_valid']:,}, n_test {info02['n_test']:,}, best_iteration {info02['best_iteration']}, features {info02['n_features']}, "
    f"test {info02['test_scoring_range']}")
y02 = ts02[LABEL].values
log(f"Test guardado: n={len(ts02):,}, churn {y02.mean():.4f}, ROC-AUC (cal) {roc_auc_score(y02, ts02['p_lgbm_cal']):.4f}, ROC-AUC (raw) {roc_auc_score(y02, ts02['p_lgbm_raw']):.4f}, "
    f"AP (cal) {average_precision_score(y02, ts02['p_lgbm_cal']):.4f}")
log(f"Valores distintos de p_lgbm_cal (isotónica): {ts02['p_lgbm_cal'].nunique()} de {len(ts02):,}; de p_lgbm_raw: {ts02['p_lgbm_raw'].nunique():,}")
for m, g in ts02.groupby(ts02["scoring_date"].dt.strftime("%Y-%m")):
    k = int(np.ceil(len(g) * .1)); s = g.sort_values("p_lgbm_cal", ascending=False); thr = s["p_lgbm_cal"].iloc[k - 1]
    log(f"  {m}: n={len(g)}, k={k}, umbral p_cal={thr:.4f}, estrictamente arriba {(g['p_lgbm_cal'] > thr).sum()}, empatados en el umbral {(g['p_lgbm_cal'] == thr).sum()}")
l_arb = lift_monthly(ts02, "p_lgbm_cal", LABEL, tie="arbitrario")
l_raw = lift_monthly(ts02, "p_lgbm_cal", LABEL, tie="raw", tiebreak_col="p_lgbm_raw")
l_ev = lift_monthly(ts02, "p_lgbm_cal", LABEL, tie="esperado")
l_rawonly = lift_monthly(ts02, "p_lgbm_raw", LABEL, tie="arbitrario")
l20_arb = lift_monthly(ts02, "p_lgbm_cal", LABEL, .2, tie="arbitrario"); l20_ev = lift_monthly(ts02, "p_lgbm_cal", LABEL, .2, tie="esperado")
log(f"Lift@10 % por mes de fable (informe 02 = 1,240): desempate arbitrario {l_arb:.4f}; desempate por score crudo {l_raw:.4f}; "
    f"valor esperado {l_ev:.4f}; ordenando por score crudo {l_rawonly:.4f}. Lift@20 %: arbitrario {l20_arb:.4f}, esperado {l20_ev:.4f}.")

# --- B.3 reconstrucción independiente de ventanas + features mensuales de fable (para chequear leakage y re-entrenar)
cfg = json.loads((config.PROJECT_DIR / "config/params.json").read_text(encoding="utf8"))
p = WindowParams.from_dict({**cfg["ventana"], "label_mode": "mes_calendario", "label_margin_days": 0})
appt = appointments(); sales = load_sales()
w = build_windows(appt, sales, p, cutoff=pd.Timestamp("2026-07-31"))
ev = w[w["status"] == "evaluable"].copy()
log(f"\nVentanas evaluables reconstruidas: {len(ev):,}; churn {ev[LABEL].mean():.4f} (informe 02: 150.691 / 0,789)")
# chequeos de la construcción
assert (ev["scoring_date"].dt.day == 1).all(), "scoring no es el 1° del mes"
assert (ev["horizon_end"] == ev["scoring_date"] + pd.offsets.MonthEnd(0)).all(), "horizonte no es fin de mes"
assert (ev["due_date"].dt.to_period("M") == ev["scoring_date"].dt.to_period("M")).all(), "vencimiento fuera del mes de scoring"
ret = ev["next_maint_date"].notna() & (ev["next_maint_date"] > ev["scoring_date"]) & (ev["next_maint_date"] <= ev["horizon_end"])
assert ((ev[LABEL] == 0) == ret).all(), "la etiqueta no coincide con 'hubo mantenimiento entre el 1° y fin de mes'"
assert not ev.duplicated(["vehicle_id", "scoring_date"]).any()
# retorno EXACTAMENTE el 1° del mes: fable lo trata como 'preempted' (fuera de la población); astra como retorno (target 0)
pre = w[(w["status"] == "preempted") & (w["next_maint_date"] == w["scoring_date"])]
log(f"Ventanas donde el vehículo volvió justo el 1° del mes: fable las excluye como 'preempted' ({len(pre):,}); astra las contaría como retorno. Diferencia de población menor.")
# leakage en el split: horizonte de train < primer scoring de valid; de valid < primer scoring de test
split = SplitConfig(train_end="2025-11-30", valid_end="2026-03-31")
tr = ev[ev["scoring_date"] <= split.train_end]; va = ev[(ev["scoring_date"] > split.train_end) & (ev["scoring_date"] <= split.valid_end)]; te = ev[ev["scoring_date"] > split.valid_end]
log(f"Split de fable: train {tr['scoring_date'].min().date()}..{tr['scoring_date'].max().date()} (n={len(tr):,}, horizonte máx {tr['horizon_end'].max().date()}); "
    f"valid {va['scoring_date'].min().date()}..{va['scoring_date'].max().date()} (n={len(va):,}, horizonte máx {va['horizon_end'].max().date()}); "
    f"test {te['scoring_date'].min().date()}..{te['scoring_date'].max().date()} (n={len(te):,})")
assert tr["horizon_end"].max() < va["scoring_date"].min() and va["horizon_end"].max() < te["scoring_date"].min(), "solapamiento de horizontes entre particiones"
log("Sin solapamiento de horizontes entre train/valid/test (el horizonte mensual cierra antes del siguiente scoring). "
    "Asimetría: fable entrena con scoring ene-24..nov-25 (incluye 2024-H1 y sep-nov 25) y usa dic-25..mar-26 para early stopping + isotónica; "
    "astra entrena sólo jul-24..ago-25. Fable usa 3 meses más recientes de entrenamiento y 6 más antiguos.")

feat = build_features(ev, appt, sales).merge(ev[["window_id", LABEL, "horizon_end", "next_maint_date"]], on="window_id")  # anchor_type ya viene en las features
# features as-of: ninguna feature de fechas debe ser negativa (evento posterior al scoring)
for c in ["days_since_last_appt", "days_since_last_maint", "days_since_last_visit", "days_since_last_km", "days_since_last_survey"]:
    assert (feat[c].dropna() > 0).all(), f"{c} tiene valores <= 0: evento del mismo día o posterior al scoring"
log(f"Features: {feat.shape[1]} columnas; todas las 'days_since_*' son > 0 (as-of estricto). Test n={int((feat['scoring_date'] > split.valid_end).sum()):,}")

# --- B.4 tres re-entrenamientos: (1) split del informe 02; (2) período de astra; (3) período de astra sin dealer/TMA/encuestas
def summarize(name, res, extra_cols=None):
    ts = res["test_scored"].copy(); ts["scoring_date"] = pd.to_datetime(ts["scoring_date"]).astype("datetime64[ns]")
    y = ts[LABEL].values
    r = {"corrida": name, "n_train": res["info"]["n_train"], "best_iter": res["info"]["best_iteration"], "n_test": len(ts),
         "roc_auc": roc_auc_score(y, ts["p_lgbm_cal"]), "ap": average_precision_score(y, ts["p_lgbm_cal"]),
         "lift10_arb": lift_monthly(ts, "p_lgbm_cal", LABEL, tie="arbitrario"),
         "lift10_esp": lift_monthly(ts, "p_lgbm_cal", LABEL, tie="esperado"),
         "lift10_raw": lift_monthly(ts, "p_lgbm_raw", LABEL, tie="arbitrario"),
         "lift20_esp": lift_monthly(ts, "p_lgbm_cal", LABEL, .2, tie="esperado")}
    return r, ts


runs = {}
log("\nRe-entrenando (1) split del informe 02 ...")
res1 = run_training(feat, split, out_dir=SCRATCH / "r1_split_fable", exclude_snapshot=True)
runs["(1) fable, split del informe 02 (train ≤ nov-25)"], ts1 = summarize("r1", res1)

log("Re-entrenando (2) período de astra: train jul-24..ago-25; valid = oct-nov 25 + ene-feb 26 (early stopping + isotónica); sin 2024-H1 ni meses de embargo ...")
mask_astra = (feat["scoring_date"] >= "2024-07-01") & ~feat["scoring_date"].dt.strftime("%Y-%m").isin(["2025-09", "2025-12", "2026-03"])
feat_a = feat[mask_astra].copy()
split_a = SplitConfig(train_end="2025-08-31", valid_end="2026-03-31")
res2 = run_training(feat_a, split_a, out_dir=SCRATCH / "r2_periodo_astra", exclude_snapshot=True)
runs["(2) fable, período de astra (train jul-24..ago-25)"], ts2 = summarize("r2", res2)

log("Re-entrenando (3) período de astra y sin features que astra eligió no usar (dealer, TMA, encuestas, zona) ...")
drop_cols = ["last_maint_dealer", "tma", "last_dealer_zone", "region", "same_dealer_as_sale", "n_surveys", "min_rating",
             "mean_rating", "last_rating", "days_since_last_survey"]
feat_b = feat_a.drop(columns=[c for c in drop_cols if c in feat_a.columns])
res3 = run_training(feat_b, split_a, out_dir=SCRATCH / "r3_periodo_astra_sin_dealer", exclude_snapshot=True)
runs["(3) = (2) sin dealer/TMA/zona/región/encuestas"], ts3 = summarize("r3", res3)

tabr = pd.DataFrame([{"corrida": k, **{kk: vv for kk, vv in v.items() if kk != "corrida"}} for k, v in runs.items()]).set_index("corrida")
log("\nResultados en el test abr-jul 2026 (población mensual de fable, capacidad 10 % por mes):\n")
log(tabr.round(4).to_markdown())
log(f"\nReproducibilidad del informe 02 (0,730 / 1,240): corrida (1) da ROC-AUC {runs[list(runs)[0]]['roc_auc']:.4f} y lift arbitrario {runs[list(runs)[0]]['lift10_arb']:.4f}. "
    f"Correlación de Spearman entre el score guardado del informe 02 y el re-entrenado: "
    f"{ts02.merge(ts1[['window_id', 'p_lgbm_raw']], on='window_id', suffixes=('_02', '_r1'))[['p_lgbm_raw_02', 'p_lgbm_raw_r1']].corr(method='spearman').iloc[0, 1]:.4f}")
imp = res1["importance"].head(12)
log("\nTop-12 features por ganancia (corrida 1): " + ", ".join(f"{r.feature} ({r.gain_pct:.1%})" for r in imp.itertuples()))
log(f"Peso de 'days_to_due_at_scoring' (= el artefacto de calendario, que astra también tiene como dias_al_vencimiento): "
    f"{res1['importance'].set_index('feature').loc['days_to_due_at_scoring', 'gain_pct']:.1%} de la ganancia.")

# --- B.5 merge con el test de astra por (vehicle_id, scoring_date)
def merge_common(ts):
    a = at[["vehicle_id", "scoring_date", "score", "score_raw", "target", "target_vin", "customer_id", "dias"]].rename(
        columns={"score": "p_astra", "score_raw": "p_astra_raw", "target": "y_astra", "customer_id": "cust_astra"})
    b = ts.merge(a, on=["vehicle_id", "scoring_date"], how="inner", validate="one_to_one")
    return b


both = merge_common(ts02)
log(f"\n### B.5 Vehículos-mes comunes (merge 1:1 por vehicle_id + scoring_date): {len(both):,} (informe 02: 9.322)")
log(f"Cobertura: {len(both) / len(at):.1%} del test de astra ({len(at):,}) y {len(both) / len(ts02):.1%} del test mensual de fable ({len(ts02):,}). "
    f"Vehículos del test de astra que fable scorea en abr-jul pero en OTRO mes: "
    f"{len(set(at['vehicle_id']) & set(ts02['vehicle_id'])) - both['vehicle_id'].nunique():,}. "
    f"Formato de id: astra strip() + string; fable string sin strip: longitud única {ts02['vehicle_id'].str.len().unique().tolist()} vs {at['vehicle_id'].str.len().unique().tolist()}.")
# ¿en qué mes cae el vencimiento estimado por astra para los vehículos comunes? verificar que la diferencia de fechas sea 0 en el merge
log(f"Etiquetas coinciden: {(both[LABEL] == both['y_astra']).mean():.2%} (informe 02: 96,6 %). Con la etiqueta por VIN de astra (target_vin): {(both[LABEL] == both['target_vin']).mean():.2%}. "
    f"Churn en comunes: fable {both[LABEL].mean():.3f}, astra {both['y_astra'].mean():.3f}.")
# mezcla de anclas en comunes vs no comunes
mix = feat[feat["scoring_date"] > split.valid_end][["window_id", "anchor_type"]].merge(ts02[["window_id", "vehicle_id", "scoring_date"]], on="window_id")
mix["comun"] = mix["window_id"].isin(both["window_id"])
log("Tipo de ancla en el test de fable, comunes vs no comunes:\n" + pd.crosstab(mix["comun"], mix["anchor_type"], normalize="index").round(3).to_markdown())


def head_to_head(b, tag, fable_col="p_lgbm_cal", fable_tb="p_lgbm_raw"):
    rows = []
    for name, col, tb in [("fable", fable_col, fable_tb), ("astra", "p_astra", "p_astra_raw")]:
        for lab, ycol in [("etiqueta fable", LABEL), ("etiqueta astra", "y_astra")]:
            rows.append({"modelo": name, "etiqueta": lab, "roc_auc": roc_auc_score(b[ycol], b[col]),
                         "lift10_arb": lift_monthly(b, col, ycol, tie="arbitrario"),
                         "lift10_esp": lift_monthly(b, col, ycol, tie="esperado"),
                         "lift10_raw": lift_monthly(b, tb, ycol, tie="arbitrario")})
    t = pd.DataFrame(rows).set_index(["modelo", "etiqueta"])
    log(f"\n{tag}:\n")
    log(t.round(4).to_markdown())
    return t


t_common = head_to_head(both, "Cara a cara en los comunes, score del informe 02")
rho_scores = both[["p_lgbm_raw", "p_astra"]].corr(method="spearman").iloc[0, 1]
log(f"Spearman entre scores (fable crudo vs astra): {rho_scores:.4f} (informe 02: 0,684 con el score isotónico).")
# AUC de fable en comunes vs no comunes (¿la población extra de fable es más 'fácil'?)
nc = ts02[~ts02["window_id"].isin(both["window_id"])]
log(f"ROC-AUC de fable (informe 02) en comunes {roc_auc_score(both[LABEL], both['p_lgbm_cal']):.4f} vs en NO comunes {roc_auc_score(nc[LABEL], nc['p_lgbm_cal']):.4f} "
    f"(n={len(nc):,}, churn {nc[LABEL].mean():.3f}); churn de astra en sus NO comunes: {at[~at.set_index(['vehicle_id', 'scoring_date']).index.isin(both.set_index(['vehicle_id', 'scoring_date']).index)]['target'].mean():.3f}. "
    f"El 0,730 global y el 0,673 de astra están medidos sobre poblaciones distintas; la comparación limpia es la de los comunes.")

# el mismo cara a cara con los re-entrenamientos (2) y (3)
for name, ts_ in [("(2) período de astra", ts2), ("(3) período de astra sin dealer/TMA/encuestas", ts3)]:
    b_ = merge_common(ts_)
    head_to_head(b_, f"Cara a cara en los comunes (n={len(b_):,}), fable re-entrenado {name}")

# --- B.6 incertidumbre: bootstrap por cliente (customer_id de astra) de la diferencia pareada en los comunes
rng = np.random.default_rng(20260915)
codes, ids = pd.factorize(both["cust_astra"])
groups = [np.flatnonzero(codes == i) for i in range(len(ids))]
diffs = []
for _ in range(300):
    pick = rng.integers(0, len(groups), len(groups))
    ix = np.concatenate([groups[i] for i in pick])
    b = both.iloc[ix]
    diffs.append([roc_auc_score(b[LABEL], b["p_lgbm_cal"]) - roc_auc_score(b[LABEL], b["p_astra"]),
                  roc_auc_score(b["y_astra"], b["p_lgbm_cal"]) - roc_auc_score(b["y_astra"], b["p_astra"]),
                  lift_monthly(b, "p_lgbm_raw", LABEL) - lift_monthly(b, "p_astra", LABEL),
                  lift_monthly(b, "p_lgbm_raw", "y_astra") - lift_monthly(b, "p_astra", "y_astra")])
dq = np.quantile(np.asarray(diffs), [.025, .975], axis=0)
log(f"\nBootstrap por cliente (300 réplicas, {len(ids):,} clientes) de la diferencia fable − astra en los comunes (IC 95 %): "
    f"ΔAUC etiqueta fable [{dq[0, 0]:+.3f}, {dq[1, 0]:+.3f}]; ΔAUC etiqueta astra [{dq[0, 1]:+.3f}, {dq[1, 1]:+.3f}]; "
    f"Δlift@10 % etiqueta fable [{dq[0, 2]:+.3f}, {dq[1, 2]:+.3f}]; Δlift@10 % etiqueta astra [{dq[0, 3]:+.3f}, {dq[1, 3]:+.3f}].")

(OUT / "verif_artefacto_y_comparacion_log.md").write_text("\n".join(lines), encoding="utf8")
tabr.to_csv(OUT / "verif_artefacto_y_comparacion_reentrenos.csv")
print("listo:", OUT / "verif_artefacto_y_comparacion_log.md")
