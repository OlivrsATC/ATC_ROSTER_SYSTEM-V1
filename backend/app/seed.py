from app.database import SessionLocal, engine, Base
from app.models.turno import TurnoCat
# Importar los modelos para que SQLAlchemy reconozca el esquema
from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.novedad import NovedadPersonal
from app.models.asignacion import TurnoAsignado
import datetime

def seed_turnos():
    # 1. Crear las tablas en la base de datos si no existen
    Base.metadata.create_all(bind=engine)
    
    db = SessionLocal()
    
    # 2. Verificar si ya existen turnos
    if db.query(TurnoCat).first():
        print("El catálogo de turnos ya se encuentra inicializado.")
        db.close()
        return

    turnos_iniciales = [
        # Supervisión
        {"id": "SM", "codigo": "SM", "nombre": "Supervisor Mañana", "tipo_servicio": "Supervision", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 2},
        {"id": "ST", "codigo": "ST", "nombre": "Supervisor Tarde", "tipo_servicio": "Supervision", "hora_inicio": datetime.time(13, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 2},
        {"id": "SD", "codigo": "SD", "nombre": "Supervisor Día FDS", "tipo_servicio": "Supervision", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 3},
        
        # Torre
        {"id": "TM", "codigo": "TM", "nombre": "Torre Mañana", "tipo_servicio": "Torre", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 2},
        {"id": "TT", "codigo": "TT", "nombre": "Torre Tarde", "tipo_servicio": "Torre", "hora_inicio": datetime.time(13, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 2},
        {"id": "TD", "codigo": "TD", "nombre": "Torre Día FDS", "tipo_servicio": "Torre", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 3},
        {"id": "TN", "codigo": "TN", "nombre": "Torre Noche", "tipo_servicio": "Torre", "hora_inicio": datetime.time(19, 0), "hora_fin": datetime.time(7, 0), "peso_equity": 5},

        # Área
        {"id": "AM", "codigo": "AM", "nombre": "Área Mañana", "tipo_servicio": "Area", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 2},
        {"id": "AT", "codigo": "AT", "nombre": "Área Tarde", "tipo_servicio": "Area", "hora_inicio": datetime.time(13, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 2},
        {"id": "AD", "codigo": "AD", "nombre": "Área Día FDS", "tipo_servicio": "Area", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 3},

        # Superficie
        {"id": "GM", "codigo": "GM", "nombre": "Superficie Mañana", "tipo_servicio": "Superficie", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 2},
        {"id": "GT", "codigo": "GT", "nombre": "Superficie Tarde", "tipo_servicio": "Superficie", "hora_inicio": datetime.time(13, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 2},
        {"id": "GD", "codigo": "GD", "nombre": "Superficie Día FDS", "tipo_servicio": "Superficie", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 3},

        # OIA
        {"id": "OM", "codigo": "OM", "nombre": "OIA Mañana", "tipo_servicio": "OIA", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 2},
        {"id": "OT", "codigo": "OT", "nombre": "OIA Tarde", "tipo_servicio": "OIA", "hora_inicio": datetime.time(13, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 2},
        {"id": "OD", "codigo": "OD", "nombre": "OIA Día FDS", "tipo_servicio": "OIA", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(19, 0), "peso_equity": 3},
        {"id": "ON", "codigo": "ON", "nombre": "OIA Noche", "tipo_servicio": "OIA", "hora_inicio": datetime.time(19, 0), "hora_fin": datetime.time(7, 0), "peso_equity": 5},

        # Administrativos y Disponibilidad
        {"id": "HU", "codigo": "HU", "nombre": "Horario Oficina", "tipo_servicio": "Administrativo", "hora_inicio": datetime.time(7, 30), "hora_fin": datetime.time(17, 0), "peso_equity": 1},
        {"id": "DISP", "codigo": "DISP", "nombre": "Disponible 24h", "tipo_servicio": "Disponibilidad", "hora_inicio": None, "hora_fin": None, "peso_equity": 1},
    ]

    for t_data in turnos_iniciales:
        turno = TurnoCat(**t_data)
        db.add(turno)
    
    db.commit()
    db.close()
    print("Catálogo de turnos inicializado exitosamente en la base de datos.")

if __name__ == "__main__":
    seed_turnos()