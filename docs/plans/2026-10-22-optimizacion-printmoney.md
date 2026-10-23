# Optimización y Estabilización de PrintMoney Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Corregir el cálculo erróneo de ganancia anual, eliminar cuellos de botella por I/O redundante y re-renderizado en la UI, optimizar consultas de reportes agregados y blindar la aplicación contra caídas silenciosas sin alterar la arquitectura base de PrintMoney.

**Architecture:** Aplicar mejoras quirúrgicas y de alto impacto sobre el modelo actual (SQLite procedural + CustomTkinter) respetando el consenso dialéctico del Consejo:
1. Corrección estricta de la fórmula de ganancia en `db_manager.py`.
2. Control de eventos en la UI mediante debounce de 250ms (`after`/`after_cancel`) y limpieza de eventos en `tkcalendar`.
3. Agregación en SQL con `GROUP BY` mensual para reducir 36 consultas a 2 en exportaciones.
4. Exportaciones de reportes en hilos de fondo (`threading.Thread`) comunicando con el hilo de UI vía `after()`.
5. Supresión de I/O de disco por pulsación (`config.json`) mediante la lectura de `app.config_data`.
6. Blindaje de escrituras en base de datos con `try/except` y captura global de excepciones en el bucle de Tkinter (`report_callback_exception`).
7. Eliminación del temporizador simulado de "autoguardado".

**Tech Stack:** Python 3, SQLite, CustomTkinter, ReportLab, openpyxl, unittest.

## Global Constraints
- No partir `db_manager.py` ni `main.py` en múltiples archivos (se mantiene la arquitectura simple).
- No migrar tipos de datos existentes en SQLite ni introducir dependencias pesadas adicionales.
- Todos los diálogos de `messagebox` deben especificar `parent=self.winfo_toplevel()` o `parent=self` para evitar bloqueos de foco en Windows.
- No ejecutar llamadas a widgets de Tkinter fuera del hilo principal (`main thread`). Usar `self.after()` para cualquier callback proveniente de threads.
- Mantener la suite de pruebas `tests_regression.py` en verde en cada commit.

---

### Task 1: Corrección de cálculo de ganancia anual y test de regresión

**Files:**
- Modify: `db_manager.py:750-756`
- Modify: `tests_regression.py:270-300`

**Interfaces:**
- Consumes: `obtener_resumen_anual(year: int) -> dict`
- Produces: `{"ingresos": float, "gastos": float, "ganancia_neta": float, "margen": float, "num_pedidos": int}` donde `ganancia_neta = r["ganancia_pedidos"] - gastos`.

- [ ] **Step 1: Escribir el test de regresión que falla**

En `tests_regression.py`, agregar en la clase `TestCancelados` o en una clase específica `TestResumenAnual`:

```python
class TestResumenAnual(BaseDB):
    def test_resumen_anual_descuenta_costos_de_pedidos(self):
        """Verifica que la ganancia anual tome ganancia_pedidos (ingresos - costos pedidos) - gastos."""
        # Pedido: precio venta $100, costo material $30, costo tiempo $10 -> ganancia del pedido = $60
        self._pedido(
            precio_venta=100.0,
            costo_material=30.0,
            costo_tiempo=10.0,
            fecha="2026-05-10",
            estado="entregado"
        )
        # Gasto general del negocio: $20.0
        db_manager.agregar_gasto(monto=20.0, categoria_id=None, descripcion="Luz", fecha="2026-05-15")

        resumen = db_manager.obtener_resumen_anual(2026)
        # Ganancia neta correcta: 60 (ganancia pedidos) - 20 (gastos) = 40.0
        # Bug anterior: 100 (ingresos) - 20 (gastos) = 80.0
        self.assertEqual(resumen["ingresos"], 100.0)
        self.assertEqual(resumen["gastos"], 20.0)
        self.assertEqual(resumen["ganancia_neta"], 40.0)
        self.assertAlmostEqual(resumen["margen"], 40.0, places=1)
```

- [ ] **Step 2: Ejecutar el test para verificar que falla con el código actual**

Run: `python -m unittest tests_regression.py -k TestResumenAnual`
Expected: FAIL con `80.0 != 40.0`.

- [ ] **Step 3: Aplicar la corrección en `db_manager.py`**

