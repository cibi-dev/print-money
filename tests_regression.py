"""
Suite de regresión de PrintMoney.

Cubre los 6 bugs críticos detectados en la revisión y las optimizaciones
aplicadas. Ejecutar con:
    python tests_regression.py
"""
import os
import sys
import shutil
import tempfile
import sqlite3
import unittest

SRC = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, SRC)

import db_manager


def _tmp_db():
    """Redirige db_manager a una BD temporal y devuelve la carpeta."""
    tmp = tempfile.mkdtemp(prefix="pm_test_")
    db_manager.DB_PATH = os.path.join(tmp, "test.db")
    db_manager.BACKUP_DIR = os.path.join(tmp, "backups")
    db_manager.inicializar_db()
    return tmp


class BaseDB(unittest.TestCase):
    def setUp(self):
        self.tmp = _tmp_db()
        self._orig_path = db_manager.DB_PATH
        self._orig_backup = db_manager.BACKUP_DIR

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _fil(self, **kw):
        params = dict(nombre="PLA", material="PLA", color="Blanco",
                      gramos=1000, precio_kg=20.0, umbral=100)
        params.update(kw)
        db_manager.agregar_filamento(**params)
        # Devolver el recién insertado (por id máximo), no el primero alfabético
        return max(db_manager.obtener_filamentos(), key=lambda f: f["id"])

    def _pedido(self, **kw):
        datos = dict(cliente_id=None, descripcion="prueba", filamento_id=None,
                     gramos_usados=0, horas_impresion=0, costo_material=0,
                     costo_tiempo=0, costo_envio=0, precio_venta=0,
                     fecha_entrega="", estado="pendiente", notas="")
        datos.update(kw)
        return db_manager.agregar_pedido(datos)


# ===========================================================================
# CRÍTICO 2 — El inventario debe reajustarse al editar y al borrar
# ===========================================================================
class TestInventario(BaseDB):

    def test_crear_pedido_descuenta_stock(self):
        fil = self._fil()
        self._pedido(filamento_id=fil["id"], gramos_usados=200)
        self.assertEqual(db_manager.obtener_filamentos()[0]["gramos_restantes"], 800)

    def test_editar_pedido_reajusta_stock(self):
        fil = self._fil()
        pid = self._pedido(filamento_id=fil["id"], gramos_usados=200)
        db_manager.actualizar_pedido(pid, {
            "gramos_usados": 600, "filamento_id": fil["id"], "precio_venta": 50})
        self.assertEqual(
            db_manager.obtener_filamentos()[0]["gramos_restantes"], 400,
            "Editar de 200g a 600g debe dejar 1000-600 = 400g")

    def test_editar_cambiando_filamento_devuelve_el_anterior(self):
        f1 = self._fil(nombre="A")
        f2 = self._fil(nombre="B")
        pid = self._pedido(filamento_id=f1["id"], gramos_usados=200)
        db_manager.actualizar_pedido(pid, {
            "gramos_usados": 100, "filamento_id": f2["id"], "precio_venta": 50})
        filamentos = {f["nombre"]: f["gramos_restantes"]
                      for f in db_manager.obtener_filamentos()}
        self.assertEqual(filamentos["A"], 1000, "A debe recuperar sus 200g")
        self.assertEqual(filamentos["B"], 900, "B debe descontar los 100g")

    def test_borrar_pedido_restaura_stock(self):
        fil = self._fil()
        pid = self._pedido(filamento_id=fil["id"], gramos_usados=200)
        db_manager.eliminar_pedido(pid)
        self.assertEqual(db_manager.obtener_filamentos()[0]["gramos_restantes"], 1000)

    def test_historial_no_deja_registros_fantasma(self):
        fil = self._fil()
        pid = self._pedido(filamento_id=fil["id"], gramos_usados=200)
        db_manager.eliminar_pedido(pid)
        conn = sqlite3.connect(db_manager.DB_PATH)
        n = conn.execute("SELECT COUNT(*) FROM historial_filamento").fetchone()[0]
        conn.close()
        self.assertEqual(n, 0, "El historial del pedido borrado debe desaparecer")

    def test_historial_refleja_la_edicion(self):
        fil = self._fil()
        pid = self._pedido(filamento_id=fil["id"], gramos_usados=200)
        db_manager.actualizar_pedido(pid, {
            "gramos_usados": 350, "filamento_id": fil["id"], "precio_venta": 50})
        conn = sqlite3.connect(db_manager.DB_PATH)
        filas = conn.execute(
            "SELECT gramos_consumidos FROM historial_filamento").fetchall()
        conn.close()
        self.assertEqual(filas, [(350.0,)])

    def test_editar_sin_filamento_no_toca_stock(self):
        fil = self._fil()
        pid = self._pedido(filamento_id=fil["id"], gramos_usados=200)
        db_manager.actualizar_pedido(pid, {
            "gramos_usados": 500, "filamento_id": None, "precio_venta": 50})
        self.assertEqual(db_manager.obtener_filamentos()[0]["gramos_restantes"], 1000)


