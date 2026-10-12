from sqlalchemy import Column, String, Date
from app.database import Base

class NovedadProgramada(Base):
    __tablename__ = "novedades_programadas"

    id = Column(String, primary_key=True, index=True)
    controlador_id = Column(String, nullable=False, index=True) # Solo guardamos el ID del controlador como texto
    tipo = Column(String, nullable=False) # Ej: "VAC", "REEN", "ENTTO"
    asunto = Column(String, nullable=False) # Ej: "Vacaciones anuales reglamentarias", "Curso de repaso"
    fecha_inicio = Column(Date, nullable=False)
    fecha_fin = Column(Date, nullable=False)