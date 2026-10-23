# ui/components.py – Componentes reutilizables de la interfaz
# Encapsula los patrones que cada vista repetía: cabeceras, tarjetas, campos,
# botones, tablas, pills de estado y estados vacíos.

import customtkinter as ctk
from ui import theme as th


# ─────────────────────────── Cabeceras ───────────────────────────

def page_header(parent, titulo, subtitulo=None):
    """Cabecera estándar de página. Devuelve (frame, zona_de_acciones)."""
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    frame.pack(fill="x", padx=th.PAD_PAGE, pady=(22, 0))
    ctk.CTkLabel(frame, text=titulo, font=th.fuente(th.FONT_PAGE, True),
                 text_color=th.TEXT).pack(side="left")
    if subtitulo:
        ctk.CTkLabel(frame, text=subtitulo, font=th.fuente(13),
                     text_color=th.SUB).pack(side="left", padx=12, pady=6)
    acciones = ctk.CTkFrame(frame, fg_color="transparent")
    acciones.pack(side="right")
    return frame, acciones


# ─────────────────────────── Botones ───────────────────────────

def primary_button(parent, texto, comando=None, width=None, **kwargs):
    opciones = dict(
        text=texto, command=comando,
        fg_color=th.ACCENT, hover_color=th.ACCENT_HOVER,
        text_color=th.BG, corner_radius=th.RADIUS_CTRL,
        height=th.H_BTN, font=th.fuente(12, True),
    )
    if width is not None:
        opciones["width"] = width
    opciones.update(kwargs)
    return ctk.CTkButton(parent, **opciones)


def secondary_button(parent, texto, comando=None, width=None, **kwargs):
    opciones = dict(
        text=texto, command=comando,
        fg_color=th.SURFACE, hover_color=th.SURFACE_HOVER,
        text_color=th.TEXT, border_width=1, border_color=th.BORDER_STRONG,
        corner_radius=th.RADIUS_CTRL, height=th.H_BTN,
        font=th.fuente(12),
    )
    if width is not None:
        opciones["width"] = width
    opciones.update(kwargs)
    return ctk.CTkButton(parent, **opciones)


def danger_button(parent, texto, comando=None, **kwargs):
    opciones = dict(
        text=texto, command=comando,
        fg_color="transparent", hover_color=th.DANGER_BG,
        text_color=th.RED, border_width=1, border_color=th.RED,
        corner_radius=th.RADIUS_CTRL, height=th.H_INPUT,
        font=th.fuente(12, True),
    )
    opciones.update(kwargs)
    return ctk.CTkButton(parent, **opciones)


def icon_button(parent, icono, comando=None, **kwargs):
    opciones = dict(
        text=icono, command=comando, width=38, height=th.H_INPUT,
        fg_color=th.CARD, hover_color=th.HOVER,
        text_color=th.ACCENT, corner_radius=th.RADIUS_INPUT,
        font=th.fuente(13),
    )
    opciones.update(kwargs)
    return ctk.CTkButton(parent, **opciones)


# ─────────────────────────── Contenedores ───────────────────────────

def card(parent, **kwargs):
    opciones = dict(fg_color=th.CARD, corner_radius=th.RADIUS_CARD,
                    border_width=1, border_color=th.BORDER)
    opciones.update(kwargs)
    return ctk.CTkFrame(parent, **opciones)


def section_title(parent, texto, **kwargs):
    return ctk.CTkLabel(parent, text=texto, font=th.fuente(th.FONT_SECTION, True),
                        text_color=th.TEXT, anchor="w", **kwargs)


def section_label(parent, texto, **kwargs):
    return ctk.CTkLabel(parent, text=texto, font=th.fuente(th.FONT_LABEL),
                        text_color=th.SUB, anchor="w", **kwargs)


def divider(parent, **kwargs):
    opciones = dict(height=1, fg_color=th.BORDER)
    opciones.update(kwargs)
    return ctk.CTkFrame(parent, **opciones)


def scrollable(parent, **kwargs):
    opciones = dict(fg_color="transparent",
                    scrollbar_button_color=th.SCROLL_BUTTON,
                    scrollbar_button_hover_color=th.SCROLL_HOVER)
    opciones.update(kwargs)
    return ctk.CTkScrollableFrame(parent, **opciones)