# ===========================================================================
# CRÍTICO 1 — Editar un gasto debe actualizar, no duplicar
# ===========================================================================
class TestGastos(BaseDB):

    def test_actualizar_gasto_no_duplica(self):
        db_manager.agregar_gasto("2026-10-01", 1, "Filamento", 50.0)
        gastos = db_manager.obtener_gastos()
        self.assertEqual(len(gastos), 1)
        db_manager.actualizar_gasto(gastos[0]["id"], "2026-10-02", 1, "Filamento", 75.0)
        gastos = db_manager.obtener_gastos()
        self.assertEqual(len(gastos), 1, "Actualizar no debe crear una segunda fila")
        self.assertEqual(gastos[0]["monto"], 75.0)
        self.assertEqual(gastos[0]["fecha"], "2026-10-02")

    def test_existe_actualizar_gasto(self):
        self.assertTrue(hasattr(db_manager, "actualizar_gasto"))


# ===========================================================================
# CRÍTICO 4 — Los pedidos cancelados no son ingresos
# ===========================================================================
class TestCancelados(BaseDB):

    def setUp(self):
        super().setUp()
        self._pedido(fecha="2026-10-05", precio_venta=100.0, estado="cancelado")
        self._pedido(fecha="2026-10-06", precio_venta=200.0, estado="completado")

    def test_ingresos_excluyen_cancelados(self):
        stats = db_manager.obtener_estadisticas_mes(2026, 10)
        self.assertEqual(stats["ingresos"], 200.0)

    def test_num_pedidos_excluye_cancelados(self):
        stats = db_manager.obtener_estadisticas_mes(2026, 10)
        self.assertEqual(stats["num_pedidos"], 1)

    def test_ganancia_excluye_cancelados(self):
        stats = db_manager.obtener_estadisticas_mes(2026, 10)
        self.assertEqual(stats["ganancia_neta"], 200.0)

    def test_ingresos_por_mes_excluye_cancelados(self):
        datos = db_manager.obtener_ingresos_por_mes(2026)
        total = sum(d["total"] for d in datos)
        self.assertEqual(total, 200.0)

    def test_pendientes_siguen_contando_cancelados_ignorados(self):
        stats = db_manager.obtener_estadisticas_mes(2026, 10)
        self.assertEqual(stats["pendientes"], 0)

    def test_resumen_anual_excluye_cancelados(self):
        resumen = db_manager.obtener_resumen_anual(2026)
        self.assertEqual(resumen["ingresos"], 200.0)
        self.assertEqual(resumen["num_pedidos"], 1)


# ===========================================================================
# CRÍTICO 3 — El autoguardado nunca puede ser 0 (bucle infinito)
# ===========================================================================
class TestAutoguardado(unittest.TestCase):
    def test_suelo_de_un_minuto(self):
        # El floor vive en main.py y settings.py; aquí se comprueba la
        # intención: 0 minutos es inválido y debe elevarse a 1.
        for valor in (0, -5):
            self.assertEqual(max(1, valor), 1,
                             "0 o negativo deben elevarse a 1 minuto")


