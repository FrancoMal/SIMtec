"""Verificación escéptica del bloque 'reconciliacion' de docs/04_revision_cruzada.md (sección 1).

Recalcula con código propio, independiente de scripts/revision_cruzada/01_reconciliacion_definiciones.py:
  (a) etiqueta mensual de astra sobre las ventanas de fable (abr-jul 2026)             -> ¿80,2 %?
  (b) etiqueta de fable (due-30 / due+90, nivel vehículo) sobre las ventanas de astra   -> ¿44,0 % en 107.557?
  (c) % de los churn mensuales de abr-jul 2026 que vuelven antes de due+90              -> ¿41,3 %?
  (d) puntos de churn que agrega exigir el mismo customer_id en astra                   -> ¿3,1?
  (e) solapamiento de poblaciones y diferencia de vencimiento por vehículo             -> ¿76.830 / 77.973 / 92.838, -7 d?

Diferencias metodológicas deliberadas respecto del script original:
  * "hay evento en [a, b)" se resuelve con merge_asof (primer evento posterior a `a`) y no con un join
    many-to-many; no puede duplicar filas.
  * se usan TRES conjuntos de eventos: fable (check-in / turno), fable con fecha de checkout, y astra
    (eventos.parquet: maintenance & valid_complete, fecha = checkout, incluye Guarantee), para medir cuánto
    pesa la convención de fecha y la definición del evento.
  * las etiquetas target / target_vin de astra se RECALCULAN desde su eventos.parquet y se comparan con
    las columnas guardadas (no se confía en la lectura del código).
  * la diferencia de vencimiento por vehículo se calcula 1 a 1 (misma ancla) y no con un merge por
    vehicle_id que cruza ventanas distintas.

Sólo lectura sobre G:\\SIMtec-astra y G:\\SIMtec\\Dataset. Escribe únicamente en reports/revision_cruzada/.
Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/verif_reconciliacion.py
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(HERE / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.ventanas import WindowParams, maintenance_events  # noqa: E402

ASTRA = Path(r"G:\SIMtec-astra\desafio-1-repurchase-propensity")
OUT = config.REPORTS_DIR / "revision_cruzada"
OUT.mkdir(parents=True, exist_ok=True)
OBS_A = pd.Timestamp("2026-08-01")            # observed_until de astra (exclusivo)
MARGIN = CUTOFF - pd.Timedelta(days=30)       # 2026-07-26: horizonte "cerrado" según fable
D30, D90 = pd.Timedelta(days=30), pd.Timedelta(days=90)
T0, T1 = pd.Timestamp("2026-04-01"), pd.Timestamp("2026-08-01")   # abr-jul 2026 (due en [T0, T1))

lines: list[str] = []


def log(s: str = ""):
    print(s, flush=True)
    lines.append(s)


def ns(s: pd.Series) -> pd.Series:
    return pd.to_datetime(s).astype("datetime64[ns]")


def first_event_after(win: pd.DataFrame, events: pd.DataFrame, start: pd.Series, inclusive: bool) -> pd.Series:
    """Fecha del primer evento del vehículo con event_date >= start (inclusive) o > start. NaT si no hay."""
    d = pd.DataFrame({"vehicle_id": win["vehicle_id"].astype(str).values, "_s": ns(start).values})
    d["_ix"] = np.arange(len(d))
    d = d.sort_values("_s")
    ev = pd.DataFrame({"vehicle_id": events["vehicle_id"].astype(str).values, "_e": ns(events["event_date"]).values})
    ev = ev.dropna().sort_values("_e")
    m = pd.merge_asof(d, ev, left_on="_s", right_on="_e", by="vehicle_id", direction="forward",
                      allow_exact_matches=inclusive).sort_values("_ix")
    return pd.Series(m["_e"].values, index=win.index)


def in_interval(win, events, start, end, incl_start, incl_end) -> pd.Series:
    fe = first_event_after(win, events, start, incl_start)
    end = ns(end)
    return fe.notna() & ((fe <= end) if incl_end else (fe < end))


def pct(x) -> str:
    return f"{100 * float(x):.1f} %"


# ------------------------------------------------------------------------------------------ datos
log("# Verificación independiente — bloque 'reconciliacion' (sección 1 de docs/04_revision_cruzada.md)\n")
log(f"Corrida: {datetime.now():%Y-%m-%d %H:%M}. Corte de datos (CUTOFF fable): {CUTOFF.date()}; margen de etiqueta: {MARGIN.date()}; "
    f"observed_until astra: {OBS_A.date()} (exclusivo).\n")

pq_f = config.PROCESSED_DIR / "ventanas.parquet"
mt = lambda p: datetime.fromtimestamp(Path(p).stat().st_mtime).strftime("%Y-%m-%d %H:%M:%S")
log("Archivos y mtimes (para saber sobre qué corrida se calculó cada cosa):")
for p in [pq_f, HERE / "config/params.json", OUT / "01_reconciliacion.md", HERE / "scripts/revision_cruzada/01_reconciliacion_definiciones.py",
          ASTRA / "data/processed/ventanas.parquet", ASTRA / "data/processed/eventos.parquet"]:
    log(f"- `{p}`: {mt(p)}")

cfg = json.loads((HERE / "config/params.json").read_text(encoding="utf8"))
params = WindowParams.from_dict(cfg["ventana"])
appt = appointments()
mF = maintenance_events(appt, params)
fable = pd.read_parquet(pq_f)
fable["vehicle_id"] = fable["vehicle_id"].astype(str)
for c in ["anchor_date", "due_date", "scoring_date", "horizon_end", "next_maint_date"]:
    fable[c] = ns(fable[c])
astra = pd.read_parquet(ASTRA / "data/processed/ventanas.parquet")
astra["vehicle_id"] = astra["vehicle_id"].astype(str)
for c in ["anchor_date", "due_date", "scoring_date", "window_end"]:
    astra[c] = ns(astra[c])
astra["due_day"] = astra["due_date"].dt.normalize()   # astra guarda el vencimiento con fracción de día
evA = pd.read_parquet(ASTRA / "data/processed/eventos.parquet")
evA["vehicle_id"] = evA["vehicle_id"].astype(str)
for c in ["maintenance", "valid_complete", "terminal"]:
    evA[c] = evA[c].astype(bool)
evA["event_date"] = ns(evA["event_date"])

log(f"\nK por generación en el parquet actual de fable: {fable['k_gen'].value_counts().to_dict()} "
    f"(params.json: {cfg['ventana']['km_by_generation']}).")
log(f"Ventanas de fable por estado: {fable['status'].value_counts().to_dict()}.")

# --- tres conjuntos de eventos "mantenimiento completado", nivel vehículo
co = (appt[appt["is_completed_maintenance"] & appt["vehicle_id"].notna()]
      .groupby(["vehicle_id", "event_date"])["EffectiveCheckoutDate"].max())
EV_F = mF[["vehicle_id", "event_date", "customer_id"]].copy()                       # fable: check-in / turno
EV_F["vehicle_id"] = EV_F["vehicle_id"].astype(str)
key = pd.MultiIndex.from_frame(mF[["vehicle_id", "event_date"]])
EV_Fco = EV_F.assign(event_date=pd.Series(co.reindex(key).values).fillna(EV_F["event_date"]).values)  # fable con checkout
EV_A = evA[evA["maintenance"] & evA["valid_complete"]][["vehicle_id", "event_date", "customer_id", "schedule_id"]].copy()  # astra
EVENTS = {"fable (check-in/turno)": EV_F, "fable con fecha de checkout": EV_Fco, "astra (checkout, incl. Guarantee)": EV_A}
gap_co = (EV_Fco["event_date"] - EV_F["event_date"]).dt.days
log(f"Eventos: fable {len(EV_F):,}; astra (maintenance & valid_complete) {len(EV_A):,}. "
    f"Checkout − fecha fable en los eventos de fable: mediana {gap_co.median():.0f} d, media {gap_co.mean():.2f} d, "
    f"p90 {gap_co.quantile(.9):.0f} d, > 0 en {pct((gap_co > 0).mean())} de los eventos.")

# ------------------------------------------------------------------------------------------ (a)
log("\n## (a) Etiqueta mensual de astra sobre las ventanas de fable — afirmación: churn abr-jul 2026 = 80,2 %\n")
w = fable[fable["status"].isin(["evaluable", "censurada", "preempted"])].copy()
w["M0"] = w["due_date"].dt.to_period("M").dt.to_timestamp()
w["M1"] = w["M0"] + pd.offsets.MonthBegin(1)
w = w[w["M1"] <= OBS_A].copy()
# ancla en fecha de checkout (para que, con eventos fechados por checkout, el propio evento ancla no cuente como "volvió")
w["anchor_co"] = pd.Series(co.reindex(pd.MultiIndex.from_frame(w[["vehicle_id", "anchor_date"]])).values, index=w.index)
w["anchor_co"] = ns(w["anchor_co"].fillna(w["anchor_date"]))
w["mes_due"] = w["due_date"].dt.to_period("M")
in_test = w["due_date"].between(T0, T1 - pd.Timedelta(days=1))
res_a = {}
for name, ev in EVENTS.items():
    anchor = w["anchor_date"] if name.startswith("fable (") else w["anchor_co"]
    fe = first_event_after(w, ev, anchor, inclusive=False)
    elig = ~(fe.notna() & (fe < w["M0"]))                      # astra: si volvió antes del 1°, la ancla nueva reemplaza a la vieja
    ret = in_interval(w, ev, w["M0"], w["M1"], True, False)    # retorno en [1°, fin de mes)
    churn = (~ret).astype(float)
    sel = elig & in_test
    res_a[name] = dict(elig=elig, churn=churn)
    bym = churn[sel].groupby(w.loc[sel, "mes_due"]).agg(["size", "mean"])
    log(f"- eventos **{name}**: n={int(sel.sum()):,}, churn mensual abr-jul = **{pct(churn[sel].mean())}** "
        f"(por mes: {', '.join(f'{m} {pct(v)} (n={n:,})' for m, (n, v) in bym.iterrows())})")
    if name.startswith("fable ("):
        sel_c = sel & w["customer_id"].notna()
        log(f"  - exigiendo customer_id no nulo en la ventana (astra descarta VIN sin cliente): n={int(sel_c.sum()):,}, "
            f"churn = {pct(churn[sel_c].mean())}")
# variante: la regla completa de astra (mismo customer_id; retorno anónimo -> indeterminado) con eventos de astra
base = w[res_a["astra (checkout, incl. Guarantee)"]["elig"] & in_test][["vehicle_id", "customer_id", "M0", "M1"]].copy()
base["_ix"] = np.arange(len(base))
j = base.merge(EV_A, on="vehicle_id", how="left")
inw = j["event_date"].ge(j["M0"]) & j["event_date"].lt(j["M1"])
j["same"] = inw & j["customer_id_x"].notna() & j["customer_id_y"].notna() & (j["customer_id_x"].astype(str) == j["customer_id_y"].astype(str))
j["anon"] = inw & j["customer_id_y"].isna()
g = j.groupby("_ix").agg(same=("same", "any"), anon=("anon", "any"))
t_same = np.where(g["same"], 0.0, np.where(g["anon"], np.nan, 1.0))
log(f"- regla completa de astra (eventos astra, **mismo customer_id**, anónimo → indeterminado) sobre las ventanas de fable: "
    f"churn = **{pct(np.nanmean(t_same))}** (n etiquetadas {int(np.isfinite(t_same).sum()):,}, indeterminadas {int(np.isnan(t_same).sum()):,}).")
sel_f = res_a["fable (check-in/turno)"]["elig"] & in_test
log(f"- referencia: astra en su propio test abr-jul 2026: {pct(astra.loc[astra['scoring_date'].between(T0, '2026-07-01') & astra['target'].notna(), 'target'].mean())} "
    f"(n={int((astra['scoring_date'].between(T0, '2026-07-01') & astra['target'].notna()).sum()):,}).")

# ------------------------------------------------------------------------------------------ (b)
log("\n## (b) Etiqueta de fable (due−30 / due+90, nivel vehículo) sobre las ventanas de astra — afirmación: 44,0 % en 107.557\n")
b_all = astra[astra["window_end"] <= OBS_A].copy()
b_all["open_F"] = pd.concat([b_all["scoring_date"], b_all["due_day"] - D30], axis=1).max(axis=1)
b_all["end_F"] = b_all["due_day"] + D90
b_all["open_F_raw"] = pd.concat([b_all["scoring_date"], b_all["due_date"] - D30], axis=1).max(axis=1)
b_all["end_F_raw"] = b_all["due_date"] + D90
b_all["mes"] = b_all["scoring_date"].dt.to_period("M")


def churn_fable_on_astra(b, ev, incl_start=True, raw=False):
    o, e = ("open_F_raw", "end_F_raw") if raw else ("open_F", "end_F")
    return (~in_interval(b, ev, b[o], b[e], incl_start, True)).astype(float)


b = b_all[b_all["target"].notna() & (b_all["end_F"] <= MARGIN)].copy()
n_raw = int((b_all["target"].notna() & (b_all["end_F_raw"] <= MARGIN)).sum())
log(f"Ventanas de astra con target no nulo y due+90 ≤ {MARGIN.date()}: **{len(b):,}** con el vencimiento normalizado a día "
    f"({n_raw:,} si se compara el `due_date` fraccionario de astra contra la medianoche del {MARGIN.date()}, como el script original); "
    f"rango de scoring {b['scoring_date'].min():%Y-%m} a {b['scoring_date'].max():%Y-%m}; churn mensual de astra en ellas: {pct(b['target'].mean())}.")
for name, ev in EVENTS.items():
    cF = churn_fable_on_astra(b, ev)
    log(f"- eventos **{name}**, inicio inclusivo, vencimiento normalizado a día: churn fable = **{pct(cF.mean())}**"
        + (f"; inicio exclusivo: {pct(churn_fable_on_astra(b, ev, False).mean())}; con due sin normalizar (como el script original): "
           f"{pct(churn_fable_on_astra(b, ev, True, True).mean())}" if name.startswith("fable (") else ""))
cF_ref = churn_fable_on_astra(b, EV_F)
b["churn_F"] = cF_ref
log(f"- abr 2026 solamente (único mes del test de astra con due+90 cerrado al {MARGIN.date()}): n={int((b['mes'] == '2026-04').sum()):,}, "
    f"churn fable = {pct(b.loc[b['mes'] == '2026-04', 'churn_F'].mean())}, churn mensual astra = {pct(b.loc[b['mes'] == '2026-04', 'target'].mean())}.")
b2 = b_all[b_all["end_F"] <= MARGIN].copy()
log(f"- incluyendo también las ventanas con target indeterminado (NaN) de astra: n={len(b2):,}, churn fable = {pct(churn_fable_on_astra(b2, EV_F).mean())}.")
b3 = b_all[b_all["target"].notna() & (b_all["end_F"] <= CUTOFF)].copy()
log(f"- con horizonte cerrado al corte sin margen ({CUTOFF.date()}): n={len(b3):,}, churn fable = {pct(churn_fable_on_astra(b3, EV_F).mean())}.")
# consistencia lógica: churn_F=1 debería implicar target=1 (el mes calendario está contenido en [open_F, end_F])
log(f"- consistencia: ventanas con churn fable = 1 y target astra = 0: {int(((b['churn_F'] == 1) & (b['target'] == 0)).sum()):,} "
    f"(esperado ~0: sólo por diferencia de eventos check-in vs checkout / mismo cliente).")
# selección: las ventanas de astra excluyen anclas que volvieron entre due-30 y el 1° del mes
ev_f = fable[fable["status"] == "evaluable"].copy()
ev_f["M0"] = ev_f["due_date"].dt.to_period("M").dt.to_timestamp()
early = ev_f["next_maint_date"].notna() & (ev_f["next_maint_date"] > ev_f["scoring_date"]) & (ev_f["next_maint_date"] < ev_f["M0"])
log(f"- selección implícita: en las ventanas evaluables de fable ({len(ev_f):,}, churn {pct(ev_f['label_churn'].mean())}), "
    f"{pct(early.mean())} vuelve entre la apertura (due−30) y el 1° del mes del vencimiento; astra nunca crea esas ventanas. "
    f"Churn de fable condicionado a NO haber vuelto antes del 1°: **{pct(ev_f.loc[~early, 'label_churn'].mean())}** (n={int((~early).sum()):,}).")

# ------------------------------------------------------------------------------------------ (c)
log("\n## (c) De los churn mensuales de abr-jul 2026 (anclas de fable), % que completa el mantenimiento antes de due+90 — afirmación: 41,3 %\n")
eligF, churnF = res_a["fable (check-in/turno)"]["elig"], res_a["fable (check-in/turno)"]["churn"]
for thr_name, thr in [("horizonte ≤ CUTOFF = 2026-08-25 (como el script original)", CUTOFF),
                      ("horizonte ≤ margen fable = 2026-07-26", MARGIN)]:
    sel = eligF & in_test & (churnF == 1) & (w["horizon_end"] <= thr)
    sub = w[sel]
    ret120 = in_interval(sub, EV_F, sub["scoring_date"], sub["horizon_end"], False, True)
    ret_co = in_interval(sub, EV_A, sub["scoring_date"], sub["horizon_end"], False, True)
    log(f"- {thr_name}: n churn mensual = {len(sub):,}, vencimientos entre {sub['due_date'].min():%Y-%m-%d} y {sub['due_date'].max():%Y-%m-%d}; "
        f"vuelven antes de due+90: **{pct(ret120.mean())}** (eventos fable) / {pct(ret_co.mean())} (eventos astra).")
    # ¿y sin condicionar al horizonte cerrado? cota inferior (los que ya volvieron aunque el horizonte siga abierto)
sel_open = eligF & in_test & (churnF == 1)
sub = w[sel_open]
ret_open = in_interval(sub, EV_F, sub["scoring_date"], sub["horizon_end"].clip(upper=CUTOFF), False, True)
log(f"- todos los churn mensuales abr-jul (n={len(sub):,}), contando sólo lo observado hasta el corte: ya volvió {pct(ret_open.mean())} (cota inferior; jun-jul censurados).")
# lo mismo sobre las ventanas REALES de astra (sección 0 del doc dice 'el 41 % de los churn de astra')
ta = astra[astra["scoring_date"].between(T0, "2026-07-01") & (astra["target"] == 1)].copy()
ta["end_F"] = ta["due_day"] + D90
for thr_name, thr in [("≤ 2026-07-26", MARGIN), ("≤ 2026-08-25", CUTOFF)]:
    s = ta[ta["end_F"] <= thr]
    r1 = in_interval(s, EV_F, s["scoring_date"], s["end_F"], True, True)
    r2 = in_interval(s, EV_A, s["scoring_date"], s["end_F"], True, True)
    log(f"- sobre los churn REALES de astra en su test (target=1, abr-jul 2026) con due+90 {thr_name}: n={len(s):,} "
        f"(vencimientos {s['due_day'].min():%Y-%m-%d} a {s['due_day'].max():%Y-%m-%d}); vuelven antes de due+90: **{pct(r1.mean())}** (eventos fable, VIN) / {pct(r2.mean())} (eventos astra, VIN).")
ta_all = astra[astra["target"].notna() & (astra["target"] == 1)].copy()
ta_all["end_F"] = ta_all["due_day"] + D90
s = ta_all[ta_all["end_F"] <= MARGIN]
r1 = in_interval(s, EV_F, s["scoring_date"], s["end_F"], True, True)
log(f"- ídem sobre TODOS los churn de astra con due+90 ≤ {MARGIN.date()} (n={len(s):,}): vuelven antes de due+90: {pct(r1.mean())}.")

# ------------------------------------------------------------------------------------------ (d)
log("\n## (d) Exigir el mismo customer_id (target vs target_vin de astra) — afirmación: suma 3,1 puntos de churn\n")
both = astra[astra["target"].notna() & astra["target_vin"].notna()]
diff = both["target"] - both["target_vin"]
log(f"- columnas guardadas por astra, todas las ventanas etiquetadas (n={len(both):,}): churn mismo usuario {pct(both['target'].mean())} vs mismo VIN {pct(both['target_vin'].mean())}; "
    f"diferencia **{100 * diff.mean():.2f} puntos**; P(target=1 & vin=0) = {pct(((both['target'] == 1) & (both['target_vin'] == 0)).mean())}; "
    f"P(target=0 & vin=1) = {int(((both['target'] == 0) & (both['target_vin'] == 1)).sum())} casos.")
log(f"- expresado sobre los churn (no sobre las ventanas): {pct(diff.mean() / both['target'].mean())} de las ventanas con target=1 son retornos del mismo VIN con otro id.")
tst = both[both["scoring_date"].between(T0, "2026-07-01")]
log(f"- en el test de astra (abr-jul 2026, n={len(tst):,}): {pct(tst['target'].mean())} vs {pct(tst['target_vin'].mean())}, "
    f"diferencia {100 * (tst['target'] - tst['target_vin']).mean():.2f} puntos.")
# recomputo independiente de target y target_vin desde eventos.parquet
A = astra[["row_id", "vehicle_id", "customer_id", "scoring_date", "window_end", "target", "target_vin"]].copy()
jj = A.merge(EV_A, on="vehicle_id", how="left", suffixes=("", "_ev"))
inw = jj["event_date"].ge(jj["scoring_date"]) & jj["event_date"].lt(jj["window_end"])
jj["vin"] = inw
jj["same"] = inw & jj["customer_id_ev"].notna() & (jj["customer_id"].astype(str) == jj["customer_id_ev"].astype(str))
jj["anon"] = inw & jj["customer_id_ev"].isna()
gg = jj.groupby("row_id").agg(vin=("vin", "any"), same=("same", "any"), anon=("anon", "any")).reindex(A["row_id"]).fillna(False)
lab = A["window_end"] <= OBS_A
my_vin = np.where(lab, (~gg["vin"].values).astype(float), np.nan)
my_t = np.where(lab, np.where(gg["same"].values, 0.0, np.where(gg["anon"].values, np.nan, 1.0)), np.nan)
ok_vin = (pd.Series(my_vin).fillna(-1).values == A["target_vin"].fillna(-1).values).mean()
ok_t = (pd.Series(my_t).fillna(-1).values == A["target"].fillna(-1).values).mean()
log(f"- recomputo independiente desde eventos.parquet: coincide con `target` en {pct(ok_t)} de las filas y con `target_vin` en {pct(ok_vin)}; "
    f"churn recalculado {pct(np.nanmean(my_t))} vs {pct(np.nanmean(my_vin))} → diferencia {100 * (np.nanmean(my_t) - np.nanmean(my_vin)):.2f} puntos.")
# ¿el "otro id" ya era conocido en ese vehículo (mismo hogar / flota / doble alta) o es un usuario nunca visto?
falsos = both[(both["target"] == 1) & (both["target_vin"] == 0)][["row_id", "vehicle_id", "customer_id", "sale_customer", "scoring_date", "window_end"]]
r = falsos.merge(EV_A, on="vehicle_id", suffixes=("", "_ev"))
r = r[r["event_date"].ge(r["scoring_date"]) & r["event_date"].lt(r["window_end"]) & r["customer_id_ev"].notna()]
prev = evA[evA["terminal"] & evA["customer_id"].notna()][["vehicle_id", "customer_id", "event_date"]].rename(columns={"customer_id": "cid_prev", "event_date": "d_prev"})
rp = r.merge(prev, on="vehicle_id")
rp = rp[(rp["cid_prev"].astype(str) == rp["customer_id_ev"].astype(str)) & (rp["d_prev"] < rp["scoring_date"])]
known_before = set(rp["row_id"])
is_sale = set(r.loc[r["sale_customer"].notna() & (r["sale_customer"].astype(str) == r["customer_id_ev"].astype(str)), "row_id"])
log(f"- de esas {len(falsos):,} ventanas 'churn por identidad': el id que volvió ya había tenido un turno con ese vehículo antes del scoring en "
    f"{pct(len(known_before) / len(falsos))}; es el comprador de la venta en {pct(len(is_sale) / len(falsos))}; nunca visto en ese vehículo en "
    f"{pct(1 - len(known_before | is_sale) / len(falsos))}.")

# ------------------------------------------------------------------------------------------ (e)
log("\n## (e) Solapamiento de poblaciones y diferencia de vencimiento — afirmación: 76.830 en común de 77.973 (astra) y 92.838 (fable); mediana −7 d en abr-jul 2026\n")
va_all = set(astra["vehicle_id"])
va_lab = set(astra.loc[astra["target"].notna(), "vehicle_id"])
vf_ec = set(fable.loc[fable["status"].isin(["evaluable", "censurada"]), "vehicle_id"])
vf_ecp = set(fable.loc[fable["status"].isin(["evaluable", "censurada", "preempted"]), "vehicle_id"])
vf_any = set(fable.loc[fable["status"] != "fuera_de_rango", "vehicle_id"])
log(f"- astra: {len(va_all):,} vehículos con ventana (todas, incl. ago-2026 y target NaN); {len(va_lab):,} con al menos una ventana etiquetada.")
log(f"- fable: {len(vf_ec):,} (evaluable+censurada, como el script original); {len(vf_ecp):,} (+preempted); {len(vf_any):,} (todo salvo fuera_de_rango, incl. futuras).")
log(f"- en común: astra(todas) ∩ fable(eval+cens) = **{len(va_all & vf_ec):,}** ({pct(len(va_all & vf_ec) / len(va_all))} de astra, {pct(len(va_all & vf_ec) / len(vf_ec))} de fable); "
    f"astra(todas) ∩ fable(+preempted) = {len(va_all & vf_ecp):,}; astra ∩ fable(todo) = {len(va_all & vf_any):,}.")
only_a = va_all - vf_any
log(f"- vehículos de astra sin NINGUNA ventana en fable: {len(only_a):,}.")
# abr-jul 2026
a24 = astra[astra["scoring_date"].between(T0, "2026-07-01")].copy()
f24 = fable[(fable["status"] != "fuera_de_rango") & fable["due_date"].between(T0, T1 - pd.Timedelta(days=1))].copy()
log(f"- abr-jul 2026: vehículos con vencimiento en astra {a24['vehicle_id'].nunique():,} ({len(a24):,} ventanas) vs fable {f24['vehicle_id'].nunique():,} ({len(f24):,} ventanas); "
    f"en común {len(set(a24['vehicle_id']) & set(f24['vehicle_id'])):,}.")
# (i) réplica del método original: merge por vehicle_id (many-to-many)
jm = a24[["vehicle_id", "due_day", "anchor_date"]].merge(f24[["vehicle_id", "due_date", "anchor_date"]], on="vehicle_id", suffixes=("_a", "_f"))
jm["diff"] = (jm["due_date"] - jm["due_day"]).dt.days
dup_a = a24.groupby("vehicle_id").size().gt(1).sum(); dup_f = f24.groupby("vehicle_id").size().gt(1).sum()
log(f"- (i) merge por vehicle_id como el script original: n pares = {len(jm):,} (vehículos con >1 ventana en abr-jul: astra {dup_a:,}, fable {dup_f:,}); "
    f"diff fable − astra: mediana **{jm['diff'].median():.0f} d**, p25 {jm['diff'].quantile(.25):.0f}, p75 {jm['diff'].quantile(.75):.0f}, media {jm['diff'].mean():.1f}.")
# (ii) 1 a 1 por la MISMA ancla (ancla de fable = check-in; de astra = checkout; tolerancia 45 d y misma ancla más cercana)
jm["anchor_gap"] = (jm["anchor_date_f"] - jm["anchor_date_a"]).dt.days
same = jm[jm["anchor_gap"].abs() <= 45].copy()
same["abs_gap"] = same["anchor_gap"].abs()
same = same.sort_values("abs_gap").drop_duplicates(["vehicle_id", "due_day"]).drop_duplicates(["vehicle_id", "due_date"])
log(f"- (ii) 1 a 1 por la misma ancla (|Δancla| ≤ 45 d, par más cercano): n = {len(same):,}; diff fable − astra: mediana **{same['diff'].median():.0f} d**, "
    f"p25 {same['diff'].quantile(.25):.0f}, p75 {same['diff'].quantile(.75):.0f}, media {same['diff'].mean():.1f}; "
    f"Δancla (fable − astra) mediana {same['anchor_gap'].median():.0f} d, media {same['anchor_gap'].mean():.1f} d.")
# descomposición por tipo de ancla
a24t = a24[["vehicle_id", "due_day", "sin_mantenimiento_previo", "familia", "ritmo_confiable"]]
f24t = f24[["vehicle_id", "due_date", "anchor_type", "binding_rule", "rate_source"]]
same2 = same.merge(a24t, on=["vehicle_id", "due_day"]).merge(f24t, on=["vehicle_id", "due_date"])
for (at, smp), g in same2.groupby(["anchor_type", "sin_mantenimiento_previo"]):
    log(f"  - ancla fable `{at}` / astra sin_mantenimiento_previo={smp}: n={len(g):,}, mediana {g['diff'].median():.0f} d, p25 {g['diff'].quantile(.25):.0f}, p75 {g['diff'].quantile(.75):.0f}")
gm = same2[(same2["anchor_type"] == "maintenance") & (same2["sin_mantenimiento_previo"] == 0)]
for fam, g in gm.groupby("familia"):
    log(f"  - anclas de mantenimiento, familia astra {fam}: n={len(g):,}, mediana {g['diff'].median():.0f} d (regla fable: {g['binding_rule'].value_counts(normalize=True).round(2).to_dict()})")
# (iii) el diff neto de la convención de fecha: ancla fable + (checkout - checkin)
log(f"- (iii) parte atribuible a la convención de fecha (fable ancla en check-in/turno, astra en checkout): mediana de Δancla en los pares = "
    f"{same['anchor_gap'].median():.0f} d; el resto de la diferencia proviene de K (16.000 en ambos hoy), del ritmo (tasa acumulada vs mediana de diferencias) y del primer service (300 d vs 1 año).")
# (iv) pares cruzados que sí estaban en (i) pero no en (ii): ¿mueven la mediana?
cross = jm[jm["anchor_gap"].abs() > 45]
log(f"- (iv) pares con anclas distintas (|Δancla| > 45 d) que el merge original mezcla: {len(cross):,} de {len(jm):,}; su diff mediana {cross['diff'].median():.0f} d "
    f"(p25 {cross['diff'].quantile(.25):.0f}, p75 {cross['diff'].quantile(.75):.0f}).")

# ------------------------------------------------------------------------------------------ extra: 46,5 % de la tabla 1.2
log("\n## Extra: etiqueta de fable sobre sus propias ventanas abr-jul 2026 (tabla 1.2 del doc: 46,5 %, n=12.186)\n")
sel = eligF & in_test
for thr_name, thr in [("≤ 2026-08-25 (script original)", CUTOFF), ("≤ 2026-07-26 (margen de fable)", MARGIN)]:
    s = w[sel & (w["horizon_end"] <= thr)]
    r = in_interval(s, EV_F, s["scoring_date"], s["horizon_end"], False, True)
    log(f"- horizonte {thr_name}: n={len(s):,}, churn fable (due−30/+90) = {pct(1 - r.mean())}.")

# ------------------------------------------------------------------------------------------ R. ¿los números del informe salen del parquet viejo (K=15.000)?
log("\n## R. Reproducción con las ventanas de fable reconstruidas con K = 15.000 (P703), como estaban cuando corrió el script original\n")
log("El informe `01_reconciliacion.md` (20:48) es anterior a `params.json` (20:49) y al `ventanas.parquet` actual (20:50). "
    "Se reconstruyen las ventanas con K=15.000 en memoria y se aplica exactamente el mismo código de esta verificación.")
from repurchase.ventanas import build_windows  # noqa: E402


def key_numbers(fb: pd.DataFrame, tag: str):
    fb = fb.copy()
    fb["vehicle_id"] = fb["vehicle_id"].astype(str)
    for c in ["anchor_date", "due_date", "scoring_date", "horizon_end", "next_maint_date"]:
        fb[c] = ns(fb[c])
    # (a) y (c)
    x = fb[fb["status"].isin(["evaluable", "censurada", "preempted"])].copy()
    x["M0"] = x["due_date"].dt.to_period("M").dt.to_timestamp()
    x["M1"] = x["M0"] + pd.offsets.MonthBegin(1)
    x = x[x["M1"] <= OBS_A]
    fe = first_event_after(x, EV_F, x["anchor_date"], False)
    elig = ~(fe.notna() & (fe < x["M0"]))
    churn = ~in_interval(x, EV_F, x["M0"], x["M1"], True, False)
    it = x["due_date"].between(T0, T1 - pd.Timedelta(days=1))
    s = elig & it
    late = x[s & churn & (x["horizon_end"] <= CUTOFF)]
    r120 = in_interval(late, EV_F, late["scoring_date"], late["horizon_end"], False, True)
    # (e)
    vf = set(fb.loc[fb["status"].isin(["evaluable", "censurada"]), "vehicle_id"])
    f24x = fb[(fb["status"] != "fuera_de_rango") & fb["due_date"].between(T0, T1 - pd.Timedelta(days=1))]
    jx = a24[["vehicle_id", "due_day", "anchor_date"]].merge(f24x[["vehicle_id", "due_date", "anchor_date"]], on="vehicle_id", suffixes=("_a", "_f"))
    jx["diff"] = (jx["due_date"] - jx["due_day"]).dt.days
    jx["gap"] = (jx["anchor_date_f"] - jx["anchor_date_a"]).dt.days.abs()
    sx = jx[jx["gap"] <= 45].sort_values("gap").drop_duplicates(["vehicle_id", "due_day"]).drop_duplicates(["vehicle_id", "due_date"])
    log(f"- **{tag}**: (a) n={int(s.sum()):,}, churn mensual abr-jul = {pct(churn[s].mean())}; (c) n churn={len(late):,}, vuelven antes de due+90 = {pct(r120.mean())}; "
        f"(e) vehículos fable eval+cens = {len(vf):,}, en común con astra = {len(va_all & vf):,}; diff due (merge por vehicle_id, n={len(jx):,}) mediana {jx['diff'].median():.0f} d, "
        f"p25 {jx['diff'].quantile(.25):.0f}, p75 {jx['diff'].quantile(.75):.0f}; 1 a 1 misma ancla (n={len(sx):,}) mediana {sx['diff'].median():.0f} d.")


key_numbers(fable, "parquet actual (K=16.000)")
kbg = dict(cfg["ventana"]["km_by_generation"])
kbg["RANGER (P703)"] = 15000
kbg["RANGER RAPTOR (P703)"] = 15000
p15 = WindowParams.from_dict({**cfg["ventana"], "km_by_generation": kbg, "km_interval": 15000})
fable15 = build_windows(appt=appt, params=p15)
key_numbers(fable15, "reconstrucción con K=15.000")

# La salida cruda va a *_evidencia.md; el informe con veredictos (verif_reconciliacion.md) la incluye como anexo.
(OUT / "verif_reconciliacion_evidencia.md").write_text("\n".join(lines) + "\n", encoding="utf8")
print("\nguardado en", OUT / "verif_reconciliacion_evidencia.md")
