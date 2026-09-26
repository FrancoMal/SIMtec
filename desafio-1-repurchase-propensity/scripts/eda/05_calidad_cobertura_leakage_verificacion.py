"""Verificacion independiente (rol esceptico) de las afirmaciones del EDA 05.

Recalcula con codigo propio (sin reutilizar el del script original) cada numero clave de
reports/eda/05_calidad_cobertura_leakage.md y prueba las hipotesis alternativas que podrian
refutarlo: denominadores equivocados, `.first()`/`.last()` que saltan nulos, comparaciones NaN,
poblaciones mezcladas (cota de truncamiento), proxies sin tasa de falsos positivos (gap de
maint_number), metricas infladas por placeholders (retrocesos de odometro), fechas de accion
desconocidas (IsReschedule) y numeros citados que el script original no produce.

Salida: stdout (tablas markdown) + reports/eda/05_calidad_cobertura_leakage_verificacion_tablas.md

Uso (desde la carpeta del proyecto):
  PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/05_calidad_cobertura_leakage_verificacion.py
"""
from __future__ import annotations

import io
import warnings

import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_agenda, load_sales

warnings.filterwarnings("ignore", category=FutureWarning)
OUT_MD = config.REPORTS_DIR / "eda" / "05_calidad_cobertura_leakage_verificacion_tablas.md"
_buf = io.StringIO()
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)
AG_START = pd.Timestamp("2024-01-01")


def T(title: str, obj, note: str | None = None) -> None:
    print(f"\n### {title}")
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    txt = obj.to_markdown() if isinstance(obj, pd.DataFrame) else str(obj)
    print(txt)
    if note:
        print(f"_{note}_")
    _buf.write(f"\n### {title}\n\n{txt}\n")
    if note:
        _buf.write(f"\n_{note}_\n")


def P(msg: str) -> None:
    print(msg)
    _buf.write(msg + "\n\n")


def pc(x: float) -> str:
    return f"{100 * x:.1f}%"


_buf.write("# Tablas de verificacion del EDA 05 (script `scripts/eda/05_calidad_cobertura_leakage_verificacion.py`)\n\n")

sales = load_sales()
agenda = load_agenda()
ap = appointments(agenda)
apv = ap.dropna(subset=["vehicle_id"]).copy()
P(f"sales {len(sales):,} | agenda filas {len(agenda):,} | turnos {len(ap):,} | turnos con vehiculo {len(apv):,} | "
  f"vehiculos con id {apv.vehicle_id.nunique():,} | mant. concluidos {int(ap.is_completed_maintenance.sum()):,}")

# Orden canonico: vehiculo, event_date, schedule_id (desempate determinista).
apv = apv.sort_values(["vehicle_id", "event_date", "schedule_id"], kind="mergesort").reset_index(drop=True)
comp = apv[apv.completed]

# =====================================================================================
# V1. KM snapshot vs VehicleCurrentKM
# =====================================================================================
P("## V1. KM es snapshot; VehicleCurrentKM es lectura del turno")
g = apv.groupby("vehicle_id").agg(km_nu=("KM", "nunique"), km_nn=("KM", "count"), km_val=("KM", "max"),
                                  vck_nu=("VehicleCurrentKM", "nunique"), vck_nn=("VehicleCurrentKM", "count"),
                                  vck_max=("VehicleCurrentKM", "max"), n=("schedule_id", "size"),
                                  conn=("ConnectedStatusARG", "first"))
km2 = g[g.km_nn >= 2]
vck2 = g[g.vck_nn >= 2]
# Ultimo turno concluido REAL (la fila, no el ultimo valor no nulo)
last_c = comp.groupby("vehicle_id").tail(1).set_index("vehicle_id")
# Ultimo turno concluido con VCK no nulo (lo que hace pandas .last())
last_c_nn = comp.dropna(subset=["VehicleCurrentKM"]).groupby("vehicle_id").tail(1).set_index("vehicle_id")
# Ultimo turno de cualquier status con VCK no nulo
last_any_nn = apv.dropna(subset=["VehicleCurrentKM"]).groupby("vehicle_id").tail(1).set_index("vehicle_id")

rows = []
for name, d_ in [("ultimo turno (60) Concluido (fila real)", last_c),
                 ("ultimo (60) Concluido con VCK no nulo (= .last() de pandas)", last_c_nn),
                 ("ultimo turno de cualquier status con VCK no nulo", last_any_nn)]:
    both = d_.dropna(subset=["KM", "VehicleCurrentKM"])
    rows.append({"definicion": name, "vehiculos": len(d_), "con KM y VCK no nulos": len(both),
                 "% KM == VCK (sobre vehiculos)": 100 * (d_.KM == d_.VehicleCurrentKM).mean(),
                 "% KM == VCK (sobre ambos no nulos)": 100 * (both.KM == both.VehicleCurrentKM).mean(),
                 "% KM > VCK": 100 * (both.KM > both.VehicleCurrentKM).mean(),
                 "% KM < VCK": 100 * (both.KM < both.VehicleCurrentKM).mean()})
V1_1 = pd.DataFrame(rows).set_index("definicion")
T("V1.1 KM vs VehicleCurrentKM del ultimo turno, tres definiciones",
  V1_1.round(1),
  f"KM constante por vehiculo: {int((km2.km_nu == 1).sum()):,} de {len(km2):,} con >=2 lecturas ({pc((km2.km_nu == 1).mean())}); "
  f"VCK varia en {int((vck2.vck_nu > 1).sum()):,} de {len(vck2):,} ({pc((vck2.vck_nu > 1).mean())}).")

