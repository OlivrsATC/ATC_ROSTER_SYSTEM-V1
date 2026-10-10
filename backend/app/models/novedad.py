from sqlalchemy import Column, String, Date, ForeignKey
from sqlalchemy.orm import relationship
from app.database import Base

class NovedadPersonal(Base):
    __tablename__ = "novedades_personal"

    id = Column(String, primary_key=True, index=True)
    controlador_id = Column(String, ForeignKey("controladores.id"), nullable=False)
    tipo_novedad = Column(String, nullable=False)
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)
    observacion = Column(String, nullable=True)

    controlador = relationship("Controlador", back_populates="novedades")