from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
import calendar
from datetime import date
import uuid

from app.database import get_db
from app.models.controlador import Controlador
from app.models.asignacion import TurnoAsignado
from app.services.generador_automatico import generar_cuadrante_mes
from app.services.motor_reglas import MotorReglasATC
from pydantic import BaseModel

router = APIRouter(prefix="/api/cuadrante", tags=["Cuadrante Mensual"])

class ActualizarCeldaRequest(BaseModel):
    controlador_id: str
    fecha: date
    turno_codigo: str

@router.get("/matriz")
def obtener_matriz_mensual(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    num_dias = calendar.monthrange(anio, mes)[1]
    controladores = db.query(Controlador).all()
    matriz = []
    
    for idx, ctrl in enumerate(controladores, start=1):
        fila = {
            "id": ctrl.id,
            "numero_orden": idx,
            "nombre_completo": f"{ctrl.rol[:2]}. {ctrl.apellidos} {ctrl.nombres} ({ctrl.identificacion[-2:]})".upper(),
            "dias": {}
        }
        for dia in range(1, num_dias + 1):
            f_dia = date(anio, mes, dia)
            asig = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == f_dia
            ).first()
            fila["dias"][dia] = asig.turno_codigo if asig else ""
        matriz.append(fila)

    # Obtener los días de la semana para la cabecera
    dias_semana = []
    dias_nombres = ['L', 'M', 'M', 'J', 'V', 'S', 'D']
    for dia in range(1, num_dias + 1):
        f_dia = date(anio, mes, dia)
        dias_semana.append(dias_nombres[f_dia.weekday()])

    return {"anio": anio, "mes": mes, "total_dias": num_dias, "dias_semana": dias_semana, "filas": matriz}

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