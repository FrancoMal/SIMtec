"""Evidencia, aislamiento y fallos de la medición de tiempos; no levanta servidor."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import pandas as pd

PROYECTO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROYECTO / "webapp"))
from lib.eficiencia import cruces_horizonte, fila_modelo, tabla_shap, telemetria_del_modelo  # noqa: E402


class EvidenciaTests(unittest.TestCase):
    def test_shap_muestra_unidad_original_y_no_proxy(self):
        entrada = pd.DataFrame({"feature": ["a", "b"], "nombre": ["A", "B"],
                                "mean_abs_shap_logodds": [.1, .8], "mean_abs_shap": [90, 2]})
        resultado = tabla_shap(entrada)
        self.assertEqual(resultado["Código"].tolist(), ["b", "a"])
        self.assertEqual(resultado["SHAP absoluto medio"].tolist(), [.8, .1])
        self.assertTrue(tabla_shap(entrada.drop(columns="mean_abs_shap_logodds")).empty)

    def test_no_toma_otro_modelo_si_falta_calibrado(self):
        self.assertFalse(fila_modelo(pd.DataFrame({"modelo": ["LightGBM sin calibrar"], "roc_auc": [.8]})))

    def test_horizontes_cuenta_solo_evaluables_del_periodo(self):
        ventanas = pd.DataFrame({"status": ["evaluable", "evaluable", "evaluable", "censurada"],
            "scoring_date": pd.to_datetime(["2025-09-01", "2025-09-02", "2025-11-01", "2025-09-01"]),
            "horizon_end": pd.to_datetime(["2025-09-30", "2025-10-01", "2026-01-01", "2026-01-01"])})
        tabla = cruces_horizonte(ventanas, {"split": {"train_end": "2025-09-30", "valid_end": "2025-12-31"}})
        self.assertEqual(tabla["Ventanas del período"].tolist(), [2, 1])
        self.assertEqual(tabla["Horizontes que cruzan"].tolist(), [1, 1])
        self.assertEqual(tabla["Proporción"].tolist(), [.5, 1.])

    def test_tiempos_no_se_atribuyen_a_otro_modelo_o_corrida_fallida(self):
        registro = {"estado": "completo", "inicio": "2026-01-01T00:00:00+00:00", "fin": "2026-01-01T00:02:00+00:00"}
        self.assertTrue(telemetria_del_modelo(registro, pd.Timestamp("2026-01-01T00:01:00Z").timestamp()))
        self.assertFalse(telemetria_del_modelo(registro, pd.Timestamp("2025-12-31T00:01:00Z").timestamp()))
        self.assertFalse(telemetria_del_modelo({**registro, "estado": "error"}, pd.Timestamp("2026-01-01T00:01:00Z").timestamp()))


class TelemetriaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location("pipeline_medicion", PROYECTO / "scripts" / "run_pipeline.py")
        cls.pipeline = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.pipeline)

    def test_fallo_guarda_etapa_y_error_sin_ocultarlo(self):
        with tempfile.TemporaryDirectory(dir=PROYECTO / ".venv", prefix="test-eficiencia-") as temporal:
            def falla(_cfg, _neg, _skip, reloj):
                reloj.etapa("primera", "Primera")
                reloj.etapa("entrenamiento", "Entrenamiento")
                raise ValueError("faltan retornos")
            with patch.object(self.pipeline, "REP", Path(temporal)), patch.object(self.pipeline, "_ejecutar", side_effect=falla):
                with self.assertRaisesRegex(ValueError, "faltan retornos"):
                    self.pipeline.main("config/params.json", "config/negocio.json", False)
            registro = json.loads((Path(temporal) / "tiempos_pipeline.json").read_text(encoding="utf8"))
            self.assertEqual(registro["estado"], "error")
            self.assertEqual([e["estado"] for e in registro["etapas"]], ["completo", "error"])
            self.assertIn("ValueError: faltan retornos", registro["error"])
            self.assertTrue(all(e["segundos"] >= 0 for e in registro["etapas"]))
            self.assertGreaterEqual(registro["segundos_total"], sum(e["segundos"] for e in registro["etapas"]))


if __name__ == "__main__":
    unittest.main()
