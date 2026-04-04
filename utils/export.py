# utils/export.py – Exportación de reportes a Excel y PDF
# Usa pandas + openpyxl para Excel y ReportLab para PDF

import os
import pandas as pd
from datetime import datetime
import db_manager

import sys
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def exportar_excel(ruta_salida: str, año: int):
    """
    Exporta un reporte anual completo a Excel con múltiples hojas.

    Hojas:
    - Pedidos: todos los pedidos del año
    - Gastos: todos los gastos del año
    - Resumen mensual: KPIs por mes
    """
    fecha_inicio = f"{año}-01-01"
    fecha_fin    = f"{año}-12-31"

    # Obtener datos
    pedidos = db_manager.obtener_pedidos(filtro_fecha_desde=fecha_inicio,
                                         filtro_fecha_hasta=fecha_fin)
    gastos  = db_manager.obtener_gastos(fecha_desde=fecha_inicio, fecha_hasta=fecha_fin)

    # Resumen mensual
    resumen = []
    for mes in range(1, 13):
        stats = db_manager.obtener_estadisticas_mes(año, mes)
        resumen.append({
            "Mes": datetime(año, mes, 1).strftime("%B"),
            "Ingresos ($)": stats["ingresos"],
            "Gastos ($)": stats["gastos"],
            "Ganancia Neta ($)": stats["ganancia_neta"],
            "Margen (%)": round(stats["margen"], 2),
            "Pedidos": stats["num_pedidos"],
        })

    # Convertir a DataFrames
    df_pedidos = pd.DataFrame(pedidos) if pedidos else pd.DataFrame()
    df_gastos  = pd.DataFrame(gastos)  if gastos  else pd.DataFrame()
    df_resumen = pd.DataFrame(resumen)

    # Columnas descriptivas para pedidos
    if not df_pedidos.empty:
        cols_ped = ["id", "fecha", "cliente_nombre", "descripcion", "filamento_nombre",
                    "gramos_usados", "horas_impresion", "costo_material", "costo_tiempo",
                    "costo_envio", "precio_venta", "ganancia", "margen_porcentaje",
                    "fecha_entrega", "estado"]
        cols_ped = [c for c in cols_ped if c in df_pedidos.columns]
        df_pedidos = df_pedidos[cols_ped]

    if not df_gastos.empty:
        cols_gas = ["id", "fecha", "categoria_nombre", "descripcion", "monto",
                    "recurrente", "frecuencia"]
        cols_gas = [c for c in cols_gas if c in df_gastos.columns]
        df_gastos = df_gastos[cols_gas]

    # Escribir Excel
    with pd.ExcelWriter(ruta_salida, engine="openpyxl") as writer:
        df_resumen.to_excel(writer, sheet_name="Resumen Mensual", index=False)
        df_pedidos.to_excel(writer, sheet_name="Pedidos", index=False)
        df_gastos.to_excel(writer, sheet_name="Gastos", index=False)

        # Aplicar formato básico
        wb = writer.book
        for sh_name in writer.sheets:
            ws = writer.sheets[sh_name]
            # Ancho automático de columnas
            for col in ws.columns:
                max_len = max((len(str(cell.value)) for cell in col if cell.value), default=10)
                ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)


