from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import date
import uuid
from pydantic import BaseModel

from app.database import get_db
from app.models.novedad import NovedadProgramada
from app.models.controlador import Controlador

router = APIRouter(prefix="/api/novedades", tags=["Novedades Programadas"])

class NovedadCreate(BaseModel):
    controlador_id: str
    tipo: str # Ej: "VAC", "REEN"
    asunto: str
    fecha_inicio: date
    fecha_fin: date

@router.get("/", response_model=List[dict])
def get_novedades(db: Session = Depends(get_db)):
    novedades = db.query(NovedadProgramada).all()
    resultado = []
    for n in novedades:
        ctrl = db.query(Controlador).filter(Controlador.id == n.controlador_id).first()
        nombre_ctrl = f"{ctrl.grado}. {ctrl.apellidos} {ctrl.nombres}" if ctrl else "Desconocido"
        resultado.append({
            "id": n.id,
            "controlador_id": n.controlador_id,
            "controlador_nombre": nombre_ctrl,
            "tipo": n.tipo,
            "asunto": n.asunto,
            "fecha_inicio": str(n.fecha_inicio),
            "fecha_fin": str(n.fecha_fin)
        })
    return resultado

@router.post("/")
def crear_novedad(data: NovedadCreate, db: Session = Depends(get_db)):
    if data.fecha_fin < data.fecha_inicio:
        raise HTTPException(status_code=400, detail="La fecha final no puede ser anterior a la fecha inicial.")
    
    ctrl = db.query(Controlador).filter(Controlador.id == data.controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")

    nuevo = NovedadProgramada(
        id=str(uuid.uuid4()),
        controlador_id=data.controlador_id,
        tipo=data.tipo,
        asunto=data.asunto,
        fecha_inicio=data.fecha_inicio,
        fecha_fin=data.fecha_fin
    )
    db.add(nuevo)
    db.commit()
    return {"mensaje": "Novedad programada registrada con éxito.", "id": nuevo.id}

@router.delete("/{novedad_id}")
def eliminar_novedad(novedad_id: str, db: Session = Depends(get_db)):
    novedad = db.query(NovedadProgramada).filter(NovedadProgramada.id == novedad_id).first()
    if not novedad:
        raise HTTPException(status_code=404, detail="Novedad no encontrada.")
    db.delete(novedad)
    db.commit()
    return {"mensaje": "Novedad programada eliminada con éxito."}