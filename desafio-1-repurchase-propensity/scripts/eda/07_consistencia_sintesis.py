"""Chequeos cortos de consistencia entre los seis informes de EDA (usados en docs/01_hallazgos_eda.md).

Correr desde la carpeta del proyecto:
    PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/07_consistencia_sintesis.py

1. Por que el EDA 02 colapsa 1.033 filas "vehiculo + event_date" y el EDA 01/03 solo 335: el EDA 02 trato los
   turnos sin vehicle_id (NaN) como un mismo vehiculo, asi que colapso tambien sus fechas repetidas.
2. Cuanto agregaria la regla "colapsar mantenimientos a <= 7 dias" (EDA 05) sobre la regla final del EDA 01
   (un evento por vehiculo-dia + mismo maint_number a <= 30 dias).
"""
from repurchase.eventos import appointments, CUTOFF

ap = appointments()
m = ap[ap.is_completed_maintenance].copy()
print("candidatos (60)+mant:", len(m))

nan = m[m.vehicle_id.isna()]
print("sin vehicle_id:", len(nan), "| event_date distintas entre ellos:", nan.event_date.nunique(),
      "| filas que colapsan si NaN cuenta como vehiculo:", len(nan) - nan.event_date.nunique())
mv = m[m.vehicle_id.notna() & (m.ScheduleDate <= CUTOFF)]
print("con vehicle_id y <= CUTOFF:", len(mv), "| duplicados vehiculo-dia:", int(mv.duplicated(["vehicle_id", "event_date"]).sum()))
print("duplicados vehiculo-dia contando NaN como vehiculo (base M del EDA 02):", int(m.duplicated(["vehicle_id", "event_date"]).sum()))

# Regla final del EDA 01 (regla_eventos)
c = mv.sort_values(["vehicle_id", "event_date", "schedule_id"])
c1 = c[~c.duplicated(["vehicle_id", "event_date"], keep="first")]
prev_date = c1.groupby("vehicle_id")["event_date"].shift(1)
prev_n = c1.groupby("vehicle_id")["maint_number"].shift(1)
dup_n = (c1.maint_number == prev_n) & ((c1.event_date - prev_date).dt.days <= 30)
k = c1[~dup_n]
print("mant_completado (regla EDA 01):", len(k), "eventos |", k.vehicle_id.nunique(), "vehiculos")

# Regla adicional del EDA 05: <= 7 dias del anterior conservado
gap = (k.event_date - k.groupby("vehicle_id")["event_date"].shift(1)).dt.days
dn = k.maint_number - k.groupby("vehicle_id")["maint_number"].shift(1)
print("eventos conservados a <= 7 d del anterior conservado:", int((gap <= 7).sum()),
      f"({(gap <= 7).mean() * 100:.2f} % de los eventos) | de ellos con delta n = +1:", int(((gap <= 7) & (dn == 1)).sum()))
print("eventos conservados a <= 30 d del anterior conservado:", int((gap <= 30).sum()))
