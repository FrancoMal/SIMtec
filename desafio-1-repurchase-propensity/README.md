# Desafío 1 — Retención de service / propensión de recompra (Ford Innovation Challenge III)

Predicción, para cada usuario–vehículo Ranger que entra en su ventana de mantenimiento, de la probabilidad de **no
completar el próximo mantenimiento programado en la red oficial** (churn de service), con ranking priorizado,
segmentos accionables y explicación por vehículo. Definición oficial en la ficha técnica de Ford; lectura completa en
`docs/00_lectura_del_desafio.md`.

## Cómo abrir la aplicación

La guía de instalación desde un clon de `main` está en [`../EMPEZAR_ACA.md`](../EMPEZAR_ACA.md).
Desde esta carpeta, en Windows:

```bat
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-lock.txt
webapp\abrir_app.bat
```

Luego elegí los datos en **Carga de datos** y ejecutá **Entrenar y priorizar** en **Entrenamiento**.

## Ejecución por consola

Los siguientes comandos usan Git Bash. Para tareas del estudio original también está `ejecutar.bat`
(menú de consola); su opción `dashboard` abre el dashboard anterior de `app/`. La aplicación con las cuatro
secciones se abre con `webapp/abrir_app.bat`.

```bash
# 1) entorno (una vez)
uv venv --python 3.12 .venv && uv pip install --python .venv/Scripts/python.exe -r requirements-lock.txt

# 2) pipeline: CSV -> ventanas -> features -> modelo -> SHAP -> scoring -> prioridad de contacto -> figuras
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/run_pipeline.py

# 3) análisis complementarios
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/sensibilidad_ventana.py   # parámetros de ventana
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/ablaciones.py             # robustez y leakage
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/eda/01_taxonomia_target.py  # (idem 02..06)

# 4) generar y ejecutar notebooks de evidencia
PYTHONIOENCODING=utf8 PYTHONPATH=src .venv/Scripts/python.exe scripts/build_notebooks.py

# 5) aplicación (desde webapp para cargar su configuración de Streamlit)
cd webapp
../.venv/Scripts/python.exe -m streamlit run demo.py --server.port 8510
cd ..

# 6) regenerar el informe base del estudio: usa Word para actualizar el índice y exportar PDF
PYTHONIOENCODING=utf8 .venv/Scripts/python.exe scripts/build_informe_docx.py
# (versión larga en markdown → PDF, sin template): .venv/Scripts/python.exe scripts/build_pdf.py docs/informe_final.md reports/informe_final_md.pdf
```

Para los datos originales se usa, en orden: **`SIMTEC_DATASET`** si está definido, **`Dataset/` del repositorio**
si contiene ambos CSV completos (Git LFS), o **`G:\SIMtec\Dataset`** como alternativa. Los datos crudos son
**solo lectura** (`src/repurchase/config.py`). Los conjuntos cargados desde la aplicación guardan sus archivos y
resultados separados en `data/datasets/<id>/`, fuera de Git. Las demás salidas quedan en `data/`, `reports/` y `docs/`.

Los entregables actualizados son [`../entregables/informe_final_SIMtec.docx`](../entregables/informe_final_SIMtec.docx)
y [`../entregables/FIC_III_Desafio_1_Equipo_SIMtec.pptx`](../entregables/FIC_III_Desafio_1_Equipo_SIMtec.pptx).
`build_informe_docx.py` genera el informe base del estudio; no incorpora automáticamente las actualizaciones
editoriales del segundo filtro y del flujo de la aplicación agregadas a esos entregables.

## Aplicación y segunda etapa de contacto

Abrir `webapp/abrir_app.bat` (el acceso anterior `abrir_demo.bat` sigue funcionando). La navegación superior
incluye sólo **Carga de datos**, **Entrenamiento**, **Resultados** y **Eficiencia del modelo**. El selector
**Conjunto de datos** permanece visible en el encabezado y determina qué datos usan todas las secciones.
En Carga de datos, **Validar y usar este conjunto** revisa los dos CSV y deja seleccionado el nuevo conjunto.
Cada conjunto conserva sus resultados separados. **Entrenar y priorizar**, en Entrenamiento, ejecuta las dos etapas:

1. Modelo de riesgo: conserva el ranking por vehículo, los grupos Alto (20 %), Medio (30 %) y Bajo (50 %),
   la probabilidad de abandono (0 a 1) y los tres motivos SHAP. Los porcentajes son fracciones del ranking,
   no umbrales de probabilidad.
2. Prioridad operativa: reúne Alto + Medio y revisa cliente identificado, turno pendiente, al menos 14 días
   de margen, historial de mantenimiento y concesionario. Consolida un vehículo representativo por cliente.
   Los elegibles se ordenan por señal SHAP operativa positiva, vínculo reciente (730 días), riesgo descendente,
   margen ascendente e identificadores. No se descarta a nadie por tener probabilidad 1.

**Resultados** muestra los clientes seleccionados por el segundo filtro. Incluye búsqueda, filtros combinados
por grupo y concesionario, estados de contacto, detalle por cliente con sus SHAP y exportación de la vista filtrada.
La auditoría por vehículo y el análisis inicial completo están en pestañas internas de la misma sección.