# ─────────────────────────── Campos ───────────────────────────

def _al_focus(entrada):
    entrada.bind("<FocusIn>", lambda e: entrada.configure(border_color=th.ACCENT), add="+")
    entrada.bind("<FocusOut>", lambda e: entrada.configure(border_color=th.BORDER), add="+")


def entry(parent, placeholder="", **kwargs):
    opciones = dict(placeholder_text=placeholder, fg_color=th.SURFACE,
                    border_color=th.BORDER, text_color=th.TEXT,
                    corner_radius=th.RADIUS_INPUT, height=th.H_INPUT)
    opciones.update(kwargs)
    widget = ctk.CTkEntry(parent, **opciones)
    _al_focus(widget)
    return widget


def option_menu(parent, values, **kwargs):
    opciones = dict(values=values, fg_color=th.SURFACE, button_color=th.BORDER,
                    button_hover_color=th.HOVER, text_color=th.TEXT,
                    dropdown_fg_color=th.CARD, corner_radius=th.RADIUS_INPUT,
                    height=th.H_INPUT)
    opciones.update(kwargs)
    return ctk.CTkOptionMenu(parent, **opciones)


def checkbox(parent, texto, variable, **kwargs):
    opciones = dict(text=texto, variable=variable, fg_color=th.ACCENT,
                    hover_color=th.ACCENT_HOVER, checkmark_color=th.BG,
                    text_color=th.SUB, font=th.fuente(th.FONT_BODY))
    opciones.update(kwargs)
    return ctk.CTkCheckBox(parent, **opciones)


# ─────────────────────────── Estado vacío ───────────────────────────

def empty_state(parent, icono, titulo, hint, cta_texto=None, cta_cmd=None,
                empaquetar=True):
    frame = ctk.CTkFrame(parent, fg_color="transparent")
    if empaquetar:
        frame.pack(fill="both", expand=True)
    centro = ctk.CTkFrame(frame, fg_color="transparent")
    centro.place(relx=0.5, rely=0.5, anchor="center")
    ctk.CTkLabel(centro, text=icono, font=ctk.CTkFont(size=40)).pack(pady=(0, 8))
    ctk.CTkLabel(centro, text=titulo, font=th.fuente(th.FONT_SECTION, True),
                 text_color=th.TEXT).pack()
    ctk.CTkLabel(centro, text=hint, font=th.fuente(th.FONT_BODY),
                 text_color=th.SUB, justify="center").pack(pady=(4, 12))
    if cta_texto and cta_cmd:
        primary_button(centro, cta_texto, cta_cmd).pack()
    return frame


def status_pill(parent, estado, width=86, color=None):
    color = color or th.ESTADO_COLORES.get((estado or "").strip().lower(), th.SUB)
    return ctk.CTkLabel(parent, text=estado, fg_color=color, text_color=th.BG,
                        corner_radius=th.RADIUS_SM, height=22, width=width,
                        font=th.fuente(10, True))


# ─────────────────────────── KPI ───────────────────────────

class KPICard(ctk.CTkFrame):
    """Tarjeta de KPI con título, valor y subtítulo."""

    def __init__(self, master, titulo, valor, subtitulo="", acento=th.ACCENT, **kwargs):
        super().__init__(master, fg_color=th.CARD, corner_radius=th.RADIUS_CARD,
                         border_width=1, border_color=th.BORDER, **kwargs)
        ctk.CTkLabel(self, text=titulo, font=th.fuente(th.FONT_BODY),
                     text_color=th.SUB).pack(anchor="w", padx=18, pady=(16, 0))
        self.lbl_valor = ctk.CTkLabel(self, text=valor, font=th.fuente(28, True),
                                      text_color=acento)
        self.lbl_valor.pack(anchor="w", padx=18, pady=(2, 0))
        if subtitulo:
            ctk.CTkLabel(self, text=subtitulo, font=th.fuente(th.FONT_LABEL),
                         text_color=th.SUB).pack(anchor="w", padx=18, pady=(0, 14))
        else:
            ctk.CTkFrame(self, height=14, fg_color="transparent").pack()

    def actualizar(self, valor, acento=None):
        self.lbl_valor.configure(text=valor)
        if acento:
            self.lbl_valor.configure(text_color=acento)


