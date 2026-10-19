from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.models.asignacion import TurnoAsignado
from app.schemas.asignacion import TurnoAsignadoCreate, TurnoAsignadoResponse
from app.services.motor_reglas import MotorReglasATC

router = APIRouter(prefix="/api/turnos", tags=["Asignación y Turnos"])

@router.get("/", response_model=List[TurnoAsignadoResponse])
def get_turnos_asignados(db: Session = Depends(get_db)):
    """Obtener todos los turnos asignados en la malla."""
    return db.query(TurnoAsignado).all()

@router.post("/", response_model=TurnoAsignadoResponse, status_code=201)
def asignar_turno(data: TurnoAsignadoCreate, db: Session = Depends(get_db)):
    """Asignar un turno validando rigurosamente las reglas de fatiga, descansos y novedades."""
    motor = MotorReglasATC(db)

    # 1. Validar Aptitud y Novedades
    if not motor.validar_aptitud_y_novedades(data.controlador_id, data.fecha):
        raise HTTPException(
            status_code=400,
            detail="Asignación bloqueada: El controlador presenta novedades activas (vacaciones/incapacidad) o aptitud psicofísica vencida."
        )

    # 2. Validar Regla del Disponible (DISP) post-tarde/noche/HU
    if not motor.verificar_regla_disponible_obligatorio(data.controlador_id, data.fecha, data.turno_codigo):
        raise HTTPException(
            status_code=400,
            detail="Violación de regla operativa: El controlador requiere obligatoriamente un turno 'DISP' (Disponible) en esta fecha debido al turno de tarde, noche u oficina anterior."
        )

    # 3. Validar Límite de Noches Consecutivas
    if not motor.validar_limite_noches(data.controlador_id, data.fecha, data.turno_codigo):
        raise HTTPException(
            status_code=400,
            detail="Violación de norma de fatiga: Se ha superado el límite máximo de turnos de noche consecutivos permitidos (máx 2 entre semana, 3 en FDS)."
        )

    # Registrar el turno si cumple todas las normativas
    nuevo_turno = TurnoAsignado(
        id=str(uuid.uuid4()),
        controlador_id=data.controlador_id,
        turno_codigo=data.turno_codigo.upper(),
        fecha=data.fecha,
        asignado_automaticamente=True,
        modificado_manualmente=False
    )
    
    db.add(nuevo_turno)
    db.commit()
    db.refresh(nuevo_turno)
    return nuevo_turno