# ui/quotes.py – Historial de cotizaciones con conversión a pedido

import threading
from datetime import datetime

import customtkinter as ctk
from tkinter import filedialog, messagebox

import db_manager
from utils import quotes
from utils.i18n import T
from ui import theme as th
from ui import components as ui

_ESTADOS = {
    "borrador": ("quote_status_borrador", th.SUB),
    "enviada": ("quote_status_enviada", th.YELLOW),
    "aceptada": ("quote_status_aceptada", th.ACCENT),
    "rechazada": ("quote_status_rechazada", th.RED),
}


def _fecha(valor):
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(valor or "")


class QuotesView(ctk.CTkFrame):
    """Lista de cotizaciones emitidas, con detalle y acciones."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._cotizaciones = []
        self._seleccion = None
        self._debounce = None
        self._construir_ui()

    def on_show(self):
        self._cargar()

    def _construir_ui(self):
        _header, acciones = ui.page_header(self, T("quotes_title"))
        ui.primary_button(acciones, T("quotes_new"), self._nueva,
                          width=180).pack(side="right")

        filtros = ui.card(self, corner_radius=th.RADIUS_CARD)
        filtros.pack(fill="x", padx=th.PAD_PAGE, pady=12)
        self.entry_buscar = ui.entry(filtros, T("quotes_search_ph"), width=280)
        self.entry_buscar.pack(side="left", padx=10, pady=8)
        self.entry_buscar.bind("<KeyRelease>", self._on_buscar_tecla)

        ui.section_label(filtros, T("quotes_col_status")).pack(side="left", padx=(14, 4))
        self.combo_estado = ui.option_menu(
            filtros, values=[T("quotes_filter_all")]
            + [T(_ESTADOS[e][0]) for e in _ESTADOS],
            width=140, command=lambda _: self._cargar())
        self.combo_estado.set(T("quotes_filter_all"))
        self.combo_estado.pack(side="left", pady=8, padx=4)

        main = ctk.CTkFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=(0, 20))
        main.columnconfigure(0, weight=3)
        main.columnconfigure(1, weight=2)
        main.rowconfigure(0, weight=1)

        self.tabla = ui.DataTable(
            main,
            columnas=[T("quotes_col_number"), T("quotes_col_date"),
                      T("quotes_col_client"), T("quotes_col_total"),
                      T("quotes_col_status")],
            pesos=[3, 2, 3, 2, 2],
            alinear=["w", "w", "w", "e", "w"],
            on_select=lambda c: self._seleccionar(c["id"]),
        )
        self.tabla.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        self.panel = ui.card(main)
        self.panel.grid(row=0, column=1, sticky="nsew")
        self.panel.grid_rowconfigure(0, weight=1)
        self.panel.grid_columnconfigure(0, weight=1)
        self.frame_detalle = ui.scrollable(self.panel)
        self.frame_detalle.grid(row=0, column=0, sticky="nsew", padx=4, pady=4)
        self._detalle_vacio()

    def _nueva(self):
        abrir = getattr(self.app, "_abrir_calculadora", None)
        if callable(abrir):
            abrir()

    def _on_buscar_tecla(self, event=None):
        if self._debounce is not None:
            try:
                self.after_cancel(self._debounce)
            except Exception:
                pass
        self._debounce = self.after(250, self._cargar)

    def _estado_actual(self):
        visible = self.combo_estado.get()
        for clave, (i18n, _color) in _ESTADOS.items():
            if visible == T(i18n):
                return clave
        return None

    def _cargar(self):
        self._cotizaciones = db_manager.obtener_cotizaciones(
            filtro_estado=self._estado_actual(),
            filtro_texto=self.entry_buscar.get().strip() or None,
        )

        if not self._cotizaciones:
            self.tabla.mostrar_vacio(T("quotes_empty_title"), icono="🧾",
                                     hint=T("quotes_empty_hint"),
                                     cta_texto=T("quotes_new"),
                                     cta_cmd=self._nueva)
            self._seleccion = None
            self._detalle_vacio()
            return

        celdas = []
        for c in self._cotizaciones:
            estado = c.get("estado", "borrador")
            etiqueta, color = _ESTADOS.get(estado, (estado, th.SUB))
            celdas.append([
                c["numero"],
                _fecha(c.get("fecha")),
                c.get("cliente_nombre") or "—",
                f"${float(c.get('total') or 0):,.2f}",
                (T(etiqueta), color),
            ])
        firma = tuple((c["id"], c.get("total"), c.get("estado"),
                       c.get("cliente_nombre")) for c in self._cotizaciones)
        self.tabla.set_rows(self._cotizaciones, celdas, firma=firma)

        if self._seleccion and not any(
                c["id"] == self._seleccion["id"] for c in self._cotizaciones):
            self._seleccion = None
            self._detalle_vacio()

    def _detalle_vacio(self):
        for w in self.frame_detalle.winfo_children():
            w.destroy()
        ui.empty_state(self.frame_detalle, "🧾", T("quotes_detail_empty"),
                       T("quotes_detail_hint"))

    def _seleccionar(self, cot_id):
        cot = db_manager.obtener_cotizacion(cot_id)
        if not cot:
            return
        self._seleccion = cot
        self._render_detalle(cot)

    def _render_detalle(self, cot):
        for w in self.frame_detalle.winfo_children():
            w.destroy()

        cab = ctk.CTkFrame(self.frame_detalle, fg_color="transparent")
        cab.pack(fill="x", padx=12, pady=(12, 4))
        ctk.CTkLabel(cab, text=cot["numero"], font=th.fuente(16, True),
                     text_color=th.TEXT).pack(side="left")
        estado = cot.get("estado", "borrador")
        etiqueta, color = _ESTADOS.get(estado, (estado, th.SUB))
        ui.status_pill(cab, T(etiqueta), width=90, color=color).pack(side="right")

        ui.section_label(self.frame_detalle,
                         f"{T('quotes_col_date')}: {_fecha(cot.get('fecha'))}"
                         ).pack(anchor="w", padx=12, pady=(2, 0))
        ui.section_label(self.frame_detalle,
                         f"{T('quote_text_valid')}: {self._vence(cot)}"
                         ).pack(anchor="w", padx=12, pady=(1, 0))
        if cot.get("cliente_nombre"):
            ctk.CTkLabel(self.frame_detalle, text=cot["cliente_nombre"],
                         font=th.fuente(13, True), text_color=th.TEXT,
                         anchor="w").pack(fill="x", padx=12, pady=(6, 0))

        ui.divider(self.frame_detalle).pack(fill="x", padx=12, pady=8)

        for item in cot.get("items", []):
            fila = ctk.CTkFrame(self.frame_detalle, fg_color="transparent")
            fila.pack(fill="x", padx=12, pady=3)
            ctk.CTkLabel(fila, text=f"{float(item.get('cantidad') or 1):g} × "
                                    f"{item.get('descripcion') or '—'}",
                         font=th.fuente(11), text_color=th.TEXT,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(fila, text=f"${float(item.get('precio_unitario') or 0):,.2f}",
                         font=th.fuente(11), text_color=th.SUB).pack(side="right")

        ui.divider(self.frame_detalle).pack(fill="x", padx=12, pady=8)
        total = float(cot.get("total") or 0)
        f_total = ctk.CTkFrame(self.frame_detalle, fg_color=th.ACCENT_DIM,
                               corner_radius=th.RADIUS_INPUT)
        f_total.pack(fill="x", padx=12, pady=(0, 8))
        ctk.CTkLabel(f_total, text=T("quote_dialog_total"),
                     font=th.fuente(12, True), text_color=th.ACCENT
                     ).pack(side="left", padx=12)
        ctk.CTkLabel(f_total, text=f"${total:,.2f}", font=th.fuente(18, True),
                     text_color=th.ACCENT).pack(side="right", padx=12, pady=8)

        if cot.get("notas"):
            ui.section_label(self.frame_detalle, cot["notas"],
                             wraplength=360).pack(anchor="w", padx=12, pady=(0, 8))

        ui.secondary_button(self.frame_detalle, T("quotes_open_pdf"),
                            lambda: self._abrir_pdf(cot)).pack(
                                fill="x", padx=12, pady=(4, 6))
        ui.primary_button(self.frame_detalle, T("quotes_convert"),
                          lambda: self._convertir(cot)).pack(
                              fill="x", padx=12, pady=(0, 6))

        opciones = [("aceptada", T("quotes_mark_accepted")),
                    ("rechazada", T("quotes_mark_rejected"))]
        opciones = [(e, t) for e, t in opciones if e != estado]
        if opciones:
            estados = ctk.CTkFrame(self.frame_detalle, fg_color="transparent")
            estados.pack(fill="x", padx=12, pady=(0, 6))
            for col in range(len(opciones)):
                estados.columnconfigure(col, weight=1, uniform="q")
            for col, (clave, texto) in enumerate(opciones):
                ui.secondary_button(estados, texto,
                                    lambda c=clave: self._cambiar_estado(cot, c),
                                    font=th.fuente(11), height=30).grid(
                                        row=0, column=col, sticky="ew",
                                        padx=(0, 4) if col == 0 else (4, 0))

        ui.danger_button(self.frame_detalle, T("quotes_delete"),
                         lambda: self._eliminar(cot)).pack(
                             fill="x", padx=12, pady=(0, 12))

    def _vence(self, cot):
        try:
            fecha = datetime.strptime(str(cot["fecha"])[:10], "%Y-%m-%d").date()
            from datetime import timedelta
            return (fecha + timedelta(days=int(cot.get("validez_dias") or 7))
                    ).strftime("%d/%m/%Y")
        except (KeyError, TypeError, ValueError):
            return "—"

    def _cot_para_render(self, cot):
        config = getattr(self.app, "config_data", None)
        config = config if isinstance(config, dict) else {}
        datos = quotes.desde_registro(cot, config.get("negocio", {}) or {})
        cliente = dict(datos.get("cliente") or {})
        if cot.get("cliente_id"):
            for c in db_manager.obtener_clientes():
                if c["id"] == cot["cliente_id"]:
                    cliente["email"] = c.get("email", "")
                    cliente["telefono"] = c.get("telefono", "")
                    break
        datos["cliente"] = cliente
        return datos

    def _abrir_pdf(self, cot):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"{cot['numero']}.pdf",
            title=T("quotes_open_pdf"),
        )
        if not ruta:
            return
        datos = self._cot_para_render(cot)

        def worker():
            try:
                quotes.render_pdf(datos, ruta)
                self.after(0, lambda: messagebox.showinfo(
                    T("success"), T("quotes_pdf_ok", path=ruta),
                    parent=self.winfo_toplevel()))
            except Exception as exc:
                self.after(0, lambda err=str(exc): messagebox.showerror(
                    T("error"), err, parent=self.winfo_toplevel()))

        threading.Thread(target=worker, daemon=True).start()

    def _convertir(self, cot):
        if not cot.get("items"):
            return
        if cot.get("pedido_id"):
            messagebox.showinfo(
                T("quotes_already_converted",
                  numero=cot.get("numero", ""), pedido=cot["pedido_id"]),
                parent=self.winfo_toplevel())
            return

        item = cot["items"][0]
        cantidad = max(0.0, float(item.get("cantidad") or 1))
        datos = {
            "descripcion": item.get("descripcion") or "",
            "cliente_id": cot.get("cliente_id"),
            "gramos": float(item.get("gramos") or 0) * cantidad,
            "horas": float(item.get("horas") or 0) * cantidad,
            "costo_material": float(item.get("costo_material") or 0) * cantidad,
            "costo_tiempo": float(item.get("costo_tiempo") or 0) * cantidad,
            "precio_sugerido": float(item.get("precio_unitario") or 0) * cantidad,
            "filamento_id": item.get("filamento_id"),
            "notas": cot.get("notas") or "",
            "cotizacion_id": cot["id"],
        }
        try:
            self.app.navegar("pedidos")
            vista = self.app._cache_vistas.get("pedidos")
            if vista is None or not hasattr(vista, "prellenar"):
                messagebox.showerror(T("error"), T("quotes_convert_error"),
                                     parent=self.winfo_toplevel())
                return
            vista.prellenar(datos)
            messagebox.showinfo(T("success"),
                                T("quotes_converted", numero=cot["numero"]),
                                parent=self.winfo_toplevel())
        except Exception as exc:
            messagebox.showerror(T("error"), str(exc),
                                 parent=self.winfo_toplevel())

    def _cambiar_estado(self, cot, estado):
        try:
            db_manager.actualizar_estado_cotizacion(cot["id"], estado)
            self._cargar()
            self._seleccionar(cot["id"])
        except Exception as exc:
            messagebox.showerror(T("error"), str(exc),
                                 parent=self.winfo_toplevel())

    def _eliminar(self, cot):
        if not messagebox.askyesno(
                T("confirm"), T("quotes_delete_confirm", numero=cot["numero"]),
                parent=self.winfo_toplevel()):
            return
        try:
            db_manager.eliminar_cotizacion(cot["id"])
            self._seleccion = None
            self._cargar()
            self._detalle_vacio()
        except Exception as exc:
            messagebox.showerror(T("error"), str(exc),
                                 parent=self.winfo_toplevel())
