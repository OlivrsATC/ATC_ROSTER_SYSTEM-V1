from sqlalchemy import Column, String, Date, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class TurnoAsignado(Base):
    __tablename__ = "turnos_asignados"

    id = Column(String, primary_key=True, index=True)
    controlador_id = Column(String, ForeignKey("controladores.id"), nullable=False)
    turno_codigo = Column(String, nullable=False)
    fecha = Column(Date, nullable=False)
    asignado_automaticamente = Column(Boolean, default=False)
    modificado_manualmente = Column(Boolean, default=False)

    # Relación inversa hacia el controlador
    controlador = relationship("Controlador", back_populates="turnos_asignados")