# Hipotesis telemetria: KM > VCK_ultimo se concentra en Conectado?
both = last_c.dropna(subset=["KM", "VehicleCurrentKM"]).copy()
both["rel"] = np.select([both.KM == both.VehicleCurrentKM, both.KM > both.VehicleCurrentKM], ["igual", "KM > VCK"], "KM < VCK")
V1_2 = pd.crosstab(both.ConnectedStatusARG, both.rel, normalize="index") * 100
V1_2["vehiculos"] = both.ConnectedStatusARG.value_counts()
T("V1.2 Relacion KM vs VCK del ultimo concluido, por ConnectedStatusARG (hipotesis: KM viene de telemetria en conectados)", V1_2.round(1))
# Cuanto excede KM a la ultima lectura cuando difiere, por conectividad
exc = both[both.rel == "KM > VCK"]
V1_2b = exc.groupby("ConnectedStatusARG").apply(lambda d_: pd.Series({
    "vehiculos": len(d_), "mediana KM - VCK": (d_.KM - d_.VehicleCurrentKM).median(),
    "mediana dias CUTOFF - ultimo turno": (CUTOFF - d_.event_date).dt.days.median()}), include_groups=False)
T("V1.2b Cuando KM > VCK del ultimo concluido: exceso mediano y antiguedad del ultimo turno", V1_2b.round(0))

# Nivel turno: es el ultimo concluido o no
comp2 = comp.dropna(subset=["KM", "VehicleCurrentKM"]).copy()
comp2["es_ultimo"] = comp2.schedule_id.isin(last_c.schedule_id)
comp2["igual"] = comp2.KM == comp2.VehicleCurrentKM
V1_3 = comp2.groupby("es_ultimo").igual.agg(["size", "mean"])
V1_3["mean"] *= 100
V1_3.columns = ["turnos concluidos", "% KM == VCK"]
T("V1.3 Turnos concluidos: KM == VCK segun sea o no el ultimo concluido del vehiculo", V1_3.round(1))
V1_4 = comp2.groupby(comp2.ScheduleDate.dt.year).igual.mean().mul(100).rename("% KM == VCK").to_frame()
V1_4["% es ultimo"] = comp2.groupby(comp2.ScheduleDate.dt.year).es_ultimo.mean() * 100
T("V1.4 Turnos concluidos por anio: % KM == VCK y % que son el ultimo del vehiculo (confusion)", V1_4.round(1))
V1_5 = ap.groupby("StatusARG").VehicleCurrentKM.apply(lambda s: 100 * s.isna().mean()).rename("% VCK nulo").to_frame()
V1_5["turnos"] = ap.StatusARG.value_counts()
T("V1.5 Nulos de VehicleCurrentKM por StatusARG", V1_5.round(1))
vck_clean = apv.VehicleCurrentKM.where(apv.VehicleCurrentKM.between(100, 1e6))
gmax_clean = vck_clean.groupby(apv.vehicle_id).max()
gg = g.join(gmax_clean.rename("vck_max_clean"))
P(f"KM >= max(VCK) (crudo): {pc((gg.km_val >= gg.vck_max)[gg.vck_max.notna() & gg.km_val.notna()].mean())}; "
  f"KM >= max(VCK) con VCK limpio (100..1M): {pc((gg.km_val >= gg.vck_max_clean)[gg.vck_max_clean.notna() & gg.km_val.notna()].mean())}.")

# =====================================================================================
# V2. ConnectedStatusARG
# =====================================================================================
P("## V2. ConnectedStatusARG es snapshot y esta confundido con la generacion")
cs_nu = apv.groupby("vehicle_id").ConnectedStatusARG.nunique()
n_appt = apv.groupby("vehicle_id").size()
P(f"Vehiculos con >=2 turnos: {int((n_appt >= 2).sum()):,}; con >1 valor de ConnectedStatusARG: {int((cs_nu[n_appt >= 2] > 1).sum()):,} "
  f"({pc((cs_nu[n_appt >= 2] > 1).mean())}).")
veh = apv.groupby("vehicle_id").agg(WSD=("WarrantyStartDate", "first"), MY=("ModelYear", "first"),
                                    cs=("ConnectedStatusARG", "first"), TMA=("TMA", "first"))
pre = veh[veh.WSD < "2023-07-01"]; post = veh[veh.WSD >= "2023-07-01"]
P(f"'Conectado' con WSD < 2023-07-01: {pc((pre.cs == 'Conectado').mean())} (n={len(pre):,}); WSD >= 2023-07-01: {pc((post.cs == 'Conectado').mean())} (n={len(post):,}).")
q = veh.WSD.dt.to_period("Q")
V2_1 = (pd.crosstab(q, veh.cs, normalize="index") * 100).loc[[pd.Period(x) for x in ("2023Q2", "2023Q3", "2024Q2", "2025Q1", "2025Q4", "2026Q2", "2026Q3")]]
V2_1["vehiculos"] = q.value_counts().reindex(V2_1.index)
V2_1.index = V2_1.index.astype(str)
T("V2.1 ConnectedStatusARG por trimestre de WSD (trimestres citados)", V2_1.round(1))
V2_2 = ap.groupby("ConnectedStatusARG")[["completed", "is_completed_maintenance"]].mean().mul(100)
V2_2.columns = ["% concluido", "% mant. concluido"]
V2_2["turnos"] = ap.ConnectedStatusARG.value_counts()
T("V2.2 Resultado del turno por ConnectedStatusARG, sin control (reproduce B2b)", V2_2.round(1))
# Control por generacion y edad: solo vehiculos P703 entregados 2023H2-2024, turnos 2025-2026
ctrl = apv[(apv.WarrantyStartDate >= "2023-07-01") & (apv.WarrantyStartDate < "2025-01-01") & (apv.ScheduleDate >= "2025-01-01") & (apv.ScheduleDate <= CUTOFF)]
V2_3 = ctrl.groupby("ConnectedStatusARG")[["completed", "is_completed_maintenance", "no_show", "cancelled"]].mean().mul(100)
V2_3.columns = ["% concluido", "% mant. concluido", "% no asistio", "% cancelado"]
V2_3["turnos"] = ctrl.ConnectedStatusARG.value_counts()
T("V2.3 Mismo control por generacion/edad: vehiculos con WSD 2023-07..2024-12, turnos 2025-01..CUTOFF", V2_3.round(1),
  "Controlando la generacion, la brecha Conectado vs No tiene Conectividad en mantenimiento concluido se reduce a pocos puntos.")

