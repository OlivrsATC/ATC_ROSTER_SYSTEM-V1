from datetime import date, timedelta
from sqlalchemy.orm import Session
from app.models.asignacion import TurnoAsignado
from app.models.controlador import Controlador

class MotorReglasATC:
    def __init__(self, db: Session):
        self.db = db

    def validar_aptitud_y_novedades(self, controlador_id: str, fecha_turno: date) -> bool:
        """Verifica si el controlador tiene novedades activas o aptitud psicofísica vencida en la fecha."""
        controlador = self.db.query(Controlador).filter(Controlador.id == controlador_id).first()
        if not controlador or not controlador.activo:
            return False

        # Validación de aptitud psicofísica
        if controlador.aptitud_psicofisica_vencimiento < fecha_turno:
            return False

        # Validación de novedades (Vacaciones, incapacidad, comisiones, etc.)
        for novedad in controlador.novedades:
            if novedad.fecha_inicio <= fecha_turno <= novedad.fecha_fin:
                return False  # Bloqueo absoluto por novedad

        return True

    def verificar_regla_disponible_obligatorio(self, controlador_id: str, fecha_propuesta: date, codigo_turno_propuesto: str) -> bool:
        """
        Regla del Disponible: Si el día anterior tuvo un turno de Tarde (termina en T), 
        Noche (N) o Horario de Oficina (HU), el día actual el único turno lógico/permitido 
        por descanso es DISP (o novedad). Si intenta asignar otra cosa sin cumplir, retorna False.
        """
        # Si el turno que se quiere asignar ya es DISP, pasa sin problema
        if codigo_turno_propuesto.upper() == 'DISP':
            return True

        dia_anterior = fecha_propuesta - timedelta(days=1)
        turno_previo = self.db.query(TurnoAsignado).filter(
            TurnoAsignado.controlador_id == controlador_id,
            TurnoAsignado.fecha == dia_anterior
        ).first()

        if turno_previo:
            codigo_previo = turno_previo.turno_codigo.upper()
            # Si el turno anterior fue Tarde, Noche o HU, se exige DISP
            if codigo_previo.endswith('T') or codigo_previo.endswith('N') or codigo_previo == 'HU':
                return False 
        
        return True

    def validar_limite_noches(self, controlador_id: str, fecha_propuesta: date, codigo_turno: str) -> bool:
        """Valida máximas noches consecutivas (2 entre semana, 3 en FDS)."""
        if not codigo_turno.upper().endswith('N'):
            return True

        conteo_noches = 0
        dia_eval = fecha_propuesta - timedelta(days=1)
        
        while True:
            turno_ant = self.db.query(TurnoAsignado).filter(
                TurnoAsignado.controlador_id == controlador_id,
                TurnoAsignado.fecha == dia_eval
            ).first()
            
            if turno_ant and turno_ant.turno_codigo.upper().endswith('N'):
                conteo_noches += 1
                dia_eval -= timedelta(days=1)
            else:
                break

        # Fin de semana (Viernes=4, Sábado=5, Domingo=6) vs Entre semana (Lunes a Jueves)
        es_fin_de_semana = fecha_propuesta.weekday() >= 4  
        limite_permitido = 3 if es_fin_de_semana else 2

        if conteo_noches >= limite_permitido:
            return False  # Incumple regla de descanso por noches consecutivas

        return True