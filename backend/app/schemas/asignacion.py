from pydantic import BaseModel
from datetime import date

class TurnoAsignadoCreate(BaseModel):
    controlador_id: str
    turno_codigo: str
    fecha: date

class TurnoAsignadoResponse(BaseModel):
    id: str
    controlador_id: str
    turno_codigo: str
    fecha: date
    asignado_automaticamente: bool
    modificado_manualmente: bool

    class Config:
        from_attributes = True