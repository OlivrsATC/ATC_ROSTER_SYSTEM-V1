from pydantic import BaseModel, EmailStr
from datetime import date
from typing import List, Optional

class AutonomiaBase(BaseModel):
    tipo: str # TWR, ACC, GND, OIA, SUP
    posicion: str
    fecha_obtencion: date
    fecha_vencimiento: date

class AutonomiaCreate(AutonomiaBase):
    pass

class AutonomiaResponse(AutonomiaBase):
    id: str
    controlador_id: str

    class Config:
        from_attributes = True

class ControladorBase(BaseModel):
    identificacion: str
    nombres: str
    apellidos: str
    email: str
    rol: Optional[str] = "CONTROLADOR"
    activo: Optional[bool] = True
    aptitud_psicofisica_vencimiento: date

class ControladorCreate(ControladorBase):
    autonomias: Optional[List[AutonomiaCreate]] = []

class ControladorResponse(ControladorBase):
    id: str
    autonomias: List[AutonomiaResponse] = []

    class Config:
        from_attributes = True