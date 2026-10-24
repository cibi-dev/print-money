"""
Smoke test de integración de la UI: construye las vistas reales de Tkinter y
ejercita los flujos que se arreglaron (paginación, edición de gastos,
validación de pedidos).

Ejecutar con:
    python tests_ui_smoke.py
"""
import os
import sys
import shutil
import tempfile
import unittest
from unittest.mock import MagicMock, patch

SRC = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, SRC)

os.environ.setdefault("PRINTMONEY_DATA_DIR",
                      tempfile.mkdtemp(prefix="pm_appdata_ui_"))
os.environ.setdefault("PRINTMONEY_DISABLE_MIGRATION", "1")

import db_manager
import customtkinter as ctk

ctk.set_appearance_mode("dark")


def _preparar_db():
    tmp = tempfile.mkdtemp(prefix="pm_ui_")
    db_manager.DB_PATH = os.path.join(tmp, "ui.db")
    db_manager.BACKUP_DIR = os.path.join(tmp, "backups")
    db_manager.inicializar_db()
    return tmp


class BaseUI(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = ctk.CTk()
        cls.root.withdraw()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.tmp = _preparar_db()
        self.errores = []

        def _showerror(titulo, mensaje=None, **kw):
            self.errores.append(mensaje)

        def _showwarning(titulo, mensaje=None, **kw):
            pass

        def _showinfo(titulo, mensaje=None, **kw):
            pass

        self._patchers = [
            patch("tkinter.messagebox.showerror", side_effect=_showerror),
            patch("tkinter.messagebox.showwarning", side_effect=_showwarning),
            patch("tkinter.messagebox.showinfo", side_effect=_showinfo),
            patch("tkinter.messagebox.askyesno", return_value=False),
        ]
        for p in self._patchers:
            p.start()

    def tearDown(self):
        for p in self._patchers:
            p.stop()
        shutil.rmtree(self.tmp, ignore_errors=True)


class TestOrdersUI(BaseUI):

    def _vista(self):
        from ui.orders import OrdersView
        v = OrdersView(self.root, MagicMock())
        v.pack()
        return v

    def _sembrar(self, n):
        for i in range(n):
            db_manager.agregar_pedido({
                "fecha": "2026-10-15", "descripcion": f"pedido {i}",
                "precio_venta": float(i), "estado": "pendiente"})

    def test_paginacion_no_renderiza_todo(self):
        self._sembrar(120)
        v = self._vista()
        v.on_show()
        filas = v.frame_tabla_scroll.winfo_children()
        self.assertEqual(len(filas), 50, "Solo se deben renderizar 50 filas por página")
        self.assertEqual(v._total_paginas, 3)
        self.assertEqual(v._total_filtrados, 120)

    def test_navegar_entre_paginas(self):
        self._sembrar(120)
        v = self._vista()
        v.on_show()
        ids_p1 = {v._todos_pedidos[i]["id"] for i in range(len(v._todos_pedidos))}
        v._cambiar_pagina(1)
        self.assertEqual(v._pagina, 1)
        ids_p2 = {v._todos_pedidos[i]["id"] for i in range(len(v._todos_pedidos))}
        self.assertFalse(ids_p1 & ids_p2, "Las páginas no deben solaparse")
        v._cambiar_pagina(-1)
        self.assertEqual(v._pagina, 0)

    def test_boton_anterior_deshabilitado_en_primera_pagina(self):
        self._sembrar(120)
        v = self._vista()
        v.on_show()
        self.assertEqual(v.btn_anterior.cget("state"), "disabled")
        self.assertEqual(v.btn_siguiente.cget("state"), "normal")

    def test_filtro_por_texto_en_sql(self):
        self._sembrar(120)
        v = self._vista()
        v.on_show()
        v.entry_buscar.insert(0, "pedido 1")
        v._filtrar()
        self.assertLess(v._total_filtrados, 120)
        self.assertGreater(v._total_filtrados, 0)
        for p in v._todos_pedidos:
            self.assertIn("pedido 1", p["descripcion"])

    def test_guardar_con_precio_no_numerico_muestra_error(self):
        v = self._vista()
        v.on_show()
        v.ent_venta.insert(0, "abc")
        v._guardar_pedido()
        self.assertTrue(self.errores, "Debe mostrarse un error, no fallar en silencio")
        self.assertEqual(db_manager.contar_pedidos(), 0, "No debe guardarse nada")

    def test_guardar_con_fecha_invalida_muestra_error(self):
        v = self._vista()
        v.on_show()
        v.ent_fecha.delete(0, "end")
        v.ent_fecha.insert(0, "32/12/2026")
        v._guardar_pedido()
        self.assertTrue(self.errores)
        self.assertEqual(db_manager.contar_pedidos(), 0)

    def test_guardar_pedido_valido(self):
        v = self._vista()
        v.on_show()
        v.ent_desc.insert(0, "prueba")
        v.ent_venta.insert(0, "50")
        v._guardar_pedido()
        self.assertEqual(self.errores, [])
        self.assertEqual(db_manager.contar_pedidos(), 1)

    def test_clientes_homonomos_aparecen_ambos(self):
        db_manager.agregar_cliente("Gemelo")
        db_manager.agregar_cliente("Gemelo")
        v = self._vista()
        v.on_show()
        etiquetas = [e for e in v._clientes_data if e.startswith("Gemelo")]
        self.assertEqual(len(etiquetas), 2, "Los dos homónimos deben ser seleccionables")
        self.assertEqual(len({v._clientes_data[e]["id"] for e in etiquetas}), 2)

    def test_tabla_se_refresca_al_editar_descripcion(self):
        pid = db_manager.agregar_pedido({
            "fecha": "2026-10-15", "descripcion": "descripcion original",
            "precio_venta": 50.0, "estado": "pendiente"})
        v = self._vista()
        v.on_show()

        def textos():
            return " ".join(
                w.cget("text")
                for fila in v.frame_tabla_scroll.winfo_children()
                for w in fila.winfo_children()
            )

        self.assertIn("descripcion original", textos())
        db_manager.actualizar_pedido(pid, {
            "fecha": "2026-10-15", "descripcion": "descripcion nueva",
            "precio_venta": 50.0, "estado": "pendiente"})
        v._aplicar_filtros()
        self.assertIn("descripcion nueva", textos())
        self.assertNotIn("descripcion original", textos())

    def test_guardar_pedido_prellenado_desde_cotizacion_enlaza(self):
        r = db_manager.crear_cotizacion(
            fecha="2026-10-23", cliente_id=None, cliente_nombre="Ana",
            validez_dias=7, notas="", condiciones="",
            items=[dict(descripcion="Soporte", cantidad=2, material="PLA",
                        gramos=100, horas=2, costo_material=2.0,
                        costo_tiempo=10.0, filamento_id=None,
                        precio_unitario=25.0)])

        v = self._vista()
        v.on_show()
        v.prellenar({
            "descripcion": "Soporte", "gramos": 200.0, "horas": 4.0,
            "costo_material": 4.0, "costo_tiempo": 20.0,
            "precio_sugerido": 50.0, "cotizacion_id": r["id"],
        })
        self.assertEqual(v._cotizacion_id, r["id"])
        v._guardar_pedido()

        self.assertEqual(self.errores, [])
        cot = db_manager.obtener_cotizacion(r["id"])
        self.assertEqual(cot["estado"], "aceptada")
        self.assertIsNotNone(cot["pedido_id"])
        self.assertEqual(db_manager.contar_pedidos(), 1)


class TestExpensesUI(BaseUI):

    def test_editar_gasto_actualiza_en_vez_de_duplicar(self):
        db_manager.agregar_gasto("2026-10-01", 1, "Compra", 50.0)
        from ui.expenses import ExpensesView
        v = ExpensesView(self.root, MagicMock())
        v.pack()
        v.on_show()

        gastos = db_manager.obtener_gastos()
        self.assertEqual(len(gastos), 1)
        v._seleccionar_gasto(gastos[0]["id"])
        v.ent_monto.delete(0, "end")
        v.ent_monto.insert(0, "125")
        v._guardar_gasto()

        gastos = db_manager.obtener_gastos()
        self.assertEqual(len(gastos), 1, "Guardar no debe duplicar el gasto")
        self.assertEqual(gastos[0]["monto"], 125.0)

    def test_frecuencia_se_guarda_en_canonico(self):
        from ui.expenses import ExpensesView
        v = ExpensesView(self.root, MagicMock())
        v.pack()
        v.on_show()
        v.ent_monto.insert(0, "10")
        v.var_recurrente.set(True)
        v.combo_freq.set(v.combo_freq.cget("values")[1])  # semanal
        v._guardar_gasto()
        gastos = db_manager.obtener_gastos()
        self.assertEqual(len(gastos), 1)
        self.assertEqual(gastos[0]["frecuencia"], "semanal",
                         "La frecuencia debe guardarse como código, no como texto traducido")


class TestQuotesUI(BaseUI):

    def test_vista_carga_y_muestra_detalle(self):
        r = db_manager.crear_cotizacion(
            fecha="2026-10-23", cliente_id=None, cliente_nombre="Ana",
            validez_dias=7, notas="", condiciones="",
            items=[dict(descripcion="Soporte", cantidad=1, material="PLA",
                        gramos=100, horas=2, costo_material=2.0,
                        costo_tiempo=10.0, filamento_id=None,
                        precio_unitario=25.0)])

        from ui.quotes import QuotesView
        v = QuotesView(self.root, MagicMock())
        v.pack()
        v.on_show()
        self.assertEqual(len(v._cotizaciones), 1)

        v._seleccionar(r["id"])
        self.assertIsNotNone(v._seleccion)
        self.assertEqual(v._seleccion["numero"], r["numero"])
        v.destroy()

    def test_detalle_pinta_el_color_del_estado(self):
        from ui import theme as th
        from utils.i18n import T

        r = db_manager.crear_cotizacion(
            fecha="2026-10-23", cliente_id=None, cliente_nombre="Ana",
            validez_dias=7, notas="", condiciones="",
            items=[dict(descripcion="Soporte", cantidad=1, material="PLA",
                        gramos=100, horas=2, costo_material=2.0,
                        costo_tiempo=10.0, filamento_id=None,
                        precio_unitario=25.0)])

        from ui.quotes import QuotesView
        v = QuotesView(self.root, MagicMock())
        v.pack()
        v.on_show()
        v._seleccionar(r["id"])
        cab = v.frame_detalle.winfo_children()[0]
        pill = next(w for w in cab.winfo_children()
                    if isinstance(w, ctk.CTkLabel)
                    and w.cget("text") == T("quote_status_borrador"))
        self.assertEqual(pill.cget("fg_color"), th.SUB)
        v.destroy()

    def test_convertir_no_marca_aceptada_y_escala_cantidad(self):
        r = db_manager.crear_cotizacion(
            fecha="2026-10-23", cliente_id=None, cliente_nombre="Ana",
            validez_dias=7, notas="", condiciones="",
            items=[dict(descripcion="Soporte", cantidad=3, material="PLA",
                        gramos=100, horas=2, costo_material=2.0,
                        costo_tiempo=10.0, filamento_id=None,
                        precio_unitario=25.0)])

        capturado = {}
        vista_pedidos = MagicMock()
        vista_pedidos.prellenar.side_effect = lambda datos: capturado.update(datos)
        app = MagicMock()
        app._cache_vistas = {"pedidos": vista_pedidos}

        from ui.quotes import QuotesView
        v = QuotesView(self.root, app)
        v.pack()
        v.on_show()
        v._convertir(db_manager.obtener_cotizacion(r["id"]))

        self.assertEqual(capturado["gramos"], 300.0)
        self.assertEqual(capturado["horas"], 6.0)
        self.assertEqual(capturado["costo_material"], 6.0)
        self.assertEqual(capturado["costo_tiempo"], 30.0)
        self.assertEqual(capturado["precio_sugerido"], 75.0)
        self.assertEqual(capturado["cotizacion_id"], r["id"])

        actual = db_manager.obtener_cotizacion(r["id"])
        self.assertEqual(actual["estado"], "borrador",
                         "No debe aceptarse hasta que se guarde el pedido")
        self.assertIsNone(actual["pedido_id"])
        v.destroy()


class TestRestoVistas(BaseUI):
    """Todas las vistas deben seguir construyéndose sin errores."""

    def test_todas_las_vistas_se_construyen(self):
        from ui.dashboard import DashboardView
        from ui.orders import OrdersView
        from ui.expenses import ExpensesView
        from ui.inventory import InventoryView
        from ui.catalog import CatalogView
        from ui.clients import ClientsView
        from ui.reports import ReportsView
        from ui.calendar import CalendarView
        from ui.settings import SettingsView
        from ui.quotes import QuotesView
        from ui.calculator import CalculatorWindow

        for cls in (DashboardView, OrdersView, ExpensesView, InventoryView,
                    CatalogView, ClientsView, ReportsView, CalendarView,
                    QuotesView, SettingsView):
            v = cls(self.root, MagicMock())
            self.assertIsNotNone(v)
            v.destroy()

        win = CalculatorWindow(self.root)
        self.assertIsNotNone(win)
        win.destroy()

    def test_dashboard_carga_datos(self):
        from ui.dashboard import DashboardView
        db_manager.agregar_pedido({"fecha": "2026-10-05", "precio_venta": 100.0,
                                   "costo_material": 10, "costo_tiempo": 5,
                                   "costo_envio": 0, "estado": "completado"})
        v = DashboardView(self.root, MagicMock())
        v.pack()
        v.on_show()
        self.assertIn("100", v.card_ingresos.lbl_valor.cget("text"))
        v.destroy()

    def test_navegar_desmapea_vista_anterior(self):
        from main import PrintMoneyApp
        app = PrintMoneyApp()
        app.withdraw()
        try:
            app.navegar("dashboard")
            dash = app._cache_vistas["dashboard"]
            self.assertNotEqual(dash.grid_info(), {})

            app.navegar("pedidos")
            pedidos = app._cache_vistas["pedidos"]
            self.assertNotEqual(pedidos.grid_info(), {})
            # La vista previa fue retirada con grid_remove() y no tiene info de grid activa
            self.assertEqual(dash.grid_info(), {}, "La vista anterior debe desmapearse para evitar widget bleed")
        finally:
            try:
                app.destroy()
            except Exception:
                pass

    def test_settings_guarda_sin_perder_negocio(self):
        import ui.settings as settings
        # Apuntar el BASE_DIR de settings a un temporal con config.json
        import json
        cfg_path = os.path.join(self.tmp, "config.json")
        with open(cfg_path, "w", encoding="utf-8") as f:
            json.dump({"idioma": "es", "tarifa_por_hora": 5.0,
                       "negocio": {"nombre": "X", "clave_extra": "debe-sobrevivir"}}, f)
        original = settings.BASE_DIR
        settings.BASE_DIR = self.tmp
        try:
            v = settings.SettingsView(self.root, MagicMock())
            v.pack()
            v.on_show()
            v._guardar()
            with open(cfg_path, "r", encoding="utf-8") as f:
                cfg = json.load(f)
            self.assertEqual(cfg["negocio"]["clave_extra"], "debe-sobrevivir",
                             "Las claves ajenas del bloque negocio no deben perderse")
            v.destroy()
        finally:
            settings.BASE_DIR = original


if __name__ == "__main__":
    unittest.main(verbosity=2)

