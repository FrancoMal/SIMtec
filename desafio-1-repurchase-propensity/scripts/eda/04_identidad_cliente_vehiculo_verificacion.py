"""Verificación independiente (rol escéptico) de las afirmaciones del EDA 04.

Recalcula con código propio (no reutiliza el del script original) cada número clave de
reports/eda/04_identidad_cliente_vehiculo.md y prueba las hipótesis alternativas que podrían
refutarlo: confusores (n° de turnos, edad del vehículo), sesgos de población (ventana calculada
sobre el "último" mantenimiento), definiciones ambiguas ("nunca vino"), truncamiento de features
as-of, y números citados que el script original no produce (KM == VehicleCurrentKM del último turno).

Salida: stdout (tablas markdown) + reports/eda/04_identidad_cliente_vehiculo_verificacion_tablas.md

Uso (desde la carpeta del proyecto):
  PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/04_identidad_cliente_vehiculo_verificacion.py
"""
from __future__ import annotations

import io

import numpy as np
import pandas as pd

from repurchase import config
from repurchase.eventos import CUTOFF, appointments
from repurchase.io import load_agenda, load_sales

OUT_MD = config.REPORTS_DIR / "eda" / "04_identidad_cliente_vehiculo_verificacion_tablas.md"
_buf = io.StringIO()
pd.set_option("display.width", 250)
pd.set_option("display.max_columns", 60)


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


def pct(x: float, d: int = 1) -> str:
    return f"{100 * x:.{d}f}%"


ap = appointments()
sales = load_sales()
print(f"turnos {len(ap):,}  ventas {len(sales):,}  CUTOFF {CUTOFF.date()}")

a = ap.dropna(subset=["vehicle_id", "customer_id"]).sort_values(["vehicle_id", "event_date", "schedule_id"]).reset_index(drop=True)
a_hist = a[a["event_date"] <= CUTOFF]
sales_idx = sales.set_index("vehicle_id")

# ==============================================================================================
# V1) Multi-cliente y patrón secuencial
# ==============================================================================================
print("\n\n==================== V1) MULTI-CLIENTE Y PATRÓN ====================")
n_cust = a.groupby("vehicle_id")["customer_id"].nunique()
T("V1.1 Vehículos por n° de customer_id distintos (recalculado)", pd.DataFrame({
    "vehículos": [len(n_cust), int((n_cust > 1).sum()), int((n_cust == 2).sum()), int((n_cust == 3).sum())],
    "pct": [pct(1), pct((n_cust > 1).mean()), pct((n_cust == 2).mean()), pct((n_cust == 3).mean())],
}, index=["con customer_id", ">1 cliente", "2 clientes", "3 clientes"]))


def patron(df: pd.DataFrame) -> pd.DataFrame:
    """Clasificación independiente: n° de corridas (runs) de customer_id en orden temporal."""
    d = df.sort_values(["vehicle_id", "event_date", "schedule_id"])
    chg = d["customer_id"].ne(d.groupby("vehicle_id")["customer_id"].shift())
    first_row = d.groupby("vehicle_id").cumcount().eq(0)
    real_chg = chg & ~first_row
    same_day = real_chg & d["event_date"].eq(d.groupby("vehicle_id")["event_date"].shift())
    out = pd.DataFrame({
        "n_cust": d.groupby("vehicle_id")["customer_id"].nunique(),
        "runs": real_chg.groupby(d["vehicle_id"]).sum() + 1,
        "same_day": same_day.groupby(d["vehicle_id"]).sum(),
        "n_turnos": d.groupby("vehicle_id").size(),
    })
    out = out[out["n_cust"] > 1]
    out["patron"] = np.where(out["runs"] > out["n_cust"], "alternancia",
                             np.where(out["same_day"] > 0, "ambiguo", "secuencial"))
    return out


p_all = patron(a)
T("V1.2 Patrón temporal recalculado (todos los turnos, como el original)",
  p_all["patron"].value_counts().to_frame("vehículos").assign(pct=lambda d: (d["vehículos"] / d["vehículos"].sum()).map(pct)))

# Robustez: ¿el "cambio permanente" se sostiene si solo miramos turnos concluidos ((60)/(90))?
a_done = a[a["completed"] | a["completed_no_os"]]
p_done = patron(a_done)
T("V1.3 Patrón temporal usando SOLO turnos concluidos ((60) y (90))",
  p_done["patron"].value_counts().to_frame("vehículos").assign(pct=lambda d: (d["vehículos"] / d["vehículos"].sum()).map(pct)),
  note=f"{len(p_done):,} vehículos multi-cliente entre concluidos (vs {len(p_all):,} con todos los estados).")

# Robustez: en los secuenciales, ¿cuántos turnos tiene el cliente "nuevo" (último)? Si es 1 solo, la permanencia no es verificable.
seq_ids = p_all.index[p_all["patron"] == "secuencial"]
d = a[a["vehicle_id"].isin(seq_ids)]
last_c = d.groupby("vehicle_id")["customer_id"].last()
d = d.assign(es_ultimo=d["customer_id"].eq(d["vehicle_id"].map(last_c)))
per_last = d[d["es_ultimo"]].groupby("vehicle_id").agg(
    n_turnos_ultimo=("schedule_id", "size"),
    n_concl_ultimo=("completed", "sum"),
    n_maint_ultimo=("is_completed_maintenance", "sum"),
    ult_fecha=("event_date", "max"),
)
per_first = d[~d["es_ultimo"]].groupby("vehicle_id").agg(n_concl_prev=("completed", "sum"))
per_last = per_last.join(per_first)
T("V1.4 Secuenciales: turnos del cliente nuevo (último)", pd.DataFrame({
    "vehículos": [len(per_last), int((per_last["n_turnos_ultimo"] == 1).sum()), int((per_last["n_concl_ultimo"] == 0).sum()),
                  int((per_last["n_maint_ultimo"] == 0).sum()), int((per_last["n_concl_prev"] == 0).sum()),
                  int(((per_last["n_concl_ultimo"] > 0) & (per_last["n_concl_prev"] > 0)).sum()),
                  int((per_last["ult_fecha"] > CUTOFF).sum())],
    "pct": [pct(1), pct((per_last["n_turnos_ultimo"] == 1).mean()), pct((per_last["n_concl_ultimo"] == 0).mean()),
            pct((per_last["n_maint_ultimo"] == 0).mean()), pct((per_last["n_concl_prev"] == 0).mean()),
            pct(((per_last["n_concl_ultimo"] > 0) & (per_last["n_concl_prev"] > 0)).mean()),
            pct((per_last["ult_fecha"] > CUTOFF).mean())],
}, index=["secuenciales", "cliente nuevo con 1 solo turno", "cliente nuevo sin ningún turno (60) Concluido",
          "cliente nuevo sin mantenimiento completado", "cliente(s) anterior(es) sin ningún (60) Concluido",
          "ambos lados con >=1 (60) Concluido", "último turno del cliente nuevo es reserva futura (> CUTOFF)"]),
  note="'Cambio permanente' solo es verificable cuando ambos clientes tienen turnos efectivamente concluidos.")

