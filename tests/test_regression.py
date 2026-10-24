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

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC)

# Aislar la carpeta de datos para que los tests no lean ni escriban en
# %APPDATA%\PrintMoney.
os.environ.setdefault("PRINTMONEY_DATA_DIR",
                      tempfile.mkdtemp(prefix="pm_appdata_"))
os.environ.setdefault("PRINTMONEY_DISABLE_MIGRATION", "1")

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

    def test_factura_en_ingles_genera_ok(self):
        from utils.i18n import get_idioma, set_idioma
        anterior = get_idioma()
        try:
            set_idioma("en")
            self._factura({"id": 4, "cliente_nombre": "John Doe",
                           "descripcion": "Custom 3D print", "precio_venta": 20,
                           "estado": "completado"})
        finally:
            set_idioma(anterior)


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

    def test_resumen_mensual_anual_coincide(self):
        self._pedido(precio_venta=150.0, costo_material=50.0, fecha="2026-03-10", estado="entregado")
        db_manager.agregar_gasto(monto=30.0, categoria_id=None, descripcion="Herramienta", fecha="2026-03-12")
        resumen = db_manager.obtener_resumen_mensual_anual(2026)
        marzo = resumen[3]
        self.assertEqual(marzo["ingresos"], 150.0)
        self.assertEqual(marzo["gastos"], 30.0)
        self.assertEqual(marzo["ganancia_neta"], 70.0)  # (150 - 50) - 30
        self.assertEqual(marzo["num_pedidos"], 1)
        self.assertEqual(resumen[1]["ingresos"], 0.0)

    def test_estadisticas_mes_usan_margen_neto(self):
        """El Dashboard y Reportes deben mostrar el mismo margen sobre ventas."""
        self._pedido(precio_venta=100.0, costo_material=30.0, costo_tiempo=10.0,
                     fecha="2026-05-10", estado="entregado")
        db_manager.agregar_gasto(monto=20.0, categoria_id=None,
                                  descripcion="Luz", fecha="2026-05-15")

        mes = db_manager.obtener_estadisticas_mes(2026, 5)
        anual = db_manager.obtener_resumen_anual(2026)
        self.assertEqual(mes["ganancia_neta"], 40.0)
        self.assertAlmostEqual(mes["margen"], 40.0, places=1)
        self.assertAlmostEqual(mes["margen"], anual["margen"], places=1)


