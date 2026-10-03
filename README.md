# SIMtec · Retención de service Ranger (Ford Innovation Challenge III · Desafío 1)

Modelo que anticipa qué Ranger no van a volver a su service en la red oficial de Ford Argentina, explica por qué y
arma la lista de clientes a contactar primero. Se opera desde una aplicación web.

---

## 1. Problema, solución y resultado

**Problema.** Cada mes, más de 6.000 Ranger entran en su ventana de mantenimiento en Argentina y **4 de cada 10 no
completan ese service en un concesionario oficial** (41,6 % sobre 142 mil ventanas, 2024–2026). Un service perdido
corta la relación con el cliente y es el primer paso hacia una recompra perdida. Hoy todos reciben el mismo
recordatorio en el mismo orden: 6 de cada 10 contactos van a clientes que iban a volver igual.

**Solución.** Un pipeline que, para cada vehículo que entra en su ventana de service:

1. estima la **probabilidad calibrada de no volver** a la red en los 90 días posteriores al vencimiento;
2. la **explica** con sus tres motivos principales (SHAP), traducidos a lenguaje de asesor;
3. lo ubica en un grupo **Alto (20 %) / Medio (30 %) / Bajo (50 %)** con una acción definida para cada uno;
4. aplica una **prioridad operativa** (cliente identificado, sin turno, con margen, un contacto por cliente) y entrega
   la lista de contactos dentro de la capacidad de la red.

Todo se carga, entrena y consulta desde una **aplicación web** (Streamlit).

**Resultado** (validación temporal sobre ~20.000 ventanas de ene–mar 2026 que el modelo nunca vio):

| Indicador | Valor |
|---|---|
| ROC-AUC / PR-AUC | 0,74 / 0,70 (tasa base 0,42) |
| Precisión en el grupo Alto (top 20 %) | ~80 % se estaban yendo, contra 42 % sin orden: **el doble de efectividad con el mismo esfuerzo** |
| Lift en el primer decil | ×2 |
| Calibración | error promedio de ~1 punto: "70 % de riesgo" ≈ 7 de cada 10 no vuelven |
| Valor estimado | ~USD 200 mil/año con 3.000 contactos/mes (bajo supuestos de negocio declarados en `config/negocio.json`) |

Se detectaron y eliminaron dos fugas de información (kilometraje y conectividad, que son fotos del momento de la
extracción): con ellas el modelo daba 0,81 de ROC-AUC, pero ese número no se cumple en la operación real.

---

## 2. Ficha técnica

| Área | Herramientas |
|---|---|
| Lenguaje y entorno | Python 3.12, `uv` (entornos), `requirements-lock.txt` (versiones exactas) |
| Datos | pandas, NumPy, PyArrow (Parquet), DuckDB |
| Modelado | LightGBM (gradient boosting), scikit-learn (regresión logística de referencia, calibración isotónica, métricas) |
| Explicabilidad | SHAP (TreeExplainer) |
| Visualización | Matplotlib, Seaborn, Plotly |
| Aplicación web | Streamlit (4 secciones, ejecución de corridas en segundo plano) |
| Evidencia y reportes | Jupyter (nbformat/nbconvert), python-docx, ReportLab, openpyxl |
| Pruebas | `unittest`, Streamlit `AppTest`, Playwright (recorrido en navegador) |
| Datos de entrada | `ranger_sales_arg_2024_2026.csv` y `ranger_service_agenda_arg_2024_2026 1.csv` (Git LFS) |

---

## 3. Algoritmo paso a paso

El pipeline completo está en `desafio-1-repurchase-propensity/scripts/run_pipeline.py` (~3 min) y sus parámetros en
`desafio-1-repurchase-propensity/config/`.

1. **Carga y tipado.** Lee los dos CSV (ventas y agenda de turnos), normaliza tipos y guarda Parquet intermedios.
   Los datos crudos son solo lectura.
2. **Agenda a nivel turno.** Consolida las líneas de la agenda en un turno por visita y marca el evento objetivo:
   mantenimiento programado completado en la red.
3. **Ventanas de service.** Para cada usuario–vehículo calcula cuándo le toca el próximo service **según sus
   kilómetros reales** (16.000 km en P703, 10.000 km en generaciones anteriores, con tope de 365 días) a partir del
   último mantenimiento completado, o 300 días desde la garantía para el primer service. La ventana abre 30 días
   antes del vencimiento.
4. **Target.** `churn = 1` si el vehículo **no** completa un mantenimiento programado en la red dentro de vencimiento
   + 90 días.
5. **Features "as-of".** Más de 80 variables calculadas solo con información disponible al momento de abrir la ventana:
   intervalos entre services, atraso respecto del plan, frecuencia de visitas, no-shows y cancelaciones, antigüedad,
   n.º de service, flota, concesionario, calificaciones, etc. Se excluyen las columnas que son fotos del presente
   (KM, conectividad, turnos futuros) para evitar leakage.
