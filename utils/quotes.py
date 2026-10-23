# utils/quotes.py – Construcción y renderizado de cotizaciones
# Un único contrato para texto y PDF. Sin impuestos: el total es el precio de venta.

import os
from datetime import datetime, timedelta, date
from xml.sax.saxutils import escape

from utils.i18n import T
from utils import paths

MONEDA_DEFECTO = "$"
VALIDEZ_DEFECTO = 7


def _txt(valor):
    return escape(str(valor if valor is not None else ""))


def _num(valor, defecto=0.0):
    try:
        return float(valor)
    except (TypeError, ValueError):
        return defecto


def _ruta_logo(ruta):
    return paths.resolver_recurso(ruta)


def _fecha(valor):
    try:
        return datetime.strptime(str(valor)[:10], "%Y-%m-%d").strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(valor or "")


def _importe(valor, moneda=MONEDA_DEFECTO):
    return f"{moneda}{_num(valor):,.2f}"


def construir_cotizacion(numero, fecha, validez_dias, negocio, cliente, items,
                         notas="", condiciones="", moneda=MONEDA_DEFECTO,
                         descuento=0.0):
    """Arma el diccionario único que consumen el texto, el PDF y la vista."""
    fecha_str = str(fecha or date.today())[:10]
    dias = max(1, int(_num(validez_dias, VALIDEZ_DEFECTO)))
    try:
        vence = (datetime.strptime(fecha_str, "%Y-%m-%d").date()
                 + timedelta(days=dias)).isoformat()
    except ValueError:
        vence = fecha_str

    items = items or []
    subtotal = sum(_num(i.get("cantidad"), 1) * _num(i.get("precio_unitario"))
                   for i in items)
    descuento = max(0.0, _num(descuento))
    total = max(0.0, subtotal - descuento)

    return {
        "numero": numero,
        "fecha": fecha_str,
        "vence": vence,
        "validez_dias": dias,
        "negocio": negocio or {},
        "cliente": cliente or {},
        "items": items,
        "subtotal": subtotal,
        "descuento": descuento,
        "total": total,
        "moneda": moneda or MONEDA_DEFECTO,
        "notas": notas or "",
        "condiciones": condiciones or T("quote_default_conditions", dias=dias),
    }


def desde_registro(registro, negocio=None):
    """Convierte una fila de la BD (con items) al contrato de cotización."""
    cot = dict(registro or {})
    return construir_cotizacion(
        numero=cot.get("numero", ""),
        fecha=cot.get("fecha"),
        validez_dias=cot.get("validez_dias", VALIDEZ_DEFECTO),
        negocio=negocio or {},
        cliente={"nombre": cot.get("cliente_nombre") or ""},
        items=cot.get("items", []),
        notas=cot.get("notas") or "",
        condiciones=cot.get("condiciones") or "",
        moneda=cot.get("moneda") or MONEDA_DEFECTO,
        descuento=cot.get("descuento") or 0,
    )


def render_texto(cotizacion):
    """Devuelve la cotización como texto listo para WhatsApp/email."""
    cot = cotizacion
    negocio = cot.get("negocio") or {}
    cliente = cot.get("cliente") or {}
    moneda = cot.get("moneda", MONEDA_DEFECTO)

    lineas = [T("quote_text_greeting"), ""]
    if negocio.get("nombre"):
        lineas.append(f"*{negocio['nombre']}*")
    lineas.append(f"{T('quote_text_number')}: {cot.get('numero', '')}")
    lineas.append(f"{T('quote_text_date')}: {_fecha(cot.get('fecha'))}")
    lineas.append(f"{T('quote_text_valid')}: {_fecha(cot.get('vence'))}")
    if cliente.get("nombre"):
        lineas.append(f"{T('quote_text_client')}: {cliente['nombre']}")
    lineas.append("")

    for item in cot.get("items", []):
        cantidad = _num(item.get("cantidad"), 1)
        precio = _num(item.get("precio_unitario"))
        descripcion = item.get("descripcion") or T("quote_default_description")
        lineas.append(
            f"• {cantidad:g} × {descripcion}: {_importe(cantidad * precio, moneda)}")

    lineas.extend([
        "",
        f"*{T('quote_text_total')}: {_importe(cot.get('total'), moneda)}*",
    ])
    if cot.get("notas"):
        lineas.extend(["", f"{T('quote_text_notes')}: {cot['notas']}"])
    if cot.get("condiciones"):
        lineas.extend(["", cot["condiciones"]])
    lineas.extend(["", T("quote_text_footer")])
    return "\n".join(lineas)


