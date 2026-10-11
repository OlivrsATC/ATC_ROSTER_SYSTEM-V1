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
def generar_orden_servicio_pdf(fecha_inicio: date = Query(...), fecha_fin: date = Query(...), db: Session = Depends(get_db)):
    if not REPORTLAB_DISPONIBLE:
        raise HTTPException(status_code=500, detail="La librería ReportLab no está instalada. Ejecute: pip install reportlab")
    
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
    elements.append(Paragraph("COMANDANCIA CACOM-1 | ESCUADRÓN DE NAVEGACIÓN AÉREA 115", ParagraphStyle('Sub', parent=styles['Normal'], fontSize=9, alignment=1)))
    elements.append(Spacer(1, 15))
    
    elements.append(Paragraph(f"<b>ORDEN DE SERVICIO / CUADRANTE OPERATIVO</b>", styles['Heading2']))
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
    
    doc.build(elements)
    buffer.seek(0)
    
    return StreamingResponse(buffer, media_type="application/pdf", headers={"Content-Disposition": "inline; filename=orden_servicio_cacom1.pdf"})