# ui/dashboard.py – Vista del Dashboard principal
# Muestra KPIs del mes actual, gráfico de ganancias últimos 30 días y accesos rápidos

import customtkinter as ctk
from datetime import datetime
import db_manager
from ui import components as ui
from ui.components import KPICard
from ui import theme as th
from utils.i18n import T, get_idioma

try:
    from babel.dates import format_date as _format_date
except ImportError:
    _format_date = None

_GRAFICO = {"rejilla": "#2A2A2A", "ejes": "#333333"}


def _mes_actual():
    ahora = datetime.now()
    if _format_date:
        try:
            locale = "es_ES" if get_idioma() == "es" else "en_US"
            texto = _format_date(ahora, "MMMM yyyy", locale=locale)
            return texto[:1].upper() + texto[1:]
        except Exception:
            pass
    return ahora.strftime("%B %Y").capitalize()


class DashboardView(ctk.CTkFrame):
    """Vista principal del Dashboard."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._firma_grafico = None
        self._firma_pedidos = None
        self._grafico_after = None
        self._construir_ui()

    def on_show(self):
        """Llamado cuando la vista se hace visible. Refresca los datos."""
        self._cargar_datos()

    def _construir_ui(self):
        """Construye el layout del dashboard."""
        # ── Encabezado ──
        mes_nombre = _mes_actual()
        _frame_header, acciones = ui.page_header(self, T("dash_title"),
                                                 subtitulo=mes_nombre)

        # Botón calculadora rápida
        ui.secondary_button(acciones, T("dash_quick_calc"), self._abrir_calculadora,
                            width=180, text_color=th.ACCENT).pack(side="right")

        # ── Tarjetas KPI ──
        frame_kpis = ctk.CTkFrame(self, fg_color="transparent")
        frame_kpis.pack(fill="x", padx=th.PAD_PAGE, pady=18)

        # Las tarjetas se acomodan en una fila responsive
        for col in range(5):
            frame_kpis.columnconfigure(col, weight=1, uniform="kpi")

        self.card_ingresos = KPICard(frame_kpis, T("dash_income_month"), "$0.00",
                                     subtitulo=T("dash_income_sub"), acento=th.TEXT)
        self.card_ingresos.grid(row=0, column=0, padx=6, pady=0, sticky="nsew")

        self.card_gastos = KPICard(frame_kpis, T("dash_expenses_month"), "$0.00",
                                   subtitulo=T("dash_expenses_sub"), acento=th.RED)
        self.card_gastos.grid(row=0, column=1, padx=6, pady=0, sticky="nsew")

        self.card_ganancia = KPICard(frame_kpis, T("dash_profit"), "$0.00",
                                     subtitulo=T("dash_profit_sub"), acento=th.ACCENT)
        self.card_ganancia.grid(row=0, column=2, padx=6, pady=0, sticky="nsew")

        self.card_margen = KPICard(frame_kpis, T("dash_margin"), "0%",
                                   subtitulo=T("dash_margin_sub"), acento=th.TEXT)
        self.card_margen.grid(row=0, column=3, padx=6, pady=0, sticky="nsew")

        self.card_pendientes = KPICard(frame_kpis, T("dash_pending"), "0",
                                       subtitulo=T("dash_pending_sub"), acento=th.YELLOW)
        self.card_pendientes.grid(row=0, column=4, padx=6, pady=0, sticky="nsew")

        # ── Área inferior: gráfico + pedidos recientes ──
        frame_inferior = ctk.CTkFrame(self, fg_color="transparent")
        frame_inferior.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=(0, 20))
        frame_inferior.columnconfigure(0, weight=3)
        frame_inferior.columnconfigure(1, weight=1)
        frame_inferior.rowconfigure(0, weight=1)

        # Gráfico de ganancias
        frame_grafico = ui.card(frame_inferior)
        frame_grafico.grid(row=0, column=0, padx=(0, th.GAP), sticky="nsew")

        ui.section_title(frame_grafico, T("dash_chart_title")).pack(
            anchor="w", padx=18, pady=(14, 4))

        self.frame_canvas = ctk.CTkFrame(frame_grafico, fg_color="transparent")
        self.frame_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Panel lateral: pedidos recientes
        frame_recientes = ui.card(frame_inferior)
        frame_recientes.grid(row=0, column=1, sticky="nsew")

        ui.section_title(frame_recientes, T("dash_recent_orders")).pack(
            anchor="w", padx=16, pady=(14, 8))

        self.frame_pedidos_scroll = ui.scrollable(frame_recientes)
        self.frame_pedidos_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 10))

    def _cargar_datos(self):
        """Carga los datos de la base de datos y actualiza las KPI y gráfico."""
        ahora = datetime.now()
        stats = db_manager.obtener_estadisticas_mes(ahora.year, ahora.month)

        # Actualizar tarjetas
        self.card_ingresos.actualizar(f"${stats['ingresos']:,.2f}")
        self.card_gastos.actualizar(f"${stats['gastos']:,.2f}")
        ganancia = stats['ganancia_neta']
        color_gan = th.ACCENT if ganancia >= 0 else th.RED
        self.card_ganancia.actualizar(f"${ganancia:,.2f}", acento=color_gan)
        self.card_margen.actualizar(f"{stats['margen']:.1f}%",
                                    acento=th.TEXT if stats['margen'] >= 0 else th.RED)
        self.card_pendientes.actualizar(str(stats['pendientes']))

        # Gráfico: se difiere para que la ventana aparezca antes de importar
        # matplotlib y dibujar. En el arranque, navegar("dashboard") se ejecuta
        # antes del primer frame.
        self._programar_grafico()

        # Pedidos recientes
        self._cargar_pedidos_recientes()

    def _programar_grafico(self):
        """Programa el dibujo del gráfico para después del primer pintado."""
        if self._grafico_after is not None:
            try:
                self.after_cancel(self._grafico_after)
            except Exception:
                pass
        self._grafico_after = self.after(60, self._renderizar_grafico)

    def _renderizar_grafico(self):
        self._grafico_after = None
        self._dibujar_grafico()

    def destroy(self):
        if self._grafico_after is not None:
            try:
                self.after_cancel(self._grafico_after)
            except Exception:
                pass
            self._grafico_after = None
        super().destroy()

    def _dibujar_grafico(self):
        """Dibuja el gráfico de líneas de ganancias de los últimos 30 días con Matplotlib."""
        datos = db_manager.obtener_ganancia_ultimos_dias(30)
        firma = tuple((d["fecha"], d["ganancia"]) for d in datos)
        if firma == self._firma_grafico:
            return
        self._firma_grafico = firma

        # Limpiar canvas actual para evitar duplicados en re-entradas
        for w in self.frame_canvas.winfo_children():
            w.destroy()

        if not datos:
            ui.empty_state(self.frame_canvas, "📈", T("dash_no_data"),
                           hint=T("dash_no_data_hint"))
            return

        # Lazy import de matplotlib (pesado): solo cuando hay datos que pintar
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        fechas = [datetime.strptime(d["fecha"], "%Y-%m-%d").date() for d in datos]
        ganancias = [d["ganancia"] for d in datos]

        estilo = {
            "font.family": "Segoe UI",
            "font.size": 8,
            "axes.labelsize": 8,
            "axes.titlesize": 9,
            "xtick.labelsize": 8,
            "ytick.labelsize": 8,
            "axes.edgecolor": _GRAFICO["ejes"],
            "axes.labelcolor": th.SUB,
            "text.color": th.SUB,
            "xtick.color": th.SUB,
            "ytick.color": th.SUB,
            "figure.facecolor": th.CARD,
            "axes.facecolor": th.CARD,
            "grid.color": _GRAFICO["rejilla"],
            "grid.alpha": 0.6,
        }

        with plt.rc_context(estilo):
            fig, ax = plt.subplots(figsize=(7, 3))
            fig.patch.set_facecolor(th.CARD)
            ax.set_facecolor(th.CARD)

            ax.plot(fechas, ganancias, color=th.ACCENT, linewidth=2.2, marker="o",
                    markersize=4, markerfacecolor=th.BG, markeredgecolor=th.ACCENT)
            ax.fill_between(fechas, ganancias, 0, alpha=0.15, color=th.ACCENT,
                            linewidth=0)

            ax.set_axisbelow(True)
            ax.grid(axis="y", color=_GRAFICO["rejilla"], alpha=0.6, linewidth=0.8)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(_GRAFICO["ejes"])
            ax.spines["bottom"].set_color(_GRAFICO["ejes"])
            ax.tick_params(axis="both", labelsize=8, colors=th.SUB, length=0)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=8))
            ax.margins(x=0.01)
            fig.tight_layout(pad=0.8)

            canvas = FigureCanvasTkAgg(fig, master=self.frame_canvas)
            canvas.draw()
            canvas.get_tk_widget().pack(fill="both", expand=True)
            plt.close(fig)

    def _cargar_pedidos_recientes(self):
        """Muestra los últimos 8 pedidos en el panel lateral."""
        # LIMIT 8 en SQL en vez de traer todos los pedidos y quedarse con los
        # 8 primeros en Python.
        pedidos = db_manager.obtener_pedidos(limite=8)
        firma = tuple((p["id"], p.get("fecha"), p.get("precio_venta"),
                       p.get("estado"), p.get("descripcion")) for p in pedidos)
        if firma == self._firma_pedidos:
            return
        self._firma_pedidos = firma

        for widget in self.frame_pedidos_scroll.winfo_children():
            widget.destroy()

        if not pedidos:
            ui.empty_state(self.frame_pedidos_scroll, "🧾", T("dash_no_recent"),
                           hint=T("dash_no_recent_hint"), empaquetar=True)
            return

        for p in pedidos:
            fila = ctk.CTkFrame(self.frame_pedidos_scroll, fg_color=th.SURFACE,
                                corner_radius=th.RADIUS_INPUT)
            fila.pack(fill="x", padx=2, pady=3)

            cabecera = ctk.CTkFrame(fila, fg_color="transparent")
            cabecera.pack(fill="x", padx=12, pady=(8, 0))
            ctk.CTkLabel(cabecera, text=f"{p.get('cliente_nombre') or '—'}",
                         font=th.fuente(th.FONT_BODY, True), text_color=th.TEXT,
                         anchor="w").pack(side="left")
            ctk.CTkLabel(cabecera, text=f"${(p.get('precio_venta') or 0):,.2f}",
                         font=th.fuente(th.FONT_BODY, True), text_color=th.ACCENT,
                         anchor="e").pack(side="right")

            pie = ctk.CTkFrame(fila, fg_color="transparent")
            pie.pack(fill="x", padx=12, pady=(2, 8))
            descripcion = (p.get("descripcion") or "").strip() or "—"
            if len(descripcion) > 26:
                descripcion = descripcion[:25] + "…"
            ctk.CTkLabel(pie, text=descripcion, font=th.fuente(10),
                         text_color=th.SUB, anchor="w").pack(side="left")
            ui.status_pill(pie, p.get("estado") or "", width=78).pack(side="right")

            for contenedor in (fila, cabecera, pie):
                for widget in [contenedor] + contenedor.winfo_children():
                    widget.bind("<Button-1>",
                                lambda _e, pid=p["id"]: self._ir_a_pedido(pid))

    def _ir_a_pedido(self, pedido_id):
        """Navega a Pedidos y, si la vista ya existe, la deja con ese pedido abierto."""
        navegar = getattr(self.app, "navegar", None)
        if not callable(navegar):
            return
        navegar("pedidos")
        cache = getattr(self.app, "_cache_vistas", None)
        vista = cache.get("pedidos") if isinstance(cache, dict) else None
        if vista is not None and hasattr(vista, "_seleccionar_pedido"):
            try:
                vista._seleccionar_pedido(pedido_id)
            except Exception:
                pass

    def _abrir_calculadora(self):
        """Abre la ventana flotante de la calculadora."""
        self.app._abrir_calculadora()
