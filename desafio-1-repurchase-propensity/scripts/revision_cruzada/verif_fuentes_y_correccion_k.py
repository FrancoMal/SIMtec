"""Verificación independiente (rol escéptico) del bloque 'fuentes_y_correccion_k' de docs/04_revision_cruzada.md.

Afirmaciones que se intentan refutar:
  (a) plan oficial Ford Argentina: Ranger nueva (P703) 16.000 km ó 12 meses; Ranger anterior (T6/P375) 10.000 km ó 1 año.
      Fuentes: manual de garantía Ranger 2016 (PDF ya descargado) y snapshot Playwright de ford.com.ar (WebFetch da 403).
  (b) con K = 16.000 los datos de fable (EDA 02: km/n 16.040-16.173 en P703; Δkm 16.138) son consistentes con el nominal.
      Se recalcula km/n y Δkm desde data/interim/agenda.parquet con filtros propios (no se reutiliza el código del EDA).
  (c) cambiar K de 15.000 a 16.000 dejó 142.558 ventanas evaluables, churn 41,6 %, test 19.704 y ROC-AUC 0,739.
      Se reconstruyen las ventanas con K = 15.000 y con K = 16.000 usando el módulo de fable y se recalcula el AUC
      desde data/models/test_scored.parquet con sklearn.
  (d) la página de Ford muestra descuentos por continuidad 5/10/15 % (2°, 3°, 4°+ service).
  (e) docs/informe_final.md y reports/informe_final.pdf no contienen '27.327' ni 'enero y abril' y sus cifras
      coinciden con reports/modelo/resumen.md (se derivan las cifras esperadas de los artefactos de la corrida).

Uso (desde desafio-1-repurchase-propensity):
  PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/verif_fuentes_y_correccion_k.py
Escribe la salida cruda en reports/revision_cruzada/verif_fuentes_y_correccion_k_salida.txt. No toca nada de astra.
"""
from __future__ import annotations

import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd
import pypdf
from sklearn.metrics import average_precision_score, roc_auc_score

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.io import load_sales  # noqa: E402
from repurchase.ventanas import WindowParams, build_windows, vehicle_master  # noqa: E402

MANUAL_PDF = Path(r"C:/Users/Usuario/.claude/projects/G--SIMtec-fable/28dff193-8508-4393-8dee-77ce51636f75/tool-results"
                  r"/webfetch-1789515918509-hcj2n9.pdf")
SNAP_DIR = ROOT.parent / ".playwright-mcp"
SCRATCH = Path(r"F:/Caches/Temp/claude/G--SIMtec-fable/28dff193-8508-4393-8dee-77ce51636f75/scratchpad")
OUT = ROOT / "reports/revision_cruzada/verif_fuentes_y_correccion_k_salida.txt"

_lines: list[str] = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s, flush=True)
    _lines.append(s)


def fmt_int(n) -> str:
    return f"{int(round(n)):,}".replace(",", ".")


def fmt_pct(x, nd=1) -> str:
    return (f"{100 * x:.{nd}f}".replace(".", ",")) + " %"


def fmt_dec(x, nd=3) -> str:
    return f"{x:.{nd}f}".replace(".", ",")


def mtime(p: Path) -> str:
    return datetime.fromtimestamp(os.stat(p).st_mtime).strftime("%Y-%m-%d %H:%M:%S")


# ==================================================================================================
say("=" * 100)
say("A. Manual de garantía Ranger 2016 (PDF descargado) — afirmación (a), Ranger anterior")
say("=" * 100)
r = pypdf.PdfReader(MANUAL_PDF)
pages = [(i + 1, p.extract_text() or "") for i, p in enumerate(r.pages)]
say(f"páginas: {len(pages)}; CreationDate: {r.metadata.get('/CreationDate')}; título p.1: {pages[0][1].splitlines()[0]!r}")
for pat in [r"10\.000 km ó 12 meses", r"10\.000 km ó 1 año", r"20\.000 km ó 2 años", r"Duratorq", r"16\.000", r"15\.000",
            r"12 meses ó 20\.000 km"]:
    hits = [n for n, t in pages if re.search(pat, t)]
    say(f"  patrón {pat!r}: páginas {hits}")
