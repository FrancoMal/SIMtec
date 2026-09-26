"""Verificación independiente del EDA 06 (canal, dealer, conectividad y experiencia).

Recalcula desde cero, con código propio (sin reutilizar las funciones del script original), las cifras que
sustentan las 10 afirmaciones clave del informe `reports/eda/06_canal_dealer_experiencia.md`, y agrega los
controles que faltaban (vehículos disjuntos entre años, residuos ajustados por mix, historial con ajuste por
intensidad, agosto 2026 sin reservas futuras, etc.).

Genera: reports/eda/06_canal_dealer_experiencia_verificacion_salida.md (todas las tablas citadas en
reports/eda/06_canal_dealer_experiencia_verificacion.md).

Ejecutar desde la carpeta del proyecto:
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/06_canal_dealer_experiencia_verificacion.py
"""
from __future__ import annotations

import warnings

import numpy as np
import pandas as pd
from scipy import stats
from sklearn.linear_model import LogisticRegression

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_agenda

warnings.filterwarnings("ignore")
OUT = config.REPORTS_DIR / "eda" / "06_canal_dealer_experiencia_verificacion_salida.md"
BASE_START, BASE_END = pd.Timestamp("2024-01-01"), pd.Timestamp("2025-05-31")
H15 = pd.DateOffset(months=15)
lines: list[str] = []


def emit(s: str = ""):
    print(s)
    lines.append(s)


def md(df: pd.DataFrame, title: str = "", index: bool = True):
    d = df.reset_index() if index else df
    emit(f"\n**{title}**\n" if title else "")
    emit("| " + " | ".join(str(c) for c in d.columns) + " |")
    emit("|" + "---|" * len(d.columns))
    for row in d.itertuples(index=False):
        cells = []
        for v in row:
            if isinstance(v, (float, np.floating)):
                cells.append("s/d" if np.isnan(v) else f"{v:.3f}".rstrip("0").rstrip("."))
            else:
                cells.append(str(v))
        emit("| " + " | ".join(cells) + " |")


def pc(x) -> float:
    return round(100 * float(x), 1)


def rate(df, col, target="ret", order=None):
    s = df[col].astype(object).where(df[col].notna(), "sin dato")
    g = df.groupby(s)[target].agg(n="size", pct="mean")
    g["pct"] = (100 * g["pct"]).round(1)
    if order:
        g = g.reindex([o for o in order if o in g.index])
    return g


def iv(df, col, target="ret", smooth=0.5):
    s = df[col].astype(object).where(df[col].notna(), "sin dato")
    ct = pd.crosstab(s, df[target]).reindex(columns=[True, False], fill_value=0).astype(float) + smooth
    pr, pch = ct[True] / ct[True].sum(), ct[False] / ct[False].sum()
    return round(float(((pr - pch) * np.log(pr / pch)).sum()), 4)


def logit_or(df, cats: dict[str, str], target="ret", extra_num: list[str] | None = None):
    """OR de una logística sin penalización; cats = {col: ref}. Matriz de diseño propia (get_dummies)."""
    d = df[list(cats) + (extra_num or []) + [target]].dropna().copy()
    parts, names = [], []
    for c, ref in cats.items():
        dm = pd.get_dummies(d[c].astype(str), prefix=c, dtype=float)
        dm = dm.drop(columns=f"{c}_{ref}")
        parts.append(dm)
        names += list(dm.columns)
    if extra_num:
        parts.append(d[extra_num].astype(float))
        names += extra_num
    X = pd.concat(parts, axis=1).values
    y = d[target].astype(int).values
    m = LogisticRegression(penalty=None, max_iter=5000).fit(X, y)
    return pd.Series(np.exp(m.coef_[0]), index=names).round(3), len(d)


# ======================================================================================================
# 0. Base y etiqueta, construidas de forma independiente (merge_asof en vez de shift)
# ======================================================================================================
ag = load_agenda()
ap = appointments(ag)
del ag
ap["gen"] = ap["ShortVehicleModelGroupTreated"].map({"RANGER (P703)": "P703", "RANGER (P375)": "P375"}).fillna("Otro")
ap["my_bin"] = pd.cut(ap["ModelYear"], [-np.inf, 2015, 2018, 2021, 2023, 2024, np.inf],
                      labels=["<=2015", "2016-18", "2019-21", "2022-23", "2024", "2025+"]).astype(object)
ap["cancel_true"] = ap["cancelled"] & ap["IsReschedule"].eq("N")
ap["cancel_resched"] = ap["cancelled"] & ap["IsReschedule"].eq("Y")
ap["digital"] = ap["ScheduleSource"].isin(["FordPass", "WEB", "Mobile"])
ap["resolved"] = ap["StatusARG"].isin(["(60) Concluido", "(70) Cancelado", "(80) No asistio", "(90) Concluido sin OS"])

cm = ap.loc[ap["is_completed_maintenance"] & ap["vehicle_id"].notna(),
            ["vehicle_id", "event_date", "schedule_id", "dealer_id"]].sort_values("event_date")
right = cm[["vehicle_id", "event_date", "dealer_id"]].rename(columns={"event_date": "next_date", "dealer_id": "next_dealer"})
nxt = pd.merge_asof(cm, right, left_on="event_date", right_on="next_date", by="vehicle_id",
                    direction="forward", allow_exact_matches=False)
right30 = right.copy()
cm30 = cm[["vehicle_id", "event_date", "schedule_id"]].copy()
cm30["k"] = cm30["event_date"] + pd.Timedelta(days=30)
cm30 = cm30.sort_values("k")
nxt30 = pd.merge_asof(cm30, right30[["vehicle_id", "next_date"]].rename(columns={"next_date": "next30"}),
                      left_on="k", right_on="next30", by="vehicle_id", direction="forward")
nxt = nxt.merge(nxt30[["schedule_id", "next30"]], on="schedule_id")

