# ui/orders.py – Vista de Pedidos (Órdenes)
# Permite agregar, editar, filtrar y exportar pedidos. Genera facturas PDF.

import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date, datetime
import db_manager
from utils.i18n import T
from utils.labels import mapa_por_etiqueta
from utils import paths
from ui import theme as th
from ui import components as ui
import json, os
import threading

BASE_DIR = paths.DATA_DIR

ESTADOS = ["pendiente", "en proceso", "completado", "cancelado"]

# Pedidos por página. Antes se renderizaban TODOS los pedidos de golpe: con
# 1000 pedidos eran 8000 widgets de Tkinter y la vista se quedaba congelada
# más de 13 segundos. Ahora solo se crea la página visible.
TAMANO_PAGINA = 50


def cargar_config():
    """Lee config.json tolerando un fichero ausente o corrupto."""
    try:
        with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


class OrdersView(ctk.CTkFrame):
    """Vista principal de gestión de pedidos."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._pedido_editando = None   # ID del pedido en edición
        self._cotizacion_id = None     # cotización que originó el formulario
        self._pagina = 0               # página visible (base 0)
        self._total_filtrados = 0      # pedidos que cumplen el filtro
        self._total_paginas = 1
        self._todos_pedidos = []       # pedidos de la página actual
        self._debounce_buscar = None
        self._construir_ui()

    def on_show(self):
        """Refresca los datos al volver a esta vista."""
        self._cargar_dropdowns()
        self._pagina = 0
        self._aplicar_filtros()

    # ──────────────── CARGA DE LISTADOS ────────────────

    def _cargar_dropdowns(self):
        """Rellena los desplegables de clientes y filamentos."""
        try:
            self._clientes_data = mapa_por_etiqueta(
                db_manager.obtener_clientes(), lambda c: c["nombre"])
            valores_clientes = [T("orders_no_client")] + list(self._clientes_data.keys())
            self.combo_cliente.configure(values=valores_clientes)
            if self.combo_cliente.get() not in valores_clientes:
                self.combo_cliente.set(T("orders_no_client"))
        except Exception:
            pass

        try:
            self._filamentos_data = mapa_por_etiqueta(
                db_manager.obtener_filamentos(),
                lambda f: f"{f['nombre']} ({f['material']})")
            valores_filamentos = [T("orders_no_filament")] + list(self._filamentos_data.keys())
            self.combo_filamento_form.configure(values=valores_filamentos)
            if self.combo_filamento_form.get() not in valores_filamentos:
                self.combo_filamento_form.set(T("orders_no_filament"))
        except Exception:
            pass

    def _construir_ui(self):
        """Construye el layout de dos paneles: tabla izq. / formulario der."""
        # ── Encabezado ──
        _, acciones = ui.page_header(self, T("orders_title"))

        ui.primary_button(acciones, T("orders_new"), self._nuevo_pedido,
                          width=150).pack(side="right")

        # ── Barra de filtros ──
        frame_filtros = ui.card(self, corner_radius=th.RADIUS_CARD)
        frame_filtros.pack(fill="x", padx=th.PAD_PAGE, pady=12)

        ui.section_label(frame_filtros, T("orders_search")).pack(
            side="left", padx=(10, 4), pady=8)

        self.entry_buscar = ui.entry(frame_filtros, T("orders_search_ph"), width=200)
        self.entry_buscar.pack(side="left", pady=8)
        self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)

        ui.section_label(frame_filtros, T("orders_status")).pack(
            side="left", padx=(12, 4))

        self.combo_estado = ui.option_menu(
            frame_filtros, values=[T("orders_all")] + ESTADOS, width=140,
            command=lambda _: self._filtrar()
        )
        self.combo_estado.pack(side="left", pady=8, padx=4)

        # ── Layout principal: tabla + formulario ──
        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=(0, 20))
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        # ── Tabla de pedidos ──
        frame_tabla = ctk.CTkFrame(frame_main, fg_color="transparent")
        frame_tabla.grid(row=0, column=0, padx=(0, th.GAP), sticky="nsew")

        cols = [T("orders_col_id"), T("orders_col_date"), T("orders_col_client"),
                T("orders_col_desc"), T("orders_col_sale"), T("orders_col_profit"),
                T("orders_col_status")]

        # ── Paginación (se empaqueta antes de la tabla para quedar abajo) ──
        frame_pag = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        frame_pag.pack(side="bottom", fill="x", pady=(th.GAP, 0))

        self.btn_anterior = ui.secondary_button(
            frame_pag, T("orders_prev"), lambda: self._cambiar_pagina(-1),
            width=100, height=30)
        self.btn_anterior.pack(side="left")

        self.lbl_pagina = ctk.CTkLabel(frame_pag, text="", text_color=th.SUB,
                                       font=th.fuente(th.FONT_LABEL))
        self.lbl_pagina.pack(side="left", expand=True)

        self.btn_siguiente = ui.secondary_button(
            frame_pag, T("orders_next"), lambda: self._cambiar_pagina(1),
            width=100, height=30)
        self.btn_siguiente.pack(side="right")

        self.tabla = ui.DataTable(frame_tabla, columnas=cols, pesos=[1, 2, 3, 4, 2, 2, 2],
                                  alinear=["w", "w", "w", "w", "e", "e", "w"],
                                  on_select=lambda p: self._seleccionar_pedido(p["id"]))
        self.frame_tabla_scroll = self.tabla.scroll
        self.tabla.pack(fill="both", expand=True)

        # ── Formulario de pedido ──
        self.frame_form = ui.scrollable(frame_main, fg_color=th.CARD,
                                        corner_radius=th.RADIUS_CARD,
                                        border_width=1, border_color=th.BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")

        self._construir_formulario(self.frame_form)

    def _celda(self, parent, fila, columna, etiqueta, colspan=1):
        """Crea la celda de un campo del formulario y devuelve su contenedor."""
        celda = ctk.CTkFrame(parent, fg_color="transparent")
        if colspan > 1:
            padx = 0
        elif columna == 0:
            padx = (0, th.GAP // 2)
        else:
            padx = (th.GAP // 2, 0)
        celda.grid(row=fila, column=columna, columnspan=colspan, sticky="ew",
                   padx=padx, pady=(0, th.GAP))
        ui.section_label(celda, etiqueta).pack(anchor="w", pady=(0, 2))
        return celda

    def _construir_formulario(self, parent):
        """Construye el formulario de entrada de pedidos."""
        # Encabezado del formulario
        frame_form_head = ctk.CTkFrame(parent, fg_color="transparent")
        frame_form_head.pack(fill="x", padx=14, pady=(14, 8))

        ui.section_title(frame_form_head, T("orders_form_title")).pack(side="left")

        ui.secondary_button(frame_form_head, T("orders_load_catalog"),
                            self._abrir_modal_catalogo, width=150,
                            height=th.H_BTN_SM).pack(side="right")

        grid_form = ctk.CTkFrame(parent, fg_color="transparent")
        grid_form.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        grid_form.grid_columnconfigure(0, weight=1, uniform="form")
        grid_form.grid_columnconfigure(1, weight=1, uniform="form")

        # ── Datos ──
        ui.section_title(grid_form, T("orders_section_data")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        celda = self._celda(grid_form, 1, 0, T("orders_date"))
        self.ent_fecha = ui.entry(celda, "YYYY-MM-DD")
        self.ent_fecha.pack(fill="x")

        celda = self._celda(grid_form, 1, 1, T("orders_client"))
        self._cargar_combo_clientes(celda)

        celda = self._celda(grid_form, 2, 0, T("orders_desc"), colspan=2)
        self.ent_desc = ui.entry(celda, T("orders_desc_ph"))
        self.ent_desc.pack(fill="x")

        celda = self._celda(grid_form, 3, 0, T("orders_filament"))
        self._cargar_combo_filamentos(celda)

        celda = self._celda(grid_form, 3, 1, T("orders_state"))
        self.combo_estado_form = ui.option_menu(celda, values=ESTADOS)
        self.combo_estado_form.pack(fill="x")

        celda = self._celda(grid_form, 4, 0, T("orders_notes"), colspan=2)
        self.ent_notas = ui.entry(celda, T("orders_notes_ph"))
        self.ent_notas.pack(fill="x")

        # ── Costos ──
        ui.section_title(grid_form, T("orders_section_costs")).grid(
            row=5, column=0, columnspan=2, sticky="w", pady=(4, 6))

        celda = self._celda(grid_form, 6, 0, T("orders_grams"))
        self.ent_gramos = ui.entry(celda, "0")
        self.ent_gramos.pack(fill="x")
        self.ent_gramos.bind("<KeyRelease>", lambda e: self._calcular_costo())

        celda = self._celda(grid_form, 6, 1, T("orders_hours"))
        self.ent_horas = ui.entry(celda, "0")
        self.ent_horas.pack(fill="x")
        self.ent_horas.bind("<KeyRelease>", lambda e: self._calcular_costo())

        celda = self._celda(grid_form, 7, 0, T("orders_material_cost"))
        self.ent_costo_mat = ui.entry(celda, "0.00")
        self.ent_costo_mat.pack(fill="x")

        celda = self._celda(grid_form, 7, 1, T("orders_time_cost"))
        self.ent_costo_tiempo = ui.entry(celda, "0.00")
        self.ent_costo_tiempo.pack(fill="x")

        celda = self._celda(grid_form, 8, 0, T("orders_shipping"))
        self.ent_envio = ui.entry(celda, "0.00")
        self.ent_envio.pack(fill="x")

        # ── Entrega ──
        ui.section_title(grid_form, T("orders_section_delivery")).grid(
            row=9, column=0, columnspan=2, sticky="w", pady=(4, 6))

        celda = self._celda(grid_form, 10, 0, T("orders_sale_price"))
        self.ent_venta = ui.entry(celda, "0.00")
        self.ent_venta.pack(fill="x")
        self.ent_venta.bind("<KeyRelease>", lambda e: self._verificar_margen())

        celda = self._celda(grid_form, 10, 1, T("orders_delivery"))
        self.ent_entrega = ui.entry(celda, "YYYY-MM-DD")
        self.ent_entrega.pack(fill="x")

        # Alerta de margen
        self.lbl_margen_alerta = ctk.CTkLabel(
            grid_form, text="", text_color=th.RED, anchor="w",
            font=th.fuente(th.FONT_LABEL)
        )
        self.lbl_margen_alerta.grid(row=11, column=0, columnspan=2, sticky="w",
                                    pady=(0, th.GAP))

        ui.divider(grid_form).grid(row=12, column=0, columnspan=2, sticky="ew",
                                   pady=(2, 10))

        # Botones de acción
        ui.primary_button(grid_form, T("orders_save"), self._guardar_pedido).grid(
            row=13, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        ui.danger_button(grid_form, T("orders_delete"), self._eliminar_pedido).grid(
            row=14, column=0, columnspan=2, sticky="ew", pady=(0, 6))

        ui.secondary_button(grid_form, T("orders_invoice"), self._generar_factura).grid(
            row=15, column=0, columnspan=2, sticky="ew")

    def _cargar_combo_clientes(self, parent):
        """Carga el dropdown de clientes."""
        self._clientes_data = mapa_por_etiqueta(
            db_manager.obtener_clientes(), lambda c: c["nombre"])
        valores = [T("orders_no_client")] + list(self._clientes_data.keys())
        self.combo_cliente = ui.option_menu(parent, values=valores)
        self.combo_cliente.pack(fill="x")

    def _cargar_combo_filamentos(self, parent):
        """Carga el dropdown de filamentos."""
        self._filamentos_data = mapa_por_etiqueta(
            db_manager.obtener_filamentos(),
            lambda f: f"{f['nombre']} ({f['material']})")
        valores = [T("orders_no_filament")] + list(self._filamentos_data.keys())
        self.combo_filamento_form = ui.option_menu(
            parent, values=valores,
            command=lambda _: self._calcular_costo()
        )
        self.combo_filamento_form.pack(fill="x")

    # ──────────────── FILTRADO Y PAGINACIÓN ────────────────

    def _filtros_actuales(self):
        """Devuelve (texto, estado) con el filtro de estado normalizado."""
        texto = self.entry_buscar.get().strip()
        estado = self.combo_estado.get()
        if estado == T("orders_all"):
            estado = None
        return texto, estado

    def _aplicar_filtros(self):
        """Consulta la página actual aplicando los filtros en SQL."""
        texto, estado = self._filtros_actuales()
        offset = self._pagina * TAMANO_PAGINA
        self._todos_pedidos = db_manager.obtener_pedidos(
            filtro_texto=texto, filtro_estado=estado,
            limite=TAMANO_PAGINA, offset=offset)
        self._total_filtrados = db_manager.contar_pedidos(
            filtro_texto=texto, filtro_estado=estado)
        self._total_paginas = max(1, (self._total_filtrados + TAMANO_PAGINA - 1) // TAMANO_PAGINA)
        if self._pagina >= self._total_paginas:
            self._pagina = max(0, self._total_paginas - 1)
        self._renderizar_filas(self._todos_pedidos)
        self._actualizar_paginacion()

    def _on_buscar_tecla(self, event=None):
        if getattr(self, "_debounce_buscar", None) is not None:
            try:
                self.after_cancel(self._debounce_buscar)
            except Exception:
                pass
        self._debounce_buscar = self.after(250, self._filtrar)

    def _filtrar(self):
        """Aplica los filtros y vuelve a la primera página."""
        self._pagina = 0
        self._aplicar_filtros()

    def _cambiar_pagina(self, delta: int):
        nueva = self._pagina + delta
        if 0 <= nueva < self._total_paginas:
            self._pagina = nueva
            self._aplicar_filtros()

    def _actualizar_paginacion(self):
        """Actualiza el texto de paginación y el estado de los botones."""
        if self._total_paginas > 1:
            self.lbl_pagina.configure(text=T(
                "orders_page", page=self._pagina + 1, total=self._total_paginas))
        else:
            self.lbl_pagina.configure(text=T(
                "orders_page", page=1, total=1))
        self.btn_anterior.configure(state="normal" if self._pagina > 0 else "disabled")
        self.btn_siguiente.configure(
            state="normal" if self._pagina < self._total_paginas - 1 else "disabled")

    def _cargar_pedidos(self):
        """Recarga la tabla conservando los filtros y la página actual."""
        self._aplicar_filtros()

    def _renderizar_filas(self, pedidos):
        """Renderiza las filas de la página actual en la tabla."""
        firma = tuple(
            (p["id"], p.get("fecha"), p.get("cliente_nombre"), p.get("descripcion"),
             p.get("precio_venta"), p.get("ganancia"), p.get("estado"))
            for p in pedidos
        )
        if firma == getattr(self, "_firma_tabla_pedidos", None):
            return
        self._firma_tabla_pedidos = firma

        if not pedidos:
            self.tabla.mostrar_vacio(T("orders_no_results"), icono="📦",
                                     hint=T("orders_empty_hint"))
            return

        celdas = [
            [
                str(p["id"]),
                p.get("fecha", ""),
                (p.get("cliente_nombre") or "—")[:18],
                (p.get("descripcion") or "—")[:22],
                f"${p.get('precio_venta', 0):.2f}",
                f"${p.get('ganancia', 0):.2f}",
                (p.get("estado", ""), th.ESTADO_COLORES.get(
                    (p.get("estado") or "").strip().lower(), th.SUB)),
            ]
            for p in pedidos
        ]
        self.tabla.set_rows(pedidos, celdas, firma=firma)

    # ──────────────── SELECCIÓN Y FORMULARIO ────────────────

    def _seleccionar_pedido(self, pedido_id):
        """Carga un pedido en el formulario para edición."""
        p = db_manager.obtener_pedido_por_id(pedido_id)
        if not p:
            return
        self._pedido_editando = pedido_id
        self._cotizacion_id = None
        self.lbl_margen_alerta.configure(text="")

        def set_entry(e, val):
            e.delete(0, "end")
            e.insert(0, str(val or ""))

        set_entry(self.ent_fecha, p.get("fecha", ""))
        set_entry(self.ent_desc, p.get("descripcion", ""))
        set_entry(self.ent_gramos, p.get("gramos_usados", 0))
        set_entry(self.ent_horas, p.get("horas_impresion", 0))
        set_entry(self.ent_costo_mat, p.get("costo_material", 0))
        set_entry(self.ent_costo_tiempo, p.get("costo_tiempo", 0))
        set_entry(self.ent_envio, p.get("costo_envio", 0))
        set_entry(self.ent_venta, p.get("precio_venta", 0))
        set_entry(self.ent_entrega, p.get("fecha_entrega", ""))
        set_entry(self.ent_notas, p.get("notas", ""))
        if p.get("estado"):
            self.combo_estado_form.set(p["estado"])

        cliente_id = p.get("cliente_id")
        etiqueta_cliente = None
        if cliente_id:
            for etiqueta, datos in self._clientes_data.items():
                if datos["id"] == cliente_id:
                    etiqueta_cliente = etiqueta
                    break
        self.combo_cliente.set(etiqueta_cliente or T("orders_no_client"))

        filamento_id = p.get("filamento_id")
        etiqueta_filamento = None
        if filamento_id:
            for etiqueta, datos in self._filamentos_data.items():
                if datos["id"] == filamento_id:
                    etiqueta_filamento = etiqueta
                    break
        self.combo_filamento_form.set(etiqueta_filamento or T("orders_no_filament"))

    def _nuevo_pedido(self):
        """Limpia el formulario para ingresar un nuevo pedido."""
        self._pedido_editando = None
        self._cotizacion_id = None
        for e in [self.ent_fecha, self.ent_desc, self.ent_gramos, self.ent_horas,
                  self.ent_costo_mat, self.ent_costo_tiempo, self.ent_envio,
                  self.ent_venta, self.ent_entrega, self.ent_notas]:
            e.delete(0, "end")
        self.ent_fecha.insert(0, str(date.today()))
        self.combo_estado_form.set("pendiente")
        self.combo_cliente.set(T("orders_no_client"))
        self.combo_filamento_form.set(T("orders_no_filament"))
        self.lbl_margen_alerta.configure(text="")

    def _calcular_costo(self, *_):
        """Calcula el costo del material automáticamente."""
        try:
            nombre_fil = self.combo_filamento_form.get()
            fil = self._filamentos_data.get(nombre_fil, {})
            precio_kg = fil.get("precio_por_kg", 0) or 0
            gramos = float(self.ent_gramos.get() or 0)
            costo = gramos * precio_kg / 1000
            self.ent_costo_mat.delete(0, "end")
            self.ent_costo_mat.insert(0, f"{costo:.2f}")

            # Costo tiempo
            horas = float(self.ent_horas.get() or 0)
            config = getattr(self.app, "config_data", None) or cargar_config()
            tarifa = config.get("tarifa_por_hora", 5.0) or 5.0
            costo_t = horas * float(tarifa)
            self.ent_costo_tiempo.delete(0, "end")
            self.ent_costo_tiempo.insert(0, f"{costo_t:.2f}")
        except (ValueError, TypeError):
            pass

    def _verificar_margen(self, *_):
        """Alerta si el margen de venta está por debajo del objetivo."""
        try:
            config = getattr(self.app, "config_data", None) or cargar_config()
            margen_obj = config.get("margen_objetivo", 0)
            if not margen_obj:
                return
            costo = (float(self.ent_costo_mat.get() or 0) +
                     float(self.ent_costo_tiempo.get() or 0) +
                     float(self.ent_envio.get() or 0))
            venta = float(self.ent_venta.get() or 0)
            margen = ((venta - costo) / venta * 100) if venta > 0 else 0
            if margen < margen_obj:
                self.lbl_margen_alerta.configure(
                    text=T("orders_margin_warn", margin=margen, target=margen_obj)
                )
            else:
                self.lbl_margen_alerta.configure(text="")
        except (ValueError, TypeError):
            pass

    # ──────────────── PERSISTENCIA ────────────────

    def _validar_fecha(self, valor: str) -> bool:
        """Comprueba que la fecha tenga el formato YYYY-MM-DD."""
        if not valor:
            return True
        try:
            datetime.strptime(valor.strip(), "%Y-%m-%d")
            return True
        except ValueError:
            return False

    def _guardar_pedido(self):
        """Guarda o actualiza el pedido en la base de datos."""
        cliente_nombre = self.combo_cliente.get()
        cliente = self._clientes_data.get(cliente_nombre)
        filamento_nombre = self.combo_filamento_form.get()
        filamento = self._filamentos_data.get(filamento_nombre)

        fecha = self.ent_fecha.get().strip() or str(date.today())
        fecha_entrega = self.ent_entrega.get().strip()
        if not self._validar_fecha(fecha) or not self._validar_fecha(fecha_entrega):
            messagebox.showerror(T("error"), T("orders_invalid_date"),
                                 parent=self.winfo_toplevel())
            return

        # Los campos numéricos se parsean DENTRO del try: antes la conversión
        # estaba fuera y una letra en el precio abortaba el guardado sin
        # mostrar ningún error.
        try:
            datos = {
                "fecha":          fecha,
                "cliente_id":     cliente["id"] if cliente else None,
                "descripcion":    self.ent_desc.get(),
                "filamento_id":   filamento["id"] if filamento else None,
                "gramos_usados":  float(self.ent_gramos.get() or 0),
                "horas_impresion": float(self.ent_horas.get() or 0),
                "costo_material": float(self.ent_costo_mat.get() or 0),
                "costo_tiempo":   float(self.ent_costo_tiempo.get() or 0),
                "costo_envio":    float(self.ent_envio.get() or 0),
                "precio_venta":   float(self.ent_venta.get() or 0),
                "fecha_entrega":  fecha_entrega,
                "estado":         self.combo_estado_form.get(),
                "notas":          self.ent_notas.get(),
            }
        except (ValueError, TypeError):
            messagebox.showerror(T("error"), T("orders_invalid_nums"),
                                 parent=self.winfo_toplevel())
            return

        try:
            if self._pedido_editando:
                db_manager.actualizar_pedido(self._pedido_editando, datos)
            else:
                db_manager.agregar_pedido(datos, cotizacion_id=self._cotizacion_id)
            self._nuevo_pedido()
            self._cargar_pedidos()
        except Exception as ex:
            messagebox.showerror(T("error"), str(ex), parent=self.winfo_toplevel())

    def _eliminar_pedido(self):
        """Elimina el pedido seleccionado."""
        if not self._pedido_editando:
            messagebox.showwarning(T("warning"), T("orders_select_first"), parent=self.winfo_toplevel())
            return
        if messagebox.askyesno(T("confirm"), T("orders_confirm_del", id=self._pedido_editando), parent=self.winfo_toplevel()):
            db_manager.eliminar_pedido(self._pedido_editando)
            self._nuevo_pedido()
            self._cargar_pedidos()

    def _generar_factura(self):
        """Genera la factura PDF del pedido seleccionado."""
        if not self._pedido_editando:
            messagebox.showwarning(T("warning"), T("orders_select_saved"), parent=self.winfo_toplevel())
            return
        pedido = db_manager.obtener_pedido_por_id(self._pedido_editando)
        if not pedido:
            messagebox.showwarning(T("warning"), T("orders_select_saved"), parent=self.winfo_toplevel())
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"Factura_{self._pedido_editando}.pdf"
        )
        if ruta:
            config = getattr(self.app, "config_data", None) or cargar_config()
            pedido_id = self._pedido_editando

            def _worker():
                try:
                    from utils.pdf_invoice import generar_factura_pdf
                    generar_factura_pdf(pedido, config, ruta)
                    db_manager.marcar_factura_generada(pedido_id)
                    self.after(0, lambda: messagebox.showinfo(
                        T("success"),
                        T("orders_invoice_ok", path=ruta),
                        parent=self.winfo_toplevel()
                    ))
                except Exception as ex:
                    self.after(0, lambda err=str(ex): messagebox.showerror(
                        T("error"),
                        err,
                        parent=self.winfo_toplevel()
                    ))

            threading.Thread(target=_worker, daemon=True).start()

    def prellenar(self, datos: dict):
        """Pre-llena el formulario con datos de la calculadora o cotización."""
        self._nuevo_pedido()
        self._cotizacion_id = datos.get("cotizacion_id")
        if datos.get("gramos"):
            self.ent_gramos.insert(0, str(datos["gramos"]))
        if datos.get("horas"):
            self.ent_horas.insert(0, str(datos["horas"]))
        if datos.get("costo_material"):
            self.ent_costo_mat.insert(0, f"{datos['costo_material']:.2f}")
        if datos.get("costo_tiempo"):
            self.ent_costo_tiempo.insert(0, f"{datos['costo_tiempo']:.2f}")
        if datos.get("precio_sugerido"):
            self.ent_venta.insert(0, f"{datos['precio_sugerido']:.2f}")
        if datos.get("descripcion"):
            self.ent_desc.insert(0, datos["descripcion"])
        if datos.get("notas"):
            self.ent_notas.insert(0, datos["notas"])

        cliente_id = datos.get("cliente_id")
        if cliente_id:
            for etiqueta, info in self._clientes_data.items():
                if info["id"] == cliente_id:
                    self.combo_cliente.set(etiqueta)
                    break

        # La calculadora envía el filamento, pero antes se ignoraba: el pedido
        # se guardaba sin filamento y el inventario NO se descontaba.
        filamento_id = datos.get("filamento_id")
        if filamento_id:
            for etiqueta, info in self._filamentos_data.items():
                if info["id"] == filamento_id:
                    self.combo_filamento_form.set(etiqueta)
                    break

    def _abrir_modal_catalogo(self):
        """Abre un modal para seleccionar un producto del catálogo y autocompletar el formulario."""
        productos = db_manager.obtener_catalogo()
        if not productos:
            messagebox.showinfo(T("sidebar_catalog"), T("orders_catalog_empty"), parent=self.winfo_toplevel())
            return

        modal = ctk.CTkToplevel(self)
        modal.title(T("orders_catalog_select"))
        modal.geometry("400x450")
        modal.resizable(False, False)
        modal.grab_set()
        modal.focus_force()
        modal.configure(fg_color=th.BG)

        modal.update_idletasks()
        x = modal.winfo_screenwidth() // 2 - 200
        y = modal.winfo_screenheight() // 2 - 225
        modal.geometry(f"+{x}+{y}")

        ctk.CTkLabel(modal, text=T("orders_catalog_title"),
                     font=th.fuente(16, True), text_color=th.TEXT).pack(pady=16)

        scroll = ui.scrollable(modal)
        scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        def seleccionar(p):
            self.ent_desc.delete(0, "end")
            self.ent_desc.insert(0, p["nombre"])

            if p.get("filamento_nombre"):
                f_key = f"{p['filamento_nombre']} ({p.get('filamento_material', 'PLA')})"
                if f_key in self._filamentos_data:
                    self.combo_filamento_form.set(f_key)
                else:
                    # Puede haber un homónimo con etiqueta "(2)"
                    for etiqueta, info in self._filamentos_data.items():
                        if info["nombre"] == p["filamento_nombre"]:
                            self.combo_filamento_form.set(etiqueta)
                            break

            self.ent_gramos.delete(0, "end")
            self.ent_gramos.insert(0, str(p["gramos_estimados"]))
            self.ent_horas.delete(0, "end")
            self.ent_horas.insert(0, str(p["horas_estimadas"]))
            self.ent_venta.delete(0, "end")
            self.ent_venta.insert(0, f"{p['precio_sugerido']:.2f}")

            self._calcular_costo()
            self._verificar_margen()
            modal.destroy()

        for p in productos:
            card = ui.card(scroll, corner_radius=th.RADIUS_INPUT, cursor="hand2")
            card.pack(fill="x", pady=3)
            card.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))

            f_top = ctk.CTkFrame(card, fg_color="transparent")
            f_top.pack(fill="x", padx=10, pady=(8, 2))
            f_top.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))

            ctk.CTkLabel(f_top, text=p["nombre"], font=th.fuente(12, True),
                         text_color=th.TEXT).pack(side="left")
            ctk.CTkLabel(f_top, text=f"${p['precio_sugerido']:.2f}",
                         font=th.fuente(12, True),
                         text_color=th.ACCENT).pack(side="right")

            ctk.CTkLabel(card, text=p.get("descripcion", ""), font=th.fuente(10),
                         text_color=th.SUB).pack(anchor="w", padx=10, pady=(0, 8))

            # Asegurar que el click en los labels también dispare la selección
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))
                for subchild in child.winfo_children():
                    subchild.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))
