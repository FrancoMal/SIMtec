"""EDA 01 - VERIFICACIÓN independiente de las afirmaciones de reports/eda/01_taxonomia_target.md.

Recalcula, con código propio (no reutiliza las tablas del script original), las cifras clave de la taxonomía
de eventos y de la definición del evento objetivo, y agrega tests que el informe original no hizo:
- (90)+mantenimiento: ¿el siguiente (60)+mant del vehículo trae el mismo número (no se hizo) o n+1 (se hizo)?
- Edad al 1° service P703 controlando la censura por cohorte de WarrantyStartDate.
- Cancelaciones con IsReschedule=Y reprogramadas a una fecha ANTERIOR (quedan fuera de la ventana [0, N]).
- 'Oil and filter change': ¿sustituye a un service del plan en vehículos que antes hacían mantenimiento?
- KM / VehicleCurrentKM constantes por vehículo con tratamiento explícito de nulos.

Salida:
- tablas  -> reports/eda/01_taxonomia_target_verificacion_tablas.md + stdout
- figuras -> reports/figures/eda/01_taxonomia_target_verif_*.png

Ejecutar desde la carpeta del proyecto:
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/01_taxonomia_target_verificacion.py
"""
from __future__ import annotations

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_agenda, load_sales

pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)

FIG_DIR = config.FIGURES_DIR / "eda"
FIG_DIR.mkdir(parents=True, exist_ok=True)
TABLES_MD = config.REPORTS_DIR / "eda" / "01_taxonomia_target_verificacion_tablas.md"
PREFIX = "01_taxonomia_target_verif_"

S60, S90, S80, S70, S30, S40 = (
    "(60) Concluido", "(90) Concluido sin OS", "(80) No asistio", "(70) Cancelado", "(30) Agendado", "(40) En progreso",
)
_sections: list[str] = []


def emit(title: str, obj, note: str | None = None) -> None:
    print(f"\n### {title}")
    if isinstance(obj, pd.Series):
        obj = obj.to_frame()
    body = obj.to_markdown() if isinstance(obj, pd.DataFrame) else str(obj)
    print(body)
    if note:
        print(note)
    _sections.append(f"### {title}\n\n{body}\n" + (f"\n{note}\n" if note else ""))


def savefig(fig, name: str) -> None:
    path = FIG_DIR / f"{PREFIX}{name}.png"
    fig.tight_layout()
    fig.savefig(path, dpi=130)
    plt.close(fig)
    print(f"[fig] {path}")


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


# ---------------------------------------------------------------------------------------------
# 0. Carga y colapso PROPIO a nivel turno (independiente de appointments())
# ---------------------------------------------------------------------------------------------
a = load_agenda().drop_duplicates().reset_index(drop=True)
sales = load_sales()
name = a["ServiceName"].fillna("")
is_maint_item = a["ServiceMaintenance"].notna()

# Nombres que contienen 'maint' (sin distinguir mayúsculas) y no tienen número
maint_like = name.str.lower().str.contains("maint")
emit("V0.1 Nombres de servicio que contienen 'maint' (cualquier mayúscula) y su número",
     pd.DataFrame({"ítems": a.loc[maint_like].groupby([name[maint_like].str.replace(r"^\d+[°ª] ", "", regex=True), is_maint_item[maint_like]]).size()}),
     note="Si hubiera ítems 'Maintenance ...' sin ServiceMaintenance, aparecerían con False.")
sin_num = (maint_like & ~is_maint_item).sum()
otros_tipos = (is_maint_item & ~a["ServiceType"].eq("Mantenimiento")).sum()
mant_sin_num = a["ServiceType"].eq("Mantenimiento") & ~is_maint_item
emit("V0.2 Consistencia ServiceMaintenance", pd.DataFrame({"n": [
    int(is_maint_item.sum()), int(otros_tipos), int(sin_num), int(mant_sin_num.sum()),
    a.loc[mant_sin_num, "ServiceName"].value_counts().to_dict(),
]}, index=["ítems con ServiceMaintenance no nulo", "... con ServiceType != Mantenimiento", "ítems con 'maint' en el nombre y sin número",
           "ítems ServiceType=Mantenimiento sin número", "... nombres"]))

# Turnos con más de un ítem de mantenimiento
mm = a[is_maint_item].groupby("schedule_id")["ServiceMaintenance"].agg(["size", "nunique", "min", "max"])
emit("V0.3 Turnos con más de un ítem de mantenimiento", pd.DataFrame({"valor": [
    len(mm), int((mm["size"] >= 2).sum()), int((mm["nunique"] >= 2).sum()), (mm["max"] - mm["min"])[mm["nunique"] >= 2].value_counts().head(5).to_dict()]},
    index=["turnos con ítem de mantenimiento", "con >= 2 ítems de mantenimiento", "con números distintos", "distribución max−min (top 5)"]),
    note="maint_number = min por turno; con 97 turnos afectados es irrelevante.")

# Colapso propio: estado por turno (primer valor), flags por pertenencia
status = a.groupby("schedule_id")["StatusARG"].agg(lambda s: s.iloc[0])
mixed = a.groupby("schedule_id")["StatusARG"].nunique()
maint_sids = set(a.loc[is_maint_item, "schedule_id"])
veh = a.groupby("schedule_id")["vehicle_id"].first()
sched = a.groupby("schedule_id")["ScheduleDate"].first()
chk = a.groupby("schedule_id")["EffectiveCheckinDate"].first()
mn = a[is_maint_item].groupby("schedule_id")["ServiceMaintenance"].min()
own = pd.DataFrame({"StatusARG": status, "vehicle_id": veh, "ScheduleDate": sched, "checkin": chk})
own["has_maint"] = own.index.isin(maint_sids)
own["maint_number"] = mn.reindex(own.index)
gap = (own["checkin"] - own["ScheduleDate"]).dt.days
own["event_date"] = own["checkin"].where(gap.between(-45, 45)).fillna(own["ScheduleDate"])
own = own.reset_index()

# Cruce con appointments()
ap = appointments(a)
apx = ap.set_index("schedule_id")
cmp_ = own.set_index("schedule_id")
emit("V0.4 Colapso propio vs appointments(): coincidencia de flags", pd.DataFrame({"valor": [
    len(own), len(ap), int((cmp_["StatusARG"] != apx.loc[cmp_.index, "StatusARG"]).sum()), int(mixed.gt(1).sum()),
    int((cmp_["has_maint"] != apx.loc[cmp_.index, "has_maint"]).sum()),
    int((cmp_["event_date"] != apx.loc[cmp_.index, "event_date"]).sum()),
    int(((cmp_["maint_number"].fillna(-1)) != apx.loc[cmp_.index, "maint_number"].fillna(-1)).sum()),
]}, index=["turnos (propio)", "turnos appointments()", "StatusARG distinto", "turnos con StatusARG mixto en ítems", "has_maint distinto",
           "event_date distinto", "maint_number distinto"]))

