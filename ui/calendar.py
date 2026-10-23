# ui/calendar.py – Vista de Calendario
# Muestra pedidos por fecha de entrega en un calendario mensual con tkcalendar

import customtkinter as ctk
try:
    from tkcalendar import Calendar as TkCalendar
except ImportError:
    TkCalendar = None
from tkinter import ttk
from datetime import datetime, date
import db_manager
from utils.i18n import T, get_idioma

try:
    from babel.dates import format_date as _format_date
except ImportError:
    _format_date = None

from ui import theme as th
from ui.theme import (
    COLOR_BG, COLOR_CARD, COLOR_ACCENT, COLOR_TEXT, COLOR_SUB,
    COLOR_BORDER, COLOR_HOVER, COLOR_RED, COLOR_YELLOW,
)

COLORES_ESTADO = th.ESTADO_COLORES

TAGS_ESTADO = {
    "pendiente": ("pendiente", th.YELLOW, th.BG),
    "en proceso": ("proceso", th.ACCENT, th.BG),
    "completado": ("completado", th.ESTADO_COLORES["completado"], th.BG),
    "cancelado": ("cancelado", th.RED, th.TEXT),
}


def _locale_actual() -> str:
    return "es_ES" if get_idioma() == "es" else "en_US"


def _capitalizar(texto: str) -> str:
    return texto[:1].upper() + texto[1:] if texto else texto


