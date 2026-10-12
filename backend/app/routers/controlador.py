from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import date
import uuid
from pydantic import BaseModel

from app.database import get_db
from app.models.controlador import Controlador

# Inicialización del enrutador de FastAPI con su prefijo base y etiqueta de documentación
router = APIRouter(prefix="/api/controladores", tags=["Controladores"])

# ============================================================================
# ESQUEMAS PYDANTIC (Validación de Datos de Entrada)
# ============================================================================

class ControladorCreate(BaseModel):
    """Esquema para validar la información requerida al registrar un nuevo controlador."""
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

class ActualizarAptitudRequest(BaseModel):
    """Esquema para validar la nueva fecha al actualizar la aptitud psicofísica."""
    aptitud_psicofisica_vencimiento: date

class ReordenarRequest(BaseModel):
    """Esquema para validar la lista de IDs al actualizar el orden por drag and drop."""
    controladores_ids: List[str]

class ControladorUpdate(BaseModel):
    """Esquema para validar la actualización de datos generales del controlador."""
    identificacion: Optional[str] = None
    grado: Optional[str] = None
    numero_curso: Optional[str] = None
    nombres: Optional[str] = None
    apellidos: Optional[str] = None
    email: Optional[str] = None
    rol: Optional[str] = None
    activo: Optional[bool] = None

# ============================================================================
# ENDPOINTS / RUTAS DE CONTROLADORES
# ============================================================================

@router.get("/", response_model=List[dict])
def get_controladores(db: Session = Depends(get_db)):
    """
    Obtiene la lista completa de controladores ordenados estrictamente 
    por la jerarquía guardada en la base de datos (campo orden).
    """
    controladores = db.query(Controlador).order_by(Controlador.orden.asc()).all()
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
    """
    Registra un nuevo controlador ubicándolo automáticamente al final de la lista 
    (última posición de orden disponible) para no alterar tu jerarquía actual.
    """
    existing = db.query(Controlador).filter(Controlador.identificacion == data.identificacion).first()
    if existing:
        raise HTTPException(status_code=400, detail="Ya existe un controlador registrado con esta identificación.")
    
    total_existentes = db.query(Controlador).count()
    
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
        activo=data.activo,
        orden=total_existentes + 1
    )
    db.add(nuevo)
    db.commit()
    return {"mensaje": "Controlador registrado exitosamente.", "id": nuevo.id}

@router.put("/ordenar")
def reordenar_controladores(data: ReordenarRequest, db: Session = Depends(get_db)):
    """
    Actualiza de manera permanente el número de orden de cada controlador 
    según los movimientos realizados con Drag and Drop en la interfaz.
    """
    for index, ctrl_id in enumerate(data.controladores_ids):
        ctrl = db.query(Controlador).filter(Controlador.id == ctrl_id).first()
        if ctrl:
            ctrl.orden = index + 1
    db.commit()
    return {"mensaje": "Orden actualizado y fijado con éxito."}

@router.put("/{controlador_id}/aptitud")
def actualizar_aptitud_psicofisica(controlador_id: str, data: ActualizarAptitudRequest, db: Session = Depends(get_db)):
    """
    Actualiza exclusivamente la fecha de vencimiento de la aptitud psicofísica 
    de un controlador específico.
    """
    ctrl = db.query(Controlador).filter(Controlador.id == controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    
    ctrl.aptitud_psicofisica_vencimiento = data.aptitud_psicofisica_vencimiento
    db.commit()
    return {"mensaje": "Fecha de aptitud psicofísica actualizada con éxito."}

@router.put("/{controlador_id}")
def actualizar_controlador(controlador_id: str, data: ControladorUpdate, db: Session = Depends(get_db)):
    """
    Actualiza la información general de un controlador existente.
    """
    ctrl = db.query(Controlador).filter(Controlador.id == controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    
    # Validar si se está cambiando la identificación y si ya existe en otro registro
    if data.identificacion and data.identificacion != ctrl.identificacion:
        existing = db.query(Controlador).filter(Controlador.identificacion == data.identificacion).first()
        if existing:
            raise HTTPException(status_code=400, detail="Ya existe otro controlador con esta identificación.")
        ctrl.identificacion = data.identificacion

    if data.grado is not None:
        ctrl.grado = data.grado
    if data.numero_curso is not None:
        ctrl.numero_curso = data.numero_curso
    if data.nombres is not None:
        ctrl.nombres = data.nombres
    if data.apellidos is not None:
        ctrl.apellidos = data.apellidos
    if data.email is not None:
        ctrl.email = data.email
    if data.rol is not None:
        ctrl.rol = data.rol
    if data.activo is not None:
        ctrl.activo = data.activo

    db.commit()
    return {"mensaje": "Datos del controlador actualizados con éxito."}

@router.delete("/{controlador_id}")
def eliminar_controlador(controlador_id: str, db: Session = Depends(get_db)):
    """
    Elimina del sistema a un controlador basándose en su ID único.
    """
    ctrl = db.query(Controlador).filter(Controlador.id == controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    db.delete(ctrl)
    db.commit()
    return {"mensaje": "Controlador eliminado con éxito."}