# ==============================================================================================
# V2) Artefactos de identidad por canal
# ==============================================================================================
print("\n\n==================== V2) ARTEFACTOS POR CANAL ====================")
a["prev_cust"] = a.groupby("vehicle_id")["customer_id"].shift()
a["prev_src"] = a.groupby("vehicle_id")["ScheduleSource"].shift()
a["prev_dealer"] = a.groupby("vehicle_id")["dealer_id"].shift()
a["prev_date"] = a.groupby("vehicle_id")["event_date"].shift()
pairs = a[a["prev_cust"].notna()].copy()
pairs["switch"] = pairs["prev_cust"] != pairs["customer_id"]
pairs["src_chg"] = pairs["prev_src"] != pairs["ScheduleSource"]
pairs["cruce_dfp"] = ((pairs["prev_src"] == "Dealer") & (pairs["ScheduleSource"] == "FordPass")) | ((pairs["prev_src"] == "FordPass") & (pairs["ScheduleSource"] == "Dealer"))
pairs["multi"] = pairs["vehicle_id"].map(n_cust).gt(1)
T("V2.1 Cambio de canal en pares consecutivos: switch vs no-switch, y baseline en vehículos de un solo cliente", pd.DataFrame({
    "n pares": [int(pairs["switch"].sum()), int((~pairs["switch"] & pairs["multi"]).sum()), int((~pairs["multi"]).sum())],
    "cambia ScheduleSource": [pct(pairs.loc[pairs["switch"], "src_chg"].mean()), pct(pairs.loc[~pairs["switch"] & pairs["multi"], "src_chg"].mean()),
                              pct(pairs.loc[~pairs["multi"], "src_chg"].mean())],
    "cruce Dealer<->FordPass": [pct(pairs.loc[pairs["switch"], "cruce_dfp"].mean()), pct(pairs.loc[~pairs["switch"] & pairs["multi"], "cruce_dfp"].mean()),
                                pct(pairs.loc[~pairs["multi"], "cruce_dfp"].mean())],
}, index=["cambio de cliente", "sin cambio (vehículos multi-cliente)", "sin cambio (vehículos de 1 cliente)"]))

# a.6 controlando por n° de turnos (confusor obvio: más turnos => más chance de mezclar canal Y de tener 2 ids)
vs = a.groupby("vehicle_id").agg(n_turnos=("schedule_id", "size"), fp=("ScheduleSource", lambda x: x.eq("FordPass").any()),
                                 nofp=("ScheduleSource", lambda x: x.ne("FordPass").any()))
vs["mezcla"] = vs["fp"] & vs["nofp"]
vs["multi"] = n_cust.reindex(vs.index).gt(1)
vs = vs[vs["n_turnos"] >= 2]
vs["n_turnos_cat"] = pd.cut(vs["n_turnos"], [1, 2, 3, 5, 8, 10**6], labels=["2", "3", "4-5", "6-8", "9+"])
t26 = vs.pivot_table(index="n_turnos_cat", columns="mezcla", values="multi", aggfunc=["mean", "size"], observed=True)
t26.columns = ["% multi | un solo tipo de canal", "% multi | mezcla FP y no-FP", "n un solo tipo", "n mezcla"]
t26 = t26.iloc[:, :2].map(pct).join(t26.iloc[:, 2:].astype(int))
T("V2.2 % de vehículos multi-cliente según mezcla de canal, ESTRATIFICADO por n° de turnos", t26,
  note=f"Sin estratificar: mezcla {pct(vs.loc[vs['mezcla'], 'multi'].mean())} vs un solo tipo {pct(vs.loc[~vs['mezcla'], 'multi'].mean())}.")

# Test fuerte de artefacto: en vehículos vendidos (0 km, comprador = primer dueño), si el COMPRADOR aparece DESPUÉS de otro id,
# ese otro id no puede ser un dueño anterior: es un artefacto (id cargado por el dealer / pre-entrega / chofer).
buyer = sales_idx["customer_id"]
seq2 = p_all[(p_all["patron"] == "secuencial") & (p_all["n_cust"] == 2)].index
d2 = a[a["vehicle_id"].isin(seq2)]
first_c = d2.groupby("vehicle_id")["customer_id"].first()
last_c2 = d2.groupby("vehicle_id")["customer_id"].last()
chk = pd.DataFrame({"first": first_c, "last": last_c2})
chk["buyer"] = buyer.reindex(chk.index)
chk = chk[chk["buyer"].notna()]
chk["caso"] = np.select([chk["buyer"] == chk["first"], chk["buyer"] == chk["last"]],
                        ["comprador primero, otro después (transferencia o artefacto)", "OTRO primero, comprador DESPUÉS (artefacto seguro)"],
                        default="comprador no aparece")
T("V2.3 Secuenciales de 2 clientes en vehículos VENDIDOS 2024-26: ¿dónde está el comprador?",
  chk["caso"].value_counts().to_frame("vehículos").assign(pct=lambda d: (d["vehículos"] / d["vehículos"].sum()).map(pct)),
  note="Un vehículo vendido 0 km en 2024-26 no puede tener un dueño real anterior al comprador: si el comprador aparece segundo, el primer id es un artefacto.")
# ¿Cómo se ve el canal en esos artefactos seguros?
art = chk.index[chk["caso"].str.startswith("OTRO")]
sw_art = pairs[(pairs["vehicle_id"].isin(art)) & pairs["switch"]]
T("V2.4 Canal (anterior -> nuevo) en los cambios 'artefacto seguro' (otro -> comprador)",
  pd.crosstab(sw_art["prev_src"], sw_art["ScheduleSource"], margins=True))
# ¿El primer id "otro" es un turno pre-entrega (PDI / demo) o un uso real del vehículo ya vendido?
fo = a[a["vehicle_id"].isin(art)].groupby("vehicle_id").agg(first_date=("event_date", "min"), first_status=("StatusARG", "first"),
                                                            first_maint=("has_maint", "first"), first_src=("ScheduleSource", "first"))
