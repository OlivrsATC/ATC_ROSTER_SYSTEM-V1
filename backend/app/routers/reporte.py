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
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False

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
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
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
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph(f"<b>ORDEN DE SERVICIOS Y DISPONIBILIDADES</b>", styles['Heading2']))
    elements.append(Paragraph(f"Período evaluado: {fecha_inicio} al {fecha_fin}", styles['Normal']))
    elements.append(Spacer(1, 10))
    
    # Consultar asignaciones en el rango de fechas
    asignaciones = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= fecha_inicio,
        TurnoAsignado.fecha <= fecha_fin
    ).order_by(TurnoAsignado.fecha).all()
    
    data = [["Fecha", "Grado, Apellidos y Nombres", "Turno"]]
    for asig in asignaciones:
        ctrl = db.query(Controlador).filter(Controlador.id == asig.controlador_id).first()
        nombre = f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}" if ctrl else "Desconocido"
        data.append([str(asig.fecha), nombre, asig.turno_codigo])
        
    t = Table(data, colWidths=[100, 320, 80])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0A2540')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 6),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    elements.append(t)
    
    # Sección de Firmas Dinámicas al pie de página
    elements.append(Spacer(1, 40))
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
    t_firmas = Table(firmas_data, colWidths=[175, 175, 170])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    elements.append(t_firmas)
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=orden_servicio_cacom1.pdf"})