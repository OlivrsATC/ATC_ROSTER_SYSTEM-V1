from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import controlador, cuadrante, turno, autonomia, reporte

# Crear las tablas en la base de datos si no existen
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ATC Roster System - CACOM-1",
    description="Sistema de programación y gestión de turnos para controladores aéreos basado en la Directiva FAC No. 061.",
    version="1.0.0"
)

# Configuración de CORS para permitir peticiones desde el Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, restringir a dominios específicos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Registrar los Routers de la API
app.include_router(controlador.router)
app.include_router(cuadrante.router)
app.include_router(turno.router)
app.include_router(autonomia.router)
app.include_router(reporte.router)

@app.get("/")
def read_root():
    return {
        "sistema": "ATC Roster System - CACOM-1",
        "estado": "Operativo",
        "documentacion": "/docs"
    }