from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.novedad import NovedadProgramada

class MotorReglasATC:
    def __init__(self, db: Session):
        """
        Inicializa el motor de reglas con la sesión activa de SQLAlchemy de la base de datos.
        """
        self.db = db

    def es_jefe_transito(self, controlador_id: str) -> bool:
        """
        Regla 6: La persona con ROL Jefe de Tránsito no debe ser asignada 
        para ningún servicio de manera automática.
        """
        ctrl = self.db.query(Controlador).filter(Controlador.id == controlador_id).first()
        if not ctrl:
            return False
        rol = str(ctrl.rol or "").upper()
        return "JEFE" in rol and "TRANSITO" in rol

    def validar_nocturnos_consecutivos(self, controlador_id: str, fecha: date, codigo_turno: str) -> bool:
        """
        Regla 1 (Gestión de fatiga operativa):
        - Lunes a Jueves: Máximo 2 nocturnos (TN u ON) seguidos; al 3er día se debe descansar.
        - Fin de semana: El servicio nocturno empieza desde el viernes hasta el domingo, máximo 3 noches.
          El día siguiente (Lunes) al último servicio nocturno debe compensar (CP) obligatoriamente.
        """
        if codigo_turno == "CP":
            return True

        ayer = fecha - timedelta(days=1)
        wd = fecha.weekday() # 0=Lunes, ..., 4=Viernes, 5=Sábado, 6=Domingo

        # Si hoy es Lunes (wd == 0) y el controlador hizo turno nocturno el fin de semana,
        # el día de hoy OBLIGATORIAMENTE debe ser CP. Cualquier otro turno se rechaza.
        if wd == 0:
            asig_v = self.db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == controlador_id,
                TurnoAsignado.fecha == (fecha - timedelta(days=3)) # Viernes
            ).first()
            asig_s = self.db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == controlador_id,
                TurnoAsignado.fecha == (fecha - timedelta(days=2)) # Sábado
            ).first()
            asig_d = self.db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == controlador_id,
                TurnoAsignado.fecha == ayer # Domingo
            ).first()

            ven_de_noche_fs = (
                (asig_v and asig_v.turno_codigo in ["TN", "ON"]) or
                (asig_s and asig_s.turno_codigo in ["TN", "ON"]) or
                (asig_d and asig_d.turno_codigo in ["TN", "ON"])
            )
            if ven_de_noche_fs and codigo_turno != "CP":
                return False

        if codigo_turno not in ["TN", "ON"]:
            return True

        # Contar cuántas noches consecutivas trae hacia atrás
        noches_consecutivas = 0
        curr = ayer
        while True:
            asig_prev = self.db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == controlador_id,
                TurnoAsignado.fecha == curr
            ).first()
            if asig_prev and asig_prev.turno_codigo in ["TN", "ON"]:
                noches_consecutivas += 1
                curr -= timedelta(days=1)
            else:
                break

        # Lunes a Jueves (0 a 3): Máximo 2 nocturnos seguidos
        if wd in [0, 1, 2, 3]:
            if noches_consecutivas >= 2:
                return False

        # Fin de semana (Viernes a Domingo: 4, 5, 6): Máximo 3 noches consecutivas
        if wd in [4, 5, 6]:
            if noches_consecutivas >= 3:
                return False

        return True
        
    def validar_rotacion_disponible(self, controlador_id: str, fecha: date, codigo_turno: str) -> bool:
        """
        Regla 3: Si la persona presta de Disponible (DISP), 
        al otro día debe estar en la tarde, noche u HU (no en la mañana ni repetir DISP).
        """
        ayer = fecha - timedelta(days=1)
        asig_ayer = self.db.query(TurnoAsignado).filter(
            TurnoAsignado.controlador_id == controlador_id,
            TurnoAsignado.fecha == ayer
        ).first()

        if asig_ayer and asig_ayer.turno_codigo == "DISP":
            # Turnos prohibidos al día siguiente de estar de DISP: Mañanas (SM, TM, AM, GM, OM) o repetir DISP
            turnos_mañana = ["SM", "TM", "AM", "GM", "OM"]
            if codigo_turno in turnos_mañana or codigo_turno == "DISP":
                return False

        return True

    def validar_descanso_fin_de_semana(self, controlador_id: str, anio: int, mes: int) -> bool:
        """
        Regla 4: Los controladores deben descansar al menos 01 fin de semana (Sábado y Domingo) al mes.
        Esta función evalúa si el controlador ya cuenta con al menos un fin de semana libre en el mes indicado.
        """
        # Generar todos los fines de semana (Sábado y Domingo) del mes
        primer_dia = date(anio, mes, 1)
        if mes == 12:
            ultimo_dia = date(anio + 1, 1, 1) - timedelta(days=1)
        else:
            ultimo_dia = date(anio, mes + 1, 1) - timedelta(days=1)

        # Buscar pares de Sábado y Domingo en el mes
        sabados_domingos = []
        curr = primer_dia
        while curr <= ultimo_dia:
            if curr.weekday() == 5:  # Sábado
                domingo = curr + timedelta(days=1)
                if domingo <= ultimo_dia:
                    sabados_domingos.append((curr, domingo))
            curr += timedelta(days=1)

        if not sabados_domingos:
            return True # Si por alguna razón el mes no tiene fines de semana completos

        # Verificar si hay al menos un fin de semana donde NO tenga turnos asignados (ambos días libres)
        for sabado, domingo in sabados_domingos:
            asignaciones_fs = self.db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == controlador_id,
                TurnoAsignado.fecha.in_([sabado, domingo])
            .all())

            # Si no tiene registros en ese fin de semana o todos son francos/descansos/vacaciones, cuenta como fin de semana libre
            if not asignaciones_fs:
                return True
            
            # Comprobar si los turnos asignados son de descanso (ej. vacío, HU, VAC)
            libre = True
            for asig in asignaciones_fs:
                if asig.turno_codigo not in ["HU", "VACACIONES", "DISP", ""]:
                    libre = False
                    break
            if libre:
                return True

        return False # No ha tenido ningún fin de semana libre en todo el mes

    def validar_autonomia(self, controlador_id: str, codigo_turno: str, fecha: date) -> bool:
        """
        Regla 5 (Certificación Operativa):
        Mapea el código de turno requerido al TIPO de autonomía directo.
        Verifica que el controlador tenga la autonomía vigente Y habilitada (activa == True).
        """
        turno_a_tipo = {
            "SM": "SUP", "ST": "SUP", "SD": "SUP",
            "TM": "TWR", "TT": "TWR", "TN": "TWR", "TD": "TWR",
            "AM": "ACC", "AT": "ACC", "AD": "ACC",
            "GM": "GND", "GT": "GND", "GD": "GND",
            "OM": "OIA", "OT": "OIA", "OD": "OIA"
        }

        tipo_requerido = turno_a_tipo.get(codigo_turno)
        
        if not tipo_requerido:
            return True

        autonomia = self.db.query(Autonomia).filter(
            Autonomia.controlador_id == controlador_id,
            Autonomia.tipo == tipo_requerido,
            Autonomia.fecha_vencimiento >= fecha,
            Autonomia.activa == True
        ).first()

        return autonomia is not None

    def validar_aptitud_y_novedades(self, controlador_id: str, fecha: date) -> bool:
        """
        Validación general del estado del controlador:
        - Verifica que esté activo en el sistema.
        - Verifica que su examen o aptitud psicofísica no esté vencido.
        - Revisa si tiene novedades o licencias programadas (VAC, etc.).
        """
        ctrl = self.db.query(Controlador).filter(Controlador.id == controlador_id).first()
        if not ctrl or not ctrl.activo:
            return False

        if ctrl.aptitud_psicofisica_vencimiento and ctrl.aptitud_psicofisica_vencimiento < fecha:
            return False

        nov = self.db.query(NovedadProgramada).filter(
            NovedadProgramada.controlador_id == controlador_id,
            NovedadProgramada.fecha_inicio <= fecha,
            NovedadProgramada.fecha_fin >= fecha
        ).first()

        if nov:
            return False

        return True