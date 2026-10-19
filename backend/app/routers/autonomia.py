# Importaciones necesarias de FastAPI, SQLAlchemy, utilidades y Pydantic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
import uuid
import datetime
from pydantic import BaseModel

from app.database import get_db
from app.models.autonomia import Autonomia
from app.models.controlador import Controlador

# Inicialización del enrutador con un prefijo y una etiqueta para la documentación automática (Swagger)
router = APIRouter(prefix="/api/autonomias", tags=["Autonomías"])

# Esquema de Pydantic para validar los datos al CREAR una nueva autonomía
class AutonomiaCreate(BaseModel):
    controlador_id: str
    tipo: str  # Tipo de autonomía (Ej: TWR, ACC, SUP, GND, OIA, INS)
    fecha_obtencion: datetime.date
    fecha_vencimiento: datetime.date

# Esquema de Pydantic para validar los datos al CAMBIAR el estado (habilitar/deshabilitar)
class EstadoAutonomiaRequest(BaseModel):
    activa: bool

# Endpoint GET: Listar todas las autonomías registradas para un controlador específico
@router.get("/{controlador_id}")
def listar_autonomias(controlador_id: str, db: Session = Depends(get_db)):
    # Consulta en la base de datos filtrando por el ID del controlador
    return db.query(Autonomia).filter(Autonomia.controlador_id == controlador_id).all()

# Endpoint POST: Registrar o crear una nueva autonomía para un controlador
@router.post("/")
def crear_autonomia(data: AutonomiaCreate, db: Session = Depends(get_db)):
    # Verificamos primero si el controlador realmente existe en la base de datos
    ctrl = db.query(Controlador).filter(Controlador.id == data.controlador_id).first()
    if not ctrl:
        raise HTTPException(status_code=404, detail="Controlador no encontrado.")
    
    # Creamos la instancia del modelo Autonomia con los datos validados
    aut = Autonomia(
        id=str(uuid.uuid4()),                    # Generamos un ID único universal (UUID)
        controlador_id=data.controlador_id,
        tipo=data.tipo.upper().strip(),          # Convertimos a mayúsculas y eliminamos espacios extra
        posicion="",                             # Campo de posición vacio por ser innecesario actualmente
        fecha_obtencion=data.fecha_obtencion,
        fecha_vencimiento=data.fecha_vencimiento,
        activa=True                              # Por defecto, toda nueva autonomía nace habilitada
    )
    db.add(aut)      # Añadimos a la sesión de la base de datos
    db.commit()      # Guardamos los cambios permanentemente
    return {"mensaje": "Autonomía asignada con éxito."}

# Endpoint PUT: Habilitar o deshabilitar una autonomía existente sin eliminarla
@router.put("/{autonomia_id}/estado")
def cambiar_estado_autonomia(autonomia_id: str, data: EstadoAutonomiaRequest, db: Session = Depends(get_db)):
    # Buscamos la autonomía por su ID único
    aut = db.query(Autonomia).filter(Autonomia.id == autonomia_id).first()
    if not aut:
        raise HTTPException(status_code=404, detail="Autonomía no encontrada.")
    
    # Actualizamos el estado booleano ('activa' pasa a True o False según la petición)
    aut.activa = data.activa
    db.commit()      # Guardamos los cambios en la base de datos
    return {"mensaje": f"Autonomía {'habilitada' if data.activa else 'deshabilitada'} con éxito."}

# Endpoint DELETE: Eliminar por completo una autonomía de la base de datos
@router.delete("/{autonomia_id}")
def eliminar_autonomia(autonomia_id: str, db: Session = Depends(get_db)):
    # Buscamos el registro a eliminar
    aut = db.query(Autonomia).filter(Autonomia.id == autonomia_id).first()
    if not aut:
        raise HTTPException(status_code=404, detail="Autonomía no encontrada.")
    
    db.delete(aut)   # Borramos el registro
    db.commit()      # Consolidamos el cambio
    return {"mensaje": "Autonomía eliminada."}