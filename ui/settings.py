# ui/settings.py – Vista de Configuración
# Permite editar datos del negocio, idioma, tarifa, notificaciones y backup

import customtkinter as ctk
from tkinter import filedialog, messagebox
import json
import os
from utils.i18n import T

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

COLOR_BG     = "#0F0F0F"
COLOR_CARD   = "#1E1E1E"
COLOR_ACCENT = "#00FF9D"
COLOR_TEXT   = "#FFFFFF"
COLOR_SUB    = "#888888"
COLOR_BORDER = "#2D2D2D"
COLOR_HOVER  = "#2A2A2A"


def cargar_config():
    """Lee config.json. Un fichero ausente o corrupto no debe romper la app."""
    try:
        with open(os.path.join(BASE_DIR, "config.json"), "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, ValueError):
        return {}


def guardar_config(cfg):
    """Escribe config.json. Lanza OSError si el destino no es escribible."""
    with open(os.path.join(BASE_DIR, "config.json"), "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=4, ensure_ascii=False)


class SettingsView(ctk.CTkFrame):
    """Vista de configuración general de la aplicación."""

    def __init__(self, master, app, **kwargs):
        super().__init__(master, fg_color=COLOR_BG, corner_radius=0, **kwargs)
        self.app = app
        self.config_data = cargar_config()
        self._construir_ui()

    def on_show(self):
        """Refresca los datos al volver a esta vista."""
        self.config_data = cargar_config()
        self._cargar_valores()

    def _construir_ui(self):
        """Construye el layout de la vista de configuración."""
        frame_header = ctk.CTkFrame(self, fg_color="transparent")
        frame_header.pack(fill="x", padx=28, pady=(22, 0))
        ctk.CTkLabel(frame_header, text=T("settings_title"),
                     font=ctk.CTkFont(family="Segoe UI", size=26, weight="bold"),
                     text_color=COLOR_TEXT).pack(side="left")
        ctk.CTkButton(frame_header, text=T("settings_save"),
                      fg_color=COLOR_ACCENT, hover_color="#00CC7A",
                      text_color="#000000", corner_radius=10,
                      font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                      command=self._guardar, width=160, height=36).pack(side="right")

        # Scroll principal
        scroll = ctk.CTkScrollableFrame(self, fg_color="transparent")
        scroll.pack(fill="both", expand=True, padx=28, pady=14)
        scroll.columnconfigure(0, weight=1)
        scroll.columnconfigure(1, weight=1)

        # ── SECCIÓN: Datos del Negocio ──
        frame_negocio = self._seccion(scroll, T("settings_business"))
        frame_negocio.grid(row=0, column=0, padx=(0, 8), pady=(0, 14), sticky="nsew")
        self._bloque_negocio(frame_negocio)

        # ── SECCIÓN: Parámetros de Cálculo ──
        frame_calc = self._seccion(scroll, T("settings_calc"))
        frame_calc.grid(row=0, column=1, padx=(8, 0), pady=(0, 14), sticky="nsew")
        self._bloque_calculo(frame_calc)

        # ── SECCIÓN: Notificaciones & Backup ──
        frame_notif = self._seccion(scroll, T("settings_notif"))
        frame_notif.grid(row=1, column=0, padx=(0, 8), pady=(0, 14), sticky="nsew")
        self._bloque_notif(frame_notif)

        # ── SECCIÓN: Idioma ──
        frame_idioma = self._seccion(scroll, T("settings_lang"))
        frame_idioma.grid(row=1, column=1, padx=(8, 0), pady=(0, 14), sticky="nsew")
        self._bloque_idioma(frame_idioma)

    def _seccion(self, parent, titulo):
        frame = ctk.CTkFrame(parent, fg_color=COLOR_CARD, corner_radius=14,
                             border_width=1, border_color=COLOR_BORDER)
        ctk.CTkLabel(frame, text=titulo,
                     font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold"),
                     text_color=COLOR_TEXT).pack(anchor="w", padx=16, pady=(14, 8))
        ctk.CTkFrame(frame, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=16, pady=(0, 8))
        return frame

    def _lbl(self, parent, texto):
        ctk.CTkLabel(parent, text=texto, text_color=COLOR_SUB,
                     font=ctk.CTkFont(size=11)).pack(anchor="w", padx=16, pady=(6, 2))

    def _ent(self, parent, ph=""):
        e = ctk.CTkEntry(parent, placeholder_text=ph, fg_color="#252525",
                         border_color=COLOR_BORDER, text_color=COLOR_TEXT,
                         corner_radius=8, height=34)
        e.pack(fill="x", padx=16, pady=(0, 4))
        return e

    def _bloque_negocio(self, parent):
        self._lbl(parent, T("settings_biz_name"))
        self.ent_negocio_nombre = self._ent(parent, T("settings_biz_name_ph"))

        self._lbl(parent, T("settings_biz_addr"))
        self.ent_negocio_dir = self._ent(parent, T("settings_biz_addr_ph"))

        self._lbl(parent, T("settings_biz_phone"))
        self.ent_negocio_tel = self._ent(parent, "+1 555 000 000")

        self._lbl(parent, T("settings_biz_email"))
        self.ent_negocio_email = self._ent(parent, "negocio@email.com")

        self._lbl(parent, T("settings_biz_logo"))
        frame_logo = ctk.CTkFrame(parent, fg_color="transparent")
        frame_logo.pack(fill="x", padx=16, pady=(0, 12))
        self.ent_logo = ctk.CTkEntry(frame_logo, placeholder_text=T("settings_biz_logo_ph"),
                                     fg_color="#252525", border_color=COLOR_BORDER,
                                     text_color=COLOR_TEXT, corner_radius=8, height=34)
        self.ent_logo.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(frame_logo, text="📁", width=38, height=34,
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_ACCENT, command=self._seleccionar_logo).pack(side="right")

    def _seleccionar_logo(self):
        ruta = filedialog.askopenfilename(
            title=T("settings_logo_dialog"),
            filetypes=[("Images", "*.png *.jpg *.jpeg *.ico")]
        )
        if ruta:
            self.ent_logo.delete(0, "end")
            self.ent_logo.insert(0, ruta)

    def _bloque_calculo(self, parent):
        self._lbl(parent, T("settings_rate"))
        self.ent_tarifa = self._ent(parent, "5.00")

        self._lbl(parent, T("settings_margin"))
        self.ent_margen = self._ent(parent, "40")

        self._lbl(parent, T("settings_alert_days"))
        self.ent_dias = self._ent(parent, "2")

        ctk.CTkFrame(parent, height=10, fg_color="transparent").pack()

    def _bloque_notif(self, parent):
        self.var_notif = ctk.BooleanVar(value=True)
        ctk.CTkCheckBox(parent, text=T("settings_notif_chk"),
                        variable=self.var_notif, fg_color=COLOR_ACCENT,
                        hover_color="#00CC7A", checkmark_color="#000000",
                        text_color=COLOR_SUB, font=ctk.CTkFont(size=12)
                        ).pack(anchor="w", padx=16, pady=(4, 8))

        self._lbl(parent, T("settings_backup_dir"))
        frame_bk = ctk.CTkFrame(parent, fg_color="transparent")
        frame_bk.pack(fill="x", padx=16, pady=(0, 8))
        self.ent_backup = ctk.CTkEntry(frame_bk, placeholder_text="data/backups",
                                       fg_color="#252525", border_color=COLOR_BORDER,
                                       text_color=COLOR_TEXT, corner_radius=8, height=34)
        self.ent_backup.pack(side="left", fill="x", expand=True, padx=(0, 6))
        ctk.CTkButton(frame_bk, text="📁", width=38, height=34,
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_ACCENT, command=self._seleccionar_backup_dir
                      ).pack(side="right")

        ctk.CTkButton(parent, text=T("settings_backup_now"),
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_TEXT, height=34, corner_radius=10,
                      command=self._hacer_backup_manual
                      ).pack(fill="x", padx=16, pady=(4, 12))

    def _seleccionar_backup_dir(self):
        dir_ = filedialog.askdirectory(title=T("settings_backup_sel"))
        if dir_:
            self.ent_backup.delete(0, "end")
            self.ent_backup.insert(0, dir_)

    def _hacer_backup_manual(self):
        import db_manager
        try:
            # La copia usa la API de backup de SQLite: `shutil.copy2` sobre un
            # fichero abierto puede dejar una imagen inconsistente.
            dst = db_manager.hacer_backup_manual()
        except FileNotFoundError:
            messagebox.showwarning(T("warning"), T("settings_backup_nodb"))
            return
        except Exception as ex:
            messagebox.showerror(T("error"), str(ex))
            return
        messagebox.showinfo(T("backup"), T("settings_backup_ok", path=dst))

    def _bloque_idioma(self, parent):
        self._lbl(parent, T("settings_lang_label"))
        self.combo_idioma = ctk.CTkOptionMenu(
            parent, values=["Español (es)", "English (en)"],
            fg_color="#252525", button_color=COLOR_BORDER,
            text_color=COLOR_TEXT, dropdown_fg_color=COLOR_CARD,
            corner_radius=8, height=34
        )
        self.combo_idioma.pack(fill="x", padx=16, pady=(0, 8))

        ctk.CTkLabel(parent,
                     text=T("settings_lang_note"),
                     text_color=COLOR_SUB, font=ctk.CTkFont(size=10), justify="left"
                     ).pack(anchor="w", padx=16, pady=(0, 12))

        ctk.CTkFrame(parent, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=16, pady=8)

        # ── Tutorial Reset ──
        ctk.CTkButton(parent, text=T("settings_tutorial"),
                      fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
                      text_color=COLOR_TEXT, height=34, corner_radius=10,
                      command=self._resetear_tutorial
                      ).pack(fill="x", padx=16, pady=(4, 12))

    def _resetear_tutorial(self):
        self.config_data["primera_ejecucion"] = True
        try:
            guardar_config(self.config_data)
        except OSError as ex:
            messagebox.showerror(T("error"), str(ex))
            return
        # Sincronizar la copia en memoria de la app: si no, una escritura
        # posterior desde main.py reescribía el fichero con el valor viejo y
        # deshacía el reinicio del tutorial.
        if hasattr(self.app, "config_data"):
            self.app.config_data["primera_ejecucion"] = True
        messagebox.showinfo(T("tutorial"), T("settings_tutorial_ok"))

    def _cargar_valores(self):
        for e in [self.ent_negocio_nombre, self.ent_negocio_dir, self.ent_negocio_tel, 
                  self.ent_negocio_email, self.ent_logo, self.ent_tarifa, self.ent_margen, 
                  self.ent_dias, self.ent_backup]:
            e.delete(0, "end")

        neg = self.config_data.get("negocio", {})
        self.ent_negocio_nombre.insert(0, neg.get("nombre", ""))
        self.ent_negocio_dir.insert(0, neg.get("direccion", ""))
        self.ent_negocio_tel.insert(0, neg.get("telefono", ""))
        self.ent_negocio_email.insert(0, neg.get("email", ""))
        self.ent_logo.insert(0, neg.get("logo", ""))

        # `or valor_por_defecto` en vez de `.get(clave, defecto)`: si el valor
        # es None en el JSON, get() lo devolvía tal cual y el campo mostraba
        # el literal "None", que luego no se podía parsear al guardar.
        self.ent_tarifa.insert(0, str(self.config_data.get("tarifa_por_hora") or 5.0))
        self.ent_margen.insert(0, str(self.config_data.get("margen_objetivo") or 40.0))
        self.ent_dias.insert(0, str(self.config_data.get("dias_antelacion_alertas") or 2))

        self.var_notif.set(self.config_data.get("notificaciones_activadas", True))
        self.ent_backup.insert(0, self.config_data.get("carpeta_backups", "data/backups"))

        idioma = self.config_data.get("idioma", "es")
        self.combo_idioma.set("Español (es)" if idioma == "es" else "English (en)")

    def _guardar(self):
        try:
            tarifa = float(self.ent_tarifa.get() or 5.0)
            margen = float(self.ent_margen.get() or 0)
            dias = int(self.ent_dias.get() or 2)
        except (ValueError, TypeError):
            messagebox.showerror(T("error"), T("settings_invalid_nums"))
            return

        # Validación de rangos
        if tarifa < 0:
            messagebox.showerror(T("error"), T("settings_invalid_nums"))
            return
        if margen < 0 or margen >= 100:
            messagebox.showerror(T("error"), T("settings_invalid_nums"))
            return
        if dias < 0:
            messagebox.showerror(T("error"), T("settings_invalid_nums"))
            return

        idioma_sel = self.combo_idioma.get()
        idioma = "es" if idioma_sel.startswith("Español") else "en"

        # Releer el fichero antes de fusionar: self.config_data es una copia
        # antigua y una escritura intermedia se perdería al guardar.
        cfg = cargar_config()
        cfg.update({
            "idioma": idioma,
            "tarifa_por_hora": tarifa,
            "margen_objetivo": margen,
            "dias_antelacion_alertas": dias,
            "notificaciones_activadas": self.var_notif.get(),
            "carpeta_backups": self.ent_backup.get() or "data/backups",
        })
        # Fusionar el bloque de negocio para no perder claves ajenas
        negocio = dict(cfg.get("negocio", {}) or {})
        negocio.update({
            "nombre": self.ent_negocio_nombre.get(),
            "direccion": self.ent_negocio_dir.get(),
            "telefono": self.ent_negocio_tel.get(),
            "email": self.ent_negocio_email.get(),
            "logo": self.ent_logo.get(),
        })
        cfg["negocio"] = negocio

        try:
            guardar_config(cfg)
        except OSError as ex:
            # Instalación en una carpeta de solo lectura (Program Files):
            # antes la excepción escapaba y los cambios se perdían en silencio.
            messagebox.showerror(T("error"), str(ex), parent=self.winfo_toplevel())
            return

        self.config_data = cfg
        # Mostrar confirmación ANTES de recargar (recargar destruye esta vista)
        messagebox.showinfo(T("settings"), T("settings_saved"), parent=self.winfo_toplevel())
        self.app.recargar_config()