# =====================================================================================
# V3. Survey
# =====================================================================================
P("## V3. SurveyResponseDate es anterior al turno")
sv = ap[ap.SurveyResponseDate.notna()].copy()
P(f"Turnos con survey: {len(sv):,} de {len(ap):,} ({pc(len(sv) / len(ap))}). Por status: " + ", ".join(f"{k}: {v:,}" for k, v in sv.StatusARG.value_counts().items()))
rows = []
for name, ref in [("survey - checkout", sv.EffectiveCheckoutDate), ("survey - checkin", sv.EffectiveCheckinDate), ("survey - ScheduleDate", sv.ScheduleDate)]:
    lag = (sv.SurveyResponseDate - ref).dt.days.dropna()
    rows.append({"lag": name, "n": len(lag), "min": lag.min(), "p5": lag.quantile(.05), "mediana": lag.median(), "p95": lag.quantile(.95), "max": lag.max(),
                 "% < 0": 100 * (lag < 0).mean(), "% = 0": 100 * (lag == 0).mean(), "% > 0": 100 * (lag > 0).mean(), "n > 0": int((lag > 0).sum())})
T("V3.1 Lags survey vs fechas del turno", pd.DataFrame(rows).set_index("lag").round(2))
src = ap.groupby("ScheduleSource").SurveyResponseDate.apply(lambda s: 100 * s.notna().mean()).rename("% con survey").to_frame()
src["turnos"] = ap.ScheduleSource.value_counts()
T("V3.2 % de turnos con survey por ScheduleSource", src.round(1))
T("V3.3 Rating medio por StatusARG", sv.groupby("StatusARG").SurveyStarRating.agg(["size", "mean"]).round(2))
# Misma survey copiada en varios turnos del mismo vehiculo?
svv = sv.dropna(subset=["vehicle_id"])
dup_sv = svv.duplicated(subset=["vehicle_id", "SurveyResponseDate"], keep=False)
dup_svc = sv.duplicated(subset=["customer_id", "SurveyResponseDate"], keep=False) & sv.customer_id.notna()
P(f"Turnos con survey cuyo (vehicle_id, SurveyResponseDate) se repite en otro turno: {int(dup_sv.sum()):,} de {len(svv):,} ({pc(dup_sv.mean())}); "
  f"por (customer_id, SurveyResponseDate): {int(dup_svc.sum()):,} ({pc(dup_svc.sum() / sv.customer_id.notna().sum())}).")
dd_ = svv[dup_sv].groupby(["vehicle_id", "SurveyResponseDate"]).StatusARG.apply(lambda s: " | ".join(sorted(s))).value_counts().head(6)
T("V3.4 Combinaciones de status cuando la misma survey aparece en >1 turno del vehiculo", dd_.rename("grupos").to_frame())
# Lag a la visita concluida previa (implementacion propia, sin merge_asof)
cmp_ = comp.dropna(subset=["EffectiveCheckoutDate"])[["vehicle_id", "EffectiveCheckoutDate"]].sort_values("EffectiveCheckoutDate")
svs = svv[["vehicle_id", "SurveyResponseDate"]].sort_values("SurveyResponseDate")
m3 = pd.merge_asof(svs, cmp_.rename(columns={"EffectiveCheckoutDate": "prev_out"}), left_on="SurveyResponseDate", right_on="prev_out",
                   by="vehicle_id", direction="backward", allow_exact_matches=False)
l3 = (m3.SurveyResponseDate - m3.prev_out).dt.days
P(f"Lag survey - ultimo checkout concluido previo del mismo vehiculo (estricto <): n con previo {int(l3.notna().sum()):,} ({pc(l3.notna().mean())}); "
  f"mediana {l3.median():.0f} d; <=14 d: {pc((l3 <= 14).sum() / l3.notna().sum())} de los que tienen previo, {pc((l3 <= 14).mean())} del total.")
lead = (sv.ScheduleDate - sv.SurveyResponseDate).dt.days
P(f"Anticipacion (ScheduleDate - survey): mediana {lead.median():.0f}, p75 {lead.quantile(.75):.0f}, p90 {lead.quantile(.9):.0f}, <=30 d: {pc((lead <= 30).mean())}.")
P(f"Surveys con fecha > CUTOFF: {int((ap.SurveyResponseDate > CUTOFF).sum())}; minima: {ap.SurveyResponseDate.min().date()}.")
# Reservas futuras conocidas en t via survey
rows = []
for t in [pd.Timestamp("2025-07-01"), pd.Timestamp("2026-01-01"), pd.Timestamp("2026-06-01")]:
    k = ap[(ap.ScheduleDate >= t) & (ap.SurveyResponseDate < t)]
    rows.append({"t": str(t.date()), "turnos con ScheduleDate >= t y survey < t": len(k), "vehiculos": k.vehicle_id.nunique(),
                 "concluidos luego": int(k.completed.sum()), "mant. concluidos luego": int(k.is_completed_maintenance.sum())})
T("V3.5 Reservas futuras conocidas en t gracias a la survey (unico proxy de fecha de reserva)", pd.DataFrame(rows).set_index("t"))

# =====================================================================================
# V4. Left-censoring
# =====================================================================================
P("## V4. Left-censoring")
n_veh = apv.vehicle_id.nunique()
wsd_v = apv.groupby("vehicle_id").WarrantyStartDate.first()
P(f"Vehiculos con id: {n_veh:,}; con WSD: {int(wsd_v.notna().sum()):,}; WSD < 2024-01-01: {int((wsd_v < AG_START).sum()):,} = "
  f"{pc((wsd_v < AG_START).sum() / n_veh)} de todos, {pc((wsd_v < AG_START).sum() / wsd_v.notna().sum())} de los que tienen WSD.")
