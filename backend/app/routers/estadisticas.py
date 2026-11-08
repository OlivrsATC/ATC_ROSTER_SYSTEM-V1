from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from datetime import date, timedelta
import calendar

from app.database import get_db
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador

router = APIRouter(prefix="/api/reportes", tags=["Reportes y Estadísticas"])

@router.get("/estadisticas-graficas")
def obtener_estadisticas_graficas(
    anio: int = Query(2026), 
    mes: int = Query(11), 
    db: Session = Depends(get_db)
):
    """
    Retorna los datos procesados para generar gráficas de barras:
    - Conteo de servicios específicos por controlador (filtrables).
    - Estadísticas de fines de semana trabajados vs descansados.
    """
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

    # Definir categorías de servicios operativas válidas para contar
    turnos_operativos = [
        "SM", "SD", "ST", "TM", "TT", "TD", "TN", 
        "AM", "AT", "AD", "GM", "GT", "GD", 
        "OM", "OT", "ON", "OD", "DISP"
    ]

    reporte_controladores = []

    for ctrl in controladores:
        nombre_completo = f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}".upper()
        
        # Conteo de servicios por código
        servicios_conteo = {t: 0 for t in turnos_operativos}
        
        fs_trabajados = 0
        fs_descansados = 0

        # Evaluar Fines de Semana
        for sabado, domingo in fines_de_semana:
            t_sab = asig_map.get((ctrl.id, sabado), "")
            t_dom = asig_map.get((ctrl.id, domingo), "")
            
            if t_sab in turnos_operativos or t_dom in turnos_operativos:
                fs_trabajados += 1
            else:
                fs_descansados += 1

        # Evaluar servicios del mes
        for dia in range(1, num_dias + 1):
            f_dia = date(anio, mes, dia)
            t_cod = asig_map.get((ctrl.id, f_dia), "").upper()
            if t_cod in servicios_conteo:
                servicios_conteo[t_cod] += 1

        reporte_controladores.append({
            "id": ctrl.id,
            "nombre": nombre_completo,
            "servicios": servicios_conteo,
            "fines_de_semana_trabajados": fs_trabajados,
            "fines_de_semana_descansados": fs_descansados
        })

    return {
        "anio": anio,
        "mes": mes,
        "data": reporte_controladores
    }