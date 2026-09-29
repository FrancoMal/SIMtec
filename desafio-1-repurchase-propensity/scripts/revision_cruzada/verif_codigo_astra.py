"""Verificación escéptica e independiente del bloque 'codigo_astra' de docs/04_revision_cruzada.md (secciones 1.1 y 2.2).

Recalcula, con código propio (sin reutilizar 01_reconciliacion_definiciones.py), las afirmaciones (a)-(g) sobre el
código de astra (G:\\SIMtec-astra, SOLO LECTURA): definición de 'maintenance', regla de retorno por customer_id,
horizonte mensual, exigencia de checkout, ancla del primer ciclo, `meses_observables` y unicidad de episodios.
Para (g) re-ejecuta el `snapshot()` de astra mes a mes (importado en solo lectura) y reconstruye su población.

Salida: reports/revision_cruzada/verif_codigo_astra.md (+ csv auxiliares). Cache de snapshots en el scratchpad.
Uso: PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/revision_cruzada/verif_codigo_astra.py
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.dont_write_bytecode = True  # la carpeta de astra es solo lectura: que el import de su src no deje .pyc allá
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import CUTOFF, appointments  # noqa: E402
from repurchase.io import load_agenda  # noqa: E402
from repurchase.ventanas import WindowParams, maintenance_events  # noqa: E402

ASTRA = Path(r"G:\SIMtec-astra\desafio-1-repurchase-propensity")
sys.path.insert(0, str(ASTRA))  # sólo para importar src.features.snapshot de astra (lectura)
OUT = config.REPORTS_DIR / "revision_cruzada"
OUT.mkdir(parents=True, exist_ok=True)
SCRATCH = Path(os.environ.get("VERIF_SCRATCH", r"F:\Caches\Temp\claude\G--SIMtec-fable\28dff193-8508-4393-8dee-77ce51636f75\scratchpad"))
SCRATCH.mkdir(parents=True, exist_ok=True)
OBS = pd.Timestamp("2026-08-01")   # observed_until de astra (exclusivo)
lines: list[str] = []


def log(s: str = ""):
    print(s, flush=True)
    lines.append(s)


def pct(x, d=1):
    return f"{100 * x:.{d}f} %"


# =============================================================================== datos
ag = load_agenda().drop_duplicates()
appt = appointments()
cfg = json.loads((config.PROJECT_DIR / "config/params.json").read_text(encoding="utf8"))
params = WindowParams.from_dict(cfg["ventana"])
maint_f = maintenance_events(appt, params)
ev = pd.read_parquet(ASTRA / "data/processed/eventos.parquet")
for c in ["maintenance", "valid_complete", "valid_without_os", "cancel", "no_show", "terminal"]:
    ev[c] = ev[c].astype(bool)
for c in ["vehicle_id", "customer_id", "schedule_id"]:
    ev[c] = ev[c].astype(object)
win = pd.read_parquet(ASTRA / "data/processed/ventanas.parquet")
win["identidad_ambigua"] = win["identidad_ambigua"].astype(bool)
tst = pd.read_parquet(ASTRA / "data/processed/test_predicciones.parquet")
sales_a = pd.read_parquet(ASTRA / "data/processed/ventas.parquet")

# Turnos a nivel schedule_id reconstruidos desde la agenda cruda (parquet tipado de fable), con las reglas de astra.
st = ag["ServiceType"].fillna("").str.strip().str.casefold()
items = pd.DataFrame({
    "schedule_id": ag["schedule_id"],
    "it_mant_type": st.eq("mantenimiento"),                       # regla de astra (nivel ítem)
    "it_num": ag["ServiceMaintenance"].notna(),                    # ítem numerado del plan (fable)
    "it_guar": ag["ServiceName"].fillna("").eq("Guarantee"),
    "it_contactless": ag["ServiceName"].fillna("").eq("Contactless service"),
})
flags = items.groupby("schedule_id").agg(any_mant_type=("it_mant_type", "any"), any_num=("it_num", "any"),
                                         any_guar=("it_guar", "any"), any_contactless=("it_contactless", "any"))
head = ag.groupby("schedule_id")[["vehicle_id", "customer_id", "StatusARG", "ScheduleDate", "EffectiveCheckinDate",
                                   "EffectiveCheckoutDate"]].first()
turnos = head.join(flags).reset_index()
turnos["concl"] = turnos["StatusARG"].eq("(60) Concluido")
turnos["sched_d"] = turnos["ScheduleDate"].dt.normalize()
turnos["checkout_d"] = turnos["EffectiveCheckoutDate"].dt.normalize()
turnos["checkin_d"] = turnos["EffectiveCheckinDate"].dt.normalize()
# turnos contradictorios según astra (nunique > 1 en columnas de nivel turno)
nun = ag.groupby("schedule_id")[["vehicle_id", "customer_id", "StatusARG", "ScheduleDate", "EffectiveCheckoutDate"]].nunique()
bad_ids = set(nun.index[nun.gt(1).any(axis=1)])
turnos["bad"] = turnos["schedule_id"].isin(bad_ids)
turnos["valid_close"] = turnos["checkout_d"].notna() & (turnos["checkout_d"] >= turnos["sched_d"])

log("# Verificación del bloque `codigo_astra` (docs/04 §1.1 y §2.2)\n")
log(f"Corte de datos de fable: {CUTOFF.date()}. Agenda cruda sin duplicados exactos: {len(ag):,} ítems, "
    f"{len(turnos):,} turnos; turnos contradictorios (regla de astra): {len(bad_ids)}.")

# =============================================================================== (a) maintenance de astra
log("\n## (a) `maintenance` de astra = ServiceType == 'Mantenimiento' a nivel turno; incluye Guarantee\n")
chk = turnos.merge(ev[["schedule_id", "maintenance", "valid_complete"]], on="schedule_id", how="inner")
log(f"Flag `maintenance` de astra vs mi recálculo 'algún ítem con ServiceType=Mantenimiento': coinciden en "
    f"{(chk['maintenance'] == chk['any_mant_type']).mean():.4%} de {len(chk):,} turnos utilizables por astra.")
ct = turnos[turnos["concl"] & turnos["any_mant_type"]]
no_num = ct[~ct["any_num"]]
log(f"Turnos (60) Concluido con algún ítem ServiceType=Mantenimiento: {len(ct):,}; de ellos SIN ningún ítem numerado "
    f"(ServiceMaintenance nulo): **{len(no_num):,}**.")
log(f"  Composición de esos {len(no_num):,}: sólo Guarantee {int((no_num['any_guar'] & ~no_num['any_contactless']).sum()):,}; "
    f"sólo Contactless {int((~no_num['any_guar'] & no_num['any_contactless']).sum()):,}; ambos "
    f"{int((no_num['any_guar'] & no_num['any_contactless']).sum()):,}.")
nn_ev = no_num.merge(ev[["schedule_id", "maintenance", "valid_complete"]], on="schedule_id", how="left")
counted = nn_ev["maintenance"].fillna(False).astype(bool) & nn_ev["valid_complete"].fillna(False).astype(bool)
log(f"  De esos {len(no_num):,}, los que astra efectivamente cuenta como mantenimiento estricto (maintenance & valid_complete "
    f"en su eventos.parquet): **{int(counted.sum()):,}**. Los demás caen por: sin vehicle_id "
    f"{int(no_num['vehicle_id'].isna().sum()):,}; checkout inválido {int((~no_num['valid_close'] & no_num['vehicle_id'].notna()).sum()):,}; "
    f"contradictorios {int(no_num['bad'].sum()):,}.")
n_astra = int((ev["maintenance"] & ev["valid_complete"]).sum())
n_fable_turno = int((appt["is_completed_maintenance"] & appt["vehicle_id"].notna()).sum())
n_fable_sinvin = int((appt["is_completed_maintenance"] & appt["vehicle_id"].isna()).sum())
n_fable_evt = len(maint_f)
log(f"Mantenimientos estrictos de astra (turnos, maintenance & valid_complete): **{n_astra:,}**.")
log(f"Mantenimientos de fable: a nivel TURNO (is_completed_maintenance & vehicle_id) **{n_fable_turno:,}** (más {n_fable_sinvin:,} sin VIN "
    f"que ninguno de los dos usa; el 01_reconciliacion los cuenta en su '222.889'); a nivel vehículo-día tras dedup y visitas partidas "
    f"(`maintenance_events`) **{n_fable_evt:,}**.")
A = set(ev.loc[ev["maintenance"] & ev["valid_complete"], "schedule_id"])
F = set(appt.loc[appt["is_completed_maintenance"] & appt["vehicle_id"].notna(), "schedule_id"])
onlyA, onlyF = A - F, F - A
oa = turnos[turnos["schedule_id"].isin(onlyA)]
of = turnos[turnos["schedule_id"].isin(onlyF)]
log(f"Comparación turno a turno: sólo astra {len(onlyA):,} (sin ítem numerado: {int((~oa['any_num']).sum()):,}; "
    f"con ítem numerado: {int(oa['any_num'].sum()):,}); sólo fable {len(onlyF):,} (checkout inválido "
    f"{int((~of['valid_close']).sum()):,}; contradictorios {int(of['bad'].sum()):,}).")
log(f"Diferencia neta a nivel turno: {n_astra - n_fable_turno:+,}; la cifra del doc (225.479 vs 220.522 = {n_astra - n_fable_evt:+,}) "
    f"mezcla el nivel turno de astra con el nivel vehículo-día deduplicado de fable ({n_fable_turno - n_fable_evt:,} turnos "
    f"colapsados por fable como misma visita).")

# =============================================================================== (b) retorno = mismo customer_id; anónimo -> NaN
log("\n## (b) Retorno exige el mismo `customer_id`; retorno anónimo → NaN; agosto sin etiqueta\n")
done = ev.loc[ev["maintenance"] & ev["valid_complete"], ["vehicle_id", "customer_id", "event_date"]]
w = win[["row_id", "vehicle_id", "customer_id", "scoring_date", "window_end", "target", "target_vin"]].copy()
j = w.merge(done, on="vehicle_id", how="left", suffixes=("", "_r"))
inwin = j["event_date"].notna() & (j["event_date"] >= j["scoring_date"]) & (j["event_date"] < j["window_end"])
same = inwin & (j["customer_id_r"].astype(object) == j["customer_id"].astype(object))
anon = inwin & j["customer_id_r"].isna()
anyvin = inwin
agg = pd.DataFrame({"same": same, "anon": anon, "anyvin": anyvin}).groupby(j["row_id"]).any()
w = w.set_index("row_id").join(agg)
w["t_re"] = np.where(w["same"], 0.0, np.where(w["anon"], np.nan, 1.0))
w.loc[w["window_end"] > OBS, "t_re"] = np.nan
w["tv_re"] = np.where(w["anyvin"], 0.0, 1.0)
w.loc[w["window_end"] > OBS, "tv_re"] = np.nan
eq = (w["t_re"].isna() & w["target"].isna()) | (w["t_re"] == w["target"])
eqv = (w["tv_re"].isna() & w["target_vin"].isna()) | (w["tv_re"] == w["target_vin"])
log(f"Recalculé `target` desde eventos.parquet con la regla '[scoring, fin) & mismo customer_id; anónimo sin retorno propio → NaN; "
    f"fin > 1/8/2026 → NaN': coincide con el parquet en {eq.mean():.4%} de {len(w):,} ventanas ({int((~eq).sum())} discrepancias). "
    f"`target_vin` (cualquier customer_id): coincide en {eqv.mean():.4%}.")
aug = w[w["scoring_date"].eq("2026-08-01")]
log(f"Ventanas de agosto 2026: {len(aug):,}, con etiqueta: {int(aug['target'].notna().sum())} (window_end = 1/9 > observed_until).")
lab = w[w["window_end"] <= OBS]
n_anon = int((lab["target"].isna()).sum())
log(f"Ventanas con horizonte observado: {len(lab):,}; sin etiqueta por retorno anónimo: {n_anon} "
    f"({n_anon / len(lab):.3%}); de ellas {int((lab['target'].isna() & lab['anon']).sum())} tienen efectivamente un retorno "
    f"anónimo del VIN en el mes (verificado).")
lab2 = lab[lab["target"].notna()]
same_vin_other = lab2["target"].eq(1) & lab2["target_vin"].eq(0)
log(f"Churn por identidad (target=1 pero target_vin=0: el VIN volvió con otro customer_id): {int(same_vin_other.sum()):,} = "
    f"{same_vin_other.mean():.2%} de las ventanas etiquetadas = {same_vin_other.sum() / lab2['target'].eq(1).sum():.2%} de sus churn. "
    f"Churn mismo usuario {lab2['target'].mean():.3f} vs mismo VIN {lab2['target_vin'].mean():.3f}.")
# ¿El customer_id de la ventana es el del último evento (o la venta)? Verifico contra el snapshot de astra más abajo (g).

# =============================================================================== (c) horizonte [scoring, 1° mes siguiente)
log("\n## (c) Horizonte [scoring, 1° del mes siguiente); scoring = 1° del mes del vencimiento; mediana 14 d tras vencer\n")
ms = win["due_date"].dt.to_period("M").dt.to_timestamp()
log(f"scoring_date == 1° del mes del vencimiento en {(ms == win['scoring_date']).mean():.4%} de las ventanas; "
    f"window_end == scoring + 1 mes en {(win['window_end'] == win['scoring_date'] + pd.offsets.MonthBegin(1)).mean():.4%}; "
    f"scoring ≤ due < window_end en {((win['due_date'] >= win['scoring_date']) & (win['due_date'] < win['window_end'])).mean():.4%}.")
# Intervalo abierto/cerrado, comprobado con casos: retorno exactamente en window_end (no cuenta) y exactamente en scoring (cuenta)
j2 = j[j["customer_id_r"].astype(object) == j["customer_id"].astype(object)]
at_end = j2[j2["event_date"] == j2["window_end"]]["row_id"].unique()
at_start = j2[j2["event_date"] == j2["scoring_date"]]["row_id"].unique()
w_end = w.loc[w.index.isin(at_end) & ~w["same"] & w["window_end"].le(OBS)]
w_start = w.loc[w.index.isin(at_start) & w["window_end"].le(OBS)]
log(f"Casos borde: {len(w_end):,} ventanas cuyo único retorno propio cae exactamente el 1° del mes siguiente → etiqueta "
    f"{w_end['target'].value_counts(dropna=False).to_dict()} (churn: el fin es exclusivo). {len(w_start):,} ventanas con retorno "
    f"exactamente el día del scoring → etiqueta {w_start['target'].value_counts(dropna=False).to_dict()} (cuenta: inicio inclusivo).")
t = tst.copy()
obs_after = (t["window_end"] - t["due_date"])
d_floor = obs_after.dt.days
d_frac = obs_after.dt.total_seconds() / 86400
log(f"Test astra ({len(t):,} ventanas abr-jul 2026, target no nulo: {int(t['target'].notna().sum()):,}): días de observación después "
    f"del vencimiento: mediana **{d_floor.median():.0f}** (días enteros) / {d_frac.median():.1f} (fraccionarios); p25 {d_frac.quantile(.25):.1f}, "
    f"p75 {d_frac.quantile(.75):.1f}; mínimo {d_frac.min():.2f}, máximo {d_frac.max():.2f}. Con menos de 5 días: {pct((d_frac < 5).mean())}; "
    f"con menos de 1 día: {pct((d_frac < 1).mean())}.")
allw = win[win["window_end"] <= OBS]
da = (allw["window_end"] - allw["due_date"]).dt.total_seconds() / 86400
log(f"Todas las ventanas etiquetables: mediana {da.median():.1f} d, máximo {da.max():.1f} d (el rango es 0-31, no 0-30: meses de 31 días "
    f"con vencimiento el 1°: {int((da > 30).sum()):,} ventanas).")

# =============================================================================== (d) checkout válido no pierde eventos
log("\n## (d) Exigir checkout válido: cuántos mantenimientos concluidos se pierden\n")
for nombre, mask in [("astra: (60) Concluido & ServiceType=Mantenimiento", turnos["concl"] & turnos["any_mant_type"]),
                     ("fable: (60) Concluido & ítem numerado", turnos["concl"] & turnos["any_num"])]:
    m = turnos[mask & turnos["vehicle_id"].notna()]
    sin = int(m["EffectiveCheckoutDate"].isna().sum())
    antes_d = int((m["checkout_d"] < m["sched_d"]).sum())
    antes_dt = int((m["EffectiveCheckoutDate"] < m["ScheduleDate"]).sum())
    log(f"{nombre}: {len(m):,} turnos con VIN; sin checkout **{sin}**; checkout anterior al turno **{antes_d}** (comparando fechas "
        f"normalizadas como astra; sin normalizar: {antes_dt}); contradictorios {int(m['bad'].sum())}.")
allc = turnos[turnos["EffectiveCheckoutDate"].notna()]
log(f"Control contra la auditoría de astra ('cierres_anteriores_al_turno' = 13, todos los status): recalculado "
    f"{int((allc['checkout_d'] < allc['sched_d']).sum())}.")
# Salvedad: la fecha de evento de astra es el CHECKOUT (fable: check-in coherente o fecha de turno)
mm = turnos[turnos["concl"] & turnos["any_mant_type"] & turnos["vehicle_id"].notna() & turnos["valid_close"]].copy()
gap_out = (mm["checkout_d"] - mm["sched_d"]).dt.days
gap_in = (mm["checkout_d"] - mm["checkin_d"]).dt.days
log(f"Fecha de evento: astra usa el checkout, fable el check-in (si está a ±45 d del turno) o la fecha del turno. En los "
    f"{len(mm):,} mantenimientos válidos de astra, checkout − fecha de turno: mediana {gap_out.median():.0f} d, p90 {gap_out.quantile(.9):.0f}, "
    f"> 0 en {pct((gap_out > 0).mean())}, ≥ 7 d en {pct((gap_out >= 7).mean())}; checkout − check-in: > 0 en {pct((gap_in > 0).mean())}, "
    f"≥ 7 d en {pct((gap_in >= 7).mean())} (check-in nulo: {pct(mm['checkin_d'].isna().mean())}).")
cross = (mm["checkout_d"].dt.to_period("M") != mm["sched_d"].dt.to_period("M"))
log(f"El checkout cae en un mes calendario distinto al de la fecha del turno en {int(cross.sum()):,} mantenimientos ({pct(cross.mean())}).")
# Efecto sobre la etiqueta mensual: churn "por convención de checkout" y retornos que ya estaban en el taller al scorear
labw = win[win["window_end"].le(OBS) & win["target"].notna()][["row_id", "vehicle_id", "customer_id", "scoring_date", "window_end", "target"]]
mm2 = mm[["vehicle_id", "customer_id", "sched_d", "checkin_d", "checkout_d"]].copy()
mm2["start_d"] = mm2[["sched_d", "checkin_d"]].min(axis=1)
jj = labw.merge(mm2, on=["vehicle_id", "customer_id"], how="inner")
strad_out = jj[(jj["start_d"] >= jj["scoring_date"]) & (jj["start_d"] < jj["window_end"]) & (jj["checkout_d"] >= jj["window_end"])]
churn_conv = labw[labw["row_id"].isin(strad_out["row_id"]) & labw["target"].eq(1)]
demora = (strad_out["checkout_d"] - strad_out["window_end"]).dt.days.groupby(strad_out["row_id"]).min().reindex(churn_conv["row_id"])
log(f"Ventanas etiquetadas churn cuyo vehículo (mismo usuario) ENTRÓ al taller por un mantenimiento dentro del mes (fecha de turno o "
    f"check-in en el mes) pero salió el mes siguiente: **{len(churn_conv):,}** ({churn_conv.shape[0] / labw['target'].eq(1).sum():.2%} de los "
    f"churn; {len(churn_conv) / len(labw):.2%} de las ventanas). Con la fecha de evento de fable serían retornos. El checkout cae a "
    f"≤ 3 días del fin de mes en {int((demora <= 3).sum()):,} de ellas, a ≤ 7 días en {int((demora <= 7).sum()):,} (mediana {demora.median():.0f} d).")
strad_in = jj[(jj["start_d"] < jj["scoring_date"]) & (jj["checkout_d"] >= jj["scoring_date"]) & (jj["checkout_d"] < jj["window_end"])]
ya_en_taller = labw[labw["row_id"].isin(strad_in["row_id"]) & labw["target"].eq(0)]
log(f"Ventanas etiquetadas retorno cuyo mantenimiento ya había empezado ANTES del scoring (turno/check-in < 1° ≤ checkout): "
    f"**{len(ya_en_taller):,}** ({len(ya_en_taller) / labw['target'].eq(0).sum():.2%} de los retornos): el vehículo estaba en el taller "
    f"al momento de scorear; fable las trataría como preempted.")

# =============================================================================== (e) primer ciclo = entrega + 1 año sin odómetro
log("\n## (e) Primer ciclo anclado en entrega + 1 año cuando no hay odómetro\n")
fc = win[win["sin_mantenimiento_previo"].eq(1)].copy()
anc_esp = fc["delivery"].fillna(fc["warranty"])
log(f"Ventanas de primer ciclo (sin_mantenimiento_previo=1): {len(fc):,} de {len(win):,} ({pct(len(fc) / len(win))}); anchor_id='entrega' en "
    f"{fc['anchor_id'].eq('entrega').mean():.2%}; anchor_date == entrega (o garantía si no hay entrega) en {(fc['anchor_date'] == anc_esp).mean():.2%}; "
    f"anclada en entrega (venta conocida) {pct(fc['delivery'].notna().mean())}, en garantía de agenda {pct(fc['delivery'].isna().mean())}.")
plus1y = pd.to_datetime(fc["anchor_date"]) + pd.DateOffset(years=1)
sin_km = fc["km_ultimo"].isna()
log(f"Sin odómetro (km_ultimo nulo): {int(sin_km.sum()):,} ({pct(sin_km.mean())}); en ellas due_date == ancla + 1 año (DateOffset) en "
    f"{(fc.loc[sin_km, 'due_date'] == plus1y[sin_km]).mean():.2%}.")
con_km = fc[~sin_km]
dd = (con_km["due_date"] - pd.to_datetime(con_km["anchor_date"])).dt.days
log(f"Con odómetro de alguna visita cerrada previa (no mantenimiento): {len(con_km):,} ({pct((~sin_km).mean())}); vencimiento a "
    f"mediana {dd.median():.0f} d del ancla; antes de los 365 d en {pct((dd < 365).mean())}.")
fct = tst[tst["sin_mantenimiento_previo"].eq(1)]
edad = (fct["scoring_date"] - pd.to_datetime(fct["anchor_date"])).dt.days
log(f"Test: {len(fct):,} ventanas de primer ciclo, churn {fct['target'].mean():.3f}; edad del vehículo al scoring (desde el ancla): mediana "
    f"{edad.median():.0f} d, p10 {edad.quantile(.1):.0f}, p90 {edad.quantile(.9):.0f}; con odómetro previo {pct(fct['km_ultimo'].notna().mean())}.")
# ¿Cuándo hacen el primer service realmente y cuántos quedan fuera de la ventana de astra?
sd = sales_a[["vehicle_id", "delivery"]].dropna().drop_duplicates("vehicle_id")
sd = sd[sd["delivery"].between("2024-01-01", "2025-07-01")]
fm = done.merge(sd, on="vehicle_id")
fm = fm[fm["event_date"] > fm["delivery"]].groupby("vehicle_id").agg(first_m=("event_date", "min"), delivery=("delivery", "first"))
mesesm = (fm["first_m"] - fm["delivery"]).dt.days / 30.44
first_mes = (fm["delivery"] + pd.DateOffset(years=1)).dt.to_period("M").dt.to_timestamp()
antes_ventana = fm["first_m"] < first_mes
log(f"Vehículos entregados ene-2024/jun-2025 con mantenimiento observado después de la entrega: {len(fm):,} de {len(sd):,}; primer "
    f"service a {mesesm.median():.1f} meses de mediana, antes de 9 meses {pct((mesesm < 9).mean())}, antes de 6 {pct((mesesm < 6).mean())}. "
    f"Lo hacen ANTES del 1° del mes de entrega+1 año (nunca tendrían ventana de primer ciclo en astra): {pct(antes_ventana.mean())}.")
got_fc = set(fc["vehicle_id"])
log(f"De esos {len(sd):,} vehículos entregados, con ventana de primer ciclo en astra: {int(sd['vehicle_id'].isin(got_fc).sum()):,} "
    f"({pct(sd['vehicle_id'].isin(got_fc).mean())}).")

# =============================================================================== (f) meses_observables
log("\n## (f) `meses_observables`: constante por mes de scoring; fuera de rango en test\n")
nu = win.groupby("scoring_date")["meses_observables"].nunique()
log(f"Valores distintos por scoring_date: máximo {nu.max()} (constante por mes: {'sí' if nu.max() == 1 else 'NO'}).")
sys.path.insert(0, str(ASTRA))
from src.modeling import split_name  # noqa: E402  (astra, lectura)
win["split"] = split_name(win["scoring_date"])
rng = win.groupby("split")["meses_observables"].agg(["min", "max"]).round(2)
log("Rango por partición de astra:\n" + rng.to_markdown())
res = json.loads((ASTRA / "reports/resultados.json").read_text(encoding="utf8"))
rank = [d["variable"] for d in res["shap_global"]].index("meses_observables") + 1
log(f"Posición por |SHAP| medio en resultados.json: {rank}°.")
# ¿Qué hace el LightGBM con valores fuera del rango? Compruebo que el score en test es idéntico si se fija al máximo de train.
try:
    import joblib
    model = joblib.load(ASTRA / "models/retencion.joblib")
    t2 = tst.copy()
    p0 = model.predict(t2)
    t2["meses_observables"] = float(win.loc[win["split"].eq("train"), "meses_observables"].max())
    p1 = model.predict(t2)
    t3 = tst.copy(); t3["meses_observables"] = float(win.loc[win["split"].eq("train"), "meses_observables"].median())
    p2 = model.predict(t3)
    from sklearn.metrics import roc_auc_score
    y = tst["target"].values
    log(f"Modelo de astra sobre su test: score idéntico si `meses_observables` se fija en el máximo de train ({t2['meses_observables'].iloc[0]:.2f}): "
        f"máx |Δ| = {np.abs(p0 - p1).max():.2e} (los valores 27-30 caen en el último bin: el modelo los trata como agosto 2025). "
        f"Fijándola en la mediana de train ({t3['meses_observables'].iloc[0]:.2f}): máx |Δ| = {np.abs(p0 - p2).max():.3f}, "
        f"ROC-AUC {roc_auc_score(y, p0):.4f} → {roc_auc_score(y, p2):.4f}, score medio {p0.mean():.3f} → {p2.mean():.3f}.")
except Exception as exc:  # noqa: BLE001
    log(f"(No se pudo cargar el modelo de astra para la prueba de saturación: {exc})")

# =============================================================================== (g) episodios: re-ejecución de los snapshots de astra
log("\n## (g) Cada episodio (VIN:ancla) entra una sola vez; retorno antes del 1° → la ventana no existe\n")
log(f"En ventanas.parquet: episodios duplicados {int(win['episode'].duplicated().sum())}; pares (vehicle_id, scoring_date) duplicados "
    f"{int(win.duplicated(['vehicle_id', 'scoring_date']).sum())}; vehículos con >1 ventana {int((win.groupby('vehicle_id').size() > 1).sum()):,} "
    f"(máximo {win.groupby('vehicle_id').size().max()} ventanas).")
jm = win[["row_id", "vehicle_id", "anchor_date", "scoring_date"]].merge(done[["vehicle_id", "event_date"]], on="vehicle_id")
viol = jm[(jm["event_date"] > jm["anchor_date"]) & (jm["event_date"] < jm["scoring_date"])]["row_id"].nunique()
log(f"Ventanas con un mantenimiento (definición astra) entre el ancla y el scoring: {viol} (si volvió antes del 1°, el ancla es la nueva).")

cache = SCRATCH / "astra_snapshots_verif.parquet"
if cache.exists():
    snaps = pd.read_parquet(cache)
else:
    from src.features import snapshot  # noqa: E402  (astra, lectura)
    events_a = pd.read_parquet(ASTRA / "data/processed/eventos.parquet")
    parts = []
    for scoring in pd.date_range("2024-07-01", "2026-08-01", freq="MS"):
        s = snapshot(sales_a, events_a, scoring)
        s = s[["vehicle_id", "customer_id", "anchor_id", "anchor_date", "due_date", "identidad_ambigua", "intervalo_km",
               "sin_mantenimiento_previo", "km_ultimo"]].copy()
        s["scoring"] = scoring
        parts.append(s)
        print(f"  snapshot {scoring:%Y-%m}: {len(s):,} VIN", flush=True)
    snaps = pd.concat(parts, ignore_index=True)
    snaps.to_parquet(cache, index=False)
snaps["identidad_ambigua"] = snaps["identidad_ambigua"].astype(bool)
snaps["end"] = snaps["scoring"] + pd.offsets.MonthBegin(1)
snaps["episode"] = snaps["vehicle_id"].astype(str) + ":" + snaps["anchor_id"].astype(str)
snaps["st"] = np.select([snaps["due_date"].isna(), snaps["due_date"] < snaps["scoring"], snaps["due_date"] < snaps["end"]],
                        ["sin_fecha", "vencida", "en_mes"], "futura")
snaps["cand"] = snaps["st"].eq("en_mes") & snaps["intervalo_km"].notna() & snaps["anchor_date"].notna()
snaps["elig"] = snaps["cand"] & ~snaps["identidad_ambigua"]
# reproducción de build_windows: primera vez elegible por episodio
first_elig = snaps[snaps["elig"]].sort_values("scoring").drop_duplicates("episode")
rep = first_elig.groupby("scoring").size()
orig = win.groupby("scoring_date").size()
cmp_ = pd.concat([orig.rename("parquet"), rep.rename("reproducido")], axis=1).fillna(0).astype(int)
log(f"Reproducción de build_windows con los snapshots re-ejecutados: ventanas {len(first_elig):,} vs {len(win):,} en el parquet; "
    f"meses con recuento idéntico: {(cmp_['parquet'] == cmp_['reproducido']).sum()} de {len(cmp_)}; episodios idénticos: "
    f"{set(first_elig['episode']) == set(win['episode'])}.")
# customer_id de la ventana = customer del snapshot (último evento con usuario o comprador)
ck = win[["episode", "customer_id"]].merge(first_elig[["episode", "customer_id"]], on="episode", suffixes=("", "_re"))
log(f"customer_id de la ventana coincide con el del snapshot re-ejecutado en {(ck['customer_id'].astype(str) == ck['customer_id_re'].astype(str)).mean():.4%}.")

# clasificación de todos los episodios vistos en algún snapshot
snaps = snaps.sort_values(["episode", "scoring"])
g = snaps.groupby("episode")
ep = g.agg(first_m=("scoring", "min"), last_m=("scoring", "max"), n=("scoring", "size"), any_en_mes=("st", lambda s: (s == "en_mes").any()),
           any_futura=("st", lambda s: (s == "futura").any()), any_elig=("elig", "any"), first_st=("st", "first"),
           last_st=("st", "last"), vid=("vehicle_id", "first"), anchor_id=("anchor_id", "first"), anchor_date=("anchor_date", "first"))
ep["ancla_mant"] = ep["anchor_id"].ne("entrega")
# Un episodio sólo termina por reemplazo del ancla (el vehículo volvió) o porque se acaba la serie (ago-2026): el índice de VIN
# de snapshot() sólo crece. Por eso last_m < ago-2026 ⇔ hubo un retorno después.
fin = ep["last_m"].eq("2026-08-01")
cond = [ep["any_elig"],
        ep["any_en_mes"] & ~ep["any_elig"],
        ep["last_st"].eq("vencida") & ep["any_futura"] & ~fin,          # fue 'futura', terminó 'vencida' sin pasar por 'en_mes', y el VIN volvió
        ep["last_st"].eq("vencida") & ep["any_futura"] & fin,           # ídem pero sigue vencido al final de los datos
        ep["last_st"].eq("vencida") & ~ep["any_futura"] & ep["first_m"].eq("2024-07-01"),  # ya vencido en el primer snapshot (anterior al rango)
        ep["last_st"].eq("vencida") & ~ep["any_futura"],                # vencido desde que apareció, después de jul-2024 (odómetro)
        ep["last_st"].eq("futura") & ~fin,
        ep["last_st"].eq("futura") & fin,
        ep["last_st"].eq("sin_fecha")]
names = ["ventana", "excluido_identidad_o_regla", "salteado_luego_volvio", "salteado_sigue_vencido",
         "vencido_antes_de_jul2024", "vencido_al_aparecer_posterior", "preempted_ancla_reemplazada", "censurado_futuro", "sin_fecha"]
ep["clase"] = np.select(cond, names, "otro")
tab = ep.groupby(["ancla_mant", "clase"]).size().unstack(0).fillna(0).astype(int).rename(columns={True: "ancla_mantenimiento", False: "ancla_entrega"})
tab["total"] = tab.sum(axis=1)
log("\nClasificación de todos los episodios (VIN:ancla) vistos en algún snapshot jul-2024/ago-2026:\n" + tab.to_markdown())
# verificación del preempted: ¿el episodio desaparece porque el vehículo tiene una ancla nueva el mes siguiente?
pre = ep[ep["clase"].eq("preempted_ancla_reemplazada")].reset_index()
nxt = snaps[["vehicle_id", "scoring", "anchor_id", "anchor_date"]].copy()
nxt["scoring"] = nxt["scoring"] - pd.offsets.MonthBegin(1)
pre = pre.merge(nxt.rename(columns={"vehicle_id": "vid", "scoring": "last_m", "anchor_id": "anchor_next", "anchor_date": "anchor_date_next"}),
                on=["vid", "last_m"], how="left")
log(f"\nEpisodios 'preempted': {len(pre):,}; al mes siguiente el vehículo tiene otra ancla en {pre['anchor_next'].notna().mean():.2%} de los casos "
    f"(sin fila siguiente: {int(pre['anchor_next'].isna().sum())}, son los que el vehículo deja de aparecer).")
# ¿dónde cayó el retorno respecto del vencimiento estimado en el último snapshot (regla de fable: preempted sólo si retorno ≤ due − 30)?
last_due = snaps.drop_duplicates("episode", keep="last").set_index("episode")["due_date"]
pre["due_last"] = pre["episode"].map(last_due)
pre["ret_vs_due"] = (pd.to_datetime(pre["anchor_date_next"]) - pre["due_last"]).dt.total_seconds() / 86400
ok = pre["ret_vs_due"].notna()
pre_m = pre[ok & pre["ancla_mant"]]
log(f"Retorno (ancla nueva) respecto del vencimiento estimado en el último snapshot ({int(ok.sum()):,} con fecha): mediana "
    f"{pre.loc[ok, 'ret_vs_due'].median():.0f} d; retorno en [due−30, due) → fable lo etiquetaría retorno (0), astra no crea la ventana: "
    f"{int((pre.loc[ok, 'ret_vs_due'] >= -30).sum()):,} ({pct((pre.loc[ok, 'ret_vs_due'] >= -30).mean())}); retorno más de 30 d antes del "
    f"vencimiento (preempted en ambos): {int((pre.loc[ok, 'ret_vs_due'] < -30).sum()):,}. Sólo anclas de mantenimiento: "
    f"{int((pre_m['ret_vs_due'] >= -30).sum()):,} de {len(pre_m):,} ({pct((pre_m['ret_vs_due'] >= -30).mean())}).")
n_ret_en_ventana_fable = int((pre.loc[ok, "ret_vs_due"] >= -30).sum())
log(f"Episodios sin clase ('otro'): {int(ep['clase'].eq('otro').sum())}.")
# distribución compacta (no se guarda el detalle de 68k episodios): retorno − vencimiento en bins de 30 días
bins_ret = pd.cut(pre.loc[ok, "ret_vs_due"], [-4000, -180, -90, -60, -30, -15, 0]).value_counts().sort_index()
bins_ret.rename("episodios").to_csv(OUT / "verif_codigo_astra_preempted_ret_vs_due.csv")
sal = ep[ep["clase"].str.startswith("salteado")]
n_volvio = int(ep["clase"].eq("salteado_luego_volvio").sum())
log(f"Episodios salteados por salto del vencimiento (estuvieron 'futura', pasaron a 'vencida' sin ningún mes 'en_mes', nunca scoreados): "
    f"{len(sal):,} (anclas de mantenimiento: {int(sal['ancla_mant'].sum()):,}); equivalen al {len(sal) / len(win):.1%} de las ventanas creadas. "
    f"De ellos el vehículo volvió después (ancla nueva) en {n_volvio:,} y sigue vencido sin ventana al final de los datos en {len(sal) - n_volvio:,}.")
sal_r = sal.reset_index()
# ejemplo trazable de salto: trayectoria del vencimiento en los snapshots
ej = sal_r[sal_r["ancla_mant"]].iloc[0]["episode"]
tr = snaps[snaps["episode"].eq(ej)][["scoring", "anchor_date", "due_date", "km_ultimo", "st"]]
log(f"  Ejemplo (episodio {ej}):\n" + tr.assign(due_date=tr["due_date"].dt.date, scoring=tr["scoring"].dt.date,
                                                anchor_date=pd.to_datetime(tr["anchor_date"]).dt.date).to_markdown(index=False))
# ejemplo trazable de 'churn por convención de checkout' (uno típico: check-in cargado y checkout a pocos días del fin de mes)
ejc_all = strad_out.merge(labw[labw["target"].eq(1)][["row_id"]], on="row_id")
ejc_all = ejc_all[ejc_all["checkin_d"].notna() & (ejc_all["checkout_d"] - ejc_all["window_end"]).dt.days.le(3)]
ejc = ejc_all.iloc[0]
log(f"  Ejemplo de churn por fecha de checkout: ventana row_id {ejc['row_id']} (VIN {ejc['vehicle_id']}, scoring {ejc['scoring_date'].date()}, "
    f"fin {ejc['window_end'].date()}): turno de mantenimiento el {ejc['sched_d'].date()}, check-in {ejc['checkin_d'].date() if pd.notna(ejc['checkin_d']) else 'NaT'}, "
    f"checkout {ejc['checkout_d'].date()} → astra: churn; fable (fecha = check-in): retorno.")
tab.to_csv(OUT / "verif_codigo_astra_clases_episodios.csv")
sal_r[["episode", "vid", "anchor_date", "first_m", "last_m", "clase"]].to_csv(OUT / "verif_codigo_astra_salteados.csv", index=False)
cmp_.to_csv(OUT / "verif_codigo_astra_reproduccion_mensual.csv")

# =============================================================================== resumen
log("\n## Tabla de veredictos\n")
tabla = [
    ("(a) `maintenance` = ServiceType=='Mantenimiento' a nivel turno e incluye Guarantee; 3.808 turnos concluidos sin ServiceMaintenance contados como mantenimiento; 225.479 vs 220.522",
     "ajustada", "3.808 / 225.479 vs 220.522", f"{len(no_num):,} sin número, de los cuales astra cuenta {int(counted.sum()):,} / {n_astra:,} vs {n_fable_turno:,} (turno) o {n_fable_evt:,} (vehículo-día)",
     f"La regla y la inclusión de Guarantee son correctas (flag reproducido al 100 %). Pero {len(no_num) - int(counted.sum()):,} de los 3.808 no entran (sin VIN o checkout inválido) y {int((no_num['any_contactless'] & ~no_num['any_guar']).sum())} son 'Contactless service', no garantía. La comparación 225.479 vs 220.522 mezcla niveles: a nivel turno es {n_astra:,} vs {n_fable_turno:,} ({n_astra - n_fable_turno:+,})."),
    ("(b) Retorno exige el mismo customer_id; retorno anónimo → NaN; ventanas de agosto sin etiqueta",
     "confirmada", "—", f"target recalculado coincide {eq.mean():.2%}; {n_anon} NaN por anonimato; agosto {len(aug):,}/{len(aug):,} sin etiqueta",
     f"Salvedad de magnitud: el 'churn por identidad' es {same_vin_other.mean():.1%} de las ventanas pero {same_vin_other.sum() / lab2['target'].eq(1).sum():.1%} de sus churn (el doc §0.7 dice '3,1 % de sus churn')."),
    ("(c) Horizonte [scoring, 1° del mes siguiente); scoring = 1° del mes del vencimiento; mediana 14 d de observación tras vencer en test",
     "confirmada", "14", f"{d_floor.median():.0f} (enteros) / {d_frac.median():.1f} (fraccionarios); rango {d_frac.min():.1f}-{d_frac.max():.1f}",
     f"Intervalo verificado con casos borde. Rango real 0-31 d (no 0-30). {pct((d_frac < 5).mean())} del test tiene < 5 d de observación."),
    ("(d) Exigir checkout válido no pierde eventos: 0 sin checkout, 1 con checkout anterior al turno",
     "confirmada", "0 / 1", f"0 / {int((turnos[turnos['concl'] & turnos['any_mant_type'] & turnos['vehicle_id'].notna()]['checkout_d'] < turnos[turnos['concl'] & turnos['any_mant_type'] & turnos['vehicle_id'].notna()]['sched_d']).sum())} (ambas definiciones)",
     f"Cierto para el FILTRO. Lo que sí mueve etiquetas es usar el checkout como FECHA del evento: {len(churn_conv):,} churn de astra entraron al taller dentro del mes y salieron al siguiente ({churn_conv.shape[0] / labw['target'].eq(1).sum():.1%} de sus churn), y {len(ya_en_taller):,} 'retornos' ya estaban en el taller al scorear."),
    ("(e) Primer ciclo anclado en entrega + 1 año cuando no hay odómetro",
     "confirmada", "—", f"{(fc.loc[sin_km, 'due_date'] == plus1y[sin_km]).mean():.1%} de las ventanas sin odómetro vencen exactamente a ancla + 1 año; {pct(sin_km.mean())} sin odómetro",
     f"Salvedad: el {pct((~sin_km).mean())} de las ventanas de primer ciclo sí tiene odómetro de otra visita y vence antes (mediana {dd.median():.0f} d). Ancla = entrega si hay venta ({pct(fc['delivery'].notna().mean())}), si no garantía de agenda. Test: {len(fct):,} ventanas, churn {fct['target'].mean():.3f}."),
    ("(f) meses_observables constante por mes de scoring; en test fuera del rango de entrenamiento (27-30 vs ≤ 20)",
     "confirmada", "27-30 vs ≤ 20; 5° por SHAP", f"train {rng.loc['train', 'min']}-{rng.loc['train', 'max']}, test {rng.loc['test', 'min']}-{rng.loc['test', 'max']}; {rank}° por SHAP",
     "Salvedad: el LightGBM no extrapola: los valores 27-30 caen en el último bin y el score es idéntico al de fijar la variable en su máximo de train (agosto 2025). No es fuga ni inestabilidad, es una constante que fija el nivel de la última época vista."),
    ("(g) Cada episodio entra una sola vez; un retorno antes del 1° hace que la ventana no exista (≈ preempted de fable)",
     "ajustada", "—", f"0 episodios duplicados; {viol} ventanas con retorno entre ancla y scoring; build_windows reproducido ({len(first_elig):,} = {len(win):,})",
     f"La equivalencia no es exacta: astra preempta hasta el 1° del mes del vencimiento, fable hasta due−30 (el corte de astra siempre es igual o posterior). De {len(pre):,} episodios preemptados por astra, {n_ret_en_ventana_fable:,} ({pct((pre.loc[ok, 'ret_vs_due'] >= -30).mean())}) volvieron en [due−30, due): fable los contaría como retornos (label 0), astra los saca de la población. Además {len(sal):,} episodios nunca se scorean porque el vencimiento recalculado salta de 'futuro' a 'vencido' entre dos snapshots ({len(sal) / len(win):.1%} de las ventanas creadas)."),
]
log("| Afirmación | Veredicto | Número original | Número recalculado | Nota |")
log("|---|---|---|---|---|")
for a_, v_, o_, r_, n_ in tabla:
    log(f"| {a_} | **{v_}** | {o_} | {r_} | {n_} |")

resumen = (
    "> Rol escéptico: recalculé cada afirmación con código propio sobre la agenda cruda (parquet tipado de fable), el "
    "`eventos.parquet` / `ventanas.parquet` / `test_predicciones.parquet` de astra y una re-ejecución mes a mes de su "
    "`snapshot()` (importado en solo lectura), que reproduce sus 132.869 ventanas y episodios exactamente.\n>\n"
    f"> **Resultado**: 5 afirmaciones confirmadas (b, c, d, e, f) y 2 ajustadas (a, g). Ninguna refutada. Las salvedades que "
    f"importan: (1) la brecha 225.479 vs 220.522 mezcla nivel turno con nivel vehículo-día; el efecto real de contar Guarantee es "
    f"+{n_astra - n_fable_turno:,} turnos; (2) la fecha de evento de astra es el **checkout** (fable: check-in), lo que convierte en "
    f"churn a {len(churn_conv):,} ventanas cuyo vehículo entró al taller dentro del mes, y en 'retorno' a {len(ya_en_taller):,} "
    f"vehículos que ya estaban en el taller el día del scoring; (3) la preempción de astra corta el 1° del mes y no en "
    f"vencimiento − 30: {n_ret_en_ventana_fable:,} episodios que fable etiquetaría como retorno no existen en astra; "
    f"(4) {len(sal):,} episodios nunca se scorean porque el vencimiento recalculado salta de 'futuro' a 'vencido' entre dos "
    f"snapshots (hallazgo nuevo, no está en el doc). Los archivos: `scripts/revision_cruzada/verif_codigo_astra.py`, "
    "`reports/revision_cruzada/verif_codigo_astra_*.csv`. Nota de integridad: la primera corrida importó `src.features` y "
    "`src.modeling` de astra y Python regeneró tres `.pyc` en su `src/__pycache__/` (mismo código fuente, sin efecto); el "
    "script ahora fija `sys.dont_write_bytecode`. No se tocó ningún otro archivo de astra.\n")
lines.insert(1, resumen)
(OUT / "verif_codigo_astra.md").write_text("\n".join(lines), encoding="utf8")
json.dump([dict(afirmacion=a_, veredicto=v_, original=o_, recalculado=r_, nota=n_) for a_, v_, o_, r_, n_ in tabla],
          open(SCRATCH / "verif_codigo_astra_veredictos.json", "w", encoding="utf8"), ensure_ascii=False, indent=1)
print("\nguardado en", OUT / "verif_codigo_astra.md")
