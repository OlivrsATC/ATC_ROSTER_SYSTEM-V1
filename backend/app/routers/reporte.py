from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
import calendar
import io

from app.database import get_db
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador

router = APIRouter(prefix="/api/reportes", tags=["Reportes PDF"])

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False

CONFIG_TURNOS = {
    "SM": {"cargo": "SUPERVISOR MAÑANA", "horario": "07:00 - 13:00"},
    "SD": {"cargo": "SUPERVISOR DIA", "horario": "07:00 - 07:00"},
    "ST": {"cargo": "SUPERVISOR TARDE", "horario": "13:00 - 07:00"},
    "TM": {"cargo": "TORRE MAÑANA", "horario": "07:00 - 13:00"},
    "TT": {"cargo": "TORRE TARDE", "horario": "13:00 - 19:00"},
    "TD": {"cargo": "TORRE DIA", "horario": "07:00 - 19:00"},
    "TN": {"cargo": "TORRE NOCHE", "horario": "19:00 - 07:00"},
    "AM": {"cargo": "AREA MAÑANA", "horario": "07:00 - 13:00"},
    "AT": {"cargo": "AREA TARDE", "horario": "13:00 - 19:00"},
    "AD": {"cargo": "AREA DIA", "horario": "07:00 - 19:00"},
    "GM": {"cargo": "SUPERFICIE MAÑANA", "horario": "07:00 - 13:00"},
    "GT": {"cargo": "SUPERFICIE TARDE", "horario": "13:00 - 19:00"},
    "GD": {"cargo": "SUPERFICIE DIA", "horario": "07:00 - 19:00"},
    "OM": {"cargo": "OIA MAÑANA", "horario": "07:00 - 19:00"},
    "OT": {"cargo": "OIA TARDE", "horario": "13:00 - 19:00"},
    "ON": {"cargo": "OIA NOCHE", "horario": "19:00 - 07:00"},
    "OD": {"cargo": "OIA DIA", "horario": "07:00 - 19:00"},
    "DISP": {"cargo": "DISPONIBLE", "horario": "H24"},
    "CP": {"cargo": "COMPENSATORIO", "horario": "N/A"},
    "HU": {"cargo": "HORARIO USUAL", "horario": "07:00 - 17:00"},
    "VAC": {"cargo": "VACACIONES", "horario": "N/A"},
}