in_period = ap["is_completed_maintenance"] & ap["event_date"].between(BASE_START, BASE_END)
n_vnull = int((in_period & ap["vehicle_id"].isna()).sum())
pct_vnull_my = pc(ap.loc[in_period & ap["vehicle_id"].isna(), "ModelYear"].isna().mean())
base = ap[in_period & ap["vehicle_id"].notna()].merge(nxt[["schedule_id", "next_date", "next_dealer", "next30"]], on="schedule_id", how="left")
base["h_end"] = (base["event_date"] + H15).clip(upper=CUTOFF)
base["ret"] = base["next_date"].notna() & (base["next_date"] <= base["h_end"])
base["ret30"] = base["next30"].notna() & (base["next30"] <= base["h_end"])
base["gap"] = (base["next_date"] - base["event_date"]).dt.days
base["year"] = base["event_date"].dt.year
base["maint_bin"] = pd.cut(base["maint_number"], [0, 1, 2, 3, 5, 8, 99], labels=["1", "2", "3", "4-5", "6-8", "9+"]).astype(object)

emit("# Salida de la verificación del EDA 06\n")
emit(f"Script: `scripts/eda/06_canal_dealer_experiencia_verificacion.py`. CUTOFF = {CUTOFF.date()}.\n")
emit("## V1. Etiqueta aproximada y base")
md(pd.DataFrame({"valor": [n_vnull, pct_vnull_my, len(base), base["vehicle_id"].nunique(), pc(base["ret"].mean()),
                            pc(1 - base["ret"].mean()), pc(base["ret30"].mean()),
                            int(((base["event_date"] + H15) > CUTOFF).sum()), int((base["gap"] <= 1).sum()),
                            float(base["gap"].median())]},
                index=["mant. completados en el período con vehicle_id nulo (excluidos)", "% de esos sin ModelYear",
                       "turnos base", "vehículos distintos", "% retorno <=15 meses", "% churn aprox.",
                       "% retorno exigiendo >=30 días", "turnos con horizonte truncado por CUTOFF",
                       "turnos con próximo mant. a <=1 día", "mediana días al próximo mant. (si existe)"]),
   "Resumen de la base (recalculado con merge_asof)")
bym = base.groupby(base["event_date"].dt.to_period("M").astype(str))["ret"].agg(n="size", pct="mean")
bym["pct"] = (100 * bym["pct"]).round(1)
emit(f"Retorno por mes del turno base: mín {bym['pct'].min()} ({bym['pct'].idxmin()}), máx {bym['pct'].max()} ({bym['pct'].idxmax()}).")
# ¿Cuánto del "retorno" a 15 meses se explica por ritmo de uso? Retorno según km/año aproximado del vehículo
# (VehicleCurrentKM del turno base / edad en años desde WarrantyStartDate).
age_y = (base["event_date"] - base["WarrantyStartDate"]).dt.days / 365.25
base["km_anio"] = np.where(age_y > 0.5, base["VehicleCurrentKM"] / age_y, np.nan)
base["km_anio_bin"] = pd.cut(base["km_anio"], [0, 10000, 20000, 30000, 50000, np.inf],
                             labels=["<10k", "10-20k", "20-30k", "30-50k", "50k+"]).astype(object)
md(rate(base, "km_anio_bin", order=["<10k", "10-20k", "20-30k", "30-50k", "50k+", "sin dato"]),
   "Retorno a 15 meses según km/año aproximado (VehicleCurrentKM / edad desde garantía; edad >6 meses)")
emit(f"IV de km_anio_bin sobre la base: {iv(base, 'km_anio_bin')}.")

# ======================================================================================================
# Historial exclusivo (implementación propia) + verificación por fuerza bruta sobre una muestra
# ======================================================================================================
ap = ap.sort_values(["vehicle_id", "event_date", "schedule_id"]).reset_index(drop=True)
vid = ap["vehicle_id"]
for name, flag in {"no_show": ap["no_show"], "cancel_true": ap["cancel_true"], "cancel_resched": ap["cancel_resched"],
                   "recall": ap["completed"] & ap["has_recall"], "repair": ap["completed"] & ap["has_repair"],
                   "diag": ap["completed"] & ap["has_diag"], "return_visit": ap["ScheduleReturn"].eq("Y"),
                   "maint": ap["is_completed_maintenance"], "digital": ap["digital"]}.items():
    f = flag.astype(int)
    ap[f"p_{name}"] = f.groupby(vid).cumsum() - f
ap["p_turnos"] = ap.groupby(vid).cumcount()
ap["prev_date"] = ap.groupby(vid)["event_date"].shift(1)
ap["dsp"] = (ap["event_date"] - ap["prev_date"]).dt.days
mdate = ap["event_date"].where(ap["is_completed_maintenance"])
ap["prev_maint_date"] = mdate.groupby(vid).shift(1).groupby(vid).ffill()
ap["dspm"] = (ap["event_date"] - ap["prev_maint_date"]).dt.days
ap["next_any"] = ap.groupby(vid)["event_date"].shift(-1)
ap["dtn"] = (ap["next_any"] - ap["event_date"]).dt.days
ap["prev_status"] = ap.groupby(vid)["StatusARG"].shift(1)
ap["next_status"] = ap.groupby(vid)["StatusARG"].shift(-1)
hcols = ["p_no_show", "p_cancel_true", "p_cancel_resched", "p_recall", "p_repair", "p_diag", "p_return_visit",
         "p_maint", "p_digital", "p_turnos", "dsp", "dspm"]
base = base.merge(ap[["schedule_id"] + hcols], on="schedule_id", how="left")

emit("\n## V2. Verificación por fuerza bruta del historial (muestra aleatoria de 400 turnos base)")
rng = np.random.default_rng(42)
samp = base.sample(400, random_state=42)
errs = 0
for r in samp.itertuples():
    h = ap[(ap["vehicle_id"] == r.vehicle_id) & ((ap["event_date"] < r.event_date) |
                                                  ((ap["event_date"] == r.event_date) & (ap["schedule_id"] < r.schedule_id)))]
    chk = {"p_turnos": len(h), "p_no_show": int(h["no_show"].sum()), "p_maint": int(h["is_completed_maintenance"].sum()),
           "p_recall": int((h["completed"] & h["has_recall"]).sum()), "p_cancel_true": int(h["cancel_true"].sum())}
    dsp = (r.event_date - h["event_date"].max()).days if len(h) else np.nan
    dspm = (r.event_date - h.loc[h["is_completed_maintenance"], "event_date"].max()).days if h["is_completed_maintenance"].any() else np.nan
    for k, v in chk.items():
        if getattr(r, k) != v:
            errs += 1
    if not ((np.isnan(dsp) and np.isnan(r.dsp)) or dsp == r.dsp):
        errs += 1
    if not ((np.isnan(dspm) and np.isnan(r.dspm)) or dspm == r.dspm):
        errs += 1
