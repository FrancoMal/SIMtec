"""Población usuario–vehículo–ventana y target (churn de service).

Idea (ficha técnica): un vehículo "entra en ventana" cuando, según su último mantenimiento (o el inicio de
garantía si nunca hizo uno) y su patrón de uso, le toca el próximo mantenimiento programado. Se lo scorea
al abrir la ventana y se observa si completa el mantenimiento dentro del horizonte.

Todos los parámetros están en :class:`WindowParams` para poder justificar cada uno con el EDA y correr
análisis de sensibilidad. Nada acá mira datos posteriores a la fecha de scoring salvo para construir el
LABEL (que es, por definición, futuro).
"""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

from .eventos import CUTOFF, appointments
from .io import load_sales

DATA_START = pd.Timestamp("2024-01-01")


# Intervalos OFICIALES del plan de mantenimiento Ford Argentina (verificados 15/09/2026 en ford.com.ar/posventa y en el
# manual de garantía Ranger T6 2016): Ranger P703 (nueva, incl. Raptor P703) = 16.000 km ó 12 meses; Ranger P375
# (anterior, incl. Raptor anterior) = 10.000 km ó 1 año. El EDA 02 había medido km/n = 16.0-16.2k y lo interpretó como
# "15.000 + atraso"; la revisión cruzada corrigió el nominal a 16.000.
KM_BY_GENERATION_DEFAULT = {"RANGER (P703)": 16000.0, "RANGER RAPTOR (P703)": 16000.0, "RANGER (P375)": 10000.0,
                            "RANGER RAPTOR": 10000.0, "RANGER": 10000.0}  # "RANGER" sin sufijo = pre-T6 (plan de 10.000)


@dataclass(frozen=True)
class WindowParams:
    cycle_days: int = 365          # tope de tiempo: el próximo service vence a lo sumo a N días del anterior
    km_interval: float = 16000.0   # regla de km por default (generación desconocida)
    km_by_generation: tuple = tuple(KM_BY_GENERATION_DEFAULT.items())  # K por generación: 16k P703 / 10k P375 (plan oficial Ford)
    lead_days: int = 30            # la ventana (y el scoring) abre `lead_days` antes del vencimiento
    horizon_days: int = 90         # el horizonte de resultado cierra `horizon_days` después del vencimiento
    min_gap_days: int = 90         # el vencimiento nunca cae antes de anchor + min_gap (tasa de uso ruidosa)
    first_due_days: int = 300      # primer service (sin km previo): vence a N días del inicio de garantía (EDA 02 §6.3)
    anchor: str = "last_maintenance"  # 'last_maintenance' (default) o 'plan' (aniversarios de garantía)
    km_source: str = "current"     # 'current' = VehicleCurrentKM (km real del evento). 'km' = columna KM: es una FOTO
                                   # por vehículo a la extracción (leakage), solo para ablación.
    min_history_days: int = 0      # exigir historia observable mínima al scoring (0 = no exigir)
    split_visit_days: int = 30     # dos mantenimientos a < N días del mismo vehículo = misma visita partida
    label_margin_days: int = 30    # margen antes del cutoff para etiquetar: los turnos de las últimas semanas pueden
                                   # estar "en progreso" o sin check-out (censura a la derecha, EDA 05/06)
    label_mode: str = "ventana"    # 'ventana' (apertura due−lead, horizonte due+H) o 'mes_calendario' (scoring el 1° del
                                   # mes del vencimiento, horizonte = fin de ese mes: la definición de la solución astra,
                                   # usada para la comparación cruzada)

    def to_dict(self):
        d = asdict(self)
        d["km_by_generation"] = dict(self.km_by_generation)
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "WindowParams":
        d = dict(d)
        if "km_by_generation" in d and isinstance(d["km_by_generation"], dict):
            d["km_by_generation"] = tuple(d["km_by_generation"].items())
        return cls(**d)


