import calendar
from datetime import date, timedelta
from sqlalchemy.orm import Session
import uuid

from app.models.controlador import Controlador
from app.models.asignacion import TurnoAsignado
from app.services.motor_reglas import MotorReglasATC

def generar_cuadrante_mes(db: Session, anio: int, mes: int):
    motor = MotorReglasATC(db)
    num_dias = calendar.monthrange(anio, mes)[1]
    controladores = db.query(Controlador).filter(Controlador.activo == True).all()
    
    if not controladores:
        return {"error": "No hay controladores activos."}

    turnos_operativos = ["VEL", "SM", "ST", "TN", "AM", "AT", "CP"]

    for dia in range(1, num_dias + 1):
        fecha_actual = date(anio, mes, dia)
        
        for idx, ctrl in enumerate(controladores):
            existente = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == fecha_actual
            ).first()
            
            if existente:
                continue

            if not motor.validar_aptitud_y_novedades(ctrl.id, fecha_actual):
                codigo_asignar = "VAC"
            else:
                candidato = turnos_operativos[(idx + dia) % len(turnos_operativos)]
                if not motor.verificar_regla_disponible_obligatorio(ctrl.id, fecha_actual, candidato):
                    codigo_asignar = "DISP"
                elif candidato.endswith('N') and not motor.validar_limite_noches(ctrl.id, fecha_actual, candidato):
                    codigo_asignar = "DISP"
                else:
                    codigo_asignar = candidato

            db.add(TurnoAsignado(
                id=str(uuid.uuid4()),
                controlador_id=ctrl.id,
                turno_codigo=codigo_asignar,
                fecha=fecha_actual,
                asignado_automaticamente=True,
                modificado_manualmente=False
            ))

    db.commit()
    return {"mensaje": f"Cuadrante generado para {anio}-{mes:02d}."}