from sqlalchemy import Column, String, Date, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.database import Base

class Autonomia(Base):
    __tablename__ = "autonomias"

    id = Column(String, primary_key=True, index=True)
    controlador_id = Column(String, ForeignKey("controladores.id"), nullable=False)
    tipo = Column(String, nullable=False) # TWR, ACC, GND, OIA, SUP
    posicion = Column(String, nullable=False)
    fecha_obtencion = Column(Date, nullable=False)
    fecha_vencimiento = Column(Date, nullable=False)
    activa = Column(Boolean, default=True, nullable=False) # Interruptor para habilitar/deshabilitar autonomias sin eliminarlas de la base de datos

    controlador = relationship("Controlador", back_populates="autonomias")