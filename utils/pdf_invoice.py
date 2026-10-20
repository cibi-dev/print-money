# utils/pdf_invoice.py – Generador de facturas PDF profesionales con ReportLab
# Genera facturas con logo del negocio, datos, tabla de items y pie de página

import os
import sys
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.colors import HexColor
from datetime import datetime


# Paleta de colores de marca
COLOR_NEGRO  = HexColor("#0F0F0F")
COLOR_BLANCO = HexColor("#FFFFFF")
COLOR_SUBTEXT = HexColor("#888888")

# Carpeta donde viven los datos del usuario (junto al .exe si está compilado)
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _txt(valor, defecto=""):
    """Convierte un valor a texto plano escapado para ReportLab.

    Sin esto, un `<` en el nombre del cliente o en las notas aborta la
    generación del PDF con 'Parse error: saw </para> instead of expected </b>'.
    """
    if valor is None:
        valor = defecto
    return escape(str(valor))


def _num(valor, defecto=0.0):
    """Convierte a float tolerando None, '' o basura en la base de datos."""
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _ruta_logo(ruta):
    """Resuelve la ruta del logo: si es relativa, se busca junto al ejecutable."""
    if not ruta:
        return ""
    if os.path.isabs(ruta):
        return ruta
    return os.path.join(BASE_DIR, ruta)


