"""Prueba la política de contacto sin datos privados ni servidor Streamlit."""
from pathlib import Path
import hashlib
import json
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

PROYECTO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROYECTO / "src"))
from repurchase.contacto import ARCHIVOS, generar_contactos, guardar_contactos  # noqa: E402


def fila(cliente="c1", vehiculo="v1", **cambios):
    return {"customer_id": cliente, "vehicle_id": vehiculo, "segmento": "Alto", "prob_churn": 0.8,
            "fecha_scoring": pd.Timestamp("2026-08-26"), "tiene_turno_agendado": False,
            "dias_restantes_horizonte": 30, "n_maint": 2, "last_maint_dealer": "d1",
            "days_since_last_maint": 365,
            "driver_1": "Motivo original 1", "driver_2": "Motivo original 2", "driver_3": "Motivo original 3",
            "driver_1_feature": "tma", "driver_1_shap": 0.6,
            "driver_2_feature": "vehicle_age_days", "driver_2_shap": -0.4,
            "driver_3_feature": "region", "driver_3_shap": 0.2, **cambios}


class ContactoTests(unittest.TestCase):
    def test_elegible_gana_y_capacidad_cuenta_clientes(self):
        s = pd.DataFrame([fila("c1", "turno", prob_churn=1, tiene_turno_agendado=True),
                          fila("c1", "elegible", segmento="Medio", prob_churn=0.6),
                          fila("c1", "otro", prob_churn=0.5), fila("c2", "v2", prob_churn=0.7),
                          fila("c3", "v3", n_maint=0)])
        candidatos, clientes, resumen = generar_contactos(s, capacidad=1)
        self.assertEqual(len(clientes), 3)
        self.assertEqual(clientes.set_index("customer_id").loc["c1", "vehicle_id"], "elegible")
        self.assertEqual(clientes.set_index("customer_id").loc["c1", "n_vehiculos_cliente"], 3)
        self.assertEqual(clientes.set_index("customer_id").loc["c1", "grupos_cliente"], "Alto | Medio")
        self.assertEqual(resumen["clientes_seleccionados"], 1)
        self.assertEqual(resumen["clientes_en_espera"], 1)
        self.assertEqual(candidatos["seleccionado"].sum(), 1)
        self.assertFalse(candidatos.loc[candidatos.vehicle_id.eq("turno"), "representante"].iloc[0])
        self.assertEqual(clientes.loc[clientes.seleccionado, "customer_id"].tolist(), ["c2"])

    def test_estados_y_probabilidad_uno_no_descarta(self):
        s = pd.DataFrame([fila("c1", "seguro", prob_churn=1), fila("c2", "turno", tiene_turno_agendado=True),
                          fila("c3", "limite", dias_restantes_horizonte=14),
                          fila("c4", "tarde", dias_restantes_horizonte=13), fila(None, "sin_id"),
                          fila("  ", "id_blanco"), fila("c5", "sin_dealer", last_maint_dealer=None),
                          fila("c6", "sin_historia", n_maint=0),
                          fila("c7", "sin_margen", dias_restantes_horizonte=None),
                          fila("c8", "turno_desconocido", tiene_turno_agendado=None),
                          fila("c9", "prob_invalida", prob_churn=float("inf"))])
        candidatos, clientes, _ = generar_contactos(s)
        estados = candidatos.set_index("vehicle_id").estado_contacto.to_dict()
        self.assertEqual(estados, {"seguro": "Contactar", "turno": "Con turno", "limite": "Contactar",
                                  "tarde": "Sin margen", "sin_id": "Sin identificador", "id_blanco": "Sin identificador",
                                  "sin_dealer": "Revisar", "sin_historia": "Revisar", "sin_margen": "Revisar",
                                  "turno_desconocido": "Revisar", "prob_invalida": "Revisar"})
        self.assertTrue(clientes.loc[clientes.vehicle_id.eq("seguro"), "seleccionado"].iloc[0])
        self.assertEqual(len(clientes), 9)

    def test_orden_estable_shap_positivo_y_vinculo(self):
        s = pd.DataFrame([fila("c1", "alta", prob_churn=1),
                          fila("c2", "accion", prob_churn=0.5, driver_1_feature="n_cancel", driver_1_shap=0.1),
                          fila("c3", "negativo", prob_churn=0.9, driver_1_feature="n_cancel", driver_1_shap=-0.1),
                          fila("c4", "antiguo", prob_churn=1, days_since_last_maint=731),
                          fila("c5", "empate_b", prob_churn=0.8), fila("c5", "empate_a", prob_churn=0.8)])
        a, c, _ = generar_contactos(s)
        b, d, _ = generar_contactos(s.sample(frac=1, random_state=12))
        pd.testing.assert_frame_equal(a, b)
        pd.testing.assert_frame_equal(c, d)
        self.assertEqual(c.vehicle_id.tolist(), ["accion", "alta", "negativo", "empate_a", "antiguo"])
        self.assertFalse(c.loc[c.vehicle_id.eq("negativo"), "shap_accionable"].iloc[0])

    def test_solo_alto_medio_sin_mutar_probabilidad_o_shap(self):
        s = pd.DataFrame([fila(), fila("c2", "v2", segmento="Medio"), fila("c3", "v3", segmento="Bajo")])
        copia = s.copy(deep=True)
        a, _, r = generar_contactos(s)
        pd.testing.assert_frame_equal(s, copia)
        self.assertEqual(set(a.vehicle_id), {"v1", "v2"})
        pd.testing.assert_frame_equal(a[s.columns].sort_values("vehicle_id").reset_index(drop=True),
                                      s[s.segmento.ne("Bajo")].sort_values("vehicle_id").reset_index(drop=True))
        self.assertEqual(r["fuera_de_alcance"], 1)
        self.assertEqual(sum(r["estados_vehiculos"].values()), len(a))

    def test_vacio_capacidad_cero_y_politica(self):
        s = pd.DataFrame([fila(segmento="Bajo")])
        a, c, r = generar_contactos(s)
        self.assertTrue(a.empty and c.empty)
        self.assertEqual(r["clientes_elegibles"], 0)
        _, c, r = generar_contactos(pd.DataFrame([fila()]), capacidad=0)
        self.assertEqual(r["clientes_en_espera"], 1)
        self.assertFalse(c.seleccionado.any())
        a, _, _ = generar_contactos(pd.DataFrame([fila(dias_restantes_horizonte=20)]), {"min_dias_restantes": 21})
        self.assertEqual(a.estado_contacto.iloc[0], "Sin margen")
        for capacidad in (-1, 1.5, True):
            with self.assertRaises(ValueError):
                generar_contactos(s, capacidad=capacidad)

    def test_columnas_operativas_faltantes_requieren_revision_y_guardado(self):
        s = pd.DataFrame([fila()]).drop(columns=["n_maint", "tiene_turno_agendado"])
        a, _, _ = generar_contactos(s)
        self.assertEqual(a.estado_contacto.iloc[0], "Revisar")
        with tempfile.TemporaryDirectory(prefix="simtec-contacto-") as temporal:
            carpeta = Path(temporal).resolve()
            guardar_contactos(s, carpeta)
            self.assertEqual({p.name for p in carpeta.iterdir()}, set(ARCHIVOS))
            pd.testing.assert_frame_equal(pd.read_parquet(carpeta / "candidatos_contacto.parquet"), a)

    def test_huella_y_fallo_no_publican_entrega_parcial(self):
        s = pd.DataFrame([fila()])
        with tempfile.TemporaryDirectory(prefix="simtec-contacto-") as temporal:
            carpeta = Path(temporal).resolve()
            fuente = carpeta / "scores_actuales.parquet"
            fuente.write_bytes(b"fuente para comprobar la huella")
            guardar_contactos(s, carpeta)
            resumen = carpeta / "contacto_resumen.json"
            previo = resumen.read_bytes()
            self.assertEqual(json.loads(previo)["scores_sha256"], hashlib.sha256(fuente.read_bytes()).hexdigest())
            # Un fallo al preparar no toca la entrega anterior ni deja archivos temporales.
            with patch.object(pd.DataFrame, "to_parquet", side_effect=OSError("sin espacio")):
                with self.assertRaises(OSError):
                    guardar_contactos(s, carpeta)
            self.assertEqual(resumen.read_bytes(), previo)
            self.assertFalse(list(carpeta.glob("*.tmp")))
            # Si falla la publicación, la falta de manifiesto impide servir tablas mezcladas.
            reemplazar = Path.replace

            def fallo_al_publicar(path, destino):
                if path.name.startswith(".contactos_por_cliente.parquet."):
                    raise OSError("archivo ocupado")
                return reemplazar(path, destino)

            with patch.object(Path, "replace", fallo_al_publicar):
                with self.assertRaises(OSError):
                    guardar_contactos(s, carpeta)
            self.assertFalse(resumen.exists())
            self.assertFalse(list(carpeta.glob("*.tmp")))


if __name__ == "__main__":
    unittest.main(verbosity=2)