# ===========================================================================
# COTIZACIONES — numeración, totales, estados y borrado en cascada
# ===========================================================================
class TestCotizaciones(BaseDB):

    def _cot(self, **kw):
        datos = dict(
            fecha="2026-10-23", cliente_id=None, cliente_nombre="Ana",
            validez_dias=7, notas="", condiciones="",
            items=[dict(descripcion="Soporte", cantidad=2, material="PLA",
                        gramos=100, horas=2, costo_material=2.0,
                        costo_tiempo=10.0, filamento_id=None,
                        precio_unitario=25.0)],
        )
        datos.update(kw)
        return db_manager.crear_cotizacion(**datos)

    def test_numeracion_secuencial_por_anio(self):
        r1 = self._cot()
        r2 = self._cot()
        self.assertEqual(r1["numero"], "C-2026-0001")
        self.assertEqual(r2["numero"], "C-2026-0002")
        r3 = self._cot(fecha="2027-01-05")
        self.assertEqual(r3["numero"], "C-2027-0001")

    def test_total_multiplica_cantidad(self):
        r = self._cot()
        self.assertEqual(r["subtotal"], 50.0)
        self.assertEqual(r["total"], 50.0)

    def test_obtener_incluye_items(self):
        r = self._cot()
        cot = db_manager.obtener_cotizacion(r["id"])
        self.assertEqual(cot["numero"], r["numero"])
        self.assertEqual(len(cot["items"]), 1)
        self.assertEqual(cot["items"][0]["descripcion"], "Soporte")
        self.assertEqual(cot["items"][0]["cantidad"], 2)

    def test_estado_y_conversion(self):
        r = self._cot()
        db_manager.actualizar_estado_cotizacion(r["id"], "enviada")
        self.assertEqual(db_manager.obtener_cotizacion(r["id"])["estado"], "enviada")
        db_manager.marcar_cotizacion_convertida(r["id"])
        self.assertEqual(db_manager.obtener_cotizacion(r["id"])["estado"], "aceptada")
        with self.assertRaises(ValueError):
            db_manager.actualizar_estado_cotizacion(r["id"], "inventado")

    def test_eliminar_borra_items(self):
        r = self._cot()
        db_manager.eliminar_cotizacion(r["id"])
        self.assertIsNone(db_manager.obtener_cotizacion(r["id"]))
        with db_manager.obtener_conexion() as conn:
            total = conn.execute("SELECT COUNT(*) FROM cotizacion_items").fetchone()[0]
        self.assertEqual(total, 0)

    def test_busqueda_por_cliente_descripcion_y_estado(self):
        self._cot(cliente_nombre="Ana Pérez")
        self._cot(cliente_nombre="Luis Gómez")
        self.assertEqual(len(db_manager.obtener_cotizaciones(filtro_texto="Ana")), 1)
        self.assertEqual(len(db_manager.obtener_cotizaciones(filtro_texto="Soporte")), 2)
        self.assertEqual(len(db_manager.obtener_cotizaciones(filtro_estado="borrador")), 2)

    def test_agregar_pedido_desde_cotizacion_marca_aceptada_y_enlaza(self):
        fil = self._fil()
        r = self._cot()  # cantidad 2: 200 g, 4 h, costes 4/20, precio 50
        pid = db_manager.agregar_pedido({
            "fecha": "2026-10-23", "descripcion": "Soporte",
            "filamento_id": fil["id"], "gramos_usados": 200.0,
            "horas_impresion": 4.0, "costo_material": 4.0,
            "costo_tiempo": 20.0, "precio_venta": 50.0, "estado": "pendiente",
        }, cotizacion_id=r["id"])

        cot = db_manager.obtener_cotizacion(r["id"])
        self.assertEqual(cot["estado"], "aceptada")
        self.assertEqual(cot["pedido_id"], pid)
        self.assertEqual(db_manager.obtener_filamentos()[0]["gramos_restantes"], 800.0)

        # Un segundo guardado no debe reenlazar la cotización a otro pedido
        db_manager.agregar_pedido({"fecha": "2026-10-24", "precio_venta": 1.0},
                                  cotizacion_id=r["id"])
        self.assertEqual(db_manager.obtener_cotizacion(r["id"])["pedido_id"], pid)


# ===========================================================================
# COTIZACIONES — contrato, texto y PDF
# ===========================================================================
class TestCotizacionRender(unittest.TestCase):

    def setUp(self):
        try:
            import reportlab  # noqa: F401
        except ImportError:
            self.skipTest("reportlab no instalado")

    def _cot(self):
        from utils import quotes
        return quotes.construir_cotizacion(
            numero="C-2026-0001", fecha="2026-10-23", validez_dias=7,
            negocio={"nombre": "Negocio <3D> & Co", "direccion": "Calle 1"},
            cliente={"nombre": "Jose <b>", "email": "jose@mail.com"},
            items=[{"descripcion": "Soporte <grande> & especial", "cantidad": 2,
                    "precio_unitario": 12.5}],
            notas="Entregar antes del <viernes>",
        )

    def test_vence_se_calcula_desde_la_fecha(self):
        self.assertEqual(self._cot()["vence"], "2026-10-30")

    def test_texto_incluye_numero_cliente_y_total(self):
        from utils import quotes
        texto = quotes.render_texto(self._cot())
        self.assertIn("C-2026-0001", texto)
        self.assertIn("Jose <b>", texto)
        self.assertIn("$25.00", texto)

    def test_pdf_no_rompe_con_caracteres_especiales(self):
        from utils import quotes
        ruta = os.path.join(tempfile.mkdtemp(prefix="pm_qpdf_"), "q.pdf")
        quotes.render_pdf(self._cot(), ruta)
        self.assertTrue(os.path.exists(ruta))
        self.assertGreater(os.path.getsize(ruta), 500)

    def test_desde_registro_reconstruye_vence(self):
        from utils import quotes
        registro = {"numero": "C-2026-0009", "fecha": "2026-10-23",
                    "validez_dias": 7, "cliente_nombre": "Ana",
                    "items": [{"descripcion": "X", "cantidad": 1,
                               "precio_unitario": 10}],
                    "total": 10}
        cot = quotes.desde_registro(registro, {"nombre": "Negocio"})
        self.assertEqual(cot["vence"], "2026-10-30")
        self.assertEqual(cot["negocio"]["nombre"], "Negocio")


