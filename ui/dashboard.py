# ui/dashboard.py – Vista del Dashboard principal
# Muestra KPIs del mes actual, gráfico de ganancias últimos 30 días y accesos rápidos

import customtkinter as ctk
from datetime import datetime
import db_manager
from utils.i18n import T

# Colores (coherentes con main.py)
COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_RED    = "#FF4C4C"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"


class KPICard(ctk.CTkFrame):
    """Tarjeta de KPI con título, valor y color de acento opcional."""

    def __init__(self, master, titulo, valor, subtitulo="", acento=COLOR_ACCENT, **kwargs):
        super().__init__(master, fg_color=COLOR_CARD, corner_radius=16, **kwargs)
        self.configure(border_width=1, border_color=COLOR_BORDER)

        ctk.CTkLabel(
            self, text=titulo,
            font=ctk.CTkFont(family="Segoe UI", size=12),
            text_color=COLOR_SUB
        ).pack(anchor="w", padx=18, pady=(16, 0))

        self.lbl_valor = ctk.CTkLabel(
            self, text=valor,
            font=ctk.CTkFont(family="Segoe UI", size=28, weight="bold"),
            text_color=acento
        )
        self.lbl_valor.pack(anchor="w", padx=18, pady=(2, 0))

        if subtitulo:
            ctk.CTkLabel(
                self, text=subtitulo,
                font=ctk.CTkFont(family="Segoe UI", size=11),
                text_color=COLOR_SUB
            ).pack(anchor="w", padx=18, pady=(0, 14))
        else:
            ctk.CTkFrame(self, height=14, fg_color="transparent").pack()

    def actualizar(self, valor, acento=None):
        """Actualiza el valor mostrado en la tarjeta."""
        self.lbl_valor.configure(text=valor)
        if acento:
            self.lbl_valor.configure(text_color=acento)


