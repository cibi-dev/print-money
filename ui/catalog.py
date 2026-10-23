# ui/catalog.py – Vista de Catálogo de Productos
# Gestión de diseños frecuentes para acelerar la toma de pedidos

import customtkinter as ctk
from tkinter import messagebox
import db_manager
from utils.i18n import T
from utils.labels import mapa_por_etiqueta
from ui import theme as th
from ui import components as ui


class CatalogView(ctk.CTkFrame):
    """Vista de catálogo de productos frecuentes."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._producto_editando = None
        self._productos_cache = []
        self._construir_ui()

    def on_show(self):
        self._cargar_catalogo()

    def _construir_ui(self):
        _, zona_acciones = ui.page_header(self, T("catalog_title"))
        ui.primary_button(zona_acciones, T("catalog_new"),
                          self._nuevo_producto, width=160).pack(side="right")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=14)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        frame_izq = ui.card(frame_main)
        frame_izq.grid(row=0, column=0, padx=(0, th.GAP), sticky="nsew")

        ui.section_title(frame_izq, T("catalog_saved")).pack(
            anchor="w", padx=16, pady=(14, 6))

        self._frame_lista_padre = ctk.CTkFrame(frame_izq, fg_color="transparent")
        self._frame_lista_padre.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self._scroll_frame = ui.scrollable(self._frame_lista_padre)
        self._scroll_frame.pack(fill="both", expand=True)

        self.frame_form = ui.scrollable(frame_main, fg_color=th.CARD,
                                        corner_radius=th.RADIUS_CARD,
                                        border_width=1, border_color=th.BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")
        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        ui.section_title(parent, T("catalog_form_title")).pack(
            anchor="w", padx=14, pady=(14, 4))

        def lbl(t):
            ui.section_label(parent, t).pack(anchor="w", padx=14, pady=(8, 2))

        def ent(ph=""):
            e = ui.entry(parent, ph)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("catalog_name"));  self.ent_nombre = ent(T("catalog_name_ph"))
        lbl(T("catalog_desc")); self.ent_desc   = ent(T("catalog_desc_ph"))

        lbl(T("catalog_filament"))
        self._filamentos_data = mapa_por_etiqueta(
            db_manager.obtener_filamentos(),
            lambda f: f"{f['nombre']} ({f.get('material', 'PLA')})"
        )
        valores = [T("catalog_no_filament")] + list(self._filamentos_data.keys())
        self.combo_filamento = ui.option_menu(parent, valores)
        self.combo_filamento.pack(fill="x", padx=14)

        lbl(T("catalog_grams"));   self.ent_gramos = ent("0")
        lbl(T("catalog_hours")); self.ent_horas  = ent("0")
        lbl(T("catalog_price"));    self.ent_precio = ent("0.00")

        ui.divider(parent).pack(fill="x", padx=14, pady=12)

        ui.primary_button(parent, T("catalog_save"), self._guardar_producto,
                          height=th.H_BTN_LG).pack(fill="x", padx=14, pady=(0, 6))

    def _cargar_catalogo(self):
        try:
            self._filamentos_data = mapa_por_etiqueta(
                db_manager.obtener_filamentos(),
                lambda f: f"{f['nombre']} ({f.get('material', 'PLA')})"
            )
            valores = [T("catalog_no_filament")] + list(self._filamentos_data.keys())
            try:
                self.combo_filamento.configure(values=valores)
            except Exception:
                pass

            for w in list(self._scroll_frame.winfo_children()):
                try:
                    w.destroy()
                except Exception:
                    pass

            self._productos_cache = db_manager.obtener_catalogo()

            if not self._productos_cache:
                ui.empty_state(self._scroll_frame, icono="📖",
                               titulo=T("catalog_saved"),
                               hint=T("catalog_empty"),
                               cta_texto=T("catalog_new"),
                               cta_cmd=self._nuevo_producto)
                return

            for p in self._productos_cache:
                self._crear_card(p)
        except Exception as e:
            messagebox.showerror(T("catalog_load_error"), str(e),
                                 parent=self.winfo_toplevel())

    def _crear_card(self, p):
        pid = p["id"]

        card = ui.card(self._scroll_frame, fg_color=th.SURFACE)
        card.pack(fill="x", pady=5, padx=4)

        row_top = ctk.CTkFrame(card, fg_color="transparent")
        row_top.pack(fill="x", padx=14, pady=(12, 0))

        ctk.CTkLabel(row_top, text=p["nombre"],
                     font=th.fuente(14, True),
                     text_color=th.TEXT, anchor="w").pack(side="left")

        precio_frame = ctk.CTkFrame(row_top, fg_color=th.ACCENT_DIM,
                                    corner_radius=th.RADIUS_SM)
        precio_frame.pack(side="right")
        ctk.CTkLabel(precio_frame, text=f"${p.get('precio_sugerido', 0):.2f}",
                     font=th.fuente(th.FONT_BODY, True),
                     text_color=th.ACCENT).pack(padx=8, pady=2)

        desc = p.get("descripcion", "") or ""
        if desc:
            ctk.CTkLabel(card, text=desc,
                         font=th.fuente(th.FONT_BODY),
                         text_color=th.SUB, anchor="w",
                         wraplength=380).pack(fill="x", padx=14, pady=(4, 0))

        detalles = []
        if p.get("filamento_nombre"):
            detalles.append(f"🎨 {p['filamento_nombre']}")
        if p.get("gramos_estimados", 0) > 0:
            detalles.append(f"⚖️ {p['gramos_estimados']}g")
        if p.get("horas_estimadas", 0) > 0:
            detalles.append(f"⏱️ {p['horas_estimadas']}h")

        if detalles:
            ctk.CTkLabel(card, text="   ".join(detalles),
                         font=th.fuente(th.FONT_LABEL),
                         text_color=th.SUB_DIM, anchor="w").pack(fill="x", padx=14, pady=(4, 0))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent", height=1)

        btn_editar = ui.secondary_button(
            btn_frame, T("catalog_edit"),
            lambda: self._seleccionar_producto(pid),
            width=80, height=28, font=th.fuente(11))
        btn_editar.pack(side="left", padx=(0, 6))

        btn_eliminar = ui.danger_button(
            btn_frame, T("catalog_del"),
            lambda: self._eliminar_producto_directo(pid),
            width=90, height=28, font=th.fuente(11))
        btn_eliminar.pack(side="left")

        card._hover_visible = False
        card._leave_after_id = None

        def _mostrar_botones():
            if not card._hover_visible:
                card._hover_visible = True
                btn_frame.pack(fill="x", padx=14, pady=(6, 12))
                card.configure(fg_color=th.SURFACE_HOVER, border_color=th.ACCENT)

        def _ocultar_botones():
            if card._hover_visible:
                card._hover_visible = False
                btn_frame.pack_forget()
                card.configure(fg_color=th.SURFACE, border_color=th.BORDER)

        def on_enter(e):
            if card._leave_after_id is not None:
                card.after_cancel(card._leave_after_id)
                card._leave_after_id = None
            _mostrar_botones()

        def on_leave(e):
            if card._leave_after_id is not None:
                card.after_cancel(card._leave_after_id)
            card._leave_after_id = card.after(100, _ocultar_botones)

        def bind_recursivo(widget):
            widget.bind("<Enter>", on_enter)
            widget.bind("<Leave>", on_leave)
            for child in widget.winfo_children():
                bind_recursivo(child)

        bind_recursivo(card)

    def _seleccionar_producto(self, pid):
        productos = [p for p in self._productos_cache if p["id"] == pid]
        if not productos:
            return
        p = productos[0]
        self._producto_editando = pid

        def set_e(e, val):
            e.delete(0, "end")
            e.insert(0, str(val or ""))

        set_e(self.ent_nombre, p["nombre"])
        set_e(self.ent_desc,   p.get("descripcion", ""))
        set_e(self.ent_gramos, p.get("gramos_estimados", 0))
        set_e(self.ent_horas,  p.get("horas_estimadas", 0))
        set_e(self.ent_precio, p.get("precio_sugerido", 0))

        # Buscar por ID: con homónimos la etiqueta puede llevar el sufijo "(2)"
        # y la comparación por texto no encontraría el filamento correcto.
        filamento_id = p.get("filamento_base_id")
        if filamento_id:
            for etiqueta, info in self._filamentos_data.items():
                if info["id"] == filamento_id:
                    self.combo_filamento.set(etiqueta)
                    return
        self.combo_filamento.set(T("catalog_no_filament"))

    def _nuevo_producto(self):
        self._producto_editando = None
        for e in [self.ent_nombre, self.ent_desc, self.ent_gramos,
                  self.ent_horas, self.ent_precio]:
            e.delete(0, "end")
        self.combo_filamento.set(T("catalog_no_filament"))

    def _guardar_producto(self):
        nombre = self.ent_nombre.get().strip()
        if not nombre:
            messagebox.showwarning(T("warning"), T("catalog_name_req"),
                                   parent=self.winfo_toplevel())
            return

        try:
            gramos = float(self.ent_gramos.get() or 0)
            horas  = float(self.ent_horas.get()  or 0)
            precio = float(self.ent_precio.get()  or 0)
        except ValueError:
            messagebox.showerror(T("error"), T("catalog_invalid_nums"),
                                 parent=self.winfo_toplevel())
            return

        try:
            fil_sel = self.combo_filamento.get()
            fil_id  = None
            if fil_sel in self._filamentos_data:
                fil_id = self._filamentos_data[fil_sel]["id"]

            args = (nombre, self.ent_desc.get(), fil_id, gramos, horas, precio)

            if self._producto_editando:
                db_manager.actualizar_producto_catalogo(self._producto_editando, *args)
            else:
                db_manager.agregar_producto_catalogo(*args)

            self._nuevo_producto()
            self._cargar_catalogo()
        except Exception as e:
            messagebox.showerror(T("catalog_save_error"), str(e),
                                 parent=self.winfo_toplevel())

    def _eliminar_producto_directo(self, pid):
        if messagebox.askyesno(T("confirm"), T("catalog_confirm_del"),
                                parent=self.winfo_toplevel()):
            db_manager.eliminar_producto_catalogo(pid)
            self._nuevo_producto()
            self._cargar_catalogo()