cm = apv[apv.is_completed_maintenance]
rows = []
for t in [pd.Timestamp("2024-07-01"), pd.Timestamp("2025-01-01"), pd.Timestamp("2026-01-01"), CUTOFF]:
    act = apv.loc[apv.event_date < t, "vehicle_id"].unique()
    prev = cm[cm.event_date < t]
    npv = prev.groupby("vehicle_id").size().reindex(act, fill_value=0)
    lastrow = prev.groupby("vehicle_id").tail(1).set_index("vehicle_id")
    dsl = (t - lastrow.event_date).dt.days
    gap = (lastrow.maint_number - npv.reindex(lastrow.index))
    rows.append({"t": str(t.date()), "activos": len(act), "% sin mant.": 100 * (npv == 0).mean(), "mediana dsl": dsl.median(),
                 "p90 dsl": dsl.quantile(.9), "techo": (t - AG_START).days, "% gap > 0": 100 * (gap > 0).mean(), "mediana gap": gap.median()})
T("V4.1 Reproduccion de A1 con codigo propio", pd.DataFrame(rows).set_index("t").round(1))
# Cota A3 reproducida
act = apv.loc[apv.event_date < CUTOFF, "vehicle_id"].unique()
prev = cm[cm.event_date < CUTOFF]
lastrow = prev.groupby("vehicle_id").tail(1)
dsl_cut = (CUTOFF - lastrow.event_date).dt.days
P("A3 reproducida (share de la distribucion de dsl al CUTOFF que supera cada ventana): " +
  ", ".join(f"{w} d: {pc((dsl_cut > w).mean())}" for w in (182, 366, 547, 731)))
# Misma poblacion, distinta profundidad de historia: vehiculos con >=1 turno en los ultimos 182 dias antes del CUTOFF
age_bins, age_lab = [-10, 1, 2, 3, 5, 8, 40], ["<1", "1-2", "2-3", "3-5", "5-8", "8+"]
rows = []
act6 = apv.loc[(apv.event_date < CUTOFF) & (apv.event_date >= CUTOFF - pd.Timedelta(days=182)), "vehicle_id"].unique()
age6 = ((CUTOFF - wsd_v.reindex(act6)).dt.days / 365.25)
ab = pd.cut(age6, age_bins, labels=age_lab)
for look in (182, 366, 547, 731, (CUTOFF - AG_START).days):
    pv = cm[(cm.event_date < CUTOFF) & (cm.event_date >= CUTOFF - pd.Timedelta(days=look))].groupby("vehicle_id").size().reindex(act6, fill_value=0)
    r = {"historia (dias)": look, "% sin mant. observado": 100 * (pv == 0).mean()}
    r.update({f"{k}": v for k, v in (100 * (pv == 0).groupby(ab, observed=True).mean()).round(1).items()})
    rows.append(r)
V4_2 = pd.DataFrame(rows).set_index("historia (dias)")
T("V4.2 Misma poblacion (vehiculos con >=1 turno en los 182 d previos al CUTOFF, n=%d): %% sin mantenimiento observado segun profundidad de historia, total y por edad" % len(act6),
  V4_2.round(1), "Aisla el efecto de la profundidad de historia del efecto calendario/poblacion que mezcla A2.")

# =====================================================================================
# V5. maint_number como proxy de historia
# =====================================================================================
P("## V5. maint_number del ultimo service como proxy de historia invisible")
first_row = cm.dropna(subset=["maint_number"]).groupby("vehicle_id").head(1).set_index("vehicle_id")
first_row = first_row.join(wsd_v.rename("WSD"))
first_row["edad"] = (first_row.event_date - first_row.WSD).dt.days / 365.25
ok = first_row.dropna(subset=["edad"])
P(f"Primer mantenimiento concluido observado (fila real, maint_number no nulo): {len(first_row):,} vehiculos; con WSD {len(ok):,}. "
  f"Correlacion Pearson(maint_number, edad) = {ok[['maint_number', 'edad']].corr().iloc[0, 1]:.3f}; Spearman = {ok[['maint_number', 'edad']].corr(method='spearman').iloc[0, 1]:.3f}. "
  f"Edad > 2 anios: {int((ok.edad > 2).sum()):,}; de ellos con 1° service: {int(((ok.edad > 2) & (ok.maint_number == 1)).sum()):,} ({pc(((ok.edad > 2) & (ok.maint_number == 1)).sum() / (ok.edad > 2).sum())}).")
P(f"Mantenimientos concluidos con maint_number nulo (has_maint por regex sin ServiceMaintenance): {int(cm.maint_number.isna().sum()):,}.")
# Falsos positivos del gap: vehiculos entregados >= 2024-01-01 (toda su historia es visible)
rows = []
for t in [pd.Timestamp("2025-01-01"), CUTOFF]:
    prev = cm[cm.event_date < t]
    npv = prev.groupby("vehicle_id").size()
    lastrow = prev.groupby("vehicle_id").tail(1).set_index("vehicle_id")
    gap = (lastrow.maint_number - npv.reindex(lastrow.index)).dropna()
    w = wsd_v.reindex(gap.index)
    for lab, mask in [("WSD < 2024-01-01 (historia invisible posible)", w < AG_START), ("WSD >= 2024-01-01 (toda la historia es visible)", w >= AG_START)]:
        gg_ = gap[mask]
        rows.append({"t": str(t.date()), "grupo": lab, "vehiculos": len(gg_), "% gap > 0": 100 * (gg_ > 0).mean(), "% gap >= 2": 100 * (gg_ >= 2).mean(),
                     "% gap < 0": 100 * (gg_ < 0).mean(), "mediana gap": gg_.median()})
