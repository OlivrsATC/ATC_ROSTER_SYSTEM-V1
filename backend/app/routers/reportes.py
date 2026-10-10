from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from datetime import date
import os

from app.database import get_db
from app.services.pdf_generator import generar_pdf_orden_servicio

router = APIRouter(prefix="/api/reportes", tags=["Reportes PDF"])

@router.get("/orden-servicio", response_class=FileResponse)
def descargar_orden_servicio_pdf(
    fecha_inicio: date = Query(..., description="Fecha inicial en formato YYYY-MM-DD"),
    fecha_fin: date = Query(..., description="Fecha final en formato YYYY-MM-DD"),
    db: Session = Depends(get_db)
):
    """
    Genera y descarga el reporte oficial en PDF de la Orden de Servicio de la FAC
    para el rango de fechas especificado.
    """
    output_dir = "reports"
    os.makedirs(output_dir, exist_ok=True)
    filename = f"Orden_Servicio_{fecha_inicio}_al_{fecha_fin}.pdf"
    filepath = os.path.join(output_dir, filename)

    try:
        generar_pdf_orden_servicio(db, fecha_inicio, fecha_fin, filepath)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generando el archivo PDF: {str(e)}")

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail="No se pudo generar el reporte PDF.")

    return FileResponse(filepath, media_type="application/pdf", filename=filename)