fo["delivery"] = sales_idx["DeliveryDate"].reindex(fo.index)
fo["sale"] = sales_idx["SalesDate"].reindex(fo.index)
fo["dias_vs_entrega"] = (fo["first_date"] - fo["delivery"]).dt.days
T("V2.5 En los 'artefacto seguro': ¿cuándo ocurre el primer turno del id 'otro' respecto de la entrega?", pd.DataFrame({
    "vehículos": [len(fo), int((fo["dias_vs_entrega"] < 0).sum()), int(fo["dias_vs_entrega"].between(0, 30).sum()), int((fo["dias_vs_entrega"] > 30).sum()),
                  int((fo["dias_vs_entrega"] > 180).sum()), int(fo["first_maint"].sum()), int(fo["first_status"].eq("(60) Concluido").sum())],
    "pct": [pct(1), pct((fo["dias_vs_entrega"] < 0).mean()), pct(fo["dias_vs_entrega"].between(0, 30).mean()), pct((fo["dias_vs_entrega"] > 30).mean()),
            pct((fo["dias_vs_entrega"] > 180).mean()), pct(fo["first_maint"].mean()), pct(fo["first_status"].eq("(60) Concluido").mean())],
}, index=["artefactos seguros", "1er turno ANTES de DeliveryDate (pre-entrega)", "0-30 días después de la entrega", "> 30 días después",
          "> 180 días después", "1er turno incluye ítem de mantenimiento", "1er turno (60) Concluido"]),
  note="Si el 'otro' id usa el vehículo meses después de la entrega y hace mantenimientos, es un usuario real (chofer/familiar) con id distinto al comprador, no un turno de pre-entrega.")

# ==============================================================================================
# V3) Transferencias por año y edad: ¿"ocurren temprano" o el parque observado es joven?
# ==============================================================================================
print("\n\n==================== V3) TRANSFERENCIAS Y EDAD ====================")
n_veh_cust = a.groupby("customer_id")["vehicle_id"].nunique()
wsd = a.groupby("vehicle_id")["WarrantyStartDate"].first()
sw = pairs[pairs["switch"] & pairs["vehicle_id"].isin(p_all.index[p_all["patron"] == "secuencial"])].copy()
sw["cruce"] = sw["cruce_dfp"]
sw["flota_any"] = sw["customer_id"].map(n_veh_cust).ge(3) | sw["prev_cust"].map(n_veh_cust).ge(3)
sw["nivel_i"] = True
sw["nivel_ii"] = ~sw["cruce"]
sw["nivel_iii"] = ~sw["cruce"] & ~sw["flota_any"]
sw["anio"] = sw["event_date"].dt.year
sw["edad"] = (sw["event_date"] - sw["vehicle_id"].map(wsd)).dt.days / 365.25
veh2025 = a.loc[a["event_date"].dt.year == 2025, "vehicle_id"].nunique()
veh2025_hist = a_hist.loc[a_hist["event_date"].dt.year == 2025, "vehicle_id"].nunique()
T("V3.1 Transferencias 2025 por nivel (recalculado) y tasa sobre vehículos con turno en 2025", pd.DataFrame({
    "cambios totales": [int(sw["nivel_i"].sum()), int(sw["nivel_ii"].sum()), int(sw["nivel_iii"].sum())],
    "2025": [int((sw["nivel_i"] & (sw["anio"] == 2025)).sum()), int((sw["nivel_ii"] & (sw["anio"] == 2025)).sum()), int((sw["nivel_iii"] & (sw["anio"] == 2025)).sum())],
    "tasa 2025": [pct((sw["nivel_i"] & (sw["anio"] == 2025)).sum() / veh2025), pct((sw["nivel_ii"] & (sw["anio"] == 2025)).sum() / veh2025),
                  pct((sw["nivel_iii"] & (sw["anio"] == 2025)).sum() / veh2025)],
    "edad mediana": [round(sw.loc[sw["nivel_i"], "edad"].median(), 2), round(sw.loc[sw["nivel_ii"], "edad"].median(), 2), round(sw.loc[sw["nivel_iii"], "edad"].median(), 2)],
}, index=["(i)", "(ii)", "(iii)"]), note=f"vehículos con turno en 2025: {veh2025:,} (== {veh2025_hist:,} con event_date <= CUTOFF)")

# Denominador alternativo: vehículos con >=2 turnos (solo ahí se puede detectar un cambio).
veh_2plus = a.groupby("vehicle_id").size()
veh2025_2plus = a.loc[(a["event_date"].dt.year == 2025) & a["vehicle_id"].map(veh_2plus).ge(2), "vehicle_id"].nunique()
T("V3.2 Tasa 2025 con denominador 'vehículos con turno en 2025 y >=2 turnos en total'", pd.DataFrame({
    "valor": [veh2025_2plus, pct((sw["nivel_iii"] & (sw["anio"] == 2025)).sum() / veh2025_2plus), pct((sw["nivel_i"] & (sw["anio"] == 2025)).sum() / veh2025_2plus)]},
    index=["vehículos", "tasa nivel iii", "tasa nivel i"]))

# Hazard por edad: transferencias 2025 (nivel iii) por franja de edad / vehículos activos en 2025 por franja de edad (edad al 2025-07-01).
act25 = a[a["event_date"].dt.year == 2025].groupby("vehicle_id").size().index
edad_act = ((pd.Timestamp("2025-07-01") - wsd.reindex(act25)).dt.days / 365.25)
bins = [-1, 1, 2, 3, 4, 5, 7, 10, 100]
lbl = ["<1", "1-2", "2-3", "3-4", "4-5", "5-7", "7-10", "10+"]
den = pd.cut(edad_act, bins, labels=lbl).value_counts().sort_index()
num = pd.cut(sw.loc[sw["nivel_iii"] & (sw["anio"] == 2025), "edad"], bins, labels=lbl).value_counts().sort_index()
haz = pd.DataFrame({"transferencias 2025 (iii)": num, "% de las transferencias": (num / num.sum()).map(pct),
                    "vehículos activos 2025": den, "% del parque activo": (den / den.sum()).map(pct),
                    "tasa por vehículo-año": (num / den).map(pct)})
T("V3.3 Transferencias 2025 (nivel iii) por edad del vehículo vs composición del parque activo: hazard por edad", haz,
  note="Si la tasa por vehículo-año es plana o creciente, 'ocurren temprano' refleja que el parque observado es joven, no una propensión mayor a transferirse a los 2-3 años.")
num_i = pd.cut(sw.loc[sw["nivel_i"] & (sw["anio"] == 2025), "edad"], bins, labels=lbl).value_counts().sort_index()
# denominador más justo: vehículos activos en 2025 con >=2 turnos en total (donde un cambio es detectable)
act25_2 = a.loc[(a["event_date"].dt.year == 2025) & a["vehicle_id"].map(veh_2plus).ge(2), "vehicle_id"].unique()
den2 = pd.cut(((pd.Timestamp("2025-07-01") - wsd.reindex(act25_2)).dt.days / 365.25), bins, labels=lbl).value_counts().sort_index()
T("V3.4 Hazard por edad, nivel (i) y (iii), con denominador 'activos 2025 con >=2 turnos'", pd.DataFrame({
    "activos 2025 (>=2 turnos)": den2, "tasa nivel i": (num_i / den2).map(pct), "tasa nivel iii": (num / den2).map(pct)}))

