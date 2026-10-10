from sqlalchemy import Column, String, Boolean, Date
from sqlalchemy.orm import relationship
from app.database import Base

class Controlador(Base):
    __tablename__ = "controladores"

    id = Column(String, primary_key=True, index=True)
    identificacion = Column(String, unique=True, index=True, nullable=False)
    nombres = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False)
    rol = Column(String, default="CONTROLADOR")
    activo = Column(Boolean, default=True)
    aptitud_psicofisica_vencimiento = Column(Date, nullable=False)

    autonomias = relationship("Autonomia", back_populates="controlador", cascade="all, delete-orphan")
    novedades = relationship("NovedadPersonal", back_populates="controlador", cascade="all, delete-orphan")
    turnos_asignados = relationship("TurnoAsignado", back_populates="controlador", cascade="all, delete-orphan")