emit(f"Discrepancias entre historial vectorizado y fuerza bruta (7 campos x 400 turnos): {errs}.")

# ======================================================================================================
# V2b. Recencia (afirmación 2)
# ======================================================================================================
emit("\n## V2b. Recencia e intensidad (sub-base ene–may 2025)")
hb = base[base["event_date"] >= "2025-01-01"].copy()
emit(f"Sub-base: n={len(hb)}, retorno {pc(hb['ret'].mean())}%.")
REC = [-np.inf, 30, 90, 180, 365, np.inf]
RECL = ["<=30", "31-90", "91-180", "181-365", ">365"]
for d in (hb, base):
    d["rec"] = pd.cut(d["dsp"], REC, labels=RECL).astype(object).where(d["dsp"].notna(), "sin turno previo")
    d["recm"] = pd.cut(d["dspm"], REC, labels=RECL).astype(object).where(d["dspm"].notna(), "sin mant. previo")
    d["b_maint"] = d["p_maint"].clip(upper=3).map({0: "0", 1: "1", 2: "2", 3: "3+"})
    d["b_turnos"] = pd.cut(d["p_turnos"], [-1, 0, 1, 2, 4, np.inf], labels=["0", "1", "2", "3-4", "5+"]).astype(object)
    for c in ["no_show", "cancel_true", "cancel_resched", "recall", "repair", "diag", "return_visit"]:
        d[f"b_{c}"] = d[f"p_{c}"].clip(upper=2).map({0: "0", 1: "1", 2: "2+"})
    d["primer"] = np.where(d["maint_number"] == 1, "1er service", "2° o posterior")
md(rate(hb, "rec", order=RECL + ["sin turno previo"]), "Días desde el turno previo (cualquier status)")
md(rate(hb, "recm", order=RECL + ["sin mant. previo"]), "Días desde el mantenimiento completado previo")
md(rate(hb, "b_maint", order=["0", "1", "2", "3+"]), "Mantenimientos previos")
md(rate(hb, "b_turnos", order=["0", "1", "2", "3-4", "5+"]), "Turnos previos")
emit(f"IV recencia (turno previo): {iv(hb, 'rec')}; IV recencia (mant. previo): {iv(hb, 'recm')}; "
     f"IV mant. previos: {iv(hb, 'b_maint')}; IV turnos previos: {iv(hb, 'b_turnos')}.")
t = hb.groupby(["primer", "rec"])["ret"].agg(n="size", pct="mean")
t["pct"] = (100 * t["pct"]).round(1)
md(t, "Recencia × primer service (sub-base 2025)")
# Salvedad: el bin '>365' solo es alcanzable para turnos base de 2025 con >365 días de lookback; ¿en qué meses cae?
emit("Turnos '>365' por mes del turno base: " + hb.loc[hb["rec"] == ">365", "event_date"].dt.to_period("M").astype(str).value_counts().sort_index().to_dict().__str__())
# Recencia SOLO de turnos concluidos (excluye cancelados/no-show como 'contacto')
cd = ap["event_date"].where(ap["completed"])
ap["prev_done_date"] = cd.groupby(vid).shift(1).groupby(vid).ffill()
ap["dspd"] = (ap["event_date"] - ap["prev_done_date"]).dt.days
hb = hb.merge(ap[["schedule_id", "dspd"]], on="schedule_id", how="left")
hb["recd"] = pd.cut(hb["dspd"], REC, labels=RECL).astype(object).where(hb["dspd"].notna(), "sin turno previo")
md(rate(hb, "recd", order=RECL + ["sin turno previo"]), "Días desde el último turno CONCLUIDO (sensibilidad: excluye cancelados/no-show)")
emit(f"IV recencia (último concluido): {iv(hb, 'recd')}.")

# ======================================================================================================
# V3. No-shows y cancelaciones previas (afirmación 3), con ajuste por intensidad
# ======================================================================================================
emit("\n## V3. No-shows, cancelaciones y 'vehículo con problemas'")
for c, lab in [("b_no_show", "No-shows previos"), ("b_cancel_true", "Cancelaciones reales previas"),
               ("b_cancel_resched", "Reprogramaciones previas"), ("b_recall", "Recalls previos"),
               ("b_repair", "Reparaciones previas"), ("b_diag", "Diagnósticos previos"), ("b_return_visit", "Re-visitas previas")]:
    t = rate(hb, c, order=["0", "1", "2+"])
    emit(f"{lab}: " + " / ".join(f"{i}: {v.pct}% (n {v.n})" for i, v in t.iterrows()) + f" — IV {iv(hb, c)}")
