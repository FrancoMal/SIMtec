"""Dashboard: bandeja de clientes priorizados para retención de service (Ranger, Argentina).

Correr desde la carpeta del proyecto:
    PYTHONPATH=src .venv/Scripts/python.exe -m streamlit run app/app.py
Lee lo que produce scripts/run_pipeline.py (data/processed y data/models). No toca datos crudos.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from repurchase import config  # noqa: E402
from repurchase.negocio import ACCION  # noqa: E402

st.set_page_config(page_title="Retención de service Ranger", page_icon="🔧", layout="wide")

COLORES = {"Alto": "#d03b3b", "Medio": "#ec835a", "Bajo": "#0ca30c"}
AZUL = "#2a78d6"
RUTAS = globals().get("SIMTEC_DASHBOARD_RUTAS", {
    "processed": config.PROCESSED_DIR, "models": config.MODELS_DIR,
    "interim": config.INTERIM_DIR, "figures": config.FIGURES_DIR,
})


@st.cache_data(show_spinner=False)
def cargar_scores(carpeta: str):
    df = pd.read_parquet(Path(carpeta) / "scores_actuales.parquet")
    for c in ["fecha_apertura_ventana", "vencimiento_estimado", "cierre_horizonte", "fecha_turno_agendado", "fecha_scoring"]:
        df[c] = pd.to_datetime(df[c])
    return df


@st.cache_data(show_spinner=False)
def cargar_usuarios(carpeta: str):
    return pd.read_parquet(Path(carpeta) / "scores_actuales_por_usuario.parquet")


@st.cache_data(show_spinner=False)
def cargar_metricas(carpeta: str):
    carpeta = Path(carpeta)
    m = pd.read_csv(carpeta / "metricas_test.csv", index_col=0)
    info = json.loads((carpeta / "info.json").read_text(encoding="utf8"))
    cap = pd.read_csv(carpeta / "capacidad_LightGBM_calibrado.csv")
    lift = pd.read_csv(carpeta / "lift_LightGBM_calibrado.csv")
    return m, info, cap, lift


@st.cache_data(show_spinner=False)
def cargar_historial(vehicle_id: str, carpeta: str):
    a = pd.read_parquet(Path(carpeta) / "agenda.parquet", filters=[("vehicle_id", "==", vehicle_id)],
                        columns=["schedule_id", "ScheduleDate", "StatusARG", "ScheduleSource", "ServiceType",
                                 "ServiceName", "KM", "VehicleCurrentKM", "dealer_id", "SurveyStarRating",
                                 "EffectiveCheckinDate", "DaysInDealer", "customer_id"])
    a = a.drop_duplicates().sort_values("ScheduleDate")
    return a


def kpi(col, label, value, help_=None):
    col.metric(label, value, help=help_)


def main():
    scores = cargar_scores(str(RUTAS["processed"]))
    st.title("Bandeja de retención de service — Ranger Argentina")
    st.caption(f"Scoring al {scores['fecha_scoring'].max().date()} · {len(scores):,} vehículos en ventana o por entrar en 30 días · "
               "probabilidad calibrada de NO completar el mantenimiento programado en la red oficial dentro del horizonte.")

    # ------------------------------------------------------------------ filtros
    with st.sidebar:
        st.header("Filtros")
        seg = st.multiselect("Segmento de riesgo", ["Alto", "Medio", "Bajo"], default=["Alto", "Medio", "Bajo"])
        pobl = st.multiselect("Población", sorted(scores["poblacion_actual"].unique()), default=sorted(scores["poblacion_actual"].unique()))
        gen = st.multiselect("Generación", sorted(scores["generation"].dropna().unique()), default=sorted(scores["generation"].dropna().unique()))
        bu = st.multiselect("Unidad de negocio (venta 2024-26)", sorted(scores["business_unit"].dropna().unique()))
        zona = st.multiselect("Zona del último concesionario", sorted(scores["last_dealer_zone"].dropna().unique()))
        dealer = st.multiselect("Concesionario del último mantenimiento", sorted(scores["last_maint_dealer"].dropna().unique()))
        excluir_turno = st.checkbox("Excluir los que ya tienen turno agendado", value=True)
        min_dias = st.slider("Días restantes de horizonte (mínimo)", 0, 120, 14, step=7,
                             help="Ventanas con pocos días restantes ya casi no tienen margen de acción")
        capacidad = st.slider("Capacidad de contacto (vehículos)", 100, 10000, 3000, step=100)

    f = scores[scores["segmento"].isin(seg) & scores["poblacion_actual"].isin(pobl)]
    if gen:
        f = f[f["generation"].isin(gen)]
    if bu:
        f = f[f["business_unit"].isin(bu)]
    if zona:
        f = f[f["last_dealer_zone"].isin(zona)]
    if dealer:
        f = f[f["last_maint_dealer"].isin(dealer)]
    if excluir_turno:
        f = f[~f["tiene_turno_agendado"]]
    if "dias_restantes_horizonte" in f:
        f = f[f["dias_restantes_horizonte"] >= min_dias]
    f = f.sort_values("prob_churn", ascending=False)

    # ------------------------------------------------------------------ KPIs
    c1, c2, c3, c4, c5 = st.columns(5)
    kpi(c1, "Vehículos seleccionados", f"{len(f):,}")
    kpi(c2, "Riesgo medio", f"{f['prob_churn'].mean():.0%}" if len(f) else "–")
    kpi(c3, "Segmento Alto", f"{(f['segmento'] == 'Alto').sum():,}")
    kpi(c4, "Churners esperados", f"{f['prob_churn'].sum():,.0f}", "suma de probabilidades calibradas")
    top = f.head(capacidad)
    kpi(c5, f"Esperados en los {capacidad:,} primeros", f"{top['prob_churn'].sum():,.0f}",
        "cuántos de los contactados no volverían si no hacemos nada")

    tabs = st.tabs(["Bandeja de contacto", "Ficha de vehículo", "Vista por usuario", "Por concesionario", "Modelo y evidencia"])

    # ------------------------------------------------------------------ bandeja
    with tabs[0]:
        st.subheader("Lista priorizada")
        st.write("Ordenada por probabilidad de churn. La acción sugerida depende del segmento:")
        for s in ["Alto", "Medio", "Bajo"]:
            st.markdown(f"- **{s}**: {ACCION[s]}")
        cols = ["prioridad", "vehicle_id", "customer_id", "segmento", "prob_churn", "poblacion_actual", "vencimiento_estimado",
                "dias_restantes_horizonte", "days_since_last_maint", "km_per_year", "last_km", "n_maint", "n_noshow", "n_cancel", "last_source",
                "last_maint_dealer", "generation", "business_unit", "fleet_size_sales", "tiene_turno_agendado",
                "driver_1", "driver_2", "driver_3"]
        show = top[cols].rename(columns={
            "prob_churn": "p(churn)", "poblacion_actual": "población", "vencimiento_estimado": "vence",
            "dias_restantes_horizonte": "días restantes",
            "days_since_last_maint": "días desde últ. service", "km_per_year": "km/año", "last_km": "último km",
            "n_maint": "services", "n_noshow": "no-shows", "n_cancel": "cancel.", "last_source": "último canal",
            "last_maint_dealer": "dealer últ. service", "generation": "generación", "business_unit": "unidad",
            "fleet_size_sales": "flota", "tiene_turno_agendado": "turno agendado"})
        st.dataframe(show.style.format({"p(churn)": "{:.0%}", "km/año": "{:,.0f}", "último km": "{:,.0f}"}),
                     use_container_width=True, height=520, hide_index=True)
        st.download_button("Descargar lista (CSV)", top[cols].to_csv(index=False).encode("utf8"),
                           file_name="bandeja_contacto.csv", mime="text/csv")
        fig = px.histogram(f, x="prob_churn", nbins=40, color="segmento", color_discrete_map=COLORES,
                           labels={"prob_churn": "probabilidad de churn", "count": "vehículos"},
                           title="Distribución del riesgo en la selección")
        fig.update_layout(bargap=0.05, plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb")
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------------ ficha
    with tabs[1]:
        st.subheader("¿Por qué este vehículo?")
        vid = st.selectbox("Vehículo (ordenados por prioridad)", top["vehicle_id"].tolist() if len(top) else scores["vehicle_id"].head(50).tolist())
        r = scores[scores["vehicle_id"] == vid].iloc[0]
        a, b, c = st.columns(3)
        a.metric("Probabilidad de churn", f"{r['prob_churn']:.0%}")
        b.metric("Segmento", r["segmento"])
        c.metric("Vence", str(pd.Timestamp(r["vencimiento_estimado"]).date()))
        st.markdown(f"**Acción sugerida:** {ACCION[r['segmento']]}")
        st.markdown("**Principales drivers del score (SHAP):**")
        for i in (1, 2, 3):
            st.markdown(f"{i}. {r[f'driver_{i}']}")
        det = {"cliente": r["customer_id"], "es el comprador": bool(r["is_buyer"]), "generación": r["generation"],
               "año modelo": r["model_year"], "unidad de negocio": r["business_unit"], "antigüedad (años)": round(float(r["vehicle_age_years"]), 1) if pd.notna(r["vehicle_age_years"]) else None,
               "km/año estimados": round(float(r["km_per_year"])) if pd.notna(r["km_per_year"]) else None,
               "último km": r["last_km"], "días desde el último service": r["days_since_last_maint"],
               "services observados": int(r["n_maint"]), "no-shows": int(r["n_noshow"]), "cancelaciones": int(r["n_cancel"]),
               "última calificación": r["last_rating"], "turno agendado": bool(r["tiene_turno_agendado"]),
               "fecha turno agendado": r["fecha_turno_agendado"]}
        st.json({k: (None if (isinstance(v, float) and pd.isna(v)) else (str(v) if isinstance(v, pd.Timestamp) else v)) for k, v in det.items()})
        st.markdown("**Historial de turnos (agenda):**")
        h = cargar_historial(vid, str(RUTAS["interim"]))
        st.dataframe(h, use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ usuarios
    with tabs[2]:
        st.subheader("Usuarios con varios vehículos en ventana")
        u = cargar_usuarios(str(RUTAS["processed"]))
        u = u[u["vehiculos_en_ventana"] >= 2].sort_values(["algun_alto", "prob_max"], ascending=[False, False])
        st.write(f"{len(u):,} usuarios tienen 2 o más vehículos en ventana (flotas). Conviene un único contacto por usuario con la lista de sus unidades.")
        st.dataframe(u.style.format({"prob_max": "{:.0%}", "prob_media": "{:.0%}"}), use_container_width=True, hide_index=True)

    # ------------------------------------------------------------------ dealers
    with tabs[3]:
        st.subheader("Carga por concesionario (último mantenimiento)")
        d = (f.groupby("last_maint_dealer").agg(vehiculos=("vehicle_id", "size"), riesgo_medio=("prob_churn", "mean"),
                                                 alto=("segmento", lambda s: (s == "Alto").sum()),
                                                 churners_esperados=("prob_churn", "sum"))
               .sort_values("churners_esperados", ascending=False).reset_index())
        st.dataframe(d.style.format({"riesgo_medio": "{:.0%}", "churners_esperados": "{:.0f}"}), use_container_width=True, hide_index=True)
        fig = px.bar(d.head(25), x="last_maint_dealer", y="churners_esperados", title="Churners esperados por concesionario (top 25)",
                     labels={"last_maint_dealer": "concesionario (id seudonimizado)", "churners_esperados": "churners esperados"})
        fig.update_traces(marker_color=AZUL)
        fig.update_layout(plot_bgcolor="#fcfcfb", paper_bgcolor="#fcfcfb")
        st.plotly_chart(fig, use_container_width=True)

    # ------------------------------------------------------------------ modelo
    with tabs[4]:
        m, info, cap, lift = cargar_metricas(str(RUTAS["models"]))
        st.subheader("Evaluación fuera de tiempo (backtesting)")
        st.write(f"Entrenado con ventanas abiertas hasta {info['split']['train_end']}, calibrado en el trimestre siguiente y "
                 f"evaluado en ventanas abiertas entre {info['test_scoring_range'][0]} y {info['test_scoring_range'][1]} "
                 f"(n = {info['n_test']:,}, churn observado {info['base_rate_test']:.0%}).")
        st.dataframe(m.round(3), use_container_width=True)
        c1, c2 = st.columns(2)
        c1.image(str(RUTAS["figures"] / "modelo" / "ganancia.png"), caption="Curva de ganancia")
        c2.image(str(RUTAS["figures"] / "modelo" / "lift_deciles.png"), caption="Lift por decil")
        c3, c4 = st.columns(2)
        c3.image(str(RUTAS["figures"] / "modelo" / "calibracion.png"), caption="Calibración")
        c4.image(str(RUTAS["figures"] / "modelo" / "shap_global.png"), caption="Importancia SHAP")
        st.markdown("**Recall según capacidad de contacto (test):**")
        st.dataframe(cap.round(3), use_container_width=True, hide_index=True)


if __name__ == "__main__":
    main()