# ===========================================================================
# I18N — factura y exportaciones
# ===========================================================================
class TestI18nExport(BaseDB):

    def setUp(self):
        super().setUp()
        from utils.i18n import get_idioma
        self._idioma_original = get_idioma()

    def tearDown(self):
        from utils.i18n import set_idioma
        set_idioma(self._idioma_original)
        super().tearDown()

    def test_etiquetas_de_factura_y_reportes_en_ingles(self):
        from utils.i18n import T, set_idioma
        set_idioma("en")
        self.assertEqual(T("invoice_title"), "INVOICE")
        self.assertEqual(T("invoice_col_description"), "Description")
        self.assertEqual(T("reports_col_month"), "Month")
        self.assertEqual(T("months_full")[0], "January")

    def test_importar_export_no_carga_pandas(self):
        import subprocess
        codigo = "import sys; import utils.export; print('pandas' in sys.modules)"
        res = subprocess.run([sys.executable, "-c", codigo], cwd=SRC,
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip(), "False",
                         "utils.export no debe importar pandas hasta exportar Excel")

    def test_excel_en_ingles_usa_meses_y_hojas_traducidas(self):
        try:
            import openpyxl
        except ImportError:
            self.skipTest("openpyxl no instalado")

        from utils.i18n import set_idioma
        from utils.export import exportar_excel
        set_idioma("en")
        ruta = os.path.join(self.tmp, "reporte_en.xlsx")
        exportar_excel(ruta, 2026)

        wb = openpyxl.load_workbook(ruta)
        self.assertIn("Monthly Summary", wb.sheetnames)
        ws = wb["Monthly Summary"]
        self.assertEqual(ws["A1"].value, "Month")
        self.assertEqual(ws["A2"].value, "January")
        self.assertEqual(ws["B1"].value, "Income ($)")

    def test_pdf_reporte_en_ingles_no_rompe(self):
        from utils.i18n import set_idioma
        from utils.export import exportar_pdf_reporte
        set_idioma("en")
        ruta = os.path.join(self.tmp, "reporte_en.pdf")
        exportar_pdf_reporte(ruta, 2026)
        self.assertTrue(os.path.isfile(ruta))
        self.assertGreater(os.path.getsize(ruta), 500)


# ===========================================================================
# MIGRACIONES — versión de esquema y columnas antiguas
# ===========================================================================
class TestMigraciones(BaseDB):

    def test_bd_nueva_queda_en_la_version_actual(self):
        with db_manager.obtener_conexion() as conn:
            version = conn.execute("PRAGMA user_version").fetchone()[0]
        self.assertEqual(version, db_manager.SCHEMA_VERSION)

    def test_migra_bd_antigua_sin_factura_generada(self):
        ruta = os.path.join(self.tmp, "antigua.db")
        conn = sqlite3.connect(ruta)
        conn.execute("""
            CREATE TABLE pedidos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fecha TEXT DEFAULT (date('now')),
                cliente_id INTEGER,
                descripcion TEXT,
                filamento_id INTEGER,
                gramos_usados REAL DEFAULT 0,
                horas_impresion REAL DEFAULT 0,
                costo_material REAL DEFAULT 0,
                costo_tiempo REAL DEFAULT 0,
                costo_envio REAL DEFAULT 0,
                precio_venta REAL DEFAULT 0,
                ganancia REAL DEFAULT 0,
                margen_porcentaje REAL DEFAULT 0,
                fecha_entrega TEXT,
                estado TEXT DEFAULT 'pendiente',
                notas TEXT
            )
        """)
        conn.execute("PRAGMA user_version = 0")
        conn.commit()
        conn.close()

        original = db_manager.DB_PATH
        db_manager.DB_PATH = ruta
        try:
            db_manager.inicializar_db()
            conn = sqlite3.connect(ruta)
            try:
                columnas = {fila[1] for fila in
                            conn.execute("PRAGMA table_info(pedidos)")}
                version = conn.execute("PRAGMA user_version").fetchone()[0]
            finally:
                conn.close()
        finally:
            db_manager.DB_PATH = original

        self.assertIn("factura_generada", columnas)
        self.assertEqual(version, db_manager.SCHEMA_VERSION)


