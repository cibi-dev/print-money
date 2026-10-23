# utils/pdf_invoice.py – Generador de facturas PDF profesionales con ReportLab
# Genera facturas con logo del negocio, datos, tabla de items y pie de página

import os
from xml.sax.saxutils import escape
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT
from reportlab.lib.colors import HexColor
from datetime import datetime

from utils.i18n import T
from utils import paths


# Paleta de colores de marca
COLOR_NEGRO  = HexColor("#0F0F0F")
COLOR_BLANCO = HexColor("#FFFFFF")
COLOR_SUBTEXT = HexColor("#888888")

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
    """Resuelve la ruta del logo contra los recursos de la aplicación."""
    return paths.resolver_recurso(ruta)


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
        "titulo", fontSize=22, leading=26, fontName="Helvetica-Bold",
        textColor=COLOR_NEGRO, alignment=TA_CENTER, spaceAfter=4
    )
    story.append(Paragraph(_txt(negocio.get("nombre"), T("quote_default_business")),
                           estilo_titulo))

    estilo_sub = ParagraphStyle(
        "sub", fontSize=9, leading=12, fontName="Helvetica",
        textColor=COLOR_SUBTEXT, alignment=TA_CENTER, spaceAfter=2
    )
    if negocio.get("direccion"):
        story.append(Paragraph(_txt(negocio["direccion"]), estilo_sub))
    if negocio.get("telefono"):
        story.append(Paragraph(
            _txt(f"{T('invoice_phone_label')} {negocio['telefono']}"), estilo_sub))
    if negocio.get("email"):
        story.append(Paragraph(_txt(negocio["email"]), estilo_sub))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width=W, thickness=2, color=COLOR_NEGRO))
    story.append(Spacer(1, 0.4*cm))

    # ── ENCABEZADO DE FACTURA ──
    num_factura = f"F-{int(_num(pedido.get('id'))):05d}"
    fecha_emision = datetime.now().strftime("%d/%m/%Y")

    entrega = pedido.get("fecha_entrega") or ""
    try:
        entrega = datetime.strptime(str(entrega)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        entrega = _txt(entrega, "—")

    clave_estado = {
        "pendiente": "status_pending",
        "en proceso": "status_in_progress",
        "completado": "status_completed",
        "cancelado": "status_cancelled",
    }.get((pedido.get("estado") or "").strip().lower())
    estado_texto = T(clave_estado) if clave_estado else pedido.get("estado")

    data_enc = [
        [T("invoice_title"), num_factura],
        [T("invoice_issue_date"), fecha_emision],
        [T("invoice_delivery_date"), entrega],
        [T("invoice_status"), _txt(estado_texto).upper()],
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
    cliente_nombre = pedido.get("cliente_nombre") or T("invoice_default_client")
    estilo_cliente_titulo = ParagraphStyle(
        "ct", fontSize=10, leading=12, fontName="Helvetica-Bold",
        textColor=COLOR_NEGRO, spaceAfter=2
    )
    story.append(Paragraph(T("invoice_billed_to"), estilo_cliente_titulo))
    story.append(Paragraph(_txt(cliente_nombre),
                           ParagraphStyle("cn", fontSize=12, leading=15,
                                          fontName="Helvetica-Bold",
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

    headers = [T("invoice_col_description"), T("invoice_col_material"),
               T("invoice_col_qty"), T("invoice_col_unit"),
               T("invoice_col_amount")]
    precio_venta_fila = _num(pedido.get("precio_venta"))
    row_item = [
        Paragraph(_txt(pedido.get("descripcion"), T("quote_default_description")),
                  estilo_celda),
        Paragraph(_txt(pedido.get("filamento_nombre"), "—"), estilo_celda),
        Paragraph("1", estilo_celda_centro),
        Paragraph(_txt(f"${precio_venta_fila:.2f}"), estilo_celda_dcha),
        Paragraph(_txt(f"${precio_venta_fila:.2f}"), estilo_celda_dcha),
    ]
    tabla_items = Table(
        [headers, row_item],
        colWidths=[W*0.40, W*0.22, W*0.10, W*0.14, W*0.14]
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

    # ── TOTAL ──
    data_totales = [[T("invoice_total"), f"${precio_venta_fila:.2f}"]]
    tabla_totales = Table(data_totales, colWidths=[W*0.7, W*0.3])
    tabla_totales.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, 0), (-1, -1), 13),
        ("TEXTCOLOR",   (0, 0), (-1, -1), COLOR_NEGRO),
        ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
        ("LINEABOVE",   (0, 0), (-1, 0), 0.8, COLOR_NEGRO),
        ("TOPPADDING",  (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla_totales)
    story.append(Spacer(1, 0.8*cm))

    # ── NOTAS ──
    notas = pedido.get("notas", "")
    if notas:
        story.append(Paragraph(T("invoice_notes"), estilo_cliente_titulo))
        story.append(Paragraph(_txt(notas),
                               ParagraphStyle("notas", fontSize=9, leading=12,
                                              textColor=COLOR_SUBTEXT)))
        story.append(Spacer(1, 0.6*cm))

    # ── PIE DE PÁGINA ──
    story.append(HRFlowable(width=W, thickness=0.5, color=COLOR_SUBTEXT))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        _txt(T("invoice_footer")),
        ParagraphStyle("pie", fontSize=10, leading=12, fontName="Helvetica-Bold",
                       textColor=COLOR_NEGRO, alignment=TA_CENTER)
    ))

    doc.build(story)
