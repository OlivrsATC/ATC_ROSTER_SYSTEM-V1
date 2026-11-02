import calendar
from datetime import date, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import extract
import uuid

from app.models.controlador import Controlador
from app.models.asignacion import TurnoAsignado
from app.models.novedad import NovedadProgramada
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
    
    # 1. Limpiar turnos asignados automáticamente del mes
    db.query(TurnoAsignado).filter(
        extract('year', TurnoAsignado.fecha) == anio,
        extract('month', TurnoAsignado.fecha) == mes,
        TurnoAsignado.asignado_automaticamente == True
    ).delete(synchronize_session=False)
    db.commit()

    # Excluir al Jefe de Tránsito de la asignación automática
    controladores = db.query(Controlador).filter(
        Controlador.activo == True,
        ~Controlador.rol.ilike("%JEFE_TRANSITO%"),
        ~Controlador.rol.ilike("%JEFE DE TRANSITO%")
    ).all()
    
    if not controladores:
        return {"error": "No hay controladores activos elegibles para generación automática."}

    # Estructura de turnos en memoria: {ctrl_id: {fecha: codigo}}
    turnos_mes = {ctrl.id: {} for ctrl in controladores}

    # Contador de servicios operativos trabajados para distribución 100% equitativa
    servicios_trabajados = {ctrl.id: 0 for ctrl in controladores}

    # Respetar turnos asignados manualmente previamente
    inicio_mes = date(anio, mes, 1)
    fin_mes = date(anio, mes, num_dias)
    turnos_existentes = db.query(TurnoAsignado).filter(
        TurnoAsignado.fecha >= inicio_mes,
        TurnoAsignado.fecha <= fin_mes
    ).all()

    for te in turnos_existentes:
        if te.controlador_id in turnos_mes:
            turnos_mes[te.controlador_id][te.fecha] = te.turno_codigo
            if te.turno_codigo not in ["", "HU", "CP", "VAC", "VACACIONES"]:
                servicios_trabajados[te.controlador_id] += 1

    # Distribución equitativa de descansos de fin de semana libres (Sábado y Domingo vacíos)
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

    # Definición de Servicios Obligatorios
    turnos_habiles = [
        "SM", "TM", "AM", "GM", "OM", "DISP",
        "ST", "TT", "AT", "GT", "OT",
        "TN", "ON"
    ]

    turnos_fin_de_semana_festivo = [
        "SD", "TD", "AD", "OD", "DISP",
        "TN", "ON"
    ]

    turnos_oia = {"OM", "OT", "ON", "OD"}

    for dia in range(1, num_dias + 1):
        fecha_actual = date(anio, mes, dia)
        es_fest_wk = es_fin_de_semana_o_festivo(fecha_actual)
        ayer = fecha_actual - timedelta(days=1)
        
        asignados_hoy = set()
        sin_aptitud_hoy = set()

        # A. Respetar asignaciones previas/manuales
        for ctrl in controladores:
            if fecha_actual in turnos_mes[ctrl.id]:
                asignados_hoy.add(ctrl.id)

        # B. Asignar casilla vacía ("") para descanso libre en fin de semana
        if es_fest_wk and fecha_actual.weekday() in [5, 6]:
            for ctrl in controladores:
                if ctrl.id in asignados_hoy:
                    continue
                if fecha_actual in descanso_fin_de_semana_map.get(ctrl.id, set()):
                    turnos_mes[ctrl.id][fecha_actual] = ""  # Casilla completamente vacía
                    asignados_hoy.add(ctrl.id)

        # C. Novedades (VAC) y vencimiento de aptitud psicofísica
        for ctrl in controladores:
            if ctrl.id in asignados_hoy:
                continue

            nov = db.query(NovedadProgramada).filter(
                NovedadProgramada.controlador_id == ctrl.id,
                NovedadProgramada.fecha_inicio <= fecha_actual,
                NovedadProgramada.fecha_fin >= fecha_actual
            ).first()

            if nov:
                turnos_mes[ctrl.id][fecha_actual] = nov.tipo
                asignados_hoy.add(ctrl.id)
                continue

            if not motor.validar_aptitud_y_novedades(ctrl.id, fecha_actual):
                sin_aptitud_hoy.add(ctrl.id)

        # D. COMPENSATORIO (CP) OBLIGATORIO POST-NOCTURNO (TN/ON)
        for ctrl in controladores:
            if ctrl.id in asignados_hoy:
                continue

            turno_ayer = turnos_mes[ctrl.id].get(ayer)
            if turno_ayer in ["TN", "ON"]:
                turnos_mes[ctrl.id][fecha_actual] = "CP"
                asignados_hoy.add(ctrl.id)

        turnos_diarios_requeridos = turnos_fin_de_semana_festivo if es_fest_wk else turnos_habiles

        # E. Cobertura de turnos asignando primero a quienes tengan MENOS servicios trabajados
        for t_req in turnos_diarios_requeridos:
            candidato_encontrado = None

            libres = [c for c in controladores if c.id not in asignados_hoy]
            
            # ORDENAR EQUITATIVAMENTE POR MENOR CANTIDAD DE SERVICIOS PRESTADOS HASTA LA FECHA
            libres_ordenados = sorted(libres, key=lambda c: servicios_trabajados[c.id])

            for ctrl in libres_ordenados:
                if ctrl.id in sin_aptitud_hoy and t_req not in turnos_oia and t_req != "DISP":
                    continue

                # Regla 3: Rotación de Disponibles (Si ayer hizo DISP, no repite DISP ni va a mañanas)
                turno_ayer = turnos_mes[ctrl.id].get(ayer)
                if turno_ayer == "DISP" and (t_req in ["DISP", "SM", "TM", "AM", "GM", "OM", "SD", "TD", "AD", "OD"]):
                    continue

                # Regla 1: Validar límites de nocturnos consecutivos
                if t_req in ["TN", "ON"]:
                    noches_previas = 0
                    curr = ayer
                    while True:
                        t_prev = turnos_mes[ctrl.id].get(curr)
                        if t_prev in ["TN", "ON"]:
                            noches_previas += 1
                            curr -= timedelta(days=1)
                        else:
                            break
                    
                    wd = fecha_actual.weekday()
                    if wd <= 3 and noches_previas >= 2: # Máximo 2 noches de Lunes a Jueves
                        continue
                    if wd >= 4 and noches_previas >= 3: # Máximo 3 noches de Viernes a Domingo
                        continue

                # Regla 5: Validar autonomía activa
                if not motor.validar_autonomia(ctrl.id, t_req, fecha_actual):
                    continue

                candidato_encontrado = ctrl
                break

            if candidato_encontrado:
                turnos_mes[candidato_encontrado.id][fecha_actual] = t_req
                asignados_hoy.add(candidato_encontrado.id)
                servicios_trabajados[candidato_encontrado.id] += 1

        # F. Asignación de días restantes: HU en días hábiles / Casilla vacía en fin de semana
        for ctrl in controladores:
            if ctrl.id not in asignados_hoy:
                if es_fest_wk:
                    turnos_mes[ctrl.id][fecha_actual] = "" # Vacío en fin de semana
                else:
                    turnos_mes[ctrl.id][fecha_actual] = "HU" # Horario Usual entre semana
                asignados_hoy.add(ctrl.id)

    # 4. Guardar resultados en la base de datos
    for ctrl_id, dias_dict in turnos_mes.items():
        for f_fecha, t_codigo in dias_dict.items():
            if t_codigo != "":
                db.add(TurnoAsignado(
                    id=str(uuid.uuid4()),
                    controlador_id=ctrl_id,
                    turno_codigo=t_codigo,
                    fecha=f_fecha,
                    asignado_automaticamente=True,
                    modificado_manualmente=False
                ))

    db.commit()
    return {"mensaje": f"Cuadrante generado con éxito para {anio}-{mes:02d} con equidad de carga y celdas libres en fin de semana."}