T("V5.1 gap = maint_number del ultimo service - n mantenimientos observados, por visibilidad de la historia (tasa de falsos positivos del proxy)",
  pd.DataFrame(rows).set_index(["t", "grupo"]).round(1))
cm_s = cm.dropna(subset=["maint_number"])
inc = (cm_s.maint_number - cm_s.groupby("vehicle_id").maint_number.shift()).dropna()
P(f"Incremento entre mantenimientos consecutivos (n={len(inc):,}): +1 {pc((inc == 1).mean())}, +2 {pc((inc == 2).mean())}, >=3 {pc((inc >= 3).mean())}, 0 {pc((inc == 0).mean())}, <0 {pc((inc < 0).mean())}.")
ed = ((cm.event_date - cm.WarrantyStartDate).dt.days / 365.25)
med = ed.groupby(cm.maint_number).median()
P("Edad mediana al service por maint_number: " + ", ".join(f"{int(k)}°: {v:.2f}" for k, v in med.items() if k in (1, 2, 3, 4, 8, 10, 12, 13, 19, 20)))
# Que ServiceName tiene cada ServiceMaintenance (codigos 11-13 y 20)
mi = agenda[agenda.ServiceMaintenance.isin([1, 2, 3, 11, 12, 13, 19, 20])]
V5_2 = pd.crosstab(mi.ServiceMaintenance, mi.ServiceName).T
V5_2 = V5_2[V5_2.sum(axis=1) > 50]
T("V5.2 ServiceName por ServiceMaintenance (codigos 1-3, 11-13, 19-20)", V5_2)

# =====================================================================================
# V6. Turnos futuros y pendientes
# =====================================================================================
P("## V6. Turnos futuros / pendientes")
fut = ap[ap.ScheduleDate > CUTOFF]
pend = ap[ap.StatusARG.isin(["(30) Agendado", "(40) En progreso"])]
old = pend[pend.ScheduleDate <= CUTOFF]
stale = pend[pend.ScheduleDate <= CUTOFF - pd.Timedelta(days=30)]
V6 = pd.Series({
    "ScheduleDate > CUTOFF": len(fut), "  (30)": int((fut.StatusARG == "(30) Agendado").sum()), "  (70)": int((fut.StatusARG == "(70) Cancelado").sum()),
    "  (40)": int((fut.StatusARG == "(40) En progreso").sum()), "  otros": int((~fut.StatusARG.isin(["(30) Agendado", "(70) Cancelado", "(40) En progreso"])).sum()),
    "  con item mant.": int(fut.has_maint.sum()), "  vehiculos (30)": fut[fut.StatusARG == "(30) Agendado"].vehicle_id.nunique(),
    "pendientes total": len(pend), "pendientes <= CUTOFF": len(old), "stale (<= CUTOFF-30)": len(stale),
    "  (40) stale": int((stale.StatusARG == "(40) En progreso").sum()), "  (30) stale": int((stale.StatusARG == "(30) Agendado").sum()),
    "pendientes <= CUTOFF-180": int((pend.ScheduleDate <= CUTOFF - pd.Timedelta(days=180)).sum()),
    "filas-item (30) con ScheduleDate > CUTOFF (agenda cruda)": int(((agenda.StatusARG == "(30) Agendado") & (agenda.ScheduleDate > CUTOFF)).sum()),
    "(60) con ScheduleDate > CUTOFF": int((fut.StatusARG == "(60) Concluido").sum()),
}).rename("valor").to_frame()
T("V6.1 Reproduccion de D1", V6)
enp = ap[ap.StatusARG == "(40) En progreso"]
P(f"(40) En progreso: check-in no nulo {pc(enp.EffectiveCheckinDate.notna().mean())}, checkout nulo {pc(enp.EffectiveCheckoutDate.isna().mean())}; "
  f"ultimo checkout {ap.EffectiveCheckoutDate.max().date()}; ultimo check-in {ap.EffectiveCheckinDate.max().date()}. "
  f"Reservas futuras por mes: " + ", ".join(f"{k}: {v:,}" for k, v in fut.ScheduleDate.dt.to_period('M').value_counts().sort_index().items()))
P(f"Columnas que podrian ser fecha de creacion: {[c for c in agenda.columns if 'reat' in c.lower() or 'created' in c.lower()]} (ninguna).")

# =====================================================================================
# V7. IsReschedule / ScheduleReturn
# =====================================================================================
P("## V7. IsReschedule y ScheduleReturn")
T("V7.1 IsReschedule x StatusARG (turnos)", pd.crosstab(ap.IsReschedule.fillna("NaN"), ap.StatusARG))
raw_c = agenda[agenda.StatusARG == "(70) Cancelado"]
T("V7.2 En filas canceladas: IsReschedule x ScheduleStatus (agenda cruda)", pd.crosstab(raw_c.IsReschedule.fillna("NaN"), raw_c.ScheduleStatus.fillna("NaN")))
apx = apv.copy()
grp = apx.groupby("vehicle_id")
apx["next_ev"] = grp.event_date.shift(-1); apx["prev_ev"] = grp.event_date.shift(1)
apx["next_st"] = grp.StatusARG.shift(-1); apx["prev_st"] = grp.StatusARG.shift(1)
apx["next_resch"] = grp.IsReschedule.shift(-1); apx["next_sched"] = grp.ScheduleDate.shift(-1)
apx["d_next"] = (apx.next_ev - apx.event_date).dt.days; apx["d_prev"] = (apx.event_date - apx.prev_ev).dt.days
canc = apx[apx.cancelled]
rows = []
for v in ["N", "Y"]:
    x = canc[canc.IsReschedule == v]
    rows.append({"IsReschedule": v, "turnos": len(x), "% turno posterior <=7d": 100 * (x.d_next <= 7).mean(), "% <=30d": 100 * (x.d_next <= 30).mean(),
                 "% algun turno posterior": 100 * x.next_ev.notna().mean(), "% siguiente es concluido (<=30d)": 100 * ((x.d_next <= 30) & (x.next_st == "(60) Concluido")).mean(),
                 "% siguiente tiene IsReschedule=Y": 100 * (x.next_resch == "Y").mean(),
                 "% siguiente el MISMO dia": 100 * (x.d_next == 0).mean(),
                 "% turno anterior <=30d": 100 * (x.d_prev <= 30).mean(), "% anterior cancelado <=30d": 100 * ((x.d_prev <= 30) & (x.prev_st == "(70) Cancelado")).mean()})