# ---------------------------------------------------------------------------------------------
# 1. Afirmación 1: definición del evento objetivo y regla final
# ---------------------------------------------------------------------------------------------
# Conteo directo desde ÍTEMS (sin pasar por el colapso): schedule_id distintos con StatusARG (60) y número
direct = a.loc[a["StatusARG"].eq(S60) & is_maint_item, "schedule_id"].nunique()
direct_veh = a.loc[a["StatusARG"].eq(S60) & is_maint_item, "vehicle_id"].nunique()
cand = own[own["StatusARG"].eq(S60) & own["has_maint"]]
n_noveh = int(cand["vehicle_id"].isna().sum())
c = cand[cand["vehicle_id"].notna() & (cand["ScheduleDate"] <= CUTOFF)].sort_values(["vehicle_id", "event_date", "schedule_id"]).copy()
# dedup (1) un evento por vehículo-día
c["dup_day"] = c.duplicated(["vehicle_id", "event_date"], keep="first")
c1 = c[~c["dup_day"]].copy()
# dedup (2) mismo número a <= 30 días del anterior conservado; implementación iterativa por vehículo (sin efecto cadena)
keep = np.ones(len(c1), dtype=bool)
vid = c1["vehicle_id"].to_numpy(); dts = c1["event_date"].to_numpy(); nn = c1["maint_number"].to_numpy()
last_date = {}; last_n = {}
for i in range(len(c1)):
    v = vid[i]
    if v in last_date and nn[i] == last_n[v] and (dts[i] - last_date[v]) / np.timedelta64(1, "D") <= 30:
        keep[i] = False
        continue
    last_date[v] = dts[i]; last_n[v] = nn[i]
c1["dup_n30"] = ~keep
# variante 'shift' (como el script original): compara con el anterior por fecha, aunque ese anterior sea un duplicado
prev_d = c1.groupby("vehicle_id")["event_date"].shift(1); prev_n = c1.groupby("vehicle_id")["maint_number"].shift(1)
dup_shift = (c1["maint_number"] == prev_n) & ((c1["event_date"] - prev_d).dt.days <= 30)
final = c1[~c1["dup_n30"]]
emit("V1.1 Recuento independiente de la regla final", pd.DataFrame({"turnos": [
    direct, len(cand), n_noveh, int((cand["vehicle_id"].notna() & (cand["ScheduleDate"] > CUTOFF)).sum()), int(c["dup_day"].sum()),
    int(c1["dup_n30"].sum()), int(dup_shift.sum()), len(final)],
    "vehículos": [direct_veh, cand["vehicle_id"].nunique(), 0, 0, c.loc[c["dup_day"], "vehicle_id"].nunique(),
                  c1.loc[c1["dup_n30"], "vehicle_id"].nunique(), c1.loc[dup_shift, "vehicle_id"].nunique(), final["vehicle_id"].nunique()]},
    index=["(60) & número, contado desde ítems (schedule_id distintos)", "candidatos (60) & has_maint (colapso propio)",
           "− sin vehicle_id", "− ScheduleDate > CUTOFF (con vehicle_id)", "− segundo evento mismo vehículo-día",
           "− mismo número a <= 30 d (iterativo, sin cadena)", "  (variante shift del script original)", "evento objetivo final"]),
    note="Informe: 222.889 / 87.531; −1.186; −335; −846; 220.522.")
emit("V1.2 Evento objetivo por año de event_date", final.groupby(final["event_date"].dt.year).size().to_frame("eventos"),
     note="Informe: 73.361 / 87.153 / 60.008.")
# ¿qué queda si NO se deduplica por número? ¿y los pares mismo número a 31-90 días?
emit("V1.3 Sensibilidad de la deduplicación", pd.DataFrame({"valor": [
    int(dup_shift.sum() - c1["dup_n30"].sum()), int((c1["dup_n30"] & c1["checkin"].isna()).sum()),
]}, index=["diferencia entre variante shift (original) e iterativa", "descartados por número sin EffectiveCheckinDate"]))
# ¿Los (60)+mant sin vehicle_id se podrían recuperar por customer_id?
cust_veh = ap[ap["vehicle_id"].notna() & ap["customer_id"].notna()].groupby("customer_id")["vehicle_id"].nunique()
nv = ap[ap["is_completed_maintenance"] & ap["vehicle_id"].isna()]
nv_c = nv["customer_id"].map(cust_veh)
emit("V1.4 (60)+mant sin vehicle_id: ¿tienen customer_id y ese cliente tiene un único vehículo en la agenda?", pd.DataFrame({"valor": [
    len(nv), int(nv["customer_id"].notna().sum()), int(nv_c.eq(1).sum()), int(nv_c.ge(2).sum()), int((nv["customer_id"].notna() & nv_c.isna()).sum())]},
    index=["(60)+mant sin vehicle_id", "con customer_id", "cliente con exactamente 1 vehículo en agenda", "cliente con >= 2 vehículos", "cliente sin ningún vehículo conocido"]),
    note="Tema del EDA de linkage; se deja como dato para decidir si vale la pena recuperarlos.")

# ---------------------------------------------------------------------------------------------
# 2. Afirmación 2: (90) Concluido sin OS
# ---------------------------------------------------------------------------------------------
ev = ap[ap["vehicle_id"].notna()].copy()
prof = ap.groupby("StatusARG").agg(
    turnos=("schedule_id", "size"),
    checkin=("EffectiveCheckinDate", lambda s: s.notna().mean()),
    checkout=("EffectiveCheckoutDate", lambda s: s.notna().mean()),
    vck=("VehicleCurrentKM", lambda s: s.notna().mean()),
    dias_med=("DaysInDealer", "median"),
    has_maint=("has_maint", "mean"), has_diag=("has_diag", "mean"), has_repair=("has_repair", "mean"),
).reindex([S60, S90, S80, S70])
for col in ["checkin", "checkout", "vck", "has_maint", "has_diag", "has_repair"]:
    prof[col] = (100 * prof[col]).round(1)
emit("V2.1 Perfil por estado (recalculado)", prof, note="Informe (90): check-in 81,1 / check-out 96,4 / VCK 97,2 / mediana 4 días / mant 26,2 / diag 48,8.")

item_sets = a.groupby("schedule_id")["ServiceType"].agg(lambda s: frozenset(s.fillna("SIN").str.lower()))
n90 = ap[ap["completed_no_os"]]
solo_diag = item_sets.reindex(n90["schedule_id"]).map(lambda s: s == frozenset({"diagnóstico"})).mean()
emit("V2.2 (90): % 'solo diagnóstico' (recalculado por ServiceType)", pd.DataFrame({"valor": [len(n90), pct(solo_diag)]}, index=["turnos (90)", "% solo Diagnóstico"]),
     note="Informe: 37,6 %.")


def within(sub: pd.DataFrame, ref: pd.DataFrame, lo: int, hi: int) -> pd.Series:
    x = sub[["schedule_id", "vehicle_id", "event_date"]].merge(ref, on="vehicle_id", how="inner")
    dd = (x["cdate"] - x["event_date"]).dt.days
    ok = x.loc[dd.between(lo, hi) & (x["csid"] != x["schedule_id"]), "schedule_id"].unique()
    return sub["schedule_id"].isin(ok)


comp = ev.loc[ev["completed"], ["schedule_id", "vehicle_id", "event_date"]].rename(columns={"schedule_id": "csid", "event_date": "cdate"})
compm = ev.loc[ev["is_completed_maintenance"], ["schedule_id", "vehicle_id", "event_date", "maint_number", "VehicleCurrentKM"]].rename(
    columns={"schedule_id": "csid", "event_date": "cdate", "maint_number": "cn", "VehicleCurrentKM": "ckm"})
