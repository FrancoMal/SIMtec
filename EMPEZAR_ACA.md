# EMPEZAR ACÁ: correr el proyecto desde cero en una máquina nueva

Rama `main` · Desafío 1 (Repurchase / retención de service) · Equipo SIMtec

Esta guía describe la aplicación actual. Los tiempos indicados como históricos corresponden a una prueba con
clon y entorno nuevos del **01/10/2026**, en Windows 11, anterior al segundo filtro y a la reorganización de la
interfaz. Son una referencia de esa versión; la aplicación registra la duración real de cada nueva ejecución.

> **Lo más importante.** El modelo, el scoring y la lista de contactos se recalculan en cada máquina.
> Después de instalar, abrí la aplicación, elegí los datos y ejecutá **Entrenar y priorizar**.
> Hasta completar esa ejecución, las secciones de resultados y eficiencia indican qué falta calcular.

En la prueba histórica, el clon llevó ~1 minuto, el entorno ~2,5 minutos y el pipeline de entonces ~1,5 minutos.
El volumen de datos, el equipo y la versión del programa pueden cambiar esos tiempos.

---

## 1. Requisitos

| Qué | Versión | Cómo verificar | Notas |
|---|---|---|---|
| Windows | 10 u 11 | — | Probado en Windows 11. Los `.bat` son de Windows. |
| Git | 2.40 o más nuevo (probado con 2.54) | `git --version` | https://git-scm.com/download/win |
| **Git LFS** | 3.x (probado con 3.7.1) | `git lfs version` | **Imprescindible**: los dos CSV de datos vienen por LFS. Viene con Git for Windows; si el comando falla, instalarlo de https://git-lfs.com. Ver el problema 1. |
| **Python 3.12** | 3.12.x (probado con 3.12.3) | `py -3.12 --version` | Con 3.13 o 3.14 las versiones fijadas de las librerías pueden no instalarse. Se puede tener 3.12 al lado de otras versiones. https://www.python.org/downloads/ |
| uv (opcional) | 0.8 o más nuevo | `uv --version` | Más rápido que pip y, si falta Python 3.12, lo descarga solo. Si no lo tenés, usá la variante B del paso 3. |
| Navegador | cualquiera | — | Para la webapp. |
| Disco | ~2,5 GB libres | — | Datos ~300 MB, entorno ~1,5 GB, salidas. |
| Microsoft Word | **no hace falta** | — | Sólo lo usa `scripts/build_informe_docx.py` (informe), que no es parte de este recorrido. |

## 2. Clonar main · referencia histórica: 64 s

En PowerShell o CMD, en la carpeta donde quieras el proyecto:

```
git lfs install
git clone --branch main https://github.com/FrancoMal/SIMtec.git SIMtec
cd SIMtec
```

Durante el clon aparece `Filtering content: 100% (2/2), 279.68 MiB`: son los dos CSV bajando por LFS.

Verificá que los datos llegaron enteros, no como punteros de LFS:

```
dir Dataset\*.csv
```

Tiene que mostrar:

- `ranger_sales_arg_2024_2026.csv` con **11.459.646** bytes
- `ranger_service_agenda_arg_2024_2026 1.csv` con **281.802.619** bytes (el nombre lleva " 1" antes de `.csv`; es
  así en git y el código lo busca con ese nombre)

Si pesan ~130 bytes, ver el **problema 1**.

## 3. Crear el entorno · referencia histórica: 2 a 2,5 min

```
cd desafio-1-repurchase-propensity
```

**Variante A, con uv** (medido: 145 s):

```
uv venv --python 3.12 .venv
uv pip install --python .venv\Scripts\python.exe -r requirements-lock.txt
```

**Variante B, con venv y pip** (medido: 119 s):

```
py -3.12 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
```

Usá **`requirements-lock.txt`** (las versiones exactas con las que se generó la entrega), no `requirements.txt`
(sólo mínimos): el lock fija el entorno de referencia para poder comparar resultados.