T("V7.3 Cancelados segun IsReschedule: que hay antes y despues (mismo vehiculo)", pd.DataFrame(rows).set_index("IsReschedule").round(1))
cc_ = apx[apx.completed]
rows = []
for lab, x in [("(60) IsReschedule=Y", cc_[cc_.IsReschedule == "Y"]), ("(60) IsReschedule=NaN", cc_[cc_.IsReschedule.isna()]),
               ("(60) ScheduleReturn=Y", cc_[cc_.ScheduleReturn == "Y"]), ("(60) ScheduleReturn=N", cc_[cc_.ScheduleReturn == "N"])]:
    rows.append({"grupo": lab, "turnos": len(x), "% turno anterior <=30d": 100 * (x.d_prev <= 30).mean(), "% anterior cancelado <=30d": 100 * ((x.d_prev <= 30) & (x.prev_st == "(70) Cancelado")).mean(),
                 "% anterior concluido <=30d": 100 * ((x.d_prev <= 30) & (x.prev_st == "(60) Concluido")).mean(),
                 "% con mant.": 100 * x.has_maint.mean(), "% con reparacion": 100 * x.has_repair.mean(), "% con diagnostico": 100 * x.has_diag.mean()})
T("V7.4 Concluidos segun IsReschedule y ScheduleReturn", pd.DataFrame(rows).set_index("grupo").round(1))
prev30 = cc_[cc_.d_prev <= 30]
P(f"Inverso: entre concluidos con un turno previo a <=30 d ({len(prev30):,}), ScheduleReturn=Y en {pc((prev30.ScheduleReturn == 'Y').mean())}; "
  f"con previo concluido a <=30 d ({int(((cc_.d_prev <= 30) & (cc_.prev_st == '(60) Concluido')).sum()):,}): {pc((prev30[prev30.prev_st == '(60) Concluido'].ScheduleReturn == 'Y').mean())}.")

# =====================================================================================
# V8. Cancelaciones administrativas
# =====================================================================================
P("## V8. Cancelaciones y no-show")
cx = apv[apv.cancelled][["schedule_id", "vehicle_id", "ScheduleDate", "has_maint"]].rename(columns={"has_maint": "c_maint"})
cs_ = comp[["vehicle_id", "event_date", "has_maint"]].rename(columns={"event_date": "cdate", "has_maint": "k_maint"})
j = cx.merge(cs_, on="vehicle_id", how="left")
j["d"] = (j.cdate - j.ScheduleDate).dt.days
j["same"] = j.d == 0; j["w7"] = j.d.abs() <= 7; j["f30"] = j.d.between(0, 30); j["m7"] = j.w7 & j.k_maint.fillna(False)
agg = j.groupby("schedule_id")[["same", "w7", "f30", "m7"]].any().reindex(cx.schedule_id).fillna(False)
cxm = cx[cx.c_maint]
V8 = pd.Series({"(70) con vehicle_id": len(cx), "% con (60) el mismo dia": 100 * agg.same.mean(), "% con (60) a <=7 d": 100 * agg.w7.mean(),
                "% seguido de (60) en 30 d": 100 * agg.f30.mean(),
                "(70) con item de mantenimiento": len(cxm), "  % con (60) con mant. a <=7 d": 100 * agg.loc[cxm.schedule_id, "m7"].mean()}).rename("valor").to_frame()
ns = apv[apv.no_show][["schedule_id", "vehicle_id", "ScheduleDate"]]
jn = ns.merge(cs_, on="vehicle_id", how="left"); jn["d"] = (jn.cdate - jn.ScheduleDate).dt.days
jn["f30"] = jn.d.between(0, 30)
f30n = jn.groupby("schedule_id").f30.any().reindex(ns.schedule_id).fillna(False)
V8.loc["(80) con vehicle_id"] = len(ns); V8.loc["  % seguido de (60) en 30 d"] = 100 * f30n.mean()
T("V8.1 Reproduccion de G2 (join completo, sin merge_asof)", V8.round(1))
gm = cm.copy(); gm["gap"] = (gm.event_date - gm.groupby("vehicle_id").event_date.shift()).dt.days
gm["same_mn"] = gm.maint_number.eq(gm.groupby("vehicle_id").maint_number.shift())
P(f"Mantenimientos concluidos a <=7 d de otro del mismo vehiculo: {int((gm.gap <= 7).sum()):,} (mismo maint_number {int(((gm.gap <= 7) & gm.same_mn).sum()):,}); "
  f"a <=30 d: {int((gm.gap <= 30).sum()):,}; mismo dia: {int((gm.gap == 0).sum()):,}.")
pairs = apv.groupby(["vehicle_id", "ScheduleDate"]).schedule_id.nunique()
P(f"Pares (vehiculo, ScheduleDate) con >1 schedule_id: {int((pairs > 1).sum()):,}; turnos {int(pairs[pairs > 1].sum()):,}.")