p18 = dict(pages)[18]
i = p18.find("10.000 km ó 12 meses")
say("  p.18 contexto:", re.sub(r"\s+", " ", p18[max(0, i - 120): i + 60]))
say("  p.18 motores listados:", [m for m in ["3.2L", "2.2L", "2.5L", "Duratorq", "Duratec"] if m in p18])
p24 = dict(pages)[24]
say("  p.24 primeras filas de la tabla del plan:", " | ".join(p24.splitlines()[3:7]))
say("  NOTA: el manual es de 2016 (Ranger T6 = P375, motores 3.2/2.2 Duratorq y 2.5 nafta). La cita '10.000 km ó 1 año' es literal.")
say("  NOTA: en p.9 '12 meses ó 20.000 km' es la garantía del material de fricción del embrague, no el plan.")

# ==================================================================================================
say("\n" + "=" * 100)
say("B. Página ford.com.ar nueva Ranger 2.0L Diesel — snapshot Playwright (WebFetch: HTTP 403) — afirmaciones (a) y (d)")
say("=" * 100)
snaps = sorted(SNAP_DIR.glob("page-*.yml")) + sorted(SCRATCH.glob("ford_*.yml"))
for y in snaps:
    t = y.read_text(encoding="utf8")
    say(f"snapshot {y.name} ({mtime(y)}), {len(t):,} chars")
    for pat in [r"revisión de 16\.000 km ó 12 meses", r"revisión de 10\.000 km ó 12 meses", r"Ranger 2\.0L Diesel",
                r"Ranger 3\.0L V6 Diesel", r"Ranger Raptor", r"Ranger \(Hasta 2023\)", r"Ranger 3\.2L Diesel",
                r"2° SERVICIO 5%", r"3° SERVICIO 10%", r"4° SERVICIO EN ADELANTE: 15%", r"“CON VOS”|\"CON VOS\"|CON VOS",
                r"VIGENTES DESDE EL \d\d/\d\d/\d{4} AL \d\d/\d\d/\d{4}", r"15\.000", r"10\.000 km"]:
        m = re.findall(pat, t)
        say(f"  {pat!r}: {len(m)} hit(s)" + (f" -> {m[0]!r}" if m and len(pat) > 20 else ""))
    tabs = list(dict.fromkeys(re.findall(r"\b(\d{1,3} mil)\b", t)))  # tabs de servicios: '16 mil', '32 mil', ...
    say("  tabs de servicios (km):", tabs)
    mvig = re.search(r"VIGENTES DESDE EL (\d\d/\d\d/\d{4}) AL (\d\d/\d\d/\d{4})", t)
    if mvig:
        say("  vigencia de precios:", mvig.group(1), "a", mvig.group(2))
logs = sorted(SNAP_DIR.glob("console-*.log"))
for lg in logs:
    urls = set(re.findall(r"https://www\.ford\.com\.ar/posventa/[^\s:]+", lg.read_text(encoding="utf8", errors="ignore")))
    say("  URL(s) en el log de consola del snapshot:", sorted(urls))

# ==================================================================================================
say("\n" + "=" * 100)
say("C. Recalculo independiente de km/n y Δkm desde data/interim/agenda.parquet — afirmación (b)")
say("=" * 100)
cols = ["schedule_id", "vehicle_id", "StatusARG", "ScheduleDate", "EffectiveCheckinDate", "VehicleCurrentKM",
        "ServiceMaintenance", "ShortVehicleModelGroupTreated"]
