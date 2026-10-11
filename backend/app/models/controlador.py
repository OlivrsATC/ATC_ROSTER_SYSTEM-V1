from sqlalchemy import Column, String, Boolean, Date
from sqlalchemy.orm import relationship
from app.database import Base

class Controlador(Base):
    __tablename__ = "controladores"

    id = Column(String, primary_key=True, index=True)
    identificacion = Column(String, unique=True, index=True, nullable=False)
    grado = Column(String, nullable=False, default="T3")  # AT, T4, T3, T2, T1, TS, TJ
    numero_curso = Column(String, nullable=True)         # Número de curso (Ej. 088)
    nombres = Column(String, nullable=False)
    apellidos = Column(String, nullable=False)
    email = Column(String, nullable=False)
    rol = Column(String, default="CONTROLADOR")
    aptitud_psicofisica_vencimiento = Column(Date, nullable=False)
    activo = Column(Boolean, default=True)

    # Relaciones con otras tablas
    autonomias = relationship("Autonomia", back_populates="controlador", cascade="all, delete")
    turnos_asignados = relationship("TurnoAsignado", back_populates="controlador", cascade="all, delete")