def render_pdf(cotizacion, ruta_salida):
    """Genera la cotización en PDF A4 con la identidad del negocio."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table,
                                    TableStyle, Image, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT
    from reportlab.lib.colors import HexColor

    cot = cotizacion
    negocio = cot.get("negocio") or {}
    cliente = cot.get("cliente") or {}
    moneda = cot.get("moneda", MONEDA_DEFECTO)

    negro = HexColor("#0F0F0F")
    gris = HexColor("#888888")
    blanco = HexColor("#FFFFFF")
    borde = HexColor("#DDDDDD")

    doc = SimpleDocTemplate(ruta_salida, pagesize=A4,
                            topMargin=2 * cm, bottomMargin=2 * cm,
                            leftMargin=2 * cm, rightMargin=2 * cm)
    W = A4[0] - 4 * cm
    story = []

    logo_path = _ruta_logo(negocio.get("logo", ""))
    if logo_path and os.path.exists(logo_path):
        try:
            logo = Image(logo_path, width=5 * cm, height=2.5 * cm)
            logo.hAlign = "CENTER"
            story.append(logo)
            story.append(Spacer(1, 0.3 * cm))
        except Exception:
            pass

    story.append(Paragraph(_txt(negocio.get("nombre") or T("quote_default_business")),
                           ParagraphStyle("negocio", fontSize=20, leading=24,
                                          fontName="Helvetica-Bold",
                                          textColor=negro, alignment=TA_CENTER, spaceAfter=3)))
    estilo_contacto = ParagraphStyle("contacto", fontSize=9, leading=12,
                                      fontName="Helvetica",
                                      textColor=gris, alignment=TA_CENTER, spaceAfter=1)
    for clave in ("direccion", "telefono", "email"):
        if negocio.get(clave):
            story.append(Paragraph(_txt(negocio[clave]), estilo_contacto))
    story.append(Spacer(1, 0.5 * cm))
    story.append(HRFlowable(width=W, thickness=2, color=negro))
    story.append(Spacer(1, 0.4 * cm))

    data_enc = [
        [T("quote_pdf_title"), f"{T('quote_pdf_number')} {cot.get('numero', '')}"],
        [f"{T('quote_pdf_date')}:", _fecha(cot.get("fecha"))],
        [f"{T('quote_pdf_valid')}:", _fecha(cot.get("vence"))],
    ]
    tabla_enc = Table(data_enc, colWidths=[W * 0.6, W * 0.4])
    tabla_enc.setStyle(TableStyle([
        ("FONTNAME", (0, 0), (1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (1, 0), 16),
        ("TEXTCOLOR", (0, 0), (1, 0), negro),
        ("ALIGN", (1, 0), (1, 0), "RIGHT"),
        ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("TEXTCOLOR", (0, 1), (-1, -1), gris),
        ("ALIGN", (1, 1), (1, -1), "RIGHT"),
        ("TOPPADDING", (0, 0), (-1, -1), 2),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    story.append(tabla_enc)
    story.append(Spacer(1, 0.5 * cm))

    if cliente.get("nombre"):
        story.append(Paragraph(T("quote_pdf_client"),
                               ParagraphStyle("ct", fontSize=9, leading=11,
                                              fontName="Helvetica-Bold",
                                              textColor=gris, spaceAfter=2)))
        story.append(Paragraph(_txt(cliente["nombre"]),
                               ParagraphStyle("cn", fontSize=12, leading=15,
                                              fontName="Helvetica-Bold",
                                              textColor=negro, spaceAfter=2)))
        if cliente.get("email") or cliente.get("telefono"):
            contacto = " · ".join(_txt(v) for v in
                                  (cliente.get("email"), cliente.get("telefono")) if v)
            story.append(Paragraph(contacto, ParagraphStyle(
                "cc", fontSize=9, leading=12, fontName="Helvetica", textColor=gris)))
        story.append(Spacer(1, 0.4 * cm))

    estilo_celda = ParagraphStyle("celda", fontSize=9, fontName="Helvetica",
                                  textColor=negro, leading=11)
    estilo_centro = ParagraphStyle("celda_c", parent=estilo_celda, alignment=TA_CENTER)
    estilo_dcha = ParagraphStyle("celda_d", parent=estilo_celda, alignment=TA_RIGHT)

    filas = [[
        T("quote_pdf_description"), T("quote_pdf_qty"),
        T("quote_pdf_unit"), T("quote_pdf_amount"),
    ]]
    for item in cot.get("items", []):
        cantidad = _num(item.get("cantidad"), 1)
        precio = _num(item.get("precio_unitario"))
        filas.append([
            Paragraph(_txt(item.get("descripcion") or T("quote_default_description")),
                      estilo_celda),
            Paragraph(_txt(f"{cantidad:g}"), estilo_centro),
            Paragraph(_txt(_importe(precio, moneda)), estilo_dcha),
            Paragraph(_txt(_importe(cantidad * precio, moneda)), estilo_dcha),
        ])

    tabla_items = Table(filas, colWidths=[W * 0.55, W * 0.1, W * 0.17, W * 0.18])
    tabla_items.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), negro),
        ("TEXTCOLOR", (0, 0), (-1, 0), blanco),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("TOPPADDING", (0, 0), (-1, 0), 6),
        ("BOTTOMPADDING", (0, 0), (-1, 0), 6),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [HexColor("#F5F5F5"), blanco]),
        ("GRID", (0, 0), (-1, -1), 0.5, borde),
        ("TOPPADDING", (0, 1), (-1, -1), 7),
        ("BOTTOMPADDING", (0, 1), (-1, -1), 7),
    ]))
    story.append(tabla_items)
    story.append(Spacer(1, 0.5 * cm))

    tabla_total = Table(
        [["", T("quote_pdf_total"), _importe(cot.get("total"), moneda)]],
        colWidths=[W * 0.5, W * 0.25, W * 0.25])
    tabla_total.setStyle(TableStyle([
        ("FONTNAME", (1, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (1, 0), (-1, 0), 13),
        ("TEXTCOLOR", (1, 0), (-1, 0), negro),
        ("ALIGN", (2, 0), (2, 0), "RIGHT"),
        ("LINEABOVE", (1, 0), (-1, 0), 0.8, negro),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    story.append(tabla_total)

    if cot.get("notas"):
        story.append(Spacer(1, 0.6 * cm))
        story.append(Paragraph(T("quote_pdf_notes"),
                               ParagraphStyle("nt", fontSize=9, leading=11,
                                              fontName="Helvetica-Bold",
                                              textColor=gris, spaceAfter=2)))
        story.append(Paragraph(_txt(cot["notas"]),
                               ParagraphStyle("nv", fontSize=9, leading=12,
                                              fontName="Helvetica",
                                              textColor=gris)))
    if cot.get("condiciones"):
        story.append(Spacer(1, 0.4 * cm))
        story.append(Paragraph(_txt(cot["condiciones"]),
                               ParagraphStyle("cond", fontSize=8, leading=10,
                                              fontName="Helvetica",
                                              textColor=gris)))

    story.append(Spacer(1, 1 * cm))
    story.append(HRFlowable(width=W, thickness=0.5, color=gris))
    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph(T("quote_pdf_thanks"),
                           ParagraphStyle("pie", fontSize=10, leading=12,
                                          fontName="Helvetica-Bold",
                                          textColor=negro, alignment=TA_CENTER)))
    doc.build(story)