n90v = ev[ev["completed_no_os"]]
n90m = n90v[n90v["has_maint"]]
emit("V2.3 (90) con vehicle_id: cercanía a un (60)", pd.DataFrame({"valor": [
    len(n90v), pct(within(n90v, comp, -30, 30).mean()), len(n90m), int(within(n90m, compm[["csid", "vehicle_id", "cdate"]], 1, 30).sum()),
    int(within(n90m, compm[["csid", "vehicle_id", "cdate"]], 0, 30).sum()), int(within(n90m, compm[["csid", "vehicle_id", "cdate"]], 1, 90).sum())]},
    index=["(90) con vehículo", "% con (60) en ±30 d", "(90) con ítem mant", "con (60)+mant en (0,30]", "con (60)+mant en [0,30]", "con (60)+mant en (0,90]"]),
    note="Informe: 15.247 / 31,7 % / 3.977 / 206 / – / 542.")

# TEST NUEVO: número de service del siguiente y del anterior (60)+mant respecto del (90)+mant
x = n90m[["schedule_id", "vehicle_id", "event_date", "maint_number", "VehicleCurrentKM"]].merge(compm, on="vehicle_id", how="left")
nxt = x[x["cdate"] > x["event_date"]].sort_values("cdate").groupby("schedule_id").first()
prv = x[x["cdate"] < x["event_date"]].sort_values("cdate").groupby("schedule_id").last()
t = n90m.set_index("schedule_id")[["maint_number", "VehicleCurrentKM", "event_date"]].copy()
t["next_n"] = nxt["cn"]; t["next_days"] = (nxt["cdate"] - t["event_date"]).dt.days; t["next_km"] = nxt["ckm"]
t["prev_n"] = prv["cn"]; t["prev_days"] = (t["event_date"] - prv["cdate"]).dt.days
dn = t["next_n"] - t["maint_number"]
cat_next = pd.Series(np.select([t["next_n"].isna(), dn.eq(0), dn.eq(1), dn.gt(1), dn.lt(0)],
                               ["sin (60)+mant posterior", "mismo número (n)", "n+1", "n+2 o más", "número menor"], "otro"), index=t.index)
tn = cat_next.value_counts().to_frame("turnos (90)+mant")
tn["%"] = (100 * tn.iloc[:, 0] / len(t)).round(1)
tn["mediana días al siguiente"] = t.groupby(cat_next)["next_days"].median()
tn["mediana Δ km al siguiente"] = (t["next_km"] - t["VehicleCurrentKM"]).groupby(cat_next).median()
emit("V2.4 TEST: número de service del SIGUIENTE (60)+mant del vehículo respecto del (90)+mant", tn,
     note="Si el service se hubiera hecho en el (90), el siguiente debería traer n+1; si no se hizo, el mismo n.")
# Solo (90) con seguimiento completo (>= 365 días antes del CUTOFF) para no confundir 'sin posterior' con censura
tt = t[t["event_date"] <= CUTOFF - pd.Timedelta(days=365)]
cat_tt = cat_next.reindex(tt.index)
tn2 = cat_tt.value_counts().to_frame("turnos (90)+mant (>= 1 año de seguimiento)")
tn2["%"] = (100 * tn2.iloc[:, 0] / len(tt)).round(1)
emit("V2.5 Ídem, solo (90)+mant con al menos 365 días de seguimiento", tn2)
dp = t["maint_number"] - t["prev_n"]
emit("V2.6 Número del (60)+mant ANTERIOR respecto del (90)+mant", pd.Series(np.select(
    [t["prev_n"].isna(), dp.eq(0), dp.eq(1), dp.gt(1), dp.lt(0)], ["sin (60)+mant anterior", "mismo número", "n−1 (el (90) es el siguiente del plan)", "salto > 1", "número mayor"], "otro"),
    index=t.index).value_counts().to_frame("turnos (90)+mant"))
# Retención comparada: ¿aparece OTRO (60)+mant del vehículo dentro de los 365 días? (eventos con >= 365 días de seguimiento)
ref_m = compm[["csid", "vehicle_id", "cdate"]]
base60 = ev[ev["is_completed_maintenance"] & (ev["event_date"] <= CUTOFF - pd.Timedelta(days=365))]
base90 = n90m[n90m["event_date"] <= CUTOFF - pd.Timedelta(days=365)]
base90_all = n90v[n90v["event_date"] <= CUTOFF - pd.Timedelta(days=365)]
emit("V2.7 Retención a 365 días: (60)+mant vs (90)+mant vs (90) sin mant (eventos con >= 1 año de seguimiento)", pd.DataFrame({
    "(60)+mant": [len(base60), pct(within(base60, ref_m, 1, 365).mean()), pct(within(base60, ref_m, 1, 180).mean())],
    "(90)+mant": [len(base90), pct(within(base90, ref_m, 1, 365).mean()), pct(within(base90, ref_m, 1, 180).mean())],
    "(90) sin mant": [len(base90_all) - len(base90), pct(within(base90_all[~base90_all["has_maint"]], ref_m, 1, 365).mean()), pct(within(base90_all[~base90_all["has_maint"]], ref_m, 1, 180).mean())],
}, index=["eventos", "% con (60)+mant del vehículo en (0,365]", "% con (60)+mant en (0,180]"]),
    note="Si el (90)+mant fuera un service hecho sin OS, su retención posterior debería parecerse a la de un (60)+mant.")
# Delta n del siguiente respecto del (90), comparado con el del siguiente respecto de un (60)+mant (tasa base)
cm_sorted = cmv_base = ev[ev["is_completed_maintenance"]].sort_values(["vehicle_id", "event_date", "schedule_id"])
nxt_n = cm_sorted.groupby("vehicle_id")["maint_number"].shift(-1)
dn60 = (nxt_n - cm_sorted["maint_number"]).dropna()
emit("V2.8 Δn del SIGUIENTE (60)+mant: tasa base tras un (60)+mant vs tras un (90)+mant (solo con siguiente observado)", pd.DataFrame({
    "tras (60)+mant": [len(dn60), pct(dn60.eq(1).mean()), pct(dn60.eq(0).mean()), pct(dn60.gt(1).mean()), pct(dn60.lt(0).mean())],
    "tras (90)+mant": [int(dn.notna().sum()), pct(dn.dropna().eq(1).mean()), pct(dn.dropna().eq(0).mean()), pct(dn.dropna().gt(1).mean()), pct(dn.dropna().lt(0).mean())],
}, index=["pares", "n+1", "mismo n", "n+2 o más", "menor"]),
    note="'mismo n' = el vehículo vuelve por el mismo hito: evidencia de que ese service no se había hecho.")

# ---------------------------------------------------------------------------------------------
# 3. Afirmación 3: garantía, campañas/recall, aceite y filtro
# ---------------------------------------------------------------------------------------------
st = a["ServiceType"].fillna("")
cls = pd.Series(np.select([is_maint_item, name.eq("Guarantee"), name.eq("Oil and filter change"), st.str.lower().eq("campañas de servicio")],
                          ["MANT", "GARANTIA", "ACEITE", "CAMPANA"], "OTRO"), index=a.index)
