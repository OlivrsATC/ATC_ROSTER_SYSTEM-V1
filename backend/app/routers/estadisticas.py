from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import date, timedelta
import calendar
import io

from app.database import get_db
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador

router = APIRouter(prefix="/api/reportes", tags=["Reportes y Estadísticas"])

try:
    from reportlab.lib.pagesizes import letter, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    REPORTLAB_DISPONIBLE = True
except ImportError:
    REPORTLAB_DISPONIBLE = False

# Diccionario de configuración de turnos oficiales
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
    "DISP": {"cargo": "DISPONIBLE", "horario": "07:00 - 07:00"},
    "CP": {"cargo": "COMPENSATORIO", "horario": "N/A"},
    "HU": {"cargo": "HORARIO USUAL / ADMINISTRATIVO", "horario": "07:00 - 17:00"},
    "VAC": {"cargo": "VACACIONES", "horario": "N/A"},
}

@router.get("/estadisticas-operativas")
def obtener_estadisticas_operativas(
    anio: int = Query(2026), 
    mes: int = Query(9), 
    db: Session = Depends(get_db)
):
    """
    Retorna las estadísticas del mes:
    - Días prestados por autonomías por cada controlador.
    - Fines de semana trabajados vs descansados.
    - Controlador que ha prestado más servicios por cada tipo de autonomía.
    """
    turno_a_autonomia = {
        "SM": "SUP", "ST": "SUP", "SD": "SUP",
        "TM": "TWR", "TT": "TWR", "TN": "TWR", "TD": "TWR",
        "AM": "ACC", "AT": "ACC", "AD": "ACC",
        "GM": "GND", "GT": "GND", "GD": "GND",
        "OM": "OIA", "OT": "OIA", "ON": "OIA", "OD": "OIA"
    }

    # Excluir al Jefe de Tránsito de las estadísticas operativas
    controladores = db.query(Controlador).filter(
        Controlador.activo == True,
        ~Controlador.rol.ilike("%JEFE_TRANSITO%"),
        ~Controlador.rol.ilike("%JEFE DE TRANSITO%")
    ).all()

    inicio_mes = date(anio, mes, 1)
    num_dias = calendar.monthrange(anio, mes)[1]
    fin_mes = date(anio, mes, num_dias)

    asignaciones = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= inicio_mes,
        TurnoAsignado.fecha <= fin_mes
    ).all()

    asig_map = {(a.controlador_id, a.fecha): a.turno_codigo for a in asignaciones}

    # Identificar fines de semana (Sábado y Domingo) del mes
    fines_de_semana = []
    curr = inicio_mes
    while curr <= fin_mes:
        if curr.weekday() == 5:  # Sábado
            domingo = curr + timedelta(days=1)
            if domingo <= fin_mes:
                fines_de_semana.append((curr, domingo))
        curr += timedelta(days=1)

    stats_por_controlador = []
    autonomia_conteo_global = {"SUP": {}, "TWR": {}, "ACC": {}, "GND": {}, "OIA": {}}

    for ctrl in controladores:
        autonomias_dias = {"SUP": 0, "TWR": 0, "ACC": 0, "GND": 0, "OIA": 0}
        fs_trabajados = 0
        fs_descansados = 0

        # Evaluar Fines de Semana
        for sabado, domingo in fines_de_semana:
            t_sab = asig_map.get((ctrl.id, sabado), "")
            t_dom = asig_map.get((ctrl.id, domingo), "")
            
            if t_sab in turno_a_autonomia or t_dom in turno_a_autonomia:
                fs_trabajados += 1
            else:
                fs_descansados += 1

        # Evaluar días del mes por autonomía
        for dia in range(1, num_dias + 1):
            f_dia = date(anio, mes, dia)
            t_cod = asig_map.get((ctrl.id, f_dia), "")
            auto = turno_a_autonomia.get(t_cod)
            
            if auto:
                autonomias_dias[auto] += 1
                if ctrl.id not in autonomia_conteo_global[auto]:
                    autonomia_conteo_global[auto][ctrl.id] = 0
                autonomia_conteo_global[auto][ctrl.id] += 1

        stats_por_controlador.append({
            "id": ctrl.id,
            "nombre_completo": f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}".upper(),
            "dias_por_autonomia": autonomias_dias,
            "fines_de_semana_trabajados": fs_trabajados,
            "fines_de_semana_descansados": fs_descansados
        })

    # Determinar quién ha prestado más servicios por cada autonomía
    lideres_por_autonomia = {}
    for auto, conteos in autonomia_conteo_global.items():
        if conteos:
            top_ctrl_id = max(conteos, key=conteos.get)
            top_ctrl = db.query(Controlador).filter(Controlador.id == top_ctrl_id).first()
            lideres_por_autonomia[auto] = {
                "controlador": f"{top_ctrl.grado}. {top_ctrl.apellidos} {top_ctrl.nombres}".upper() if top_ctrl else "N/A",
                "servicios": conteos[top_ctrl_id]
            }
        else:
            lideres_por_autonomia[auto] = {"controlador": "Ninguno", "servicios": 0}

    return {
        "anio": anio,
        "mes": mes,
        "lideres_por_autonomia": lideres_por_autonomia,
        "estadisticas_detalladas": stats_por_controlador
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
    
    asignaciones = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= fecha_inicio,
        TurnoAsignado.fecha <= fecha_fin
    ).order_by(TurnoAsignado.fecha).all()
    
    data = [["FECHA", "CARGO", "GRADO Y NOMBRE", "CEDULA", "HORARIO"]]
    dias_es = {0: "LUNES", 1: "MARTES", 2: "MIERCOLES", 3: "JUEVES", 4: "VIERNES", 5: "SABADO", 6: "DOMINGO"}
    
    for asig in asignaciones:
        ctrl = db.query(Controlador).filter(Controlador.id == asig.controlador_id).first()
        if not ctrl:
            continue
                
        dia_sem = dias_es[asig.fecha.weekday()]
        str_fecha = f"{dia_sem}<br/>{asig.fecha.strftime('%d/%m/%Y')}"
        
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
        
    t = Table(data, colWidths=[85, 180, 277, 100, 100])
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