Verificación (tiene que imprimir `3.0.5 4.7.0 1.64.0`):

```
.venv\Scripts\python.exe -c "import pandas, lightgbm, streamlit; print(pandas.__version__, lightgbm.__version__, streamlit.__version__)"
```

## 4. Abrir la webapp

```
cd webapp
abrir_app.bat
```

Se abre el navegador en http://localhost:8510. Para cerrarla: Ctrl+C en esa terminal o cerrar la ventana.
El acceso anterior `abrir_demo.bat` sigue funcionando y abre la misma aplicación.

## 5. Usar la aplicación

La navegación superior tiene cuatro secciones: **Carga de datos → Entrenamiento → Resultados → Eficiencia del
modelo**. El selector **Conjunto de datos**, en el encabezado, aplica a toda la aplicación.

### Carga de datos

Podés usar **Dataset original** o cargar un CSV de ventas y otro de agenda de servicios. Asigná un nombre y revisá
**Fechas del análisis**: fin de entrenamiento, fin de calibración y corte de datos. Los archivos pueden tener
cualquier nombre; deben conservar las columnas del extracto de Ford, usar comas y codificación UTF-8. La sección
**Formato de los archivos** muestra las columnas necesarias. Se admiten hasta 1 GB por archivo.

**Validar y usar este conjunto** revisa ambos archivos completos: cabeceras, identificadores, fechas y cantidad
de filas. Guarda los nombres originales y las huellas SHA-256 y deja seleccionado el conjunto nuevo. Cada conjunto
conserva sus datos, configuración, resultados e historial bajo `desafio-1-repurchase-propensity/data/datasets/<id>/`.
Los CSV originales no se reemplazan. Los conjuntos cargados y sus resultados quedan en esta máquina, fuera de Git.

Las fechas deben dejar ventanas evaluables con retornos y abandonos en entrenamiento, calibración y evaluación.
Si no alcanza la historia, la corrida explica el problema. El corte no puede superar la última fecha efectiva
de cierre o encuesta del archivo.

Para el conjunto original, se usa `SIMTEC_DATASET` si esa variable está definida; si no, `Dataset/` del repositorio
con los CSV completos y, como alternativa, `G:\SIMtec\Dataset`. Los datos crudos son de solo lectura.

### Entrenamiento

1. Confirmá el conjunto y las fechas. **Diagnóstico técnico** permite revisar el entorno y las rutas.
2. Presioná **Entrenar y priorizar**. Procesa los CSV, entrena y evalúa el modelo, calcula SHAP y aplica el segundo
   filtro de contactos. Muestra la etapa actual, tiempo transcurrido y registro en vivo; permite cancelar.
3. Al terminar, seguí **Ver resultados y contactos**. El historial conserva el estado, duración y registro de cada
   ejecución. Se puede navegar durante el proceso; Resultados y Eficiencia esperan a que termine la corrida activa.

Si ya hay un modelo calculado, **Actualizar contactos** reaplica solo el segundo filtro con el scoring y SHAP
existentes. No vuelve a entrenar. Solo puede ejecutarse un proceso a la vez.

Los **Análisis complementarios** (auditoría de leakage y robustez, sensibilidad, análisis exploratorio, notebooks
y diccionario) están disponibles para el conjunto original después del pipeline. Los documentos finales también
corresponden al estudio original.

### Resultados

La vista principal muestra los clientes seleccionados por el **segundo filtro**, con búsqueda por identificador,
filtros combinados por estado, grupo y concesionario, detalle del cliente y descarga en CSV de la vista filtrada.
Cada fila conserva `customer_id`, `vehicle_id`, fecha de scoring, probabilidad de abandono (0 a 1), grupo y los tres
motivos SHAP. Las pestañas internas permiten revisar la auditoría por vehículo y el análisis inicial completo.

