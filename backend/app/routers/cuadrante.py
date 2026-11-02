from fastapi import APIRouter, Depends, HTTPException, Query
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
        curso_str = f" - {ctrl.numero_curso}" if ctrl.numero_curso else ""
        
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
        "dias_semana": [d["letra"] for d in dias_info],
        "filas": matriz
    }


@router.post("/celda")
def actualizar_celda_cuadrante(data: ActualizarCeldaRequest, db: Session = Depends(get_db)):
    """
    Endpoint único y consolidado para actualizar celdas de forma manual.
    Valida:
    1. No duplicar posiciones operativas el mismo día.
    2. Autonomías vigentes y activas (Regla 5).
    3. Aptitud psicofísica y fatiga por turnos nocturnos consecutivos (Regla 1).
    """
    motor = MotorReglasATC(db)
    codigo = data.turno_codigo.strip().upper() if data.turno_codigo else ""

    # Códigos de turno administrativos, novedades o descansos que SÍ se pueden repetir el mismo día
    turnos_permitidos_duplicar = {
        "", "HU", "CP", "DISP", "VAC", "VACACIONES", "REEN", "ENTTO", 
        "PAT", "VEL", "VELASQUEZ", "CURSO", "INS"
    }

    # 1. REGLA: Impedir posiciones operativas duplicadas en el mismo día
    if codigo and codigo not in turnos_permitidos_duplicar:
        turno_existente = db.query(TurnoAsignado).filter(
            TurnoAsignado.fecha == data.fecha,
            TurnoAsignado.turno_codigo == codigo,
            TurnoAsignado.controlador_id != data.controlador_id
        ).first()

        if turno_existente:
            ctrl_ocupante = db.query(Controlador).filter(Controlador.id == turno_existente.controlador_id).first()
            nombre_ocupante = f"{ctrl_ocupante.grado} {ctrl_ocupante.apellidos}" if ctrl_ocupante else "otro controlador"
            raise HTTPException(
                status_code=400,
                detail=f"⚠️ La posición operativa '{codigo}' ya está asignada el día {data.fecha.strftime('%d/%m/%Y')} a {nombre_ocupante}. No se pueden repetir posiciones operativas el mismo día."
            )

    # 2. REGLAS DEL MOTOR: Autonomías, Aptitud y Fatiga
    if codigo and codigo not in {"HU", "CP", "DISP", "VAC", "VACACIONES", "REEN", "ENTTO", "PAT", "VEL", "VELASQUEZ"}:
        # Validar Autonomía (Regla 5)
        if not motor.validar_autonomia(data.controlador_id, codigo, data.fecha):
            raise HTTPException(
                status_code=400, 
                detail=f"⚠️ Alerta de Autonomía: El controlador seleccionado no cuenta con la autonomía requerida y activa para cubrir el turno '{codigo}'."
            )

        # Validar Aptitud y Novedades
        if not motor.validar_aptitud_y_novedades(data.controlador_id, data.fecha):
            raise HTTPException(
                status_code=400, 
                detail="⚠️ Restricción: El controlador presenta aptitud psicofísica vencida o novedad activa en la fecha."
            )

        # Validar Límite de Nocturnos Consecutivos (Regla 1)
        if not motor.validar_nocturnos_consecutivos(data.controlador_id, data.fecha, codigo):
            raise HTTPException(
                status_code=400, 
                detail="⚠️ Restricción Operativa (Fatiga): Excede el límite permitido de turnos nocturnos consecutivos."
            )

    # 3. Guardar, actualizar o eliminar la asignación en la base de datos
    asig = db.query(TurnoAsignado).filter(
        TurnoAsignado.controlador_id == data.controlador_id,
        TurnoAsignado.fecha == data.fecha
    ).first()

    if not codigo:
        if asig:
            db.delete(asig)
            db.commit()
        return {"mensaje": "Turno eliminado con éxito."}

    if asig:
        asig.turno_codigo = codigo
        asig.modificado_manualmente = True
    else:
        asig = TurnoAsignado(
            id=str(uuid.uuid4()),
            controlador_id=data.controlador_id,
            fecha=data.fecha,
            turno_codigo=codigo,
            asignado_automaticamente=False,
            modificado_manualmente=True
        )
        db.add(asig)

    db.commit()
    return {"mensaje": "Celda actualizada correctamente."}


@router.post("/generar")
def generar(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    """Ejecuta el generador automático aplicando el nuevo motor de reglas."""
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