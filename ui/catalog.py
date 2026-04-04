# ui/catalog.py – Vista de Catálogo de Productos
# Gestión de diseños frecuentes para acelerar la toma de pedidos

import customtkinter as ctk
from tkinter import messagebox
import db_manager
from utils.i18n import T

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_RED    = "#FF4C4C"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"

class CatalogView(ctk.CTkFrame):
    """Vista de catálogo de productos frecuentes."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._producto_editando = None
        self._productos_cache = []
        self._construir_ui()

    def on_show(self):
        self._cargar_catalogo()

    def _construir_ui(self):
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("catalog_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkButton(frame_header, text=T("catalog_new"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000", corner_radius=10,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._nuevo_producto, width=160, height=36).pack(side="right")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=28, pady=14)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        frame_izq = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                 border_width=1, border_color=COLOR_BORDER)
        frame_izq.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(frame_izq, text=T("catalog_saved"),
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(14, 6))

        self._frame_lista_padre = ctk.CTkFrame(frame_izq, fg_color="transparent")
        self._frame_lista_padre.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self._scroll_frame = ctk.CTkScrollableFrame(self._frame_lista_padre,
                                                     fg_color="transparent")
        self._scroll_frame.pack(fill="both", expand=True)

        self.frame_form = ctk.CTkScrollableFrame(frame_main, fg_color=COLOR_CARD,
                                                 corner_radius=14, border_width=1,
                                                 border_color=COLOR_BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")
        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        ctk.CTkLabel(parent, text=T("catalog_form_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(14, 4))

        def lbl(t):
            ctk.CTkLabel(parent, text=t, text_color=COLOR_SUB,
                         font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(8, 2))

        def ent(ph=""):
            e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color="#252525",
                             border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                             corner_radius=8, height=34)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("catalog_name"));  self.ent_nombre = ent(T("catalog_name_ph"))
        lbl(T("catalog_desc")); self.ent_desc   = ent(T("catalog_desc_ph"))

        lbl(T("catalog_filament"))
        self._filamentos_data = {
            f"{f['nombre']} ({f.get('material', 'PLA')})": f
            for f in db_manager.obtener_filamentos()
        }
        valores = [T("catalog_no_filament")] + list(self._filamentos_data.keys())
        self.combo_filamento = ctk.CTkOptionMenu(
            parent, values=valores,
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34)
        self.combo_filamento.pack(fill="x", padx=14)

        lbl(T("catalog_grams"));   self.ent_gramos = ent("0")
        lbl(T("catalog_hours")); self.ent_horas  = ent("0")
        lbl(T("catalog_price"));    self.ent_precio = ent("0.00")

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=12)

        ctk.CTkButton(parent, text=T("catalog_save"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      height=40, corner_radius=10,
                      command=self._guardar_producto).pack(fill="x", padx=14, pady=(0, 6))

    def _cargar_catalogo(self):
        try:
            self._filamentos_data = {
                f"{f['nombre']} ({f.get('material', 'PLA')})": f
                for f in db_manager.obtener_filamentos()
            }
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
                ctk.CTkLabel(self._scroll_frame,
                             text=T("catalog_empty"),
                             text_color=COLOR_SUB, font=ctk.CTkFont(size=13),
                             justify="center").pack(pady=40)
                return

            for p in self._productos_cache:
                self._crear_card(p)
        except Exception as e:
            messagebox.showerror(T("catalog_load_error"), str(e),
                                 parent=self.winfo_toplevel())

    def _crear_card(self, p):
        pid = p["id"]

        card = ctk.CTkFrame(self._scroll_frame, fg_color="#252525",
                            corner_radius=12, border_width=1,
                            border_color=COLOR_BORDER)
        card.pack(fill="x", pady=5, padx=4)

        row_top = ctk.CTkFrame(card, fg_color="transparent")
        row_top.pack(fill="x", padx=14, pady=(12, 0))

        ctk.CTkLabel(row_top, text=p["nombre"],
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color=COLOR_TEXT, anchor="w").pack(side="left")

        precio_frame = ctk.CTkFrame(row_top, fg_color="#003D26", corner_radius=6)
        precio_frame.pack(side="right")
        ctk.CTkLabel(precio_frame, text=f"${p.get('precio_sugerido', 0):.2f}",
                     font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                     text_color=COLOR_ACCENT).pack(padx=8, pady=2)

        desc = p.get("descripcion", "") or ""
        if desc:
            ctk.CTkLabel(card, text=desc,
                         font=ctk.CTkFont(size=12),
                         text_color=COLOR_SUB, anchor="w",
                         wraplength=350).pack(fill="x", padx=14, pady=(4, 0))

        detalles = []
        if p.get("filamento_nombre"):
            detalles.append(f"🎨 {p['filamento_nombre']}")
        if p.get("gramos_estimados", 0) > 0:
            detalles.append(f"⚖️ {p['gramos_estimados']}g")
        if p.get("horas_estimadas", 0) > 0:
            detalles.append(f"⏱️ {p['horas_estimadas']}h")

        if detalles:
            ctk.CTkLabel(card, text="   ".join(detalles),
                         font=ctk.CTkFont(size=11),
                         text_color="#666666", anchor="w").pack(fill="x", padx=14, pady=(4, 0))

        btn_frame = ctk.CTkFrame(card, fg_color="transparent")
        btn_frame.pack(fill="x", padx=14, pady=(6, 12))

        btn_editar = ctk.CTkButton(
            btn_frame, text=T("catalog_edit"), width=80, height=28,
            fg_color=COLOR_BORDER, hover_color="#3A3A3A",
            text_color=COLOR_TEXT, corner_radius=6,
            font=ctk.CTkFont(size=11),
            command=lambda: self._seleccionar_producto(pid))

        btn_eliminar = ctk.CTkButton(
            btn_frame, text=T("catalog_del"), width=90, height=28,
            fg_color="#2D0000", hover_color="#3D0000",
            text_color=COLOR_RED, corner_radius=6,
            font=ctk.CTkFont(size=11),
            command=lambda: self._eliminar_producto_directo(pid))

        card._hover_visible = False
        card._leave_after_id = None

        def _mostrar_botones():
            if not card._hover_visible:
                card._hover_visible = True
                btn_editar.pack(side="left", padx=(0, 6))
                btn_eliminar.pack(side="left")
                card.configure(fg_color="#2E2E2E", border_color=COLOR_ACCENT)

        def _ocultar_botones():
            if card._hover_visible:
                card._hover_visible = False
                btn_editar.pack_forget()
                btn_eliminar.pack_forget()
                card.configure(fg_color="#252525", border_color=COLOR_BORDER)

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

        if p.get("filamento_nombre"):
            f_key = f"{p['filamento_nombre']} ({p.get('filamento_material', 'PLA')})"
            if f_key in self._filamentos_data:
                self.combo_filamento.set(f_key)
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