# =====================================================================================
# V9. Cobertura sales-agenda
# =====================================================================================
P("## V9. Cobertura sales vs agenda")
s_idx = sales.set_index("vehicle_id")
both_v = s_idx.index.intersection(wsd_v.index)
P(f"Vehiculos en ambas tablas: {len(both_v):,}.")
w_s = s_idx.loc[both_v, "WarrantyStartDate"]; w_a = wsd_v.reindex(both_v)
m_ = pd.DataFrame({"ws": w_s, "wa": w_a, "dd": s_idx.loc[both_v, "DeliveryDate"]})
mm_ = m_.dropna(subset=["ws", "wa"])
P(f"Con WSD en ambas: {len(mm_):,}; iguales {int((mm_.ws == mm_.wa).sum()):,} ({pc((mm_.ws == mm_.wa).mean())}); distintas {int((mm_.ws != mm_.wa).sum()):,}; "
  f"|dif| > 30 d: {int(((mm_.ws - mm_.wa).dt.days.abs() > 30).sum())}; mediana |dif| entre distintas: {(mm_.ws - mm_.wa).dt.days.abs()[mm_.ws != mm_.wa].median():.0f}. "
  f"Con WSD en agenda pero nula en sales: {int((m_.wa.notna() & m_.ws.isna()).sum())}. WSD agenda == DeliveryDate sales: {pc((m_.wa == m_.dd)[m_.wa.notna()].mean())}.")
in_sales = wsd_v.index.isin(s_idx.index)
w24 = wsd_v >= AG_START
P(f"Vehiculos de la agenda con WSD >= 2024-01-01: {int(w24.sum()):,}; en sales {int((w24 & in_sales).sum()):,} ({pc((w24 & in_sales).sum() / w24.sum())}).")
my_v = apv.groupby("vehicle_id").ModelYear.first()
new = (my_v >= 2024) & ~pd.Series(in_sales, index=wsd_v.index)
P(f"MY >= 2024 y no en sales: {int(new.sum()):,}; con WSD en 2023: {int((wsd_v[new].dt.year == 2023).sum()):,}.")
age_s = (CUTOFF - sales.SalesDate).dt.days
has_any = sales.vehicle_id.isin(apv.vehicle_id)
has_comp = sales.vehicle_id.isin(comp.vehicle_id)
has_cm = sales.vehicle_id.isin(cm.vehicle_id)
rows = []
for lab, mk in [("todas", age_s >= 0), ("> 365 d", age_s > 365), ("> 730 d", age_s > 730)]:
    rows.append({"ventas": lab, "n": int(mk.sum()), "% >=1 turno": 100 * has_any[mk].mean(), "% >=1 (60)": 100 * has_comp[mk].mean(), "% >=1 mant. concluido": 100 * has_cm[mk].mean()})
T("V9.1 Presencia en agenda de los vendidos, tres definiciones", pd.DataFrame(rows).set_index("ventas").round(1))
s365 = sales[age_s > 365]
V9_2 = pd.concat([s365.groupby("BusinessUnit").vehicle_id.apply(lambda x: 100 * x.isin(apv.vehicle_id).mean()),
                  s365.groupby("SalesChannel").vehicle_id.apply(lambda x: 100 * x.isin(apv.vehicle_id).mean())]).rename("% en agenda").to_frame()
T("V9.2 Ventas > 365 d por segmento", V9_2.round(1))
# Cohorte: % con primer turno dentro de 365 d de la venta, por mes de venta (solo cohortes con 365 d de exposicion)
fe = apv.groupby("vehicle_id").event_date.min()
sc = sales[age_s > 365].copy(); sc["first_ev"] = sc.vehicle_id.map(fe)
sc["in365"] = (sc.first_ev - sc.SalesDate).dt.days <= 365
V9_3 = sc.groupby(sc.SalesDate.dt.to_period("Q")).agg(ventas=("vehicle_id", "size"), pct_turno_365d=("in365", "mean"))
V9_3["pct_turno_365d"] *= 100; V9_3.index = V9_3.index.astype(str)
T("V9.3 % de vendidos con >=1 turno dentro de los 365 d de la venta, por trimestre de venta (exposicion completa)", V9_3.round(1),
  "Si es estable, la caida de cobertura en cohortes recientes es solo falta de tiempo.")
mb = s_idx.loc[both_v, ["DeliveryDate"]].join(fe.rename("first_ev"))
P(f"Primer turno antes de DeliveryDate: {int((mb.first_ev < mb.DeliveryDate).sum()):,} ({pc((mb.first_ev < mb.DeliveryDate).mean())}); > 30 d antes: {int(((mb.DeliveryDate - mb.first_ev).dt.days > 30).sum())}.")
buyer = s_idx.customer_id
eqv = apv.assign(b=apv.vehicle_id.map(buyer)).dropna(subset=["b"]).assign(e=lambda d_: d_.customer_id == d_.b).groupby("vehicle_id").e.any()
P(f"Comprador aparece en algun turno: {int(eqv.sum()):,} de {len(eqv):,} ({pc(eqv.mean())}).")

# =====================================================================================
# V10. Inconsistencias
# =====================================================================================
P("## V10. Inconsistencias puntuales")
ci_old = ap[ap.EffectiveCheckinDate < AG_START]
P(f"Check-in < 2024-01-01: {len(ci_old)} turnos; fechas {sorted(ci_old.EffectiveCheckinDate.dt.date.astype(str))}; DaysInDealer {ci_old.DaysInDealer.tolist()}.")
gap_ci = (ap.EffectiveCheckinDate - ap.ScheduleDate).dt.days
P(f"Turnos con check-in: {int(gap_ci.notna().sum()):,}; mismo dia {pc((gap_ci == 0).sum() / gap_ci.notna().sum())}; |gap| > 30: {int((gap_ci.abs() > 30).sum())}; "
  f"|gap| > 45 (eventos.py usa ScheduleDate): {int((gap_ci.abs() > 45).sum())}; event_date != check-in entre turnos con check-in: {int((ap.event_date != ap.EffectiveCheckinDate)[ap.EffectiveCheckinDate.notna()].sum())}.")