ag = pd.read_parquet(ROOT / "data/interim/agenda.parquet", columns=cols).drop_duplicates()
m = ag[ag["StatusARG"].eq("(60) Concluido") & ag["ServiceMaintenance"].notna() & ag["vehicle_id"].notna()]
# una fila por turno: n = menor número de service del turno; km = odómetro del evento
t = (m.groupby("schedule_id", sort=False)
       .agg(vehicle_id=("vehicle_id", "first"), gen=("ShortVehicleModelGroupTreated", "first"),
            date=("ScheduleDate", "first"), km=("VehicleCurrentKM", "first"), n=("ServiceMaintenance", "min"))
       .reset_index())
t["km"] = t["km"].astype(float).where((t["km"] >= 100) & (t["km"] <= 1_000_000))
say(f"turnos concluidos con n° de service: {len(t):,}; vehículos: {t.vehicle_id.nunique():,}")
# una fila por vehículo-día (turnos duplicados el mismo día)
t = (t.sort_values(["vehicle_id", "date", "km"]).groupby(["vehicle_id", "date"], as_index=False)
       .agg(gen=("gen", "first"), km=("km", "max"), n=("n", "min")))
# el mismo service cargado dos veces a <= 30 días (mismo n): se conserva el primero
t = t.sort_values(["vehicle_id", "date"]).reset_index(drop=True)
g = t.groupby("vehicle_id")
dup = (g["date"].diff().dt.days <= 30) & (t["n"] == g["n"].shift(1))
say(f"vehículo-día: {len(t):,}; duplicados mismo n <= 30 d eliminados: {int(dup.sum()):,}")
t = t[~dup].copy()
t["km_n"] = t["km"] / t["n"]
res_kmn = {}
for gen, ns in [("RANGER (P703)", list(range(1, 8))), ("RANGER (P375)", list(range(2, 13)))]:
    sub = t[t["gen"].eq(gen) & t["km"].notna()]
    med = sub.groupby("n")["km_n"].median()
    cnt = sub.groupby("n").size()
    sel = med.reindex(ns)
    res_kmn[gen] = (sel.min(), sel.max())
    say(f"{gen}: km/n mediana por n = " + ", ".join(f"{int(k)}:{v:,.0f} (n={cnt.get(k, 0):,})" for k, v in sel.items()))
    say(f"   rango n={ns[0]}..{ns[-1]}: {sel.min():,.0f} - {sel.max():,.0f}")
# Δkm entre services consecutivos (n -> n+1)
t = t.sort_values(["vehicle_id", "date"]).reset_index(drop=True)
g = t.groupby("vehicle_id")
t["dkm"] = t["km"] - g["km"].shift(1)
t["dn"] = t["n"] - g["n"].shift(1)
for gen in ["RANGER (P703)", "RANGER (P375)"]:
    sub = t[t["gen"].eq(gen) & t["dn"].eq(1) & t["dkm"].gt(0)]
    say(f"{gen}: Δkm mediana n->n+1 = {sub.dkm.median():,.0f} (p25 {sub.dkm.quantile(.25):,.0f}, p75 "
        f"{sub.dkm.quantile(.75):,.0f}, n={len(sub):,}); todos los pares consecutivos con Δkm>0: "
        f"{t[t.gen.eq(gen) & t.dkm.gt(0)].dkm.median():,.0f}")
say("Lectura: atraso relativo del km/n mediano respecto del nominal candidato")
for gen, K in [("RANGER (P703)", 16000), ("RANGER (P703)", 15000), ("RANGER (P375)", 10000)]:
    lo, hi = res_kmn[gen]
    say(f"   {gen} con K={K:,}: km/n mediano llega {100 * (lo / K - 1):+.1f} % a {100 * (hi / K - 1):+.1f} % del nominal")
say("NOTA: los datos por sí solos no fijan el nominal (16.040 puede ser 16.000 + 0,25 % o 15.000 + 6,9 %); lo que zanja es la fuente.")
say("      El argumento de consistencia es que con 16.000 el atraso relativo del P703 (0,3-1,1 %) queda en la misma escala que")
say("      el del P375 con 10.000 (1,3-3,3 %), y con 15.000 sería 7-8 %, fuera de escala.")

