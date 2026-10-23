# ui/calculator.py – Ventana flotante de calculadora de costos
# Se puede abrir desde el Dashboard o la barra lateral y queda independiente

import customtkinter as ctk
import db_manager
from utils.i18n import T
from utils.labels import mapa_por_etiqueta
from ui import theme as th
from ui import components as ui


def _sin_dos_puntos(texto):
    return texto[:-1] if texto.endswith(":") else texto


class CalculatorWindow(ctk.CTkToplevel):
    """Ventana flotante de calculadora de costo para impresión 3D."""

    def __init__(self, master):
        super().__init__(master)
        self.title(T("calc_title"))
        self.geometry("420x760")
        self.resizable(False, True)
        self.configure(fg_color=th.BG)
        self.attributes("-topmost", True)

        # Cargar configuración del app padre
        self.tarifa_default = getattr(master, 'config_data', {}).get("tarifa_por_hora", 5.0)
        self.margen_default = getattr(master, 'config_data', {}).get("margen_objetivo", 40.0)
        self.app = master

        self._construir_ui()
        self._cargar_filamentos()

    def _construir_ui(self):
        header = ctk.CTkFrame(self, fg_color="transparent")
        header.pack(fill="x", padx=20, pady=(16, 2))
        ctk.CTkLabel(header, text="⚡", font=th.fuente(22, True),
                     text_color=th.ACCENT).pack(side="left")
        ctk.CTkLabel(header, text=T("calc_heading"),
                     font=th.fuente(20, True),
                     text_color=th.TEXT).pack(side="left", padx=(8, 0))

        ctk.CTkLabel(self, text=T("calc_subtitle"), font=th.fuente(11),
                     text_color=th.SUB).pack(anchor="w", padx=20)

        ui.divider(self).pack(fill="x", padx=20, pady=(10, 6))

        scroll = ui.scrollable(self, corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=16, pady=0)

        card_datos = ui.card(scroll)
        card_datos.pack(fill="x", pady=(0, 8))

        ui.section_title(card_datos, T("calc_form_section")).pack(
            anchor="w", padx=14, pady=(12, 6))

        ui.section_label(card_datos, T("calc_filament")).pack(
            anchor="w", padx=14, pady=(4, 2))
        self.combo_filamento = ui.option_menu(card_datos, values=[T("calc_select")])
        self.combo_filamento.pack(fill="x", padx=14)

        grid = ctk.CTkFrame(card_datos, fg_color="transparent")
        grid.pack(fill="x", padx=14, pady=(2, 0))
        grid.columnconfigure(0, weight=1, uniform="calc")
        grid.columnconfigure(1, weight=1, uniform="calc")

        def celda(fila, columna, etiqueta, atributo, placeholder, valor=None):
            marco = ctk.CTkFrame(grid, fg_color="transparent")
            marco.grid(row=fila, column=columna, sticky="ew",
                       padx=(0, 4) if columna == 0 else (4, 0), pady=(6, 0))
            ui.section_label(marco, etiqueta).pack(anchor="w", pady=(0, 2))
            entrada = ui.entry(marco, placeholder)
            entrada.pack(fill="x")
            if valor is not None:
                entrada.insert(0, str(valor))
            entrada.bind("<KeyRelease>", lambda e: self._calcular())
            setattr(self, atributo, entrada)

        celda(0, 0, T("calc_grams"), "entry_gramos", "100")
        celda(0, 1, T("calc_hours"), "entry_horas", "2.5")
        celda(1, 0, T("calc_rate"), "entry_tarifa", "5.0", self.tarifa_default)
        celda(1, 1, T("calc_margin"), "entry_margen", "40", self.margen_default)

        self.var_incluir_tiempo = ctk.BooleanVar(value=True)
        ui.checkbox(card_datos, T("calc_include_time"),
                    self.var_incluir_tiempo,
                    command=self._calcular).pack(anchor="w", padx=14, pady=(12, 12))

        card_res = ui.card(scroll)
        card_res.pack(fill="x", pady=(0, 8))
        ui.section_title(card_res, T("calc_results_title")).pack(
            anchor="w", padx=14, pady=(12, 6))

        def res_row(texto, atributo):
            fila = ctk.CTkFrame(card_res, fg_color="transparent")
            fila.pack(fill="x", padx=14, pady=4)
            ui.section_label(fila, texto).pack(side="left")
            lbl = ctk.CTkLabel(fila, text="$0.00", font=th.fuente(13, True),
                               text_color=th.TEXT)
            lbl.pack(side="right")
            setattr(self, atributo, lbl)

        res_row(_sin_dos_puntos(T("calc_material_cost")), "lbl_costo_mat")
        res_row(_sin_dos_puntos(T("calc_time_cost")), "lbl_costo_tiempo")
        ui.divider(card_res).pack(fill="x", padx=14, pady=(6, 2))
        res_row(_sin_dos_puntos(T("calc_total_cost")), "lbl_costo_total")

        f_sug = ctk.CTkFrame(card_res, fg_color=th.ACCENT_DIM,
                             corner_radius=th.RADIUS_INPUT)
        f_sug.pack(fill="x", padx=10, pady=(8, 12))
        ui.section_label(f_sug, T("calc_suggested")).pack(side="left", padx=14)
        self.lbl_precio_sug = ctk.CTkLabel(
            f_sug, text="$0.00",
            font=th.fuente(22, True),
            text_color=th.ACCENT
        )
        self.lbl_precio_sug.pack(side="right", padx=14, pady=10)

        ui.primary_button(
            scroll, T("calc_copy_order"), self._copiar_a_pedido,
            height=th.H_BTN_LG
        ).pack(fill="x", pady=(2, 6))

        ui.secondary_button(
            scroll, T("calc_quote"), self._abrir_cotizacion
        ).pack(fill="x", pady=(0, 12))

    def _cargar_filamentos(self):
        filamentos = db_manager.obtener_filamentos()
        # Etiquetas únicas: dos filamentos con el mismo nombre y material
        # colapsaban en una sola entrada y uno quedaba inaccesible.
        self._filamentos_data = mapa_por_etiqueta(
            filamentos, lambda f: f"{f['nombre']} ({f['material']})")
        values = list(self._filamentos_data.keys()) or [T("calc_no_filaments")]
        self.combo_filamento.configure(values=values)
        if values:
            self.combo_filamento.set(values[0])
        self.combo_filamento.configure(command=lambda _: self._calcular())
        self._calcular()

    def _calcular(self, *_):
        try:
            gramos = float(self.entry_gramos.get() or 0)
            horas = float(self.entry_horas.get() or 0)
            tarifa = float(self.entry_tarifa.get() or self.tarifa_default or 5.0)
            margen = float(self.entry_margen.get() or self.margen_default or 0)

            nombre_fil = self.combo_filamento.get()
            fil = self._filamentos_data.get(nombre_fil, {})
            precio_kg = fil.get("precio_por_kg", 0) or 0

            costo_material = gramos * (precio_kg / 1000)
            costo_tiempo = horas * tarifa if self.var_incluir_tiempo.get() else 0
            costo_total = costo_material + costo_tiempo

            # Un margen >= 100 daría una división por cero; uno negativo
            # generaría un precio por debajo del coste.
            margen = max(0, min(99, margen))
            precio_sugerido = costo_total / (1 - margen / 100) if costo_total > 0 else 0

            self.lbl_costo_mat.configure(text=f"${costo_material:.2f}")
            self.lbl_costo_tiempo.configure(text=f"${costo_tiempo:.2f}")
            self.lbl_costo_total.configure(text=f"${costo_total:.2f}")
            self.lbl_precio_sug.configure(text=f"${precio_sugerido:.2f}")

            self._ultimo_calculo = {
                "filamento_id": fil.get("id"),
                "material_nombre": nombre_fil,
                "gramos": gramos,
                "horas": horas,
                "costo_material": costo_material,
                "costo_tiempo": costo_tiempo,
                "precio_sugerido": precio_sugerido,
            }

        except (ValueError, TypeError):
            # Antes el error se ignoraba en silencio: los labels seguían
            # mostrando el cálculo ANTERIOR y "Copiar a nuevo pedido" copiaba
            # cifras obsoletas a un pedido real.
            self._ultimo_calculo = None
            self.lbl_costo_mat.configure(text="—")
            self.lbl_costo_tiempo.configure(text="—")
            self.lbl_costo_total.configure(text="—")
            self.lbl_precio_sug.configure(text="—")

    def _copiar_a_pedido(self):
        datos = getattr(self, "_ultimo_calculo", None)
        if not datos:
            import tkinter.messagebox as messagebox
            messagebox.showwarning(T("warning"), T("calc_invalid_values"))
            return
        self.app.navegar("pedidos")
        if hasattr(self.app, "_vista_actual") and hasattr(self.app._cache_vistas.get(self.app._vista_actual), "prellenar"):
            self.app._cache_vistas[self.app._vista_actual].prellenar(datos)
        # destroy() y no withdraw(): withdraw() dejaba una ventana Toplevel
        # invisible y siempre encima, y se acumulaba una por cada clic.
        self.destroy()

    def _abrir_cotizacion(self):
        datos = getattr(self, "_ultimo_calculo", None)
        if not datos:
            import tkinter.messagebox as messagebox
            messagebox.showwarning(T("warning"), T("calc_invalid_values"), parent=self)
            return
        from ui.quote_dialog import QuoteDialog
        QuoteDialog(self, self.app, datos)