sets = pd.DataFrame({"schedule_id": a["schedule_id"], "cls": cls}).groupby("schedule_id")["cls"].agg(frozenset)
own2 = own.set_index("schedule_id")
own2["i_G"] = sets.map(lambda s: "GARANTIA" in s); own2["i_O"] = sets.map(lambda s: "ACEITE" in s); own2["i_C"] = sets.map(lambda s: "CAMPANA" in s)
c60 = own2[own2["StatusARG"].eq(S60)]
scen = {
    "A (60)&mant": c60["has_maint"], "B A+aceite": c60["has_maint"] | c60["i_O"], "C B+garantía": c60["has_maint"] | c60["i_O"] | c60["i_G"],
    "D C+campañas/recall": c60["has_maint"] | c60["i_O"] | c60["i_G"] | c60["i_C"],
}
sc = pd.DataFrame({"turnos": {k: int(v.sum()) for k, v in scen.items()}, "vehículos": {k: c60.loc[v, "vehicle_id"].nunique() for k, v in scen.items()}})
sc["Δ turnos vs A"] = sc["turnos"] - sc["turnos"].iloc[0]
e_ = own2[own2["StatusARG"].isin([S60, S90]) & own2["has_maint"]]
sc.loc["E A+(90) con mant"] = [len(e_), e_["vehicle_id"].nunique(), len(e_) - sc["turnos"].iloc[0]]
emit("V3.1 Escenarios de target (recalculados)", sc, note="Informe: 222.889 / 224.016 / 227.805 / 254.596 / 226.947.")

gi = a[name.eq("Guarantee")]; ri = a[st.str.lower().eq("campañas de servicio")]; oi = a[name.eq("Oil and filter change")]
emit("V3.2 Guarantee por año de ScheduleDate", gi["ScheduleDate"].dt.year.value_counts().sort_index().to_frame("ítems"))
emit("V3.3 'Service campaign' vs 'Recall' por mes (2025-10 en adelante)",
     pd.crosstab(ri.loc[ri["ScheduleDate"] >= "2025-10-01", "ScheduleDate"].dt.to_period("M").astype(str), ri.loc[ri["ScheduleDate"] >= "2025-10-01", "ServiceName"]),
     note="Transición limpia enero-febrero 2026, igual que 'service' -> 'review'.")
emit("V3.4 Campañas/Recall: precio fijo y flag", pd.crosstab(ri["ServiceName"], [ri["ServiceFordFixedPriceFlag"].fillna("(nulo)"), ri["ServiceFordFixedPrice"].fillna(-1)]),
     note="Ambos nombres tienen ServiceFordFixedPrice = 0 (gratuito); 'Recall' lleva flag N, no Y.")
edad_r = ((ri["ScheduleDate"] - ri["WarrantyStartDate"]).dt.days / 30.44)
edad_o = ((oi["ScheduleDate"] - oi["WarrantyStartDate"]).dt.days / 30.44)
emit("V3.5 Campañas/Recall y Oil&filter: edad y km (ítems, todos los estados)", pd.DataFrame({
    "Campañas/Recall": [len(ri), round(edad_r.median(), 1), ri["VehicleCurrentKM"].median(), pct(ri["VehicleCurrentKM"].notna().mean())],
    "Oil and filter change": [len(oi), round(edad_o.median(), 1), oi["VehicleCurrentKM"].median(), pct(oi["VehicleCurrentKM"].notna().mean())],
}, index=["ítems", "mediana edad (meses)", "mediana VehicleCurrentKM (no nulos)", "% VehicleCurrentKM no nulo"]),
    note="Informe: campañas 13,6 meses / 24.174 km; aceite 32,8 meses / 65.496 km.")

# Oil & filter: ¿sustituye a un service del plan?
oil60 = ap[ap["completed"] & ap["schedule_id"].isin(own2.index[own2["i_O"]]) & ap["vehicle_id"].notna()].copy()
solo_oil = oil60[~oil60["has_maint"] & sets.reindex(oil60["schedule_id"]).map(lambda s: s <= frozenset({"ACEITE", "OTRO"})).values]
# 'solo aceite' en sentido estricto del informe: solo ACEITE (+PUD/móvil); acá 'OTRO' incluye PUD/móvil y también diag/repar -> uso la clase fina
fine = pd.Series(np.select([is_maint_item, name.eq("Oil and filter change"), st.isin(["Pick Up & Delivery", "Mobile Service", "Taller Móvil"])],
                           ["MANT", "ACEITE", "AUX"], "OTRO"), index=a.index)
fsets = pd.DataFrame({"schedule_id": a["schedule_id"], "cls": fine}).groupby("schedule_id")["cls"].agg(frozenset)
only_oil_mask = fsets.reindex(oil60["schedule_id"]).map(lambda s: "ACEITE" in s and s <= frozenset({"ACEITE", "AUX"})).values
solo_oil = oil60[only_oil_mask].copy()
xo = solo_oil[["schedule_id", "vehicle_id", "event_date", "VehicleCurrentKM", "ShortVehicleModelGroupTreated"]].merge(compm, on="vehicle_id", how="left")
po = xo[xo["cdate"] < xo["event_date"]].sort_values("cdate").groupby("schedule_id").last()
no = xo[xo["cdate"] > xo["event_date"]].sort_values("cdate").groupby("schedule_id").first()
so = solo_oil.set_index("schedule_id")
so["prev_n"] = po["cn"]; so["prev_days"] = (so["event_date"] - po["cdate"]).dt.days; so["prev_km"] = po["ckm"]
so["next_n"] = no["cn"]; so["next_days"] = (no["cdate"] - so["event_date"]).dt.days
gen = so["ShortVehicleModelGroupTreated"]
p703 = gen.eq("RANGER (P703)"); p375 = gen.eq("RANGER (P375)")
hito = np.where(p703, 15000, np.where(p375, 10000, np.nan))
resid = (so["VehicleCurrentKM"] / hito)
near_hito = ((resid - resid.round()).abs() <= 0.15) & (resid.round() >= 1)
emit("V3.6 (60) 'solo Oil and filter change' (+PUD/móvil): ¿reemplaza un service del plan?", pd.DataFrame({"valor": [
    len(so), so["vehicle_id"].nunique(), int(p703.sum()), int(p375.sum()),
    so["VehicleCurrentKM"].quantile([.25, .5, .75]).round(0).tolist(),
    pct(so["prev_n"].notna().mean()), so["prev_days"].median(), (so["VehicleCurrentKM"] - so["prev_km"]).median(),
    so.loc[so["prev_n"].notna(), "prev_n"].value_counts().sort_index().head(6).to_dict(),
    pct(so["next_n"].notna().mean()), so["next_days"].median(),
    pct((so["next_n"] - so["prev_n"]).eq(1).mean()), pct((so["next_n"] - so["prev_n"]).ge(2).mean()),
    pct(near_hito[p703 | p375].mean()),
    pct(near_hito[p703].mean()), pct(near_hito[p375].mean()),
    so["ModelYear"].value_counts().sort_index().to_dict(),
]}, index=["turnos (60) solo aceite", "vehículos", "P703", "P375", "VehicleCurrentKM p25/p50/p75",
           "% con (60)+mant ANTERIOR del vehículo", "mediana días desde el (60)+mant anterior", "mediana Δ km desde el (60)+mant anterior",
           "número del (60)+mant anterior (top 6)", "% con (60)+mant POSTERIOR", "mediana días al (60)+mant posterior",
           "% con anterior y posterior: Δn = +1 (el aceite no cuenta en el plan)", "% con anterior y posterior: Δn >= 2 (el aceite 'ocupó' un hito)",
           "% con km a ±15 % de un múltiplo del hito (15k P703 / 10k P375)", "... P703", "... P375", "ModelYear"]),
    note="Si el cambio de aceite sustituyera un service del plan, esperaríamos km cerca de un múltiplo del hito y Δn >= 2 entre el service anterior y el posterior.")