6. **Split temporal.** Entrenamiento hasta sep-2025, validación oct–dic 2025, test ene–mar 2026.
7. **Entrenamiento.** LightGBM con early stopping sobre validación; se compara contra azar, una heurística y una
   regresión logística.
8. **Calibración.** Regresión isotónica sobre la validación, para que el score sea una probabilidad real.
9. **Evaluación.** ROC-AUC, PR-AUC, Brier, ECE, lift por decil y recall a capacidad sobre el test.
10. **Explicabilidad.** SHAP por vehículo: los tres motivos con mayor aporte al riesgo, traducidos a texto.
11. **Segmentos y ROI.** Ranking por probabilidad → Alto (top 20 %), Medio (30 %), Bajo (50 %); simulación de
    capacidad y ROI con los supuestos de `config/negocio.json`.
12. **Scoring actual.** Aplica el modelo a la población que hoy está en ventana o entra en los próximos 30 días.
13. **Prioridad de contacto** (`config/contacto.json`). Toma Alto + Medio y deja elegibles a los clientes
    identificados, sin turno agendado y con al menos 14 días de margen; consolida un vehículo representativo por
    cliente y ordena por: señal SHAP accionable → vínculo reciente (≤ 730 días) → probabilidad descendente → menos
    días de margen. Selecciona hasta 3.000 clientes por corrida; el resto queda en espera.

Esta segunda etapa es una **regla operativa explicable**, no un modelo de respuesta al contacto: el efecto real de
llamar se valida con un piloto con grupo de comparación.

---

## 4. Cómo levantar la aplicación web

### Requisitos

- Python 3.12 y [`uv`](https://docs.astral.sh/uv/) (o `python -m venv` + `pip`).
- Git LFS para bajar los CSV: `git lfs install && git lfs pull`.

### Instalación (una vez)

Desde `desafio-1-repurchase-propensity/`:

```bash
# Linux / macOS
uv venv --python 3.12 .venv
uv pip install --python .venv/bin/python -r requirements-lock.txt
```

```bat
:: Windows
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-lock.txt
```

### Abrir la aplicación

```bash
./webapp/abrir_app.sh          # Linux / macOS
```

```bat
webapp\abrir_app.bat           :: Windows (abre el navegador solo)
```

O a mano: `cd webapp && ../.venv/bin/python -m streamlit run app.py`.
La aplicación queda en **http://localhost:8510**.

### Operar desde la web

La barra superior tiene cuatro secciones; el selector **Conjunto de datos** del encabezado define con qué datos
trabaja cada una.

1. **Carga de datos** — usar los CSV originales o subir un par nuevo (ventas + agenda) y presionar
   **Validar y usar este conjunto**. Cada conjunto guarda sus resultados por separado en `data/datasets/<id>/`.
2. **Entrenamiento** — **Entrenar y priorizar** corre el pipeline completo en segundo plano y muestra el progreso.
   Si el modelo ya existe, **Actualizar contactos** recalcula solo la prioridad de contacto.
3. **Resultados** — lista de clientes seleccionados con búsqueda, filtros por grupo y concesionario, estado de
   contacto, detalle por cliente con sus motivos SHAP y exportación a CSV. Incluye la auditoría por vehículo.
4. **Eficiencia del modelo** — métricas, calibración, curva de capacidad, controles de leakage, SHAP global y
   tiempos por etapa de la última corrida.

### Datos de origen

Se buscan en este orden: variable `SIMTEC_DATASET`, la carpeta `Dataset/` del repo (con ambos CSV completos) o
`G:\SIMtec\Dataset`. Las salidas generadas (`data/`, `reports/modelo/`, `reports/figures/`) no se versionan.

### Por consola (opcional)

```bash
cd desafio-1-repurchase-propensity
PYTHONPATH=src .venv/bin/python scripts/run_pipeline.py     # pipeline completo
PYTHONPATH=src .venv/bin/python scripts/run_contacto.py     # solo prioridad de contacto (--capacidad N)
./ejecutar.sh                                               # menú (ejecutar.bat en Windows)
```

---

## Estructura del repositorio

| Ruta | Contenido |
|---|---|
| `Dataset/` | CSV de ventas y agenda, ficha técnica (Git LFS) |
| `entregables/` | Informe final, presentación y pitch |
| `desafio-1-repurchase-propensity/src/repurchase/` | Librería: carga, eventos, ventanas, features, modelo, evaluación, SHAP, negocio, contacto |
| `desafio-1-repurchase-propensity/scripts/` | Pipeline, análisis complementarios (sensibilidad, ablaciones, EDA) e informes |
| `desafio-1-repurchase-propensity/reports/eda/` | Informes del análisis exploratorio, con su verificación |
| `desafio-1-repurchase-propensity/config/` | `params.json` (ventana, split, segmentos), `negocio.json` (ROI), `contacto.json` (segunda etapa) |
| `desafio-1-repurchase-propensity/webapp/` | Aplicación web: `app.py`, `paginas/`, `lib/`, `chequeos/` |
