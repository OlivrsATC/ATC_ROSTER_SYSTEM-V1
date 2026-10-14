from sqlalchemy.orm import Session
from datetime import date, timedelta
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.novedad import NovedadProgramada

class MotorReglasATC:
    def __init__(self, db: Session):
        self.db = db

    def validar_nocturnos_consecutivos(self, controlador_id: str, fecha: date, codigo_turno: str) -> bool:
        """
        Regla 1:
        - Lunes a Jueves: Máximo 2 nocturnos (TN u ON) seguidos, el tercer día se debe descansar.
        - Fin de semana (Viernes a Domingo): Máximo 3 noches, y el día siguiente al último servicio debe ser CP.
        """
        if codigo_turno not in ["TN", "ON"]:
            return True

        wd = fecha.weekday() # 0=Lunes, ..., 4=Viernes, 5=Sábado, 6=Domingo
        ayer = fecha - timedelta(days=1)
        anteayer = fecha - timedelta(days=2)

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

        if wd <= 3: # Lunes a Jueves
            if es_noche_ayer and es_noche_anteayer:
                return False # Ya lleva 2 noches seguidas, el 3ro debe descansar
        else: # Fin de semana (Vie, Sáb, Dom)
            if es_noche_ayer and es_noche_anteayer:
                trasanteayer = fecha - timedelta(days=3)
                asig_tras = self.db.query(TurnoAsignado).filter(
                    TurnoAsignado.controlador_id == controlador_id,
                    TurnoAsignado.fecha == trasanteayer
                ).first()
                if asig_tras and asig_tras.turno_codigo in ["TN", "ON"]:
                    return False # Máximo 3 noches en fin de semana
        return True

    def validar_autonomia(self, controlador_id: str, codigo_turno: str, fecha: date) -> bool:
        """
        Regla 5: Si se escoge manualmente una autonomía con la que el personal no cuente, se alerta.
        """
        pos_map = {
            "TM": "TORRE", "TT": "TORRE", "TN": "TORRE",
            "AM": "AREA", "AT": "AREA",
            "GM": "SUPERFICIE", "GT": "SUPERFICIE",
            "OM": "OIA", "OT": "OIA", "ON": "OIA",
            "SM": "SUPERVISOR", "ST": "SUPERVISOR"
        }

        posicion_requerida = pos_map.get(codigo_turno)
        if not posicion_requerida:
            return True # Turnos especiales, administrativos o descanso no requieren autonomía operativa

        autonomia = self.db.query(Autonomia).filter(
            Autonomia.controlador_id == controlador_id,
            Autonomia.posicion == posicion_requerida,
            Autonomia.fecha_vencimiento >= fecha
        ).first()

        return autonomia is not None

    def validar_aptitud_y_novedades(self, controlador_id: str, fecha: date) -> bool:
        ctrl = self.db.query(Controlador).filter(Controlador.id == controlador_id).first()
        if not ctrl or not ctrl.activo:
            return False
        if ctrl.aptitud_psicofisica_vencimiento and ctrl.aptitud_psicofisica_vencimiento < fecha:
            return False

        # Verificar si tiene novedad programada (VAC, REEN, etc.)
        nov = self.db.query(NovedadProgramada).filter(
            NovedadProgramada.controlador_id == controlador_id,
            NovedadProgramada.fecha_inicio <= fecha,
            NovedadProgramada.fecha_fin >= fecha
        ).first()
        if nov:
            return False

        return True