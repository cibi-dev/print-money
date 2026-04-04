# main.py – Punto de entrada principal de PrintMoney
# Configura la ventana CTk, el tema oscuro, la barra lateral y la navegación entre módulos

import sys
import os
import ctypes

# ── Dar identidad propia en la taskbar de Windows ──
try:
    import ctypes
    # Usar un ID de aplicación profesional y estable
    APP_ID = "PrintMoney.V1.Official"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
except Exception:
    pass

# ── Asegurar que el directorio del proyecto esté en el path ──
if getattr(sys, 'frozen', False):
    # Si somos un ejecutable de PyInstaller, el directorio base real donde 
    # residen los datos de usuario (config, bd) es donde está el .exe.
    # sys._MEIPASS es el directorio temporal para assets empaquetados.
    BASE_DIR = os.path.dirname(sys.executable)
    ASSETS_DIR = os.path.join(sys._MEIPASS, "assets")
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    ASSETS_DIR = os.path.join(BASE_DIR, "assets")

sys.path.insert(0, BASE_DIR)


import customtkinter as ctk
import json
import threading
from datetime import datetime
from PIL import Image, ImageTk

import db_manager
from utils.notifications import mostrar_notificacion
from utils.i18n import T, set_idioma, get_idioma

# ── Importar vistas de la UI (Lazy loading) ──
# Se movieron al método navegar() para mejorar el tiempo de inicio

# ── Configuración global de apariencia ──
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("dark-blue")

# ── Paleta de colores personalizada ──
COLOR_BG      = "#0F0F0F"   # Fondo principal
COLOR_SIDEBAR  = "#1A1A1A"  # Fondo barra lateral
COLOR_CARD     = "#1E1E1E"  # Tarjetas / paneles
COLOR_ACCENT   = "#00FF9D"  # Verde neón (ganancias / guardar)
COLOR_TEXT     = "#FFFFFF"  # Texto principal
COLOR_SUBTEXT  = "#888888"  # Texto secundario
COLOR_HOVER    = "#2A2A2A"  # Hover en botones de sidebar
COLOR_BORDER   = "#2D2D2D"  # Bordes sutiles
COLOR_RED      = "#FF4C4C"  # Alertas
COLOR_YELLOW   = "#FFD166"  # Advertencias


def cargar_config():
    """Carga la configuración desde config.json. Si no existe, crea una por defecto."""
    ruta = os.path.join(BASE_DIR, "config.json")
    if not os.path.exists(ruta):
        default_config = {
            "idioma": "es",
            "primera_ejecucion": True,
            "dias_antelacion_alertas": 2,
            "autoguardado_minutos": 10,
            "notificaciones_activadas": True
        }
        try:
            with open(ruta, "w", encoding="utf-8") as f:
                json.dump(default_config, f, indent=4, ensure_ascii=False)
        except Exception:
            pass
        return default_config
        
    try:
        with open(ruta, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"idioma": "es", "primera_ejecucion": True}


def guardar_config(config):
    """Guarda el diccionario de configuración en config.json."""
    ruta = os.path.join(BASE_DIR, "config.json")
    with open(ruta, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=4, ensure_ascii=False)


class SidebarButton(ctk.CTkButton):
    """Botón personalizado para la barra lateral con estado activo/inactivo."""

    def __init__(self, master, text, icon=None, command=None, **kwargs):
        # icon es ahora un emoji string; lo incluimos al inicio del texto
        label = f" {icon}  {text}" if icon else f"  {text}"
        super().__init__(
            master,
            text=label,
            command=command,
            anchor="w",
            corner_radius=10,
            height=44,
            fg_color="transparent",
            hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=14),
            **kwargs
        )
        self._is_active = False
        self._label = label

    def set_active(self, active: bool):
        """Cambia el estilo visual del botón según si está activo."""
        self._is_active = active
        if active:
            self.configure(
                fg_color=COLOR_HOVER,
                text_color=COLOR_ACCENT,
                font=ctk.CTkFont(family="Segoe UI", size=14, weight="bold")
            )
        else:
            self.configure(
                fg_color="transparent",
                text_color=COLOR_TEXT,
                font=ctk.CTkFont(family="Segoe UI", size=14)
            )


