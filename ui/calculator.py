# ui/calculator.py – Ventana flotante de calculadora de costos
# Se puede abrir desde el Dashboard o la barra lateral y queda independiente

import customtkinter as ctk
import db_manager
from utils.i18n import T

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"


class CalculatorWindow(ctk.CTkToplevel):
    """Ventana flotante de calculadora de costo para impresión 3D."""

    def __init__(self, master):
        super().__init__(master)
        self.title(T("calc_title"))
        self.geometry("400x620")
        self.resizable(False, True)
        self.configure(fg_color=COLOR_BG)
        self.attributes("-topmost", True)

        # Cargar configuración del app padre
        self.tarifa_default = getattr(master, 'config_data', {}).get("tarifa_por_hora", 5.0)
        self.margen_default = getattr(master, 'config_data', {}).get("margen_objetivo", 40.0)
        self.app = master

        self._construir_ui()
        self._cargar_filamentos()

    def _label(self, parent, texto, size=12, color=COLOR_SUB, bold=False):
        return ctk.CTkLabel(
            parent, text=texto,
            font=ctk.CTkFont(family="Segoe UI", size=size, weight="bold" if bold else "normal"),
            text_color=color, anchor="w"
        )

    def _entry(self, parent, placeholder="0", width=None):
        return ctk.CTkEntry(
            parent, placeholder_text=placeholder,
            fg_color=COLOR_CARD, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, width=width or 340,
            corner_radius=8, height=36
        )

    def _construir_ui(self):
        ctk.CTkLabel(
            self, text=T("calc_title"),
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_ACCENT
        ).pack(pady=(20, 4), padx=20, anchor="w")

        ctk.CTkLabel(
            self, text=T("calc_subtitle"),
            font=ctk.CTkFont(family="Segoe UI", size=11),
            text_color=COLOR_SUB
        ).pack(padx=20, anchor="w")

        ctk.CTkFrame(self, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=20, pady=12)

        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0)
        scroll.pack(fill="both", expand=True, padx=20, pady=0)

        def row(text):
            self._label(scroll, text).pack(anchor="w", pady=(10, 2))

        row(T("calc_filament"))
        self.combo_filamento = ctk.CTkOptionMenu(
            scroll, values=[T("calc_select")],
            fg_color=COLOR_CARD, button_color=COLOR_BORDER,
            button_hover_color=COLOR_HOVER, text_color=COLOR_TEXT,
            dropdown_fg_color=COLOR_CARD, corner_radius=8, height=36
        )
        self.combo_filamento.pack(fill="x")

        row(T("calc_grams"))
        self.entry_gramos = self._entry(scroll, placeholder="100")
        self.entry_gramos.pack(fill="x")
        self.entry_gramos.bind("<KeyRelease>", lambda e: self._calcular())

        row(T("calc_hours"))
        self.entry_horas = self._entry(scroll, placeholder="2.5")
        self.entry_horas.pack(fill="x")
        self.entry_horas.bind("<KeyRelease>", lambda e: self._calcular())

        row(T("calc_rate"))
        self.entry_tarifa = ctk.CTkEntry(
            scroll, placeholder_text=str(self.tarifa_default),
            fg_color=COLOR_CARD, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, corner_radius=8, height=36
        )
        self.entry_tarifa.pack(fill="x")
        self.entry_tarifa.insert(0, str(self.tarifa_default))
        self.entry_tarifa.bind("<KeyRelease>", lambda e: self._calcular())

        self.var_incluir_tiempo = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(
            scroll, text=T("calc_include_time"),
            variable=self.var_incluir_tiempo,
            text_color=COLOR_SUB, fg_color=COLOR_ACCENT,
            hover_color="#00CC7A", checkmark_color="#000000",
            command=self._calcular
        ).pack(anchor="w", pady=(10, 0))

        row(T("calc_margin"))
        self.entry_margen = ctk.CTkEntry(
            scroll, placeholder_text=str(self.margen_default),
            fg_color=COLOR_CARD, border_color=COLOR_BORDER,
            text_color=COLOR_TEXT, corner_radius=8, height=36
        )
        self.entry_margen.pack(fill="x")
        self.entry_margen.insert(0, str(self.margen_default))
        self.entry_margen.bind("<KeyRelease>", lambda e: self._calcular())

        ctk.CTkFrame(scroll, height=1, fg_color=COLOR_BORDER).pack(fill="x", pady=14)

        self._label(scroll, T("calc_results"), size=11, bold=True).pack(anchor="w")

        frame_res = ctk.CTkFrame(scroll, fg_color=COLOR_CARD, corner_radius=12,
                                 border_width=1, border_color=COLOR_BORDER)
        frame_res.pack(fill="x", pady=6)

        def res_row(texto, attr):
            f = ctk.CTkFrame(frame_res, fg_color="transparent")
            f.pack(fill="x", padx=14, pady=3)
            self._label(f, texto, color=COLOR_SUB).pack(side="left")
            lbl = ctk.CTkLabel(f, text="$0.00",
                               font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                               text_color=COLOR_TEXT)
            lbl.pack(side="right")
            setattr(self, attr, lbl)

        res_row(T("calc_material_cost"),   "lbl_costo_mat")
        res_row(T("calc_time_cost"),       "lbl_costo_tiempo")
        res_row(T("calc_total_cost"),      "lbl_costo_total")

        f_sug = ctk.CTkFrame(frame_res, fg_color="#252525", corner_radius=8)
        f_sug.pack(fill="x", padx=10, pady=(6, 10))
        ctk.CTkLabel(f_sug, text=T("calc_suggested"),
                     font=ctk.CTkFont(family="Segoe UI", size=12),
                     text_color=COLOR_SUB).pack(side="left", padx=14)
        self.lbl_precio_sug = ctk.CTkLabel(
            f_sug, text="$0.00",
            font=ctk.CTkFont(family="Segoe UI", size=20, weight="bold"),
            text_color=COLOR_ACCENT
        )
        self.lbl_precio_sug.pack(side="right", padx=14, pady=8)

        ctk.CTkButton(
            scroll, text=T("calc_copy_order"),
            fg_color=COLOR_ACCENT, hover_color="#00CC7A",
            text_color="#000000",
            font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
            height=40, corner_radius=10,
            command=self._copiar_a_pedido
        ).pack(fill="x", pady=(6, 0))

        ctk.CTkButton(
            scroll, text=T("calc_copy_quote"),
            fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT, border_width=1, border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36, corner_radius=10,
            command=self._copiar_cotizacion_texto
        ).pack(fill="x", pady=(6, 0))

        ctk.CTkButton(
            scroll, text=T("calc_export_pdf"),
            fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT, border_width=1, border_color=COLOR_BORDER,
            font=ctk.CTkFont(family="Segoe UI", size=13),
            height=36, corner_radius=10,
            command=self._exportar_cotizacion_pdf
        ).pack(fill="x", pady=(6, 14))

    def _cargar_filamentos(self):
        filamentos = db_manager.obtener_filamentos()
        self._filamentos_data = {f"{f['nombre']} ({f['material']})": f for f in filamentos}
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
            tarifa = float(self.entry_tarifa.get() or self.tarifa_default)
            margen = float(self.entry_margen.get() or self.margen_default)

            nombre_fil = self.combo_filamento.get()
            fil = self._filamentos_data.get(nombre_fil, {})
            precio_kg = fil.get("precio_por_kg", 0)

            costo_material = gramos * (precio_kg / 1000)
            costo_tiempo = horas * tarifa if self.var_incluir_tiempo.get() else 0
            costo_total = costo_material + costo_tiempo

            if margen >= 100:
                margen = 99
            precio_sugerido = costo_total / (1 - margen / 100) if costo_total > 0 else 0

            self.lbl_costo_mat.configure(text=f"${costo_material:.2f}")
            self.lbl_costo_tiempo.configure(text=f"${costo_tiempo:.2f}")
            self.lbl_costo_total.configure(text=f"${costo_total:.2f}")
            self.lbl_precio_sug.configure(text=f"${precio_sugerido:.2f}")

            self._ultimo_calculo = {
                "filamento_id": fil.get("id"),
                "gramos": gramos,
                "horas": horas,
                "costo_material": costo_material,
                "costo_tiempo": costo_tiempo,
                "precio_sugerido": precio_sugerido,
            }

        except ValueError:
            pass

    def _copiar_a_pedido(self):
        datos = getattr(self, "_ultimo_calculo", {})
        self.app.navegar("pedidos")
        if hasattr(self.app, "_vista_actual") and hasattr(self.app._cache_vistas.get(self.app._vista_actual), "prellenar"):
            self.app._cache_vistas[self.app._vista_actual].prellenar(datos)
        self.withdraw()

    def _obtener_datos_cotizacion(self):
        try:
            gramos = float(self.entry_gramos.get() or 0)
            horas = float(self.entry_horas.get() or 0)
        except ValueError:
            gramos, horas = 0, 0
            
        nombre_fil = self.combo_filamento.get()
        if nombre_fil == T("calc_select"):
            nombre_fil = T("calc_not_specified")
            
        precio_str = self.lbl_precio_sug.cget("text").replace("$", "")
        try:
            precio = float(precio_str)
        except ValueError:
            precio = 0.0

        return {
            "producto": T("calc_product_3d"),
            "material": nombre_fil,
            "tiempo": f"{horas}",
            "total": precio
        }

    def _copiar_cotizacion_texto(self):
        import tkinter.messagebox as messagebox
        datos = self._obtener_datos_cotizacion()
        texto = T("calc_quote_msg",
                  product=datos['producto'],
                  material=datos['material'],
                  time=datos['tiempo'],
                  total=datos['total'])
        self.clipboard_clear()
        self.clipboard_append(texto)
        self.update()
        messagebox.showinfo(T("calc_copied"), T("calc_copied_msg"))

    def _exportar_cotizacion_pdf(self):
        import tkinter.filedialog as filedialog
        import tkinter.messagebox as messagebox
        from utils.export import exportar_cotizacion_pdf
        
        datos = self._obtener_datos_cotizacion()
        ruta = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF", "*.pdf")],
            initialfile="Cotizacion.pdf"
        )
        if ruta:
            try:
                exportar_cotizacion_pdf(ruta, datos)
                messagebox.showinfo(T("success"), T("calc_pdf_ok", path=ruta))
            except Exception as e:
                messagebox.showerror(T("error"), f"Error: {e}")