# ==============================================================================================
# V4) Comprador vs agenda
# ==============================================================================================
print("\n\n==================== V4) COMPRADOR VS AGENDA ====================")
custs = a.groupby("vehicle_id")["customer_id"].agg(set)
last_cust = a_hist.groupby("vehicle_id")["customer_id"].last()
first_cust = a.groupby("vehicle_id")["customer_id"].first()
sv = sales[sales["vehicle_id"].isin(custs.index)].copy()
sv["en_agenda"] = [b in c for b, c in zip(sv["customer_id"], sv["vehicle_id"].map(custs))]
sv["es_ultimo"] = sv["customer_id"].values == sv["vehicle_id"].map(last_cust).values
sv["es_primero"] = sv["customer_id"].values == sv["vehicle_id"].map(first_cust).values
sv["sin_hist"] = sv["vehicle_id"].map(last_cust).isna()
T("V4.1 Comprador en la agenda de su vehículo (recalculado)", pd.DataFrame({
    "vehículos": [len(sv), int(sv["en_agenda"].sum()), int(sv["es_primero"].sum()), int(sv["es_ultimo"].sum()), int(sv["sin_hist"].sum()),
                  int(sv.loc[~sv["sin_hist"], "es_ultimo"].sum())],
    "pct": [pct(1), pct(sv["en_agenda"].mean()), pct(sv["es_primero"].mean()), pct(sv["es_ultimo"].mean()), pct(sv["sin_hist"].mean()),
            pct(sv.loc[~sv["sin_hist"], "es_ultimo"].mean())],
}, index=["vendidos con turnos (customer_id no nulo)", "comprador aparece", "comprador es primero", "comprador es último (<= CUTOFF)",
          "vehículos cuyo único turno es reserva futura (> CUTOFF): último = NaN", "comprador es último, excluyendo los sin historia <= CUTOFF"]))
T("V4.2 % comprador en agenda por PersonType y canal (recalculado)", pd.concat([
    sv.groupby("PersonType")["en_agenda"].agg(n="size", tasa="mean"), sv.groupby("SalesChannel")["en_agenda"].agg(n="size", tasa="mean"),
    sv.groupby("BusinessUnit")["en_agenda"].agg(n="size", tasa="mean")]).assign(tasa=lambda d: d["tasa"].map(pct)))
hr = sales[sales["SalesChannel"] == "HR"]["customer_id"].value_counts()
p25 = sales[sales["PersonType"] == "25"]["customer_id"].value_counts()
T("V4.3 HR / PersonType 25: concentración (recalculado)", pd.DataFrame({
    "ventas": [int(hr.sum()), int(p25.sum())], "top id ventas": [int(hr.iloc[0]), int(p25.iloc[0])],
    "mismo id": [hr.index[0] == p25.index[0]] * 2}, index=["HR", "PersonType 25"]))

# ==============================================================================================
# V5) Proxy retorno_15m: es_comprador, mismo_dealer, calidad del proxy
# ==============================================================================================
print("\n\n==================== V5) PROXY DE RETORNO ====================")
cm = a[a["is_completed_maintenance"]].copy()
cm["next"] = cm.groupby("vehicle_id")["event_date"].shift(-1)
cm["gap_next"] = (cm["next"] - cm["event_date"]).dt.days
ev = cm[(cm["event_date"] <= CUTOFF - pd.Timedelta(days=456)) & (cm["event_date"] >= "2024-01-01")].copy()
ev["ret15"] = ev["gap_next"].le(456).fillna(False)
ev["buyer"] = ev["vehicle_id"].map(buyer)
ev["es_comprador"] = np.select([ev["buyer"].isna(), ev["customer_id"] == ev["buyer"]], ["sin venta", "comprador"], default="otro")
ev["person_type"] = ev["vehicle_id"].map(sales_idx["PersonType"])
ev["bu"] = ev["vehicle_id"].map(sales_idx["BusinessUnit"])
T("V5.1 Base del proxy (recalculado)", pd.DataFrame({"valor": [len(ev), ev["vehicle_id"].nunique(), pct(ev["ret15"].mean())]},
                                                    index=["eventos", "vehículos", "retorno_15m"]))
T("V5.2 retorno_15m por es_comprador (recalculado), total y por PersonType / BusinessUnit", pd.concat([
    ev.groupby("es_comprador")["ret15"].agg(n="size", tasa="mean"),
    ev[ev["es_comprador"] != "sin venta"].groupby(["person_type", "es_comprador"])["ret15"].agg(n="size", tasa="mean"),
    ev[ev["es_comprador"] != "sin venta"].groupby(["bu", "es_comprador"])["ret15"].agg(n="size", tasa="mean"),
]).assign(tasa=lambda d: d["tasa"].map(pct)))
# ¿Retornos espurios? Un "retorno" a pocos días es un turno duplicado / reprogramado, no un service siguiente.
T("V5.3 Gap al siguiente mantenimiento completado entre los eventos con retorno=1 (calidad del proxy)", pd.DataFrame({
    "eventos": [int(ev["ret15"].sum()), int(ev["gap_next"].le(7).sum()), int(ev["gap_next"].le(30).sum()), int(ev["gap_next"].le(90).sum())],
    "% de los eventos": [pct(ev["ret15"].mean()), pct(ev["gap_next"].le(7).mean()), pct(ev["gap_next"].le(30).mean()), pct(ev["gap_next"].le(90).mean())],
}, index=["retorno_15m = 1", "gap <= 7 días", "gap <= 30 días", "gap <= 90 días"]),
  note="Un 'retorno' a <= 30 días no es el próximo mantenimiento programado; infla el proxy (afecta a todos los temas, no solo a este).")
ev["ret15_strict"] = ev["gap_next"].between(31, 456).fillna(False)  # excluye re-visitas a <=30 días
# Recalcular es_comprador con proxy que salte los retornos a <=30 días (siguiente mantenimiento a >30 días).
cm2 = cm.copy()
nxt = []
grp = cm2.groupby("vehicle_id")["event_date"]
# siguiente mantenimiento a más de 30 días: usar merge_asof por vehículo
cm2 = cm2.sort_values("event_date")
tmp = cm2[["vehicle_id", "event_date"]].copy()
tmp["t30"] = tmp["event_date"] + pd.Timedelta(days=30)
nx = pd.merge_asof(tmp.sort_values("t30"), cm2[["vehicle_id", "event_date"]].rename(columns={"event_date": "next30"}).sort_values("next30"),
                   left_on="t30", right_on="next30", by="vehicle_id", direction="forward", allow_exact_matches=False)
nx.index = tmp.sort_values("t30").index
ev["next30"] = nx["next30"].reindex(ev.index)
ev["ret15_30"] = (ev["next30"] - ev["event_date"]).dt.days.le(456).fillna(False)
T("V5.4 retorno_15m 'limpio' (siguiente mantenimiento a > 30 días) por es_comprador", pd.concat([
    ev.groupby("es_comprador")["ret15_30"].agg(n="size", tasa="mean"),
    ev[ev["es_comprador"] != "sin venta"].groupby(["person_type", "es_comprador"])["ret15_30"].agg(n="size", tasa="mean")]).assign(tasa=lambda d: d["tasa"].map(pct)),
  note=f"Base limpia = {pct(ev['ret15_30'].mean())}.")
