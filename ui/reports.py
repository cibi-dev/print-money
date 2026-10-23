# ui/reports.py – Vista de Reportes
# Genera gráficos de línea, pastel y barras. Exporta a Excel y PDF.

import threading
import customtkinter as ctk
from tkinter import filedialog, messagebox
from datetime import datetime, date
import db_manager
from ui import components as ui
from ui import theme as th
from utils.export import exportar_excel, exportar_pdf_reporte
from utils.i18n import T

_GRAFICO = {"rejilla": "#2A2A2A", "ejes": "#333333"}
_PALETA = [th.ACCENT, th.YELLOW, th.RED, "#74B9FF", "#A29BFE",
           "#FD79A8", "#00CEC9", "#FDCB6E"]


class ReportsView(ctk.CTkFrame):
    """Vista de reportes con múltiples gráficos y opciones de exportación."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=th.BG, corner_radius=0, **kwargs)
        self.app = app
        self._año_actual = datetime.now().year
        self._firma_datos = None
        self._construir_ui()

    def on_show(self):
        self._actualizar_graficos()

    def _construir_ui(self):
        _frame_header, acciones = ui.page_header(self, T("reports_title"))

        años = [str(y) for y in range(2023, datetime.now().year + 2)]
        self.combo_año = ui.option_menu(acciones, values=años, width=100,
                                        command=lambda _: self._actualizar_graficos())
        self.combo_año.set(str(self._año_actual))
        self.combo_año.pack(side="right", padx=(6, 0))
        ctk.CTkLabel(acciones, text=T("reports_year"), text_color=th.SUB,
                     font=th.fuente(th.FONT_BODY)).pack(side="right")

        ui.secondary_button(acciones, T("reports_pdf"), self._exportar_pdf,
                            width=150).pack(side="right", padx=(0, th.GAP))
        ui.secondary_button(acciones, T("reports_excel"), self._exportar_excel,
                            width=160).pack(side="right")

        self.frame_graficos = ui.scrollable(self)
        self.frame_graficos.pack(fill="both", expand=True, padx=th.PAD_PAGE, pady=14)

    def _actualizar_graficos(self):
        año = int(self.combo_año.get())

        # Recoger los datos primero para poder compararlos con lo que ya se
        # está mostrando. Si no ha cambiado nada, no se rehacen los gráficos:
        # crear las 3 figuras de matplotlib costaba ~250 ms y se repetía cada
        # vez que el usuario volvía a la vista.
        ingresos_mes = db_manager.obtener_ingresos_por_mes(año)
        gastos_cat = db_manager.obtener_gastos_por_categoria()
        ganancia_dias = db_manager.obtener_ganancia_ultimos_dias(30)
        resumen = db_manager.obtener_resumen_anual(año)

        firma = (
            año,
            tuple((d["mes"], d["total"]) for d in ingresos_mes),
            tuple((d["nombre"], d["total"]) for d in gastos_cat),
            tuple((d["fecha"], d["ganancia"]) for d in ganancia_dias),
            tuple(sorted(resumen.items())),
        )
        if firma == self._firma_datos:
            return
        self._firma_datos = firma

        for w in self.frame_graficos.winfo_children():
            w.destroy()

        meses = T("months_short")

        frame_bar = ui.card(self.frame_graficos)
        frame_bar.pack(fill="x", pady=(0, 14))
        ui.section_title(frame_bar, f"{T('reports_income_chart')} – {año}").pack(
            anchor="w", padx=16, pady=(12, 4))
        self._grafico_barras_ingresos(frame_bar, ingresos_mes, meses)

        frame_pie = ui.card(self.frame_graficos)
        frame_pie.pack(fill="x", pady=(0, 14))
        ui.section_title(frame_pie, T("reports_expenses_chart")).pack(
            anchor="w", padx=16, pady=(12, 4))
        self._grafico_pastel_gastos(frame_pie, gastos_cat)

        frame_line = ui.card(self.frame_graficos)
        frame_line.pack(fill="x", pady=(0, 14))
        ui.section_title(frame_line, T("reports_profit_chart")).pack(
            anchor="w", padx=16, pady=(12, 4))
        self._grafico_ganancia_linea(frame_line, ganancia_dias)

        self._renderizar_resumen(año, resumen)

    def _estilo_ax(self, ax, fig):
        fig.patch.set_facecolor(th.CARD)
        ax.set_facecolor(th.CARD)
        ax.set_axisbelow(True)
        ax.grid(axis="y", color=_GRAFICO["rejilla"], alpha=0.6, linewidth=0.8)
        ax.tick_params(colors=th.SUB, labelsize=8, length=0)
        for etiqueta in ax.get_xticklabels() + ax.get_yticklabels():
            etiqueta.set_fontfamily("Segoe UI")
            etiqueta.set_fontsize(8)
            etiqueta.set_color(th.SUB)
        for etiqueta in (ax.xaxis.label, ax.yaxis.label):
            etiqueta.set_fontfamily("Segoe UI")
            etiqueta.set_fontsize(9)
            etiqueta.set_color(th.SUB)
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        ax.spines['left'].set_color(_GRAFICO["ejes"])
        ax.spines['bottom'].set_color(_GRAFICO["ejes"])

    def _grafico_barras_ingresos(self, parent, datos, meses):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        ingresos = [0] * 12
        for d in datos:
            mes_idx = int(d["mes"]) - 1
            ingresos[mes_idx] = d["total"]

        fig, ax = plt.subplots(figsize=(9, 3))
        colores = [th.ACCENT if v > 0 else th.BORDER for v in ingresos]
        ax.bar(meses, ingresos, color=colores, width=0.6, edgecolor="none")
        ax.set_ylabel(T("reports_income_label"), fontsize=9)
        if not any(ingresos):
            ax.set_ylim(0, 1)
            ax.set_yticks([])
            ax.text(0.5, 0.5, T("reports_no_data"), ha="center", va="center",
                    color=th.SUB, transform=ax.transAxes, fontsize=12,
                    fontfamily="Segoe UI")
        self._estilo_ax(ax, fig)
        plt.tight_layout(pad=1.0)

        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0, 10))
        plt.close(fig)

    def _grafico_pastel_gastos(self, parent, datos):
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        datos = [d for d in datos if d["total"] > 0]

        fig, ax = plt.subplots(figsize=(6, 3.2))

        if datos:
            labels = [d["nombre"] for d in datos]
            values = [d["total"] for d in datos]
            wedges, texts, autotexts = ax.pie(
                values, labels=labels, autopct='%1.1f%%',
                colors=_PALETA[:len(values)],
                textprops={'color': th.TEXT, 'fontsize': 9,
                           'fontfamily': 'Segoe UI'},
                startangle=90
            )
            for at in autotexts:
                at.set_color(th.BG)
                at.set_fontweight("bold")
        else:
            ax.text(0.5, 0.54, T("reports_no_expenses"), ha="center", va="center",
                    color=th.SUB, transform=ax.transAxes, fontsize=13,
                    fontfamily="Segoe UI")
            ax.text(0.5, 0.42, T("reports_no_expenses_hint"), ha="center",
                    va="center", color=th.SUB_DIM, transform=ax.transAxes,
                    fontsize=9, fontfamily="Segoe UI")

        self._estilo_ax(ax, fig)
        ax.axis("off")

        plt.tight_layout(pad=0.5)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0, 10))
        plt.close(fig)

    def _grafico_ganancia_linea(self, parent, datos):
        import matplotlib.dates as mdates
        import matplotlib.pyplot as plt
        from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

        fig, ax = plt.subplots(figsize=(9, 3))

        if datos:
            fechas = [datetime.strptime(d["fecha"], "%Y-%m-%d").date() for d in datos]
            ganancias = [d["ganancia"] for d in datos]
            ax.plot(fechas, ganancias, color=th.ACCENT, linewidth=2.2,
                    marker="o", markersize=4, markerfacecolor=th.BG,
                    markeredgecolor=th.ACCENT)
            ax.fill_between(fechas, ganancias, 0, alpha=0.15, color=th.ACCENT,
                            linewidth=0)
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m"))
            ax.xaxis.set_major_locator(mdates.AutoDateLocator(minticks=3, maxticks=10))
            ax.margins(x=0.01)
            for etiqueta in ax.get_xticklabels():
                etiqueta.set_rotation(45)
                etiqueta.set_ha("right")
            ax.set_ylabel(T("reports_profit_label"), fontsize=9)
        else:
            ax.text(0.5, 0.5, T("reports_no_data"), ha="center", va="center",
                    color=th.SUB, transform=ax.transAxes, fontsize=12,
                    fontfamily="Segoe UI")

        self._estilo_ax(ax, fig)
        plt.tight_layout(pad=1.0)
        canvas = FigureCanvasTkAgg(fig, master=parent)
        canvas.draw()
        canvas.get_tk_widget().pack(fill="x", padx=10, pady=(0, 10))
        plt.close(fig)

    def _renderizar_resumen(self, año, resumen):
        frame_resumen = ui.card(self.frame_graficos)
        frame_resumen.pack(fill="x", pady=(0, 14))
        ui.section_title(frame_resumen, f"{T('reports_summary')} {año}").pack(
            anchor="w", padx=16, pady=(12, 8))

        frame_stats = ctk.CTkFrame(frame_resumen, fg_color="transparent")
        frame_stats.pack(fill="x", padx=16, pady=(0, 16))

        # El resumen viene de una sola consulta agregada del año. Antes se
        # llamaba a obtener_estadisticas_mes() 24 veces (12 meses x 2 métricas),
        # es decir 24 conexiones y 120 consultas para pintar 4 números.
        total_ingresos = resumen["ingresos"]
        total_gastos = resumen["gastos"]
        ganancia = resumen["ganancia_neta"]
        margen = resumen["margen"]

        stats = [
            (T("reports_total_income"), f"${total_ingresos:,.2f}", th.TEXT),
            (T("reports_total_expenses"), f"${total_gastos:,.2f}", th.RED),
            (T("reports_net_profit"), f"${ganancia:,.2f}",
             th.ACCENT if ganancia >= 0 else th.RED),
            (T("reports_avg_margin"), f"{margen:.1f}%", th.TEXT),
        ]
        for titulo, valor, color in stats:
            tarjeta = ui.card(frame_stats, corner_radius=th.RADIUS_CTRL)
            tarjeta.pack(side="left", expand=True, fill="x", padx=4)
            ui.section_label(tarjeta, titulo).pack(anchor="w", padx=14, pady=(10, 0))
            ctk.CTkLabel(tarjeta, text=valor, text_color=color,
                         font=th.fuente(17, True), anchor="w").pack(
                             anchor="w", padx=14, pady=(0, 12))

    def _exportar_excel(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"reporte_{self.combo_año.get()}.xlsx"
        )
        if ruta:
            año = int(self.combo_año.get())

            def _worker():
                try:
                    exportar_excel(ruta, año)
                    self.after(0, lambda: messagebox.showinfo(
                        T("reports_export_ok"),
                        T("reports_excel_ok", path=ruta),
                        parent=self.winfo_toplevel()
                    ))
                except Exception as e:
                    self.after(0, lambda err=str(e): messagebox.showerror(
                        T("error"),
                        err,
                        parent=self.winfo_toplevel()
                    ))

            threading.Thread(target=_worker, daemon=True).start()

    def _exportar_pdf(self):
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile=f"reporte_{self.combo_año.get()}.pdf"
        )
        if ruta:
            año = int(self.combo_año.get())

            def _worker():
                try:
                    exportar_pdf_reporte(ruta, año)
                    self.after(0, lambda: messagebox.showinfo(
                        T("reports_export_ok"),
                        T("reports_pdf_ok", path=ruta),
                        parent=self.winfo_toplevel()
                    ))
                except Exception as e:
                    self.after(0, lambda err=str(e): messagebox.showerror(
                        T("error"),
                        err,
                        parent=self.winfo_toplevel()
                    ))

            threading.Thread(target=_worker, daemon=True).start()
