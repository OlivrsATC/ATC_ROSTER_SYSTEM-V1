from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date
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

# Diccionario de mapeo de turnos a Cargos y Horarios Oficiales - agregar conforme a solicitud
CONFIG_TURNOS = {
    "SM": {"cargo": "SUPERVISOR MAÑANA", "horario": "07:00 - 13:00"},
    "ST": {"cargo": "SUPERVISOR TARDE", "horario": "13:00 - 07:00"},
    "TN": {"cargo": "TORRE NOCHE", "horario": "19:00 - 07:00"},
    "AM": {"cargo": "AREA MAÑANA", "horario": "07:00 - 13:00"},
    "AT": {"cargo": "AREA TARDE", "horario": "13:00 - 19:00"},
    "ON": {"cargo": "TORRE NOCHE", "horario": "19:00 - 07:00"},
    "DISP": {"cargo": "DISPONIBLE", "horario": "07:00 - 07:00"},
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
    # Se usa landscape(letter) para formato horizontal, ideal para acomodar las 5 columnas
    doc = SimpleDocTemplate(buffer, pagesize=landscape(letter), rightMargin=25, leftMargin=25, topMargin=25, bottomMargin=25)
    elements = []
    
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=13,
        alignment=1,
        textColor=colors.HexColor('#0A2540')
    )
    
    elements.append(Paragraph("FUERZA AEROESPACIAL COLOMBIANA", title_style))
    elements.append(Paragraph("COMANDO AÉREO DE COMBATE NO. 1 - ESCUADRÓN DE NAVEGACIÓN AÉREA 115", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, alignment=1)))
    elements.append(Spacer(1, 10))
    
    elements.append(Paragraph(f"<b>ORDEN DE SERVICIOS Y DISPONIBILIDADES</b>", styles['Heading2']))
    elements.append(Paragraph(f"Período evaluado: {fecha_inicio} al {fecha_fin}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Consultar asignaciones en el rango de fechas ordenadas por fecha
    asignaciones = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= fecha_inicio,
        TurnoAsignado.fecha <= fecha_fin
    ).order_by(TurnoAsignado.fecha).all()
    
    # Cabecera de la tabla con las 5 columnas requeridas
    data = [["FECHA", "CARGO", "GRADO Y NOMBRE", "CEDULA", "HORARIO"]]
    
    dias_es = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SABADO", 6: "DOMINGO"}
    
    for asig in asignaciones:
        ctrl = db.query(Controlador).filter(Controlador.id == asig.controlador_id).first()
        if not ctrl:
            continue
            
        # Formato de fecha con día de la semana en mayúsculas
        dia_sem = dias_es[asig.fecha.weekday()]
        str_fecha = f"{dia_sem}<br/>{asig.fecha.strftime('%d/%m/%Y')}"
        
        # Obtener información del turno desde el diccionario de configuración
        codigo_turno = asig.turno_codigo.upper()
        info_turno = CONFIG_TURNOS.get(codigo_turno, {"cargo": f"TURNO {codigo_turno}", "horario": "07:00 - 19:00"})
        
        grado_y_nombre = f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}"
        cedula = ctrl.identificacion
        
        data.append([
            Paragraph(str_fecha, ParagraphStyle('CenterCell', parent=styles['Normal'], fontSize=7, alignment=1)),
            Paragraph(info_turno["cargo"], ParagraphStyle('LeftCell', parent=styles['Normal'], fontSize=8, alignment=0)),
            Paragraph(grado_y_nombre, ParagraphStyle('LeftCell', parent=styles['Normal'], fontSize=8, alignment=0)),
            Paragraph(cedula, ParagraphStyle('CenterCell', parent=styles['Normal'], fontSize=8, alignment=1)),
            Paragraph(info_turno["horario"], ParagraphStyle('CenterCell', parent=styles['Normal'], fontSize=8, alignment=1))
        ])
        
    # Anchos de columna proporcionales a la hoja horizontal (Ancho total útil ~ 742 pt)
    t = Table(data, colWidths=[90, 180, 242, 110, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0A2540')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,0), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 5),
        ('TOPPADDING', (0,0), (-1,-1), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t)
    
    # Sección de Firmas Dinámicas al pie de página
    elements.append(Spacer(1, 30))
    firmas_data = [
        [
            Paragraph(f"<b>{asesor_nav}</b>", ParagraphStyle('Center', parent=styles['Normal'], fontSize=8, alignment=1)),
            Paragraph(f"<b>{comandante_gruco}</b>", ParagraphStyle('Center', parent=styles['Normal'], fontSize=8, alignment=1)),
            Paragraph(f"<b>{comandante_esnav}</b>", ParagraphStyle('Center', parent=styles['Normal'], fontSize=8, alignment=1))
        ],
        ["\n\n___________________________________", "\n\n___________________________________", "\n\n___________________________________"],
        [
            Paragraph("Técnico Asesor Serv. Nav. Aérea", ParagraphStyle('SubF', parent=styles['Normal'], fontSize=7, alignment=1)),
            Paragraph("Comandante GRUCO-11", ParagraphStyle('SubF', parent=styles['Normal'], fontSize=7, alignment=1)),
            Paragraph("Comandante ESNAV-115", ParagraphStyle('SubF', parent=styles['Normal'], fontSize=7, alignment=1))
        ]
    ]
    t_firmas = Table(firmas_data, colWidths=[240, 240, 240])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(t_firmas)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=orden_servicio_cacom1.pdf"})