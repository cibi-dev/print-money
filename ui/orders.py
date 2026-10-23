# ui/orders.py – Vista de Pedidos (Órdenes)
# Permite agregar, editar, filtrar y exportar pedidos. Genera facturas PDF.

import customtkinter as ctk
from tkinter import messagebox, filedialog
from datetime import date, datetime
import db_manager
from utils.pdf_invoice import generar_factura_pdf
from utils.i18n import T
from utils.labels import mapa_por_etiqueta
import json, os
import threading

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_RED    = "#FF4C4C"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"
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
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._pedido_editando = None   # ID del pedido en edición
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
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))

        ctk.CTkLabel(frame_header, text=T("orders_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")

        ctk.CTkButton(frame_header, text=T("orders_new"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000", corner_radius=10,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._nuevo_pedido, width=140, height=36).pack(side="right")

        # ── Barra de filtros ──
        frame_filtros = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=12)
        frame_filtros.pack(fill="x", padx=28, pady=12)

        ctk.CTkLabel(frame_filtros, text=T("orders_search"), text_color=COLOR_SUB,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(10, 4), pady=8)

        self.entry_buscar = ctk.CTkEntry(frame_filtros, placeholder_text=T("orders_search_ph"),
                                         width=200, fg_color="#252525", border_color=COLOR_BORDER,
                                         text_color=COLOR_TEXT, corner_radius=8)
        self.entry_buscar.pack(side="left", pady=8)
        self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)

        ctk.CTkLabel(frame_filtros, text=T("orders_status"), text_color=COLOR_SUB,
                     font=ctk.CTkFont(size=12)).pack(side="left", padx=(12, 4))

        self.combo_estado = ctk.CTkOptionMenu(
            frame_filtros, values=[T("orders_all")] + ESTADOS,
            fg_color="#252525", button_color=COLOR_BORDER,
            button_hover_color=COLOR_HOVER, text_color=COLOR_TEXT,
            dropdown_fg_color=COLOR_CARD, width=140, height=32,
            command=lambda _: self._filtrar()
        )
        self.combo_estado.pack(side="left", pady=8, padx=4)

        # ── Layout principal: tabla + formulario ──
        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        # ── Tabla de pedidos ──
        frame_tabla = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDER)
        frame_tabla.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        cols = [T("orders_col_id"), T("orders_col_date"), T("orders_col_client"),
                T("orders_col_desc"), T("orders_col_sale"), T("orders_col_profit"), T("orders_col_status")]
        # Encabezado de la tabla
        frame_col_header = ctk.CTkFrame(frame_tabla, fg_color="#252525", corner_radius=0)
        frame_col_header.pack(fill="x", padx=0)
        pesos = [1, 2, 3, 4, 2, 2, 2]
        for col, peso in zip(cols, pesos):
            ctk.CTkLabel(frame_col_header, text=col, text_color=COLOR_SUB,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").pack(side="left", padx=8, pady=6, expand=True, fill="x")

        # ── Paginación (se empaqueta antes del scroll para quedar abajo) ──
        frame_pag = ctk.CTkFrame(frame_tabla, fg_color="transparent")
        frame_pag.pack(side="bottom", fill="x", padx=10, pady=(4, 8))

        self.btn_anterior = ctk.CTkButton(
            frame_pag, text=T("orders_prev"), width=100, height=30,
            fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT, corner_radius=8,
            font=ctk.CTkFont(size=11),
            command=lambda: self._cambiar_pagina(-1))
        self.btn_anterior.pack(side="left")

        self.lbl_pagina = ctk.CTkLabel(frame_pag, text="", text_color=COLOR_SUB,
                                       font=ctk.CTkFont(size=11))
        self.lbl_pagina.pack(side="left", expand=True)

        self.btn_siguiente = ctk.CTkButton(
            frame_pag, text=T("orders_next"), width=100, height=30,
            fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT, corner_radius=8,
            font=ctk.CTkFont(size=11),
            command=lambda: self._cambiar_pagina(1))
        self.btn_siguiente.pack(side="right")

        self.frame_tabla_scroll = ctk.CTkScrollableFrame(frame_tabla, fg_color="transparent")
        self.frame_tabla_scroll.pack(fill="both", expand=True)

        # ── Formulario de pedido ──
        self.frame_form = ctk.CTkScrollableFrame(frame_main, fg_color=COLOR_CARD,
                                                  corner_radius=14, border_width=1,
                                                  border_color=COLOR_BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")

        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        """Construye el formulario de entrada de pedidos."""
        # Encabezado del formulario
        frame_form_head = ctk.CTkFrame(parent, fg_color="transparent")
        frame_form_head.pack(fill="x", padx=14, pady=(13, 1))

        ctk.CTkLabel(frame_form_head, text=T("orders_form_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")

        ctk.CTkButton(frame_form_head, text=T("orders_load_catalog"),
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_ACCENT, border_width=1, border_color=COLOR_BORDER,
                      width=140, height=28, font=ctk.CTkFont(size=11),
                      command=self._abrir_modal_catalogo).pack(side="right")

        def lbl(t): ctk.CTkLabel(parent, text=t, text_color=COLOR_SUB,
                                  font=ctk.CTkFont(size=11), anchor="w").pack(
                                      anchor="w", padx=14, pady=(8, 2))
        def ent(ph=""):
            e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color="#252525",
                             border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                             corner_radius=8, height=34)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("orders_date")); self.ent_fecha = ent("YYYY-MM-DD")
        lbl(T("orders_client")); self._cargar_combo_clientes(parent)
        lbl(T("orders_desc")); self.ent_desc = ent(T("orders_desc_ph"))
        lbl(T("orders_filament")); self._cargar_combo_filamentos(parent)
        lbl(T("orders_grams")); self.ent_gramos = ent("0")
        self.ent_gramos.bind("<KeyRelease>", lambda e: self._calcular_costo())
        lbl(T("orders_hours")); self.ent_horas = ent("0")
        self.ent_horas.bind("<KeyRelease>", lambda e: self._calcular_costo())
        lbl(T("orders_material_cost")); self.ent_costo_mat = ent("0.00")
        lbl(T("orders_time_cost")); self.ent_costo_tiempo = ent("0.00")
        lbl(T("orders_shipping")); self.ent_envio = ent("0.00")
        lbl(T("orders_sale_price")); self.ent_venta = ent("0.00")
        self.ent_venta.bind("<KeyRelease>", lambda e: self._verificar_margen())
        lbl(T("orders_delivery")); self.ent_entrega = ent("YYYY-MM-DD")
        lbl(T("orders_state"))
        self.combo_estado_form = ctk.CTkOptionMenu(
            parent, values=ESTADOS,
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34
        )
        self.combo_estado_form.pack(fill="x", padx=14)
        lbl(T("orders_notes")); self.ent_notas = ent(T("orders_notes_ph"))

        # Alerta de margen
        self.lbl_margen_alerta = ctk.CTkLabel(
            parent, text="", text_color=COLOR_RED,
            font=ctk.CTkFont(size=11)
        )
        self.lbl_margen_alerta.pack(anchor="w", padx=14)

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=10)

        # Botones de acción
        ctk.CTkButton(parent, text=T("orders_save"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      height=40, corner_radius=10,
                      command=self._guardar_pedido).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(parent, text=T("orders_delete"),
                      fg_color="#2D0000", hover_color="#3D0000",
                      text_color=COLOR_RED, height=34, corner_radius=10,
                      command=self._eliminar_pedido).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(parent, text=T("orders_invoice"),
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_TEXT, height=34, corner_radius=10,
                      command=self._generar_factura).pack(fill="x", padx=14, pady=(0, 14))

    def _cargar_combo_clientes(self, parent):
        """Carga el dropdown de clientes."""
        self._clientes_data = mapa_por_etiqueta(
            db_manager.obtener_clientes(), lambda c: c["nombre"])
        valores = [T("orders_no_client")] + list(self._clientes_data.keys())
        self.combo_cliente = ctk.CTkOptionMenu(
            parent, values=valores,
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34
        )
        self.combo_cliente.pack(fill="x", padx=14)

    def _cargar_combo_filamentos(self, parent):
        """Carga el dropdown de filamentos."""
        self._filamentos_data = mapa_por_etiqueta(
            db_manager.obtener_filamentos(),
            lambda f: f"{f['nombre']} ({f['material']})")
        valores = [T("orders_no_filament")] + list(self._filamentos_data.keys())
        self.combo_filamento_form = ctk.CTkOptionMenu(
            parent, values=valores,
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34,
            command=lambda _: self._calcular_costo()
        )
        self.combo_filamento_form.pack(fill="x", padx=14)

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
        """Renderiza las filas de la página actual en el scroll frame."""
        for w in self.frame_tabla_scroll.winfo_children():
            w.destroy()

        if not pedidos:
            ctk.CTkLabel(self.frame_tabla_scroll, text=T("orders_no_results"),
                         text_color=COLOR_SUB, font=ctk.CTkFont(size=12),
                         justify="center").pack(pady=40)
            return

        for i, p in enumerate(pedidos):
            row = ctk.CTkFrame(self.frame_tabla_scroll,
                               fg_color="#252525" if i % 2 == 0 else COLOR_CARD,
                               corner_radius=0)
            row.pack(fill="x")
            row.bind("<Button-1>", lambda e, pid=p["id"]: self._seleccionar_pedido(pid))
            datos = [
                str(p["id"]),
                p.get("fecha", ""),
                (p.get("cliente_nombre") or "—")[:18],
                (p.get("descripcion") or "—")[:22],
                f"${p.get('precio_venta', 0):.2f}",
                f"${p.get('ganancia', 0):.2f}",
                p.get("estado", ""),
            ]
            for d in datos:
                lbl = ctk.CTkLabel(row, text=d, text_color=COLOR_TEXT,
                                   font=ctk.CTkFont(size=11), anchor="w")
                lbl.pack(side="left", padx=8, pady=5, expand=True, fill="x")
                lbl.bind("<Button-1>", lambda e, pid=p["id"]: self._seleccionar_pedido(pid))

    # ──────────────── SELECCIÓN Y FORMULARIO ────────────────

    def _seleccionar_pedido(self, pedido_id):
        """Carga un pedido en el formulario para edición."""
        p = db_manager.obtener_pedido_por_id(pedido_id)
        if not p:
            return
        self._pedido_editando = pedido_id
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
                db_manager.agregar_pedido(datos)
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
        """Pre-llena el formulario con datos de la calculadora."""
        self._nuevo_pedido()
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
        modal.configure(fg_color=COLOR_BG)

        modal.update_idletasks()
        x = modal.winfo_screenwidth() // 2 - 200
        y = modal.winfo_screenheight() // 2 - 225
        modal.geometry(f"+{x}+{y}")

        ctk.CTkLabel(modal, text=T("orders_catalog_title"),
                     font=ctk.CTkFont(size=16, weight="bold"), text_color=COLOR_TEXT).pack(pady=16)

        scroll = ctk.CTkScrollableFrame(modal, fg_color="transparent")
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
            card = ctk.CTkFrame(scroll, fg_color=COLOR_CARD, corner_radius=8, cursor="hand2")
            card.pack(fill="x", pady=3)
            card.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))

            f_top = ctk.CTkFrame(card, fg_color="transparent")
            f_top.pack(fill="x", padx=10, pady=(8, 2))
            f_top.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))

            ctk.CTkLabel(f_top, text=p["nombre"], font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_TEXT).pack(side="left")
            ctk.CTkLabel(f_top, text=f"${p['precio_sugerido']:.2f}", font=ctk.CTkFont(size=12, weight="bold"), text_color=COLOR_ACCENT).pack(side="right")

            ctk.CTkLabel(card, text=p.get("descripcion", ""), font=ctk.CTkFont(size=10), text_color=COLOR_SUB).pack(anchor="w", padx=10, pady=(0, 8))

            # Asegurar que el click en los labels también dispare la selección
            for child in card.winfo_children():
                child.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))
                for subchild in child.winfo_children():
                    subchild.bind("<Button-1>", lambda e, prod=p: seleccionar(prod))