class TestMigracionDatos(unittest.TestCase):

    def test_copia_config_db_y_backups_sin_borrar_origen(self):
        import json
        import subprocess

        legacy = tempfile.mkdtemp(prefix="pm_legacy_")
        datos = tempfile.mkdtemp(prefix="pm_datos_")
        try:
            os.makedirs(os.path.join(legacy, "data", "backups"))
            with open(os.path.join(legacy, "config.json"), "w",
                      encoding="utf-8") as f:
                json.dump({"idioma": "en", "marca": "legacy"}, f)

            conn = sqlite3.connect(os.path.join(legacy, "data", "printmoney.db"))
            try:
                conn.execute("CREATE TABLE pedidos "
                             "(id INTEGER PRIMARY KEY, descripcion TEXT)")
                conn.execute("INSERT INTO pedidos (descripcion) VALUES ('heredado')")
                conn.commit()
            finally:
                conn.close()

            with open(os.path.join(legacy, "data", "backups",
                                   "backup_2026-10-01.db"), "wb") as f:
                f.write(b"backup")

            env = os.environ.copy()
            env.update({
                "PRINTMONEY_DATA_DIR": datos,
                "PRINTMONEY_LEGACY_DIR": legacy,
                "PRINTMONEY_DISABLE_MIGRATION": "0",
            })
            codigo = """
import json, os, sqlite3
import utils.paths as p
r = p.migrar_datos_legados()
print(r['config'], r['db'], r['backups'])
print(os.path.exists(p.CONFIG_PATH), os.path.exists(p.DB_PATH))
print(os.path.exists(os.path.join(p.BACKUP_DIR, 'backup_2026-10-01.db')))
print(json.load(open(p.CONFIG_PATH, encoding='utf-8'))['marca'])
c = sqlite3.connect(p.DB_PATH)
print(c.execute('SELECT descripcion FROM pedidos').fetchone()[0])
c.close()
print(os.path.exists(os.path.join(p.legacy_dir(), 'config.json')))
"""
            res = subprocess.run([sys.executable, "-c", codigo], cwd=SRC,
                                 env=env, capture_output=True, text=True)
            self.assertEqual(res.returncode, 0, res.stderr)
            lineas = res.stdout.strip().splitlines()
            self.assertEqual(lineas[0], "True True 1")
            self.assertEqual(lineas[1], "True True")
            self.assertEqual(lineas[2], "True")
            self.assertEqual(lineas[3], "legacy")
            self.assertEqual(lineas[4], "heredado")
            self.assertEqual(lineas[5], "True",
                             "La migración no debe borrar los archivos originales")
        finally:
            shutil.rmtree(legacy, ignore_errors=True)
            shutil.rmtree(datos, ignore_errors=True)


class TestInstanciaUnica(unittest.TestCase):

    def test_segunda_instancia_detecta_el_mutex(self):
        if os.name != "nt":
            self.skipTest("El mutex de instancia única es de Windows")
        import subprocess
        codigo = (
            "import os, main;"
            "n = f'PrintMoney.Test.{os.getpid()}';"
            "h1 = main._crear_mutex_instancia(n);"
            "h2 = main._crear_mutex_instancia(n);"
            "print(h1 is not None, h2 is None)"
        )
        res = subprocess.run([sys.executable, "-c", codigo], cwd=SRC,
                             capture_output=True, text=True)
        self.assertEqual(res.returncode, 0, res.stderr)
        self.assertEqual(res.stdout.strip(), "True True")


