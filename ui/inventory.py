# ui/inventory.py – Vista de Inventario de Filamentos
# Gestión de stock de filamentos con alertas visuales cuando baja del umbral

import customtkinter as ctk
from tkinter import messagebox
import db_manager
from utils.i18n import T
from ui import theme as th
from ui import components as ui

MATERIALES = ["PLA", "PETG", "ABS", "TPU", "ASA", "Nylon", "Resina", "Otro"]


class InventoryView(ctk.CTkFrame):
    """Vista de inventario con cards de filamento y formulario lateral."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._filamento_editando = None
        self._construir_ui()

    def on_show(self):
        self._cargar_filamentos()

    def _construir_ui(self):
        _, zona_acciones = ui.page_header(self, T("inv_title"))
        ui.primary_button(zona_acciones, T("inv_new"),
                          self._nuevo_filamento, width=160).pack(side="right")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=14)
        frame_main.columnconfigure(0, weight=3)
        frame_main.columnconfigure(1, weight=2)
        frame_main.rowconfigure(0, weight=1)

        frame_izq = ui.card(frame_main)
        frame_izq.grid(row=0, column=0, padx=(0, th.GAP), sticky="nsew")

        ui.section_title(frame_izq, T("inv_stock")).pack(
            anchor="w", padx=16, pady=(14, 6))

        self.frame_cards = ui.scrollable(frame_izq)
        self.frame_cards.pack(fill="both", expand=True, padx=6, pady=(0, 8))

        self.frame_form = ui.scrollable(frame_main, fg_color=th.CARD,
                                        corner_radius=th.RADIUS_CARD,
                                        border_width=1, border_color=th.BORDER)
        self.frame_form.grid(row=0, column=1, sticky="nsew")
        self._construir_formulario(self.frame_form)

    def _construir_formulario(self, parent):
        ui.section_title(parent, T("inv_form_title")).pack(
            anchor="w", padx=14, pady=(14, 6))

        grid = ctk.CTkFrame(parent, fg_color="transparent")
        grid.pack(fill="x", padx=14)
        grid.grid_columnconfigure(0, weight=1, uniform="inv")
        grid.grid_columnconfigure(1, weight=1, uniform="inv")

        def celda(fila, col, texto, colspan=1):
            caja = ctk.CTkFrame(grid, fg_color="transparent")
            caja.grid(row=fila, column=col, columnspan=colspan, sticky="ew",
                      padx=(0, th.GAP if col == 0 else 0), pady=(0, th.GAP))
            ui.section_label(caja, texto).pack(anchor="w", pady=(0, 3))
            return caja

        caja = celda(0, 0, T("inv_name"))
        self.ent_nombre = ui.entry(caja, T("inv_name_ph"))
        self.ent_nombre.pack(fill="x")

        caja = celda(0, 1, T("inv_material"))
        self.combo_material = ui.option_menu(caja, MATERIALES)
        self.combo_material.pack(fill="x")

        caja = celda(1, 0, T("inv_color"))
        self.ent_color = ui.entry(caja, T("inv_color_ph"))
        self.ent_color.pack(fill="x")

        caja = celda(1, 1, T("inv_grams"))
        self.ent_gramos = ui.entry(caja, "1000")
        self.ent_gramos.pack(fill="x")

        caja = celda(2, 0, T("inv_price_kg"))
        self.ent_precio = ui.entry(caja, "20.00")
        self.ent_precio.pack(fill="x")

        caja = celda(2, 1, T("inv_threshold"))
        self.ent_umbral = ui.entry(caja, "100")
        self.ent_umbral.pack(fill="x")

        caja = celda(3, 0, T("inv_supplier"), colspan=2)
        self.ent_proveedor = ui.entry(caja, T("inv_supplier_ph"))
        self.ent_proveedor.pack(fill="x")

        caja = celda(4, 0, T("inv_notes"), colspan=2)
        self.ent_notas = ui.entry(caja, T("inv_notes_ph"))
        self.ent_notas.pack(fill="x")

        ui.divider(parent).pack(fill="x", padx=14, pady=12)

        ui.primary_button(parent, T("inv_save"), self._guardar_filamento,
                          height=th.H_BTN_LG).pack(fill="x", padx=14, pady=(0, 6))

        ui.danger_button(parent, T("inv_delete"), self._eliminar_filamento).pack(
            fill="x", padx=14, pady=(0, 14))

    def _cargar_filamentos(self):
        for w in self.frame_cards.winfo_children():
            w.destroy()
        filamentos = db_manager.obtener_filamentos()

        if not filamentos:
            ui.empty_state(self.frame_cards, icono="🧵",
                           titulo=T("inv_stock"),
                           hint=T("inv_empty"),
                           cta_texto=T("inv_new"),
                           cta_cmd=self._nuevo_filamento)
            return

        for f in filamentos:
            self._crear_card_filamento(f)

    def _crear_card_filamento(self, f):
        bajo_umbral = f["gramos_restantes"] < f["umbral_bajo"]

        card = ui.card(self.frame_cards,
                       fg_color=th.DANGER_BG if bajo_umbral else th.SURFACE,
                       border_color=th.RED if bajo_umbral else th.BORDER)
        card.pack(fill="x", pady=4, padx=2)
        card.bind("<Button-1>", lambda e, fid=f["id"]: self._seleccionar_filamento(fid))

        frame_row = ctk.CTkFrame(card, fg_color="transparent")
        frame_row.pack(fill="x", padx=12, pady=(10, 0))
        frame_row.bind("<Button-1>", lambda e, fid=f["id"]: self._seleccionar_filamento(fid))

        ctk.CTkLabel(frame_row,
                     text=f"{f['nombre']}  [{f['material']}]",
                     font=th.fuente(13, True),
                     text_color=th.RED if bajo_umbral else th.TEXT,
                     anchor="w").pack(side="left")

        ctk.CTkLabel(frame_row,
                     text=f"{f['gramos_restantes']:.0f} g",
                     font=th.fuente(13, True),
                     text_color=th.RED if bajo_umbral else th.ACCENT,
                     anchor="e").pack(side="right")

        max_gramos = max(f["gramos_restantes"], f["umbral_bajo"], 1000)
        progreso = max(0, min(1, f["gramos_restantes"] / max_gramos))
        barra = ctk.CTkProgressBar(card, height=6, corner_radius=4,
                                   progress_color=th.RED if bajo_umbral else th.ACCENT,
                                   fg_color=th.BORDER)
        barra.set(progreso)
        barra.pack(fill="x", padx=12, pady=(6, 4))

        if bajo_umbral:
            info = ctk.CTkLabel(card, text=T("inv_low_stock", threshold=f['umbral_bajo'], price=f['precio_por_kg']),
                                font=th.fuente(10), text_color=th.RED)
        else:
            info = ctk.CTkLabel(card, text=f"Color: {f.get('color','—')}  ·  ${f['precio_por_kg']}/kg  ·  {T('inv_threshold')}: {f['umbral_bajo']}g",
                                font=th.fuente(10), text_color=th.SUB_DIM)
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
            messagebox.showerror(T("error"), T("inv_invalid_nums"), parent=self.winfo_toplevel())
            return

        if not args["nombre"]:
            messagebox.showwarning(T("warning"), T("inv_name_required"), parent=self.winfo_toplevel())
            return

        try:
            if self._filamento_editando:
                db_manager.actualizar_filamento(self._filamento_editando, **args)
            else:
                db_manager.agregar_filamento(**args)
        except Exception as e:
            messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())
            return

        self._nuevo_filamento()
        self._cargar_filamentos()

    def _eliminar_filamento(self):
        if not self._filamento_editando:
            messagebox.showwarning(T("warning"), T("inv_select"), parent=self.winfo_toplevel())
            return
        if messagebox.askyesno(T("confirm"), T("inv_confirm_del", id=self._filamento_editando), parent=self.winfo_toplevel()):
            try:
                db_manager.eliminar_filamento(self._filamento_editando)
            except Exception as e:
                messagebox.showerror(T("error"), str(e), parent=self.winfo_toplevel())
                return
            self._nuevo_filamento()
            self._cargar_filamentos()
