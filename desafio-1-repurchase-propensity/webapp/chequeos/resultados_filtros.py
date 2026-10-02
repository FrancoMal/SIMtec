"""Filtros operativos combinados y exportación del mismo alcance de datos."""
from io import BytesIO
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from lib.resultados import SIN_CONCESIONARIO, csv_resultados, filtrar_resultados


tabla = pd.DataFrame([
    {"customer_id": "CLIENTE-A", "vehicle_id": "V-1", "vehiculos_cliente": "V-1 | V.[2]", "grupo": "Alto",
     "situacion": "Seleccionado", "concesionario": "dealer-1", "orden_contacto": 3},
    {"customer_id": "CLIENTE-B", "vehicle_id": "V-2", "vehiculos_cliente": "V-2", "grupo": "Medio",
     "situacion": "En espera", "concesionario": "dealer-1", "orden_contacto": 3001},
    {"customer_id": "CLIENTE-C", "vehicle_id": "V-3", "vehiculos_cliente": "V-3", "grupo": "Alto",
     "situacion": "Seleccionado", "concesionario": "dealer-2", "orden_contacto": 29},
    {"customer_id": None, "vehicle_id": "V-4", "vehiculos_cliente": None, "grupo": "Alto",
     "situacion": "Sin identificador", "concesionario": None, "orden_contacto": None},
    {"customer_id": "CLIENTE-D", "vehicle_id": "V-5", "vehiculos_cliente": "V-5", "grupo": "Alto",
     "situacion": "Revisar", "concesionario": "  ", "orden_contacto": None},
])
original = tabla.copy(deep=True)
combinado = filtrar_resultados(tabla, situacion="Seleccionado", grupo="Alto", concesionario="dealer-1", busqueda="v.[2]")
assert combinado["customer_id"].tolist() == ["CLIENTE-A"], "Debe encontrar un vehículo asociado con búsqueda literal."
assert filtrar_resultados(tabla, grupo="Medio", busqueda="cliente-a").empty, "La búsqueda no debe ignorar el filtro de grupo."
assert filtrar_resultados(tabla, situacion="Seleccionado", concesionario="dealer-2")["orden_contacto"].tolist() == [29]
assert filtrar_resultados(tabla, concesionario=SIN_CONCESIONARIO)["vehicle_id"].tolist() == ["V-4", "V-5"]
assert filtrar_resultados(tabla, busqueda="   ").equals(tabla)
assert filtrar_resultados(tabla, busqueda=".*").empty, "La búsqueda no debe interpretar expresiones regulares."
assert filtrar_resultados(tabla, busqueda="CLIENTE-b")["vehicle_id"].tolist() == ["V-2"]
assert filtrar_resultados(tabla, busqueda="no-existe").empty
exportado = pd.read_csv(BytesIO(csv_resultados(combinado)))
assert exportado["customer_id"].tolist() == combinado["customer_id"].tolist()
assert exportado["orden_contacto"].tolist() == [3], "El filtro y el CSV conservan la prioridad global."
pd.testing.assert_frame_equal(tabla, original)
print("Filtros combinados, búsqueda asociada literal, faltantes y CSV de la vista: OK")
