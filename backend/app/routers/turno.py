from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from datetime import date
from pydantic import BaseModel
import uuid

from app.database import get_db
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador
from app.services.motor_reglas import MotorReglasATC

# Asegúrate de usar el prefijo de tu router
router = APIRouter(prefix="/api/cuadrante", tags=["Cuadrante"])

class ActualizarCeldaRequest(BaseModel):
    controlador_id: str
    fecha: date
    turno_codigo: str

@router.post("/celda")
def actualizar_celda_manual(data: ActualizarCeldaRequest, db: Session = Depends(get_db)):
    motor = MotorReglasATC(db)
    
    # Códigos de turno administrativos, novedades o descansos que SÍ se pueden repetir el mismo día
    turnos_permitidos_duplicar = {
        "", "HU", "CP", "DISP", "VAC", "VACACIONES", "REEN", "ENTTO", 
        "PAT", "VEL", "VELASQUEZ", "CURSO", "INS"
    }
    
    codigo = data.turno_codigo.strip().upper() if data.turno_codigo else ""

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
                detail=f"La posición '{codigo}' ya está asignada el día {data.fecha.strftime('%d/%m/%Y')} a {nombre_ocupante}. No se pueden repetir posiciones operativas el mismo día."
            )

    # 2. REGLA: Validar autonomía activa y no vencida mediante el Motor de Reglas
    if codigo and codigo not in {"HU", "CP", "DISP", "VAC", "VACACIONES", "REEN", "ENTTO", "PAT", "VEL", "VELASQUEZ"}:
        tiene_autonomia = motor.validar_autonomia(data.controlador_id, codigo, data.fecha)
        if not tiene_autonomia:
            raise HTTPException(
                status_code=400,
                detail=f"El controlador no cuenta con la autonomía habilitada/activa para cubrir el turno '{codigo}'."
            )

    # 3. Guardar o actualizar la asignación
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
    return {"mensaje": "Turno asignado correctamente."}