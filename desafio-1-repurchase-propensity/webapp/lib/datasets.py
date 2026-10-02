"""Catálogo local de datasets: archivos inmutables y resultados aislados por conjunto."""
from __future__ import annotations

import csv
import hashlib
import json
import os
import shutil
import uuid
from datetime import date, datetime
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.csv as pacsv
import streamlit as st

PROYECTO = Path(os.environ.get("SIMTEC_REPO", Path(__file__).resolve().parents[2])).resolve()
CATALOGO = PROYECTO / "data" / "datasets"
VENTAS = "ranger_sales_arg_2024_2026.csv"
AGENDA = "ranger_service_agenda_arg_2024_2026 1.csv"


def original() -> dict:
    raw = Path(os.environ.get("SIMTEC_DATASET", PROYECTO.parent / "Dataset"))
    if not os.environ.get("SIMTEC_DATASET") and not all(
        (raw / nombre).is_file() and (raw / nombre).stat().st_size >= 1024 for nombre in (VENTAS, AGENDA)
    ):
        compartida = Path(r"G:\SIMtec\Dataset")
        if all((compartida / nombre).is_file() and (compartida / nombre).stat().st_size >= 1024
               for nombre in (VENTAS, AGENDA)):
            raw = compartida
    return {"id": "original", "nombre": "Dataset original", "raw": raw,
            "resultados": PROYECTO, "cutoff": "2026-08-25", "params": PROYECTO / "config" / "params.json"}


def catalogo() -> list[dict]:
    out = [original()]
    for p in sorted(CATALOGO.glob("*/dataset.json")):
        meta = json.loads(p.read_text(encoding="utf8"))
        meta.update(raw=p.parent / "raw", resultados=p.parent / "resultados", params=p.parent / "params.json")
        out.append(meta)
    return out


def activo() -> dict:
    elegido = st.session_state.get("dataset_id")
    if elegido is None:
        try:
            elegido = json.loads((CATALOGO / "seleccion.json").read_text(encoding="utf8"))["id"]
        except (FileNotFoundError, KeyError, json.JSONDecodeError):
            elegido = "original"
    d = next((d for d in catalogo() if d["id"] == elegido), original())
    st.session_state.setdefault("dataset_id", d["id"])
    return d


def seleccionar(identificador: str):
    if identificador not in {d["id"] for d in catalogo()}:
        raise ValueError("No encuentro ese dataset.")
    # Evita conservar vehículos y filtros pertenecientes al conjunto anterior.
    for clave in list(st.session_state):
        if clave not in {"dataset_id", "selector_dataset", "dataset_guardado"}:
            del st.session_state[clave]
    st.session_state["dataset_id"] = identificador
    CATALOGO.mkdir(parents=True, exist_ok=True)
    temporal = CATALOGO / f"seleccion-{uuid.uuid4().hex}.tmp"
    temporal.write_text(json.dumps({"id": identificador}), encoding="utf8")
    temporal.replace(CATALOGO / "seleccion.json")


def _cabecera(path: Path) -> list[str]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return next(csv.reader(f), [])