class DashboardView(ctk.CTkFrame):
    """Vista principal del Dashboard."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._construir_ui()

    def on_show(self):
        """Llamado cuando la vista se hace visible. Refresca los datos."""
        self._cargar_datos()

    def _construir_ui(self):
        """Construye el layout del dashboard."""
        # ── Encabezado ──
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))

        ahora = datetime.now()
        mes_nombre = ahora.strftime("%B %Y").capitalize()
        ctk.CTkLabel(
            frame_header,
            text=T("dash_title"),
            font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(side="left")

        ctk.CTkLabel(
            frame_header,
            text=mes_nombre,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_SUB
        ).pack(side="left", padx=12, pady=6)

        # Botón calculadora rápida
        ctk.CTkButton(
            frame_header,
            text=T("dash_quick_calc"),
            fg_color=COLOR_CARD,
            hover_color=COLOR_HOVER,
            text_color=COLOR_ACCENT,
            corner_radius=10,
            font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
            command=self._abrir_calculadora,
            width=170, height=36
        ).pack(side="right")

        # ── Tarjetas KPI ──
        frame_kpis = ctk.CTkFrame(self, fg_color="transparent")
        frame_kpis.pack(fill="x", padx=28, pady=18)

        # Las tarjetas se acomodan en una fila responsive
        for col in range(5):
            frame_kpis.columnconfigure(col, weight=1, uniform="kpi")

        self.card_ingresos = KPICard(frame_kpis, T("dash_income_month"), "$0.00",
                                     subtitulo=T("dash_income_sub"), acento=COLOR_TEXT)
        self.card_ingresos.grid(row=0, column=0, padx=6, pady=0, sticky="nsew")

        self.card_gastos = KPICard(frame_kpis, T("dash_expenses_month"), "$0.00",
                                   subtitulo=T("dash_expenses_sub"), acento=COLOR_RED)
        self.card_gastos.grid(row=0, column=1, padx=6, pady=0, sticky="nsew")

        self.card_ganancia = KPICard(frame_kpis, T("dash_profit"), "$0.00",
                                     subtitulo=T("dash_profit_sub"), acento=COLOR_ACCENT)
        self.card_ganancia.grid(row=0, column=2, padx=6, pady=0, sticky="nsew")

        self.card_margen = KPICard(frame_kpis, T("dash_margin"), "0%",
                                   subtitulo=T("dash_margin_sub"), acento=COLOR_TEXT)
        self.card_margen.grid(row=0, column=3, padx=6, pady=0, sticky="nsew")

        self.card_pendientes = KPICard(frame_kpis, T("dash_pending"), "0",
                                       subtitulo=T("dash_pending_sub"), acento="#FFD166")
        self.card_pendientes.grid(row=0, column=4, padx=6, pady=0, sticky="nsew")

        # ── Área inferior: gráfico + pedidos recientes ──
        frame_inferior = ctk.CTkFrame(self, fg_color="transparent")
        frame_inferior.pack(fill="both", expand=True, padx=28, pady=(0, 20))
        frame_inferior.columnconfigure(0, weight=3)
        frame_inferior.columnconfigure(1, weight=1)
        frame_inferior.rowconfigure(0, weight=1)

        # Gráfico de ganancias
        frame_grafico = ctk.CTkFrame(frame_inferior, fg_color=COLOR_CARD, corner_radius=16,
                                     border_width=1, border_color=COLOR_BORDER)
        frame_grafico.grid(row=0, column=0, padx=(0, 8), sticky="nsew")

        ctk.CTkLabel(
            frame_grafico,
            text=T("dash_chart_title"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", padx=18, pady=(14, 4))

        self.frame_canvas = ctk.CTkFrame(frame_grafico, fg_color="transparent")
        self.frame_canvas.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        # Panel lateral: pedidos recientes
        frame_recientes = ctk.CTkFrame(frame_inferior, fg_color=COLOR_CARD, corner_radius=16,
                                       border_width=1, border_color=COLOR_BORDER)
        frame_recientes.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(
            frame_recientes,
            text=T("dash_recent_orders"),
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            text_color=COLOR_TEXT
        ).pack(anchor="w", padx=14, pady=(14, 8))

        self.frame_pedidos_scroll = ctk.CTkScrollableFrame(
            frame_recientes, fg_color="transparent",
            scrollbar_button_color=COLOR_BORDER
        )
        self.frame_pedidos_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 10))

    def _cargar_datos(self):
        """Carga los datos de la base de datos y actualiza las KPI y gráfico."""
        ahora = datetime.now()
        stats = db_manager.obtener_estadisticas_mes(ahora.year, ahora.month)

        # Actualizar tarjetas
        self.card_ingresos.actualizar(f"${stats['ingresos']:,.2f}")
        self.card_gastos.actualizar(f"${stats['gastos']:,.2f}")
        ganancia = stats['ganancia_neta']
        color_gan = COLOR_ACCENT if ganancia >= 0 else COLOR_RED
        self.card_ganancia.actualizar(f"${ganancia:,.2f}", acento=color_gan)
        self.card_margen.actualizar(f"{stats['margen']:.1f}%")
        self.card_pendientes.actualizar(str(stats['pendientes']))

        # Gráfico
        self._dibujar_grafico()

        # Pedidos recientes
        self._cargar_pedidos_recientes()

    def _dibujar_grafico(self):
        """Dibuja el gráfico de líneas de ganancias de los últimos 30 días con Matplotlib."""
        # Lazy import de matplotlib (pesado)
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        # Limpiar canvas actual para evitar duplicados en re-entradas
        for w in self.frame_canvas.winfo_children():
            w.destroy()

        datos = db_manager.obtener_ganancia_ultimos_dias(30)

        fechas = [d["fecha"] for d in datos]
        ganancias = [d["ganancia"] for d in datos]

        fig, ax = plt.subplots(figsize=(7, 3), facecolor="#1E1E1E")
        ax.set_facecolor("#1E1E1E")

        if fechas:
            ax.plot(fechas, ganancias, color=COLOR_ACCENT, linewidth=2.5, marker="o",
                    markersize=5, markerfacecolor="#0F0F0F")
            ax.fill_between(fechas, ganancias, alpha=0.15, color=COLOR_ACCENT)
        else:
            ax.text(0.5, 0.5, T("dash_no_data"), ha="center", va="center",
                    color=COLOR_SUB, transform=ax.transAxes, fontsize=12)

        # Estilo del gráfico
        ax.tick_params(axis='x', rotation=45, labelsize=7, colors="#888888")
        ax.tick_params(axis='y', labelsize=8, colors="#888888")
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color("#333333")
        ax.spines['bottom'].set_color("#333333")
        ax.yaxis.label.set_color("#888888")
        for label in ax.get_xticklabels():
            label.set_color("#888888")
        plt.tight_layout(pad=1.0)

        # Embeber en CTk
        canvas = FigureCanvasTkAgg(fig, master=self.frame_canvas)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="both", expand=True)
        plt.close(fig)

    def _cargar_pedidos_recientes(self):
        """Muestra los últimos 8 pedidos en el panel lateral."""
        for widget in self.frame_pedidos_scroll.winfo_children():
            widget.destroy()

        # LIMIT 8 en SQL en vez de traer todos los pedidos y quedarse con los
        # 8 primeros en Python.
        pedidos = db_manager.obtener_pedidos(limite=8)
        for p in pedidos:
            frame_p = ctk.CTkFrame(self.frame_pedidos_scroll, fg_color="#252525", corner_radius=8)
            frame_p.pack(fill="x", pady=3, padx=2)

            ctk.CTkLabel(
                frame_p,
                text=f"{p.get('cliente_nombre','—') or '—'}",
                font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                text_color=COLOR_TEXT
            ).pack(anchor="w", padx=10, pady=(6, 0))

            ctk.CTkLabel(
                frame_p,
                text=f"${p.get('precio_venta', 0):.2f}  ·  {p.get('fecha','')}",
                font=ctk.CTkFont(family="Segoe UI", size=10),
                text_color=COLOR_SUB
            ).pack(anchor="w", padx=10, pady=(0, 6))

    def _abrir_calculadora(self):
        """Abre la ventana flotante de la calculadora."""
        self.app._abrir_calculadora()
