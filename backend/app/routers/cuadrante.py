from fastapi import APIRouter, Depends, HTTPException, Query, responses 
from sqlalchemy.orm import Session
from sqlalchemy import extract
import calendar
from datetime import date, timedelta
import uuid

from app.database import get_db
from app.models.controlador import Controlador
from app.models.asignacion import TurnoAsignado
from app.models.novedad import NovedadProgramada
from app.services.generador_automatico import generar_cuadrante_mes
from app.services.motor_reglas import MotorReglasATC
from pydantic import BaseModel

router = APIRouter(prefix="/api/cuadrante", tags=["Cuadrante Mensual"])

class ActualizarCeldaRequest(BaseModel):
    controlador_id: str
    fecha: date
    turno_codigo: str

def es_festivo_colombia(f: date) -> bool:
    """Calcula festivos fijos y móviles de Colombia para el año 2026"""
    fijos = [(1, 1), (5, 1), (7, 20), (8, 7), (12, 8), (12, 25)]
    if (f.month, f.day) in fijos:
        return True
    
    # Festivos móviles de Colombia 2026 (Pascua = 5 de abril de 2026)
    pascua = date(2026, 4, 5)
    movibles = [
        date(2026, 1, 12),  # Reyes Magos
        date(2026, 3, 23),  # San José
        pascua - timedelta(days=3),  # Jueves Santo
        pascua - timedelta(days=2),  # Viernes Santo
        pascua + timedelta(days=43), # Ascensión del Señor
        pascua + timedelta(days=64), # Corpus Christi
        pascua + timedelta(days=71), # Sagrado Corazón
        date(2026, 6, 29),  # San Pedro y San Pablo
        date(2026, 8, 17),  # Asunción de la Virgen
        date(2026, 10, 12), # Día de la Raza
        date(2026, 11, 2),  # Todos los Santos
        date(2026, 11, 16), # Independencia de Cartagena
    ]
    return f in movibles

@router.get("/matriz")
def obtener_matriz_mensual(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    num_dias = calendar.monthrange(anio, mes)[1]
    controladores = db.query(Controlador).order_by(Controlador.orden.asc()).all()
    matriz = []
    
    for idx, ctrl in enumerate(controladores, start=1):
        # Formato militar: Grado, Apellidos, Nombres y Número de Curso
        curso_str = f" - {ctrl.numero_curso}" if ctrl.numero_curso else ""
        
        # Obtener las novedades programadas con antelación para este controlador
        novedades_ctrl = db.query(NovedadProgramada).filter(
            NovedadProgramada.controlador_id == ctrl.id
        ).all()

        fila = {
            "id": ctrl.id,
            "numero_orden": idx,
            "nombre_completo": f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}{curso_str}".upper(),
            "dias": {}
        }
        
        for dia in range(1, num_dias + 1):
            f_dia = date(anio, mes, dia)
            
            # Verificar si la fecha cae dentro de una novedad programada (Vacaciones, Cursos, etc.)
            codigo_novedad = ""
            for nov in novedades_ctrl:
                if nov.fecha_inicio <= f_dia <= nov.fecha_fin:
                    codigo_novedad = nov.tipo
                    break
            
            if codigo_novedad:
                fila["dias"][dia] = codigo_novedad
            else:
                asig = db.query(TurnoAsignado).filter(
                    TurnoAsignado.controlador_id == ctrl.id,
                    TurnoAsignado.fecha == f_dia
                ).first()
                fila["dias"][dia] = asig.turno_codigo if asig else ""
                
        matriz.append(fila)

    # Obtener los días de la semana y verificar si son fines de semana o festivos
    dias_info = []
    dias_nombres = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
    for dia in range(1, num_dias + 1):
        f_dia = date(anio, mes, dia)
        wd = f_dia.weekday()
        es_fin_semana = wd >= 5
        es_fest = es_festivo_colombia(f_dia)
        
        dias_info.append({
            "dia": dia,
            "letra": dias_nombres[wd],
            "es_especial": es_fin_semana or es_fest
        })

    return {
        "anio": anio, 
        "mes": mes, 
        "total_dias": num_dias, 
        "dias_info": dias_info, 
        "dias_semana": [d["letra"] for d in dias_info], # Compatibilidad
        "filas": matriz
    }

@router.post("/celda")
def actualizar_celda_cuadrante(data: ActualizarCeldaRequest, db: Session = Depends(get_db)):
    """Actualiza o asigna el turno de una celda específica evaluando el motor de reglas."""
    motor = MotorReglasATC(db)
    codigo = data.turno_codigo.upper().strip()

    # Si no es vacío ni VAC, validar reglas de fatiga opcionales
    if codigo and codigo != "VAC":
        if not motor.validar_aptitud_y_novedades(data.controlador_id, data.fecha):
            raise HTTPException(status_code=400, detail="Aptitud psicofísica vencida o novedad activa.")

    # Buscar si ya existe asignación en esa fecha para este controlador
    asig = db.query(TurnoAsignado).filter(
        TurnoAsignado.controlador_id == data.controlador_id,
        TurnoAsignado.fecha == data.fecha
    ).first()

    if asig:
        if codigo == "":
            db.delete(asig)
        else:
            asig.turno_codigo = codigo
            asig.modificado_manualmente = True
    else:
        if codigo != "":
            nuevo = TurnoAsignado(
                id=str(uuid.uuid4()),
                controlador_id=data.controlador_id,
                turno_codigo=codigo,
                fecha=data.fecha,
                asignado_automaticamente=False,
                modificado_manualmente=True
            )
            db.add(nuevo)

    db.commit()
    return {"mensaje": "Celda actualizada con éxito."}

@router.post("/generar")
def generar(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    return generar_cuadrante_mes(db, anio, mes)

@router.delete("/limpiar")
def deshacer_cuadrante_mes(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    """Borra todos los turnos asignados en el mes y año especificados (Deshacer)"""
    eliminados = db.query(TurnoAsignado).filter(
        extract('year', TurnoAsignado.fecha) == anio,
        extract('month', TurnoAsignado.fecha) == mes
    ).delete(synchronize_session=False)
    db.commit()
    return {"mensaje": f"Se ha deshecho la programación eliminando {eliminados} turnos del mes {mes}."}