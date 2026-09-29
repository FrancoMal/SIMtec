"""Preguntas de Franco: (1) fuentes, (2) qué hay antes de 2024 y qué se puede deducir, (3) recompra observable.
Salida: reports/revision_cruzada/03_historia_previa_y_recompra.md
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from repurchase import config  # noqa: E402
from repurchase.eventos import appointments  # noqa: E402
from repurchase.io import load_agenda, load_sales  # noqa: E402

OUT = config.REPORTS_DIR / "revision_cruzada"
L = []


def log(s=""):
    print(s, flush=True); L.append(s)


ag = load_agenda().drop_duplicates()
sales = load_sales()
appt = appointments(ag)
D0 = pd.Timestamp("2024-01-01")

log("# Historia previa a 2024 y recompra observable\n")
log("## 1. Fuentes")
log(f"Archivos en la carpeta compartida: 3 (ventas CSV, agenda CSV, ficha técnica docx). No hay CRM, DMS, campañas, web ni telemetría.")

log("\n## 2. Qué hay antes de 2024")
sd = ag["ScheduleDate"]
log(f"Agenda: turnos con ScheduleDate < 2024-01-01: {int((sd < D0).sum())} de {ag['schedule_id'].nunique():,} turnos. "
    f"Check-ins con fecha < 2024: {int((ag['EffectiveCheckinDate'] < D0).sum())} filas (errores de carga: 2001 y 2023). "
    f"Ventas con SalesDate < 2024: {int((sales['SalesDate'] < D0).sum())} de {len(sales):,}.")
vm = appt.dropna(subset=["vehicle_id"]).groupby("vehicle_id").agg(wsd=("WarrantyStartDate", "first"), my=("ModelYear", "first"),
                                                                    first_seen=("event_date", "min"), n=("schedule_id", "size"))
old = vm[vm["wsd"] < D0]
log(f"Vehículos en agenda: {len(vm):,}; con inicio de garantía anterior a 2024: {len(old):,} ({len(old)/len(vm):.1%}); "
    f"con garantía anterior a 2023: {int((vm['wsd'] < '2023-01-01').sum()):,}; con garantía anterior a 2020: {int((vm['wsd'] < '2020-01-01').sum()):,}. "
    f"Sin garantía informada: {int(vm['wsd'].isna().sum()):,}.")
log(f"Ventas 2024-26 cuyo vehículo NO aparece en la agenda: {int((~sales['vehicle_id'].isin(vm.index)).sum()):,} de {len(sales):,}.")

# señal de services previos: número del primer service observado en vehículos viejos
m = appt[appt["is_completed_maintenance"] & appt["vehicle_id"].notna()].sort_values("event_date")
first = m.drop_duplicates("vehicle_id")[["vehicle_id", "maint_number", "event_date"]].set_index("vehicle_id")
fo = first.join(vm[["wsd"]], how="inner")
fo_old = fo[fo["wsd"] < D0]
log(f"\nVehículos con garantía anterior a 2024 y al menos un mantenimiento en 2024-26: {len(fo_old):,}. "
    f"Número de service del PRIMER mantenimiento observado: 1° → {int((fo_old['maint_number']==1).sum()):,} ({(fo_old['maint_number']==1).mean():.1%}); "
    f"2°-5° → {int(fo_old['maint_number'].between(2,5).sum()):,} ({fo_old['maint_number'].between(2,5).mean():.1%}); "
    f"6° o más → {int((fo_old['maint_number']>=6).sum()):,} ({(fo_old['maint_number']>=6).mean():.1%}); sin número → {int(fo_old['maint_number'].isna().sum()):,}.")
age_first = (fo_old["event_date"] - fo_old["wsd"]).dt.days / 365.25
log(f"De esos, con más de 2 años de antigüedad al primer mantenimiento observado: {int((age_first > 2).sum()):,}; "
    f"de ellos el {(fo_old.loc[age_first > 2, 'maint_number'] >= 2).mean():.1%} arranca con un service numerado ≥ 2° (evidencia de services previos en el plan).")
never = old[~old.index.isin(m["vehicle_id"])]
log(f"Vehículos con garantía anterior a 2024 que aparecen en la agenda pero SIN ningún mantenimiento completado en 2024-26: {len(never):,} "
    f"(sólo diagnósticos, campañas, cancelaciones o no-shows).")

# usuarios: ¿cuántos customer_id sólo existen por vehículos viejos?
cu = appt.dropna(subset=["customer_id", "vehicle_id"]).merge(vm[["wsd"]], left_on="vehicle_id", right_index=True)
cust_old = cu.groupby("customer_id")["wsd"].max()
log(f"Clientes (customer_id) en agenda: {cu['customer_id'].nunique():,}; cuyos vehículos son TODOS anteriores a 2024: {int((cust_old < D0).sum()):,} "
    f"({(cust_old < D0).mean():.1%}). Para ellos no hay ningún evento propio antes de 2024: sólo se sabe que poseen un Ford entregado antes.")

log("\n## 3. Recompra observable")
# (a) dentro de ventas
per_c = sales.groupby("customer_id").agg(n=("vehicle_id", "nunique"), first=("SalesDate", "min"), last=("SalesDate", "max"), pt=("PersonType", "first"))
multi = per_c[per_c["n"] >= 2]
log(f"Ventas: {len(sales):,} vehículos, {len(per_c):,} compradores; con ≥2 vehículos: {len(multi):,} ({len(multi)/len(per_c):.1%}), "
    f"que compran {int(sales[sales['customer_id'].isin(multi.index)].shape[0]):,} vehículos. Por tipo: F (físicas) {int((multi['pt']=='F').sum()):,}, "
    f"J (jurídicas) {int((multi['pt']=='J').sum()):,}, otros {int((~multi['pt'].isin(['F','J'])).sum()):,}.")
seq = multi[(multi["last"] - multi["first"]).dt.days >= 90]
log(f"Con compras separadas ≥ 90 días (compra secuencial, no flota simultánea): {len(seq):,} compradores; personas físicas: {int((seq['pt']=='F').sum()):,}; "
    f"separadas ≥ 365 días: {int(((multi['last'] - multi['first']).dt.days >= 365).sum()):,}.")
log(f"Compradores con exactamente 2 vehículos: {int((multi['n']==2).sum()):,}; 3-9: {int(multi['n'].between(3,9).sum()):,}; 10 o más: {int((multi['n']>=10).sum()):,} (máximo {int(multi['n'].max()):,}).")

# (b) cruce agenda -> ventas: cliente que ya usaba OTRO Ranger (visto en agenda antes de la venta) y compra uno nuevo
ev = appt.dropna(subset=["customer_id", "vehicle_id"])[["customer_id", "vehicle_id", "event_date"]]
j = sales[["customer_id", "vehicle_id", "SalesDate", "PersonType"]].merge(ev, on="customer_id", suffixes=("_venta", "_agenda"))
prev = j[(j["vehicle_id_agenda"] != j["vehicle_id_venta"]) & (j["event_date"] < j["SalesDate"])]
prev_vm = prev.merge(vm[["wsd"]], left_on="vehicle_id_agenda", right_index=True)
prev_old = prev_vm[prev_vm["wsd"] < prev_vm["SalesDate"] - pd.Timedelta(days=365)]
rec_sales = prev_old.drop_duplicates("vehicle_id_venta")
log(f"\nRecompra por cruce agenda→ventas: ventas 2024-26 cuyo comprador ya había pasado por la agenda con OTRO Ranger (entregado al menos un año antes) "
    f"antes de la fecha de compra: {len(rec_sales):,} ventas ({len(rec_sales)/len(sales):.1%}), {rec_sales['customer_id'].nunique():,} compradores; "
    f"personas físicas: {int((rec_sales['PersonType']=='F').sum()):,}.")
# (c) tasa base de recompra para dueños de Ranger viejas vistos en agenda
owners = cu[cu["wsd"] < D0].groupby("customer_id").agg(first_ev=("event_date", "min"), n_veh=("vehicle_id", "nunique"))
bought = sales.groupby("customer_id")["SalesDate"].min()
owners["compro_despues"] = owners.index.map(bought)
owners["recompra"] = owners["compro_despues"].notna() & (owners["compro_despues"] > owners["first_ev"])
log(f"Dueños de Ranger anteriores a 2024 vistos en la agenda: {len(owners):,}; de ellos compraron una Ranger 0 km en 2024-26 después de su primer turno: "
    f"{int(owners['recompra'].sum()):,} ({owners['recompra'].mean():.1%}). Es una tasa base de recompra observable, sólo Ranger→Ranger y sólo dentro de 2024-26.")
owners_f = owners[owners.index.isin(cu[cu["vehicle_id"].isin(vm.index)]["customer_id"])]
by_year = owners.assign(y=owners["first_ev"].dt.year).groupby("y")["recompra"].agg(["size", "mean"])
log("Por año del primer turno observado (menos seguimiento en 2026):\n" + by_year.round(3).to_markdown())

(OUT / "03_historia_previa_y_recompra.md").write_text("\n".join(L), encoding="utf8")