def generar_factura_pdf(pedido: dict, config: dict, ruta_salida: str):
    """
    Genera una factura PDF profesional para el pedido dado.

    Args:
        pedido: dict con datos del pedido (de db_manager.obtener_pedidos)
        config: dict de configuración del negocio (config.json)
        ruta_salida: ruta completa del archivo PDF a generar
    """
    doc = SimpleDocTemplate(
        ruta_salida,
        pagesize=A4,
        topMargin=2*cm,
        bottomMargin=2*cm,
        leftMargin=2*cm,
        rightMargin=2*cm
    )

    negocio = config.get("negocio", {}) or {}
    story = []
    styles = getSampleStyleSheet()
    W = A4[0] - 4*cm  # ancho disponible

    # ── LOGO ──
    logo_path = _ruta_logo(negocio.get("logo", ""))
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=5*cm, height=2.5*cm)
            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 0.4*cm))
        except Exception:
            pass

    # ── NOMBRE DEL NEGOCIO ──
    estilo_titulo = ParagraphStyle(
        "titulo", fontSize=22, fontName="Helvetica-Bold",
        textColor=COLOR_NEGRO, alignment=TA_CENTER, spaceAfter=4
    )
    story.append(Paragraph(_txt(negocio.get("nombre"), "Mi Negocio 3D"), estilo_titulo))

    estilo_sub = ParagraphStyle(
        "sub", fontSize=9, fontName="Helvetica",
        textColor=COLOR_SUBTEXT, alignment=TA_CENTER, spaceAfter=2
    )
    if negocio.get("direccion"):
        story.append(Paragraph(_txt(negocio["direccion"]), estilo_sub))
    if negocio.get("telefono"):
        story.append(Paragraph(_txt(f"Tel: {negocio['telefono']}"), estilo_sub))
    if negocio.get("email"):
        story.append(Paragraph(_txt(negocio["email"]), estilo_sub))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width=W, thickness=2, color=COLOR_NEGRO))
    story.append(Spacer(1, 0.4*cm))

    # ── ENCABEZADO DE FACTURA ──
    num_factura = f"F-{int(_num(pedido.get('id'))):05d}"
    fecha_emision = datetime.now().strftime("%d/%m/%Y")

    data_enc = [
        ["FACTURA", num_factura],
        ["Fecha de emisión:", fecha_emision],
        ["Fecha de entrega:", _txt(pedido.get("fecha_entrega"), "—")],
        ["Estado:", _txt(pedido.get("estado"), "").upper()],
    ]
    tabla_enc = Table(data_enc, colWidths=[W*0.5, W*0.5])
    tabla_enc.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (0, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (0, 0), 16),
        ("TEXTCOLOR",   (0, 0), (0, 0), COLOR_NEGRO),
        ("FONTNAME",    (1, 0), (1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (1, 0), (1, 0), 16),
        ("TEXTCOLOR",   (1, 0), (1, 0), COLOR_NEGRO),
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 1), (-1, -1), COLOR_SUBTEXT),
        ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
        ("TOPPADDING",  (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(tabla_enc)
    story.append(Spacer(1, 0.5*cm))

    # ── DATOS DEL CLIENTE ──
    cliente_nombre = pedido.get("cliente_nombre") or "Cliente"
    estilo_cliente_titulo = ParagraphStyle(
        "ct", fontSize=10, fontName="Helvetica-Bold",
        textColor=COLOR_NEGRO, spaceAfter=2
    )
    story.append(Paragraph("FACTURADO A:", estilo_cliente_titulo))
    story.append(Paragraph(_txt(cliente_nombre),
                           ParagraphStyle("cn", fontSize=12, fontName="Helvetica-Bold",
                                         textColor=COLOR_NEGRO)))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width=W, thickness=0.5, color=COLOR_SUBTEXT))
    story.append(Spacer(1, 0.4*cm))

    # ── TABLA DE ITEMS ──
    # Las celdas de texto van como Paragraph para que el contenido largo se
    # ajuste al ancho de la columna en vez de desbordarse sobre las vecinas.
    estilo_celda = ParagraphStyle("celda", fontSize=9, fontName="Helvetica",
                                  textColor=COLOR_NEGRO, leading=11)
    estilo_celda_centro = ParagraphStyle("celda_c", parent=estilo_celda, alignment=TA_CENTER)
    estilo_celda_dcha = ParagraphStyle("celda_d", parent=estilo_celda, alignment=TA_RIGHT)

    headers = ["Descripción", "Filamento", "Gramos", "Horas", "Monto"]
    row_item = [
        Paragraph(_txt(pedido.get("descripcion"), "Impresión 3D"), estilo_celda),
        Paragraph(_txt(pedido.get("filamento_nombre"), "—"), estilo_celda),
        Paragraph(_txt(f"{_num(pedido.get('gramos_usados')):.1f} g"), estilo_celda_centro),
        Paragraph(_txt(f"{_num(pedido.get('horas_impresion')):.1f} h"), estilo_celda_centro),
        Paragraph(_txt(f"${_num(pedido.get('precio_venta')):.2f}"), estilo_celda_dcha),
    ]
    tabla_items = Table(
        [headers, row_item],
        colWidths=[W*0.35, W*0.2, W*0.12, W*0.12, W*0.21]
    )
    tabla_items.setStyle(TableStyle([
        # Encabezado
        ("BACKGROUND",  (0, 0), (-1, 0), COLOR_NEGRO),
        ("TEXTCOLOR",   (0, 0), (-1, 0), COLOR_BLANCO),
        ("FONTNAME",    (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, 0), 9),
        ("ALIGN",       (0, 0), (-1, 0), "CENTER"),
        ("TOPPADDING",  (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        # Fila de items
        ("FONTNAME",    (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE",    (0, 1), (-1, 1), 9),
        ("TOPPADDING",  (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#F5F5F5"), COLOR_BLANCO]),
        ("GRID",        (0, 0), (-1, -1), 0.5, HexColor("#DDDDDD")),
    ]))
    story.append(tabla_items)
    story.append(Spacer(1, 0.4*cm))

    # ── TABLA DE TOTALES ──
    costo_mat = _num(pedido.get("costo_material"))
    costo_tiempo = _num(pedido.get("costo_tiempo"))
    costo_envio = _num(pedido.get("costo_envio"))
    precio_venta = _num(pedido.get("precio_venta"))
    ganancia = _num(pedido.get("ganancia"))

    data_totales = [
        ["Costo material:", f"${costo_mat:.2f}"],
        ["Costo tiempo:", f"${costo_tiempo:.2f}"],
        ["Costo envío:", f"${costo_envio:.2f}"],
        ["─"*30, "─"*10],
        ["TOTAL:", f"${precio_venta:.2f}"],
        ["Ganancia:", f"${ganancia:.2f}"],
    ]
    tabla_totales = Table(data_totales, colWidths=[W*0.7, W*0.3])
    tabla_totales.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -4), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, -4), COLOR_SUBTEXT),
        ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME",    (0, -2), (-1, -2), "Helvetica-Bold"),
        ("FONTSIZE",    (0, -2), (-1, -2), 13),
        ("TEXTCOLOR",   (0, -2), (-1, -2), COLOR_NEGRO),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, -1), (-1, -1), 10),
        ("TEXTCOLOR",   (0, -1), (-1, -1), COLOR_NEGRO),
        ("TOPPADDING",  (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
    ]))
    story.append(tabla_totales)
    story.append(Spacer(1, 0.8*cm))

    # ── NOTAS ──
    notas = pedido.get("notas", "")
    if notas:
        story.append(Paragraph("Notas:", estilo_cliente_titulo))
        story.append(Paragraph(_txt(notas),
                               ParagraphStyle("notas", fontSize=9, textColor=COLOR_SUBTEXT)))
        story.append(Spacer(1, 0.6*cm))

    # ── PIE DE PÁGINA ──
    story.append(HRFlowable(width=W, thickness=0.5, color=COLOR_SUBTEXT))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "¡Gracias por tu compra!  Impresión 3D de calidad.",
        ParagraphStyle("pie", fontSize=10, fontName="Helvetica-Bold",
                       textColor=COLOR_NEGRO, alignment=TA_CENTER)
    ))

    doc.build(story)