dk = (so["VehicleCurrentKM"] - so["prev_km"])
emit("V3.7 'Solo aceite': Δ km y días desde el (60)+mant anterior, por generación", pd.DataFrame({
    "P703": [int((p703 & so["prev_n"].notna()).sum()), dk[p703].median(), dk[p703].quantile(.25), dk[p703].quantile(.75), so.loc[p703, "prev_days"].median(),
             pct(so.loc[p703, "prev_days"].le(400).mean())],
    "P375": [int((p375 & so["prev_n"].notna()).sum()), dk[p375].median(), dk[p375].quantile(.25), dk[p375].quantile(.75), so.loc[p375, "prev_days"].median(),
             pct(so.loc[p375, "prev_days"].le(400).mean())],
}, index=["turnos con (60)+mant anterior", "mediana Δ km", "p25 Δ km", "p75 Δ km", "mediana días desde el anterior", "% con anterior a <= 400 días"]),
    note="Comparar con el intervalo entre services consecutivos Δn=+1: P703 ~16.000 km, P375 ~10.200 km (V6.2).")
fig, ax = plt.subplots(figsize=(9, 4.5))
bins = np.arange(0, 160001, 5000)
ax.hist(so.loc[p703, "VehicleCurrentKM"].clip(upper=160000), bins=bins, alpha=0.65, label=f"P703 (n={int(p703.sum())})", color="#4c72b0")
ax.hist(so.loc[p375, "VehicleCurrentKM"].clip(upper=160000), bins=bins, alpha=0.55, label=f"P375 (n={int(p375.sum())})", color="#dd8452")
for k in range(1, 11):
    ax.axvline(15000 * k, color="#4c72b0", ls=":", lw=0.7)
ax.set_xlabel("VehicleCurrentKM al ingreso (truncado a 160.000)"); ax.set_ylabel("Turnos (60) 'solo aceite y filtro'")
ax.set_title("Turnos (60) 'solo aceite y filtro': km al ingreso (líneas punteadas = múltiplos de 15.000 km)")
ax.legend()
savefig(fig, "aceite_km")

# ---------------------------------------------------------------------------------------------
# 4. Afirmación 4: n es hito de km; edad al 1° service y censura
# ---------------------------------------------------------------------------------------------
mi = a[is_maint_item & a["StatusARG"].eq(S60)].copy()
mi["n"] = mi["ServiceMaintenance"].astype(int)
mi["edad_m"] = (mi["ScheduleDate"] - mi["WarrantyStartDate"]).dt.days / 30.44
g703 = mi[mi["ShortVehicleModelGroupTreated"].eq("RANGER (P703)")]
g375 = mi[mi["ShortVehicleModelGroupTreated"].eq("RANGER (P375)")]
kmn = pd.DataFrame({
    "P703 ítems": g703.groupby("n").size(), "P703 mediana km": g703.groupby("n")["VehicleCurrentKM"].median(),
    "P703 p25 km": g703.groupby("n")["VehicleCurrentKM"].quantile(.25), "P703 p75 km": g703.groupby("n")["VehicleCurrentKM"].quantile(.75),
    "P703 mediana edad": g703.groupby("n")["edad_m"].median().round(1),
    "P375 ítems": g375.groupby("n").size(), "P375 mediana km": g375.groupby("n")["VehicleCurrentKM"].median(),
    "P375 mediana edad": g375.groupby("n")["edad_m"].median().round(1),
}).reindex(range(1, 21))
emit("V4.1 km al ingreso y edad por número de service, turnos (60), por generación (recalculado)", kmn,
     note="Informe P703: 16.008 / 32.130 / 48.416 / 64.650; P375: 11.060 / 20.548 / 30.614 / 40.696; n=20 P375 221.749.")


def share_within(df, per):
    r = df["VehicleCurrentKM"] / (df["n"] * per)
    return r.between(0.8, 1.2).mean()


emit("V4.2 % de ítems dentro de ±20 % de n × hito", pd.DataFrame({"valor": [
    pct(share_within(g703, 15000)), pct(share_within(g703, 10000)), round((g703["VehicleCurrentKM"] / g703["n"]).median()),
    pct(share_within(g375, 10000)), pct(share_within(g375, 15000)), round((g375["VehicleCurrentKM"] / g375["n"]).median()),
    pct(share_within(g703[g703["n"] <= 10], 15000)), pct(share_within(g375[g375["n"] <= 10], 10000)),
]}, index=["P703 ±20 % de n×15.000", "P703 ±20 % de n×10.000", "P703 mediana km/n", "P375 ±20 % de n×10.000", "P375 ±20 % de n×15.000",
           "P375 mediana km/n", "P703 n<=10: ±20 % de n×15.000", "P375 n<=10: ±20 % de n×10.000"]),
    note="Informe: 75,4 % / 8,1 % / 16.073; 78,5 % / 7,9 % / 10.161.")
diff = mi["edad_m"] - mi["ServiceMonth"]
emit("V4.3 edad − ServiceMonth", pd.DataFrame({"valor": [round(diff.median(), 1), pct((diff.abs() <= 6).mean()), pct(mi["edad_m"].isna().mean())]},
                                                index=["mediana (meses)", "% con |edad − ServiceMonth| <= 6", "% ítems sin WarrantyStartDate (cuentan como no)"]),
     note="Informe: −17,5 / 24,2 %.")

# Censura: edad al 1° service P703 por cohorte de WarrantyStartDate
f1 = g703[g703["n"].eq(1)].copy()
f1["cohorte"] = f1["WarrantyStartDate"].dt.to_period("Q").astype(str)
f1["fu_meses"] = (CUTOFF - f1["WarrantyStartDate"]).dt.days / 30.44
coh = f1.groupby("cohorte").agg(items=("n", "size"), mediana_edad=("edad_m", "median"), p75_edad=("edad_m", lambda s: s.quantile(.75)),
                                p90_edad=("edad_m", lambda s: s.quantile(.9)), mediana_km=("VehicleCurrentKM", "median"), seguimiento_min_meses=("fu_meses", "min"))
coh = coh[coh.index >= "2023Q1"].round(1)
emit("V4.4 P703, 1° service (60): edad por cohorte trimestral de WarrantyStartDate (la mediana global 8,4 mezcla cohortes censuradas)", coh,
     note="Las cohortes de 2023 tienen censura por la izquierda (la agenda empieza en 2024-01: sus 1° service tempranos no se ven); "
          "las de 2025-2026 por la derecha (todavía no llegaron al 1° service los que tardan más).")