El primer análisis divide el ranking en Alto (20 %), Medio (30 %) y Bajo (50 %): son fracciones del ranking, no
umbrales de probabilidad. El segundo reúne Alto + Medio, aplica reglas de disponibilidad e identificación y
consolida un vehículo representativo por cliente. La capacidad inicial es 3.000 clientes por corrida; el resto
de los elegibles queda en espera. Es una **prioridad operativa explicable**, no una estimación del efecto de llamar.
Conserva la probabilidad y SHAP del primer modelo. Las reglas se documentan en el README del proyecto.

### Eficiencia del modelo

Reúne métricas de calidad y calibración, capacidad, tiempos registrados por etapa, controles de leakage y SHAP
global y por caso. Al pasar el cursor por los encabezados o las ayudas de métricas y SHAP aparece una explicación
de su significado y unidad. Los SHAP se muestran en log-odds del modelo base, no en puntos de probabilidad.
Los controles de leakage distinguen la evidencia disponible de las verificaciones pendientes.

Las métricas predictivas corresponden al primer modelo. Sin datos de campañas con grupo de comparación, no se
mide el retorno adicional causado por contactar. Los tiempos nuevos se guardan en
`reports/modelo/tiempos_pipeline.json`; las ejecuciones antiguas solo muestran las duraciones que se registraron.

## 6. Problemas posibles y su solución

**1. Los CSV pesan ~130 bytes / el diagnóstico dice "es un puntero de Git LFS".** Se clonó sin Git LFS, y en lugar
de los datos llegaron punteros. Solución, desde la raíz del clon:

```
git lfs install
git lfs pull
dir Dataset\*.csv
```

(tienen que quedar con los tamaños del paso 2). Si existe la carpeta compartida `G:\SIMtec\Dataset`, el código la
usa automáticamente cuando el `Dataset/` del repo sólo tiene punteros; en una máquina nueva no existe, así que hay
que hacer el `git lfs pull`.

**2. Faltan resultados o métricas.** Es lo esperado al clonar: falta ejecutar **Entrenar y priorizar** (paso 5).

**3. Los análisis complementarios están deshabilitados o no aparecen.** Requieren el pipeline del conjunto
original. No están disponibles para los conjuntos cargados.

**4. `py -3.12` dice que no encuentra esa versión.** Falta Python 3.12: instalarlo, o usar la variante A (uv), que
lo descarga sola.

**5. `abrir_app.bat` dice "No existe el entorno ..\.venv".** Se saltó el paso 3, o el entorno se creó en otra
carpeta: tiene que estar en `desafio-1-repurchase-propensity\.venv`.

**6. La webapp no abre: el puerto 8510 está ocupado.** Hay otra webapp abierta (otra terminal con `abrir_app.bat`).
Cerrarla, o abrir en otro puerto desde `desafio-1-repurchase-propensity\webapp`:
`..\.venv\Scripts\python.exe -m streamlit run demo.py --server.port 8511`.

**7. Mensajes en la consola que no son errores:**
- `[notice] A new release of pip is available`: aviso de pip, se puede ignorar.
- `ConnectionResetError: [WinError 10054]`: aparece al cerrar una pestaña del navegador; no afecta nada.
- `UserWarning: LightGBM binary classifier with TreeExplainer shap values output has changed`: aviso de la
  librería SHAP durante el pipeline; no cambia los resultados.

## 7. Qué NO se puede reconstruir en otra máquina

- `reports/revision_cruzada/`: la comparación con la solución independiente necesita una carpeta que no está en el
  repo (`G:\SIMtec-astra`). Esos 11 archivos siguen versionados como evidencia archivada y sus scripts no tienen botón.
- Los 12 informes narrativos de `reports/eda/` (`<tema>.md` y `<tema>_verificacion.md`) y los documentos de `docs/`:
  los escribió una persona, no un script, así que se versionan.
- El generador del informe (`scripts/build_informe_docx.py`) necesita Microsoft Word; no tiene botón. Los documentos
  finales se abren directamente desde `entregables/`: `informe_final_SIMtec.docx` y
  `FIC_III_Desafio_1_Equipo_SIMtec.pptx`. El script regenera el informe base del estudio; no incorpora automáticamente
  las actualizaciones editoriales del segundo filtro y del flujo de la aplicación agregadas a los entregables.