# ==================================================================================================
say("\n" + "=" * 100)
say("D. Reconstrucción de ventanas con K = 15.000 y K = 16.000 (módulo de fable) — afirmación (c)")
say("=" * 100)
cfg = json.load(open(ROOT / "config/params.json", encoding="utf8"))["ventana"]
say("config/params.json ventana:", json.dumps(cfg, ensure_ascii=False))
t0 = time.time()
appt = appointments()
sales = load_sales()
say(f"appointments: {len(appt):,} turnos; sales: {len(sales):,} ({time.time() - t0:.0f} s)")
p16 = WindowParams.from_dict(cfg)
cfg15 = dict(cfg)
cfg15["km_by_generation"] = {"RANGER (P703)": 15000, "RANGER RAPTOR (P703)": 15000, "RANGER (P375)": 10000,
                             "RANGER RAPTOR": 10000}
cfg15["km_interval"] = 15000
p15 = WindowParams.from_dict(cfg15)


def resumen_ventanas(w: pd.DataFrame, tag: str) -> dict:
    ev = w[w["status"].eq("evaluable")]
    te = ev[(ev["scoring_date"] >= "2026-01-01") & (ev["scoring_date"] <= "2026-03-28")]
    tr = ev[ev["scoring_date"] <= "2025-09-30"]
    va = ev[(ev["scoring_date"] > "2025-09-30") & (ev["scoring_date"] <= "2025-12-31")]
    d = dict(tag=tag, total=len(w), evaluables=len(ev), churn=ev["label_churn"].mean(),
             censuradas=int(w["status"].eq("censurada").sum()), preempted=int(w["status"].eq("preempted").sum()),
             train=len(tr), valid=len(va), test=len(te), churn_test=te["label_churn"].mean(),
             test_max_scoring=str(te["scoring_date"].max().date()))
    say(f"[{tag}] total {d['total']:,} | evaluables {d['evaluables']:,} churn {d['churn']:.4f} | censuradas "
        f"{d['censuradas']:,} | preempted {d['preempted']:,} | train {d['train']:,} valid {d['valid']:,} test {d['test']:,} "
        f"(churn test {d['churn_test']:.4f}, último scoring {d['test_max_scoring']})")
    return d


t0 = time.time()
w16 = build_windows(appt, sales, params=p16, cutoff=CUTOFF)
say(f"build_windows K=16.000: {time.time() - t0:.0f} s")
d16 = resumen_ventanas(w16, "K=16.000 (reconstruido)")
t0 = time.time()
w15 = build_windows(appt, sales, params=p15, cutoff=CUTOFF)
say(f"build_windows K=15.000: {time.time() - t0:.0f} s")
d15 = resumen_ventanas(w15, "K=15.000 (reconstruido)")
wp = pd.read_parquet(ROOT / "data/processed/ventanas.parquet")
dp = resumen_ventanas(wp, "data/processed/ventanas.parquet")
say("¿parquet == reconstrucción K=16.000?", {k: (dp[k] == d16[k]) for k in ["total", "evaluables", "censuradas", "test", "train", "valid"]},
    "k_gen en parquet:", wp["k_gen"].value_counts().to_dict())
say("PDF viejo del informe decía: 145.538 evaluables, 36.397 censuradas, train 103.841, valid 21.506, test 20.191 (churn 42,9 %).")
say("Reconstrucción K=15.000 da:", {k: d15[k] for k in ["evaluables", "censuradas", "train", "valid", "test"]},
    f"churn test {d15['churn_test']:.3f}")