full = f1[f1["WarrantyStartDate"].between("2024-01-01", "2024-06-30")]
full24 = full[full["edad_m"] <= 24]
emit("V4.5 P703, 1° service: cohorte WarrantyStart 2024-01..06 (>= 26 meses de seguimiento) vs todas", pd.DataFrame({
    "todas las cohortes": [len(f1), round(f1["edad_m"].median(), 1), round(f1["edad_m"].quantile(.75), 1), round(f1["edad_m"].quantile(.9), 1), pct((f1["edad_m"] <= 12).mean())],
    "cohorte 2024-H1": [len(full), round(full["edad_m"].median(), 1), round(full["edad_m"].quantile(.75), 1), round(full["edad_m"].quantile(.9), 1), pct((full["edad_m"] <= 12).mean())],
    "cohorte 2024-H1, edad <= 24 m": [len(full24), round(full24["edad_m"].median(), 1), round(full24["edad_m"].quantile(.75), 1), round(full24["edad_m"].quantile(.9), 1), pct((full24["edad_m"] <= 12).mean())],
}, index=["ítems n=1", "mediana edad (meses)", "p75", "p90", "% con 1° service antes de los 12 meses"]))
fig, ax = plt.subplots(figsize=(9, 4.5))
bins = np.arange(0, 37, 1)
ax.hist(f1["edad_m"].dropna().clip(upper=36), bins=bins, density=True, alpha=0.55, label=f"todas las cohortes (n={len(f1)})", color="#4c72b0")
ax.hist(full["edad_m"].dropna().clip(upper=36), bins=bins, density=True, alpha=0.55, label=f"WarrantyStart 2024-H1 (n={len(full)})", color="#dd8452")
ax.axvline(12, color="gray", ls="--", lw=1)
ax.set_xlabel("Edad del vehículo al 1° service (meses desde WarrantyStartDate, truncado a 36)"); ax.set_ylabel("Densidad")
ax.set_title("P703: edad al 1° service, todas las cohortes vs cohorte con seguimiento completo")
ax.legend()
savefig(fig, "edad_1er_service_cohorte")

# ---------------------------------------------------------------------------------------------
# 5. Afirmación 5: nombres 11 -> '1°', service -> review
# ---------------------------------------------------------------------------------------------
mall = a[is_maint_item].copy()
mall["n"] = mall["ServiceMaintenance"].astype(int)
mall["fam"] = np.where(mall["ServiceName"].str.contains("review"), "review", "service")
mall["num_nombre"] = mall["ServiceName"].str.extract(r"^(\d+)")[0].astype(int)
mall["nombre_ok"] = mall["num_nombre"] == mall["n"]
emit("V5.1 ¿El número del nombre coincide con ServiceMaintenance? por n y familia",
     pd.crosstab(mall["n"], [mall["fam"], mall["nombre_ok"]]).loc[9:20])
mon = mall[mall["ScheduleDate"].between("2025-12-01", "2026-03-31")]
emit("V5.2 review vs service por mes (dic-2025 a mar-2026)", pd.crosstab(mon["ScheduleDate"].dt.to_period("M").astype(str), mon["fam"]),
     note=f"Primer 'review': {mall.loc[mall['fam'].eq('review'), 'ScheduleDate'].min().date()}. Informe: ene 2.477/8.390; feb 7.951/536; mar 10.209/21.")
d26 = mall[mall["ScheduleDate"] >= "2026-02-01"].groupby("dealer_id")["fam"].agg(lambda s: s.eq("review").mean())
emit("V5.3 % review por dealer desde 2026-02", pd.DataFrame({"valor": [len(d26), round(100 * d26.min(), 1), int((d26 < 0.99).sum())]},
                                                           index=["dealers", "mínimo % review", "dealers con < 99 %"]), note="Informe: 94 / 92,4 % / 21.")
hi = mall["n"] >= 11
emit("V5.4 % ítems con n >= 11 por generación", (100 * hi.groupby(mall["ShortVehicleModelGroupTreated"]).mean()).round(1).to_frame("% n>=11"),
     note="Informe: P375 22,9 %; P703 1,3 %.")
my12 = mall[mall["ModelYear"].eq(2012)]
emit("V5.5 ModelYear 2012: % n >= 11", pd.DataFrame({"valor": [len(my12), pct((my12["n"] >= 11).mean())]}, index=["ítems", "% n>=11"]), note="Informe: 58 %.")

# ---------------------------------------------------------------------------------------------
# 6. Afirmación 6: maint_number como contador
# ---------------------------------------------------------------------------------------------
cmv = ev[ev["is_completed_maintenance"]].sort_values(["vehicle_id", "event_date", "schedule_id"]).copy()
g = cmv.groupby("vehicle_id")
cmv["dn"] = cmv["maint_number"] - g["maint_number"].shift(1)
cmv["dd"] = (cmv["event_date"] - g["event_date"].shift(1)).dt.days
cmv["dkm"] = cmv["VehicleCurrentKM"] - g["VehicleCurrentKM"].shift(1)
pairs = cmv[cmv["dn"].notna()]
nv2 = (g.size() >= 2)
mono = g["maint_number"].agg(lambda s: s.is_monotonic_increasing)[nv2]
strict = g["maint_number"].agg(lambda s: s.is_monotonic_increasing and s.is_unique)[nv2]
# tras la deduplicación de la regla final
cmf = cmv[cmv["schedule_id"].isin(final["schedule_id"])].copy()
gf = cmf.groupby("vehicle_id")
cmf["dn"] = cmf["maint_number"] - gf["maint_number"].shift(1); cmf["dd"] = (cmf["event_date"] - gf["event_date"].shift(1)).dt.days
pf = cmf[cmf["dn"].notna()]
emit("V6.1 Δn entre (60)+mant consecutivos (antes y después de la deduplicación)", pd.DataFrame({
    "antes de dedup": [len(pairs), pct(pairs["dn"].eq(1).mean()), pct(pairs["dn"].eq(0).mean()), pct(pairs["dn"].lt(0).mean()), pct(pairs["dn"].gt(1).mean()),
                       int(nv2.sum()), pct(mono.mean()), pct(strict.mean()), pairs["dd"].median(), pairs.loc[pairs["dn"].eq(1), "dkm"].median()],
    "después de dedup": [len(pf), pct(pf["dn"].eq(1).mean()), pct(pf["dn"].eq(0).mean()), pct(pf["dn"].lt(0).mean()), pct(pf["dn"].gt(1).mean()),
                         int((gf.size() >= 2).sum()), "–", "–", pf["dd"].median(), "–"],
}, index=["pares", "Δn = +1", "Δn = 0", "Δn < 0", "Δn > 1", "vehículos con >= 2", "secuencia no decreciente", "estrictamente creciente",
          "mediana días", "mediana Δ km (Δn=+1)"]), note="Informe: 134.172; 77,5 / 5,3 / 4,7 / 12,5 %; 55.815; 90,7 / 82,2 %; 161 d; 12.434 km.")
p1 = pairs[pairs["dn"].eq(1)]
emit("V6.2 Δ km entre services consecutivos con Δn = +1, por generación",
     p1.groupby("ShortVehicleModelGroupTreated")["dkm"].agg(["size", "median", lambda s: s.quantile(.25), lambda s: s.quantile(.75)]).rename(columns={"<lambda_0>": "p25", "<lambda_1>": "p75"}).round(0),
     note="El 12.434 pooled mezcla 15.000 (P703) y 10.000 (P375).")
z = pairs[pairs["dn"].eq(0)].copy()
z["bucket"] = pd.cut(z["dd"], [-1, 3, 30, 90, 180, 10000], labels=["0-3 d", "4-30 d", "31-90 d", "91-180 d", "> 180 d"])
emit("V6.3 Pares con el MISMO número: gap en días y Δ km", z.groupby("bucket", observed=True)["dkm"].agg(["size", "median", lambda s: (s.abs() <= 500).mean()]).rename(columns={"<lambda_0>": "% |Δkm| <= 500"}).round(2),
     note="Los pares con mismo número a > 30 días quedan como dos eventos en la regla final.")