# mismo dealer que venta y 1er mantenimiento en dealer vendedor
da = set(a["dealer_id"].dropna())
ev["sale_dealer"] = ev["vehicle_id"].map(sales_idx["dealer_id"])
ev["mismo_dealer"] = np.select([ev["sale_dealer"].isna() | ~ev["sale_dealer"].isin(da), ev["dealer_id"] == ev["sale_dealer"]], ["n/a", "sí"], default="no")
T("V5.5 retorno_15m por mismo_dealer_que_venta (recalculado)", ev.groupby("mismo_dealer")[["ret15", "ret15_30"]].agg(["size", "mean"]).pipe(
    lambda t: pd.DataFrame({"n": t[("ret15", "size")], "retorno_15m": t[("ret15", "mean")].map(pct), "retorno_15m limpio": t[("ret15_30", "mean")].map(pct)})))
fmd = cm.sort_values(["vehicle_id", "event_date"]).groupby("vehicle_id").agg(first_dealer=("dealer_id", "first"), first_date=("event_date", "min"))
b2 = sales[["vehicle_id", "dealer_id"]].merge(fmd, left_on="vehicle_id", right_index=True)
b2["mismo"] = b2["dealer_id"] == b2["first_dealer"]
b2["en_agenda"] = b2["dealer_id"].isin(da)
T("V5.6 1er mantenimiento completado en el dealer vendedor (recalculado)", pd.DataFrame({
    "vehículos": [len(b2), int(b2["en_agenda"].sum())], "% mismo dealer": [pct(b2["mismo"].mean()), pct(b2.loc[b2["en_agenda"], "mismo"].mean())]},
    index=["todos", "dealer vendedor en agenda"]))

# ==============================================================================================
# V6) Flotas: tamaño por sales vs agenda vs combinado
# ==============================================================================================
print("\n\n==================== V6) FLOTAS ====================")
nv_sales = sales.groupby("customer_id")["vehicle_id"].nunique()
sales["tam_sales"] = sales["customer_id"].map(nv_sales)
sales["tam_agenda"] = sales["customer_id"].map(n_veh_cust).fillna(0)
# combinado: vehículos distintos del comprador en sales ∪ agenda
pares = pd.concat([sales[["customer_id", "vehicle_id"]], a[["customer_id", "vehicle_id"]]]).drop_duplicates()
nv_comb = pares.groupby("customer_id")["vehicle_id"].nunique()
sales["tam_comb"] = sales["customer_id"].map(nv_comb)
fc = lambda s: pd.cut(s, [0, 1, 2, 9, 49, 10**6], labels=["1", "2", "3-9", "10-49", "50+"])
T("V6.1 Ventas por tamaño de flota del comprador: sales solo vs combinado (sales ∪ agenda)",
  pd.crosstab(fc(sales["tam_sales"]), fc(sales["tam_comb"]), margins=True),
  note=f"Flota (>=3) por sales: {pct(sales['tam_sales'].ge(3).mean())} de las ventas; por combinado: {pct(sales['tam_comb'].ge(3).mean())}. "
       f"Compradores '1 vehículo' en sales que tienen >=3 en la agenda: {int((sales['tam_sales'].eq(1) & sales['tam_agenda'].ge(3)).sum()):,} ventas.")
T("V6.2 % Ford Pro por tamaño de flota (sales) y % de cada BU que es flota (recalculado)", pd.concat([
    pd.crosstab(fc(sales["tam_sales"]), sales["BusinessUnit"], normalize="index").map(pct),
    pd.crosstab(fc(sales["tam_comb"]), sales["BusinessUnit"], normalize="index").map(pct).add_prefix("comb: ")], axis=1),
  note=f"Ford Pro con flota>=3 (sales): {pct(sales.loc[sales['BusinessUnit']=='Ford Pro','tam_sales'].ge(3).mean())}; (comb): "
       f"{pct(sales.loc[sales['BusinessUnit']=='Ford Pro','tam_comb'].ge(3).mean())}. Ford Blue flota (sales): {pct(sales.loc[sales['BusinessUnit']=='Ford Blue','tam_sales'].ge(3).mean())}; "
       f"(comb): {pct(sales.loc[sales['BusinessUnit']=='Ford Blue','tam_comb'].ge(3).mean())}. J con 1 vehículo (sales): {int((sales['PersonType'].eq('J') & sales['tam_sales'].eq(1)).sum()):,} "
       f"({pct((sales['PersonType'].eq('J') & sales['tam_sales'].eq(1)).sum() / sales['PersonType'].eq('J').sum())}); (comb): "
       f"{int((sales['PersonType'].eq('J') & sales['tam_comb'].eq(1)).sum()):,} ({pct((sales['PersonType'].eq('J') & sales['tam_comb'].eq(1)).sum() / sales['PersonType'].eq('J').sum())}).")

# ==============================================================================================
# V7) Flotas: entrada, curva por año de vida, retorno condicional
# ==============================================================================================
print("\n\n==================== V7) FLOTAS: ENTRADA Y RETORNO ====================")
sales["meses_wsd"] = (CUTOFF - sales["WarrantyStartDate"]).dt.days / 30.44
s15 = sales[sales["meses_wsd"] >= 15].copy()
s15["first_maint"] = s15["vehicle_id"].map(fmd["first_date"])
s15["r1"] = ((s15["first_maint"] - s15["WarrantyStartDate"]).dt.days <= 456).fillna(False)
# alternativa: primer turno CONCLUIDO de cualquier tipo (no solo mantenimiento) dentro de 15 meses
fdone = a[a["completed"]].groupby("vehicle_id")["event_date"].min()
s15["first_done"] = s15["vehicle_id"].map(fdone)
s15["r1_any"] = ((s15["first_done"] - s15["WarrantyStartDate"]).dt.days <= 456).fillna(False)
T("V7.1 Vendidos con >=15 meses: 1er mantenimiento completado en 15 m por tamaño de flota (sales y combinado) y BU", pd.concat([
    s15.groupby(fc(s15["tam_sales"]), observed=True)["r1"].agg(n="size", tasa="mean"),
    s15.groupby(fc(s15["tam_comb"]), observed=True)["r1"].agg(n="size", tasa="mean").rename(index=lambda x: f"comb {x}"),
    s15.groupby("BusinessUnit")["r1"].agg(n="size", tasa="mean")]).assign(tasa=lambda d: d["tasa"].map(pct)),
  note=f"Total {pct(s15['r1'].mean())} sobre {len(s15):,}. Con 'cualquier turno concluido en 15 m': {pct(s15['r1_any'].mean())}.")