# --------------------------------------------------------------------------------------------------
# Maestro de vehículos
# --------------------------------------------------------------------------------------------------
def vehicle_master(appt: pd.DataFrame, sales: pd.DataFrame) -> pd.DataFrame:
    """Una fila por vehículo con atributos estáticos (garantía, generación, año, venta)."""
    ag = (appt.dropna(subset=["vehicle_id"])
              .sort_values(["vehicle_id", "event_date"])
              .groupby("vehicle_id")
              .agg(warranty_agenda=("WarrantyStartDate", "first"),
                   generation=("ShortVehicleModelGroupTreated", "first"),
                   model_year_agenda=("ModelYear", "first"),
                   tma=("TMA", "first"),
                   connected_status=("ConnectedStatusARG", "first"),
                   region=("Region", "first"),
                   dealer_zone_first=("DealerStateOrZone", "first"),
                   first_seen=("event_date", "min"),
                   n_appts_total=("schedule_id", "size")))
    # EDA 05 I2: 110 ventas inválidas (107 con Status != ACCEPTED, 3 con DeliveryDate 2013/2015, 1 "GLOBAL RANGER")
    sales = sales[sales["Status"].eq("ACCEPTED") & sales["ModelShortName"].eq("RANGER")
                  & (sales["DeliveryDate"].isna() | (sales["DeliveryDate"] >= pd.Timestamp("2023-01-01")))]
    sa = sales.set_index("vehicle_id")[["customer_id", "dealer_id", "PersonType", "BusinessUnit", "SalesChannel",
                                         "SalesDate", "DeliveryDate", "WarrantyStartDate", "ModelYear",
                                         "ModelCode", "State"]].rename(columns={
        "customer_id": "sales_customer_id", "dealer_id": "sales_dealer_id", "WarrantyStartDate": "warranty_sales",
        "ModelYear": "model_year_sales", "ModelCode": "sales_model_code", "State": "sales_state",
        "PersonType": "person_type", "BusinessUnit": "business_unit", "SalesChannel": "sales_channel",
    })
    vm = ag.join(sa, how="outer")
    vm["in_sales"] = vm["sales_customer_id"].notna()
    vm["in_agenda"] = vm["first_seen"].notna()
    vm["warranty_start"] = vm["warranty_sales"].fillna(vm["warranty_agenda"])
    vm["model_year"] = vm["model_year_sales"].astype("Float64").fillna(vm["model_year_agenda"])
    # Generación: si no está en agenda, inferir por ModelCode de ventas (xDC/TA1 = P703 nueva gen; xBC = P375).
    gen_from_code = vm["sales_model_code"].map(
        lambda c: "RANGER (P703)" if isinstance(c, str) and (c.endswith("DC") or c == "TA1") else
                  ("RANGER (P375)" if isinstance(c, str) and c.endswith("BC") else np.nan))
    vm["generation"] = vm["generation"].fillna(gen_from_code)
    vm.index.name = "vehicle_id"
    return vm.reset_index()


# --------------------------------------------------------------------------------------------------
# Anclas y ventanas
# --------------------------------------------------------------------------------------------------
def _event_km(appt: pd.DataFrame, km_source: str = "current") -> pd.Series:
    """Km del evento. EDA 02: `KM` es constante por vehículo (foto a la extracción) => leakage; el km real del
    evento es `VehicleCurrentKM` (0 % nulo en turnos concluidos)."""
    if km_source == "current":
        return appt["VehicleCurrentKM"].astype(float)
    if km_source == "km":  # solo para ablación / demostrar el leakage
        return appt["KM"].astype(float)
    raise ValueError(km_source)


def _clean_km(km: pd.Series) -> pd.Series:
    # Lecturas absurdas (< 100 km: placeholders "1"; > 1.000.000) se tratan como desconocidas (EDA 02 §1).
    return km.where((km >= 100) & (km <= 1_000_000))


def _monotonic_km(df: pd.DataFrame, km_col: str = "km") -> pd.Series:
    """Dentro de cada vehículo (ordenado por fecha), una lectura menor que la máxima anterior se anula (1,8 %)."""
    prev_max = df.groupby("vehicle_id")[km_col].cummax().groupby(df["vehicle_id"]).shift(1)
    return df[km_col].where(prev_max.isna() | (df[km_col] >= prev_max))


def maintenance_events(appt: pd.DataFrame, params: WindowParams) -> pd.DataFrame:
    """Mantenimientos programados completados, una fila por vehículo-día (dedup de duplicados lógicos)."""
    m = appt[appt["is_completed_maintenance"] & appt["vehicle_id"].notna()].copy()
    m["km"] = _clean_km(_event_km(m, params.km_source))
    m = (m.sort_values(["vehicle_id", "event_date", "km"])
           .groupby(["vehicle_id", "event_date"], as_index=False)
           .agg(km=("km", "max"), customer_id=("customer_id", "last"), dealer_id=("dealer_id", "last"),
                maint_number=("maint_number", "min"), schedule_id=("schedule_id", "last"),
                source=("ScheduleSource", "last")))
    m = drop_split_visits(m, params.split_visit_days)
    m["km"] = _monotonic_km(m, "km")
    return m


