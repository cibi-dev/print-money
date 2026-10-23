"""
Tests de la escritura atómica de config.json (utils/atomic_io.py).

Ejecutar con:
    python tests_atomic_io.py
"""
import json
import os
import shutil
import sys
import tempfile
import unittest
from unittest import mock

SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)

from utils.atomic_io import escribir_json_atomico


class BaseAtomicIO(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp(prefix="pm_atomic_")
        self.ruta = os.path.join(self.tmp, "config.json")

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _tmp_residuales(self):
        return [n for n in os.listdir(self.tmp) if n.endswith(".tmp")]

    def _bytes_original(self):
        with open(self.ruta, "rb") as f:
            return f.read()

    def _leer_json(self):
        with open(self.ruta, "r", encoding="utf-8") as f:
            return json.load(f)


class TestEscrituraCorrecta(BaseAtomicIO):
    def test_escribe_y_relee_sin_residuos(self):
        datos = {"idioma": "es", "dias_antelacion_alertas": 2,
                 "notificaciones_activadas": True}
        escribir_json_atomico(self.ruta, datos)
        self.assertEqual(self._leer_json(), datos)
        self.assertEqual(self._tmp_residuales(), [])

    def test_utf8_sin_escapes_unicode(self):
        datos = {"nombre_negocio": "Impresión 3D Ñandú",
                 "lema": "Calidad y rápido 🚀✨"}
        escribir_json_atomico(self.ruta, datos)
        self.assertEqual(self._leer_json(), datos)
        with open(self.ruta, "rb") as f:
            crudo = f.read()
        self.assertNotIn(b"\\u", crudo)
        self.assertIn("Impresión".encode("utf-8"), crudo)
        self.assertEqual(self._tmp_residuales(), [])


class TestFallos(BaseAtomicIO):
    def test_serializacion_falla_no_toca_el_original(self):
        original = {"idioma": "es", "version": 1}
        escribir_json_atomico(self.ruta, original)
        antes = self._bytes_original()

        with self.assertRaises(TypeError):
            escribir_json_atomico(self.ruta, {"x": object()})

        self.assertEqual(self._bytes_original(), antes)
        self.assertEqual(self._tmp_residuales(), [])

    def test_fallo_de_escritura_propaga_y_conserva_original(self):
        original = {"idioma": "es", "version": 1}
        escribir_json_atomico(self.ruta, original)
        antes = self._bytes_original()

        with mock.patch("builtins.open", side_effect=OSError("disco lleno")):
            with self.assertRaises(OSError):
                escribir_json_atomico(self.ruta, {"idioma": "en"})

        self.assertEqual(self._bytes_original(), antes)
        self.assertEqual(self._tmp_residuales(), [])


class TestReemplazo(BaseAtomicIO):
    def test_dos_escrituras_dejan_solo_la_segunda(self):
        escribir_json_atomico(self.ruta, {"contador": 1, "idioma": "es"})
        escribir_json_atomico(self.ruta, {"contador": 2, "idioma": "en"})

        self.assertEqual(self._leer_json(), {"contador": 2, "idioma": "en"})
        self.assertEqual(sorted(os.listdir(self.tmp)), ["config.json"])
        self.assertEqual(self._tmp_residuales(), [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