# Curva por año de vida, recalculada de forma independiente (grupo = tamaño de flota del cliente vigente, agenda).
veh = pd.DataFrame({"cust": last_cust})
veh["tam"] = veh["cust"].map(n_veh_cust)
veh["grupo"] = np.where(veh["tam"] >= 3, "flota", np.where(veh["tam"] == 2, "dos", "particular"))
veh["wsd"] = wsd.reindex(veh.index)
veh = veh.dropna(subset=["wsd"])
cmh = cm[cm["event_date"] <= CUTOFF].copy()
cmh["wsd"] = cmh["vehicle_id"].map(wsd)
cmh["k"] = np.floor((cmh["event_date"] - cmh["wsd"]).dt.days / 365.25) + 1
has_k = cmh.dropna(subset=["k"]).groupby(["vehicle_id", "k"]).size()
rows = []
for k in range(1, 9):
    st = veh["wsd"] + pd.Timedelta(days=(k - 1) * 365.25)
    en = veh["wsd"] + pd.Timedelta(days=k * 365.25)
    sub = veh[(st >= pd.Timestamp("2024-01-01")) & (en <= CUTOFF)].copy()
    sub["k"] = float(k)
    sub["hizo"] = pd.MultiIndex.from_arrays([sub.index, sub["k"]]).isin(has_k.index)
    rows.append(sub)
yl = pd.concat(rows)
c6 = yl.pivot_table(index="k", columns="grupo", values="hizo", aggfunc=["mean", "size"])
T("V7.2 % con mantenimiento completado por año de vida (recalculado)", c6["mean"].map(pct).join(c6["size"].add_prefix("n ")))
# Sesgo de supervivencia en años 1-2: incluir vendidos que NUNCA vinieron (solo posible para WSD >= 2024 desde sales).
sold = sales.dropna(subset=["WarrantyStartDate"]).set_index("vehicle_id")
sold["grupo"] = np.where(sold["tam_comb"] >= 3, "flota", np.where(sold["tam_comb"] == 2, "dos", "particular"))
rows = []
for k in (1, 2):
    en = sold["WarrantyStartDate"] + pd.Timedelta(days=k * 365.25)
    sub = sold[(sold["WarrantyStartDate"] >= "2024-01-01") & (en <= CUTOFF)].copy()
    sub["k"] = float(k)
    sub["hizo"] = pd.MultiIndex.from_arrays([sub.index, sub["k"]]).isin(has_k.index)
    rows.append(sub)
yl2 = pd.concat(rows)
c6b = yl2.pivot_table(index="k", columns="grupo", values="hizo", aggfunc=["mean", "size"])
T("V7.3 Años 1 y 2 desde SALES (incluye vendidos que nunca tuvieron turno; grupo = flota combinada)", c6b["mean"].map(pct).join(c6b["size"].add_prefix("n ")),
  note="Compara con V7.2: la población 'con al menos un turno' infla el año 1-2, sobre todo en flotas.")

# Retorno condicional por edad: flota as-of (truncada en 2024-01) vs flota de período completo.
ev["edad"] = (ev["event_date"] - ev["vehicle_id"].map(wsd)).dt.days / 365.25
ev["edad_cat"] = pd.cut(ev["edad"], [-1, 2, 4, 100], labels=["<2", "2-4", "4+"])
ev["tam_full"] = pd.cut(ev["customer_id"].map(n_veh_cust), [0, 1, 2, 9, 10**6], labels=["1", "2", "3-9", "10+"])
ac = a[["customer_id", "vehicle_id", "event_date"]].sort_values(["customer_id", "event_date"])
ac["nuevo"] = ~ac.duplicated(["customer_id", "vehicle_id"])
a["tam_asof"] = ac.groupby("customer_id")["nuevo"].cumsum().reindex(a.index)
ev["tam_asof"] = pd.cut(a["tam_asof"].reindex(ev.index), [0, 1, 2, 9, 10**6], labels=["1", "2", "3-9", "10+"])
for nm, col in [("as-of (como el original)", "tam_asof"), ("período completo", "tam_full")]:
    t = ev.pivot_table(index=col, columns="edad_cat", values="ret15", aggfunc=["mean", "size"], observed=True)
    T(f"V7.4 retorno_15m por tamaño de flota [{nm}] x edad del vehículo", t["mean"].map(pct).join(t["size"].add_prefix("n ")))
T("V7.5 Cruce: tamaño de flota as-of vs período completo en los eventos del proxy (cuántos 'flota' quedan como '1' por truncamiento)",
  pd.crosstab(ev["tam_asof"], ev["tam_full"], margins=True))
# canal/no-show por grupo (turno-nivel)
a["grupo_t"] = np.where(a["customer_id"].map(n_veh_cust) >= 3, "flota", np.where(a["customer_id"].map(n_veh_cust) == 2, "dos", "particular"))
ah = a[a["event_date"] <= CUTOFF]
T("V7.6 Turnos por grupo: no-show, cancelado, FordPass (recalculado)", ah.groupby("grupo_t").agg(
    turnos=("schedule_id", "size"), no_show=("no_show", "mean"), cancelado=("cancelled", "mean"), fordpass=("ScheduleSource", lambda x: x.eq("FordPass").mean()))
  .assign(no_show=lambda d: d["no_show"].map(pct), cancelado=lambda d: d["cancelado"].map(pct), fordpass=lambda d: d["fordpass"].map(pct)))

# ==============================================================================================
# V8) Dealers
# ==============================================================================================
print("\n\n==================== V8) DEALERS ====================")
ds = set(sales["dealer_id"].dropna())
T("V8.1 Overlap de dealer_id (recalculado)", pd.DataFrame({"valor": [len(ds), len(da), len(ds & da), len(ds - da), len(da - ds),
                                                                     pct(sales["dealer_id"].isin(da).mean()), pct(a["dealer_id"].isin(ds).mean()),
                                                                     pct(ap["dealer_id"].isin(ds).mean())]},
                                                          index=["sales", "agenda", "ambas", "solo sales", "solo agenda", "% ventas con dealer en agenda",
                                                                 "% turnos (base) con dealer en sales", "% turnos (todos) con dealer en sales"]))
first_dealer = a.groupby("vehicle_id")["dealer_id"].first()
sd = sales[["vehicle_id", "dealer_id"]].dropna()
sd["fd"] = sd["vehicle_id"].map(first_dealer)
sd = sd.dropna()
rows = []
for dlr, g in sd.groupby("dealer_id"):
    vc = g["fd"].value_counts(normalize=True)
    rows.append({"dealer_id": dlr, "n": len(g), "en_agenda": dlr in da, "top": vc.index[0], "share_top": vc.iloc[0],
                 "top_es_mismo": vc.index[0] == dlr, "top_es_solo_agenda": vc.index[0] in (da - ds), "share_2do": vc.iloc[1] if len(vc) > 1 else 0})
