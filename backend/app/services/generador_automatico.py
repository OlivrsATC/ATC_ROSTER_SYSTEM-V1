import calendar
from datetime import date
from sqlalchemy.orm import Session
import uuid

from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.asignacion import TurnoAsignado
from app.services.motor_reglas import MotorReglasATC

def generar_cuadrante_mes(db: Session, anio: int, mes: int):
    motor = MotorReglasATC(db)
    num_dias = calendar.monthrange(anio, mes)[1]
    controladores = db.query(Controlador).filter(Controlador.activo == True).all()
    
    if not controladores:
        return {"error": "No hay controladores activos."}

    # Mapeo de autonomías institucionales a códigos de turnos permitidos
    mapa_turnos_autonomia = {
        "SUP": ["SM", "ST","SD" ],
        "TWR": ["TM", "TT", "TN", "TD"],
        "ACC": ["AM", "AT", "AD"],
        "GND": ["GM", "GT", "GD"],
        "OIA": ["OM", "OT", "OD", "ON"],
        "INS": ["IM", "IT"]
    }

    for dia in range(1, num_dias + 1):
        fecha_actual = date(anio, mes, dia)
        
        for ctrl in controladores:
            existente = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == fecha_actual
            ).first()
            
            if existente:
                continue

            # Verificar aptitud psicofísica y novedades (Vacaciones)
            if not motor.validar_aptitud_y_novedades(ctrl.id, fecha_actual):
                codigo_asignar = "VAC"
            else:
                # Obtener autonomías vigentes del controlador
                autonomias_ctrl = db.query(Autonomia).filter(Autonomia.controlador_id == ctrl.id).all()
                tipos_aut = [a.tipo.upper() for a in autonomias_ctrl]

                # Recopilar turnos elegibles según sus autonomías
                turnos_elegibles = []
                for t_tipo in tipos_aut:
                    if t_tipo in mapa_turnos_autonomia:
                        turnos_elegibles.extend(mapa_turnos_autonomia[t_tipo])
                
                # Si no tiene autonomías operativas, asignar Horario Oficina (HU) por defecto
                if not turnos_elegibles:
                    codigo_asignar = "HU"
                else:
                    # Seleccionar rotativamente de sus turnos permitidos
                    candidato = turnos_elegibles[(dia + hash(ctrl.id)) % len(turnos_elegibles)]

                    # Aplicar motor de reglas (DISP obligatorio post-tarde/noche y límite de noches)
                    if not motor.verificar_regla_disponible_obligatorio(ctrl.id, fecha_actual, candidato):
                        codigo_asignar = "DISP"
                    elif candidato in ["TN", "ON"] and not motor.validar_limite_noches(ctrl.id, fecha_actual, candidato):
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
    return {"mensaje": f"Cuadrante generado con éxito para {anio}-{mes:02d} basado en autonomías."}