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

    def validar_nocturnos_consecutivos(self, controlador_id: str, fecha: date, codigo_turno: str) -> bool:
        """
        Regla 1 (Gestión de fatiga operativa):
        - Lunes a Jueves: Máximo 2 nocturnos (TN u ON) seguidos; al 3er día se debe descansar.
        - Fin de semana (Viernes a Domingo): Máximo 3 noches consecutivas.
        """
        # Si el turno a asignar no es nocturno (TN u ON), la regla se aprueba automáticamente
        if codigo_turno not in ["TN", "ON"]:
            return True

        wd = fecha.weekday() # 0=Lunes, 1=Martes, ..., 4=Viernes, 5=Sábado, 6=Domingo
        ayer = fecha - timedelta(days=1)
        anteayer = fecha - timedelta(days=2)

        # Consultar si el controlador realizó turnos nocturnos ayer y anteayer
        asig_ayer = self.db.query(TurnoAsignado).filter(
            TurnoAsignado.controlador_id == controlador_id,
            TurnoAsignado.fecha == ayer
        ).first()

        asig_anteayer = self.db.query(TurnoAsignado).filter(
            TurnoAsignado.controlador_id == controlador_id,
            TurnoAsignado.fecha == anteayer
        ).first()

        es_noche_ayer = asig_ayer and asig_ayer.turno_codigo in ["TN", "ON"]
        es_noche_anteayer = asig_anteayer and asig_anteayer.turno_codigo in ["TN", "ON"]

        # Lunes a Jueves (wd <= 3)
        if wd <= 3:
            if es_noche_ayer and es_noche_anteayer:
                return False # Rechazado: Ya acumula 2 noches seguidas, debe descansar el 3er día

        # Fin de semana (Viernes a Domingo)
        else:
            if es_noche_ayer and es_noche_anteayer:
                trasanteayer = fecha - timedelta(days=3)
                asig_tras = self.db.query(TurnoAsignado).filter(
                    TurnoAsignado.controlador_id == controlador_id,
                    TurnoAsignado.fecha == trasanteayer
                ).first()
                if asig_tras and asig_tras.turno_codigo in ["TN", "ON"]:
                    return False # Rechazado: Límite de 3 noches consecutivas alcanzado

        return True

    def validar_autonomia(self, controlador_id: str, codigo_turno: str, fecha: date) -> bool:
        """
        Regla 5 (Certificación Operativa):
        Mapea el código de turno requerido al TIPO de autonomía directo (SUP, TWR, ACC, GND, OIA).
        Verifica que el controlador tenga la autonomía vigente Y habilitada (activa == True).
        """
        # Mapeo directo de Códigos de Turno a Tipos de Autonomía
        turno_a_tipo = {
            "SM": "SUP", "ST": "SUP", "SD": "SUP",
            "TM": "TWR", "TT": "TWR", "TN": "TWR", "TD": "TWR",
            "AM": "ACC", "AT": "ACC", "AD": "ACC",
            "GM": "GND", "GT": "GND", "GD": "GND",
            "OM": "OIA", "OT": "OIA", "ON": "OIA", "OD": "OIA"
        }

        tipo_requerido = turno_a_tipo.get(codigo_turno)
        
        # Si el turno no requiere autonomía operativa (HU, VAC, CP, DISP, etc.), aprueba
        if not tipo_requerido:
            return True

        # Consultar la autonomía correspondiente en la base de datos
        autonomia = self.db.query(Autonomia).filter(
            Autonomia.controlador_id == controlador_id,
            Autonomia.tipo == tipo_requerido,           # 👈 Coincidencia directa por TIPO
            Autonomia.fecha_vencimiento >= fecha,       # 👈 Verifica que no esté vencida
            Autonomia.activa == True                    # 👈 NUEVO: Verifica que esté HABILITADA
        ).first()

        # Retorna True solo si existe la autonomía válida y activa
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

        # Si la aptitud psicofísica expiró antes de la fecha evaluada, no es apto
        if ctrl.aptitud_psicofisica_vencimiento and ctrl.aptitud_psicofisica_vencimiento < fecha:
            return False

        # Verificar si tiene licencias/vacaciones/permisos programados para esa fecha
        nov = self.db.query(NovedadProgramada).filter(
            NovedadProgramada.controlador_id == controlador_id,
            NovedadProgramada.fecha_inicio <= fecha,
            NovedadProgramada.fecha_fin >= fecha
        ).first()

        if nov:
            return False # No disponible para asignaciones operacionales

        return True