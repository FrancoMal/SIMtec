@echo off
setlocal EnableDelayedExpansion
chcp 65001 >nul
title FIC III - Desafio 1 - SIMtec
cd /d "%~dp0"

set PYTHONIOENCODING=utf8
set PYTHONPATH=src
set PY=.venv\Scripts\python.exe

if not exist "%PY%" (
    echo No existe el entorno .venv. Crealo una vez con:
    echo    uv venv --python 3.12 .venv ^&^& uv pip install --python .venv\Scripts\python.exe -r requirements.txt
    echo o con:
    echo    py -3.12 -m venv .venv ^&^& .venv\Scripts\python.exe -m pip install -r requirements.txt
    pause
    exit /b 1
)

:: Uso directo sin menu: ejecutar.bat pipeline | notebooks | informe | diccionario | complementarios | dashboard | todo
if not "%~1"=="" (
    set OPCION=%~1
    goto :correr
)

:menu
echo.
echo  ==========================================================
echo   FIC III - Desafio 1 - Repurchase / retencion de service
echo  ==========================================================
echo   1. Pipeline completo (CSV -^> ventanas -^> features -^> modelo -^> scoring)   ~3 min
echo   2. Notebooks de evidencia (generar y ejecutar)
echo   3. Informe oficial (docx sobre el template de Ford + PDF, usa Word)
echo   4. Diccionario del dataset analitico
echo   5. Dashboard (Streamlit, abre en el navegador)
echo   6. Todo en orden: 1, 2, 4, 3
echo   7. Analisis complementarios (sensibilidad de ventana + ablaciones)   ~15 min
echo   8. Solo ver el resumen de las salidas actuales (sin correr nada)
echo   0. Salir
echo.
set /p OPCION=Opcion:
if "%OPCION%"=="0" exit /b 0

:correr
if /i "%OPCION%"=="1" set OPCION=pipeline
if /i "%OPCION%"=="2" set OPCION=notebooks
if /i "%OPCION%"=="3" set OPCION=informe
if /i "%OPCION%"=="4" set OPCION=diccionario
if /i "%OPCION%"=="5" set OPCION=dashboard
if /i "%OPCION%"=="6" set OPCION=todo
if /i "%OPCION%"=="7" set OPCION=complementarios
if /i "%OPCION%"=="8" set OPCION=resumen

:: marca de inicio (segundos epoch) para que el resumen distinga lo generado ahora de lo viejo
"%PY%" scripts\resumen_salidas.py --inicio
set HECHO=

if /i "%OPCION%"=="pipeline"        call :paso "Pipeline completo" scripts\run_pipeline.py
if /i "%OPCION%"=="notebooks"       call :paso "Notebooks" scripts\build_notebooks.py
if /i "%OPCION%"=="informe"         call :paso "Informe docx + PDF" scripts\build_informe_docx.py
if /i "%OPCION%"=="diccionario"     call :paso "Diccionario del dataset" scripts\diccionario_dataset.py
if /i "%OPCION%"=="complementarios" (
    call :paso "Sensibilidad de ventana" scripts\sensibilidad_ventana.py
    call :paso "Ablaciones" scripts\ablaciones.py
)
if /i "%OPCION%"=="todo" (
    call :paso "Pipeline completo" scripts\run_pipeline.py
    call :paso "Notebooks" scripts\build_notebooks.py
    call :paso "Diccionario del dataset" scripts\diccionario_dataset.py
    call :paso "Informe docx + PDF" scripts\build_informe_docx.py
)
if /i "%OPCION%"=="dashboard" (
    echo.
    echo  Abriendo el dashboard. Cerrar esta ventana o Ctrl+C para detenerlo.
    "%PY%" -m streamlit run app\app.py
    goto :fin
)
if /i "%OPCION%"=="resumen" (
    for %%o in (pipeline notebooks diccionario informe) do "%PY%" scripts\resumen_salidas.py %%o --sin-inicio
    goto :fin
)

if not defined HECHO (
    echo Opcion no reconocida: %OPCION%
    if "%~1"=="" goto :menu
    exit /b 1
)

:: cuadro resumen de lo que produjo esta corrida
"%PY%" scripts\resumen_salidas.py %OPCION%

:fin
if "%~1"=="" pause
exit /b 0

:paso
set HECHO=1
echo.
echo  ---- %~1 ----
"%PY%" %2
if errorlevel 1 (
    echo.
    echo  ERROR en "%~1". Revisar el mensaje de arriba. Estado de las salidas:
    "%PY%" scripts\resumen_salidas.py %OPCION%
    if "%~1"=="" pause
    exit /b 1
)
goto :eof
