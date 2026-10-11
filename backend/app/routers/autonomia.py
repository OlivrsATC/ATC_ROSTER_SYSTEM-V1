from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.autonomia import Autonomia
from app.models.controlador import Controlador

router = APIRouter(prefix="/api/autonomias", tags=["Autonomías"])

class AutonomiaCreate(BaseModel):
    controlador_id: str
    tipo: str  # TWR, ACC, SUP
    posicion: str
    fecha_obtencion: datetime.date
    fecha_vencimiento: datetime.date

@router.get("/{controlador_id}")
def listar_autonomias(controlador_id: str, db: Session = Depends(get_db)):
    return db.query(Autonomia).filter(Autonomia.controlador_id == controlador_id).all()

@router.post("/")
def crear_autonomia(data: AutonomiaCreate, db: Session = Depends(get_db)):
    ctrl = db.query(Controlador).filter(Controlador.id == data.controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    
    aut = Autonomia(
        id=str(uuid.uuid4()),
        controlador_id=data.controlador_id,
        tipo=data.tipo.upper().strip(),
        posicion=data.posicion.upper().strip(),
        fecha_obtencion=data.fecha_obtencion,
        fecha_vencimiento=data.fecha_vencimiento
    )
    db.add(aut)
    db.commit()
    return {"mensaje": "Autonomía asignada con éxito."}

@router.delete("/{autonomia_id}")
def eliminar_autonomia(autonomia_id: str, db: Session = Depends(get_db)):
    aut = db.query(Autonomia).filter(Autonomia.id == autonomia_id).first()
    if not aut:
        raise HTTPException(status_code=404, detail="Autonomía no encontrada.")
    db.delete(aut)
    db.commit()
    return {"mensaje": "Autonomía eliminada."}