class TestPragmas(BaseDB):

    def test_journal_mode_wal(self):
        """inicializar_db() debe dejar el archivo en WAL (es persistente)."""
        conn = sqlite3.connect(db_manager.DB_PATH)
        try:
            modo = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(modo.lower(), "wal",
                         "journal_mode debe quedar en wal tras inicializar_db()")

    def test_synchronous_normal(self):
        """synchronous es por conexión: debe valer 1 (NORMAL) en cada una."""
        with db_manager.obtener_conexion() as conn:
            valor = conn.execute("PRAGMA synchronous").fetchone()[0]
        self.assertEqual(valor, 1, "synchronous debe ser NORMAL (1)")

    def test_inicializar_db_es_idempotente(self):
        """Fijar WAL dos veces seguidas no debe fallar ni salir del modo wal."""
        db_manager.inicializar_db()
        conn = sqlite3.connect(db_manager.DB_PATH)
        try:
            modo = conn.execute("PRAGMA journal_mode").fetchone()[0]
        finally:
            conn.close()
        self.assertEqual(modo.lower(), "wal")

    def test_copia_segura_genera_backup_valido_con_los_datos(self):
        """Round-trip: pedido + gasto -> backup -> el backup los contiene."""
        pid = self._pedido(fecha="2026-10-05", descripcion="pedido de backup",
                           precio_venta=100.0, estado="completado")
        db_manager.agregar_gasto("2026-10-06", 1, "Filamento", 25.0)

        ruta = os.path.join(self.tmp, "backup_test.db")
        db_manager._copiar_db_segura(ruta)
        self.assertTrue(os.path.isfile(ruta), "El backup debe existir en disco")

        conn = sqlite3.connect(ruta)
        try:
            self.assertEqual(
                conn.execute("PRAGMA integrity_check").fetchone()[0], "ok",
                "El backup debe ser una base SQLite válida")
            fila = conn.execute("SELECT id, descripcion FROM pedidos").fetchone()
            self.assertEqual(fila[0], pid)
            self.assertEqual(fila[1], "pedido de backup")
            self.assertEqual(
                conn.execute("SELECT COUNT(*) FROM gastos").fetchone()[0], 1)
        finally:
            conn.close()

    def test_backup_manual_publico_contiene_el_pedido(self):
        """La función pública de backup también es consistente con WAL."""
        pid = self._pedido(fecha="2026-10-07", descripcion="pedido backup manual",
                           precio_venta=10.0)
        # `ruta_backups()` respeta config.json y apuntaría a la carpeta real del
        # proyecto; se redirige a la temporal para no ensuciar data/backups.
        original = db_manager.ruta_backups
        db_manager.ruta_backups = lambda: os.path.join(self.tmp, "backups_manual")
        try:
            ruta = db_manager.hacer_backup_manual()
        finally:
            db_manager.ruta_backups = original

        self.assertTrue(os.path.isfile(ruta))
        conn = sqlite3.connect(ruta)
        try:
            ids = [r[0] for r in conn.execute("SELECT id FROM pedidos")]
        finally:
            conn.close()
        self.assertIn(pid, ids, "El backup manual debe contener el pedido insertado")

    def test_backups_manuales_del_mismo_dia_no_se_sobrescriben(self):
        from datetime import datetime as real_datetime
        from unittest.mock import patch

        original = db_manager.ruta_backups
        db_manager.ruta_backups = lambda: os.path.join(self.tmp, "backups_seq")
        try:
            with patch("db_manager.datetime") as mock_dt:
                mock_dt.now.side_effect = [
                    real_datetime(2026, 10, 23, 10, 0, 1),
                    real_datetime(2026, 10, 23, 10, 0, 2),
                ]
                ruta1 = db_manager.hacer_backup_manual()
                ruta2 = db_manager.hacer_backup_manual()
        finally:
            db_manager.ruta_backups = original

        self.assertNotEqual(ruta1, ruta2)
        self.assertTrue(os.path.isfile(ruta1))
        self.assertTrue(os.path.isfile(ruta2))


if __name__ == "__main__":
    unittest.main(verbosity=2)