class CalendarView(ctk.CTkFrame):
    """Vista de calendario mensual con pedidos por fecha de entrega."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._todos_pedidos = []
        self._fecha_sel = date.today()
        self._locale = _locale_actual()
        self._construir_ui()

    def on_show(self):
        self._cargar_pedidos()

    def _construir_ui(self):
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("cal_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")

        frame_main = ctk.CTkFrame(self, fg_color="transparent")
        frame_main.pack(fill="both", expand=True, padx=28, pady=14)
        frame_main.columnconfigure(0, weight=2, uniform="cal")
        frame_main.columnconfigure(1, weight=3, uniform="cal")
        frame_main.rowconfigure(0, weight=1)

        self._construir_panel_calendario(frame_main)
        self._construir_panel_dia(frame_main)

    def _construir_panel_calendario(self, parent):
        frame_izq = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=14,
                                  border_width=1, border_color=COLOR_BORDER)
        frame_izq.grid(row=0, column=0, padx=(0, 8), sticky="nsew")
        frame_izq.grid_columnconfigure(0, weight=1)
        frame_izq.grid_rowconfigure(3, weight=1)

        head = ctk.CTkFrame(frame_izq, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 4))
        ctk.CTkLabel(head, text=T("cal_select_date"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")
        self.lbl_resumen_mes = ctk.CTkLabel(head, text="", text_color=COLOR_YELLOW,
                                            font=ctk.CTkFont(size=11, weight="bold"))
        self.lbl_resumen_mes.pack(side="right")

        contenedor_cal = ctk.CTkFrame(frame_izq, fg_color="transparent")
        contenedor_cal.grid(row=1, column=0, sticky="nsew", pady=(4, 10))

        if TkCalendar:
            self._aplicar_tema_ttk()
            self.cal = TkCalendar(
                contenedor_cal,
                selectmode="day",
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day,
                locale=self._locale,
                firstweekday="monday",
                showweeknumbers=False,
                background=COLOR_CARD,
                foreground=COLOR_TEXT,
                bordercolor=COLOR_BORDER,
                headersbackground=th.SURFACE,
                headersforeground=COLOR_ACCENT,
                selectbackground=COLOR_ACCENT,
                selectforeground=th.BG,
                normalbackground=COLOR_CARD,
                normalforeground="#D0D0D0",
                weekendbackground="#232323",
                weekendforeground=COLOR_YELLOW,
                othermonthbackground="#171717",
                othermonthforeground="#555555",
                othermonthwebackground="#151515",
                othermonthweforeground="#4A4A4A",
                disabledbackground=COLOR_CARD,
                disabledforeground=th.SUB_DIM,
                tooltipbackground=th.BG,
                tooltipforeground=COLOR_TEXT,
                tooltipdelay=350,
                borderwidth=0,
                font=("Segoe UI", 13),
            )
            self.cal.pack()
            self.cal.bind("<<CalendarSelected>>", self._on_fecha_seleccionada)
            self.cal.bind("<<CalendarMonthChanged>>", lambda e: self._actualizar_resumen_mes())
        else:
            ctk.CTkLabel(contenedor_cal,
                         text=T("cal_install_msg"),
                         text_color=COLOR_SUB, justify="center",
                         font=ctk.CTkFont(size=12)).pack(pady=40)

        frame_proximas = ctk.CTkFrame(frame_izq, fg_color=th.SURFACE, corner_radius=10)
        frame_proximas.grid(row=2, column=0, sticky="ew", padx=12, pady=(0, 14))
        frame_proximas.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(frame_proximas, text=T("cal_next_7"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_YELLOW).grid(row=0, column=0, sticky="w",
                                                   padx=12, pady=(10, 6))

        self.frame_proximas_scroll = ctk.CTkScrollableFrame(
            frame_proximas, fg_color="transparent", height=150,
            scrollbar_button_color=th.SCROLL_BUTTON,
            scrollbar_button_hover_color=th.SCROLL_HOVER)
        self.frame_proximas_scroll.grid(row=1, column=0, sticky="nsew",
                                        padx=6, pady=(0, 8))

        self.lbl_proximas_vacio = ctk.CTkLabel(frame_proximas,
                                               text=T("cal_no_upcoming"),
                                               text_color=COLOR_SUB,
                                               font=ctk.CTkFont(size=11))

    def _construir_panel_dia(self, parent):
        frame_der = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=14,
                                  border_width=1, border_color=COLOR_BORDER)
        frame_der.grid(row=0, column=1, sticky="nsew")
        frame_der.grid_columnconfigure(0, weight=1)
        frame_der.grid_rowconfigure(2, weight=1)

        head = ctk.CTkFrame(frame_der, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=16, pady=(14, 2))
        self.lbl_fecha_sel = ctk.CTkLabel(head, text="",
                                           font=ctk.CTkFont(size=16, weight="bold"),
                                           text_color=COLOR_TEXT)
        self.lbl_fecha_sel.pack(side="left")

        ctk.CTkButton(head, text=T("cal_today_btn"), width=62, height=28,
                      fg_color=th.SURFACE, hover_color=th.HOVER,
                      text_color=COLOR_ACCENT, corner_radius=8,
                      font=ctk.CTkFont(size=11, weight="bold"),
                      command=self._ir_hoy).pack(side="right")

        self.lbl_conteo_dia = ctk.CTkLabel(frame_der, text="", text_color=COLOR_SUB,
                                           font=ctk.CTkFont(size=12), anchor="w")
        self.lbl_conteo_dia.grid(row=1, column=0, sticky="w", padx=16, pady=(0, 8))

        cuerpo = ctk.CTkFrame(frame_der, fg_color="transparent")
        cuerpo.grid(row=2, column=0, sticky="nsew", padx=8, pady=(0, 12))
        cuerpo.grid_columnconfigure(0, weight=1)
        cuerpo.grid_rowconfigure(0, weight=1)

        self.frame_pedidos_fecha = ctk.CTkScrollableFrame(
            cuerpo, fg_color="transparent",
            scrollbar_button_color=th.SCROLL_BUTTON,
            scrollbar_button_hover_color=th.SCROLL_HOVER)

        self.frame_vacio = ctk.CTkFrame(cuerpo, fg_color="transparent")
        ctk.CTkLabel(self.frame_vacio, text="📅",
                     font=ctk.CTkFont(size=38)).pack(pady=(0, 8))
        ctk.CTkLabel(self.frame_vacio, text=T("cal_empty_title"),
                     font=ctk.CTkFont(size=15, weight="bold"),
                     text_color=COLOR_TEXT).pack()
        ctk.CTkLabel(self.frame_vacio, text=T("cal_empty_hint"),
                     font=ctk.CTkFont(size=12),
                     text_color=COLOR_SUB).pack(pady=(4, 0))

    def _aplicar_tema_ttk(self):
        """tkcalendar usa ttk; el tema 'clam' respeta los colores oscuros de los botones."""
        try:
            estilo = ttk.Style(self)
            if "clam" in estilo.theme_names():
                estilo.theme_use("clam")
        except Exception:
            pass

    def _cargar_pedidos(self):
        self._todos_pedidos = db_manager.obtener_pedidos()
        self._mostrar_proximas()
        self._set_fecha(self._fecha_sel)
        if TkCalendar and getattr(self, "cal", None):
            self._marcar_fechas_calendario()

    def _marcar_fechas_calendario(self):
        try:
            self.cal.calevent_remove("all")
        except Exception:
            pass

        for tag, color, texto in TAGS_ESTADO.values():
            try:
                self.cal.tag_config(tag, background=color, foreground=texto)
            except Exception:
                pass

        for p in self._todos_pedidos:
            fecha = p.get("fecha_entrega")
            estado = (p.get("estado") or "pendiente").strip().lower()
            if not fecha or estado not in TAGS_ESTADO:
                continue
            try:
                dia = datetime.strptime(fecha, "%Y-%m-%d").date()
            except ValueError:
                continue
            cliente = p.get("cliente_nombre") or p.get("descripcion") or "Pedido"
            detalle = f"{cliente} · ${p.get('precio_venta', 0):.2f} · {estado}"
            try:
                self.cal.calevent_create(dia, detalle, [TAGS_ESTADO[estado][0]])
            except Exception:
                pass

    def _actualizar_resumen_mes(self):
        if not (TkCalendar and getattr(self, "cal", None)):
            return
        try:
            mes, anio = self.cal.get_displayed_month()
        except Exception:
            return
        prefijo = f"{anio}-{mes:02d}"
        pendientes = sum(
            1 for p in self._todos_pedidos
            if p.get("estado") == "pendiente"
            and (p.get("fecha_entrega") or "").startswith(prefijo)
        )
        self.lbl_resumen_mes.configure(
            text=T("cal_month_summary", n=pendientes, mes=self._nombre_mes(anio, mes))
        )

    def _nombre_mes(self, anio: int, mes: int) -> str:
        if _format_date:
            try:
                return _capitalizar(_format_date(date(anio, mes, 1), "MMMM",
                                                locale=self._locale))
            except Exception:
                pass
        return T("months_short")[mes - 1]

    def _fecha_larga(self, dia: date) -> str:
        if _format_date:
            try:
                patron = ("EEEE d 'de' MMMM 'de' yyyy" if self._locale.startswith("es")
                          else "EEEE, MMMM d, yyyy")
                return _capitalizar(_format_date(dia, patron, locale=self._locale))
            except Exception:
                pass
        return dia.strftime("%Y-%m-%d")

    def _fecha_corta(self, fecha_str: str) -> str:
        try:
            dia = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return fecha_str or ""
        if _format_date:
            try:
                patron = "EEE d MMM" if self._locale.startswith("es") else "EEE, MMM d"
                return _capitalizar(_format_date(dia, patron, locale=self._locale))
            except Exception:
                pass
        return dia.strftime("%d/%m")

    def _mostrar_proximas(self):
        for w in self.frame_proximas_scroll.winfo_children():
            w.destroy()

        pedidos = db_manager.obtener_pedidos_proximos(7)
        if not pedidos:
            self.frame_proximas_scroll.grid_remove()
            self.lbl_proximas_vacio.grid(row=1, column=0, pady=18)
            return

        self.lbl_proximas_vacio.grid_remove()
        self.frame_proximas_scroll.grid(row=1, column=0, sticky="nsew",
                                        padx=6, pady=(0, 8))

        for p in pedidos:
            fecha = p.get("fecha_entrega", "")
            color = COLORES_ESTADO.get(p.get("estado", ""), COLOR_SUB)
            fila = ctk.CTkFrame(self.frame_proximas_scroll, fg_color=th.CARD,
                                corner_radius=8, height=36)
            fila.pack(fill="x", padx=2, pady=2)
            punto = ctk.CTkLabel(fila, text="●", text_color=color, width=16,
                                 font=ctk.CTkFont(size=12))
            punto.pack(side="left", padx=(8, 4))
            texto = ctk.CTkLabel(
                fila,
                text=f"{p.get('cliente_nombre') or '—'}  ·  {self._fecha_corta(fecha)}",
                font=ctk.CTkFont(size=11), text_color=COLOR_TEXT, anchor="w")
            texto.pack(side="left", fill="x", expand=True, pady=8)
            for widget in (fila, punto, texto):
                widget.bind("<Button-1>", lambda e, f=fecha: self._ir_a_fecha(f))

    def _ir_a_fecha(self, fecha_str: str):
        try:
            dia = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        except (TypeError, ValueError):
            return
        if TkCalendar and getattr(self, "cal", None):
            try:
                self.cal.selection_set(dia)
                self.cal.see(dia)
            except Exception:
                pass
        self._set_fecha(dia)

    def _ir_hoy(self):
        hoy = date.today()
        if TkCalendar and getattr(self, "cal", None):
            try:
                self.cal.selection_set(hoy)
                self.cal.see(hoy)
            except Exception:
                pass
        self._set_fecha(hoy)

    def _on_fecha_seleccionada(self, event=None):
        if TkCalendar and getattr(self, "cal", None):
            seleccion = self.cal.selection_get()
            if seleccion:
                self._set_fecha(seleccion)

    def _set_fecha(self, dia: date):
        self._fecha_sel = dia
        self._mostrar_pedidos_fecha(dia.strftime("%Y-%m-%d"))
        self._actualizar_resumen_mes()

    def _mostrar_pedidos_fecha(self, fecha_str: str):
        self.lbl_fecha_sel.configure(
            text=self._fecha_larga(datetime.strptime(fecha_str, "%Y-%m-%d").date())
        )
        for w in self.frame_pedidos_fecha.winfo_children():
            w.destroy()

        orden_estado = {"pendiente": 0, "en proceso": 1, "completado": 2, "cancelado": 3}
        pedidos_fecha = [p for p in self._todos_pedidos
                         if p.get("fecha_entrega") == fecha_str]
        pedidos_fecha.sort(key=lambda p: (orden_estado.get(p.get("estado", ""), 9),
                                         p.get("id", 0)))

        self.lbl_conteo_dia.configure(
            text=T("cal_day_count", n=len(pedidos_fecha)) if pedidos_fecha
            else T("cal_pick_hint")
        )

        if not pedidos_fecha:
            self.frame_pedidos_fecha.grid_remove()
            self.frame_vacio.grid(row=0, column=0, sticky="nsew")
            return

        self.frame_vacio.grid_remove()
        self.frame_pedidos_fecha.grid(row=0, column=0, sticky="nsew")

        for p in pedidos_fecha:
            estado = p.get("estado", "")
            color_estado = COLORES_ESTADO.get(estado, COLOR_SUB)

            card = ctk.CTkFrame(self.frame_pedidos_fecha, fg_color=th.SURFACE,
                                corner_radius=10)
            card.pack(fill="x", pady=4, padx=4)

            f_top = ctk.CTkFrame(card, fg_color="transparent")
            f_top.pack(fill="x", padx=12, pady=(10, 2))
            ctk.CTkLabel(f_top, text=f"#{p['id']}  {p.get('descripcion', '')[:44]}",
                         font=ctk.CTkFont(size=13, weight="bold"),
                         text_color=COLOR_TEXT, anchor="w").pack(side="left")
            ctk.CTkLabel(f_top, text=estado, fg_color=color_estado,
                         text_color=th.BG, corner_radius=6, height=22, width=86,
                         font=ctk.CTkFont(size=10, weight="bold")).pack(side="right")

            f_bottom = ctk.CTkFrame(card, fg_color="transparent")
            f_bottom.pack(fill="x", padx=12, pady=(0, 10))
            ctk.CTkLabel(f_bottom,
                         text=f"👤 {p.get('cliente_nombre') or '—'}",
                         font=ctk.CTkFont(size=11), text_color=COLOR_SUB,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(f_bottom,
                         text=f"${p.get('precio_venta', 0):,.2f}",
                         font=ctk.CTkFont(size=12, weight="bold"),
                         text_color=COLOR_ACCENT, anchor="e").pack(side="right")