def exportar_pdf_reporte(ruta_salida: str, año: int):
    """
    Exporta un reporte anual resumido en PDF.
    Incluye tabla de KPIs mensuales y totales del año.
    """
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER

    COLOR_NEGRO  = HexColor("#0F0F0F")
    COLOR_BLANCO = HexColor("#FFFFFF")
    COLOR_VERDE  = HexColor("#00FF9D")
    COLOR_GRIS   = HexColor("#F5F5F5")

    doc = SimpleDocTemplate(ruta_salida, pagesize=A4,
                            topMargin=2*cm, bottomMargin=2*cm,
                            leftMargin=2*cm, rightMargin=2*cm)
    story = []
    styles = getSampleStyleSheet()
    W = A4[0] - 4*cm

    # Título
    story.append(Paragraph(
        f"Reporte Anual {año} – PrintMoney",
        ParagraphStyle("t", fontSize=20, fontName="Helvetica-Bold",
                       textColor=COLOR_NEGRO, alignment=TA_CENTER, spaceAfter=6)
    ))
    story.append(Paragraph(
        f"Generado el {datetime.now().strftime('%d/%m/%Y %H:%M')}",
        ParagraphStyle("s", fontSize=9, textColor=HexColor("#888888"),
                       alignment=TA_CENTER, spaceAfter=4)
    ))
    story.append(Spacer(1, 0.4*cm))
    story.append(HRFlowable(width=W, thickness=2, color=COLOR_NEGRO))
    story.append(Spacer(1, 0.5*cm))

    # Tabla mensual
    headers = ["Mes", "Ingresos", "Gastos", "Ganancia Neta", "Margen %", "Pedidos"]
    rows = [headers]
    total_ingresos = total_gastos = total_ganancia = 0
    for mes in range(1, 13):
        stats = db_manager.obtener_estadisticas_mes(año, mes)
        total_ingresos += stats["ingresos"]
        total_gastos   += stats["gastos"]
        total_ganancia += stats["ganancia_neta"]
        rows.append([
            datetime(año, mes, 1).strftime("%B"),
            f"${stats['ingresos']:,.2f}",
            f"${stats['gastos']:,.2f}",
            f"${stats['ganancia_neta']:,.2f}",
            f"{stats['margen']:.1f}%",
            str(stats["num_pedidos"]),
        ])

    # Fila de totales
    margen_total = (total_ganancia / total_ingresos * 100) if total_ingresos > 0 else 0
    rows.append([
        "TOTAL", f"${total_ingresos:,.2f}", f"${total_gastos:,.2f}",
        f"${total_ganancia:,.2f}", f"{margen_total:.1f}%", ""
    ])

    tabla = Table(rows, colWidths=[W/6]*6)
    tabla.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, 0), COLOR_NEGRO),
        ("TEXTCOLOR",     (0, 0), (-1, 0), COLOR_BLANCO),
        ("FONTNAME",      (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, -1), 8),
        ("ALIGN",         (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING",    (0, 0), (-1, -1), 5),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ("ROWBACKGROUNDS",(0, 1), (-1, -2), [COLOR_GRIS, COLOR_BLANCO]),
        ("FONTNAME",      (0, -1), (-1, -1), "Helvetica-Bold"),
        ("BACKGROUND",    (0, -1), (-1, -1), HexColor("#E8FFF8")),
        ("GRID",          (0, 0), (-1, -1), 0.4, HexColor("#DDDDDD")),
    ]))
    story.append(tabla)
    story.append(Spacer(1, 1*cm))
    story.append(Paragraph("¡Gracias por usar PrintMoney! 🖨️",
                           ParagraphStyle("pie", fontSize=10, fontName="Helvetica-Bold",
                                         textColor=COLOR_NEGRO, alignment=TA_CENTER)))

    doc.build(story)

def exportar_cotizacion_pdf(ruta_salida: str, datos: dict):
    """
    Exporta una cotización sencilla en PDF.
    datos: dict con producto, material, tiempo, costo total.
    """
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.units import cm
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
    from reportlab.lib.colors import HexColor
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT

    COLOR_NEGRO  = HexColor("#0F0F0F")
    COLOR_ACCENT = HexColor("#00FF9D")

    doc = SimpleDocTemplate(ruta_salida, pagesize=A5,
                            topMargin=1.5*cm, bottomMargin=1.5*cm,
                            leftMargin=1.5*cm, rightMargin=1.5*cm)
    story = []
    
    # Título Principal
    story.append(Paragraph("COTIZACIÓN", ParagraphStyle("t", fontSize=18, fontName="Helvetica-Bold", textColor=COLOR_NEGRO, alignment=TA_CENTER)))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(f"Fecha: {datetime.now().strftime('%d/%m/%Y')}", ParagraphStyle("d", fontSize=9, textColor=HexColor("#888888"), alignment=TA_CENTER)))
    story.append(Spacer(1, 0.5*cm))
    story.append(HRFlowable(width=A5[0]-3*cm, thickness=1, color=COLOR_NEGRO))
    story.append(Spacer(1, 1*cm))

    # Detalles
    estilo_item = ParagraphStyle("item", fontSize=11, fontName="Helvetica", spaceAfter=8)
    estilo_bold = ParagraphStyle("bold", fontSize=11, fontName="Helvetica-Bold", spaceAfter=8)
    
    story.append(Paragraph(f"<b>Producto:</b> {datos.get('producto', 'Impresión 3D')}", estilo_item))
    story.append(Paragraph(f"<b>Material:</b> {datos.get('material', 'No especificado')}", estilo_item))
    story.append(Paragraph(f"<b>Tiempo Estimado:</b> {datos.get('tiempo', 'N/A')} h", estilo_item))
    
    story.append(Spacer(1, 1*cm))
    story.append(HRFlowable(width=A5[0]-3*cm, thickness=1, color=HexColor("#CCCCCC")))
    story.append(Spacer(1, 0.5*cm))

    # Total
    precio = datos.get("total", 0.0)
    story.append(Paragraph(f"TOTAL: ${precio:.2f}", ParagraphStyle("total", fontSize=16, fontName="Helvetica-Bold", textColor=COLOR_NEGRO, alignment=TA_RIGHT)))
    
    story.append(Spacer(1, 1.5*cm))
    
    # Pie de página
    nota = "<i>Nota: Esta cotización es válida por 7 días. Los tiempos pueden variar ligeramente según la carga de trabajo actual.</i>"
    story.append(Paragraph(nota, ParagraphStyle("nota", fontSize=8, textColor=HexColor("#666666"), alignment=TA_CENTER)))

    doc.build(story)