nci = ap.completed & ap.EffectiveCheckinDate.isna()
P(f"(60) sin check-in: {int(nci.sum()):,} de {int(ap.completed.sum()):,} ({pc(nci.sum() / ap.completed.sum())}); en 2024: {pc(ap[ap.completed & (ap.ScheduleDate.dt.year == 2024)].EffectiveCheckinDate.isna().mean())}; "
  f"2025: {pc(ap[ap.completed & (ap.ScheduleDate.dt.year == 2025)].EffectiveCheckinDate.isna().mean())}; 2026: {pc(ap[ap.completed & (ap.ScheduleDate.dt.year == 2026)].EffectiveCheckinDate.isna().mean())}.")
c_ = ap[ap.completed]
low = c_.VehicleCurrentKM[c_.VehicleCurrentKM < 100]
P(f"VCK < 100 en concluidos: {len(low):,} ({pc(len(low) / len(c_))}); top valores: {low.value_counts().head(5).to_dict()}; VCK > 1e6: {int((c_.VehicleCurrentKM > 1e6).sum())}; > 5e5: {int((c_.VehicleCurrentKM > 5e5).sum())}.")
# Retrocesos crudos vs limpios
def regress(df: pd.DataFrame, label: str) -> dict:
    d_ = df.dropna(subset=["VehicleCurrentKM"]).sort_values(["vehicle_id", "event_date", "schedule_id"], kind="mergesort")
    d_ = d_.assign(prev=d_.groupby("vehicle_id").VehicleCurrentKM.shift(), prev_dt=d_.groupby("vehicle_id").event_date.shift()).dropna(subset=["prev"])
    dk = d_.VehicleCurrentKM - d_.prev; days = (d_.event_date - d_.prev_dt).dt.days.clip(lower=1); kmd = dk / days
    return {"filtro": label, "pares": len(d_), "retrocede > 1.000 km": int((dk < -1000).sum()), "% pares": 100 * (dk < -1000).mean(),
            "vehiculos con retroceso": d_.loc[dk < -1000, "vehicle_id"].nunique(), "retrocede > 10.000": int((dk < -10000).sum()),
            "> 300 km/dia (excl. mismo dia)": int(((kmd > 300) & (days > 1)).sum()), "% > 300 km/dia": 100 * ((kmd > 300) & (days > 1)).mean(),
            "km/dia mediana": kmd.median(), "km/dia p99": kmd.quantile(.99)}
V10_1 = pd.DataFrame([regress(comp[comp.VehicleCurrentKM > 0], "VCK > 0 (script original)"),
                      regress(comp[comp.VehicleCurrentKM.between(100, 1e6)], "VCK en [100, 1.000.000] (placeholders y >1M fuera)")]).set_index("filtro")
T("V10.1 Retrocesos de odometro y ritmo implausible, crudo vs. con placeholders excluidos", V10_1.round(1))
bad_my = ((my_v == 0) | (my_v < 2005))
P(f"Vehiculos con ModelYear 0/<2005: {int(bad_my.sum())}; sin WSD: {int((bad_my & wsd_v.isna()).sum())}.")
P(f"sales: DeliveryDate < 2020: {int((sales.DeliveryDate < '2020-01-01').sum())} ({sorted(sales.DeliveryDate[sales.DeliveryDate < '2020-01-01'].dt.year.tolist())}); "
  f"Status != ACCEPTED: {int((sales.Status != 'ACCEPTED').sum())}, sin DeliveryDate: {int(sales[sales.Status != 'ACCEPTED'].DeliveryDate.isna().sum())}; "
  f"GLOBAL RANGER: {int((sales.ModelShortName != 'RANGER').sum())}; PersonType: {sales.PersonType.value_counts(dropna=False).to_dict()}; "
  f"PersonType 25 canal HR: {pc((sales[sales.PersonType == '25'].SalesChannel == 'HR').mean())}.")
spd = agenda.ServicePriceDiscount
P(f"ServicePriceDiscount: no nulo {int(spd.notna().sum()):,} ({pc(spd.notna().mean())}); == 0: {int((spd == 0).sum()):,}; mediana {spd.median():,.0f}.")
mm = agenda[agenda.ServiceMaintenance.notna()]
qq = mm.ScheduleDate.dt.to_period("Q")
V10_2 = mm.groupby(qq).ServicePriceDiscount.agg(items="size", pct_no_nulo=lambda s: 100 * s.notna().mean(), mediana="median")
V10_2["mediana 1° service"] = mm[mm.ServiceMaintenance == 1].groupby(qq).ServicePriceDiscount.median()
V10_2.index = V10_2.index.astype(str)
T("V10.2 ServicePriceDiscount en items de mantenimiento por trimestre (refuta 'informado desde 2025')", V10_2.round(0))
slc = agenda.ServiceLaborCost
P(f"ServiceLaborCost no nulo: {int(slc.notna().sum()):,} ({pc(slc.notna().mean())}); anios: {agenda.ScheduleDate[slc.notna()].dt.year.value_counts().to_dict()}; "
  f"ServiceType: {agenda.ServiceType[slc.notna()].value_counts().to_dict()}; mediana {slc.median():,.0f}.")
P(f"ServiceFordFixedPrice valores: {agenda.ServiceFordFixedPrice.value_counts().to_dict()} (misma escala que ServiceLaborCost, no que ServicePriceDiscount).")
# customer_id cambia: dos denominadores
cu = apv.groupby("vehicle_id").customer_id.nunique()
P(f"Vehiculos con >1 customer_id: {int((cu > 1).sum()):,} = {pc((cu > 1).sum() / len(cu))} de {len(cu):,} vehiculos; "
  f"{pc((cu > 1)[n_appt >= 2].mean())} de los {int((n_appt >= 2).sum()):,} con >=2 turnos; "
  f"{pc((cu > 1)[apv.groupby('vehicle_id').customer_id.count() >= 2].mean())} de los con >=2 customer_id no nulos.")

OUT_MD.write_text(_buf.getvalue(), encoding="utf-8")
print(f"\nTablas escritas en {OUT_MD}")