Modificar `obtener_resumen_anual` en [db_manager.py](file:///C:/Users/admin/Proyectos/projects/print-money/db_manager.py#L750-L755):
```python
    ingresos = r["ingresos"]
    gastos = r2["gastos"]
    ganancia_pedidos = r["ganancia_pedidos"]
    ganancia = ganancia_pedidos - gastos
    return {
        "ingresos": ingresos,
        "gastos": gastos,
        "ganancia_neta": ganancia,
        "margen": (ganancia / ingresos * 100) if ingresos > 0 else 0,
        "num_pedidos": r["num_pedidos"],
    }
```

- [ ] **Step 4: Ejecutar el test para verificar que pasa**

Run: `python -m unittest tests_regression.py -k TestResumenAnual`
Expected: OK.

- [ ] **Step 5: Ejecutar suite completa y hacer commit**

Run: `python tests_regression.py`
Expected: Ran 36 tests ... OK.
Commit:
```bash
git add db_manager.py tests_regression.py
git commit -m "fix(db): corregir cálculo de ganancia anual descontando costos de pedidos"
```

---

### Task 2: Debounce de 250 ms en búsqueda de pedidos y clientes

**Files:**
- Modify: `ui/orders.py:110-120`
- Modify: `ui/clients.py:59-65`

**Interfaces:**
- Consumes: Eventos de teclado `<KeyRelease>` de `entry_buscar`.
- Produces: Cancelación de temporizador pendiente con `self.after_cancel` y diferimiento de consulta mediante `self.after(250, ...)`.

- [ ] **Step 1: Modificar `ui/orders.py` implementando debounce**

En `ui/orders.py`, inicializar `self._debounce_buscar = None` en `__init__`.
Reemplazar en línea ~115:
```python
self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)
```
Y agregar el método:
```python
def _on_buscar_tecla(self, event=None):
    if getattr(self, "_debounce_buscar", None) is not None:
        try:
            self.after_cancel(self._debounce_buscar)
        except Exception:
            pass
    self._debounce_buscar = self.after(250, self._filtrar)
```

- [ ] **Step 2: Modificar `ui/clients.py` implementando debounce**

En `ui/clients.py`, inicializar `self._debounce_buscar = None` en `__init__`.
Reemplazar en línea ~63:
```python
self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)
```
Y agregar el método:
```python
def _on_buscar_tecla(self, event=None):
    if getattr(self, "_debounce_buscar", None) is not None:
        try:
            self.after_cancel(self._debounce_buscar)
        except Exception:
            pass
    self._debounce_buscar = self.after(250, self._filtrar_clientes)
```

- [ ] **Step 3: Validar que no hay errores de sintaxis ni regresión**

Run: `python -m py_compile ui/orders.py ui/clients.py`
Run: `python tests_regression.py`
Expected: OK.

- [ ] **Step 4: Commit**

```bash
git add ui/orders.py ui/clients.py
git commit -m "perf(ui): aplicar debounce de 250ms en búsqueda de pedidos y clientes"
```

---

### Task 3: Limpieza de eventos en calendario e índice `idx_pedidos_entrega`

**Files:**
- Modify: `db_manager.py:192-205`
- Modify: `ui/calendar.py:105-125`

**Interfaces:**
- Consumes: `self.cal.calevent_remove('all')` de `tkcalendar`.
- Produces: Base de datos con índice `idx_pedidos_entrega ON pedidos(fecha_entrega)`.

- [ ] **Step 1: Agregar índice en `db_manager.py`**

En `db_manager.py`, dentro de `inicializar_db()`, agregar en la lista de índices:
```python
"CREATE INDEX IF NOT EXISTS idx_pedidos_entrega ON pedidos(fecha_entrega)",
```

- [ ] **Step 2: Limpiar eventos previos antes de poblar el calendario**

En `ui/calendar.py`, modificar `_marcar_fechas_calendario(self)`:
```python
    def _marcar_fechas_calendario(self):
        if not TkCalendar or not hasattr(self, "cal"):
            return
        # Evitar duplicación de marcadores al cambiar de pestaña
        try:
            self.cal.calevent_remove("all")
        except Exception:
            pass

        for p in self._todos_pedidos:
            if p.get("fecha_entrega") and p.get("estado") == "pendiente":
                try:
                    d = datetime.strptime(p["fecha_entrega"], "%Y-%m-%d")
                    self.cal.calevent_create(d.date(), p.get("cliente_nombre") or "Pedido", "pedido")
                except Exception:
                    pass
        try:
            self.cal.tag_config("pedido", background=COLOR_ACCENT, foreground="#000000")
        except Exception:
            pass
```

- [ ] **Step 3: Validar sintaxis y pruebas**

Run: `python tests_regression.py`
Expected: OK.

- [ ] **Step 4: Commit**

```bash
git add db_manager.py ui/calendar.py
git commit -m "fix(calendar): eliminar duplicación de eventos y añadir índice idx_pedidos_entrega"
```

---

### Task 4: Consulta mensual consolidada en un solo `GROUP BY`

**Files:**
- Modify: `db_manager.py:700-740`
- Modify: `utils/export.py:25-45, 120-140`

**Interfaces:**
- Consumes: `pedidos` y `gastos` de un año en SQLite.
- Produces: `obtener_resumen_mensual_anual(year: int) -> dict[int, dict]` que retorna los 12 meses consolidados en solo 2 queries SQL.

- [ ] **Step 1: Crear función en `db_manager.py`**

En `db_manager.py`:
```python
def obtener_resumen_mensual_anual(year: int):
    """Retorna ingresos, gastos, ganancia y pedidos para los 12 meses del año en 2 consultas."""
    year = int(year)
    fecha_inicio = f"{year}-01-01"
    fecha_fin = f"{year + 1}-01-01"

    meses = {
        m: {"ingresos": 0.0, "gastos": 0.0, "ganancia_pedidos": 0.0, "ganancia_neta": 0.0, "margen": 0.0, "num_pedidos": 0}
        for m in range(1, 13)
    }

    with obtener_conexion() as conn:
        # 1. Pedidos agrupados por mes
        rows_ped = conn.execute(f"""
            SELECT CAST(strftime('%m', fecha) AS INTEGER) as mes,
                   COALESCE(SUM(precio_venta), 0) as ingresos,
                   COALESCE(SUM(ganancia), 0) as ganancia_pedidos,
                   COUNT(*) as num_pedidos
            FROM pedidos
            WHERE fecha >= ? AND fecha < ? AND {_COND_ACTIVO}
            GROUP BY strftime('%m', fecha)
        """, (fecha_inicio, fecha_fin)).fetchall()

        for r in rows_ped:
            m = r["mes"]
            if m in meses:
                meses[m]["ingresos"] = float(r["ingresos"])
                meses[m]["ganancia_pedidos"] = float(r["ganancia_pedidos"])
                meses[m]["num_pedidos"] = int(r["num_pedidos"])

        # 2. Gastos agrupados por mes
        rows_gas = conn.execute("""
            SELECT CAST(strftime('%m', fecha) AS INTEGER) as mes,
                   COALESCE(SUM(monto), 0) as gastos
            FROM gastos
            WHERE fecha >= ? AND fecha < ?
            GROUP BY strftime('%m', fecha)
        """, (fecha_inicio, fecha_fin)).fetchall()

        for r in rows_gas:
            m = r["mes"]
            if m in meses:
                meses[m]["gastos"] = float(r["gastos"])

    # Calcular ganancias netas y márgenes consolidados
    for m, d in meses.items():
        ganancia_neta = d["ganancia_pedidos"] - d["gastos"]
        d["ganancia_neta"] = ganancia_neta
        d["margen"] = (ganancia_neta / d["ingresos"] * 100) if d["ingresos"] > 0 else 0.0

    return meses
```

- [ ] **Step 2: Actualizar `utils/export.py` para usar `obtener_resumen_mensual_anual`**

En `exportar_excel()`:
```python
    # Resumen mensual en 2 consultas en lugar de 36
    resumen_meses = db_manager.obtener_resumen_mensual_anual(año)
    resumen = []
    for mes in range(1, 13):
        stats = resumen_meses[mes]
        resumen.append({
            "Mes": datetime(año, mes, 1).strftime("%B"),
            "Ingresos ($)": stats["ingresos"],
            "Gastos ($)": stats["gastos"],
            "Ganancia Neta ($)": stats["ganancia_neta"],
            "Margen (%)": round(stats["margen"], 2),
            "Pedidos": stats["num_pedidos"],
        })
```
En `exportar_pdf_reporte()`:
```python
    resumen_meses = db_manager.obtener_resumen_mensual_anual(año)
    headers = ["Mes", "Ingresos", "Gastos", "Ganancia Neta", "Margen %", "Pedidos"]
    rows = [headers]
    total_ingresos = total_gastos = total_ganancia = 0
    for mes in range(1, 13):
        stats = resumen_meses[mes]
        total_ingresos += stats["ingresos"]
        total_gastos   += stats["gastos"]
        total_ganancia += stats["ganancia_neta"]
        rows.append([
            datetime(año, mes, 1).strftime("%B"),
            f"${stats['ingresos']:,.2f}",
            f"${stats['gastos']:,.2f}",
            f"${stats['ganancia_neta']:,.2f}",
            f"{stats['margen']:.1f}%",
            str(stats["num_pedidos"]),
        ])
```

- [ ] **Step 3: Verificar con test unitario**

Agregar en `tests_regression.py` un test que compruebe la concordancia entre `obtener_estadisticas_mes` y `obtener_resumen_mensual_anual`.
Run: `python tests_regression.py`
Expected: OK.

- [ ] **Step 4: Commit**

```bash
git add db_manager.py utils/export.py tests_regression.py
git commit -m "perf(export): consolidar resumen mensual anual en 2 consultas SQL"
```

---

### Task 5: Exportaciones y generación de facturas en hilo secundario

**Files:**
- Modify: `ui/reports.py:150-210`
- Modify: `ui/orders.py:550-575`

**Interfaces:**
- Consumes: `threading.Thread(target=..., daemon=True)` y `self.after(0, ...)`.
- Produces: Interfaz de usuario responsiva sin congelamiento durante la generación de archivos PDF/Excel.

- [ ] **Step 1: Desacoplar exportación en `ui/reports.py`**

En los métodos de exportación de `ui/reports.py`:
```python
import threading

def _ejecutar_exportacion_async(self, fn_export, ruta, año, mensaje_exito):
    def tarea():
        try:
            fn_export(ruta, año)
            self.after(0, lambda: messagebox.showinfo(T("reports_export_title"), mensaje_exito, parent=self.winfo_toplevel()))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(T("error"), f"{T('reports_export_err')}: {e}", parent=self.winfo_toplevel()))
    threading.Thread(target=tarea, daemon=True).start()
```

- [ ] **Step 2: Desacoplar generación de factura en `ui/orders.py`**

En `ui/orders.py`, método `_generar_factura_pdf(self)`:
```python
def _generar_factura_pdf_async(self, ruta, pedido, config):
    def tarea():
        try:
            from utils.export import exportar_factura_pdf
            exportar_factura_pdf(ruta, pedido, config)
            self.after(0, lambda: messagebox.showinfo(T("orders_invoice"), T("orders_invoice_saved", ruta=ruta), parent=self.winfo_toplevel()))
        except Exception as e:
            self.after(0, lambda: messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel()))
    threading.Thread(target=tarea, daemon=True).start()
```

- [ ] **Step 3: Validar que no hay errores de import o sintaxis**

Run: `python -m py_compile ui/reports.py ui/orders.py`
Expected: OK.

- [ ] **Step 4: Commit**

```bash
git add ui/reports.py ui/orders.py
git commit -m "feat(ui): mover generación de exports y PDFs a hilos secundarios con callbacks seguros"
```

---

### Task 6: Reutilización de configuración en memoria (`cargar_config` -> `app.config_data`)

**Files:**
- Modify: `ui/orders.py:445-465`

**Interfaces:**
- Consumes: `self.app.config_data` preexistente en `App`.
- Produces: Cero accesos de I/O a `config.json` al teclear números en los campos de gramos, horas o precio de venta.

- [ ] **Step 1: Modificar `_calcular_costo` y `_verificar_margen` en `ui/orders.py`**

En [ui/orders.py:447](file:///C:/Users/admin/Proyectos/projects/print-money/ui/orders.py#L447):
```python
        try:
            horas = float(self.ent_horas.get() or 0)
            config = getattr(self.app, "config_data", None) or cargar_config()
            tarifa = config.get("tarifa_por_hora", 5.0) or 5.0
            ...
```
En [ui/orders.py:458](file:///C:/Users/admin/Proyectos/projects/print-money/ui/orders.py#L458):
```python
        try:
            config = getattr(self.app, "config_data", None) or cargar_config()
            margen_obj = config.get("margen_objetivo", 0)
            ...
```

- [ ] **Step 2: Validar suite de pruebas**

Run: `python tests_regression.py`
Expected: OK.

- [ ] **Step 3: Commit**

```bash
git add ui/orders.py
git commit -m "perf(orders): usar app.config_data en cálculos para evitar lectura de disco por tecla"
```

---

### Task 7: Robustez y manejo de excepciones en escrituras (`ui/clients.py`, `ui/expenses.py`, `ui/inventory.py`)

**Files:**
- Modify: `ui/clients.py:215-245`
- Modify: `ui/expenses.py:265-295`
- Modify: `ui/inventory.py:210-235`

**Interfaces:**
- Consumes: Métodos de escritura de `db_manager`.
- Produces: Diálogos de advertencia y error con `parent=self.winfo_toplevel()`, captura de excepciones SQLite y refresco seguro del estado.

- [ ] **Step 1: Proteger operaciones en `ui/clients.py`**

En `_guardar_cliente` y `_eliminar_cliente`:
- Envolver las llamadas a `db_manager.actualizar_cliente`, `db_manager.agregar_cliente` y `db_manager.eliminar_cliente` en bloques `try...except Exception as e:`.
- En caso de excepción: `messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())`.
- Asegurar `parent=self.winfo_toplevel()` en `messagebox.showwarning` y `messagebox.askyesno`.

- [ ] **Step 2: Proteger operaciones en `ui/expenses.py`**

En `_guardar_gasto` y `_eliminar_gasto`:
- Envolver `db_manager.actualizar_gasto`, `db_manager.agregar_gasto` y `db_manager.eliminar_gasto` en `try...except Exception as e:`.
- Notificar errores con `messagebox.showerror(..., parent=self.winfo_toplevel())`.
- Asegurar `parent=self.winfo_toplevel()` en todos los diálogos.

- [ ] **Step 3: Proteger operaciones en `ui/inventory.py`**

En `_guardar_filamento` y `_eliminar_filamento`:
- Envolver `db_manager.actualizar_filamento`, `db_manager.agregar_filamento` y `db_manager.eliminar_filamento` en `try...except Exception as e:`.
- Notificar con `parent=self.winfo_toplevel()`.

- [ ] **Step 4: Ejecutar suite de pruebas**

Run: `python tests_regression.py`
Expected: OK.

- [ ] **Step 5: Commit**

```bash
git add ui/clients.py ui/expenses.py ui/inventory.py
git commit -m "fix(ui): blindar escrituras de clientes, gastos e inventario con try-except y modal parent"
```

---

### Task 8: Logging estructurado y `report_callback_exception` en `main.py`

**Files:**
- Modify: `main.py:10-35, 110-150`

**Interfaces:**
- Consumes: `logging` estándar de Python y `Tk.report_callback_exception`.
- Produces: Archivo `printmoney.log` y captura controlada de excepciones de interfaz sin fallos silenciosos.

- [ ] **Step 1: Configurar logging en `main.py`**

Al inicio de `main.py`:
```python
import logging

LOG_PATH = os.path.join(BASE_DIR, "printmoney.log")
logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    encoding="utf-8"
)
```

- [ ] **Step 2: Instrumentar `report_callback_exception` en la clase `App`**

En el `__init__` de `App` en `main.py`:
```python
        # Captura de excepciones globales en callbacks de Tkinter
        self.report_callback_exception = self._on_tk_exception
```
Y agregar el método:
```python
    def _on_tk_exception(self, exc, val, tb):
        import traceback
        logging.error("Excepción no capturada en callback de UI:\n%s", "".join(traceback.format_exception(exc, val, tb)))
        try:
            messagebox.showerror(
                T("error"),
                f"Ocurrió un error inesperado:\n{val}\n\nLos detalles técnicos se guardaron en 'printmoney.log'.",
                parent=self
            )
        except Exception:
            pass
```

- [ ] **Step 3: Validar que la aplicación inicializa sin errores**

Run: `python tests_ui_smoke.py` (o `python -m py_compile main.py`)
Run: `python tests_regression.py`
Expected: OK.

- [ ] **Step 4: Commit**

```bash
git add main.py
git commit -m "feat(core): configurar logging rotativo y captura de excepciones con report_callback_exception"
```

---

### Task 9: Eliminación del autoguardado simulado

**Files:**
- Modify: `main.py:630-660`
- Modify: `ui/settings.py:155-160, 245-285`
- Modify: `tests_regression.py:179-186`

**Interfaces:**
- Consumes: `_iniciar_autoguardado` en `main.py`.
- Produces: Eliminación de temporizador falso que engañaba al usuario y mantenía tareas repetitivas en el event loop.

- [ ] **Step 1: Eliminar el ticker de autoguardado en `main.py`**

Remover la llamada `self._iniciar_autoguardado()` y el método `_iniciar_autoguardado()` de `main.py`, ya que SQLite persiste de forma transaccional e inmediata en cada operación `commit`.

- [ ] **Step 2: Actualizar `ui/settings.py` y `tests_regression.py`**

En `ui/settings.py`, retirar el campo de texto de minutos de autoguardado o dejarlo deshabilitado explicando que las operaciones son guardadas al instante.
En `tests_regression.py`, remover la clase obsoleta `TestAutoguardado`.

- [ ] **Step 3: Ejecutar suite de pruebas completa**

Run: `python tests_regression.py`
Expected: All tests pass.

- [ ] **Step 4: Commit**

```bash
git add main.py ui/settings.py tests_regression.py
git commit -m "refactor(core): remover autoguardado simulado y limpiar temporizadores obsoletos"
```