# Ajuste: los no-shows previos implican haber tenido turnos previos (intensidad). Comparar dentro de n turnos previos.
hb2 = hb[hb["p_turnos"] >= 1].copy()
hb2["ns_any"] = np.where(hb2["p_no_show"] > 0, "con no-show previo", "sin no-show previo")
t = hb2.groupby(["b_turnos", "ns_any"])["ret"].agg(n="size", pct="mean")
t["pct"] = (100 * t["pct"]).round(1)
md(t, "Retorno según no-show previo DENTRO de cada nivel de turnos previos (sub-base 2025, >=1 turno previo)")
hb2["ns_rate"] = hb2["p_no_show"] / hb2["p_turnos"]
hb2["ns_rate_bin"] = pd.cut(hb2["ns_rate"], [-0.01, 0, 0.2, 0.5, 1.0], labels=["0%", "1-20%", "21-50%", ">50%"]).astype(object)
md(rate(hb2, "ns_rate_bin", order=["0%", "1-20%", "21-50%", ">50%"]), "Retorno según % de no-shows entre los turnos previos")
ors, n = logit_or(hb, {"b_no_show": "0", "b_cancel_true": "0", "b_turnos": "0", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
md(ors.to_frame("OR"), f"OR ajustados (n={n}): no-shows y cancelaciones reales previas controlando turnos previos, generación, año modelo y n° de service")
ors, n = logit_or(hb, {"b_recall": "0", "b_repair": "0", "b_turnos": "0", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
md(ors.to_frame("OR"), f"OR ajustados (n={n}): recalls y reparaciones previas controlando turnos previos, generación, año modelo y n° de service")
# Modelo conjunto de TODO el historial (lo que va a ver un modelo multivariante)
hist_cats = {"b_no_show": "0", "b_cancel_true": "0", "b_cancel_resched": "0", "b_recall": "0", "b_repair": "0", "b_diag": "0",
             "b_return_visit": "0", "b_turnos": "0", "rec": "91-180", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"}
ors, n = logit_or(hb, hist_cats)
md(ors[~ors.index.str.startswith(("gen", "my_bin", "maint_bin"))].to_frame("OR"),
   f"Modelo conjunto del historial (n={n}): OR de cada feature controlando por todas las demás + generación, año modelo y n° de service")
# Sensibilidad sin controlar por turnos previos ni recencia (solo edad del vehículo)
ors, n = logit_or(hb, {k: v for k, v in hist_cats.items() if k not in ("b_turnos", "rec")})
md(ors[~ors.index.str.startswith(("gen", "my_bin", "maint_bin"))].to_frame("OR"),
   f"Mismo modelo SIN turnos previos ni recencia (n={n}): muestra cuánto del efecto crudo es intensidad de contacto")
# Los no-shows previos, ¿son el turno cancelado/no asistido del MISMO ciclo? Días desde el último no-show al turno base.
ns_date = ap["event_date"].where(ap["no_show"])
ap["last_ns_date"] = ns_date.groupby(vid).shift(1).groupby(vid).ffill()
hb = hb.merge(ap[["schedule_id", "last_ns_date"]], on="schedule_id", how="left")
d_ns = (hb["event_date"] - hb["last_ns_date"]).dt.days
emit(f"Entre los turnos base con no-show previo (n={int(d_ns.notna().sum())}), días desde el último no-show: mediana {d_ns.median():.0f}, "
     f"p25 {d_ns.quantile(.25):.0f}, p75 {d_ns.quantile(.75):.0f}; % a <=30 días: {pc((d_ns <= 30).sum() / d_ns.notna().sum())}.")

# ======================================================================================================
# V4. FordPass (afirmación 4)
# ======================================================================================================
emit("\n## V4. Canal de agendado")
md(rate(base, "ScheduleSource", order=["Dealer", "FordPass", "WEB", "Mobile", "CAF"]), "Retorno por fuente del turno base")
t = base[base["ScheduleSource"].isin(["Dealer", "FordPass"])].groupby(["gen", "my_bin", "ScheduleSource"])["ret"].agg(n="size", pct="mean")
t = t[t["n"] >= 200]
t["pct"] = (100 * t["pct"]).round(1)
w = t["pct"].unstack("ScheduleSource")
w["dif_pp"] = (w["FordPass"] - w["Dealer"]).round(1)
w["n_FordPass"] = t["n"].unstack("ScheduleSource")["FordPass"]
md(w.dropna(subset=["dif_pp"]), "FordPass − Dealer dentro de generación × año modelo (celdas n>=200)")
ww = w.dropna(subset=["dif_pp"])
emit(f"Diferencia FordPass−Dealer ponderada por n FordPass del estrato: {np.average(ww['dif_pp'], weights=ww['n_FordPass']):.1f} pp "
     f"(cruda: {rate(base, 'ScheduleSource').loc['FordPass', 'pct'] - rate(base, 'ScheduleSource').loc['Dealer', 'pct']:.1f} pp).")
b2 = base[base["gen"].isin(["P703", "P375"]) & base["ScheduleSource"].isin(["Dealer", "FordPass", "WEB", "Mobile"]) & base["my_bin"].notna()]
ors, n = logit_or(b2, {"ScheduleSource": "Dealer", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
md(ors[ors.index.str.startswith("ScheduleSource")].to_frame("OR"), f"OR fuente (n={n}) controlando gen, año modelo, n° de service — réplica")
ors, n = logit_or(b2, {"ScheduleSource": "Dealer", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1", "dealer_id": b2["dealer_id"].mode()[0]})
md(ors[ors.index.str.startswith("ScheduleSource")].to_frame("OR"), f"OR fuente (n={n}) agregando efecto fijo por DEALER")
hb3 = hb[hb["gen"].isin(["P703", "P375"]) & hb["ScheduleSource"].isin(["Dealer", "FordPass", "WEB", "Mobile"]) & hb["my_bin"].notna()]
ors, n = logit_or(hb3, {"ScheduleSource": "Dealer", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1", "b_turnos": "0", "rec": "91-180"})
md(ors[ors.index.str.startswith("ScheduleSource")].to_frame("OR"), f"OR fuente en la sub-base 2025 (n={n}) agregando turnos previos y recencia")
ors, n = logit_or(hb3, {"ScheduleSource": "Dealer", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1", "b_turnos": "0", "rec": "91-180",
                        "dealer_id": hb3["dealer_id"].mode()[0]})
md(ors[ors.index.str.startswith("ScheduleSource")].to_frame("OR"), f"OR fuente en la sub-base 2025 (n={n}) con turnos previos, recencia y efecto fijo por dealer")
emit(f"IV ScheduleSource (base): {iv(base, 'ScheduleSource')}.")
obs = ap[ap["ScheduleDate"] <= CUTOFF]
fp = obs.groupby(obs["ScheduleDate"].dt.to_period("M").astype(str))["ScheduleSource"].apply(lambda s: pc(s.eq("FordPass").mean()))
emit(f"% FordPass ene-24: {fp.iloc[0]}; ago-26: {fp.iloc[-1]}.")
comp = pd.crosstab(base["gen"], base["ScheduleSource"], normalize="index").mul(100).round(1)
emit(f"FordPass como % de turnos base: P703 {comp.loc['P703', 'FordPass']}, P375 {comp.loc['P375', 'FordPass']}.")
res = obs[obs["resolved"]]
st = res.groupby("ScheduleSource").agg(n=("schedule_id", "size"), no_show=("no_show", "mean"), reprog=("cancel_resched", "mean"), cancel_real=("cancel_true", "mean"))
for c in ["no_show", "reprog", "cancel_real"]:
    st[c] = (100 * st[c]).round(1)
md(st, "No-show / reprogramación / cancelación real por fuente (turnos resueltos)")

# ======================================================================================================
# V5. Dealer (afirmación 5)
# ======================================================================================================
emit("\n## V5. Dealer")
dy = base.groupby(["dealer_id", "year"])["ret"].agg(["size", "mean"]).unstack("year")
dy.columns = [f"{a}_{b}" for a, b in dy.columns]
dy = dy[(dy["size_2024"] >= 100) & (dy["size_2025"] >= 100)]
emit(f"Dealers con >=100 turnos base en 2024 y 2025: {len(dy)}. Pearson {stats.pearsonr(dy['mean_2024'], dy['mean_2025'])[0]:.3f}, "
     f"Spearman {stats.spearmanr(dy['mean_2024'], dy['mean_2025'])[0]:.3f}.")
# Solapamiento de vehículos entre 2024 y 2025
v24 = set(base.loc[base["year"] == 2024, "vehicle_id"])
b25 = base[base["year"] == 2025]
emit(f"Vehículos de la base 2025 que también están en la base 2024: {pc(b25['vehicle_id'].isin(v24).mean())}%.")
b25d = b25[~b25["vehicle_id"].isin(v24)]
dyd = base[base["year"] == 2024].groupby("dealer_id")["ret"].agg(n24="size", r24="mean").join(
    b25d.groupby("dealer_id")["ret"].agg(n25d="size", r25d="mean"))
dyd = dyd[(dyd["n24"] >= 100) & (dyd["n25d"] >= 50)]
emit(f"Vehículos DISJUNTOS (2025 sin turno base en 2024): {len(dyd)} dealers (n24>=100, n25>=50); Pearson "
     f"{stats.pearsonr(dyd['r24'], dyd['r25d'])[0]:.3f}, Spearman {stats.spearmanr(dyd['r24'], dyd['r25d'])[0]:.3f}.")
# Split-half por vehículo dentro de 2024
b24 = base[base["year"] == 2024].copy()
vh = pd.Series(rng.random(b24["vehicle_id"].nunique()) < 0.5, index=b24["vehicle_id"].unique())
b24["half"] = b24["vehicle_id"].map(vh)
sh = b24.groupby(["dealer_id", "half"])["ret"].agg(["size", "mean"]).unstack("half")
sh = sh[(sh[("size", False)] >= 50) & (sh[("size", True)] >= 50)]
emit(f"Split-half por vehículo dentro de 2024 ({len(sh)} dealers con >=50 en cada mitad): Pearson "
     f"{stats.pearsonr(sh[('mean', False)], sh[('mean', True)])[0]:.3f}.")
# Dispersión vs binomial
dd = base.groupby("dealer_id")["ret"].agg(n="size", r="mean")
dd = dd[dd["n"] >= 100]
p = base["ret"].mean()
sd_obs, sd_bin = dd["r"].std(), np.sqrt((p * (1 - p) / dd["n"]).mean())
emit(f"Dealers n_base>=100: {len(dd)}. SD observado {pc(sd_obs)} pp; SD binomial esperado {pc(sd_bin)} pp; ratio {sd_obs / sd_bin:.2f}. "
     f"p10/p50/p90 del retorno: {pc(dd['r'].quantile(.1))}/{pc(dd['r'].quantile(.5))}/{pc(dd['r'].quantile(.9))}.")
# Ajuste por mix: esperado según gen × my_bin × maint_bin
base["exp_mix"] = base.groupby(["gen", "my_bin", "maint_bin"], dropna=False)["ret"].transform("mean")
adj = base.groupby("dealer_id").agg(n=("ret", "size"), obs=("ret", "mean"), esp=("exp_mix", "mean"))
adj = adj[adj["n"] >= 100]
adj["resid_pp"] = 100 * (adj["obs"] - adj["esp"])
emit(f"Residuo obs − esperado por mix (gen × año modelo × n° service), dealers n>=100: p10 {adj['resid_pp'].quantile(.1):.1f}, "
     f"p90 {adj['resid_pp'].quantile(.9):.1f}, SD {adj['resid_pp'].std():.1f} pp (vs SD crudo {pc(sd_obs)} pp).")
share = base.groupby("dealer_id")["gen"].apply(lambda s: s.eq("P703").mean())
emit(f"Pearson share P703 vs retorno (dealers n>=100): {stats.pearsonr(share.loc[dd.index], dd['r'])[0]:.3f}.")
# Estabilidad de los RESIDUOS entre años (el test que no depende del mix)
for yr in (2024, 2025):
    b = base[base["year"] == yr].copy()
    b["exp_y"] = b.groupby(["gen", "my_bin", "maint_bin"], dropna=False)["ret"].transform("mean")
    a = b.groupby("dealer_id").agg(n=("ret", "size"), obs=("ret", "mean"), esp=("exp_y", "mean"))
    a[f"res_{yr}"] = 100 * (a["obs"] - a["esp"])
    adj = adj.join(a[[f"res_{yr}"]].rename(columns={}), how="left") if yr == 2024 else adj.join(a[[f"res_{yr}"]], how="left")
ra = adj.dropna(subset=["res_2024", "res_2025"]).loc[dy.index.intersection(adj.index)]
emit(f"Residuos ajustados por mix, 2024 vs 2025 ({len(ra)} dealers): Pearson {stats.pearsonr(ra['res_2024'], ra['res_2025'])[0]:.3f}, "
     f"Spearman {stats.spearmanr(ra['res_2024'], ra['res_2025'])[0]:.3f}.")
# Target encoding fuera de tiempo: quintiles por TURNO (réplica) y por DEALER
te = base[base["year"] == 2024].groupby("dealer_id")["ret"].agg(n24="size", r24="mean")
te = te[te["n24"] >= 50]
b25 = b25.merge(te, left_on="dealer_id", right_index=True, how="left")
b25["q_turno"] = pd.qcut(b25["r24"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"]).astype(object)
b25["q_dealer"] = b25["dealer_id"].map(pd.qcut(te["r24"], 5, labels=["Q1", "Q2", "Q3", "Q4", "Q5"]).astype(object))
md(rate(b25, "q_turno", order=["Q1", "Q2", "Q3", "Q4", "Q5", "sin dato"]), "TE 2024 → 2025, quintiles calculados sobre TURNOS de 2025 (réplica del original)")
md(rate(b25, "q_dealer", order=["Q1", "Q2", "Q3", "Q4", "Q5", "sin dato"]), "TE 2024 → 2025, quintiles calculados sobre DEALERS (cada quintil = ~17 dealers)")
emit(f"IV TE por turno: {iv(b25[b25['q_turno'].notna()], 'q_turno')}; IV TE por dealer: {iv(b25[b25['q_dealer'].notna()], 'q_dealer')}.")
# ¿El TE sobrevive al ajuste por mix en 2025? Retorno 2025 obs − esperado por mix, por quintil
b25["exp25"] = b25.groupby(["gen", "my_bin", "maint_bin"], dropna=False)["ret"].transform("mean")
t = b25.dropna(subset=["q_turno"]).groupby("q_turno").agg(n=("ret", "size"), obs=("ret", "mean"), esp=("exp25", "mean"))
t["obs"], t["esp"] = (100 * t["obs"]).round(1), (100 * t["esp"]).round(1)
t["resid_pp"] = (t["obs"] - t["esp"]).round(1)
md(t, "Quintil TE 2024 (por turno) en 2025: observado vs esperado por mix del propio quintil")
ors, n = logit_or(b25.dropna(subset=["q_turno"]), {"q_turno": "Q3", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
md(ors[ors.index.str.startswith("q_turno")].to_frame("OR"), f"OR del quintil TE 2024 en 2025 controlando gen, año modelo y n° de service (n={n}, ref Q3)")
# Mismo dealer
r = base[base["ret"]]
emit(f"Retornos: {len(r)} (= suma de ret, sin duplicar por merge); próximo mantenimiento en el mismo dealer: {pc((r['next_dealer'] == r['dealer_id']).mean())}%.")
# Concentración
vol = ap[ap["resolved"] & (ap["ScheduleDate"] <= CUTOFF)].groupby("dealer_id").size().sort_values(ascending=False)
cum = vol.cumsum() / vol.sum()
v = np.sort(vol.values)
gini = (2 * np.sum(np.arange(1, len(v) + 1) * v) / (len(v) * v.sum())) - (len(v) + 1) / len(v)
emit(f"Dealers: {len(vol)}; top-10 = {pc(cum.iloc[9])}%; top-20 = {pc(cum.iloc[19])}%; dealer #1 = {pc(vol.iloc[0] / vol.sum())}% ({vol.iloc[0]}); "
     f"Gini (fórmula estándar) {gini:.3f}.")
dy["cambio_pp"] = (100 * (dy["mean_2025"] - dy["mean_2024"])).round(1)
md(dy.nsmallest(3, "cambio_pp")[["size_2024", "size_2025", "cambio_pp"]], "Mayores caídas 2024→2025 (dealers n>=100 ambos años)")

# ======================================================================================================
# V6. Conectividad (afirmación 6)
# ======================================================================================================
emit("\n## V6. ConnectedStatusARG")
nun = ap.groupby("vehicle_id")["ConnectedStatusARG"].nunique()
emit(f"Vehículos con >1 valor: {int((nun > 1).sum())} de {len(nun)}.")
CO = ["Conectado", "No Conectado", "No tiene Conectividad", "Sin Información de Conectividad"]
last_any = ap.groupby("vehicle_id")["event_date"].max()
base["last_any"] = base["vehicle_id"].map(last_any)
base["any_later"] = base["last_any"] > base["event_date"]
last_le = ap[ap["ScheduleDate"] <= CUTOFF].groupby("vehicle_id")["event_date"].max()
base["any_later_le_cutoff"] = base["vehicle_id"].map(last_le) > base["event_date"]
t = base.groupby("ConnectedStatusARG").agg(n=("ret", "size"), retorno=("ret", "mean"), turno_posterior=("any_later", "mean"),
                                           turno_posterior_sin_reservas_futuras=("any_later_le_cutoff", "mean"))
for c in t.columns[1:]:
    t[c] = (100 * t[c]).round(1)
md(t.reindex(CO), "Retorno y % con algún turno posterior por conectividad")
t = base.groupby(["ConnectedStatusARG", "year"])["any_later"].agg(n="size", pct="mean").unstack("year")
md((t["pct"] * 100).round(1).join(t["n"], lsuffix=" %", rsuffix=" n").reindex(CO), "% con algún turno posterior por conectividad × año del turno base")
t = base[(base["gen"] == "P703") & (base["my_bin"] == "2024")].groupby("ConnectedStatusARG")["ret"].agg(n="size", pct="mean")
t["pct"] = (100 * t["pct"]).round(1)
md(t.reindex(CO), "P703 año modelo 2024: retorno por conectividad")
ors, n = logit_or(base[(base["gen"] == "P703") & base["my_bin"].notna()], {"ConnectedStatusARG": "Conectado", "my_bin": "2024"})
md(ors[ors.index.str.startswith("Connected")].to_frame("OR"), f"OR dentro de P703 (n={n}), ref Conectado, control año modelo")
emit(f"'No tiene Conectividad' en P375: n={int(((base['gen'] == 'P375') & (base['ConnectedStatusARG'] == 'No tiene Conectividad')).sum())}, "
     f"retorno {pc(base.loc[(base['gen'] == 'P375') & (base['ConnectedStatusARG'] == 'No tiene Conectividad'), 'ret'].mean())}%.")
emit(f"IV ConnectedStatusARG: {iv(base, 'ConnectedStatusARG')}; IV año modelo (my_bin): {iv(base, 'my_bin')}; IV gen: {iv(base, 'gen')}.")
# Test adicional de leakage: la participación de 'Sin Información' por mes del turno base (si marca vehículos que se
# fueron, debería ser mayor en los turnos base más antiguos, que tuvieron más tiempo para irse).
si = base.groupby(base["event_date"].dt.to_period("Q").astype(str))["ConnectedStatusARG"].apply(lambda s: pc(s.eq("Sin Información de Conectividad").mean()))
md(si.to_frame("% Sin Información"), "Participación de 'Sin Información' por trimestre del turno base")
# Último evento de los vehículos 'Sin Información' vs resto
le = base.groupby("ConnectedStatusARG")["last_any"].agg(lambda s: s.dt.to_period("Q").astype(str).value_counts(normalize=True).mul(100).round(1).sort_index().to_dict())
for k in CO:
    emit(f"- {k}: distribución del ÚLTIMO evento del vehículo por trimestre: {le[k]}")
# Cambio de customer_id como proxy de transferencia
ncust = ap.groupby("vehicle_id")["customer_id"].nunique()
base["n_cust"] = base["vehicle_id"].map(ncust)
t = base.groupby("ConnectedStatusARG")["n_cust"].apply(lambda s: pc((s > 1).mean()))
md(t.to_frame("% vehículos con >1 customer_id en la agenda").reindex(CO), "Proxy de transferencia por conectividad")

# ======================================================================================================
# V7. Encuesta (afirmación 7)
# ======================================================================================================
emit("\n## V7. SurveyStarRating")
sv = ap[ap["SurveyResponseDate"].notna()]
lag = (sv["SurveyResponseDate"] - sv["ScheduleDate"]).dt.days
lag_ci = (sv["SurveyResponseDate"] - sv["EffectiveCheckinDate"]).dt.days
emit(f"Turnos con encuesta: {len(sv)} ({pc(len(sv) / len(ap))}% de {len(ap)}). % antes de ScheduleDate: {pc((lag < 0).mean())}; "
     f"mismo día: {pc((lag == 0).mean())}; después: {pc((lag > 0).mean())}. p5/mediana/p95: {lag.quantile(.05):.0f}/{lag.median():.0f}/{lag.quantile(.95):.0f}.")
lc = lag_ci.dropna()
emit(f"Respecto del check-in (cuando existe, n={len(lc)}): % antes {pc((lc < 0).mean())}, % mismo día {pc((lc == 0).mean())}, % después {pc((lc > 0).mean())}.")
emit(f"5 estrellas: {pc(sv['SurveyStarRating'].eq(5).mean())}%.")
rr = ap[ap["ScheduleDate"] <= CUTOFF].groupby("ScheduleSource")["SurveyStarRating"].agg(n="size", pct=lambda s: pc(s.notna().mean()))
md(rr, "Tasa de respuesta por fuente")
base["sg"] = pd.cut(base["SurveyStarRating"], [0, 2, 3, 4, 5], labels=["1-2", "3", "4", "5"]).astype(object)
base["sg"] = base["sg"].where(base["sg"].notna(), "sin respuesta")
md(rate(base, "sg", order=["1-2", "3", "4", "5", "sin respuesta"]), "Retorno por rating")
dig = base[base["digital"] & base["gen"].isin(["P375", "P703"])].copy()
dig["resp"] = np.where(dig["SurveyStarRating"].notna(), "respondió", "no respondió")
t = dig.groupby(["gen", "resp"])["ret"].agg(n="size", pct="mean")
t["pct"] = (100 * t["pct"]).round(1)
md(t, "Solo canales digitales: respondió vs no, por generación")
emit(f"IV survey_grp: {iv(base, 'sg')}.")

# ======================================================================================================
# V8. IsReschedule / ScheduleReturn (afirmación 8)
# ======================================================================================================
emit("\n## V8. Semántica de IsReschedule y ScheduleReturn")
canc = ap[ap["cancelled"] & ap["vehicle_id"].notna()]
emit(f"Cancelados: {int(ap['cancelled'].sum())}; con IsReschedule=Y: {int(ap['cancel_resched'].sum())} ({pc(ap['cancel_resched'].sum() / ap['cancelled'].sum())}%).")
# Turno más cercano en CUALQUIER dirección (el reemplazo puede ser anterior en fecha al cancelado)
ap["dfp"] = ap["dsp"]
rows = []
for lab, m in [("Cancelado IsReschedule=Y", canc["IsReschedule"].eq("Y")), ("Cancelado IsReschedule=N", canc["IsReschedule"].eq("N"))]:
    x = canc[m]
    near = pd.concat([x["dtn"], x["dsp"]], axis=1).min(axis=1)
    rows.append({"grupo": lab, "n": len(x), "% turno siguiente <=30d": pc((x["dtn"] <= 30).mean()), "mediana días al siguiente": x["dtn"].median(),
                 "% turno (anterior o siguiente) a <=30d": pc((near <= 30).mean()), "% sin ningún otro turno": pc((x["dtn"].isna() & x["dsp"].isna()).mean()),
                 "% turno siguiente concluido": pc(x["next_status"].eq("(60) Concluido").mean())})
md(pd.DataFrame(rows).set_index("grupo"), "Cancelados según IsReschedule (vehículo identificado)")
cy = ap[ap["completed"] & ap["IsReschedule"].eq("Y")]
emit(f"Concluidos con IsReschedule=Y: {len(cy)}; % con turno previo cancelado: {pc(cy['prev_status'].eq('(70) Cancelado').mean())}; mediana días desde previo: {cy['dsp'].median():.0f}.")
rows = []
for v in ["Y", "N"]:
    x = ap[ap["ScheduleReturn"].eq(v)]
    rows.append({"ScheduleReturn": v, "n": len(x), "mediana días desde previo": x["dsp"].median(), "p90": x["dsp"].quantile(.9),
                 "% previo concluido": pc(x["prev_status"].eq("(60) Concluido").mean()), "% mant.": pc(x["has_maint"].mean()),
                 "% diag": pc(x["has_diag"].mean()), "% repar.": pc(x["has_repair"].mean()), "% sin turno previo": pc(x["dsp"].isna().mean())})
md(pd.DataFrame(rows).set_index("ScheduleReturn"), "ScheduleReturn (toda la agenda)")

# ======================================================================================================
# V9. Conveniencia (afirmación 9)
# ======================================================================================================
emit("\n## V9. Conveniencia y atributos del turno base")
base["days_bin"] = pd.cut(base["DaysInDealer"], [-np.inf, -1, 0, 1, 3, 7, 14, 30, np.inf], labels=["<0", "0", "1", "2-3", "4-7", "8-14", "15-30", "31+"]).astype(object)
for c, lab in [("has_pud", "PUD"), ("has_mobile", "Móvil"), ("CustomerWaiting", "Esperó"), ("NeededTowing", "Remolque"), ("has_fixed_price", "Precio fijo"),
               ("has_diag", "Diagnóstico"), ("has_recall", "Recall"), ("DealerStateOrZone", "Zona"), ("days_bin", "DaysInDealer")]:
    t = rate(base, c)
    emit(f"{lab}: " + " / ".join(f"{i}: {v.pct}% (n {v.n})" for i, v in t.iterrows()) + f" — IV {iv(base, c)}")
t = base.groupby(["gen", "has_diag"])["ret"].agg(n="size", pct="mean")
t["pct"] = (100 * t["pct"]).round(1)
md(t, "Diagnóstico en el turno base, dentro de cada generación")
ors, n = logit_or(base[base["my_bin"].notna()], {"has_diag": "False", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
emit(f"OR has_diag ajustado por gen/año modelo/n° service: {ors['has_diag_True']} (n={n}).")
ors, n = logit_or(base[base["my_bin"].notna()], {"days_bin": "0", "gen": "P375", "my_bin": "2022-23", "maint_bin": "1"})
md(ors[ors.index.str.startswith("days_bin")].to_frame("OR"), f"OR DaysInDealer (ref 0 días) ajustado por gen/año modelo/n° service (n={n})")
miss = base.groupby("ScheduleSource")[["NeededTowing", "ScheduleReturn"]].agg(lambda s: pc(s.isna().mean()))
md(miss, "% nulo de NeededTowing y ScheduleReturn por fuente (base)")

# ======================================================================================================
# V10. Tendencia (afirmación 10) — con y sin reservas futuras de agosto 2026
# ======================================================================================================
emit("\n## V10. Estacionalidad y tendencia")
ap["ym"] = ap["ScheduleDate"].dt.to_period("M").astype(str)
w_all = ap[(ap["ScheduleDate"] >= "2024-01-01") & (ap["ScheduleDate"] < "2026-09-01")]
w_cut = w_all[w_all["ScheduleDate"] <= CUTOFF]
for lab, w in [("ScheduleDate < 2026-09-01 (como el script original)", w_all), ("ScheduleDate <= CUTOFF (25/8/2026)", w_cut)]:
    a = w[w["ym"] == "2026-08"]
    r = a[a["resolved"]]
    emit(f"Agosto 2026, {lab}: turnos {len(a)}; (30) Agendado {int(a['StatusARG'].eq('(30) Agendado').sum())}; (40) En progreso "
         f"{int(a['StatusARG'].eq('(40) En progreso').sum())}; (70) Cancelado {int(a['cancelled'].sum())}; resueltos {len(r)}; "
         f"reprogramación {pc(r['cancel_resched'].mean())}%; cancel. real {pc(r['cancel_true'].mean())}%; no-show {pc(r['no_show'].mean())}%; concluido {pc(r['completed'].mean())}%.")
m = w_cut[w_cut["resolved"]].groupby("ym").agg(n=("schedule_id", "size"), no_show=("no_show", "mean"), cancel_real=("cancel_true", "mean"), reprog=("cancel_resched", "mean"), concl=("completed", "mean"))
for c in m.columns[1:]:
    m[c] = (100 * m[c]).round(1)
emit(f"Turnos totales ene-24: {int((w_cut['ym'] == '2024-01').sum())}; mar-26: {int((w_cut['ym'] == '2026-03').sum())}; jul-26: {int((w_cut['ym'] == '2026-07').sum())}.")
emit(f"Mant. completados ene-24: {int(w_cut[w_cut['is_completed_maintenance'] & (w_cut['ym'] == '2024-01')].shape[0])}; ene-26: {int(w_cut[w_cut['is_completed_maintenance'] & (w_cut['ym'] == '2026-01')].shape[0])}.")
emit(f"No-show: ene-24 {m.loc['2024-01', 'no_show']} → jul-26 {m.loc['2026-07', 'no_show']} → ago-26 {m.loc['2026-08', 'no_show']}. "
     f"Reprogramación: ene-24 {m.loc['2024-01', 'reprog']} → jul-26 {m.loc['2026-07', 'reprog']} → ago-26 {m.loc['2026-08', 'reprog']}. "
     f"Cancelación real: mín {m['cancel_real'].min()} ({m['cancel_real'].idxmin()}), máx {m['cancel_real'].max()} ({m['cancel_real'].idxmax()}).")
ci = w_cut[w_cut["completed"]].groupby("ym")["EffectiveCheckinDate"].apply(lambda s: pc(s.isna().mean()))
emit(f"Check-in nulo entre concluidos: ene-24 {ci.loc['2024-01']}, oct-24 {ci.loc['2024-10']}, nov-24 {ci.loc['2024-11']}, dic-24 {ci.loc['2024-12']}, "
     f"2025 rango {ci.loc['2025-01':'2025-12'].min()}–{ci.loc['2025-01':'2025-12'].max()}, 2026 rango {ci.loc['2026-01':'2026-08'].min()}–{ci.loc['2026-01':'2026-08'].max()}.")
yr = w_cut[w_cut["resolved"]].groupby(w_cut["ScheduleDate"].dt.year)["completed"].mean().mul(100).round(1)
emit(f"Concluido por año: {yr.to_dict()}.")
fut = ap[ap["ScheduleDate"] > CUTOFF]
md(pd.crosstab(fut["ym"], fut["StatusARG"]), "Turnos con ScheduleDate > CUTOFF")
bym2 = base.groupby(base["event_date"].dt.month)["ret"].mean().mul(100).round(1)
emit(f"Retorno por mes calendario: mín {bym2.min()} máx {bym2.max()}.")

OUT.write_text("\n".join(lines), encoding="utf-8")
print(f"\nOK: {OUT}")
