from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
import uuid

from app.database import get_db
from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.schemas.controlador import ControladorCreate, ControladorResponse

router = APIRouter(prefix="/api/controladores", tags=["Controladores"])

@router.get("/", response_model=List[ControladorResponse])
def get_controladores(db: Session = Depends(get_db)):
    """Obtener todo el personal con sus respectivas autonomías."""
    return db.query(Controlador).all()

@router.post("/", response_model=ControladorResponse, status_code=201)
def create_controlador(data: ControladorCreate, db: Session = Depends(get_db)):
    """Registrar un nuevo controlador con sus autonomías y validación de duplicados."""
    existente = db.query(Controlador).filter(
        (Controlador.identificacion == data.identificacion) | (Controlador.email == data.email)
    ).first()
    
    if existente:
        raise HTTPException(
            status_code=400, 
            detail="Ya existe un controlador registrado con esa identificación o correo electrónico."
        )

    controlador_id = str(uuid.uuid4())
    nuevo_controlador = Controlador(
        id=controlador_id,
        identificacion=data.identificacion,
        nombres=data.nombres,
        apellidos=data.apellidos,
        email=data.email,
        rol=data.rol,
        activo=data.activo,
        aptitud_psicofisica_vencimiento=data.aptitud_psicofisica_vencimiento
    )
    db.add(nuevo_controlador)

    # Registrar autonomías asociadas
    if data.autonomias:
        for aut in data.autonomias:
            nueva_autonomia = Autonomia(
                id=str(uuid.uuid4()),
                controlador_id=controlador_id,
                tipo=aut.tipo,
                posicion=aut.posicion,
                fecha_obtencion=aut.fecha_obtencion,
                fecha_vencimiento=aut.fecha_vencimiento
            )
            db.add(nueva_autonomia)

    db.commit()
    db.refresh(nuevo_controlador)
    return nuevo_controlador

@router.delete("/{controlador_id}", status_code=200)
def delete_controlador(controlador_id: str, db: Session = Depends(get_db)):
    """Eliminar un controlador y sus autonomías asociadas (Cascade)."""
    controlador = db.query(Controlador).filter(Controlador.id == controlador_id).first()
    if not controlador:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    
    db.delete(controlador)
    db.commit()
    return {"mensaje": "Controlador eliminado exitosamente."}