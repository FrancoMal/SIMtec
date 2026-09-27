"""Features "as-of" la fecha de scoring, sin leakage.

Regla única: para una ventana con scoring_date = t, solo se usan turnos con event_date < t (y encuestas con
SurveyResponseDate < t). La implementación usa acumulados por vehículo + ``merge_asof`` hacia atrás con
``allow_exact_matches=False``, así que el mismo día del scoring queda excluido.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .eventos import appointments
from .io import load_sales
from .ventanas import _clean_km, _event_km, _monotonic_km, drop_split_visits, vehicle_master


def _customer_change(a: pd.DataFrame) -> pd.Series:
    prev = a.groupby("vehicle_id")["customer_id"].shift(1)
    return a["customer_id"].notna() & prev.notna() & (a["customer_id"] != prev)


def _dealer_change(a: pd.DataFrame) -> pd.Series:
    prev = a.groupby("vehicle_id")["dealer_id"].shift(1)
    return prev.notna() & (a["dealer_id"] != prev)


FLAG_COLS = {
    "n_maint": lambda a: a["is_completed_maintenance"],
    "n_completed": lambda a: a["completed"],
    "n_no_os": lambda a: a["completed_no_os"],
    "n_noshow": lambda a: a["no_show"],
    "n_cancel": lambda a: a["cancelled"],
    "n_appts": lambda a: pd.Series(True, index=a.index),
    "n_recall": lambda a: a["completed"] & a["has_recall"],
    "n_diag": lambda a: a["completed"] & a["has_diag"],
    "n_repair": lambda a: a["completed"] & a["has_repair"],
    "n_guarantee": lambda a: a["completed"] & a["has_guarantee"],
    "n_fordpass": lambda a: a["ScheduleSource"].eq("FordPass"),
    "n_web_or_app": lambda a: a["ScheduleSource"].isin(["FordPass", "WEB", "Mobile"]),
    "n_pud": lambda a: a["completed"] & a["has_pud"],
    "n_mobile": lambda a: a["completed"] & a["has_mobile"],
    "n_fixed_price": lambda a: a["completed"] & a["has_fixed_price"],
    "n_reschedule": lambda a: a["IsReschedule"].eq("Y"),
    # EDA 01/06: IsReschedule = N => cancelación "dura" (46 % no vuelve en 90 d); = Y => reprogramación (72 % re-agenda)
    "n_hard_cancel": lambda a: a["cancelled"] & a["IsReschedule"].eq("N"),
    "n_return_visits": lambda a: a["ScheduleReturn"].eq("Y"),  # re-visita a ~15 d por el mismo problema
    "n_towing": lambda a: a["NeededTowing"].eq("Y"),
    "n_customer_changes": _customer_change,
    "n_dealer_changes": _dealer_change,
}


def _asof(left: pd.DataFrame, right: pd.DataFrame, right_on: str, cols: list[str]) -> pd.DataFrame:
    """merge_asof hacia atrás estricto (right_on < scoring_date), por vehicle_id. Preserva el orden de left."""
    r = right[["vehicle_id", right_on] + cols].dropna(subset=[right_on]).sort_values(right_on)
    left = left.copy()
    left["_ord"] = np.arange(len(left))
    l = left.sort_values("scoring_date")
    out = pd.merge_asof(l, r, left_on="scoring_date", right_on=right_on, by="vehicle_id",
                        direction="backward", allow_exact_matches=False)
    out = out.sort_values("_ord").drop(columns=[right_on, "_ord"]).reset_index(drop=True)
    return out


def build_features(windows: pd.DataFrame, appt: pd.DataFrame | None = None,
                   sales: pd.DataFrame | None = None) -> pd.DataFrame:
    appt = appointments() if appt is None else appt
    sales = load_sales() if sales is None else sales
    vm = vehicle_master(appt, sales).set_index("vehicle_id")

    a = appt[appt["vehicle_id"].notna()].sort_values(["vehicle_id", "event_date", "schedule_id"]).copy()
    a["km_event"] = _clean_km(_event_km(a, "current"))  # nunca la columna KM (foto a la extracción)
    a["km_event"] = _monotonic_km(a, "km_event")
    for name, fn in FLAG_COLS.items():
        a[name] = fn(a).astype("int32")
    a[list(FLAG_COLS)] = a.groupby("vehicle_id")[list(FLAG_COLS)].cumsum()
    a["last_event_date"] = a["event_date"]
    a["last_status"] = a["StatusARG"]
    a["last_source"] = a["ScheduleSource"]
    a["last_dealer_zone"] = a["DealerStateOrZone"]
    a["last_days_in_dealer"] = a["DaysInDealer"].clip(lower=0)

    w = windows[["window_id", "vehicle_id", "scoring_date", "anchor_date", "anchor_km", "k_gen", "km_rate_per_day",
                 "rate_source", "due_date", "due_time", "due_km", "binding_rule", "anchor_type", "history_days",
                 "customer_id", "last_dealer_id"]].reset_index(drop=True)

    # 1) acumulados + último turno de cualquier tipo
    f = _asof(w, a, "event_date", list(FLAG_COLS) + ["last_event_date", "last_status", "last_source",
                                                       "last_dealer_zone", "last_days_in_dealer"])
    f["days_since_last_appt"] = (f["scoring_date"] - f["last_event_date"]).dt.days
    f = f.drop(columns=["last_event_date"])
    for c in FLAG_COLS:
        f[c] = f[c].fillna(0).astype("int32")

    # 2) último mantenimiento completado (+ estadísticas de intervalos)
    m = a[a["is_completed_maintenance"]].sort_values(["vehicle_id", "event_date"]).copy()
    m = drop_split_visits(m)  # misma regla que en ventanas: el mismo service cargado dos veces no cuenta dos veces
    m["prev_maint_date"] = m.groupby("vehicle_id")["event_date"].shift(1)
    m["interval_days"] = (m["event_date"] - m["prev_maint_date"]).dt.days.astype(float)
    m["prev_km"] = m.groupby("vehicle_id")["km_event"].shift(1)
    m["interval_km"] = (m["km_event"] - m["prev_km"]).where(lambda s: s > 0)
    # services hechos fuera de la red: la numeración del plan salta >= 2 entre visitas consecutivas (EDA 02: 9,4 %)
    prev_n = m.groupby("vehicle_id")["maint_number"].shift(1)
    m["jump"] = ((m["maint_number"] - prev_n) >= 2).astype(int)
    m["n_numbering_jumps"] = m.groupby("vehicle_id")["jump"].cumsum()
    m["int_known"] = m["interval_days"].notna().astype(int)
    m["int_n"] = m.groupby("vehicle_id")["int_known"].cumsum()
    m["int_sum"] = m.groupby("vehicle_id")["interval_days"].cumsum()
    m["int_sq"] = (m["interval_days"] ** 2).groupby(m["vehicle_id"]).cumsum()
    m["last_maint_km"] = m["km_event"]
    m["last_maint_number"] = m["maint_number"]
    m["last_maint_source"] = m["ScheduleSource"]
    m["last_maint_dealer"] = m["dealer_id"]
    m["last_maint_days_in_dealer"] = m["DaysInDealer"].clip(lower=0)
    m["last_maint_fixed_price"] = m["has_fixed_price"].astype("int32")
    m["last_maint_pud"] = m["has_pud"].astype("int32")
    m["last_maint_customer_waiting"] = m["CustomerWaiting"].eq("Y").astype("int32")
    m["last_maint_date"] = m["event_date"]
    f = _asof(f, m, "event_date", ["last_maint_date", "last_maint_km", "last_maint_number", "last_maint_source",
                                    "last_maint_dealer", "last_maint_days_in_dealer", "last_maint_fixed_price",
                                    "last_maint_pud", "last_maint_customer_waiting", "interval_days", "interval_km",
                                    "int_n", "int_sum", "int_sq", "n_numbering_jumps"])
    f["n_numbering_jumps"] = f["n_numbering_jumps"].fillna(0).astype("int32")
    f["days_since_last_maint"] = (f["scoring_date"] - f["last_maint_date"]).dt.days
    f["last_interval_days"] = f["interval_days"]
    f["last_interval_km"] = f["interval_km"]
    n = f["int_n"].fillna(0)
    f["mean_interval_days"] = (f["int_sum"] / n).where(n > 0)
    var = (f["int_sq"] / n - f["mean_interval_days"] ** 2).where(n > 1)
    f["std_interval_days"] = np.sqrt(var.clip(lower=0))
    f["n_intervals_known"] = n.astype("int32")
    f = f.drop(columns=["interval_days", "interval_km", "int_n", "int_sum", "int_sq", "last_maint_date"])

    # 3) último no-show / última cancelación / última visita concluida de cualquier tipo
    for flag, name in [("no_show", "days_since_last_noshow"), ("cancelled", "days_since_last_cancel"),
                       ("completed", "days_since_last_visit")]:
        s = a[a[flag]][["vehicle_id", "event_date"]].copy()
        s["d"] = s["event_date"]
        f = _asof(f, s, "event_date", ["d"])
        f[name] = (f["scoring_date"] - f["d"]).dt.days
        f = f.drop(columns=["d"])

    # 4) última lectura de km
    k = a[a["km_event"].notna()][["vehicle_id", "event_date", "km_event"]].copy()
    k["last_km_date"] = k["event_date"]
    f = _asof(f, k, "event_date", ["km_event", "last_km_date"])
    f = f.rename(columns={"km_event": "last_km"})
    f["days_since_last_km"] = (f["scoring_date"] - f["last_km_date"]).dt.days
    f = f.drop(columns=["last_km_date"])

    # 5) encuestas: solo las respondidas antes del scoring
    s = a[a["SurveyResponseDate"].notna()][["vehicle_id", "SurveyResponseDate", "SurveyStarRating"]].copy()
    s = s.sort_values(["vehicle_id", "SurveyResponseDate"])
    s["n_surveys"] = s.groupby("vehicle_id").cumcount() + 1
    s["min_rating"] = s.groupby("vehicle_id")["SurveyStarRating"].cummin()
    s["sum_rating"] = s.groupby("vehicle_id")["SurveyStarRating"].cumsum()
    s["last_rating"] = s["SurveyStarRating"]
    s["last_survey_date"] = s["SurveyResponseDate"]
    f = _asof(f, s, "SurveyResponseDate", ["n_surveys", "min_rating", "sum_rating", "last_rating", "last_survey_date"])
    f["n_surveys"] = f["n_surveys"].fillna(0).astype("int32")
    f["mean_rating"] = (f["sum_rating"] / f["n_surveys"]).where(f["n_surveys"] > 0)
    f["days_since_last_survey"] = (f["scoring_date"] - f["last_survey_date"]).dt.days
    f = f.drop(columns=["sum_rating", "last_survey_date"])

    # 6) estáticas del vehículo y de la venta
    st = vm[["warranty_start", "generation", "model_year", "tma", "connected_status", "region", "in_sales",
             "sales_customer_id", "sales_dealer_id", "person_type", "business_unit", "sales_channel",
             "sales_state", "SalesDate"]]
    f = f.merge(st, left_on="vehicle_id", right_index=True, how="left")
    f["vehicle_age_days"] = (f["scoring_date"] - f["warranty_start"]).dt.days.clip(lower=0)
    f["vehicle_age_years"] = f["vehicle_age_days"] / 365.25
    f["in_sales"] = f["in_sales"].fillna(False).astype("int32")
    f["is_buyer"] = (f["customer_id"].notna() & (f["customer_id"] == f["sales_customer_id"])).astype("int32")
    f["same_dealer_as_sale"] = (f["last_maint_dealer"].notna() & (f["last_maint_dealer"] == f["sales_dealer_id"])).astype("int32")
    f["months_observable"] = f["history_days"] / 30.44

    # 7) tamaño de flota del cliente vigente: vehículos comprados por ese cliente antes del scoring (sales)
    fl = sales.dropna(subset=["customer_id", "SalesDate"]).sort_values(["customer_id", "SalesDate"]).copy()
    fl["fleet_size_sales"] = fl.groupby("customer_id").cumcount() + 1
    fl = fl[["customer_id", "SalesDate", "fleet_size_sales"]].sort_values("SalesDate")
    ff = f[["window_id", "customer_id", "scoring_date"]].dropna(subset=["customer_id"]).sort_values("scoring_date")
    ff = pd.merge_asof(ff, fl, left_on="scoring_date", right_on="SalesDate", by="customer_id",
                       direction="backward", allow_exact_matches=False)[["window_id", "fleet_size_sales"]]
    f = f.merge(ff, on="window_id", how="left")
    f["fleet_size_sales"] = f["fleet_size_sales"].fillna(0).astype("int32")
    # vehículos distintos del cliente vistos en agenda antes del scoring
    cv = a.dropna(subset=["customer_id"]).sort_values(["customer_id", "event_date"])
    cv = cv.drop_duplicates(["customer_id", "vehicle_id"], keep="first")[["customer_id", "vehicle_id", "event_date"]]
    cv["n_vehicles_customer_agenda"] = cv.groupby("customer_id").cumcount() + 1
    cv = cv.sort_values("event_date")
    ff = f[["window_id", "customer_id", "scoring_date"]].dropna(subset=["customer_id"]).sort_values("scoring_date")
    ff = pd.merge_asof(ff, cv[["customer_id", "event_date", "n_vehicles_customer_agenda"]], left_on="scoring_date",
                       right_on="event_date", by="customer_id", direction="backward",
                       allow_exact_matches=False)[["window_id", "n_vehicles_customer_agenda"]]
    f = f.merge(ff, on="window_id", how="left")
    f["n_vehicles_customer_agenda"] = f["n_vehicles_customer_agenda"].fillna(0).astype("int32")

    # 8) geometría de la ventana y uso
    f["days_anchor_to_due"] = (f["due_date"] - f["anchor_date"]).dt.days
    f["km_per_year"] = f["km_rate_per_day"] * 365.25
    f["km_expected_at_scoring"] = f["anchor_km"] + f["km_rate_per_day"] * (f["scoring_date"] - f["anchor_date"]).dt.days
    f["last_maint_late_days"] = f["last_interval_days"] - 365  # >0: el último intervalo fue más largo que el ciclo
    # cuán tarde (en km) llegó al último service respecto del plan nominal K_gen x n (EDA 02: mediana +1.000 km en P703)
    f["last_maint_km_vs_plan"] = f["last_maint_km"] - f["k_gen"] * f["last_maint_number"]
    f["last_interval_km_vs_k"] = f["last_interval_km"] / f["k_gen"]
    f["days_to_due_at_scoring"] = (f["due_date"] - f["scoring_date"]).dt.days
    f["noshow_rate"] = (f["n_noshow"] / f["n_appts"]).where(f["n_appts"] > 0)
    f["cancel_rate"] = (f["n_cancel"] / f["n_appts"]).where(f["n_appts"] > 0)
    f["fordpass_share"] = (f["n_fordpass"] / f["n_appts"]).where(f["n_appts"] > 0)
    f["maint_per_year_observed"] = f["n_maint"] / (f["history_days"].clip(lower=30) / 365.25)
    f["scoring_month"] = f["scoring_date"].dt.month
    f["is_first_service"] = f["anchor_type"].eq("warranty").astype("int32")
    return f


CATEGORICAL = ["last_status", "last_source", "last_dealer_zone", "last_maint_source", "last_maint_dealer",
               "generation", "tma", "connected_status", "region", "person_type", "business_unit",
               "sales_channel", "sales_state", "binding_rule", "anchor_type", "rate_source"]
ID_COLS = ["window_id", "vehicle_id", "scoring_date", "anchor_date", "due_date", "due_time", "due_km",
           "customer_id", "last_dealer_id", "warranty_start", "sales_customer_id", "sales_dealer_id",
           "SalesDate", "history_days"]


if __name__ == "__main__":
    from .ventanas import build_windows
    w = build_windows()
    w = w[w["status"].isin(["evaluable", "censurada"])]
    f = build_features(w)
    print(f.shape)
    print(f.isna().mean().sort_values(ascending=False).head(25).round(3).to_string())
    print(f.describe().T.to_string())
