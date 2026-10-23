# ui/quote_dialog.py – Diálogo para crear una cotización desde la calculadora

import threading
from datetime import date

import customtkinter as ctk
from tkinter import filedialog, messagebox

import db_manager
from utils import quotes
from utils.i18n import T
from utils.labels import mapa_por_etiqueta
from ui import theme as th
from ui import components as ui


class QuoteDialog(ctk.CTkToplevel):
    """Pide los datos comerciales, guarda la cotización y genera texto o PDF."""

    def __init__(self, master, app, calculo, on_created=None):
        super().__init__(master)
        self.app = app
        self.calculo = calculo or {}
        self.on_created = on_created

        config = getattr(app, "config_data", None)
        config = config if isinstance(config, dict) else {}
        self.negocio = config.get("negocio", {}) or {}
        self.moneda = config.get("moneda") or quotes.MONEDA_DEFECTO

        self.title(T("quote_dialog_title"))
        self.geometry("520x790")
        self.resizable(False, False)
        self.configure(fg_color=th.BG)
        self.attributes("-topmost", True)
        self.transient(master)

        self._clientes_data = mapa_por_etiqueta(
            db_manager.obtener_clientes(), lambda c: c["nombre"])
        self._construir_ui()
        self._centrar(master)
        self.grab_set()
        self.after(80, self.ent_descripcion.focus_set)

    def _centrar(self, master):
        self.update_idletasks()
        try:
            x = master.winfo_rootx() + (master.winfo_width() - self.winfo_width()) // 2
            y = master.winfo_rooty() + (master.winfo_height() - self.winfo_height()) // 2
            self.geometry(f"+{max(0, x)}+{max(0, y)}")
        except Exception:
            pass

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=22, pady=(18, 0))
        ctk.CTkLabel(header, text=T("quote_dialog_title"),
                     font=th.fuente(20, True),
                     text_color=th.TEXT).pack(anchor="w")
        ctk.CTkLabel(self, text=T("quote_dialog_subtitle"),
                     font=th.fuente(11), text_color=th.SUB).pack(anchor="w", padx=22)
        ui.divider(self).pack(fill="x", padx=22, pady=(10, 10))

        footer = ctk.CTkFrame(self, fg_color="transparent")
        footer.pack(side="bottom", fill="x", padx=18, pady=(8, 12))

        acciones = ctk.CTkFrame(footer, fg_color="transparent")
        acciones.pack(fill="x")
        acciones.columnconfigure(0, weight=1, uniform="qb")
        acciones.columnconfigure(1, weight=1, uniform="qb")
        ui.secondary_button(acciones, T("quote_dialog_copy"), self._copiar_texto,
                            font=th.fuente(12)).grid(row=0, column=0, sticky="ew",
                                                     padx=(0, 4))
        ui.primary_button(acciones, T("quote_dialog_pdf"), self._guardar_pdf,
                          font=th.fuente(12)).grid(row=0, column=1, sticky="ew",
                                                   padx=(4, 0))
        ui.secondary_button(footer, T("quote_dialog_cancel"), self.destroy).pack(
            fill="x", pady=(6, 0))

        scroll = ui.scrollable(self, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=18, pady=0)

        card = ui.card(scroll)
        card.pack(fill="x", pady=(0, 8))
        ui.section_title(card, T("quote_dialog_data")).pack(
            anchor="w", padx=16, pady=(12, 8))

        ui.section_label(card, T("quote_dialog_client")).pack(
            anchor="w", padx=16, pady=(2, 2))
        valores = [T("quote_dialog_no_client")] + list(self._clientes_data.keys())
        self.combo_cliente = ui.option_menu(card, values=valores)
        self.combo_cliente.set(valores[0])
        self.combo_cliente.pack(fill="x", padx=16)

        ui.section_label(card, T("quote_dialog_description")).pack(
            anchor="w", padx=16, pady=(10, 2))
        self.ent_descripcion = ui.entry(
            card, self.calculo.get("descripcion") or T("quote_default_description"))
        self.ent_descripcion.insert(0, self.calculo.get("descripcion")
                                    or T("quote_default_description"))
        self.ent_descripcion.pack(fill="x", padx=16)

        grid = ctk.CTkFrame(card, fg_color="transparent")
        grid.pack(fill="x", padx=16, pady=(2, 0))
        grid.columnconfigure(0, weight=1, uniform="q")
        grid.columnconfigure(1, weight=1, uniform="q")

        col_qty = ctk.CTkFrame(grid, fg_color="transparent")
        col_qty.grid(row=0, column=0, sticky="ew", padx=(0, 5), pady=(8, 0))
        ui.section_label(col_qty, T("quote_dialog_qty")).pack(anchor="w", pady=(0, 2))
        self.ent_cantidad = ui.entry(col_qty, "1")
        self.ent_cantidad.insert(0, "1")
        self.ent_cantidad.pack(fill="x")
        self.ent_cantidad.bind("<KeyRelease>", lambda e: self._actualizar_total())

        col_val = ctk.CTkFrame(grid, fg_color="transparent")
        col_val.grid(row=0, column=1, sticky="ew", padx=(5, 0), pady=(8, 0))
        ui.section_label(col_val, T("quote_dialog_validity")).pack(anchor="w", pady=(0, 2))
        self.ent_validez = ui.entry(col_val, "7")
        self.ent_validez.insert(0, "7")
        self.ent_validez.pack(fill="x")

        ui.section_label(card, T("quote_dialog_notes")).pack(
            anchor="w", padx=16, pady=(10, 2))
        self.ent_notas = ui.entry(card, T("quote_dialog_notes"))
        self.ent_notas.pack(fill="x", padx=16, pady=(0, 12))

        resumen = ui.card(scroll)
        resumen.pack(fill="x", pady=(0, 8))
        ui.section_title(resumen, T("quote_dialog_summary")).pack(
            anchor="w", padx=16, pady=(12, 6))

        def fila(etiqueta, valor):
            f = ctk.CTkFrame(resumen, fg_color="transparent")
            f.pack(fill="x", padx=16, pady=3)
            ui.section_label(f, etiqueta).pack(side="left")
            lbl = ctk.CTkLabel(f, text=valor, font=th.fuente(12, True),
                               text_color=th.TEXT)
            lbl.pack(side="right")
            return lbl

        material = self.calculo.get("material_nombre") or "—"
        fila(T("quote_dialog_material"), material)
        fila(T("quote_dialog_grams"), f"{float(self.calculo.get('gramos') or 0):g} g")
        fila(T("quote_dialog_hours"), f"{float(self.calculo.get('horas') or 0):g} h")
        self.lbl_unitario = fila(
            T("quote_dialog_unit_price"),
            f"{self.moneda}{float(self.calculo.get('precio_sugerido') or 0):,.2f}")

        ui.divider(resumen).pack(fill="x", padx=16, pady=(8, 4))
        f_total = ctk.CTkFrame(resumen, fg_color=th.ACCENT_DIM,
                               corner_radius=th.RADIUS_INPUT)
        f_total.pack(fill="x", padx=10, pady=(0, 12))
        ctk.CTkLabel(f_total, text=T("quote_dialog_total"),
                     font=th.fuente(12, True),
                     text_color=th.ACCENT).pack(side="left", padx=14)
        self.lbl_total = ctk.CTkLabel(f_total, text=f"{self.moneda}0.00",
                                      font=th.fuente(18, True),
                                      text_color=th.ACCENT)
        self.lbl_total.pack(side="right", padx=14, pady=8)

        if not self.negocio.get("nombre"):
            ctk.CTkLabel(scroll, text=T("quotes_no_business"),
                         font=th.fuente(10), text_color=th.YELLOW,
                         justify="left", wraplength=440).pack(
                             anchor="w", padx=6, pady=(0, 8))

        self._actualizar_total()

    def _cantidad(self):
        try:
            return max(0.0, float(self.ent_cantidad.get() or 0))
        except ValueError:
            return 0.0

    def _actualizar_total(self):
        total = self._cantidad() * float(self.calculo.get("precio_sugerido") or 0)
        self.lbl_total.configure(text=f"{self.moneda}{total:,.2f}")

    def _cliente(self):
        etiqueta = self.combo_cliente.get()
        if etiqueta in self._clientes_data:
            return self._clientes_data[etiqueta]
        return {}

    def _datos(self):
        cantidad = self._cantidad()
        try:
            validez = max(1, int(float(self.ent_validez.get() or 7)))
        except ValueError:
            validez = quotes.VALIDEZ_DEFECTO
        precio = max(0.0, float(self.calculo.get("precio_sugerido") or 0))
        if cantidad <= 0 or precio <= 0:
            messagebox.showwarning(T("warning"), T("quote_dialog_invalid"),
                                   parent=self)
            return None

        cliente = self._cliente()
        item = {
            "descripcion": self.ent_descripcion.get().strip()
                           or T("quote_default_description"),
            "cantidad": cantidad,
            "material": self.calculo.get("material_nombre") or "",
            "gramos": float(self.calculo.get("gramos") or 0),
            "horas": float(self.calculo.get("horas") or 0),
            "costo_material": float(self.calculo.get("costo_material") or 0),
            "costo_tiempo": float(self.calculo.get("costo_tiempo") or 0),
            "filamento_id": self.calculo.get("filamento_id"),
            "precio_unitario": precio,
        }
        res = db_manager.crear_cotizacion(
            fecha=str(date.today()),
            cliente_id=cliente.get("id"),
            cliente_nombre=cliente.get("nombre", ""),
            validez_dias=validez,
            notas=self.ent_notas.get().strip(),
            condiciones="",
            items=[item],
            moneda=self.moneda,
        )
        cot = quotes.desde_registro(db_manager.obtener_cotizacion(res["id"]),
                                    self.negocio)
        cot["cliente"] = cliente
        return cot

    def _finalizar(self, cot):
        if self.on_created:
            try:
                self.on_created(cot)
            except Exception:
                pass
        self.destroy()

    def _copiar_texto(self):
        cot = self._datos()
        if not cot:
            return
        try:
            self.clipboard_clear()
            self.clipboard_append(quotes.render_texto(cot))
            self.update()
        except Exception as exc:
            messagebox.showerror(T("error"), str(exc), parent=self)
            return
        messagebox.showinfo(T("success"), T("quote_dialog_copied"), parent=self)
        self._finalizar(cot)

    def _guardar_pdf(self):
        cot = self._datos()
        if not cot:
            return
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{cot['numero']}.pdf",
            title=T("quotes_open_pdf"),
        )
        if not ruta:
            self._finalizar(cot)
            return

        def worker():
            try:
                quotes.render_pdf(cot, ruta)
                self.after(0, lambda: self._pdf_listo(ruta, cot))
            except Exception as exc:
                self.after(0, lambda err=str(exc): messagebox.showerror(
                    T("error"), err, parent=self))

        threading.Thread(target=worker, daemon=True).start()

    def _pdf_listo(self, ruta, cot):
        messagebox.showinfo(T("success"), T("quotes_pdf_ok", path=ruta), parent=self)
        self._finalizar(cot)
