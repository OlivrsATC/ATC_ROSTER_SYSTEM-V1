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
    
    # Regla 6: Excluir al Jefe de Tránsito de la asignación automática
    controladores = db.query(Controlador).filter(
        Controlador.activo == True,
        ~Controlador.rol.ilike("%JEFE_TRANSITO%"),
        ~Controlador.rol.ilike("%JEFE DE TRANSITO%")
    ).all()
    
    if not controladores:
        return {"error": "No hay controladores activos elegibles para generación automática."}

    # Turnos operacionales diarios obligatorios requeridos (Regla 2)
    turnos_diarios_requeridos = [
        "SM", "TM", "AM", "GM", "OM", 
        "ST", "TT", "AT", "GT", "OT", 
        "TN", "ON", "DISP"
    ]

    # Conjunto de turnos pertenecientes a la Oficina de Información Aeronáutica (OIA)
    turnos_oia = {"OM", "OT", "ON", "OD"}

    for dia in range(1, num_dias + 1):
        fecha_actual = date(anio, mes, dia)
        asignados_hoy = set()      # IDs de controladores asignados hoy
        sin_aptitud_hoy = set()    # IDs de controladores sin aptitud psicofísica vigente hoy

        # 1. Identificar registros existentes y controladores sin aptitud psicofísica
        for ctrl in controladores:
            existente = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == fecha_actual
            ).first()
            
            if existente:
                asignados_hoy.add(ctrl.id)
                continue

            # Verificar si la aptitud psicofísica está vencida o si posee novedades
            if not motor.validar_aptitud_y_novedades(ctrl.id, fecha_actual):
                sin_aptitud_hoy.add(ctrl.id)

        # 2. Asignar Compensatorios (CP) obligatorios si el día anterior hicieron turno nocturno
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

        # 3. Cubrir los turnos operativos diarios requeridos
        for t_req in turnos_diarios_requeridos:
            candidato_encontrado = None

            # Filtrar personal libre en el día
            libres = [c for c in controladores if c.id not in asignados_hoy]

            for ctrl in libres:
                # 👈 REGLA APTITUD PSICOFÍSICA: Si no tiene aptitud, SOLO puede hacer turnos de OIA
                if ctrl.id in sin_aptitud_hoy and t_req not in turnos_oia and t_req != "DISP":
                    continue

                # Validar límite de turnos nocturnos consecutivos
                if t_req in ["TN", "ON"] and not motor.validar_nocturnos_consecutivos(ctrl.id, fecha_actual, t_req):
                    continue

                # Validar autonomía activa correspondiente
                if not motor.validar_autonomia(ctrl.id, t_req, fecha_actual):
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

        # 4. Asignar Horario de Oficina / Administrativo (HU) al personal restante
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
    return {"mensaje": f"Cuadrante generado con éxito para {anio}-{mes:02d} aplicando restricciones de aptitud psicofísica."}