# corrimiento del vencimiento para anclas de mantenimiento P703
key = ["vehicle_id", "anchor_date"]
mm = (w16[w16["anchor_type"].eq("maintenance") & w16["k_gen"].eq(16000)][key + ["due_date", "binding_rule", "scoring_date"]]
      .merge(w15[key + ["due_date", "binding_rule"]], on=key, suffixes=("_16", "_15")))
shift = (mm["due_date_16"] - mm["due_date_15"]).dt.days
say(f"corrimiento del vencimiento (K16 - K15) en anclas de mantenimiento P703: mediana {shift.median():.0f} d, "
    f"p25 {shift.quantile(.25):.0f}, p75 {shift.quantile(.75):.0f}, n={len(shift):,}; "
    f"sólo regla km: mediana {shift[mm.binding_rule_15.eq('km') & mm.binding_rule_16.eq('km')].median():.0f} d")
# generación desconocida -> K por default (km_interval)
vm = vehicle_master(appt, sales)
gen_map = vm.set_index("vehicle_id")["generation"]
wg = w16.assign(generation=w16["vehicle_id"].map(gen_map))
unk = ~wg["generation"].isin(list(dict(p16.km_by_generation).keys()))
say(f"ventanas cuya generación NO está en km_by_generation (reciben km_interval={p16.km_interval:.0f} por default): "
    f"{int(unk.sum()):,} en total, {int((unk & wg.status.eq('evaluable')).sum()):,} evaluables; "
    f"generaciones: {wg.loc[unk, 'generation'].fillna('<NaN>').value_counts().to_dict()}")

# ==================================================================================================
say("\n" + "=" * 100)
say("E. ROC-AUC recalculado desde data/models/test_scored.parquet — afirmación (c)")
say("=" * 100)
ts = pd.read_parquet(ROOT / "data/models/test_scored.parquet")
ev = wp[wp["status"].eq("evaluable")]
te_ids = set(ev[(ev["scoring_date"] >= "2026-01-01") & (ev["scoring_date"] <= "2026-03-28")]["window_id"])
say(f"test_scored: {len(ts):,} filas, window_id único: {ts.window_id.is_unique}, mismo conjunto que el test del parquet: "
    f"{set(ts.window_id) == te_ids}, churn {ts.label_churn.mean():.4f}")
chk = ts.merge(wp[["window_id", "label_churn"]], on="window_id", suffixes=("", "_parquet"))
say(f"etiquetas coinciden con el parquet: {(chk.label_churn == chk.label_churn_parquet).all()}")
auc_cal = roc_auc_score(ts["label_churn"], ts["p_lgbm_cal"])
auc_raw = roc_auc_score(ts["label_churn"], ts["p_lgbm_raw"])
ap_cal = average_precision_score(ts["label_churn"], ts["p_lgbm_cal"])
auc_lr = roc_auc_score(ts["label_churn"], ts["p_logreg"])
say(f"ROC-AUC LightGBM calibrado {auc_cal:.4f} | sin calibrar {auc_raw:.4f} | PR-AUC calibrado {ap_cal:.4f} | logreg {auc_lr:.4f}")
o = ts.sort_values("p_lgbm_cal", ascending=False)
k20 = int(round(0.2 * len(o)))
rec20 = o["label_churn"].iloc[:k20].sum() / o["label_churn"].sum()
say(f"recall@20 % {rec20:.3f} (contactados {k20:,}, capturados {int(o['label_churn'].iloc[:k20].sum()):,}); lift {rec20 / 0.2:.2f}")
met = pd.read_csv(ROOT / "data/models/metricas_test.csv")
say("metricas_test.csv:", met[["modelo", "n", "roc_auc", "pr_auc"]].round(4).to_string(index=False))

