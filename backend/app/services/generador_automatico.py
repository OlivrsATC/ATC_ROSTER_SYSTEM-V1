import calendar
from datetime import date, timedelta
from sqlalchemy.orm import Session
import uuid

from app.models.controlador import Controlador
from app.models.asignacion import TurnoAsignado
from app.services.motor_reglas import MotorReglasATC

def calcular_domingo_pascua(anio: int) -> date:
    a = anio % 19
    b = anio // 100
    c = anio % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31
    dia = ((h + l - 7 * m + 114) % 31) + 1
    return date(anio, mes, dia)

def siguiente_lunes(d: date) -> date:
    dias_hasta_lunes = (0 - d.weekday()) % 7
    return d + timedelta(days=dias_hasta_lunes)

def es_festivo_colombia(f: date) -> bool:
    anio = f.year
    fijos = [
        date(anio, 1, 1),
        date(anio, 5, 1),
        date(anio, 7, 20),
        date(anio, 8, 7),
        date(anio, 12, 8),
        date(anio, 12, 25)
    ]
    if f in fijos:
        return True
    
    trasladables = [
        date(anio, 1, 6),
        date(anio, 3, 19),
        date(anio, 6, 29),
        date(anio, 8, 15),
        date(anio, 10, 12),
        date(anio, 11, 1),
        date(anio, 11, 11),
    ]
    for d in trasladables:
        if siguiente_lunes(d) == f:
            return True
            
    pascua = calcular_domingo_pascua(anio)
    jueves_santo = pascua - timedelta(days=3)
    viernes_santo = pascua - timedelta(days=2)
    ascension = siguiente_lunes(pascua + timedelta(days=40))
    corpus = siguiente_lunes(pascua + timedelta(days=60))
    sagrado_corazon = siguiente_lunes(pascua + timedelta(days=68))
    
    festivos_pascua = [jueves_santo, viernes_santo, ascension, corpus, sagrado_corazon]
    if f in festivos_pascua:
        return True
        
    return False

def es_fin_de_semana_o_festivo(f: date) -> bool:
    return f.weekday() >= 5 or es_festivo_colombia(f)

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

    # Distribución equitativa de descanso de fin de semana (mínimo 1 fin de semana libre por controlador)
    fines_de_semana = []
    dias_s = None
    for d in range(1, num_dias + 1):
        f_dt = date(anio, mes, d)
        if f_dt.weekday() == 5:
            dias_s = f_dt
        elif f_dt.weekday() == 6 and dias_s and dias_s.month == f_dt.month:
            fines_de_semana.append((dias_s, f_dt))
            dias_s = None

    descanso_fin_de_semana_map = {}
    if fines_de_semana:
        for idx, ctrl in enumerate(controladores):
            wk_idx = idx % len(fines_de_semana)
            sat, sun = fines_de_semana[wk_idx]
            descanso_fin_de_semana_map[ctrl.id] = {sat, sun}

    # Turnos operacionales para días hábiles (Lunes a Viernes no festivos)
    turnos_habiles = [
        "SM", "TM", "AM", "GM", "OM", 
        "ST", "TT", "AT", "GT", "OT", 
        "TN", "ON", "DISP"
    ]

    # Turnos operacionales requeridos para fines de semana y festivos (incluyendo DISP)
    turnos_fin_de_semana_festivo = [
        "SD", "TD", "AD", "OD", "TN", "ON", "DISP"
    ]

    turnos_oia = {"OM", "OT", "ON", "OD"}

    for dia in range(1, num_dias + 1):
        fecha_actual = date(anio, mes, dia)
        es_fest_wk = es_fin_de_semana_o_festivo(fecha_actual)
        
        asignados_hoy = set()
        sin_aptitud_hoy = set()

        # REGLA NUEVA: Si es fin de semana y corresponde al descanso equitativo del controlador, queda libre (casilla vacía)
        if es_fest_wk:
            for ctrl in controladores:
                if fecha_actual in descanso_fin_de_semana_map.get(ctrl.id, set()):
                    asignados_hoy.add(ctrl.id)

        # 1. Asignar novedades (VAC) o aptitud psicofísica vencida
        for ctrl in controladores:
            if ctrl.id in asignados_hoy:
                continue

            existente = db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == ctrl.id,
                TurnoAsignado.fecha == fecha_actual
            ).first()
            
            if existente:
                asignados_hoy.add(ctrl.id)
                continue

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

        turnos_diarios_requeridos = turnos_fin_de_semana_festivo if es_fest_wk else turnos_habiles

        # 3. Cubrir los turnos operativos diarios requeridos sin repetir personal
        for t_req in turnos_diarios_requeridos:
            candidato_encontrado = None

            libres = [c for c in controladores if c.id not in asignados_hoy]

            for ctrl in libres:
                # Si no tiene aptitud, solo OIA o DISP
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
    return {"mensaje": f"Cuadrante generado con éxito para {anio}-{mes:02d} aplicando turnos DISP y descansos de fin de semana libres."}