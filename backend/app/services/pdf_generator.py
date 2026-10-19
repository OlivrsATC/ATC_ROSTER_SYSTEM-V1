import os
from reportlab.lib.pagesizes import letter, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from sqlalchemy.orm import Session
from datetime import date
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador

def generar_pdf_orden_servicio(db: Session, fecha_inicio: date, fecha_fin: date, output_path: str):
    """
    Genera el reporte PDF oficial de la Orden de Servicio del Escuadrón de Navegación Aérea 115
    basado en los turnos asignados entre un rango de fechas.
    """
    # Configurar página en horizontal (landscape) para mejor distribución del cuadrante
    doc = SimpleDocTemplate(
        output_path,
        pagesize=landscape(letter),
        rightMargin=30,
        leftMargin=30,
        topMargin=30,
        bottomMargin=30
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Estilos tipográficos institucionales
    titulo_style = ParagraphStyle(
        'TituloEscuadron',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=13,
        alignment=1, # Centrado
        spaceAfter=4,
        textColor=colors.HexColor("#0A2540")
    )
    
    subtitulo_style = ParagraphStyle(
        'SubTituloEscuadron',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9,
        alignment=1,
        spaceAfter=12,
        textColor=colors.HexColor("#333333")
    )
    
    celda_style = ParagraphStyle(
        'CeldaTabla',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10
    )
    
    celda_header_style = ParagraphStyle(
        'CeldaHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.whitesmoke,
        alignment=1
    )

    # Cabecera Institucional FAC
    elements.append(Paragraph("FUERZA AEROESPACIAL COLOMBIANA", titulo_style))
    elements.append(Paragraph("COMANDO AÉREO DE COMBATE NO. 1 - ESCUADRÓN DE NAVEGACIÓN AÉREA 115", titulo_style))
    elements.append(Paragraph(f"ORDEN DE SERVICIOS Y DISPONIBILIDADES / PERIODO: {fecha_inicio} AL {fecha_fin}", subtitulo_style))
    elements.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#0A2540"), spaceAfter=15))

    # Consultar asignaciones en el rango de fechas
    asignaciones = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= fecha_inicio,
        TurnoAsignado.fecha <= fecha_fin
    ).order_by(TurnoAsignado.fecha, TurnoAsignado.turno_codigo).all()

    # Construcción de la tabla de servicios
    data = [[
        Paragraph("FECHA", celda_header_style),
        Paragraph("CARGO / SERVICIO", celda_header_style),
        Paragraph("GRADO Y NOMBRE", celda_header_style),
        Paragraph("CÉDULA", celda_header_style),
        Paragraph("HORARIO", celda_header_style)
    ]]

    horarios_map = {
        "SM": ("Supervisor Mañana", "07:00 - 13:00"),
        "ST": ("Supervisor Tarde", "13:00 - 19:00"),
        "SD": ("Supervisor Día FDS", "07:00 - 19:00"),
        "TM": ("Torre Mañana", "07:00 - 13:00"),
        "TT": ("Torre Tarde", "13:00 - 19:00"),
        "TD": ("Torre Día FDS", "07:00 - 19:00"),
        "TN": ("Torre Noche", "19:00 - 07:00"),
        "AM": ("Área Mañana", "07:00 - 13:00"),
        "AT": ("Área Tarde", "13:00 - 19:00"),
        "AD": ("Área Día FDS", "07:00 - 19:00"),
        "GM": ("Superficie Mañana", "07:00 - 13:00"),
        "GT": ("Superficie Tarde", "13:00 - 19:00"),
        "GD": ("Superficie Día FDS", "07:00 - 19:00"),
        "OM": ("OIA Mañana", "07:00 - 13:00"),
        "OT": ("OIA Tarde", "13:00 - 19:00"),
        "OD": ("OIA Día FDS", "07:00 - 19:00"),
        "ON": ("OIA Noche", "19:00 - 07:00"),
        "HU": ("Horario Oficina", "07:30 - 17:00"),
        "DISP": ("Disponible 24h", "H24")
    }

    for asig in asignaciones:
        ctrl = db.query(Controlador).filter(Controlador.id == asig.controlador_id).first()
        nombre_completo = f"{ctrl.nombres} {ctrl.apellidos}" if ctrl else "N/A"
        cedula = ctrl.identificacion if ctrl else "N/A"
        
        nombre_turno, horario_str = horarios_map.get(asig.turno_codigo.upper(), (asig.turno_codigo, "07:00 - 19:00"))

        data.append([
            Paragraph(str(asig.fecha), celda_style),
            Paragraph(f"{asig.turno_codigo} - {nombre_turno}", celda_style),
            Paragraph(nombre_completo, celda_style),
            Paragraph(cedula, celda_style),
            Paragraph(horario_str, celda_style)
        ])

    t = Table(data, colWidths=[80, 190, 230, 90, 120])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#0A2540")),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CCCCCC")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    
    elements.append(t)
    elements.append(Spacer(1, 25))

    # Bloque de Firmas Institucionales al pie de página
    firmas_data = [
        [
            Paragraph("<b>TS. BUSTOS NIETO DIEGO FERNANDO</b><br/>Técnico asesor servicios a la navegación aérea", celda_style),
            Paragraph("<b>TC. KRISTIAN DARÍO ROMERO ORJUELA</b><br/>Comandante GRUCO-11", celda_style),
            Paragraph("<b>CT. ACOSTA INSUASTY VANESSA PAOLA</b><br/>Comandante ESNAV-115", celda_style)
        ]
    ]
    t_firmas = Table(firmas_data, colWidths=[240, 240, 240])
    t_firmas.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LINEABOVE', (0, 0), (-1, 0), 0.75, colors.HexColor("#333333")),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
    ]))
    
    elements.append(t_firmas)

    doc.build(elements)