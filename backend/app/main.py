from fastapi import FastAPI
from app.database import engine, Base
# Importar los modelos para que SQLAlchemy los reconozca al crear las tablas
from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.turno import TurnoCat
from app.models.novedad import NovedadPersonal
from app.models.asignacion import TurnoAsignado
from app.routers import controlador, asignacion, reportes

# Crear las tablas en la base de datos SQLite
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Sistema de Programación ATC - CACOM-1",
    description="API Backend para la gestión de cuadrantes y motor de reglas operativas (FAC)",
    version="1.0.0"
)

# Registrar Endpoints de Controladores
app.include_router(controlador.router)
app.include_router(asignacion.router)
app.include_router(reportes.router)

@app.get("/")
def read_root():
    return {
        "estado": "activo",
        "mensaje": "Bienvenido al Sistema de Programación de Servicios ATC - Escuadrón 115"
    }