def drop_split_visits(m: pd.DataFrame, days: int = 30) -> pd.DataFrame:
    """El mismo service cargado dos veces (EDA 01 §12, verificado): dos mantenimientos consecutivos del mismo
    vehículo con el MISMO número de service a <= `days` días (Δkm mediana 0). Se conserva el primero. Los pares
    cercanos con número distinto son visitas reales (flotas de alto uso) y se mantienen."""
    m = m.sort_values(["vehicle_id", "event_date"]).copy()
    g = m.groupby("vehicle_id")
    gap = g["event_date"].diff().dt.days
    same_n = m["maint_number"].notna() & (m["maint_number"] == g["maint_number"].shift(1))
    dup = gap.notna() & (gap <= days) & same_n
    return m[~dup].copy()


def build_windows(appt: pd.DataFrame | None = None, sales: pd.DataFrame | None = None,
                  params: WindowParams = WindowParams(), cutoff: pd.Timestamp = CUTOFF) -> pd.DataFrame:
    """Devuelve una fila por ventana con scoring_date, due_date, horizon_end, label y estado.

    Estados: 'evaluable' (label conocido), 'censurada' (horizonte pasa el cutoff; es la población a scorear
    hoy), 'preempted' (el vehículo volvió antes de que abriera la ventana: nunca estuvo en ventana),
    'fuera_de_rango' (scoring antes del inicio de datos), 'futura' (scoring después del cutoff).
    """
    appt = appointments() if appt is None else appt
    sales = load_sales() if sales is None else sales
    vm = vehicle_master(appt, sales)
    maint = maintenance_events(appt, params)

    # ---- anclas ----
    if params.anchor == "last_maintenance":
        a_m = maint.rename(columns={"event_date": "anchor_date", "km": "anchor_km"})[
            ["vehicle_id", "anchor_date", "anchor_km"]].copy()
        a_m["anchor_type"] = "maintenance"
        t0 = vm.loc[vm["warranty_start"].notna(), ["vehicle_id", "warranty_start"]].rename(
            columns={"warranty_start": "anchor_date"})
        t0["anchor_km"] = 0.0
        t0["anchor_type"] = "warranty"
        anchors = pd.concat([a_m, t0], ignore_index=True)
    elif params.anchor == "plan":
        # aniversarios del inicio de garantía: anchor_k = warranty + k*cycle, k = 0,1,2,...
        rows = []
        w0 = vm.loc[vm["warranty_start"].notna(), ["vehicle_id", "warranty_start"]]
        max_k = int(np.ceil((cutoff - w0["warranty_start"].min()).days / params.cycle_days)) + 1
        for k in range(max_k):
            r = w0.copy()
            r["anchor_date"] = r["warranty_start"] + pd.to_timedelta(k * params.cycle_days, unit="D")
            r["anchor_km"] = np.nan
            r["anchor_type"] = "plan"
            rows.append(r.drop(columns="warranty_start"))
        anchors = pd.concat(rows, ignore_index=True)
        anchors = anchors[anchors["anchor_date"] <= cutoff]
    else:
        raise ValueError(params.anchor)

    anchors = anchors.merge(vm[["vehicle_id", "warranty_start", "generation"]], on="vehicle_id", how="left")
    anchors = anchors.sort_values(["vehicle_id", "anchor_date"]).reset_index(drop=True)
    km_by_gen = dict(params.km_by_generation)
    anchors["k_gen"] = anchors["generation"].map(km_by_gen).fillna(params.km_interval)

    # ---- tasa de uso (km/día) conocida AL MOMENTO del ancla: km acumulado / edad del vehículo ----
    # (EDA 02 §4: concuerda con la pendiente entre visitas, Spearman 0,895, y está disponible casi siempre)
    age_days = (anchors["anchor_date"] - anchors["warranty_start"]).dt.days
    rate = anchors["anchor_km"] / age_days.where(age_days >= 90)
    prev_km = anchors.groupby("vehicle_id")["anchor_km"].shift(1)
    prev_dt = anchors.groupby("vehicle_id")["anchor_date"].shift(1)
    gap = (anchors["anchor_date"] - prev_dt).dt.days
    slope = (anchors["anchor_km"] - prev_km) / gap.where(gap >= 60)
    rate = rate.fillna(slope.where(slope > 0))
    rate = rate.where((rate >= 2000 / 365.25) & (rate <= 150000 / 365.25))  # rango plausible 2k-150k km/año
    anchors["rate_source"] = np.where(rate.notna(), "individual", "generacion")
    # fallback: mediana de la generación (EDA 02: 4,1 % de las ventanas)
    is_maint = anchors["anchor_type"] == "maintenance"
    gen_median = rate[is_maint].groupby(anchors.loc[is_maint, "generation"]).median()
    fallback = anchors["generation"].map(gen_median).fillna(rate[is_maint].median())
    anchors["km_rate_per_day"] = rate.fillna(fallback)

    # ---- vencimiento: min(tope anual, K_gen / tasa); primer service (sin km) por tiempo ----
    anchors["due_time"] = anchors["anchor_date"] + pd.to_timedelta(params.cycle_days, unit="D")
    days_to_km = (anchors["k_gen"] / anchors["km_rate_per_day"]).clip(upper=3650)
    anchors["due_km"] = anchors["anchor_date"] + pd.to_timedelta(days_to_km.round(), unit="D")
    due = anchors[["due_time", "due_km"]].min(axis=1)
    floor = anchors["anchor_date"] + pd.to_timedelta(params.min_gap_days, unit="D")
    anchors["due_date"] = due.where(due >= floor, floor)
    anchors["binding_rule"] = np.where(anchors["due_km"] < anchors["due_time"], "km", "tiempo")
    anchors.loc[anchors["due_date"] == floor, "binding_rule"] = "piso"
    first = anchors["anchor_type"] == "warranty"
    anchors.loc[first, "due_date"] = anchors.loc[first, "anchor_date"] + pd.to_timedelta(params.first_due_days, unit="D")
    anchors.loc[first, "binding_rule"] = "primer_service_tiempo"
    anchors.loc[first, ["km_rate_per_day", "due_km"]] = np.nan
    anchors.loc[first, "rate_source"] = "sin_km"
    if params.label_mode == "mes_calendario":
        anchors["scoring_date"] = anchors["due_date"].dt.to_period("M").dt.to_timestamp()
        anchors["horizon_end"] = anchors["scoring_date"] + pd.offsets.MonthEnd(0)
    else:
        anchors["scoring_date"] = anchors["due_date"] - pd.to_timedelta(params.lead_days, unit="D")
        anchors["horizon_end"] = anchors["due_date"] + pd.to_timedelta(params.horizon_days, unit="D")

    # ---- siguiente mantenimiento completado después del ancla ----
    nxt = maint[["vehicle_id", "event_date", "km", "schedule_id"]].rename(
        columns={"event_date": "next_maint_date", "km": "next_maint_km", "schedule_id": "next_maint_schedule_id"})
    nxt = nxt.sort_values("next_maint_date")
    anchors = anchors.sort_values("anchor_date")
    anchors = pd.merge_asof(anchors, nxt, left_on="anchor_date", right_on="next_maint_date",
                            by="vehicle_id", direction="forward", allow_exact_matches=False)
    # ---- siguiente visita concluida de cualquier tipo (target secundario "volvió a la red") ----
    vis = (appt[appt["completed"] & appt["vehicle_id"].notna()][["vehicle_id", "event_date"]]
             .rename(columns={"event_date": "next_visit_date"}).sort_values("next_visit_date"))
    anchors = pd.merge_asof(anchors, vis, left_on="anchor_date", right_on="next_visit_date",
                            by="vehicle_id", direction="forward", allow_exact_matches=False)

    # ---- label y estado ----
    w = anchors
    w["days_next_vs_due"] = (w["next_maint_date"] - w["due_date"]).dt.days
    returned_in_horizon = w["next_maint_date"].notna() & (w["next_maint_date"] > w["scoring_date"]) & \
                          (w["next_maint_date"] <= w["horizon_end"])
    preempted = w["next_maint_date"].notna() & (w["next_maint_date"] <= w["scoring_date"])
    visited_in_horizon = w["next_visit_date"].notna() & (w["next_visit_date"] > w["scoring_date"]) & \
                         (w["next_visit_date"] <= w["horizon_end"])
    w["label_churn"] = np.where(returned_in_horizon, 0, 1).astype(float)
    w["label_no_visit"] = np.where(visited_in_horizon, 0, 1).astype(float)
    # Historia observable: desde el inicio de datos o desde el inicio de garantía (lo que sea posterior); si la
    # garantía está mal cargada (posterior al primer evento visto), se usa el primer evento visto.
    w = w.merge(vm[["vehicle_id", "first_seen"]], on="vehicle_id", how="left")
    w_start = w[["warranty_start", "first_seen"]].min(axis=1)
    hist_start = pd.concat([w_start, pd.Series(DATA_START, index=w.index)], axis=1).max(axis=1)
    w["history_days"] = (w["scoring_date"] - hist_start).dt.days.clip(lower=0)
    w["status"] = "evaluable"
    w.loc[w["horizon_end"] > cutoff - pd.Timedelta(days=params.label_margin_days), "status"] = "censurada"
    w.loc[preempted, "status"] = "preempted"
    w.loc[w["scoring_date"] < DATA_START, "status"] = "fuera_de_rango"
    w.loc[w["scoring_date"] > cutoff, "status"] = "futura"
    if params.min_history_days > 0:
        w.loc[(w["status"] == "evaluable") & (w["history_days"] < params.min_history_days), "status"] = "poca_historia"
    w.loc[w["status"] != "evaluable", ["label_churn", "label_no_visit"]] = np.nan

    # ---- cliente vigente al scoring: último turno (cualquier status) antes del scoring, si no el comprador ----
    cust = (appt.dropna(subset=["vehicle_id", "customer_id"])[["vehicle_id", "event_date", "customer_id", "dealer_id"]]
                .rename(columns={"customer_id": "customer_id_at_scoring", "dealer_id": "last_dealer_id"})
                .sort_values("event_date"))
    w = w.sort_values("scoring_date")
    w = pd.merge_asof(w, cust, left_on="scoring_date", right_on="event_date", by="vehicle_id",
                      direction="backward", allow_exact_matches=False).drop(columns=["event_date"])
    w = w.merge(vm[["vehicle_id", "sales_customer_id"]], on="vehicle_id", how="left")
    w["customer_id"] = w["customer_id_at_scoring"].fillna(w["sales_customer_id"])
    # Dos anclas distintas pueden caer en la misma fecha de scoring (p. ej. ancla de garantía y primer
    # mantenimiento muy cercano): se conserva la del ancla más reciente, que es la que "manda".
    w = w.sort_values(["vehicle_id", "scoring_date", "anchor_date"])
    w = w.drop_duplicates(["vehicle_id", "scoring_date"], keep="last")
    w["window_n"] = w.groupby("vehicle_id").cumcount() + 1
    w["window_id"] = w["vehicle_id"] + "_" + w["scoring_date"].dt.strftime("%Y%m%d")
    cols = ["window_id", "vehicle_id", "customer_id", "customer_id_at_scoring", "sales_customer_id", "window_n",
            "anchor_type", "anchor_date", "anchor_km", "k_gen", "km_rate_per_day", "rate_source", "due_time", "due_km",
            "due_date", "binding_rule", "scoring_date", "horizon_end", "next_maint_date", "next_maint_km",
            "days_next_vs_due", "next_visit_date", "history_days", "status", "label_churn", "label_no_visit",
            "last_dealer_id"]
    return w[cols].sort_values(["scoring_date", "vehicle_id"]).reset_index(drop=True)


if __name__ == "__main__":
    p = WindowParams()
    w = build_windows(params=p)
    print(p.to_dict())
    print(w["status"].value_counts().to_string())
    ev = w[w["status"] == "evaluable"]
    print("evaluables:", len(ev), " churn rate:", round(ev["label_churn"].mean(), 4),
          " no-visit rate:", round(ev["label_no_visit"].mean(), 4))
    print(ev.groupby(ev["scoring_date"].dt.to_period("Q"))["label_churn"].agg(["size", "mean"]).to_string())
    print(ev["binding_rule"].value_counts(normalize=True).round(3).to_string())
    print(ev["anchor_type"].value_counts().to_string())