# ==================================================================================================
say("\n" + "=" * 100)
say("F. docs/informe_final.md y reports/informe_final.pdf vs artefactos de la corrida — afirmación (e)")
say("=" * 100)
md_p = ROOT / "docs/informe_final.md"
pdf_p = ROOT / "reports/informe_final.pdf"
res_p = ROOT / "reports/modelo/resumen.md"
say(f"mtime: informe_final.md {mtime(md_p)} | informe_final.pdf {mtime(pdf_p)} | resumen.md {mtime(res_p)} | "
    f"ventanas.parquet {mtime(ROOT / 'data/processed/ventanas.parquet')} | ablaciones.md {mtime(ROOT / 'reports/modelo/ablaciones.md')} | "
    f"sensibilidad_ventana.csv {mtime(ROOT / 'reports/modelo/sensibilidad_ventana.csv')}")
md = md_p.read_text(encoding="utf8")
md_n = re.sub(r"\s+", " ", md)
pr = pypdf.PdfReader(pdf_p)
say(f"PDF: {len(pr.pages)} páginas, CreationDate {pr.metadata.get('/CreationDate')}")
pdf_n = re.sub(r"\s+", " ", "\n".join(p.extract_text() or "" for p in pr.pages))

say("\nF.1 Cadenas obsoletas (corrida anterior con K = 15.000 / sin margen):")
stale = ["27.327", "enero y abril", "15.000", "20.191", "145.538", "36.397", "103.841", "21.506", "42,9 %", "16.629",
         "31.651", "1.825", "6.330", "9.495", "15.826", "0,736", "ECE = 0,012", "el de menor, 14 %", "64 % de los churners"]
for s in stale:
    say(f"   {s!r:28} md: {md_n.count(s):2d}   pdf: {pdf_n.count(s):2d}")
for mm_ in re.finditer(r"15\.000", md):
    say("   md contexto '15.000':", md[max(0, mm_.start() - 90): mm_.start() + 60].replace("\n", " "))

say("\nF.2 Cifras esperadas derivadas de los artefactos (data/models, reports/modelo) y presencia en md / pdf:")
info = json.load(open(ROOT / "data/models/info.json", encoding="utf8"))
cap = pd.read_csv(ROOT / "data/models/capacidad_LightGBM_calibrado.csv")
lift = pd.read_csv(ROOT / "data/models/lift_LightGBM_calibrado.csv")
seg = pd.read_csv(ROOT / "reports/modelo/segmentos_test.csv")
roi = pd.read_csv(ROOT / "reports/modelo/roi_por_capacidad.csv")
abl = pd.read_csv(ROOT / "reports/modelo/ablaciones.csv")
vol = pd.read_csv(ROOT / "reports/modelo/volumen_mensual_ventanas.csv")
sc = pd.read_parquet(ROOT / "data/processed/scores_actuales.parquet")
lg = met[met["modelo"].str.startswith("LightGBM calibrado")].iloc[0]
lr = met[met["modelo"].str.startswith("regresión")].iloc[0]
exp: list[tuple[str, str]] = []
exp += [("n_test", fmt_int(info["n_test"])), ("n_train", fmt_int(info["n_train"])), ("n_valid", fmt_int(info["n_valid"])),
        ("churn_test", fmt_pct(info["base_rate_test"])), ("roc_lgbm", fmt_dec(lg.roc_auc)), ("pr_lgbm", fmt_dec(lg.pr_auc)),
        ("brier_lgbm", fmt_dec(lg.brier)), ("ece_lgbm", fmt_dec(lg.ece)), ("roc_logreg", fmt_dec(lr.roc_auc)),
        ("pr_logreg", fmt_dec(lr.pr_auc)), ("evaluables", fmt_int(dp["evaluables"])), ("churn_evaluables", fmt_pct(dp["churn"])),
        ("censuradas", fmt_int(dp["censuradas"]))]
for _, rw in cap.iterrows():
    c = int(round(100 * rw.capacidad_pct))
    exp += [(f"cap{c}_contactados", fmt_int(rw.contactados)), (f"cap{c}_capturados", fmt_int(rw.churners_capturados)),
            (f"cap{c}_recall", fmt_pct(rw.recall)), (f"cap{c}_lift", fmt_dec(rw.lift, 1) + "×")]
