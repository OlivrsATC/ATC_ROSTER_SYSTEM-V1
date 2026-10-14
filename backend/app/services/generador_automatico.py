import calendar
from datetime import date, timedelta
from sqlalchemy.orm import Session
import uuid

from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.asignacion import TurnoAsignado
from app.services.motor_reglas import MotorReglasATC

def generar_cuadrante_mes(db: Session, anio: int, mes: int):
    motor = MotorReglasATC(db)
    num_dias = calendar.monthrange(anio, mes)[1]
    
    # Regla 6: Excluir al Jefe de Tránsito de la asignación automática
    controladores = db.query(Controlador).filter(
        Controlador.activo == True,
        ~Controlador.rol.ilike("%JEFE_TRANSITO%"),
        ~Controlador.rol.ilike("%JEFE DE TRANSITO%")
    ).all()
    
    if not controladores:
        return {"error": "No hay controladores activos elegibles para generación automática."}

    # Mapeo de autonomías institucionales a códigos de turnos permitidos
    mapa_turnos_autonomia = {
        "SUP": ["SM", "ST", "SD"],
        "TWR": ["TM", "TT", "TN", "TD"],
        "ACC": ["AM", "AT", "AD"],
        "GND": ["GM", "GT", "GD"],
        "OIA": ["OM", "OT", "OD", "ON"],
        "INS": ["IM", "IT"]
    }

    # Posición requerida por cada turno operativo para validar autonomías
    turno_a_posicion = {
        "SM": "SUPERVISOR", "ST": "SUPERVISOR",
        "TM": "TORRE", "TT": "TORRE", "TN": "TORRE",
        "AM": "AREA", "AT": "AREA",
        "GM": "SUPERFICIE", "GT": "SUPERFICIE",
        "OM": "OIA", "OT": "OIA", "ON": "OIA"
    }

    # Turnos operacionales diarios obligatorios requeridos (Regla 2)
    turnos_diarios_requeridos = [
        "SM", "TM", "AM", "GM", "OM", 
        "ST", "TT", "AT", "GT", "OT", 
        "TN", "ON", "DISP"
    ]

    for dia in range(1, num_dias + 1):
        fecha_actual = date(anio, mes, dia)
        asignados_hoy = set() # IDs de controladores ya ocupados en este día
        
        # 1. Asignar novedades (VAC) o aptitud psicofísica vencida
        for ctrl in controladores:
            existente = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == fecha_actual
            ).first()
            
            if existente:
                asignados_hoy.add(ctrl.id)
                continue

            if not motor.validar_aptitud_y_novedades(ctrl.id, fecha_actual):
                db.add(TurnoAsignado(
                    id=str(uuid.uuid4()),
                    controlador_id=ctrl.id,
                    turno_codigo="VAC",
                    fecha=fecha_actual,
                    asignado_automaticamente=True,
                    modificado_manualmente=False
                ))
                asignados_hoy.add(ctrl.id)

        # 2. Asignar Compensatorios (CP) obligatorios si el día anterior hicieron turno nocturno (Regla 1)
        ayer = fecha_actual - timedelta(days=1)
        for ctrl in controladores:
            if ctrl.id in asignados_hoy:
                continue

            asig_ayer = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == ayer
            ).first()

            if asig_ayer and asig_ayer.turno_codigo in ["TN", "ON"]:
                db.add(TurnoAsignado(
                    id=str(uuid.uuid4()),
                    controlador_id=ctrl.id,
                    turno_codigo="CP",
                    fecha=fecha_actual,
                    asignado_automaticamente=True,
                    modificado_manualmente=False
                ))
                asignados_hoy.add(ctrl.id)

        # Cargar autonomías vigentes de todos los controladores para el día de hoy
        auton_cache = {}
        for ctrl in controladores:
            auton_db = db.query(Autonomia).filter(
                Autonomia.controlador_id == ctrl.id,
                Autonomia.fecha_vencimiento >= fecha_actual
            ).all()
            auton_cache[ctrl.id] = {a.tipo.upper() for a in auton_db}

        # 3. Cubrir los turnos operativos diarios requeridos sin repetir personal (Regla 2)
        for t_req in turnos_diarios_requeridos:
            candidato_encontrado = None
            pos_req = turno_a_posicion.get(t_req)

            # Filtrar personal libre en el día
            libres = [c for c in controladores if c.id not in asignados_hoy]

            for ctrl in libres:
                # Regla 1: Validar límite de turnos nocturnos consecutivos (máx 2 L-J, máx 3 Viernes-Domingo)
                if t_req in ["TN", "ON"] and not motor.validar_nocturnos_consecutivos(ctrl.id, fecha_actual, t_req):
                    continue

                # Validar autonomía institucional correspondiente al puesto
                if pos_req:
                    tipo_nec = next((k for k, v in mapa_turnos_autonomia.items() if t_req in v), None)
                    if tipo_nec and tipo_nec not in auton_cache.get(ctrl.id, set()):
                        continue

                candidato_encontrado = ctrl
                break

            if candidato_encontrado:
                db.add(TurnoAsignado(
                    id=str(uuid.uuid4()),
                    controlador_id=candidato_encontrado.id,
                    turno_codigo=t_req,
                    fecha=fecha_actual,
                    asignado_automaticamente=True,
                    modificado_manualmente=False
                ))
                asignados_hoy.add(candidato_encontrado.id)

        # 4. A los controladores restantes sin asignar en el día, asignarles Horario de Oficina / Administrativo (HU)
        for ctrl in controladores:
            if ctrl.id not in asignados_hoy:
                db.add(TurnoAsignado(
                    id=str(uuid.uuid4()),
                    controlador_id=ctrl.id,
                    turno_codigo="HU",
                    fecha=fecha_actual,
                    asignado_automaticamente=True,
                    modificado_manualmente=False
                ))
                asignados_hoy.add(ctrl.id)

    db.commit()
    return {"mensaje": f"Cuadrante generado con éxito para {anio}-{mes:02d} cumpliendo la nueva directiva de reglas operativas."}