"""Comprueba el listado completo y sus filtros sin iniciar un servidor."""
from pathlib import Path
import sys

import pandas as pd
from streamlit.testing.v1 import AppTest

PROYECTO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROYECTO / "webapp"))
from lib.listado import filtrar, tabla_completa  # noqa: E402

s = pd.read_parquet(PROYECTO / "data/processed/scores_actuales.parquet")
tabla = tabla_completa(s)
assert list(tabla) == ["customer_id", "vehicle_id", "fecha", "probabilidad", "grupo",
                      "motivo_SHAP_1", "motivo_SHAP_2", "motivo_SHAP_3"]
assert len(tabla) == len(s)
assert tabla["probabilidad"].between(0, 1).all()
ordenado = s.sort_values("prioridad").reset_index(drop=True)
for i in (1, 2, 3):
    pd.testing.assert_series_equal(tabla[f"motivo_SHAP_{i}"], ordenado[f"driver_{i}"], check_names=False)
for grupo in ("Alto", "Medio", "Bajo"):
    assert len(filtrar(tabla, grupo)) == int((s["segmento"] == grupo).sum())
vid = str(tabla.iloc[0]["vehicle_id"])
assert filtrar(tabla, busqueda=vid)["vehicle_id"].eq(vid).all()
assert filtrar(tabla, busqueda="identificador-inexistente").empty
assert len(tabla_completa(s, adicionales=True)) == len(s)
print("Lista íntegra, probabilidades, grupos y motivos SHAP: OK", flush=True)

app = AppTest.from_file(str(PROYECTO / "webapp/demo.py"), default_timeout=60).run()
app.switch_page("paginas/lista.py").run()
assert not app.exception, [e.message for e in app.exception]
assert len(app.dataframe[0].value) == len(s)
app.radio(key="lista_grupo").set_value("Alto").run()
assert len(app.dataframe[0].value) == int((s["segmento"] == "Alto").sum())
app.radio(key="lista_grupo").set_value("Todos").run()
app.text_input(key="lista_busqueda").set_value(vid).run()
assert app.dataframe[0].value["vehicle_id"].eq(vid).all()
app.toggle(key="lista_adicionales").set_value(True).run()
assert not app.exception, [e.message for e in app.exception]
assert "aporte_SHAP_1" in app.dataframe[0].value
print("Página, selección de grupo, búsqueda y datos adicionales: OK", flush=True)