exp += [("decil1_tasa", f"{100 * lift.iloc[0].tasa:.0f} %"), ("decil10_tasa", f"{100 * lift.iloc[-1].tasa:.0f} %")]
for _, rw in seg.iterrows():
    exp += [(f"seg_{rw.segmento}_churn", f"{100 * rw.tasa_churn:.0f} %"), (f"seg_{rw.segmento}_share", f"{100 * rw.share_churners:.0f} %")]
for _, rw in roi.iterrows():
    c = int(round(100 * rw.capacidad_pct))
    exp += [(f"roi{c}_modelo", fmt_int(rw.services_recuperados_modelo)), (f"roi{c}_azar", fmt_int(rw.services_recuperados_azar)),
            (f"roi{c}_incremental", f"+{100 * (rw.services_recuperados_modelo / rw.services_recuperados_azar - 1):.0f} %")]
r20 = roi[roi.capacidad_pct.eq(0.2)].iloc[0]
exp += [("roi20_usd_incremental_miles", f"USD {int(round(r20.ganancia_incremental_usd / 1000))}.000")]
for _, rw in abl.iterrows():
    exp += [(f"abl[{rw.variante[:28]}]_roc", fmt_dec(rw.roc_auc)), (f"abl[{rw.variante[:28]}]_pr", fmt_dec(rw.pr_auc))]
abl_first = abl[abl.variante.str.contains("primer")].iloc[0]
abl_next = abl[abl.variante.str.contains("siguientes")].iloc[0]
exp += [("abl_primer_n", "n = " + fmt_int(abl_first.n_test)), ("abl_siguientes_n", "n = " + fmt_int(abl_next.n_test))]
seg_col = [c for c in sc.columns if c.lower().startswith("segmento")]
say(f"scores_actuales.parquet: {len(sc):,} filas; columnas con 'segmento': {seg_col}; con 'turno': {[c for c in sc.columns if 'turno' in c.lower()]}")
exp += [("hoy_total", fmt_int(len(sc)))]
if seg_col:
    for s_, n_ in sc[seg_col[0]].value_counts().items():
        exp += [(f"hoy_seg_{s_}", fmt_int(n_))]
turno_cols = [c for c in sc.columns if "turno" in c.lower() and sc[c].dtype == bool]
if turno_cols:
    exp += [("hoy_con_turno", fmt_int(sc[turno_cols[0]].sum()))]
faltan_md, faltan_pdf = [], []
for name, s in exp:
    in_md, in_pdf = s in md_n, s in pdf_n
    if not in_md:
        faltan_md.append((name, s))
    if not in_pdf:
        faltan_pdf.append((name, s))
say(f"   cifras esperadas: {len(exp)}; ausentes en md: {len(faltan_md)}; ausentes en pdf: {len(faltan_pdf)}")
say("   AUSENTES EN md:", faltan_md)
say("   AUSENTES EN pdf:", faltan_pdf)

say("\nF.3 Otras cifras del informe contrastadas con los datos:")
say("   volumen mensual de ventanas (csv): 2025 min/max", vol[vol.mes.str.startswith("2025")].n.min(), vol[vol.mes.str.startswith("2025")].n.max(),
    "| 2026 ene-jul min/max", vol[vol.mes.str.startswith("2026") & ~vol.mes.eq("2026-08")].n.min(), vol[vol.mes.str.startswith("2026") & ~vol.mes.eq("2026-08")].n.max(),
    "| informe dice 'unos 5.000 a 6.000 vehículos' (§1) y '6.000 a 7.000 ventanas por mes' (§9)")
