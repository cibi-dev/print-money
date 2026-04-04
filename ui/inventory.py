# ui/inventory.py – Vista de Inventario de Filamentos
# Gestión de stock de filamentos con alertas visuales cuando baja del umbral

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
COLOR_YELLOW = "#FFD166"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"

MATERIALES = ["PLA", "PETG", "ABS", "TPU", "ASA", "Nylon", "Resina", "Otro"]


class InventoryView(ctk.CTkFrame):
    """Vista de inventario con cards de filamento y formulario lateral."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._filamento_editando = None
        self._construir_ui()

    def on_show(self):
        self._cargar_filamentos()

    def _construir_ui(self):
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("inv_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkButton(frame_header, text=T("inv_new"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000", corner_radius=10,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._nuevo_filamento, width=160, height=36).pack(side="right")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=28, pady=14)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        frame_izq = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                  border_width=1, border_color=COLOR_BORDER)
        frame_izq.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(frame_izq, text=T("inv_stock"),
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(14, 6))

        self.frame_cards = ctk.CTkScrollableFrame(frame_izq, fg_color="transparent")
        self.frame_cards.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self.frame_form = ctk.CTkScrollableFrame(frame_main, fg_color=COLOR_CARD,
                                                  corner_radius=14, border_width=1,
                                                  border_color=COLOR_BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")
        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        ctk.CTkLabel(parent, text=T("inv_form_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=15, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(14, 4))

        def lbl(t): ctk.CTkLabel(parent, text=t, text_color=COLOR_SUB,
                                  font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(8, 2))
        def ent(ph=""):
            e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color="#252525",
                             border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                             corner_radius=8, height=34)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("inv_name")); self.ent_nombre = ent(T("inv_name_ph"))
        lbl(T("inv_material"))
        self.combo_material = ctk.CTkOptionMenu(
            parent, values=MATERIALES,
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34)
        self.combo_material.pack(fill="x", padx=14)
        lbl(T("inv_color")); self.ent_color = ent(T("inv_color_ph"))
        lbl(T("inv_grams")); self.ent_gramos = ent("1000")
        lbl(T("inv_price_kg")); self.ent_precio = ent("20.00")
        lbl(T("inv_threshold")); self.ent_umbral = ent("100")
        lbl(T("inv_supplier")); self.ent_proveedor = ent(T("inv_supplier_ph"))
        lbl(T("inv_notes")); self.ent_notas = ent(T("inv_notes_ph"))

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=12)

        ctk.CTkButton(parent, text=T("inv_save"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      height=40, corner_radius=10,
                      command=self._guardar_filamento).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(parent, text=T("inv_delete"),
                      fg_color="#2D0000", hover_color="#3D0000",
                      text_color=COLOR_RED, height=34, corner_radius=10,
                      command=self._eliminar_filamento).pack(fill="x", padx=14, pady=(0, 14))

    def _cargar_filamentos(self):
        for w in self.frame_cards.winfo_children():
            w.destroy()
        filamentos = db_manager.obtener_filamentos()

        if not filamentos:
            ctk.CTkLabel(self.frame_cards, text=T("inv_empty"),
                         text_color=COLOR_SUB, font=ctk.CTkFont(size=13),
                         justify="center").pack(pady=40)
            return

        for f in filamentos:
            self._crear_card_filamento(f)

    def _crear_card_filamento(self, f):
        bajo_umbral = f["gramos_restantes"] < f["umbral_bajo"]
        borde = COLOR_RED if bajo_umbral else COLOR_BORDER
        bg = "#2D0000" if bajo_umbral else "#252525"

        card = ctk.CTkFrame(self.frame_cards, fg_color=bg, corner_radius=12,
                            border_width=1, border_color=borde)
        card.pack(fill="x", pady=4, padx=2)
        card.bind("<Button-1>", lambda e, fid=f["id"]: self._seleccionar_filamento(fid))

        frame_row = ctk.CTkFrame(card, fg_color="transparent")
        frame_row.pack(fill="x", padx=12, pady=(10, 0))
        frame_row.bind("<Button-1>", lambda e, fid=f["id"]: self._seleccionar_filamento(fid))

        ctk.CTkLabel(frame_row,
                     text=f"{f['nombre']}  [{f['material']}]",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_RED if bajo_umbral else COLOR_TEXT,
                     anchor="w").pack(side="left")

        ctk.CTkLabel(frame_row,
                     text=f"{f['gramos_restantes']:.0f} g",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_RED if bajo_umbral else COLOR_ACCENT,
                     anchor="e").pack(side="right")

        max_gramos = max(f["gramos_restantes"], f["umbral_bajo"], 1000)
        progreso = max(0, min(1, f["gramos_restantes"] / max_gramos))
        barra = ctk.CTkProgressBar(card, height=6, corner_radius=4,
                                   progress_color=COLOR_RED if bajo_umbral else COLOR_ACCENT,
                                   fg_color=COLOR_BORDER)
        barra.set(progreso)
        barra.pack(fill="x", padx=12, pady=(6, 4))

        if bajo_umbral:
            info = ctk.CTkLabel(card, text=T("inv_low_stock", threshold=f['umbral_bajo'], price=f['precio_por_kg']),
                                font=ctk.CTkFont(size=10), text_color=COLOR_RED)
        else:
            info = ctk.CTkLabel(card, text=f"Color: {f.get('color','—')}  ·  ${f['precio_por_kg']}/kg  ·  {T('inv_threshold')}: {f['umbral_bajo']}g",
                                font=ctk.CTkFont(size=10), text_color=COLOR_SUB)
        info.pack(anchor="w", padx=12, pady=(0, 10))

    def _seleccionar_filamento(self, fid):
        filamento = next((f for f in db_manager.obtener_filamentos() if f["id"] == fid), None)
        if not filamento:
            return
        self._filamento_editando = fid
        f = filamento

        def set_e(e, val):
            e.delete(0, "end"); e.insert(0, str(val or ""))

        set_e(self.ent_nombre, f["nombre"])
        self.combo_material.set(f.get("material", MATERIALES[0]))
        set_e(self.ent_color, f.get("color", ""))
        set_e(self.ent_gramos, f["gramos_restantes"])
        set_e(self.ent_precio, f["precio_por_kg"])
        set_e(self.ent_umbral, f["umbral_bajo"])
        set_e(self.ent_proveedor, f.get("proveedor", ""))
        set_e(self.ent_notas, f.get("notas", ""))

    def _nuevo_filamento(self):
        self._filamento_editando = None
        for e in [self.ent_nombre, self.ent_color, self.ent_gramos,
                  self.ent_precio, self.ent_umbral, self.ent_proveedor, self.ent_notas]:
            e.delete(0, "end")

    def _guardar_filamento(self):
        try:
            args = dict(
                nombre=self.ent_nombre.get(),
                material=self.combo_material.get(),
                color=self.ent_color.get(),
                gramos=float(self.ent_gramos.get() or 0),
                precio_kg=float(self.ent_precio.get() or 0),
                umbral=float(self.ent_umbral.get() or 100),
                proveedor=self.ent_proveedor.get(),
                notas=self.ent_notas.get()
            )
        except ValueError:
            messagebox.showerror(T("error"), T("inv_invalid_nums"))
            return

        if not args["nombre"]:
            messagebox.showwarning(T("warning"), T("inv_name_required"))
            return

        if self._filamento_editando:
            db_manager.actualizar_filamento(self._filamento_editando, **args)
        else:
            db_manager.agregar_filamento(**args)

        self._nuevo_filamento()
        self._cargar_filamentos()

    def _eliminar_filamento(self):
        if not self._filamento_editando:
            messagebox.showwarning(T("warning"), T("inv_select"))
            return
        if messagebox.askyesno(T("confirm"), T("inv_confirm_del", id=self._filamento_editando)):
            db_manager.eliminar_filamento(self._filamento_editando)
            self._nuevo_filamento()
            self._cargar_filamentos()