Si el modelo ya está calculado, **Actualizar contactos** en Entrenamiento reaplica sólo la prioridad de contacto.
También puede ejecutarse desde la carpeta del proyecto, en CMD:

```bat
.venv\Scripts\python.exe scripts\run_contacto.py
```

Las reglas están en `config/contacto.json`. La capacidad inicial es 3.000 **clientes por corrida**, ajustable con
`--capacidad`; no es un saldo mensual y no registra llamadas efectuadas. Los casos fuera de capacidad permanecen
en espera. `SIMTEC_OUTPUT_DIR` permite recalcular sólo los resultados de un conjunto cargado.

Salidas en `data/processed/`: `candidatos_contacto.csv/.parquet` (auditoría Alto + Medio),
`contactos_por_cliente.csv/.parquet` (una fila por cliente identificado) y `contacto_resumen.json`
(reglas aplicadas, conteos, fecha y SHA256 del scoring de origen). La web solicita recalcular si el scoring cambió.
El pipeline completo guarda además los conteos en su resumen; las corridas lanzadas desde la web conservan su log.

**Eficiencia del modelo** reúne calidad predictiva, calibración, capacidad, controles de leakage, comparación de
ablaciones cuando está disponible y valores SHAP globales en log-odds. Las nuevas ejecuciones registran tiempos
reales por etapa y tiempo total en `reports/modelo/tiempos_pipeline.json`; para ejecuciones anteriores sólo se
muestran duraciones registradas. Los controles de leakage exponen evidencia y pendientes, no una certificación
de ausencia de fuga. Las ayudas al pasar el cursor explican las métricas y columnas SHAP, incluidas sus unidades.
Los aportes SHAP explican el score del modelo base: no son puntos de probabilidad ni el efecto causal de contactar.
Mientras una ejecución está activa, la aplicación espera antes de mostrar sus resultados.

Este segundo paso es una política operativa explicable, **no un modelo de respuesta al contacto**.
Conserva la probabilidad y los SHAP originales; no mide el efecto de llamar ni promete mayor retorno observado.
Las métricas de test corresponden al primer modelo y el uplift del ROI sigue siendo un supuesto.
Para validar el efecto del contacto se necesitan resultados de campañas con grupo de comparación.
El dataset no confirma teléfono ni permiso de contacto, y el indicador de turno incluye cualquier service pendiente.

Pruebas sin iniciar un servidor, con `.venv\Scripts\python.exe <archivo>`: `webapp/chequeos/contacto.py`,
`webapp/chequeos/resultados_filtros.py`, `webapp/chequeos/eficiencia.py`, `webapp/chequeos/contactos_ui.py`
(requiere las salidas locales del pipeline) y `webapp/chequeos/datasets.py` (ejecuta ambas etapas en un conjunto aislado).

## Estructura

| Carpeta | Qué hay |
|---|---|
| `src/repurchase/` | `io` (carga y tipado), `eventos` (agenda a nivel turno + evento objetivo), `ventanas` (población–ventana–target), `features` (as-of, sin leakage), `modelo` (split temporal, LightGBM, calibración), `evaluacion` (lift, recall a capacidad, calibración), `explicabilidad` (SHAP), `negocio` (segmentos, ROI), `graficos` |
| `scripts/` | `run_pipeline.py` (todo), `sensibilidad_ventana.py`, `ablaciones.py`, `build_notebooks.py`, `build_informe_docx.py` (informe sobre el template oficial), `diccionario_dataset.py`, `build_pdf.py`, `eda/` (seis análisis reproducibles + verificaciones), `revision_cruzada/` (reconciliación de definiciones y comparación con la otra solución) |
| `config/` | `params.json` (ventana, split, segmentos), `negocio.json` (supuestos de ROI), `contacto.json` (segunda etapa) |
| `reports/` | `eda/` (informes + tablas), `modelo/` (resumen de la corrida, ROI, sensibilidad, ablaciones), `revision_cruzada/` (evidencia de la segunda vuelta), `figures/` |
| `docs/` | `00_lectura_del_desafio.md`, `01_hallazgos_eda.md`, `02_decisiones_y_descartes.md`, `03_pitch_trials_day.md`, `04_revision_cruzada.md` (comparación con la solución de `G:\SIMtec-astra`), `diccionario_dataset_analitico.md` (columna por columna del dataset analítico y del ranking), `informe_final.md` |
| `notebooks/` | `01_eda`, `02_target_y_ventanas`, `03_modelo` (ejecutados) |
| `webapp/` | aplicación: carga de datos, entrenamiento, resultados de contacto y eficiencia del modelo |
| `app/` | dashboard anterior del estudio, conservado para consulta |
| `data/` | `interim/` parquet tipados, `processed/` ventanas, dataset analítico y scores actuales, `models/` artefactos (no se versiona) |

## Regla del repo

Ninguna IA hace `git add`, `git commit` ni `git push`. Los commits los hace una persona del equipo.
