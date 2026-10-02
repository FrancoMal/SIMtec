# EMPEZAR ACÁ: correr el proyecto desde cero en una máquina nueva

Rama `franco/webapp-demo` · Desafío 1 (Repurchase / retención de service) · Equipo SIMtec

Estas instrucciones se escribieron **después** de hacer exactamente estos pasos en una carpeta limpia: clon nuevo
desde GitHub, entorno nuevo, sin reusar nada de otra carpeta. Los tiempos son los medidos en esa prueba (Windows 11):
sirven para saber si algo está tardando o se colgó.

> **Lo más importante.** El repositorio NO trae resultados (figuras, tablas, modelo, scores): se recalculan en cada
> máquina. **Después de instalar, lo primero es correr el Pipeline completo (1 min 20 s).** Si abrís la webapp antes,
> las páginas del recorrido dicen "Todavía no hay resultados": no está roto, falta ese paso.

Resumen del tiempo total: clon ~1 min + entorno ~2,5 min + pipeline ~1,5 min = **la demo funcionando en ~5 minutos**.
Recalcular todo lo demás suma ~14 minutos más (opcional).

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

## 2. Clonar la rama · medido: 64 s

En PowerShell o CMD, en la carpeta donde quieras el proyecto:

```
git lfs install
git clone --branch franco/webapp-demo https://github.com/FrancoMal/SIMtec.git SIMtec
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

## 3. Crear el entorno · medido: 2 a 2,5 min

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
(sólo mínimos): con el lock, los resultados salen idénticos a los entregados.

Verificación (tiene que imprimir `3.0.5 4.7.0 1.64.0`):

```
.venv\Scripts\python.exe -c "import pandas, lightgbm, streamlit; print(pandas.__version__, lightgbm.__version__, streamlit.__version__)"
```

## 4. Abrir la webapp

```
cd webapp
abrir_demo.bat
```

Se abre el navegador en http://localhost:8510. Para cerrarla: Ctrl+C en esa terminal o cerrar la ventana.

## 5. Recalcular: primero el pipeline

### Cargar y elegir otros datasets desde la demo

**Lista completa** muestra todos los vehículos del ranking del dataset activo. Permite alternar entre todos
y los grupos Alto, Medio y Bajo (por defecto, 20 %, 30 % y 50 % de la lista priorizada). Estos porcentajes son
fracciones del ranking, no umbrales de probabilidad. Cada fila incluye `customer_id`, `vehicle_id`, fecha de
scoring, probabilidad entre 0 y 1, grupo y los tres motivos SHAP. Se puede buscar por identificador, mostrar
datos adicionales (fechas, turno, concesionario y aportes SHAP) y descargar la vista o la lista completa en CSV.

En **Datasets**, cargá un CSV de ventas y otro de agenda de servicios, poné un nombre al conjunto y elegí las
fechas de entrenamiento, calibración y corte de datos. Los nombres de los archivos pueden ser distintos a los
originales; deben conservar las columnas del extracto de Ford (la página muestra las necesarias), el formato CSV
separado por comas y la codificación UTF-8. Se admiten hasta 1 GB por archivo.

**Validar y guardar** revisa ambos archivos completos: cabeceras, identificadores, fechas y cantidad de filas.
También guarda los nombres originales y las huellas SHA-256 para identificar los datos utilizados. Después usá
**Usar el conjunto recién cargado** o el selector **Dataset activo** del menú lateral.

En **Corridas**, ejecutá **Pipeline completo**. Cada conjunto tiene su propia carpeta bajo
`desafio-1-repurchase-propensity/data/datasets/<id>/`, con archivos originales, configuración y resultados.
Cambiar de conjunto cambia las páginas, el ranking, el dashboard y el historial de corridas. Volver a
**Dataset original** recupera los resultados anteriores; los CSV originales no se reemplazan.

Las fechas elegidas deben dejar ventanas evaluables con retornos y abandonos en entrenamiento, calibración y
evaluación. Si no alcanza la historia, la corrida explica el problema. El corte no puede superar la última fecha
efectiva de cierre o encuesta del archivo. Cada registro de corrida identifica el conjunto, sus rutas y su corte.

Para conjuntos cargados se habilita el pipeline (modelo, evaluación, ranking, gráficos y evidencia). Los análisis
complementarios, la comparación con la entrega y los documentos finales corresponden al estudio original.
Los datos cargados y sus resultados permanecen en esta máquina y están ignorados por Git.

Para comprobar los cambios sin levantar el servidor: desde `desafio-1-repurchase-propensity`, ejecutá
`.venv\Scripts\python.exe webapp\chequeos\datasets.py`. El chequeo usa una carpeta temporal y prueba carga,
validación, selección, aislamiento de resultados y un pipeline con los datos originales como conjunto nuevo.

En la webapp, menú de la izquierda, abajo: **Corridas (recalcular)**.

1. Abrí **Diagnóstico del entorno** y confirmá: Python 3.12.x, "Datos crudos" apuntando a la carpeta `Dataset` de
   tu clon, los dos CSV en "ok" (11.5 MB y 281.8 MB).
2. Botón **Correr** de **Pipeline completo**. Se ve el log en vivo y se puede seguir navegando mientras corre.
   Termina con `listo. resumen en ...\reports\modelo\resumen.md`.
3. Recién ahí el recorrido de la demo (Inicio → Bandeja → Caso guiado → Resultados) tiene datos.

Tiempos medidos de cada botón en la prueba desde cero (corre uno a la vez; todos terminaron sin errores):

| Botón | Medido | Qué genera |
|---|---|---|
| **Pipeline completo** (primero, obligatorio) | **1:19** | datos procesados, modelo, scores, 7 figuras y resumen del modelo |
| Análisis exploratorio | **8:56** | 13 análisis: 55 figuras y 72 tablas de `reports/` |
| Notebooks de evidencia | **0:50** | los 3 notebooks ejecutados |
| Diccionario del dataset | **0:04** | `docs/diccionario_dataset_analitico.md` |
| Sensibilidad de la ventana | **3:04** | `reports/modelo/sensibilidad_ventana.csv` (36 combinaciones) |
| Ablaciones | **1:04** | `reports/modelo/ablaciones.csv` y `.md` |
| Recalcular todo (sin el informe) | ~15 min | todo lo anterior, en orden |

Si un botón tarda más del doble de lo medido, mirá el log en la misma página: ahí aparece el error.

**Al final, en la misma página: Comparar ahora.** Compara las cifras calculadas en tu máquina con las de la entrega
(`webapp/referencia_entrega.json`): métricas, capacidad de contacto, lift, segmentos, ROI, ablaciones y sensibilidad.
**En la prueba desde cero dio 7 de 7 salidas idénticas.** Si a vos te da distinto, algo cambió en el entorno
(lo más probable: no se instaló con `requirements-lock.txt`).

Después de recalcular, `git status` sigue sin cambios: todas las salidas están en `.gitignore`.

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

**2. Todas las páginas dicen "Todavía no hay resultados".** Es lo esperado al clonar: falta correr el Pipeline
completo (paso 5).

**3. Los botones de Análisis exploratorio, Notebooks, etc. aparecen deshabilitados.** Dependen de lo que genera el
pipeline: se habilitan cuando termina.

**4. `py -3.12` dice que no encuentra esa versión.** Falta Python 3.12: instalarlo, o usar la variante A (uv), que
lo descarga sola.

**5. `abrir_demo.bat` dice "No existe el entorno ..\.venv".** Se saltó el paso 3, o el entorno se creó en otra
carpeta: tiene que estar en `desafio-1-repurchase-propensity\.venv`.

**6. La webapp no abre: el puerto 8510 está ocupado.** Hay otra webapp abierta (otra terminal con `abrir_demo.bat`).
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
- El informe (`scripts/build_informe_docx.py`): necesita Microsoft Word; no tiene botón. Los documentos finales están
  en `entregables/` y se descargan desde la página Documentos de la webapp.

## 8. Chequeos automáticos (opcional)

Con la webapp abierta, desde `desafio-1-repurchase-propensity\webapp`:

```
..\.venv\Scripts\python.exe -m pip install playwright
..\.venv\Scripts\python.exe chequeos\recorrido.py
```

`recorrido.py` abre las 8 páginas y falla si alguna muestra un error (usa el Chrome instalado; no descarga
navegadores). `chequeos\interaccion.py` además prueba bandeja → caso guiado y lanza un pipeline en segundo plano
mientras navega.

## 9. Para quien modifique el código de esta rama

- **Compilar los `.py` antes de commitear.** En la prueba se subió una vez un error de sintaxis que rompió la página
  de Corridas durante un minuto. Un control rápido, desde la raíz del repo (Git Bash):
  `for f in $(git ls-files "*.py"); do desafio-1-repurchase-propensity/.venv/Scripts/python.exe -m py_compile "$f" || echo "ERROR: $f"; done`
- Si algo nuevo queda "sin seguimiento" sin motivo, revisar el `.gitignore` global de la máquina: en una de las
  máquinas del equipo ignora cualquier carpeta llamada `pruebas/` (por eso los chequeos están en `chequeos/`).
- Las salidas generadas no se commitean: si aparecen en `git status`, falta una regla en el `.gitignore`.

## Anexo: cómo se hizo la prueba y qué se corrigió en el camino

Prueba hecha el 01/10/2026 en `G:\SIMtec-prueba-limpia`: clon de esta rama desde GitHub, entorno desde cero por las
dos variantes, webapp abierta sin salidas (las 8 páginas cargan y mandan a Corridas), los 6 botones corridos desde la
webapp (6 de 6 sin errores), los 146 archivos que no se versionan regenerados (146 de 146), comparación con la entrega
7 de 7 idénticas, `git status` del clon con 0 cambios, y los dos chequeos automáticos pasando.

Lo que se corrigió en la rama a partir de la prueba:

- Un clon sin Git LFS tomaba los punteros como datos aunque existiera la carpeta compartida (problema 1): ahora una
  carpeta sólo se usa si tiene los CSV con datos reales.
- La tabla del diagnóstico del entorno se veía como listas JSON; y su primer arreglo subió un error de sintaxis que
  se corrigió en el commit siguiente.
- Los tiempos de los botones se ajustaron a lo medido en el clon limpio.

Dos problemas de la prueba fueron de cómo se armó (no le pasan a quien sigue estos pasos): un enlace duro entre
unidades de disco distintas en un script de prueba, y una instalación con pip que se cortó porque se lanzó mal en
segundo plano; repetida bien, terminó en 119 s.