@router.get("/orden-servicio")
def generar_orden_servicio_pdf(
    fecha_inicio: date = Query(...), 
    fecha_fin: date = Query(...), 
    asesor_nav: str = Query("Técnico Asesor Servicios a la Navegación Aérea"),
    comandante_gruco: str = Query("Comandante GRUCO-11"),
    comandante_esnav: str = Query("Comandante ESNAV-115"),
    db: Session = Depends(get_db)
):
    if not REPORTLAB_DISPONIBLE:
        raise HTTPException(status_code=500, detail="La librería ReportLab no está instalada.")
    
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=landscape(letter), 
        rightMargin=15, 
        leftMargin=15, 
        topMargin=15, 
        bottomMargin=15
    )
    elements = []
    
    styles = getSampleStyleSheet()
    
    style_th = ParagraphStyle('TH', parent=styles['Normal'], fontSize=6, leading=7, fontName='Helvetica-Bold', alignment=1, textColor=colors.black)
    style_date = ParagraphStyle('TD_Date', parent=styles['Normal'], fontSize=5.5, leading=6.5, fontName='Helvetica-Bold', alignment=1)
    style_text = ParagraphStyle('TD_Text', parent=styles['Normal'], fontSize=5.5, leading=6.5, fontName='Helvetica', alignment=0)
    style_center = ParagraphStyle('TD_Center', parent=styles['Normal'], fontSize=5.5, leading=6.5, fontName='Helvetica', alignment=1)

    # 1. Cabecera principal
    header_data = [
        [Paragraph("<b>ESCUADRÓN DE NAVEGACIÓN AÉREA 115</b>", ParagraphStyle('H1', parent=styles['Normal'], fontSize=9, alignment=1, leading=10))]
    ]
    t_header = Table(header_data, colWidths=[762])
    t_header.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 3),
        ('BOTTOMPADDING', (0,0), (-1,-1), 3),
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 2))

    sub_text = f"SE NOMBRAN SERVICIOS / DISPONIBILIDADES PARA EL PERÍODO DEL {fecha_inicio.strftime('%d/%m/%Y')} AL {fecha_fin.strftime('%d/%m/%Y')}".upper()
    sub_data = [[Paragraph(f"<b>{sub_text}</b>", ParagraphStyle('H2', parent=styles['Normal'], fontSize=7, alignment=1, leading=8))]]
    t_sub = Table(sub_data, colWidths=[762])
    t_sub.setStyle(TableStyle([
        ('BOX', (0,0), (-1,-1), 1, colors.black),
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#F2F2F2')),
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    elements.append(t_sub)
    elements.append(Spacer(1, 4))

    # 2. Consultar asignaciones
    asignaciones = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= fecha_inicio,
        TurnoAsignado.fecha <= fecha_fin
    ).order_by(TurnoAsignado.fecha).all()

    dias_es = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SABADO", 6: "DOMINGO"}
    
    agrupado_por_fecha = {}
    curr_date = fecha_inicio
    while curr_date <= fecha_fin:
        agrupado_por_fecha[curr_date] = []
        curr_date += timedelta(days=1)

    for asig in asignaciones:
        if asig.fecha in agrupado_por_fecha:
            agrupado_por_fecha[asig.fecha].append(asig)

    fechas_ordenadas = list(agrupado_por_fecha.keys())
    mitad = (len(fechas_ordenadas) + 1) // 2
    fechas_izquierda = fechas_ordenadas[:mitad]
    fechas_derecha = fechas_ordenadas[mitad:]

    def construir_filas_lado(fechas_sub):
        filas_lado = []
        for f in fechas_sub:
            asigs = agrupado_por_fecha[f]
            dia_sem = dias_es[f.weekday()]
            str_fecha = f"{dia_sem}<br/>{f.strftime('%d/%m/%Y')}"
            
            if not asigs:
                filas_lado.append([
                    Paragraph(str_fecha, style_date), 
                    Paragraph("SIN ASIGNACIÓN", style_text), 
                    Paragraph("-", style_text), 
                    Paragraph("-", style_center), 
                    Paragraph("-", style_center)
                ])
            else:
                for asig in asigs:
                    ctrl = db.query(Controlador).filter(Controlador.id == asig.controlador_id).first()
                    cargo = CONFIG_TURNOS.get(asig.turno_codigo.upper(), {"cargo": asig.turno_codigo, "horario": "07:00 - 19:00"})
                    
                    nombre = f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}" if ctrl else "N/A"
                    cedula = ctrl.identificacion if ctrl else ""
                    horario = cargo["horario"]
                    cargo_txt = cargo["cargo"]
                    
                    filas_lado.append([
                        Paragraph(str_fecha, style_date),
                        Paragraph(cargo_txt, style_text),
                        Paragraph(nombre, style_text),
                        Paragraph(str(cedula), style_center),
                        Paragraph(str(horario), style_center)
                    ])
        return filas_lado

    filas_izq = construir_filas_lado(fechas_izquierda)
    filas_der = construir_filas_lado(fechas_derecha)

    max_filas = max(len(filas_izq), len(filas_der))
    vacia_fila = [
        Paragraph("", style_date), 
        Paragraph("", style_text), 
        Paragraph("", style_text), 
        Paragraph("", style_center), 
        Paragraph("", style_center)
    ]
    
    while len(filas_izq) < max_filas:
        filas_izq.append(list(vacia_fila))
    while len(filas_der) < max_filas:
        filas_der.append(list(vacia_fila))

    table_data = [[
        Paragraph("FECHA", style_th),
        Paragraph("CARGO", style_th),
        Paragraph("GRADO Y NOMBRE", style_th),
        Paragraph("CEDULA", style_th),
        Paragraph("HORARIO", style_th),
        Paragraph("FECHA", style_th),
        Paragraph("CARGO", style_th),
        Paragraph("GRADO Y NOMBRE", style_th),
        Paragraph("CEDULA", style_th),
        Paragraph("HORARIO", style_th),
    ]]

    for i in range(max_filas):
        table_data.append(filas_izq[i] + filas_der[i])

    # Anchos simétricos que suman exactamente 762 pt
    col_widths = [55, 110, 136, 40, 40, 55, 110, 136, 40, 40]

    t_style = [
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#E6E6E6')),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.black),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]

    # repeatRows=1 asegura que la cabecera se repita limpiamente si pasa a otra página
    t_main = Table(table_data, colWidths=col_widths, repeatRows=1)
    t_main.setStyle(TableStyle(t_style))
    elements.append(t_main)
    elements.append(Spacer(1, 10))

    # 3. Firmas Dinámicas
    firmas_data = [
        [
            Paragraph(f"<b>{asesor_nav}</b>", ParagraphStyle('F1', parent=styles['Normal'], fontSize=6.5, alignment=1)),
            Paragraph(f"<b>{comandante_gruco}</b>", ParagraphStyle('F2', parent=styles['Normal'], fontSize=6.5, alignment=1)),
            Paragraph(f"<b>{comandante_esnav}</b>", ParagraphStyle('F3', parent=styles['Normal'], fontSize=6.5, alignment=1))
        ],
        ["\n___________________________________", "\n___________________________________", "\n___________________________________"],
        [
            Paragraph("Técnico Asesor Serv. Nav. Aérea", ParagraphStyle('SF1', parent=styles['Normal'], fontSize=5.5, alignment=1)),
            Paragraph("Comandante GRUCO-11", ParagraphStyle('SF2', parent=styles['Normal'], fontSize=5.5, alignment=1)),
            Paragraph("Comandante ESNAV-115", ParagraphStyle('SF3', parent=styles['Normal'], fontSize=5.5, alignment=1))
        ]
    ]
    t_firmas = Table(firmas_data, colWidths=[254, 254, 254])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
        ('TOPPADDING', (0,0), (-1,-1), 0),
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
    ]))
    elements.append(t_firmas)

    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(
        buffer, 
        media_type="application/pdf", 
        headers={"Content-Disposition": "inline; filename=orden_servicio_cacom1.pdf"}
    )