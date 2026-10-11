from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
from datetime import date
from pydantic import BaseModel

from app.database import get_db
from app.models.asignacion import TurnoAsignado
from app.services.motor_reglas import MotorReglasATC

router = APIRouter(prefix="/api/turnos", tags=["Turnos"])

class TurnoCreate(BaseModel):
    controlador_id: str
    turno_codigo: str
    fecha: date

@router.post("/")
def asignar_turno(data: TurnoCreate, db: Session = Depends(get_db)):
    motor = MotorReglasATC(db)
    codigo = data.turno_codigo.upper().strip()

    # Validar aptitud psicofísica y novedades
    if not motor.validar_aptitud_y_novedades(data.controlador_id, data.fecha):
        raise HTTPException(status_code=400, detail="Aptitud psicofísica vencida o novedad activa.")

    # Validar reglas de descanso y fatiga FAC No. 061
    if not motor.verificar_regla_disponible_obligatorio(data.controlador_id, data.fecha, codigo):
        raise HTTPException(status_code=400, detail="Restricción FAC: Incumple regla de descanso obligatorio posterior a turno de tarde/noche.")

    if codigo in ["TN", "ON"] and not motor.validar_limite_noches(data.controlador_id, data.fecha, codigo):
        raise HTTPException(status_code=400, detail="Restricción FAC: Supera el límite de turnos nocturnos consecutivos permitidos.")

    # Buscar si ya existe asignación en esa fecha
    existente = db.query(TurnoAsignado).filter(
        TurnoAsignado.controlador_id == data.controlador_id,
        TurnoAsignado.fecha == data.fecha
    ).first()

    if existente:
        existente.turno_codigo = codigo
        existente.modificado_manualmente = True
    else:
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
    return {"mensaje": "Turno asignado exitosamente validando normas de fatiga."}