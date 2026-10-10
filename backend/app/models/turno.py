from sqlalchemy import Column, String, Integer, Time
from app.database import Base

class TurnoCat(Base):
    __tablename__ = "catalogo_turnos"

    id = Column(String, primary_key=True, index=True)
    codigo = Column(String, unique=True, index=True, nullable=False) # SM, TT, TN, DISP, HU, etc.
    nombre = Column(String, nullable=False)
    tipo_servicio = Column(String, nullable=False)
    hora_inicio = Column(Time, nullable=True)
    hora_fin = Column(Time, nullable=True)
    peso_equity = Column(Integer, default=1)