# ui/theme.py – Sistema de diseño centralizado
# Única fuente de verdad para colores, tipografía, radios y espaciado.

import customtkinter as ctk

# ── Colores ──
BG           = "#0F0F0F"
SIDEBAR      = "#1A1A1A"
CARD         = "#1E1E1E"
SURFACE      = "#252525"
BORDER       = "#2D2D2D"
BORDER_STRONG = "#3A3A3A"
HOVER        = "#2A2A2A"
SURFACE_HOVER = "#2E2E2E"
ACCENT       = "#00FF9D"
ACCENT_HOVER = "#00CC7A"
ACCENT_DIM   = "#003D26"
TEXT         = "#FFFFFF"
INK          = "#111111"
SUB          = "#888888"
SUB_DIM      = "#666666"
RED          = "#FF4C4C"
DANGER_BG    = "#2D0000"
DANGER_HOVER = "#3D0000"
YELLOW       = "#FFD166"
SCROLL_BUTTON = "#333333"
SCROLL_HOVER  = "#444444"

# ── Estados (pedidos / calendario / dashboard) ──
ESTADO_COLORES = {
    "pendiente": YELLOW,
    "en proceso": ACCENT,
    "completado": "#00C97A",
    "cancelado": RED,
}

# ── Radios ──
RADIUS_CARD  = 14
RADIUS_CTRL  = 10
RADIUS_INPUT = 8
RADIUS_SM    = 6

# ── Alturas ──
H_BTN      = 36
H_BTN_LG   = 40
H_BTN_SM   = 28
H_INPUT    = 34
H_ROW      = 30

# ── Tipografía ──
FONT_PAGE    = 26
FONT_SECTION = 15
FONT_LABEL   = 11
FONT_BODY    = 12

# ── Espaciado ──
PAD_PAGE = 28
GAP      = 8


def fuente(size=FONT_BODY, bold=False, family="Segoe UI"):
    return ctk.CTkFont(family=family, size=size,
                       weight="bold" if bold else "normal")


# ── Alias heredados ──
# Permiten migrar las vistas sin renombrar cada referencia de golpe.
COLOR_BG       = BG
COLOR_SIDEBAR  = SIDEBAR
COLOR_CARD     = CARD
COLOR_SURFACE  = SURFACE
COLOR_BORDER   = BORDER
COLOR_HOVER    = HOVER
COLOR_ACCENT   = ACCENT
COLOR_TEXT     = TEXT
COLOR_SUB      = SUB
COLOR_SUBTEXT  = SUB
COLOR_RED      = RED
COLOR_YELLOW   = YELLOW
