# ui/calendar.py – Vista de Calendario
# Muestra pedidos por fecha de entrega en un calendario mensual con tkcalendar

import customtkinter as ctk
try:
    from tkcalendar import Calendar as TkCalendar
except ImportError:
    TkCalendar = None
from datetime import datetime, date
import db_manager
from utils.i18n import T

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"
COLOR_RED    = "#FF4C4C"
COLOR_YELLOW = "#FFD166"


class CalendarView(ctk.CTkFrame):
    """Vista de calendario mensual con pedidos por fecha de entrega."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
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
        frame_main.columnconfigure(0, weight=2)
        frame_main.columnconfigure(1, weight=3)
        frame_main.rowconfigure(0, weight=1)

        frame_izq = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                  border_width=1, border_color=COLOR_BORDER)
        frame_izq.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(frame_izq, text=T("cal_select_date"),
                     font=ctk.CTkFont(size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(pady=(14, 8), padx=14, anchor="w")

        if TkCalendar:
            self.cal = TkCalendar(
                frame_izq,
                selectmode='day',
                year=datetime.now().year,
                month=datetime.now().month,
                day=datetime.now().day,
                background="#1E1E1E",
                foreground="#FFFFFF",
                bordercolor="#2D2D2D",
                headersbackground="#252525",
                headersforeground="#00FF9D",
                selectbackground="#00FF9D",
                selectforeground="#000000",
                weekendforeground="#FFD166",
                normalforeground="#CCCCCC",
                othermonthforeground="#555555",
                othermonthbackground="#1A1A1A",
                font=("Segoe UI", 10),
                showweeknumbers=False,
                firstweekday="monday",
            )
            self.cal.pack(padx=14, pady=(0, 14))
            self.cal.bind("<<CalendarSelected>>", self._on_fecha_seleccionada)
        else:
            ctk.CTkLabel(frame_izq,
                         text=T("cal_install_msg"),
                         text_color=COLOR_SUB, justify="center",
                         font=ctk.CTkFont(size=12)).pack(pady=40)

        frame_proximas = ctk.CTkFrame(frame_izq, fg_color="#252525", corner_radius=10)
        frame_proximas.pack(fill="x", padx=12, pady=(0, 14))
        ctk.CTkLabel(frame_proximas, text=T("cal_next_7"),
                     font=ctk.CTkFont(size=11, weight="bold"),
                     text_color=COLOR_YELLOW).pack(anchor="w", padx=10, pady=(8, 4))
        self.frame_proximas_scroll = ctk.CTkScrollableFrame(frame_proximas, fg_color="transparent",
                                                            height=120)
        self.frame_proximas_scroll.pack(fill="x", padx=4, pady=(0, 8))

        frame_der = ctk.CTkFrame(frame_main, fg_color=COLOR_CARD, corner_radius=14,
                                  border_width=1, border_color=COLOR_BORDER)
        frame_der.grid(row=0, column=1, sticky="nsew")

        self.lbl_fecha_sel = ctk.CTkLabel(frame_der,
                                           text=f"{T('cal_orders_today')} {date.today()}",
                                           font=ctk.CTkFont(size=14, weight="bold"),
                                           text_color=COLOR_TEXT)
        self.lbl_fecha_sel.pack(anchor="w", padx=16, pady=(14, 8))

        self.frame_pedidos_fecha = ctk.CTkScrollableFrame(frame_der, fg_color="transparent")
        self.frame_pedidos_fecha.pack(fill="both", expand=True, padx=8, pady=(0, 12))

    def _cargar_pedidos(self):
        self._todos_pedidos = db_manager.obtener_pedidos()
        self._mostrar_proximas()
        self._mostrar_pedidos_fecha(str(date.today()))
        if TkCalendar:
            self._marcar_fechas_calendario()

    def _marcar_fechas_calendario(self):
        if hasattr(self.cal, "calevent_remove"):
            try:
                self.cal.calevent_remove("all")
            except Exception:
                pass
        for p in self._todos_pedidos:
            if p.get("fecha_entrega") and p.get("estado") == "pendiente":
                try:
                    d = datetime.strptime(p["fecha_entrega"], "%Y-%m-%d")
                    self.cal.calevent_create(d.date(), p.get("cliente_nombre") or "Pedido",
                                             tags="entrega")
                except (ValueError, Exception):
                    pass
        try:
            self.cal.tag_config("entrega", background="#FFD166", foreground="#000000")
        except Exception:
            pass

    def _mostrar_proximas(self):
        for w in self.frame_proximas_scroll.winfo_children():
            w.destroy()
        pedidos_proximos = db_manager.obtener_pedidos_proximos(7)
        if not pedidos_proximos:
            ctk.CTkLabel(self.frame_proximas_scroll,
                         text=T("cal_no_upcoming"), text_color=COLOR_SUB,
                         font=ctk.CTkFont(size=11)).pack(pady=4)
            return
        for p in pedidos_proximos:
            f = ctk.CTkFrame(self.frame_proximas_scroll, fg_color="#1E1E1E", corner_radius=6)
            f.pack(fill="x", pady=2)
            ctk.CTkLabel(f, text=f"📦 {p.get('cliente_nombre') or '—'} – {p.get('fecha_entrega','')}",
                         font=ctk.CTkFont(size=10), text_color=COLOR_YELLOW,
                         anchor="w").pack(padx=8, pady=4, anchor="w")

    def _on_fecha_seleccionada(self, event=None):
        if TkCalendar and self.cal:
            fecha_sel = self.cal.selection_get()
            fecha_str = fecha_sel.strftime("%Y-%m-%d")
            self._mostrar_pedidos_fecha(fecha_str)

    def _mostrar_pedidos_fecha(self, fecha_str: str):
        self.lbl_fecha_sel.configure(text=f"{T('cal_orders_for')} {fecha_str}")
        for w in self.frame_pedidos_fecha.winfo_children():
            w.destroy()

        pedidos_fecha = [p for p in self._todos_pedidos if p.get("fecha_entrega") == fecha_str]

        if not pedidos_fecha:
            ctk.CTkLabel(self.frame_pedidos_fecha,
                         text=T("cal_no_deliveries"),
                         text_color=COLOR_SUB, font=ctk.CTkFont(size=12), justify="center"
                         ).pack(pady=40)
            return

        for p in pedidos_fecha:
            color_estado = {
                "pendiente": COLOR_YELLOW,
                "en proceso": COLOR_ACCENT,
                "completado": COLOR_ACCENT,
                "cancelado": COLOR_RED,
            }.get(p.get("estado", ""), COLOR_SUB)

            card = ctk.CTkFrame(self.frame_pedidos_fecha, fg_color="#252525", corner_radius=10)
            card.pack(fill="x", pady=4, padx=4)

            f_top = ctk.CTkFrame(card, fg_color="transparent")
            f_top.pack(fill="x", padx=12, pady=(10, 2))
            ctk.CTkLabel(f_top, text=f"#{p['id']}  {p.get('descripcion','')[:40]}",
                         font=ctk.CTkFont(size=13, weight="bold"), text_color=COLOR_TEXT,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(f_top, text=p.get("estado", ""),
                         font=ctk.CTkFont(size=11), text_color=color_estado,
                         anchor="e").pack(side="right")

            ctk.CTkLabel(card,
                         text=f"👤 {p.get('cliente_nombre') or '—'}   💰 ${p.get('precio_venta',0):.2f}",
                         font=ctk.CTkFont(size=11), text_color=COLOR_SUB,
                         anchor="w").pack(padx=12, pady=(0, 10), anchor="w")
