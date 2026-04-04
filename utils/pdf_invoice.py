# utils/pdf_invoice.py – Generador de facturas PDF profesionales con ReportLab
# Genera facturas con logo del negocio, datos, tabla de items y pie de página

import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                 TableStyle, Image, HRFlowable)
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.lib.colors import HexColor
from datetime import datetime


# Paleta de colores de marca
COLOR_NEGRO  = HexColor("#0F0F0F")
COLOR_BLANCO = HexColor("#FFFFFF")
COLOR_VERDE  = HexColor("#00FF9D")
COLOR_GRIS   = HexColor("#1E1E1E")
COLOR_SUBTEXT = HexColor("#888888")


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

    negocio = config.get("negocio", {})
    story = []
    styles = getSampleStyleSheet()
    W = A4[0] - 4*cm  # ancho disponible

    # ── LOGO ──
    logo_path = negocio.get("logo", "")
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
    story.append(Paragraph(negocio.get("nombre", "Mi Negocio 3D"), estilo_titulo))

    estilo_sub = ParagraphStyle(
        "sub", fontSize=9, fontName="Helvetica",
        textColor=COLOR_SUBTEXT, alignment=TA_CENTER, spaceAfter=2
    )
    if negocio.get("direccion"):
        story.append(Paragraph(negocio["direccion"], estilo_sub))
    if negocio.get("telefono"):
        story.append(Paragraph(f"Tel: {negocio['telefono']}", estilo_sub))
    if negocio.get("email"):
        story.append(Paragraph(negocio["email"], estilo_sub))

    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width=W, thickness=2, color=COLOR_NEGRO))
    story.append(Spacer(1, 0.4*cm))

    # ── ENCABEZADO DE FACTURA ──
    num_factura = f"F-{pedido.get('id', 0):05d}"
    fecha_emision = datetime.now().strftime("%d/%m/%Y")

    data_enc = [
        ["FACTURA", num_factura],
        ["Fecha de emisión:", fecha_emision],
        ["Fecha de entrega:", pedido.get("fecha_entrega") or "—"],
        ["Estado:", pedido.get("estado", "").upper()],
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
    story.append(Paragraph(cliente_nombre,
                           ParagraphStyle("cn", fontSize=12, fontName="Helvetica-Bold",
                                         textColor=COLOR_NEGRO)))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width=W, thickness=0.5, color=COLOR_SUBTEXT))
    story.append(Spacer(1, 0.4*cm))

    # ── TABLA DE ITEMS ──
    headers = ["Descripción", "Filamento", "Gramos", "Horas", "Monto"]
    row_item = [
        pedido.get("descripcion") or "Impresión 3D",
        pedido.get("filamento_nombre") or "—",
        f"{pedido.get('gramos_usados', 0):.1f} g",
        f"{pedido.get('horas_impresion', 0):.1f} h",
        f"${pedido.get('precio_venta', 0):.2f}",
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
        ("FONTSIZE",    (0, 1), (-1, -1), 9),
        ("ALIGN",       (2, 1), (-1, -1), "CENTER"),
        ("ALIGN",       (-1, 1), (-1, -1), "RIGHT"),
        ("TOPPADDING",  (0, 1), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 8),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#F5F5F5"), COLOR_BLANCO]),
        ("GRID",        (0, 0), (-1, -1), 0.5, HexColor("#DDDDDD")),
    ]))
    story.append(tabla_items)
    story.append(Spacer(1, 0.4*cm))

    # ── TABLA DE TOTALES ──
    costo_mat = pedido.get("costo_material", 0)
    costo_tiempo = pedido.get("costo_tiempo", 0)
    costo_envio = pedido.get("costo_envio", 0)
    precio_venta = pedido.get("precio_venta", 0)
    ganancia = pedido.get("ganancia", 0)

    data_totales = [
        ["Costo material:", f"${costo_mat:.2f}"],
        ["Costo tiempo:", f"${costo_tiempo:.2f}"],
        ["Costo envío:", f"${costo_envio:.2f}"],
        ["─"*30, "─"*10],
        ["TOTAL:", f"${precio_venta:.2f}"],
    ]
    tabla_totales = Table(data_totales, colWidths=[W*0.7, W*0.3])
    tabla_totales.setStyle(TableStyle([
        ("FONTNAME",    (0, 0), (-1, -2), "Helvetica"),
        ("FONTSIZE",    (0, 0), (-1, -1), 9),
        ("TEXTCOLOR",   (0, 0), (-1, -2), COLOR_SUBTEXT),
        ("ALIGN",       (1, 0), (1, -1), "RIGHT"),
        ("FONTNAME",    (0, -1), (-1, -1), "Helvetica-Bold"),
        ("FONTSIZE",    (0, -1), (-1, -1), 13),
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
        story.append(Paragraph(notas,
                               ParagraphStyle("notas", fontSize=9, textColor=COLOR_SUBTEXT)))
        story.append(Spacer(1, 0.6*cm))

    # ── PIE DE PÁGINA ──
    story.append(HRFlowable(width=W, thickness=0.5, color=COLOR_SUBTEXT))
    story.append(Spacer(1, 0.3*cm))
    story.append(Paragraph(
        "¡Gracias por tu compra! 🙌  Impresión 3D de calidad.",
        ParagraphStyle("pie", fontSize=10, fontName="Helvetica-Bold",
                       textColor=COLOR_NEGRO, alignment=TA_CENTER)
    ))

    doc.build(story)