# ─────────────────────────── Tabla de datos ───────────────────────────

class DataTable(ctk.CTkFrame):
    """Tabla con cabecera y filas alineadas mediante grid.

    `scroll` es el CTkScrollableFrame que contiene las filas como hijos
    directos (los tests de la app cuentan filas ahí). Los valores de cada
    celda pueden ser texto o una tupla (texto, color) para renderizar una pill.
    """

    def __init__(self, master, columnas, pesos=None, alinear=None,
                 on_select=None, **kwargs):
        super().__init__(master, fg_color=th.CARD, corner_radius=th.RADIUS_CARD,
                         border_width=1, border_color=th.BORDER, **kwargs)
        self.columnas = columnas
        self.pesos = pesos or [1] * len(columnas)
        self.alinear = alinear or ["w"] * len(columnas)
        self.on_select = on_select
        self._filas = []
        self._seleccion = None
        self._firma = None

        self._header = ctk.CTkFrame(self, fg_color=th.SURFACE, corner_radius=0)
        self._header.pack(fill="x")
        for i, (col, peso) in enumerate(zip(self.columnas, self.pesos)):
            self._header.grid_columnconfigure(i, weight=peso, uniform="dt")
            ctk.CTkLabel(self._header, text=col, text_color=th.SUB,
                         font=th.fuente(th.FONT_LABEL, True),
                         anchor=self.alinear[i]).grid(
                             row=0, column=i, sticky="ew", padx=8, pady=6)

        self.scroll = scrollable(self)
        self.scroll.pack(fill="both", expand=True)

    def set_rows(self, items, valores, firma=None):
        if firma is not None and firma == self._firma:
            return
        self._firma = firma

        for w in self.scroll.winfo_children():
            w.destroy()
        self._filas = []
        self._seleccion = None

        for idx, (item, celdas) in enumerate(zip(items, valores)):
            fila = ctk.CTkFrame(self.scroll, corner_radius=0,
                                fg_color=th.SURFACE if idx % 2 == 0 else th.CARD)
            fila.pack(fill="x")
            for i, celda in enumerate(celdas):
                fila.grid_columnconfigure(i, weight=self.pesos[i], uniform="dt")
                if isinstance(celda, tuple):
                    texto, color = celda
                    widget = ctk.CTkLabel(fila, text=texto, fg_color=color,
                                          text_color=th.BG,
                                          corner_radius=th.RADIUS_SM,
                                          height=20, width=80,
                                          font=th.fuente(10, True))
                else:
                    widget = ctk.CTkLabel(fila, text=str(celda), text_color=th.TEXT,
                                          font=th.fuente(th.FONT_LABEL),
                                          anchor=self.alinear[i])
                widget.grid(row=0, column=i, sticky="ew", padx=8, pady=6)
                if self.on_select:
                    widget.bind("<Button-1>", lambda e, it=item: self._seleccionar(it))
            if self.on_select:
                fila.bind("<Button-1>", lambda e, it=item: self._seleccionar(it))
            self._filas.append((fila, item))

    def _seleccionar(self, item):
        for idx, (fila, it) in enumerate(self._filas):
            if it is item:
                fila.configure(fg_color=th.SURFACE_HOVER)
            else:
                fila.configure(fg_color=th.SURFACE if idx % 2 == 0 else th.CARD)
        if self.on_select:
            self.on_select(item)

    def mostrar_vacio(self, texto, icono=None, hint=None,
                      cta_texto=None, cta_cmd=None):
        for w in self.scroll.winfo_children():
            w.destroy()
        self._filas = []
        self._firma = None
        if icono:
            empty_state(self.scroll, icono, texto, hint or "",
                        cta_texto=cta_texto, cta_cmd=cta_cmd)
        else:
            ctk.CTkLabel(self.scroll, text=texto, text_color=th.SUB,
                         font=th.fuente(th.FONT_BODY), justify="center").pack(pady=60)
