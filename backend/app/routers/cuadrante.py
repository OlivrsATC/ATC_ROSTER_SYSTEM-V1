from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
import calendar
from datetime import date

from app.database import get_db
from app.models.controlador import Controlador
from app.models.asignacion import TurnoAsignado
from app.services.generador_automatico import generar_cuadrante_mes

router = APIRouter(prefix="/api/cuadrante", tags=["Cuadrante Mensual"])

@router.get("/matriz")
def obtener_matriz_mensual(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    num_dias = calendar.monthrange(anio, mes)[1]
    controladores = db.query(Controlador).all()
    matriz = []
    
    for idx, ctrl in enumerate(controladores, start=1):
        fila = {
            "id": ctrl.id,
            "numero_orden": idx,
            "nombre_completo": f"{ctrl.rol[:2]}. {ctrl.apellidos} {ctrl.nombres} ({ctrl.identificacion[-2:]})".upper(),
            "dias": {}
        }
        for dia in range(1, num_dias + 1):
            f_dia = date(anio, mes, dia)
            asig = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == f_dia
            ).first()
            fila["dias"][dia] = asig.turno_codigo if asig else ""
        matriz.append(fila)

    return {"anio": anio, "mes": mes, "total_dias": num_dias, "filas": matriz}

@router.post("/generar")
def generar(anio: int = Query(2026), mes: int = Query(9), db: Session = Depends(get_db)):
    return generar_cuadrante_mes(db, anio, mes)