## 8. Chequeos automáticos (opcional)

Sin iniciar un servidor, desde `desafio-1-repurchase-propensity`:

```
.venv\Scripts\python.exe webapp\chequeos\contacto.py
.venv\Scripts\python.exe webapp\chequeos\resultados_filtros.py
.venv\Scripts\python.exe webapp\chequeos\eficiencia.py
.venv\Scripts\python.exe webapp\chequeos\contactos_ui.py
.venv\Scripts\python.exe webapp\chequeos\datasets.py
```

`contactos_ui.py` necesita las salidas locales del pipeline. `datasets.py` usa una carpeta temporal y ejecuta
ambas etapas con los datos originales como conjunto nuevo para verificar carga, validación y aislamiento.

Para una comprobación visual, con la aplicación ya abierta por vos, desde `desafio-1-repurchase-propensity\webapp`:

```
..\.venv\Scripts\python.exe -m pip install playwright
..\.venv\Scripts\python.exe chequeos\recorrido.py
```

`recorrido.py` abre las cuatro secciones actuales y falla si alguna muestra una excepción de Streamlit
(usa el Chrome instalado; no descarga navegadores).

## 9. Para quien modifique el código de esta rama

- **Compilar los `.py` antes de commitear.** En la prueba se subió una vez un error de sintaxis que rompió la página
  de Corridas durante un minuto. Un control rápido, desde la raíz del repo (Git Bash):
  `for f in $(git ls-files "*.py"); do desafio-1-repurchase-propensity/.venv/Scripts/python.exe -m py_compile "$f" || echo "ERROR: $f"; done`
- Si algo nuevo queda "sin seguimiento" sin motivo, revisar el `.gitignore` global de la máquina: en una de las
  máquinas del equipo ignora cualquier carpeta llamada `pruebas/` (por eso los chequeos están en `chequeos/`).
- Las salidas generadas no se commitean: si aparecen en `git status`, falta una regla en el `.gitignore`.

## Anexo: cómo se hizo la prueba y qué se corrigió en el camino

**Evidencia histórica de la versión anterior a la reorganización de la aplicación y al segundo filtro.**
Prueba hecha el 01/10/2026 en `G:\SIMtec-prueba-limpia`: clon de `franco/webapp-demo` desde GitHub, entorno desde cero por las
dos variantes, webapp abierta sin salidas (las 8 páginas de entonces cargaban y mandaban a Corridas), los 6 botones corridos desde la
webapp (6 de 6 sin errores), los 146 archivos que no se versionan regenerados (146 de 146), comparación con la entrega
7 de 7 idénticas, `git status` del clon con 0 cambios, y los dos chequeos automáticos de esa versión pasando.
No representa una nueva medición de la aplicación actual.

| Proceso histórico | Tiempo medido |
|---|---|
| Pipeline de la versión del 01/10/2026 | 1:19 |
| Análisis exploratorio | 8:56 |
| Notebooks de evidencia | 0:50 |
| Diccionario del dataset | 0:04 |
| Sensibilidad de la ventana | 3:04 |
| Ablaciones | 1:04 |
| Recalcular todo (sin el informe) | ~15 min |

Lo que se corrigió en la rama a partir de la prueba:

- Un clon sin Git LFS tomaba los punteros como datos aunque existiera la carpeta compartida (problema 1): ahora una
  carpeta sólo se usa si tiene los CSV con datos reales.
- La tabla del diagnóstico del entorno se veía como listas JSON; y su primer arreglo subió un error de sintaxis que
  se corrigió en el commit siguiente.
- Los tiempos de los botones se ajustaron a lo medido en el clon limpio.

Dos problemas de la prueba fueron de cómo se armó (no le pasan a quien sigue estos pasos): un enlace duro entre
unidades de disco distintas en un script de prueba, y una instalación con pip que se cortó porque se lanzó mal en
segundo plano; repetida bien, terminó en 119 s.