conc = pd.DataFrame(rows).set_index("dealer_id")
T("V8.2 Concentración del dealer del 1er turno por dealer vendedor: ausentes vs presentes", conc.groupby("en_agenda").agg(
    dealers=("n", "size"), ventas=("n", "sum"), share_top_mediana=("share_top", "median"), share_top_p25=("share_top", lambda x: x.quantile(.25)),
    share_top_p75=("share_top", lambda x: x.quantile(.75)), top_es_mismo_id=("top_es_mismo", "mean"), top_es_dealer_solo_agenda=("top_es_solo_agenda", "mean")))
absn = conc[~conc["en_agenda"]].sort_values("n", ascending=False)
T("V8.3 Dealers vendedores ausentes: ¿su destino principal es un dealer que existe solo en la agenda (34) o uno compartido (61)?",
  pd.DataFrame({"dealers ausentes": [len(absn)], "ventas": [absn["n"].sum()],
                "top = dealer solo-agenda (dealers)": [int(absn["top_es_solo_agenda"].sum())],
                "top = dealer solo-agenda (% ventas)": [pct(absn.loc[absn["top_es_solo_agenda"], "n"].sum() / absn["n"].sum())],
                "destinos top distintos": [absn["top"].nunique()],
                "dealers ausentes con share_top >= 50%": [int((absn["share_top"] >= .5).sum())],
                "ventas de ausentes con share_top >= 50%": [pct(absn.loc[absn["share_top"] >= .5, "n"].sum() / absn["n"].sum())]}).T.rename(columns={0: "valor"}))
T("V8.4 Los 10 ausentes con más ventas: destino principal y si ese destino es solo-agenda", absn.head(10)[["n", "top", "share_top", "share_2do", "top_es_solo_agenda"]]
  .assign(share_top=lambda d: d["share_top"].map(pct), share_2do=lambda d: d["share_2do"].map(pct)))
# ¿varios ausentes comparten el mismo destino? (si el mapeo fuera 1:1 no debería pasar)
dup_top = absn.groupby("top").agg(n_ausentes=("n", "size"), ventas=("n", "sum")).sort_values("n_ausentes", ascending=False)
T("V8.5 Destinos principales compartidos por más de un dealer ausente", dup_top[dup_top["n_ausentes"] > 1])

# ==============================================================================================
# V9) Vista consolidada: ventanas coincidentes
# ==============================================================================================
print("\n\n==================== V9) VISTA CONSOLIDADA ====================")
act = a_hist[a_hist["event_date"] >= "2025-01-01"]
veh_vig = last_cust.to_frame("cust")
veh_vig["activo"] = veh_vig.index.isin(set(act["vehicle_id"]))
vc = veh_vig[veh_vig["activo"]].groupby("cust").size()
T("V9.1 Clientes vigentes con vehículos activos 2025-26 (recalculado)", pd.DataFrame({"valor": [
    len(vc), int((vc >= 2).sum()), pct((vc >= 2).mean()), int(vc[vc >= 2].sum()), pct(vc[vc >= 2].sum() / vc.sum())]},
    index=["clientes vigentes", "con >=2 vehículos", "% clientes", "vehículos en ellos", "% vehículos activos"]))
# (a) como el original: SOLO el último mantenimiento + 12 m
lastm = cmh.groupby("vehicle_id")["event_date"].max().to_frame("d")
lastm["cust"] = last_cust.reindex(lastm.index)
lastm["mes"] = (lastm["d"] + pd.DateOffset(months=12)).dt.to_period("M")
ga = lastm.groupby(["cust", "mes"]).size()
per = (pd.Period("2025-09", "M"), pd.Period("2026-08", "M"))
in_per = lastm["mes"].between(*per)
ga_p = ga[(ga.index.get_level_values("mes") >= per[0]) & (ga.index.get_level_values("mes") <= per[1])]
# (b) corregido: TODOS los mantenimientos completados + 12 m, cliente = el del turno; ventanas en 2025-09 -> 2026-08
allm = cmh[["vehicle_id", "customer_id", "event_date"]].copy()
allm["mes"] = (allm["event_date"] + pd.DateOffset(months=12)).dt.to_period("M")
allm = allm[allm["mes"].between(*per)].drop_duplicates(["vehicle_id", "mes"])
gb = allm.groupby(["customer_id", "mes"])["vehicle_id"].nunique()
# (c) corregido con cliente VIGENTE (último <= CUTOFF) en vez del cliente del turno
allm["cust_vig"] = allm["vehicle_id"].map(last_cust)
gc = allm.groupby(["cust_vig", "mes"])["vehicle_id"].nunique()
T("V9.2 Vehículos que entran en ventana 2025-09 → 2026-08 y coincidencia por cliente: método original vs corregido", pd.DataFrame({
    "original (solo último mantenimiento)": [int(in_per.sum()), int(ga_p[ga_p >= 2].sum()), pct(ga_p[ga_p >= 2].sum() / in_per.sum()),
                                             ga_p[ga_p >= 2].index.get_level_values("cust").nunique()],
    "corregido (todos los mantenimientos, cliente del turno)": [len(allm), int(gb[gb >= 2].sum()), pct(gb[gb >= 2].sum() / len(allm)),
                                                                gb[gb >= 2].index.get_level_values("customer_id").nunique()],
    "corregido (todos, cliente vigente)": [len(allm), int(gc[gc >= 2].sum()), pct(gc[gc >= 2].sum() / len(allm)),
                                           gc[gc >= 2].index.get_level_values("cust_vig").nunique()],
}, index=["vehículos-ventana en el período", "de clientes con >=2 el mismo mes", "% coincidencia", "clientes con >=2 el mismo mes"]),
  note="El método original toma el ÚLTIMO mantenimiento al CUTOFF: un vehículo que volvió corre su ventana al futuro y desaparece del período. "
       "Subestima las ventanas de los meses más viejos y sesga la población hacia los que NO volvieron.")
mm = pd.DataFrame({"original": lastm[in_per].groupby("mes").size(), "corregido": allm.groupby("mes").size()})
T("V9.3 Vehículos que entran en ventana por mes: original vs corregido", mm)