firstm = cmv[g.cumcount().eq(0)].merge(sales[["vehicle_id", "SalesDate"]], on="vehicle_id", how="inner")
emit("V6.4 Vehículos de SALES: número del primer (60)+mant observado", pd.DataFrame({"valor": [len(firstm), pct(firstm["maint_number"].eq(1).mean()), int(firstm["maint_number"].eq(1).sum())]},
                                                                                index=["vehículos", "% n = 1", "n = 1"]), note="Informe: 36.950 / 92,0 % / 33.979.")

# ---------------------------------------------------------------------------------------------
# 7. Afirmación 7: IsReschedule / ScheduleReturn
# ---------------------------------------------------------------------------------------------
emit("V7.1 IsReschedule x StatusARG", pd.crosstab(ap["IsReschedule"].fillna("(nulo)"), ap["StatusARG"]))
raw = a.groupby("schedule_id")["ScheduleStatus"].first().reindex(ap["schedule_id"]).fillna("(nulo)").values
emit("V7.2 Cancelados: ScheduleStatus crudo x IsReschedule", pd.crosstab(pd.Series(raw, index=ap.index)[ap["cancelled"]], ap.loc[ap["cancelled"], "IsReschedule"].fillna("(nulo)")))
# (60) con IsReschedule=Y: ¿algún (70) del mismo vehículo en los 14 días previos? (cualquiera, no solo el turno inmediato anterior)
canc_ref = ev.loc[ev["cancelled"], ["schedule_id", "vehicle_id", "ScheduleDate"]].rename(columns={"schedule_id": "csid", "ScheduleDate": "cdate"})
c60y = ev[ev["completed"] & ev["IsReschedule"].eq("Y")]; c60n = ev[ev["completed"] & ev["IsReschedule"].isna()]


def within_sched(sub, ref, lo, hi):
    x = sub[["schedule_id", "vehicle_id", "ScheduleDate"]].merge(ref, on="vehicle_id", how="inner")
    dd = (x["cdate"] - x["ScheduleDate"]).dt.days
    ok = x.loc[dd.between(lo, hi) & (x["csid"] != x["schedule_id"]), "schedule_id"].unique()
    return sub["schedule_id"].isin(ok)


emit("V7.3 (60): ¿hay algún (70) del mismo vehículo en [-14, 0] días de ScheduleDate?", pd.DataFrame({"valor": [
    len(c60y), pct(within_sched(c60y, canc_ref, -14, 0).mean()), len(c60n), pct(within_sched(c60n, canc_ref, -14, 0).mean())]},
    index=["(60) IsReschedule=Y", "% con (70) en [-14,0]", "(60) IsReschedule nulo", "% con (70) en [-14,0]"]),
    note="Informe (solo el turno inmediato anterior): 57,7 % vs 3,0 %.")
ry = ev[ev["ScheduleReturn"].eq("Y")]
any_ref = ev[["schedule_id", "vehicle_id", "ScheduleDate"]].rename(columns={"schedule_id": "csid", "ScheduleDate": "cdate"})
comp_ref = ev.loc[ev["completed"], ["schedule_id", "vehicle_id", "ScheduleDate"]].rename(columns={"schedule_id": "csid", "ScheduleDate": "cdate"})
emit("V7.4 ScheduleReturn = Y (recalculado)", pd.DataFrame({"valor": [
    int(ap["ScheduleReturn"].eq("Y").sum()), len(ry), pct(within_sched(ry, any_ref, -30, -1).mean()), pct(within_sched(ry, comp_ref, -30, -1).mean()),
    pct(ry["has_maint"].mean()), pct(ry["has_diag"].mean()), pct(ry["has_repair"].mean()), pct(ap.loc[ap["ScheduleReturn"].eq("Y"), "ScheduleSource"].eq("Dealer").mean()),
    int((ap["completed"] & ap["has_maint"] & ap["ScheduleReturn"].eq("Y")).sum())]},
    index=["turnos Y", "con vehículo", "% con algún turno previo en [-30,-1]", "% con (60) previo en [-30,-1]", "% has_maint", "% has_diag", "% has_repair",
           "% fuente Dealer", "(60)+mant con ScheduleReturn=Y"]),
    note="Informe: 35.172; 98,0 %; 74,2 %; 14,1 / 37,4 / 30,4 %; 90,6 %; 4.380. (El 98,0 % del informe usa <= 30 incluyendo el mismo día.)")

# ---------------------------------------------------------------------------------------------
# 8. Afirmación 8: cancelaciones y no-show
# ---------------------------------------------------------------------------------------------
obs = ev[ev["ScheduleDate"] <= CUTOFF - pd.Timedelta(days=90)]
canc = obs[obs["cancelled"]]; ns_ = obs[obs["no_show"]]
cy = canc[canc["IsReschedule"].eq("Y")]; cn = canc[canc["IsReschedule"].eq("N")]
compY = ev.loc[ev["completed"] & ev["IsReschedule"].eq("Y"), ["schedule_id", "vehicle_id", "event_date"]].rename(columns={"schedule_id": "csid", "event_date": "cdate"})
rows = []
for label, sub, ref in [("(70) -> algún (60)", canc, comp), ("(70) Y -> algún (60)", cy, comp), ("(70) N -> algún (60)", cn, comp),
                        ("(70) con mant -> (60)+mant", canc[canc["has_maint"]], compm[["csid", "vehicle_id", "cdate"]]),
                        ("(80) -> algún (60)", ns_, comp), ("(80) con mant -> (60)+mant", ns_[ns_["has_maint"]], compm[["csid", "vehicle_id", "cdate"]])]:
    r = {"caso": label, "turnos": len(sub)}
    for h in (30, 60, 90):
        r[f"[0,{h}]"] = pct(within(sub, ref, 0, h).mean())
    r["[-30,-1]"] = pct(within(sub, ref, -30, -1).mean())
    r["[-30,90]"] = pct(within(sub, ref, -30, 90).mean())
    rows.append(r)
r = {"caso": "(60) -> otro (60)", "turnos": int(obs["completed"].sum())}
for h in (30, 60, 90):
    r[f"[0,{h}]"] = pct(within(obs[obs["completed"]], comp, 1, h).mean())
r["[-30,-1]"] = "–"; r["[-30,90]"] = "–"
rows.append(r)
emit("V8.1 Seguimiento (ScheduleDate <= CUTOFF−90): % con un (60) del mismo vehículo en la ventana", pd.DataFrame(rows).set_index("caso"),
     note="Informe [0,30/60/90]: (70) 57,5/64,2/69,1; Y 66,9/72,5/76,6; N 38,3/47,2/53,6; (70)mant 39,1/43,9/49,7; (80) 28,6/39,7/47,8; (80)mant 34,8/44,3/50,3; base 10,1/19,5/29,5.")