class TutorialDialog(ctk.CTkToplevel):
    """Ventana de tutorial en 6 slides para la primera ejecución."""

    SLIDES_KEYS = [
        ("tutorial_s1_title", "tutorial_s1_desc"),
        ("tutorial_s2_title", "tutorial_s2_desc"),
        ("tutorial_s3_title", "tutorial_s3_desc"),
        ("tutorial_s4_title", "tutorial_s4_desc"),
        ("tutorial_s5_title", "tutorial_s5_desc"),
        ("tutorial_s6_title", "tutorial_s6_desc"),
    ]

    def __init__(self, master, callback_fin=None):
        super().__init__(master)
        self.callback_fin = callback_fin
        self.slide_actual = 0

        self.title("PrintMoney – Tutorial")
        self.geometry("560x420")
        self.resizable(False, False)
        self.configure(fg_color=COLOR_BG)
        self.grab_set()  # Modal
        self.focus_force()

        # Centrar la ventana
        self.update_idletasks()
        x = master.winfo_x() + (master.winfo_width() // 2) - 280
        y = master.winfo_y() + (master.winfo_height() // 2) - 210
        self.geometry(f"+{x}+{y}")

        self._construir_ui()
        self._actualizar_slide()

    def _construir_ui(self):
        """Construye los widgets del tutorial."""
        # Encabezado
        self.lbl_main_title = ctk.CTkLabel(
            self, text=T("tutorial_title"),
            font=ctk.CTkFont(family="Segoe UI", size=22, weight="bold"),
            text_color=COLOR_ACCENT
        )
        self.lbl_main_title.pack(pady=(30, 4))

        ctk.CTkLabel(
            self, text=T("tutorial_subtitle"),
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_SUBTEXT
        ).pack()

        # Separador
        ctk.CTkFrame(self, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=40, pady=16)

        # Contenido del slide
        self.frame_slide = ctk.CTkFrame(self, fg_color=COLOR_CARD, corner_radius=14)
        self.frame_slide.pack(fill="both", expand=True, padx=40)

        self.lbl_slide_titulo = ctk.CTkLabel(
            self.frame_slide, text="",
            font=ctk.CTkFont(family="Segoe UI", size=19, weight="bold"),
            text_color=COLOR_TEXT
        )
        self.lbl_slide_titulo.pack(pady=(20, 8))

        self.lbl_slide_desc = ctk.CTkLabel(
            self.frame_slide, text="",
            font=ctk.CTkFont(family="Segoe UI", size=13),
            text_color=COLOR_SUBTEXT,
            justify="center"
        )
        self.lbl_slide_desc.pack(padx=20)

        # Indicadores de slide (puntos)
        self.frame_dots = ctk.CTkFrame(self.frame_slide, fg_color="transparent")
        self.frame_dots.pack(pady=16)
        self.dots = []
        for i in range(len(self.SLIDES_KEYS)):
            dot = ctk.CTkLabel(
                self.frame_dots, text="●",
                font=ctk.CTkFont(size=10),
                text_color=COLOR_SUBTEXT
            )
            dot.pack(side="left", padx=3)
            self.dots.append(dot)

        # Botones de navegación
        frame_nav = ctk.CTkFrame(self, fg_color="transparent")
        frame_nav.pack(pady=16, fill="x", padx=40)

        self.btn_saltar = ctk.CTkButton(
            frame_nav, text=T("tutorial_skip"),
            fg_color="transparent", hover_color=COLOR_HOVER,
            text_color=COLOR_SUBTEXT, width=140,
            command=self._finalizar_no_mostrar
        )
        self.btn_saltar.pack(side="left")

        self.btn_anterior = ctk.CTkButton(
            frame_nav, text=T("tutorial_back"),
            fg_color=COLOR_CARD, hover_color=COLOR_HOVER,
            text_color=COLOR_TEXT, width=100,
            command=self._slide_anterior
        )
        self.btn_anterior.pack(side="right", padx=(6, 0))

        self.btn_siguiente = ctk.CTkButton(
            frame_nav, text=T("tutorial_next"),
            fg_color=COLOR_ACCENT, hover_color="#00CC7A",
            text_color="#000000", width=110,
            command=self._slide_siguiente
        )
        self.btn_siguiente.pack(side="right")

    def _actualizar_slide(self):
        """Actualiza el contenido visual del slide actual."""
        title_key, desc_key = self.SLIDES_KEYS[self.slide_actual]
        self.lbl_slide_titulo.configure(text=T(title_key))
        self.lbl_slide_desc.configure(text=T(desc_key))

        # Actualizar puntos indicadores
        for i, dot in enumerate(self.dots):
            dot.configure(text_color=COLOR_ACCENT if i == self.slide_actual else COLOR_SUBTEXT)

        # Botón siguiente en el último slide
        es_ultimo = (self.slide_actual == len(self.SLIDES_KEYS) - 1)
        self.btn_siguiente.configure(
            text=T("tutorial_start") if es_ultimo else T("tutorial_next"),
            command=self._finalizar if es_ultimo else self._slide_siguiente
        )
        self.btn_anterior.configure(state="normal" if self.slide_actual > 0 else "disabled")

    def _slide_siguiente(self):
        if self.slide_actual < len(self.SLIDES_KEYS) - 1:
            self.slide_actual += 1
            self._actualizar_slide()

    def _slide_anterior(self):
        if self.slide_actual > 0:
            self.slide_actual -= 1
            self._actualizar_slide()

    def _finalizar(self):
        self.destroy()
        if self.callback_fin:
            self.callback_fin(no_mostrar=False)

    def _finalizar_no_mostrar(self):
        self.destroy()
        if self.callback_fin:
            self.callback_fin(no_mostrar=True)


class PrintMoneyApp(ctk.CTk):
    """Aplicación principal PrintMoney con barra lateral y navegación entre vistas."""

    def __init__(self):
        # className debe coincidir exactamente con el AppUserModelID para agrupación perfecta
        super().__init__(className="PrintMoney.V1.Official.Release")

        # ── Cargar configuración ──
        self.config_data = cargar_config()
        self.idioma = self.config_data.get("idioma", "es")
        set_idioma(self.idioma)

        # ── Configurar ventana principal ──
        self.title(T("app_title"))
        self.geometry("1280x780")
        self.minsize(900, 600)
        self.configure(fg_color=COLOR_BG)
        self.after(200, lambda: self.state("zoomed")) # Iniciar maximizada con retraso para asegurar efecto

        # Icono de la app (Nuclear Fix: Usar el ICO multi-tamaño)
        ico_path = os.path.join(ASSETS_DIR, "app_icon.ico")
        png_path = os.path.join(ASSETS_DIR, "logo32.png")
            
        if not os.path.exists(ico_path):
            ico_path = os.path.join(ASSETS_DIR, "logo.ico")
        
        if not os.path.exists(png_path):
            png_path = os.path.join(ASSETS_DIR, "logo.png")

        if os.path.exists(ico_path):
            self._ico_path = ico_path
            self._png_path = png_path if os.path.exists(png_path) else None
            
            # Aplicar icono (Síncrono + Refresco Forzado)
            self._aplicar_icono()
            # Un pequeño parpadeo ocultando y mostrando la ventana ayuda a la taskbar a refrescar el icono
            self.after(500, self._forzar_refresco_taskbar)

        # ── Inicializar base de datos ──
        db_manager.inicializar_db()

        # ── Hacer backup diario ──
        backup_ok = db_manager.hacer_backup_diario()
        if backup_ok and self.config_data.get("notificaciones_activadas", True):
            threading.Thread(
                target=mostrar_notificacion,
                args=("PrintMoney", T("backup_ok")),
                daemon=True
            ).start()

        # ── Cargar iconos ──
        self._cargar_iconos()

        # ── Construir layout principal ──
        self._construir_layout()

        # ── Vista activa, botón activo y caché de vistas ──
        self._vista_actual = None   # clave string de la vista visible
        self._boton_activo = None
        self._cache_vistas = {}     # dict[str, CTkFrame] – vistas construidas una vez

        # ── Navegar al dashboard por defecto ──
        self.navegar("dashboard")

        # ── Verificar pedidos próximos al iniciar ──
        self.after(1500, self._verificar_pedidos_proximos)

        # ── Iniciar autoguardado cada 10 minutos ──
        self._iniciar_autoguardado()

        # ── Tutorial de primera ejecución ──
        if self.config_data.get("primera_ejecucion", True):
            self.after(800, self._mostrar_tutorial)

    def _cargar_iconos(self):
        """Define los iconos emoji para cada sección de la barra lateral."""
        # Usamos emojis Unicode como iconos: más amigables, sin dependencia de archivos
        self.iconos = {
            "home":       "🏠",
            "orders":     "📦",
            "expenses":   "💸",
            "inventory":  "🧵",
            "catalog":    "📖",
            "clients":    "👥",
            "reports":    "📊",
            "calendar":   "📅",
            "calculator": "🧮",
            "settings":   "⚙️",
        }

    def _construir_layout(self):
        """Construye la estructura principal: sidebar + área de contenido."""
        # ── Barra lateral ──
        self.sidebar = ctk.CTkFrame(
            self, width=220, corner_radius=0,
            fg_color=COLOR_SIDEBAR
        )
        self.sidebar.pack(side="left", fill="y")
        self.sidebar.pack_propagate(False)

        self._construir_sidebar_contenido()

        # ── Área de contenido principal ──
        self.frame_contenido = ctk.CTkFrame(
            self, corner_radius=0, fg_color=COLOR_BG
        )
        self.frame_contenido.pack(side="right", fill="both", expand=True)

    def _construir_sidebar_contenido(self):
        """Construye el contenido interno de la sidebar (se puede reconstruir al cambiar idioma)."""
        # Limpiar contenido actual de la sidebar
        for w in self.sidebar.winfo_children():
            w.destroy()

        # Logo / nombre de la app
        frame_logo = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_logo.pack(pady=(24, 8), padx=16, fill="x")

        ctk.CTkLabel(
            frame_logo,
            text="🖨️  PrintMoney",
            font=ctk.CTkFont(family="Segoe UI", size=18, weight="bold"),
            text_color=COLOR_ACCENT
        ).pack(anchor="w")

        ctk.CTkLabel(
            frame_logo,
            text=T("app_subtitle"),
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_SUBTEXT
        ).pack(anchor="w")

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=12, pady=12)

        # ── Botones de navegación ──
        nav_items = [
            ("dashboard",   T("sidebar_dashboard"),    "home"),
            ("pedidos",     T("sidebar_orders"),       "orders"),
            ("gastos",      T("sidebar_expenses"),     "expenses"),
            ("inventario",  T("sidebar_inventory"),    "inventory"),
            ("catalogo",    T("sidebar_catalog"),      "catalog"),
            ("clientes",    T("sidebar_clients"),      "clients"),
            ("reportes",    T("sidebar_reports"),      "reports"),
            ("calendario",  T("sidebar_calendar"),     "calendar"),
        ]

        self.botones_nav = {}
        for key, label, icono in nav_items:
            btn = SidebarButton(
                self.sidebar,
                text=label,
                icon=self.iconos.get(icono),
                command=lambda k=key: self.navegar(k)
            )
            btn.pack(fill="x", padx=12, pady=2)
            self.botones_nav[key] = btn

        ctk.CTkFrame(self.sidebar, height=1, fg_color=COLOR_BORDER).pack(fill="x", padx=12, pady=12)

        # Botón calculadora (flotante)
        btn_calc = SidebarButton(
            self.sidebar,
            text=T("sidebar_calculator"),
            icon=self.iconos.get("calculator"),
            command=self._abrir_calculadora
        )
        btn_calc.pack(fill="x", padx=12, pady=2)
        self.botones_nav["calculadora"] = btn_calc

        # Separador + configuración (al final)
        frame_bottom = ctk.CTkFrame(self.sidebar, fg_color="transparent")
        frame_bottom.pack(side="bottom", fill="x", padx=12, pady=16)

        # Etiqueta de estado (autoguardado)
        self.lbl_status = ctk.CTkLabel(
            frame_bottom,
            text="",
            font=ctk.CTkFont(family="Segoe UI", size=10),
            text_color=COLOR_SUBTEXT
        )
        self.lbl_status.pack(pady=(0, 6))

        btn_settings = SidebarButton(
            frame_bottom,
            text=T("sidebar_settings"),
            icon=self.iconos.get("settings"),
            command=lambda: self.navegar("configuracion")
        )
        btn_settings.pack(fill="x")
        self.botones_nav["configuracion"] = btn_settings

    def _aplicar_icono(self):
        """Aplica el ícono de la aplicación de la forma más agresiva posible (Nivel de Clase)."""
        try:
            # 1. Aplicar .ico tradicional
            self.iconbitmap(self._ico_path)
            
            # 2. Aplicar vía iconphoto usando PNG (muy efectivo para la taskbar)
            path_para_img = self._png_path if self._png_path else self._ico_path
            img = Image.open(path_para_img)
            self._tk_icon = ImageTk.PhotoImage(img)
            self.iconphoto(True, self._tk_icon)

            # 3. INTERVENCIÓN DE BAJO NIVEL: SetClassLongPtrW
            # Esto cambia el icono de la CLASE de la ventana en el sistema operativo.
            try:
                import ctypes
                from ctypes import wintypes
                
                self.update_idletasks()
                # Obtener el HWND real (el padre del frame de Tk)
                hwnd = ctypes.windll.user32.GetParent(self.winfo_id())
                if not hwnd: hwnd = self.winfo_id()
                
                # Cargar el icono nativo con todos sus tamaños
                LR_LOADFROMFILE = 0x0010
                IMAGE_ICON      = 1
                hicon = ctypes.windll.user32.LoadImageW(None, self._ico_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE)
                
                if hicon:
                    # GCLP_HICON = -14, GCLP_HICONSM = -34
                    # Usamos W (Unicode) y Ptr (64-bit friendly)
                    if hasattr(ctypes.windll.user32, 'SetClassLongPtrW'):
                        set_class_long = ctypes.windll.user32.SetClassLongPtrW
                    else:
                        set_class_long = ctypes.windll.user32.SetClassLongW
                        
                    set_class_long(hwnd, -14, hicon) # Icono Grande
                    set_class_long(hwnd, -34, hicon) # Icono Pequeño
            except Exception:
                pass

        except Exception:
            pass

    def _forzar_refresco_taskbar(self):
        """Oculta y muestra la ventana brevemente para forzar a la barra de tareas a refrescar el icono."""
        try:
            self.withdraw()
            self._aplicar_icono()
            self.deiconify()
            # Si estaba maximizada, volver a maximizar
            self.after(100, lambda: self.state("zoomed"))
        except Exception:
            pass


    def navegar(self, destino: str):
        """Navega instantáneamente usando caché de vistas (pack_forget / pack).

        - La primera vez que se visita un destino, se crea la vista y se guarda en caché.
        - Las veces siguientes, la vista ya existe: solo se oculta la actual y se muestra
          la nueva. Sin crear widgets, sin queries iniciales → cambio en <1 frame.
        - Se llama a on_show() para refrescar los datos DESPUÉS de que el frame ya es
          visible, así el usuario ve el contenido anterior mientras se actualiza.
        """
        if destino == self._vista_actual:
            return  # ya estamos ahí

        # Desactivar botón anterior / activar nuevo
        if self._boton_activo:
            self._boton_activo.set_active(False)
        btn = self.botones_nav.get(destino)
        if btn:
            btn.set_active(True)
            self._boton_activo = btn

        # Importar la vista dinámicamente (Lazy loading)
        cls = None
        if destino == "dashboard":
            from ui.dashboard import DashboardView as cls
        elif destino == "pedidos":
            from ui.orders import OrdersView as cls
        elif destino == "gastos":
            from ui.expenses import ExpensesView as cls
        elif destino == "inventario":
            from ui.inventory import InventoryView as cls
        elif destino == "catalogo":
            from ui.catalog import CatalogView as cls
        elif destino == "clientes":
            from ui.clients import ClientsView as cls
        elif destino == "reportes":
            from ui.reports import ReportsView as cls
        elif destino == "calendario":
            from ui.calendar import CalendarView as cls
        elif destino == "configuracion":
            from ui.settings import SettingsView as cls

        if not cls:
            return

        # Ocultar vista actual
        if self._vista_actual and self._vista_actual in self._cache_vistas:
            self._cache_vistas[self._vista_actual].pack_forget()

        # Obtener o crear vista del caché
        if destino not in self._cache_vistas:
            vista = cls(master=self.frame_contenido, app=self)
            self._cache_vistas[destino] = vista
        else:
            vista = self._cache_vistas[destino]

        # Mostrar vista instantáneamente
        vista.pack(fill="both", expand=True)
        self._vista_actual = destino

        # Refrescar datos EN SEGUNDO PLANO (ya es visible, sin delay percibido)
        if hasattr(vista, "on_show"):
            self.after(1, vista.on_show)


    def _abrir_calculadora(self):
        """Abre la ventana flotante de calculadora (puede quedar abierta)."""
        from ui.calculator import CalculatorWindow
        win = CalculatorWindow(self)
        win.focus()

    def _mostrar_tutorial(self):
        """Muestra el diálogo de tutorial de primera ejecución."""
        TutorialDialog(self, callback_fin=self._tutorial_terminado)

    def _tutorial_terminado(self, no_mostrar: bool):
        """Callback cuando el usuario cierra el tutorial."""
        if no_mostrar:
            self.config_data["primera_ejecucion"] = False
            guardar_config(self.config_data)

    def _verificar_pedidos_proximos(self):
        """Comprueba pedidos próximos y muestra notificación si los hay."""
        dias = self.config_data.get("dias_antelacion_alertas", 2)
        pedidos = db_manager.obtener_pedidos_proximos(dias)
        if pedidos and self.config_data.get("notificaciones_activadas", True):
            nombres = ", ".join([p["cliente_nombre"] or "Cliente" for p in pedidos[:3]])
            mensaje = T("notif_orders_msg", count=len(pedidos), names=nombres)
            threading.Thread(
                target=mostrar_notificacion,
                args=(T("notif_orders_title"), mensaje),
                daemon=True
            ).start()

    def _iniciar_autoguardado(self):
        """Programa el autoguardado periódico cada 10 minutos."""
        minutos = self.config_data.get("autoguardado_minutos", 10)
        ms = minutos * 60 * 1000

        def autoguardar():
            self.lbl_status.configure(text=T("auto_saved"), text_color=COLOR_ACCENT)
            self.after(3000, lambda: self.lbl_status.configure(text="", text_color=COLOR_SUBTEXT))
            # Reprogramar
            self._timer_autoguardado = self.after(ms, autoguardar)

        self._timer_autoguardado = self.after(ms, autoguardar)

    def recargar_config(self):
        """Recarga la configuración desde disco y reaplica el idioma instantáneamente."""
        self.config_data = cargar_config()
        nuevo_idioma = self.config_data.get("idioma", "es")
        
        cambio_idioma = (nuevo_idioma != self.idioma)
        self.idioma = nuevo_idioma
        set_idioma(self.idioma)

        if cambio_idioma:
            # ── Reconstruir sidebar con el nuevo idioma ──
            vista_anterior = self._vista_actual
            self._boton_activo = None
            self._construir_sidebar_contenido()

            # ── Limpiar caché de vistas para que se reconstruyan con el nuevo idioma ──
            if self._vista_actual and self._vista_actual in self._cache_vistas:
                self._cache_vistas[self._vista_actual].pack_forget()
            for key, vista in self._cache_vistas.items():
                try:
                    vista.destroy()
                except Exception:
                    pass
            self._cache_vistas.clear()
            self._vista_actual = None

            # ── Navegar de vuelta a la vista de configuración ──
            self.navegar("configuracion")


if __name__ == "__main__":
    app = PrintMoneyApp()
    app.mainloop()