# ==============================================================================================
# V10) Vendidos que nunca aparecen
# ==============================================================================================
print("\n\n==================== V10) NUNCA VINIERON ====================")
sales["en_agenda_any"] = sales["vehicle_id"].isin(set(ap["vehicle_id"].dropna()))
sales["algun_concluido"] = sales["vehicle_id"].isin(set(a.loc[a["completed"] | a["completed_no_os"], "vehicle_id"]))
sales["algun_maint"] = sales["vehicle_id"].isin(set(cm["vehicle_id"]))
so = sales[~sales["en_agenda_any"]]
T("V10.1 Vendidos sin ningún turno (recalculado)", pd.DataFrame({"valor": [
    len(so), pct((so["meses_wsd"] < 12).mean()), pct((so["meses_wsd"] < 12).sum() / so["meses_wsd"].notna().sum()), int((so["meses_wsd"] >= 12).sum()),
    int((so["meses_wsd"] >= 15).sum()), int((sales["meses_wsd"] >= 15).sum()), pct((so["meses_wsd"] >= 15).sum() / (sales["meses_wsd"] >= 15).sum()),
    round(so["meses_wsd"].median(), 1)]},
    index=["sin turno", "% <12 meses (sobre 17.173, NaN cuenta como no)", "% <12 meses (sobre los con WSD)", ">=12 meses", ">=15 meses",
           "vendidos con >=15 meses", "% nunca / vendidos >=15 m", "mediana meses"]))
s15b = sales[sales["meses_wsd"] >= 15]
T("V10.2 Vendidos con >=15 meses: tres definiciones de 'nunca vino'", pd.DataFrame({
    "vehículos": [len(s15b), int((~s15b["en_agenda_any"]).sum()), int((~s15b["algun_concluido"]).sum()), int((~s15b["algun_maint"]).sum()),
                  int((s15b["en_agenda_any"] & ~s15b["algun_concluido"]).sum())],
    "pct": [pct(1), pct((~s15b["en_agenda_any"]).mean()), pct((~s15b["algun_concluido"]).mean()), pct((~s15b["algun_maint"]).mean()),
            pct((s15b["en_agenda_any"] & ~s15b["algun_concluido"]).mean())],
}, index=["vendidos >=15 m", "sin NINGÚN turno (ni cancelado)", "sin ningún turno concluido (60/90)", "sin ningún mantenimiento completado",
          "en la agenda pero solo con cancelados / no-show / pendientes"]),
  note="'Elegible y nunca vino' depende de la definición: 9,9 % (sin ningún turno), 11,7 % (sin turno concluido), 15,9 % (sin mantenimiento completado nunca); "
       "y 22,8 % si se exige el 1er mantenimiento DENTRO de los 15 meses (complemento del 77,2 % de f.4).")
T("V10.3 Vendidos >=15 m: % sin ningún turno por segmento (recalculado)", pd.concat([
    s15b.groupby("BusinessUnit")["en_agenda_any"].agg(n="size", t=lambda x: 1 - x.mean()),
    s15b.groupby("SalesChannel")["en_agenda_any"].agg(n="size", t=lambda x: 1 - x.mean()),
    s15b.groupby(fc(s15b["tam_sales"]), observed=True)["en_agenda_any"].agg(n="size", t=lambda x: 1 - x.mean())]).assign(t=lambda d: d["t"].map(pct)))

# ==============================================================================================
# V11) KM snapshot
# ==============================================================================================
print("\n\n==================== V11) KM SNAPSHOT ====================")
k = ap.dropna(subset=["vehicle_id"]).groupby("vehicle_id").agg(km_nu=("KM", "nunique"), km_nn=("KM", "count"),
                                                                vck_nu=("VehicleCurrentKM", "nunique"), vck_nn=("VehicleCurrentKM", "count"))
T("V11.1 KM / VehicleCurrentKM constantes por vehículo (nivel turno, recalculado)", pd.DataFrame({
    "vehículos con >=2 valores": [int((k["km_nn"] >= 2).sum()), int((k["vck_nn"] >= 2).sum())],
    "% constante": [pct((k.loc[k["km_nn"] >= 2, "km_nu"] == 1).mean(), 2), pct((k.loc[k["vck_nn"] >= 2, "vck_nu"] == 1).mean(), 2)]}, index=["KM", "VehicleCurrentKM"]))
# Nivel fila (agenda cruda, sin colapsar): mismo chequeo
raw = load_agenda()[["vehicle_id", "KM", "VehicleCurrentKM", "ScheduleDate", "EffectiveCheckinDate", "schedule_id"]].dropna(subset=["vehicle_id"])
kr = raw.groupby("vehicle_id")["KM"].agg(["nunique", "count"])
T("V11.2 KM constante por vehículo a nivel FILA (agenda cruda)", pd.DataFrame({"valor": [int((kr["count"] >= 2).sum()), pct((kr.loc[kr["count"] >= 2, "nunique"] == 1).mean(), 2)]},
                                                                             index=["vehículos con >=2 filas con KM", "% con un único KM"]))
# ¿KM == VehicleCurrentKM del último turno con VCK? ¿== max(VCK)?
h = ap.dropna(subset=["vehicle_id", "VehicleCurrentKM"]).sort_values(["vehicle_id", "event_date", "schedule_id"])
lastv = h.groupby("vehicle_id").agg(vck_last=("VehicleCurrentKM", "last"), vck_max=("VehicleCurrentKM", "max"), km=("KM", "first"), n=("VehicleCurrentKM", "size"))
lastv = lastv.dropna(subset=["km"])
T("V11.3 ¿KM coincide con VehicleCurrentKM del último turno / con el máximo? (vehículos con KM y >=1 VCK)", pd.DataFrame({
    "vehículos": [len(lastv), int((lastv["km"] == lastv["vck_last"]).sum()), int((lastv["km"] == lastv["vck_max"]).sum()),
                  int((lastv["km"] >= lastv["vck_max"]).sum()), int((lastv["km"] < lastv["vck_max"]).sum())],
    "pct": [pct(1), pct((lastv["km"] == lastv["vck_last"]).mean()), pct((lastv["km"] == lastv["vck_max"]).mean()),
            pct((lastv["km"] >= lastv["vck_max"]).mean()), pct((lastv["km"] < lastv["vck_max"]).mean())],
}, index=["vehículos", "KM == VCK del último turno", "KM == max(VCK)", "KM >= max(VCK)", "KM < max(VCK)"]),
  note="La afirmación 'KM coincide con VehicleCurrentKM en el último turno' NO está en el script original (tabla 0.2 solo mide constancia).")
# ¿Y para vehículos con >=2 VCK, KM coincide con el último o con el primero?
lv2 = lastv[lastv["n"] >= 2].join(h.groupby("vehicle_id")["VehicleCurrentKM"].first().rename("vck_first"))
T("V11.4 Vehículos con >=2 VCK: KM == último VCK vs KM == primer VCK", pd.DataFrame({"valor": [
    len(lv2), pct((lv2["km"] == lv2["vck_last"]).mean()), pct((lv2["km"] == lv2["vck_first"]).mean()), pct((lv2["km"] > lv2["vck_last"]).mean())]},
    index=["vehículos", "KM == último VCK", "KM == primer VCK", "KM > último VCK (odómetro posterior al último turno con VCK)"]))

OUT_MD.write_text("# Tablas de verificación del EDA 04 (scripts/eda/04_identidad_cliente_vehiculo_verificacion.py)\n" + _buf.getvalue(), encoding="utf-8")
print(f"\nTablas guardadas en {OUT_MD}")
