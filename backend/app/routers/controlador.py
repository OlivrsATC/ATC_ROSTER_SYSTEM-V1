from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import uuid
from pydantic import BaseModel

from app.database import get_db
from app.models.controlador import Controlador

router = APIRouter(prefix="/api/controladores", tags=["Controladores"])

class ControladorCreate(BaseModel):
    identificacion: str
    grado: str
    numero_curso: Optional[str] = None
    nombres: str
    apellidos: str
    email: str
    rol: str = "CONTROLADOR"
    aptitud_psicofisica_vencimiento: date
    activo: bool = True
    autonomias: Optional[list] = []

@router.get("/", response_model=List[dict])
def get_controladores(db: Session = Depends(get_db)):
    controladores = db.query(Controlador).all()
    resultado = []
    for c in controladores:
        resultado.append({
            "id": c.id,
            "identificacion": c.identificacion,
            "grado": c.grado,
            "numero_curso": c.numero_curso,
            "nombres": c.nombres,
            "apellidos": c.apellidos,
            "email": c.email,
            "rol": c.rol,
            "aptitud_psicofisica_vencimiento": str(c.aptitud_psicofisica_vencimiento),
            "activo": c.activo
        })
    return resultado

@router.post("/")
def crear_controlador(data: ControladorCreate, db: Session = Depends(get_db)):
    existing = db.query(Controlador).filter(Controlador.identificacion == data.identificacion).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un controlador registrado con esta identificación.")
    
    nuevo = Controlador(
        id=str(uuid.uuid4()),
        identificacion=data.identificacion,
        grado=data.grado,
        numero_curso=data.numero_curso,
        nombres=data.nombres,
        apellidos=data.apellidos,
        email=data.email,
        rol=data.rol,
        aptitud_psicofisica_vencimiento=data.aptitud_psicofisica_vencimiento,
        activo=data.activo
    )
    db.add(nuevo)
    db.commit()
    return {"mensaje": "Controlador registrado exitosamente.", "id": nuevo.id}

@router.delete("/{controlador_id}")
def eliminar_controlador(controlador_id: str, db: Session = Depends(get_db)):
    ctrl = db.query(Controlador).filter(Controlador.id == controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    db.delete(ctrl)
    db.commit()
    return {"mensaje": "Controlador eliminado con éxito."}