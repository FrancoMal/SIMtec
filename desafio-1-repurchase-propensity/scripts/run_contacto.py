"""Recalcula sólo el segundo paso desde scores_actuales; no reentrena el modelo.

Respeta SIMTEC_OUTPUT_DIR para conjuntos de datos con resultados separados.
Uso: python scripts/run_contacto.py [--policy config/contacto.json] [--capacidad 3000]
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from repurchase import config  # noqa: E402
from repurchase.contacto import guardar_contactos  # noqa: E402


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy", help="JSON con la politica operativa")
    parser.add_argument("--capacidad", type=int, help="Maximo de clientes seleccionados en esta corrida")
    args = parser.parse_args()
    fuente = config.PROCESSED_DIR / "scores_actuales.parquet"
    if not fuente.is_file():
        parser.error(f"No existe {fuente}. Primero ejecuta el pipeline completo del conjunto elegido.")
    policy = json.loads(Path(args.policy).read_text(encoding="utf8")) if args.policy else None
    _, _, resumen = guardar_contactos(pd.read_parquet(fuente), config.PROCESSED_DIR, policy, args.capacidad)
    print(json.dumps({k: resumen[k] for k in ("candidatos", "clientes_identificados", "clientes_elegibles",
                                             "clientes_seleccionados", "clientes_en_espera", "capacidad_por_corrida")},
                     ensure_ascii=False, indent=2), flush=True)
    print(f"Segundo paso guardado en {config.PROCESSED_DIR}", flush=True)


if __name__ == "__main__":
    main()