# clientes con 2+ vehículos entrando en ventana el mismo mes en los últimos 12 meses
w12 = wp[wp["status"].isin(["evaluable", "censurada"]) & (wp["scoring_date"] > CUTOFF - pd.Timedelta(days=365)) & wp["customer_id"].notna()].copy()
w12["mes"] = w12["scoring_date"].dt.to_period("M")
per = w12.groupby(["customer_id", "mes"]).size()
multi = per[per >= 2]
say(f"   últimos 12 meses: clientes-mes con 2+ vehículos en ventana: {len(multi):,} (clientes distintos {multi.reset_index().customer_id.nunique():,}); "
    f"ventanas involucradas {int(multi.sum()):,} de {len(w12):,} = {100 * multi.sum() / len(w12):.1f} % | informe: 'unos 1.200 clientes ... 13 % de las ventanas'")
veh_all = set(vm["vehicle_id"])
veh_win = set(wp.loc[~wp["status"].eq("fuera_de_rango"), "vehicle_id"])
solo_fuera = set(wp["vehicle_id"]) - veh_win
say(f"   vehículos en el maestro {len(veh_all):,}; con alguna ventana no 'fuera_de_rango' {len(veh_win):,}; sólo con ventanas fuera de rango "
    f"{len(solo_fuera):,}; sin ninguna ventana {len(veh_all - set(wp['vehicle_id'])):,} | informe: 'quedan fuera los 17.973 vehículos entregados antes de 2024 sin ningún mantenimiento'")
sens = pd.read_csv(ROOT / "reports/modelo/sensibilidad_ventana.csv")
say(f"   sensibilidad_ventana.csv: {len(sens)} filas; valores de km_by_generation: {sens.km_by_generation.fillna('<un solo K>').unique().tolist()}")
one_k = sens[sens.km_by_generation.isna()]
if len(one_k):
    say("   filas con un único K:\n" + one_k[["km_interval", "horizon_days", "n_evaluables", "churn_rate", "pct_preempted", "mediana_dias_retorno_vs_due"]].to_string(index=False))
say("   md §4 dice: 'Un único K para todo el parque: con 16.000 la P375 vence un mes tarde (más de la mitad ya volvió al abrir); con 10.000 la P703 vence antes de tiempo'")
say("   docs/02 §K dice: 'K = 15.000 para todo el parque: corre el vencimiento 33 días tarde en P375' (harness viejo)")

# ==================================================================================================
say("\n" + "=" * 100)
say("G. 'Un único K para todo el parque' (informe §4): K = 16.000 también para la P375, medido POR GENERACIÓN")
say("=" * 100)
cfg_all16 = dict(cfg)
cfg_all16["km_by_generation"] = {k: 16000 for k in cfg["km_by_generation"]}
w_all16 = build_windows(appt, sales, params=WindowParams.from_dict(cfg_all16), cutoff=CUTOFF)


def p375_stats(w: pd.DataFrame, tag: str):
    x = w.assign(generation=w["vehicle_id"].map(gen_map))
    x = x[x["generation"].eq("RANGER (P375)") & x["anchor_type"].eq("maintenance") & x["status"].isin(["evaluable", "preempted", "censurada"])]
    ret = x[x["next_maint_date"].notna() & x["status"].isin(["evaluable", "preempted"])]
    say(f"[{tag}] P375 anclas de mantenimiento: {len(x):,}; preempted (volvió antes de abrir) {x.status.eq('preempted').mean():.1%}; "
        f"retraso del retorno real vs vencimiento (mediana, sólo con retorno observado): {ret.days_next_vs_due.median():.0f} d; "
        f"retornos antes del vencimiento: {(ret.days_next_vs_due < 0).mean():.1%}")


p375_stats(w16, "K por generación (P375=10.000)")
p375_stats(w_all16, "K=16.000 para todos")
say("   informe §4 dice: 'con 16.000 la P375 vence un mes tarde (más de la mitad ya volvió al abrir)'; docs/02 decía lo mismo para K=15.000 (33 d, 51,6 %).")

OUT.write_text("\n".join(_lines), encoding="utf8")
say(f"\nsalida cruda escrita en {OUT}")
