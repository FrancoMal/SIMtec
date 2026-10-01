"""Panel de control: recalcular en segundo plano. No es parte del recorrido de la demo.
Las salidas que generan las corridas están en .gitignore: recalcular no modifica nada versionado."""
import json
import platform
import sys
import time
from datetime import datetime

import pandas as pd
import streamlit as st

from lib import corridas as C
from lib.fuentes import REPO, WEBAPP

st.title("Corridas")
st.markdown("Recalcula el trabajo del equipo en esta máquina. Las corridas siguen en segundo plano aunque se navegue "
            "a otra página o se cierre la pestaña. Corre una a la vez.")

# ------------------------------------------------------------------ diagnóstico del entorno
sys.path.insert(0, str(REPO / "src"))
from repurchase import config  # noqa: E402

with st.expander("Diagnóstico del entorno", expanded=not C.pipeline_corrido()):
    filas = [("Python", f"{platform.python_version()} ({sys.executable})"), ("Proyecto", str(REPO)),
             ("Datos crudos (Dataset)", str(config.RAW_DIR))]
    for p in (config.RAW_SALES, config.RAW_AGENDA):
        if not p.exists():
            estado = "NO ENCONTRADO"
        elif p.stat().st_size < 1024 and p.read_bytes()[:40].startswith(b"version https://git-lfs"):
            estado = "es un puntero de Git LFS, no el dato: falta `git lfs pull`"
        else:
            estado = f"ok ({p.stat().st_size / 1e6:,.1f} MB)"
        filas.append((p.name, estado))
    filas.append(("Pipeline corrido", "sí" if C.pipeline_corrido() else "todavía no: es lo primero que hay que correr"))
    st.markdown("| | |
|---|---|
" + "
".join(f"| {k} | {v} |" for k, v in filas))

# ------------------------------------------------------------------ lanzar
st.subheader("Recalcular")
activa = C.activa()
hay_pipeline = C.pipeline_corrido()
if not hay_pipeline:
    st.warning("Todavía no hay resultados en esta máquina. **Lo primero es correr el Pipeline completo** (~1 min): "
               "hasta entonces el recorrido de la demo no tiene datos.", icon="⏳")
for t in C.TAREAS + [C.TODO]:
    a, b = st.columns([4, 1.4])
    a.markdown(f"**{t.titulo}** · {t.duracion}  \n<span style='color:#7F7F7F'>{t.que_hace}</span>",
               unsafe_allow_html=True)
    bloqueada = activa is not None or (t.necesita_pipeline and not hay_pipeline)
    if b.button(f"Correr ({t.duracion})", key=f"run_{t.clave}", disabled=bloqueada, width="stretch",
                type="primary" if t.clave == "pipeline" and not hay_pipeline else "secondary"):
        try:
            C.lanzar(t.clave)
        except RuntimeError as e:
            st.error(str(e))
        st.rerun()
st.caption("Duraciones medidas en una corrida desde cero. No está el informe: scripts/build_informe_docx.py "
           "necesita Microsoft Word y genera la versión anterior del informe.")


# ------------------------------------------------------------------ en curso (se refresca solo)
@st.fragment(run_every=2)
def en_curso():
    e = C.activa()
    if not e:
        if st.session_state.get("_habia_activa"):
            st.session_state["_habia_activa"] = False
            st.cache_data.clear()  # para que las páginas lean las salidas nuevas
            st.rerun(scope="app")
        return
    st.session_state["_habia_activa"] = True
    seg = int(time.time() - e["inicio"])
    st.subheader("En curso")
    a, b = st.columns([4, 1])
    a.markdown(f"**{e['titulo']}** · {seg // 60}:{seg % 60:02d} transcurridos")
    if b.button("Cancelar", width="stretch"):
        C.cancelar(e)
        st.rerun(scope="app")
    st.code(C.log(e, 60) or "(arrancando…)", language=None)


en_curso()

# ------------------------------------------------------------------ historial
st.subheader("Historial")
h = C.historial()
if not h:
    st.caption("Todavía no se corrió nada desde la aplicación en esta máquina.")
else:
    filas = []
    for e in h:
        dur = (e["fin"] - e["inicio"]) if e.get("fin") else time.time() - e["inicio"]
        estado = ("en curso" if e.get("fin") is None else "ok" if e.get("codigo") == 0
                  else "cancelada" if e.get("codigo") == "cancelada" else f"error ({e.get('codigo')})")
        filas.append({"Inicio": datetime.fromtimestamp(e["inicio"]).strftime("%d/%m %H:%M:%S"), "Corrida": e["titulo"],
                      "Duración": f"{int(dur) // 60}:{int(dur) % 60:02d}", "Estado": estado, "_e": e})
    st.dataframe(pd.DataFrame(filas).drop(columns="_e"), hide_index=True, width="stretch")
    elegida = st.selectbox("Ver el log de", range(len(filas)),
                           format_func=lambda i: f"{filas[i]['Inicio']} · {filas[i]['Corrida']} · {filas[i]['Estado']}")
    st.code(C.log(filas[elegida]["_e"], 300), language=None)

# ------------------------------------------------------------------ comparación con la entrega
st.subheader("¿Esta máquina reproduce la entrega?")
st.caption("Compara las cifras calculadas acá con las de la corrida entregada (webapp/referencia_entrega.json): "
           "métricas, capacidad de contacto, lift, segmentos, ROI, ablaciones y sensibilidad.")
if st.button("Comparar ahora", disabled=not hay_pipeline):
    ref = json.loads((WEBAPP / "referencia_entrega.json").read_text(encoding="utf8"))
    filas = []
    for archivo, sp in ref["archivos"].items():
        p = REPO / archivo
        if not p.exists():
            filas.append({"Salida": archivo, "Resultado": "todavía no se generó", "Mayor diferencia": "—"})
            continue
        a = pd.DataFrame(sp["data"], columns=sp["columns"])
        b = pd.read_csv(p).drop(columns=["seg"], errors="ignore")
        if list(a.columns) != list(b.columns) or len(a) != len(b):
            filas.append({"Salida": archivo, "Resultado": "DISTINTA (forma)", "Mayor diferencia": f"{a.shape} vs {b.shape}"})
            continue
        num = a.select_dtypes("number").columns
        dif = float((a[num] - b[num].astype(float)).abs().max().max()) if len(num) else 0.0
        txt_igual = a.drop(columns=num).astype(str).equals(b.drop(columns=num).astype(str))
        res = "idéntica" if dif == 0 and txt_igual else ("igual (redondeo < 1e-9)" if dif < 1e-9 and txt_igual
                                                         else "DISTINTA")
        filas.append({"Salida": archivo, "Resultado": res, "Mayor diferencia": f"{dif:.2e}"})
    df = pd.DataFrame(filas)
    st.dataframe(df, hide_index=True, width="stretch")
    ok = df["Resultado"].str.startswith(("idéntica", "igual")).sum()
    (st.success if ok == len(df) else st.warning)(f"{ok} de {len(df)} salidas coinciden con la entrega.")