def validar_csv(path: Path, tipo: str) -> dict:
    """Valida el CSV completo por bloques, sin cargar todo el archivo en memoria."""
    nombre = VENTAS if tipo == "ventas" else AGENDA
    columnas = _cabecera(path)
    esperadas = _cabecera(original()["raw"] / nombre)
    opcionales = {"SalesType", "ScheduleModalityCode", "CancellationReason", "Quicklane"}
    faltan = sorted(set(esperadas) - opcionales - set(columnas))
    if not columnas or len(columnas) != len(set(columnas)):
        raise ValueError(f"{tipo}: la cabecera está vacía o tiene columnas duplicadas.")
    if faltan:
        raise ValueError(f"{tipo}: faltan columnas: {', '.join(faltan)}.")
    fechas = (["SalesDate", "DeliveryDate", "RegistrationDate", "WarrantyStartDate"] if tipo == "ventas"
              else ["ScheduleDate", "ScheduleDateTime", "EffectiveCheckinDate", "EffectiveCheckoutDate",
                    "SurveyResponseDate", "WarrantyStartDate"])
    ids = ["vehicle_id", "customer_id"] + (["schedule_id"] if tipo == "agenda" else [])
    filas, minimo, maximo, ultimo_evento = 0, None, None, None
    vacios = {c: 0 for c in ids}
    with pacsv.open_csv(path, read_options=pacsv.ReadOptions(encoding="utf8"),
                        convert_options=pacsv.ConvertOptions(column_types={c: pa.string() for c in columnas})) as reader:
        for bloque in reader:
            df = bloque.to_pandas()
            filas += len(df)
            for c in ids:
                vacios[c] += int(df[c].fillna("").str.strip().eq("").sum())
            for c in fechas:
                values = df[c].fillna("").str.strip()
                parsed = pd.to_datetime(values, errors="coerce", utc=True, format="mixed")
                if (values.ne("") & parsed.isna()).any():
                    raise ValueError(f"{tipo}: hay fechas inválidas en {c}.")
                if parsed.notna().any():
                    lo, hi = parsed.min().date(), parsed.max().date()
                    minimo = min(minimo, lo) if minimo else lo
                    maximo = max(maximo, hi) if maximo else hi
                    if c in {"EffectiveCheckoutDate", "SurveyResponseDate"}:
                        ultimo_evento = max(ultimo_evento, hi) if ultimo_evento else hi
    if not filas:
        raise ValueError(f"{tipo}: el archivo no contiene filas.")
    for c, n in vacios.items():
        if n == filas:
            raise ValueError(f"{tipo}: todos los identificadores vacíos en {c}.")
    return {"filas": filas, "identificadores_vacios": vacios, "desde": str(minimo) if minimo else None,
            "hasta": str(maximo) if maximo else None,
            "ultimo_evento": str(ultimo_evento) if ultimo_evento else None}


def guardar(nombre: str, ventas, agenda, cutoff: date, train_end: date, valid_end: date) -> dict:
    nombre = nombre.strip()
    if not nombre or len(nombre) > 100:
        raise ValueError("Ingresá un nombre de entre 1 y 100 caracteres.")
    if any(d["nombre"].casefold() == nombre.casefold() for d in catalogo()):
        raise ValueError("Ya existe un conjunto con ese nombre. Elegí otro nombre para distinguirlos.")
    if not train_end < valid_end < cutoff:
        raise ValueError("Las fechas deben estar en orden: entrenamiento < calibración < corte de datos.")
    if ventas is None or agenda is None:
        raise ValueError("Seleccioná los dos archivos: ventas y agenda de servicios.")
    identificador = uuid.uuid4().hex
    carpeta = CATALOGO / identificador
    raw = carpeta / "raw"
    raw.mkdir(parents=True)
    try:
        resumen = {}
        for tipo, archivo, destino in (("ventas", ventas, VENTAS), ("agenda", agenda, AGENDA)):
            archivo.seek(0)
            digest = hashlib.sha256()
            with (raw / destino).open("wb") as f:
                while chunk := archivo.read(1024 * 1024):
                    f.write(chunk)
                    digest.update(chunk)
            resumen[tipo] = {**validar_csv(raw / destino, tipo), "archivo": Path(archivo.name).name,
                             "sha256": digest.hexdigest(), "bytes": (raw / destino).stat().st_size}
        if not resumen["agenda"]["ultimo_evento"]:
            raise ValueError("La agenda no contiene fechas de cierre o encuesta para evaluar el modelo.")
        if cutoff > date.fromisoformat(resumen["agenda"]["ultimo_evento"]):
            raise ValueError("El corte de datos no puede superar la última fecha efectiva de cierre o encuesta: "
                             + resumen["agenda"]["ultimo_evento"] + ".")
        params = json.loads((PROYECTO / "config" / "params.json").read_text(encoding="utf8"))
        params["split"] = {"train_end": str(train_end), "valid_end": str(valid_end)}
        (carpeta / "params.json").write_text(json.dumps(params, ensure_ascii=False, indent=2), encoding="utf8")
        meta = {"id": identificador, "nombre": nombre, "creado": datetime.now().isoformat(timespec="seconds"),
                "cutoff": str(cutoff), "archivos": resumen, "split": params["split"]}
        (carpeta / "dataset.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf8")
        return meta
    except Exception:
        shutil.rmtree(carpeta)
        raise


def selector():
    opciones = catalogo()
    ids = [d["id"] for d in opciones]
    nombres = {d["id"]: d["nombre"] for d in opciones}
    actual = activo()["id"]
    with st.sidebar:
        elegido = st.selectbox("Dataset activo", ids, index=ids.index(actual),
                               format_func=nombres.get, key="selector_dataset")
        if elegido != actual:
            seleccionar(elegido)
            st.rerun()
        st.caption("Las páginas y las corridas usan este conjunto.")
