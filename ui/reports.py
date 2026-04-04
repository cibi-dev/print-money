# ui/reports.py – Vista de Reportes
# Genera gráficos de línea, pastel y barras. Exporta a Excel y PDF.

import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime, date
import db_manager
from utils.export import exportar_excel, exportar_pdf_reporte
from utils.i18n import T

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_RED    = "#FF4C4C"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"


class ReportsView(ctk.CTkFrame):
    """Vista de reportes con múltiples gráficos y opciones de exportación."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self._año_actual = datetime.now().year
        self._construir_ui()

    def on_show(self):
        self._actualizar_graficos()

    def _construir_ui(self):
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("reports_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")

        años = [str(y) for y in range(2023, datetime.now().year + 2)]
        self.combo_año = ctk.CTkOptionMenu(
            frame_header, values=años,
            fg_color=COLOR_CARD, button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            width=100, height=36, command=lambda _: self._actualizar_graficos()
        )
        self.combo_año.set(str(self._año_actual))
        self.combo_año.pack(side="right", padx=(6, 0))
        ctk.CTkLabel(frame_header, text=T("reports_year"), text_color=COLOR_SUB,
                     font=ctk.CTkFont(size=12)).pack(side="right")

        ctk.CTkButton(frame_header, text=T("reports_excel"),
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_TEXT, corner_radius=10, height=36, width=140,
                      command=self._exportar_excel).pack(side="right", padx=(0, 8))
        ctk.CTkButton(frame_header, text=T("reports_pdf"),
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_TEXT, corner_radius=10, height=36, width=130,
                      command=self._exportar_pdf).pack(side="right", padx=(0, 4))

        self.frame_graficos = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.frame_graficos.pack(fill="both", expand=True, padx=28, pady=14)

    def _actualizar_graficos(self):
        for w in self.frame_graficos.winfo_children():
            w.destroy()

        año = int(self.combo_año.get())
        meses = T("months_short")

        frame_bar = ctk.CTkFrame(self.frame_graficos, fg_color=COLOR_CARD,
                                  corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        frame_bar.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(frame_bar, text=f"{T('reports_income_chart')} – {año}",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(12, 4))
        self._grafico_barras_ingresos(frame_bar, año, meses)

        frame_pie = ctk.CTkFrame(self.frame_graficos, fg_color=COLOR_CARD,
                                  corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        frame_pie.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(frame_pie, text=T("reports_expenses_chart"),
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(12, 4))
        self._grafico_pastel_gastos(frame_pie)

        frame_line = ctk.CTkFrame(self.frame_graficos, fg_color=COLOR_CARD,
                                   corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        frame_line.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(frame_line, text=T("reports_profit_chart"),
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(12, 4))
        self._grafico_ganancia_linea(frame_line)

        self._renderizar_resumen(año)

    def _estilo_ax(self, ax, fig):
        fig.patch.set_facecolor("#1E1E1E")
        ax.set_facecolor("#1E1E1E")
        ax.tick_params(colors="#888888", labelsize=8)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color("#333333")
        ax.spines['bottom'].set_color("#333333")

    def _grafico_barras_ingresos(self, parent, año, meses):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        datos = db_manager.obtener_ingresos_por_mes(año)
        ingresos = [0] * 12
        for d in datos:
            mes_idx = int(d["mes"]) - 1
            ingresos[mes_idx] = d["total"]

        fig, ax = plt.subplots(figsize=(9, 3), facecolor="#1E1E1E")
        self._estilo_ax(ax, fig)
        colores = [COLOR_ACCENT if v > 0 else "#333333" for v in ingresos]
        bars = ax.bar(meses, ingresos, color=colores, width=0.6, edgecolor="none")
        ax.set_ylabel(T("reports_income_label"), color="#888888", fontsize=9)
        plt.tight_layout(pad=1.0)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0, 10))
        plt.close(fig)

    def _grafico_pastel_gastos(self, parent):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        datos = db_manager.obtener_gastos_por_categoria()
        datos = [d for d in datos if d["total"] > 0]

        fig, ax = plt.subplots(figsize=(6, 3.5), facecolor="#1E1E1E")
        self._estilo_ax(ax, fig)
        ax.axis("off")

        if datos:
            labels = [d["nombre"] for d in datos]
            values = [d["total"] for d in datos]
            paleta = ["#00FF9D", "#FFD166", "#FF4C4C", "#74B9FF", "#A29BFE",
                      "#FD79A8", "#00CEC9", "#FDCB6E"]
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=paleta[:len(values)],
                textprops={'color': '#CCCCCC', 'fontsize': 9},
                startangle=90
            )
            for at in autotexts:
                at.set_color("#0F0F0F"); at.set_fontweight("bold")
        else:
            ax.text(0.5, 0.5, T("reports_no_expenses"), ha="center", va="center",
                    color=COLOR_SUB, transform=ax.transAxes, fontsize=12)

        plt.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0, 10))
        plt.close(fig)

    def _grafico_ganancia_linea(self, parent):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        datos = db_manager.obtener_ganancia_ultimos_dias(30)
        fechas = [d["fecha"] for d in datos]
        ganancias = [d["ganancia"] for d in datos]

        fig, ax = plt.subplots(figsize=(9, 3), facecolor="#1E1E1E")
        self._estilo_ax(ax, fig)
        if fechas:
            ax.plot(fechas, ganancias, color=COLOR_ACCENT, linewidth=2.5,
                    marker="o", markersize=5, markerfacecolor="#0F0F0F")
            ax.fill_between(fechas, ganancias, alpha=0.15, color=COLOR_ACCENT)
        else:
            ax.text(0.5, 0.5, T("reports_no_data"), ha="center", va="center",
                    color=COLOR_SUB, transform=ax.transAxes, fontsize=12)

        ax.tick_params(axis='x', rotation=40, labelsize=7)
        ax.set_ylabel(T("reports_profit_label"), color="#888888", fontsize=9)
        plt.tight_layout(pad=1.0)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0, 10))
        plt.close(fig)

    def _renderizar_resumen(self, año):
        frame_resumen = ctk.CTkFrame(self.frame_graficos, fg_color=COLOR_CARD,
                                     corner_radius=14, border_width=1, border_color=COLOR_BORDER)
        frame_resumen.pack(fill="x", pady=(0, 14))
        ctk.CTkLabel(frame_resumen, text=f"{T('reports_summary')} {año}",
                     font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(12, 8))

        frame_stats = ctk.CTkFrame(frame_resumen, fg_color="transparent")
        frame_stats.pack(fill="x", padx=16, pady=(0, 16))

        total_ingresos = sum(
            db_manager.obtener_estadisticas_mes(año, m)["ingresos"] for m in range(1, 13)
        )
        total_gastos = sum(
            db_manager.obtener_estadisticas_mes(año, m)["gastos"] for m in range(1, 13)
        )
        ganancia = total_ingresos - total_gastos
        margen = (ganancia / total_ingresos * 100) if total_ingresos > 0 else 0

        stats = [
            (T("reports_total_income"), f"${total_ingresos:,.2f}", COLOR_TEXT),
            (T("reports_total_expenses"), f"${total_gastos:,.2f}", COLOR_RED),
            (T("reports_net_profit"), f"${ganancia:,.2f}", COLOR_ACCENT if ganancia >= 0 else COLOR_RED),
            (T("reports_avg_margin"), f"{margen:.1f}%", COLOR_TEXT),
        ]
        for titulo, valor, color in stats:
            f = ctk.CTkFrame(frame_stats, fg_color="#252525", corner_radius=10)
            f.pack(side="left", expand=True, fill="x", padx=4)
            ctk.CTkLabel(f, text=titulo, text_color=COLOR_SUB,
                         font=ctk.CTkFont(size=11)).pack(pady=(8, 2))
            ctk.CTkLabel(f, text=valor, text_color=color,
                         font=ctk.CTkFont(size=16, weight="bold")).pack(pady=(0, 10))

    def _exportar_excel(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"reporte_{self.combo_año.get()}.xlsx"
        )
        if ruta:
            try:
                exportar_excel(ruta, int(self.combo_año.get()))
                messagebox.showinfo(T("reports_export_ok"), T("reports_excel_ok", path=ruta))
            except Exception as e:
                messagebox.showerror(T("error"), str(e))

    def _exportar_pdf(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"reporte_{self.combo_año.get()}.pdf"
        )
        if ruta:
            try:
                exportar_pdf_reporte(ruta, int(self.combo_año.get()))
                messagebox.showinfo(T("reports_export_ok"), T("reports_pdf_ok", path=ruta))
            except Exception as e:
                messagebox.showerror(T("error"), str(e))