emit("V8.2 (70) IsReschedule=Y: ¿el turno reprogramado cayó ANTES de la fecha cancelada?", pd.DataFrame({"valor": [
    len(cy), pct(within(cy, compY, -30, -1).mean()), pct(within(cy, compY, 0, 90).mean()), pct(within(cy, compY, -30, 90).mean()),
    pct(within(cy, comp, -30, 90).mean())]},
    index=["(70) Y con seguimiento", "% con (60) IsReschedule=Y en [-30,-1]", "% con (60) IsReschedule=Y en [0,90]", "% con (60) IsReschedule=Y en [-30,90]",
           "% con algún (60) en [-30,90]"]),
    note="La 'cancelación efectiva' del informe (23,4 % para Y) ignora las reprogramaciones a una fecha anterior.")
emit("V8.3 Cancelaciones sin ningún ítem tipado", pd.DataFrame({"valor": [int(ap["cancelled"].sum()), int((ap["cancelled"] & ap["n_items"].eq(1) & ap["schedule_id"].isin(a.loc[a["ServiceType"].isna(), "schedule_id"])).sum())]},
                                                              index=["(70)", "(70) con un único ítem sin ServiceType"]), note="Informe: 58.113 de 101.222.")

# ---------------------------------------------------------------------------------------------
# 9. Afirmación 9: KM snapshot
# ---------------------------------------------------------------------------------------------
gv = ev.sort_values(["vehicle_id", "ScheduleDate", "schedule_id"]).groupby("vehicle_id")
sz = gv.size()
km_cnt = gv["KM"].count(); km_nu = gv["KM"].nunique()
vck_cnt = gv["VehicleCurrentKM"].count(); vck_nu = gv["VehicleCurrentKM"].nunique()
m2 = sz >= 2
emit("V9.1 KM y VehicleCurrentKM por vehículo (nulos tratados explícitamente)", pd.DataFrame({"valor": [
    int(m2.sum()), int((m2 & (km_cnt == 0)).sum()), int((m2 & (km_cnt >= 2)).sum()), pct((km_nu[m2 & (km_cnt >= 2)] == 1).mean()),
    int((m2 & (vck_cnt >= 2)).sum()), pct((vck_nu[m2 & (vck_cnt >= 2)] == 1).mean()),
]}, index=["vehículos con >= 2 turnos", "... con KM nulo en todos", "... con KM en >= 2 turnos", "% de esos con un único valor de KM",
           "... con VehicleCurrentKM en >= 2 turnos", "% de esos con un único valor de VehicleCurrentKM"]),
    note="Informe: 100 % / 13,3 % (el 13,3 % incluía vehículos con VehicleCurrentKM en un solo turno o en ninguno).")
# KM vs último VehicleCurrentKM no nulo del vehículo (no solo el último turno)
last_vck = gv["VehicleCurrentKM"].last()  # último no nulo
first_vck = gv["VehicleCurrentKM"].first()
kmv = gv["KM"].first()
ok = kmv.notna() & last_vck.notna()
emit("V9.2 KM vs VehicleCurrentKM", pd.DataFrame({"valor": [
    int(ok.sum()), pct(((kmv - last_vck).abs() <= 1000)[ok].mean()), pct((kmv >= last_vck - 1000)[ok].mean()),
    pct(((kmv - first_vck).abs() <= 1000)[kmv.notna() & first_vck.notna()].mean()),
    pct(((kmv - first_vck) > 1000)[kmv.notna() & first_vck.notna()].mean()),
]}, index=["vehículos con KM y algún VehicleCurrentKM", "% |KM − último VCK no nulo| <= 1.000", "% KM >= último VCK − 1.000",
           "% |KM − primer VCK no nulo| <= 1.000", "% KM > primer VCK + 1.000"]),
    note="Informe (último turno con ambos): 96,5 %; primer turno: 30,1 % / 67,0 %.")
n1 = ap[ap["is_completed_maintenance"] & ap["maint_number"].eq(1) & ap["ShortVehicleModelGroupTreated"].eq("RANGER (P703)")]
emit("V9.3 P703 1° service: KM vs VehicleCurrentKM (cuantiles)", pd.DataFrame({"KM": n1["KM"].quantile([.25, .5, .75]).round(0), "VehicleCurrentKM": n1["VehicleCurrentKM"].quantile([.25, .5, .75]).round(0)}).T,
     note="Informe: VCK 14.446 / 16.008 / 16.908; KM mediana 31.498, p75 48.700.")
emit("V9.4 % VehicleCurrentKM no nulo por estado", (100 * ap.groupby("StatusARG")["VehicleCurrentKM"].agg(lambda s: s.notna().mean())).round(1).to_frame("%"))

# ---------------------------------------------------------------------------------------------
# 10. Afirmación 10: Region / DealerStateOrZone
# ---------------------------------------------------------------------------------------------
dr = a.groupby("dealer_id").agg(n_region=("Region", "nunique"), n_zona=("DealerStateOrZone", "nunique"), region=("Region", "first"), zona=("DealerStateOrZone", "first"))
emit("V10.1 Constancia por dealer (filas ítem)", pd.DataFrame({"valor": [len(dr), int((dr["n_region"] > 1).sum()), int((dr["n_zona"] > 1).sum())]},
                                                             index=["dealers", "con > 1 Region", "con > 1 DealerStateOrZone"]))
reg = ap.groupby("Region").agg(dealers=("dealer_id", "nunique"), turnos=("schedule_id", "size"))
reg["% turnos"] = (100 * reg["turnos"] / len(ap)).round(2)
emit("V10.2 Region", reg, note="Informe: 60 → 80 dealers / 82,95 %; 00 → 11 / 15,83 %; 31 → 1; A → 3 (131 turnos).")
emit("V10.3 Dealers por DealerStateOrZone", dr["zona"].fillna("(nulo)").value_counts().sort_index().to_frame("dealers"), note="Informe: 15/17/18/23/20.")
dstate = sales.groupby("dealer_id")["State"].agg(lambda x: x.value_counts().index[0])
dr["prov"] = dr.index.map(dstate)
emit("V10.4 Dealers Region 00: provincia principal en SALES", dr.loc[dr["region"].eq("00"), "prov"].fillna("(sin ventas)").value_counts().to_frame("dealers"))
emit("V10.5 Zona 1: provincias (dealers con ventas)", dr.loc[dr["zona"].eq("1"), "prov"].fillna("(sin ventas)").value_counts().to_frame("dealers"))
emit("V10.6 dealer_id SALES vs AGENDA", pd.DataFrame({"valor": [sales["dealer_id"].nunique(), a["dealer_id"].nunique(), len(set(sales["dealer_id"].dropna()) & set(a["dealer_id"]))]},
                                                    index=["SALES", "AGENDA", "en común"]))
# ¿Region se relaciona con la fuente de agenda o con el tamaño del dealer?
emit("V10.7 Region x ScheduleSource (% por fila)", (100 * pd.crosstab(ap["Region"], ap["ScheduleSource"], normalize="index")).round(1))

# ---------------------------------------------------------------------------------------------
# Apéndice
# ---------------------------------------------------------------------------------------------
header = ("# Apéndice generado: verificación del EDA 01 (taxonomía de eventos y target)\n\n"
          f"Generado por `scripts/eda/01_taxonomia_target_verificacion.py` sobre `data/interim/agenda.parquet` "
          f"({len(a)} ítems tras eliminar duplicados exactos) y `sales.parquet`. CUTOFF = {CUTOFF.date()}.\n\n")
TABLES_MD.write_text(header + "\n".join(_sections), encoding="utf-8")
print(f"\n[ok] tablas -> {TABLES_MD}")
