# ui/expenses.py – Vista de Gastos
# Gestión de gastos con categorías, gastos recurrentes y tabla visual

import customtkinter as ctk
from tkinter import messagebox
from datetime import date
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


class ExpensesView(ctk.CTkFrame):
    """Vista de gestión de gastos con formulario y tabla."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._gasto_editando = None
        self._construir_ui()

    def on_show(self):
        """Refresca datos al volver a esta vista."""
        self._cargar_datos()

    def _construir_ui(self):
        """Construye el layout de la vista de gastos."""
        # Encabezado
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("expenses_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")

        ctk.CTkButton(frame_header, text=T("expenses_new"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000", corner_radius=10,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._nuevo_gasto, width=130, height=36).pack(side="right")

        # Layout principal
        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=28, pady=14)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        # Tabla
        frame_tabla = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                   border_width=1, border_color=COLOR_BORDER)
        frame_tabla.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        cols = [T("expenses_col_id"), T("expenses_col_date"), T("expenses_col_cat"),
                T("expenses_col_desc"), T("expenses_col_amount"), T("expenses_col_recur")]
        frame_col_h = ctk.CTkFrame(frame_tabla, fg_color="#252525", corner_radius=0)
        frame_col_h.pack(fill="x")
        for col in cols:
            ctk.CTkLabel(frame_col_h, text=col, text_color=COLOR_SUB,
                         font=ctk.CTkFont(size=11, weight="bold"),
                         anchor="w").pack(side="left", padx=8, pady=6, expand=True, fill="x")

        self.frame_scroll = ctk.CTkScrollableFrame(frame_tabla, fg_color="transparent")
        self.frame_scroll.pack(fill="both", expand=True)

        # Formulario
        self.frame_form = ctk.CTkScrollableFrame(frame_main, fg_color=COLOR_CARD,
                                                  corner_radius=14, border_width=1,
                                                  border_color=COLOR_BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")
        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        """Construye el formulario de gastos."""
        ctk.CTkLabel(parent, text=T("expenses_form_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=16, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=14, pady=(14, 4))

        def lbl(t): ctk.CTkLabel(parent, text=t, text_color=COLOR_SUB,
                                  font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(8, 2))
        def ent(ph=""):
            e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color="#252525",
                             border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                             corner_radius=8, height=34)
            e.pack(fill="x", padx=14)
            return e

        lbl(T("expenses_date")); self.ent_fecha = ent(str(date.today()))
        self.ent_fecha.insert(0, str(date.today()))

        lbl(T("expenses_category"))
        self._categorias_data = {c["nombre"]: c for c in db_manager.obtener_categorias_gastos()}
        self.combo_cat = ctk.CTkOptionMenu(
            parent, values=list(self._categorias_data.keys()),
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34
        )
        self.combo_cat.pack(fill="x", padx=14)

        lbl(T("expenses_desc")); self.ent_desc = ent(T("expenses_desc_ph"))
        lbl(T("expenses_amount")); self.ent_monto = ent("0.00")
        lbl(T("expenses_notes")); self.ent_notas = ent(T("expenses_notes_ph"))

        # ── Recurrente ──
        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=10)
        self.var_recurrente = ctk.BooleanVar(value=False)
        ctk.CTkCheckBox(parent, text=T("expenses_recurring"),
                        variable=self.var_recurrente, fg_color=COLOR_ACCENT,
                        hover_color="#00CC7A", checkmark_color="#000000",
                        text_color=COLOR_SUB,
                        command=self._toggle_recurrente).pack(anchor="w", padx=14)

        ctk.CTkLabel(parent, text=T("expenses_frequency"), text_color=COLOR_SUB,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(8, 2))
        self.combo_freq = ctk.CTkOptionMenu(
            parent, values=[T("freq_monthly"), T("freq_weekly"), T("freq_yearly")],
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34, state="disabled"
        )
        self.combo_freq.pack(fill="x", padx=14)

        # ── Nueva categoría rápida ──
        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=10)
        ctk.CTkLabel(parent, text=T("expenses_new_cat"), text_color=COLOR_SUB,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=14, pady=(0, 2))
        frame_cat_add = ctk.CTkFrame(parent, fg_color="transparent")
        frame_cat_add.pack(fill="x", padx=14)
        self.ent_nueva_cat = ctk.CTkEntry(frame_cat_add, placeholder_text=T("expenses_cat_ph"),
                                          fg_color="#252525", border_color=COLOR_BORDER,
                                          text_color=COLOR_TEXT, corner_radius=8, height=32)
        self.ent_nueva_cat.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(frame_cat_add, text="+", width=36, height=32,
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_ACCENT,
                      command=self._agregar_categoria).pack(side="right")

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=14, pady=10)

        ctk.CTkButton(parent, text=T("expenses_save"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000",
                      font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                      height=40, corner_radius=10,
                      command=self._guardar_gasto).pack(fill="x", padx=14, pady=(0, 6))

        ctk.CTkButton(parent, text=T("expenses_delete"),
                      fg_color="#2D0000", hover_color="#3D0000",
                      text_color=COLOR_RED, height=34, corner_radius=10,
                      command=self._eliminar_gasto).pack(fill="x", padx=14, pady=(0, 14))

    def _toggle_recurrente(self):
        if self.var_recurrente.get():
            self.combo_freq.configure(state="normal")
        else:
            self.combo_freq.configure(state="disabled")

    def _agregar_categoria(self):
        nombre = self.ent_nueva_cat.get().strip()
        if nombre:
            db_manager.agregar_categoria_gasto(nombre)
            self._cargar_datos()
            self.ent_nueva_cat.delete(0, "end")

    def _cargar_datos(self):
        self._categorias_data = {c["nombre"]: c for c in db_manager.obtener_categorias_gastos()}
        self.combo_cat.configure(values=list(self._categorias_data.keys()))

        for w in self.frame_scroll.winfo_children():
            w.destroy()
        gastos = db_manager.obtener_gastos()
        self._todos_gastos = gastos

        for i, g in enumerate(gastos):
            row = ctk.CTkFrame(self.frame_scroll,
                               fg_color="#252525" if i % 2 == 0 else COLOR_CARD,
                               corner_radius=0)
            row.pack(fill="x")
            row.bind("<Button-1>", lambda e, gid=g["id"]: self._seleccionar_gasto(gid))
            for txt in [str(g["id"]), g.get("fecha",""), g.get("categoria_nombre",""),
                        (g.get("descripcion") or "")[:24],
                        f"${g.get('monto',0):.2f}",
                        "✓" if g.get("recurrente") else ""]:
                lbl = ctk.CTkLabel(row, text=txt, text_color=COLOR_TEXT,
                                   font=ctk.CTkFont(size=11), anchor="w")
                lbl.pack(side="left", padx=8, pady=5, expand=True, fill="x")
                lbl.bind("<Button-1>", lambda e, gid=g["id"]: self._seleccionar_gasto(gid))

    def _seleccionar_gasto(self, gasto_id):
        gastos = [g for g in self._todos_gastos if g["id"] == gasto_id]
        if not gastos:
            return
        g = gastos[0]
        self._gasto_editando = gasto_id

        self.ent_fecha.delete(0, "end"); self.ent_fecha.insert(0, g.get("fecha",""))
        cat = g.get("categoria_nombre","")
        if cat in self._categorias_data:
            self.combo_cat.set(cat)
        self.ent_desc.delete(0, "end"); self.ent_desc.insert(0, g.get("descripcion",""))
        self.ent_monto.delete(0, "end"); self.ent_monto.insert(0, str(g.get("monto",0)))
        self.ent_notas.delete(0, "end"); self.ent_notas.insert(0, g.get("notas",""))
        self.var_recurrente.set(bool(g.get("recurrente")))
        self._toggle_recurrente()

    def _nuevo_gasto(self):
        self._gasto_editando = None
        for e in [self.ent_fecha, self.ent_desc, self.ent_monto, self.ent_notas]:
            e.delete(0, "end")
        self.ent_fecha.insert(0, str(date.today()))
        self.var_recurrente.set(False)
        self._toggle_recurrente()

    def _guardar_gasto(self):
        cat_nombre = self.combo_cat.get()
        cat = self._categorias_data.get(cat_nombre)
        try:
            monto = float(self.ent_monto.get() or 0)
        except ValueError:
            messagebox.showerror(T("error"), T("expenses_invalid_amt"))
            return

        db_manager.agregar_gasto(
            fecha=self.ent_fecha.get() or str(date.today()),
            categoria_id=cat["id"] if cat else None,
            descripcion=self.ent_desc.get(),
            monto=monto,
            recurrente=1 if self.var_recurrente.get() else 0,
            frecuencia=self.combo_freq.get(),
            notas=self.ent_notas.get()
        )
        self._nuevo_gasto()
        self._cargar_datos()

    def _eliminar_gasto(self):
        if not self._gasto_editando:
            messagebox.showwarning(T("warning"), T("expenses_select"))
            return
        if messagebox.askyesno(T("confirm"), T("expenses_confirm_del", id=self._gasto_editando)):
            db_manager.eliminar_gasto(self._gasto_editando)
            self._nuevo_gasto()
            self._cargar_datos()
