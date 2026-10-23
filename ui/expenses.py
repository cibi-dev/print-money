# ui/expenses.py – Vista de Gastos
# Gestión de gastos con categorías, gastos recurrentes y tabla visual

import customtkinter as ctk
from tkinter import messagebox
from datetime import date
import db_manager
from utils.i18n import T
from ui import theme as th
from ui import components as ui

# La frecuencia se guarda SIEMPRE en un código canónico ('mensual',
# 'semanal', 'anual') y se traduce solo al mostrarlo. Antes se guardaba el
# texto ya traducido, así que cambiar de idioma reescribía el contenido de
# la base de datos.
_FRECUENCIA_CLAVES = {
    "mensual": "freq_monthly",
    "semanal": "freq_weekly",
    "anual": "freq_yearly",
}
# Valores que могут quedar en bases de datos creadas con la versión anterior
_FRECUENCIA_ANTIGUAS = {
    "monthly": "freq_monthly",
    "weekly": "freq_weekly",
    "yearly": "freq_yearly",
}


def _frecuencia_a_visible(valor):
    """Convierte el valor guardado en la BD al texto que se muestra."""
    clave = _FRECUENCIA_CLAVES.get(valor) or _FRECUENCIA_ANTIGUAS.get(valor)
    return T(clave or "freq_monthly")


def _frecuencia_a_canonica(texto_visible):
    """Convierte el texto visible del desplegable al valor que se guarda."""
    for canonico, clave in _FRECUENCIA_CLAVES.items():
        if texto_visible == T(clave):
            return canonico
    return "mensual"