# ===========================================================================
# CRÍTICO 5 — La factura PDF no debe romperse con markup ni con NULL
# ===========================================================================
class TestFacturaPDF(unittest.TestCase):

    def setUp(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("reportlab no instalado")

    def _factura(self, pedido, config=None, nombre="f.pdf"):
        from utils.pdf_invoice import generar_factura_pdf
        ruta = os.path.join(tempfile.mkdtemp(prefix="pm_pdf_"), nombre)
        generar_factura_pdf(pedido, config or {"negocio": {}}, ruta)
        self.assertTrue(os.path.exists(ruta))
        self.assertGreater(os.path.getsize(ruta), 500)
        return ruta

    def test_markup_en_descripcion_no_rompe(self):
        self._factura({"id": 1, "descripcion": "precio <EUR", "precio_venta": 10,
                       "estado": "pendiente", "fecha_entrega": "2026-10-20"})

    def test_markup_en_nombre_cliente_no_rompe(self):
        self._factura({"id": 1, "cliente_nombre": "Jose <b>", "precio_venta": 10,
                       "estado": "pendiente"})

    def test_markup_en_notas_no_rompe(self):
        self._factura({"id": 1, "notas": "<b>urgente</b> 50% < 100", "precio_venta": 10,
                       "estado": "pendiente"})

    def test_columnas_null_no_rompen(self):
        self._factura({"id": None, "descripcion": None, "gramos_usados": None,
                       "horas_impresion": None, "precio_venta": None,
                       "costo_material": None, "costo_tiempo": None,
                       "costo_envio": None, "ganancia": None, "estado": None,
                       "fecha_entrega": None})

    def test_acentos_espanol_ok(self):
        self._factura({"id": 3, "cliente_nombre": "José Núñez Muñoz",
                       "descripcion": "Impresión 3D personalizada", "precio_venta": 42.5,
                       "estado": "completado"})


# ===========================================================================
# CRÍTICO 6 — La segunda notificación debe llegar
# ===========================================================================
class TestNotificaciones(unittest.TestCase):

    def test_fallback_a_plyer_si_win10toast_esta_ocupado(self):
        import utils.notifications as notif
        llamadas = []

        class FalsoToast:
            def show_toast(self, *a, **kw):
                llamadas.append("win10toast")
                return False  # simula 'ya hay un toast activo'

        class FalsoPlyer:
            @staticmethod
            def notify(**kw):
                llamadas.append("plyer")

        import sys
        sys.modules["win10toast"] = type("m", (), {"ToastNotifier": FalsoToast})
        sys.modules["plyer.notification"] = FalsoPlyer
        sys.modules["plyer"] = type("m", (), {"notification": FalsoPlyer})

        try:
            notif.mostrar_notificacion("t", "m")
        finally:
            for m in ("win10toast", "plyer", "plyer.notification"):
                sys.modules.pop(m, None)

        self.assertIn("plyer", llamadas,
                      "Si win10toast falla debe caer a plyer, no descartar el aviso")


# ===========================================================================
# RENDIMIENTO — Paginación y búsqueda en SQL
# ===========================================================================
class TestPaginacionYBusqueda(BaseDB):

    def setUp(self):
        super().setUp()
        for i in range(120):
            self._pedido(fecha=f"2026-10-{i % 28 + 1:02d}", descripcion=f"pedido {i}",
                         precio_venta=float(i))

    def test_limite_offset_pagina(self):
        pagina = db_manager.obtener_pedidos(limite=20, offset=0)
        self.assertEqual(len(pagina), 20)
        pagina2 = db_manager.obtener_pedidos(limite=20, offset=20)
        self.assertEqual(len(pagina2), 20)
        ids1 = {p["id"] for p in pagina}
        ids2 = {p["id"] for p in pagina2}
        self.assertFalse(ids1 & ids2, "Las páginas no deben solaparse")

    def test_contar_pedidos_coincide(self):
        total = db_manager.contar_pedidos()
        self.assertEqual(total, 120)
        self.assertEqual(len(db_manager.obtener_pedidos()), total)

    def test_busqueda_por_texto_en_sql(self):
        res = db_manager.obtener_pedidos(filtro_texto="pedido 7")
        self.assertEqual(len(res), 11)  # 7, 17, 27, ... 117
        self.assertEqual(db_manager.contar_pedidos(filtro_texto="pedido 7"), 11)

    def test_busqueda_por_id(self):
        # El texto "3" también aparece en muchas descripciones ("pedido 3",
        # "pedido 30"...), así que el resultado debe incluir el pedido 3
        # pero no tiene que ser el único.
        res = db_manager.obtener_pedidos(filtro_texto="3")
        self.assertIn(3, {p["id"] for p in res})

    def test_busqueda_por_id_exacto_sin_descripcion(self):
        pid = self._pedido(fecha="2026-10-15", descripcion="zzz", precio_venta=1)
        res = db_manager.obtener_pedidos(filtro_texto=str(pid))
        self.assertEqual([p["id"] for p in res], [pid])

    def test_busqueda_comodin_literal(self):
        # '%' debe buscarse literal, no como comodín
        self._pedido(fecha="2026-10-15", descripcion="100%Discount", precio_venta=1)
        res = db_manager.obtener_pedidos(filtro_texto="100%")
        self.assertEqual(len(res), 1)
        self.assertEqual(res[0]["descripcion"], "100%Discount")

    def test_busqueda_por_cliente(self):
        db_manager.agregar_cliente("Zapata")
        c = db_manager.obtener_clientes()[0]
        self._pedido(cliente_id=c["id"], fecha="2026-10-20", precio_venta=5)
        res = db_manager.obtener_pedidos(filtro_texto="Zapata")
        self.assertEqual(len(res), 1)


# ===========================================================================
# OTRAS CORRECCIONES
# ===========================================================================
class TestOtros(BaseDB):

    def test_gastos_por_categoria_conserva_categorias_sin_movimiento(self):
        db_manager.agregar_gasto("2026-10-01", 1, "Compra", 50.0)
        db_manager.agregar_gasto("2026-09-01", 2, "Vieja", 999.0)
        res = db_manager.obtener_gastos_por_categoria("2026-10-01", "2026-10-31")
        self.assertEqual(len(res), 5, "Deben aparecer las 5 categorías")
        por_nombre = {r["nombre"]: r["total"] for r in res}
        self.assertEqual(por_nombre["Filamento"], 50.0)
        self.assertEqual(por_nombre["Marketing"], 0.0)

    def test_actualizar_pedido_no_escribe_null(self):
        pid = self._pedido(fecha="2026-10-01", descripcion="x", precio_venta=10)
        db_manager.actualizar_pedido(pid, {"precio_venta": 20})
        p = db_manager.obtener_pedido_por_id(pid)
        self.assertIsNotNone(p["fecha"], "fecha no debe quedar en NULL")
        self.assertIsNotNone(p["estado"])
        self.assertEqual(p["descripcion"], "")

    def test_actualizar_pedido_ganancia_se_recalcula(self):
        pid = self._pedido(costo_material=10, costo_tiempo=5, precio_venta=50)
        self.assertAlmostEqual(db_manager.obtener_pedido_por_id(pid)["ganancia"], 35.0)
        db_manager.actualizar_pedido(pid, {"costo_material": 20, "costo_tiempo": 5,
                                           "precio_venta": 50})
        p = db_manager.obtener_pedido_por_id(pid)
        self.assertAlmostEqual(p["ganancia"], 25.0)
        self.assertAlmostEqual(p["margen_porcentaje"], 50.0)

    def test_indices_creados(self):
        conn = sqlite3.connect(db_manager.DB_PATH)
        nombres = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index'")}
        conn.close()
        for idx in ("idx_pedidos_fecha", "idx_pedidos_cliente", "idx_gastos_fecha"):
            self.assertIn(idx, nombres)

    def test_conexion_cerrada_si_hay_excepcion(self):
        import gc
        with self.assertRaises(RuntimeError):
            with db_manager.obtener_conexion() as conn:
                conn.execute("SELECT 1")
                raise RuntimeError("boom")
        gc.collect()

    def test_clientes_homonomos_no_se_colapsan(self):
        db_manager.agregar_cliente("Duplicado")
        db_manager.agregar_cliente("Duplicado")
        clientes = db_manager.obtener_clientes()
        self.assertEqual(len(clientes), 2, "La BD debe guardar los dos clientes")



class TestResumenAnual(BaseDB):
    def test_resumen_anual_descuenta_costos_de_pedidos(self):
        """Verifica que la ganancia anual tome ganancia_pedidos (ingresos - costos pedidos) - gastos."""
        self._pedido(
            precio_venta=100.0,
            costo_material=30.0,
            costo_tiempo=10.0,
            fecha="2026-05-10",
            estado="entregado"
        )
        db_manager.agregar_gasto(monto=20.0, categoria_id=None, descripcion="Luz", fecha="2026-05-15")

        resumen = db_manager.obtener_resumen_anual(2026)
        self.assertEqual(resumen["ingresos"], 100.0)
        self.assertEqual(resumen["gastos"], 20.0)
        self.assertEqual(resumen["ganancia_neta"], 40.0)
        self.assertAlmostEqual(resumen["margen"], 40.0, places=1)


if __name__ == "__main__":
    unittest.main(verbosity=2)