class ExpensesView(ctk.CTkFrame):
    """Vista de gestión de gastos con formulario y tabla."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._gasto_editando = None
        self._todos_gastos = []
        self._construir_ui()

    def on_show(self):
        """Refresca datos al volver a esta vista."""
        self._cargar_datos()

    def _construir_ui(self):
        """Construye el layout de la vista de gastos."""
        # Encabezado
        _, acciones = ui.page_header(self, T("expenses_title"))

        ui.primary_button(acciones, T("expenses_new"), self._nuevo_gasto,
                          width=150).pack(side="right")

        # Layout principal
        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=14)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        # Tabla
        frame_tabla = ctk.CTkFrame(frame_main, fg_color="transparent")
        frame_tabla.grid(row=0, column=0, padx=(0, th.GAP), sticky="nsew")

        cols = [T("expenses_col_id"), T("expenses_col_date"), T("expenses_col_cat"),
                T("expenses_col_desc"), T("expenses_col_amount"), T("expenses_col_recur")]
        self.tabla = ui.DataTable(frame_tabla, columnas=cols, pesos=[1, 2, 2, 4, 2, 2],
                                  alinear=["w", "w", "w", "w", "e", "w"],
                                  on_select=lambda g: self._seleccionar_gasto(g["id"]))
        self.tabla.pack(fill="both", expand=True)

        # Formulario
        self.frame_form = ui.scrollable(frame_main, fg_color=th.CARD,
                                        corner_radius=th.RADIUS_CARD,
                                        border_width=1, border_color=th.BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")
        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        """Construye el formulario de gastos."""
        ui.section_title(parent, T("expenses_form_title")).pack(
            anchor="w", padx=14, pady=(14, 8))

        cont = ctk.CTkFrame(parent, fg_color="transparent")
        cont.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        ui.section_label(cont, T("expenses_date")).pack(anchor="w", pady=(0, 2))
        self.ent_fecha = ui.entry(cont, "YYYY-MM-DD")
        self.ent_fecha.pack(fill="x", pady=(0, th.GAP))
        self.ent_fecha.insert(0, str(date.today()))

        ui.section_label(cont, T("expenses_category")).pack(anchor="w", pady=(0, 2))
        self._categorias_data = {c["nombre"]: c for c in db_manager.obtener_categorias_gastos()}
        self.combo_cat = ui.option_menu(cont, values=list(self._categorias_data.keys()))
        self.combo_cat.pack(fill="x", pady=(0, th.GAP))

        ui.section_label(cont, T("expenses_desc")).pack(anchor="w", pady=(0, 2))
        self.ent_desc = ui.entry(cont, T("expenses_desc_ph"))
        self.ent_desc.pack(fill="x", pady=(0, th.GAP))

        ui.section_label(cont, T("expenses_amount")).pack(anchor="w", pady=(0, 2))
        self.ent_monto = ui.entry(cont, "0.00")
        self.ent_monto.pack(fill="x", pady=(0, th.GAP))

        ui.section_label(cont, T("expenses_notes")).pack(anchor="w", pady=(0, 2))
        self.ent_notas = ui.entry(cont, T("expenses_notes_ph"))
        self.ent_notas.pack(fill="x", pady=(0, th.GAP))

        # ── Recurrente ──
        ui.divider(cont).pack(fill="x", pady=10)
        self.var_recurrente = ctk.BooleanVar(value=False)
        ui.checkbox(cont, T("expenses_recurring"), self.var_recurrente,
                    command=self._toggle_recurrente).pack(anchor="w")

        ui.section_label(cont, T("expenses_frequency")).pack(anchor="w", pady=(8, 2))
        self.combo_freq = ui.option_menu(
            cont, values=[T("freq_monthly"), T("freq_weekly"), T("freq_yearly")],
            state="disabled"
        )
        self.combo_freq.pack(fill="x")

        # ── Nueva categoría rápida ──
        ui.divider(cont).pack(fill="x", pady=10)
        ui.section_label(cont, T("expenses_new_cat")).pack(anchor="w", pady=(0, 2))
        frame_cat_add = ctk.CTkFrame(cont, fg_color="transparent")
        frame_cat_add.pack(fill="x")
        self.ent_nueva_cat = ui.entry(frame_cat_add, T("expenses_cat_ph"))
        self.ent_nueva_cat.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ui.icon_button(frame_cat_add, "+", self._agregar_categoria,
                       width=36).pack(side="right")

        ui.divider(cont).pack(fill="x", pady=10)

        ui.primary_button(cont, T("expenses_save"), self._guardar_gasto).pack(
            fill="x", pady=(0, 6))

        ui.danger_button(cont, T("expenses_delete"), self._eliminar_gasto).pack(fill="x")

    def _toggle_recurrente(self):
        if self.var_recurrente.get():
            self.combo_freq.configure(state="normal")
        else:
            self.combo_freq.configure(state="disabled")

    def _agregar_categoria(self):
        nombre = self.ent_nueva_cat.get().strip()
        if nombre:
            try:
                db_manager.agregar_categoria_gasto(nombre)
                self._cargar_datos()
                self.ent_nueva_cat.delete(0, "end")
            except Exception as e:
                messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())

    def _cargar_datos(self):
        self._categorias_data = {c["nombre"]: c for c in db_manager.obtener_categorias_gastos()}
        # Conservar la categoría seleccionada si sigue existiendo
        seleccion = self.combo_cat.get()
        valores = list(self._categorias_data.keys())
        self.combo_cat.configure(values=valores)
        if seleccion in valores:
            self.combo_cat.set(seleccion)

        gastos = db_manager.obtener_gastos()
        self._todos_gastos = gastos

        if not gastos:
            self.tabla.mostrar_vacio(T("expenses_empty_title"), icono="💸",
                                     hint=T("expenses_empty_hint"))
            return

        firma = tuple((g["id"], g.get("fecha"), g.get("monto"), g.get("recurrente"),
                       g.get("categoria_nombre"), g.get("descripcion")) for g in gastos)
        celdas = [
            [
                str(g["id"]),
                g.get("fecha", ""),
                g.get("categoria_nombre", "") or "—",
                (g.get("descripcion") or "")[:28],
                f"${g.get('monto', 0):.2f}",
                (T("expenses_yes"), th.YELLOW) if g.get("recurrente") else "—",
            ]
            for g in gastos
        ]
        self.tabla.set_rows(gastos, celdas, firma=firma)

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
        self.combo_freq.set(_frecuencia_a_visible(g.get("frecuencia")))
        self._toggle_recurrente()

    def _nuevo_gasto(self):
        self._gasto_editando = None
        for e in [self.ent_fecha, self.ent_desc, self.ent_monto, self.ent_notas]:
            e.delete(0, "end")
        self.ent_fecha.insert(0, str(date.today()))
        self.combo_freq.set(T("freq_monthly"))
        self.var_recurrente.set(False)
        self._toggle_recurrente()

    def _guardar_gasto(self):
        cat_nombre = self.combo_cat.get()
        cat = self._categorias_data.get(cat_nombre)
        try:
            monto = float(self.ent_monto.get() or 0)
        except ValueError:
            messagebox.showerror(T("error"), T("expenses_invalid_amt"), parent=self.winfo_toplevel())
            return

        args = dict(
            fecha=self.ent_fecha.get() or str(date.today()),
            categoria_id=cat["id"] if cat else None,
            descripcion=self.ent_desc.get(),
            monto=monto,
            recurrente=1 if self.var_recurrente.get() else 0,
            frecuencia=_frecuencia_a_canonica(self.combo_freq.get()),
            notas=self.ent_notas.get(),
        )

        # Antes de arreglar esto, guardar SIEMPRE insertaba una fila nueva y
        # duplicaba el gasto sin avisar, dejando el original intacto.
        try:
            if self._gasto_editando:
                db_manager.actualizar_gasto(self._gasto_editando, **args)
            else:
                db_manager.agregar_gasto(**args)
        except Exception as e:
            messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())
            return

        self._nuevo_gasto()
        self._cargar_datos()

    def _eliminar_gasto(self):
        if not self._gasto_editando:
            messagebox.showwarning(T("warning"), T("expenses_select"), parent=self.winfo_toplevel())
            return
        if messagebox.askyesno(T("confirm"), T("expenses_confirm_del", id=self._gasto_editando), parent=self.winfo_toplevel()):
            try:
                db_manager.eliminar_gasto(self._gasto_editando)
            except Exception as e:
                messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())
                return
            self._nuevo_gasto()
            self._cargar_datos()
