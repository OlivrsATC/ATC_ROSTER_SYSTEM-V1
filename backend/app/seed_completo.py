from app.database import SessionLocal, engine, Base
import datetime

# IMPORTANTE: Importar TODOS los modelos para que SQLAlchemy configure los mappers correctamente
from app.models.controlador import Controlador
from app.models.autonomia import Autonomia
from app.models.turno import TurnoCat
from app.models.novedad import NovedadPersonal
from app.models.asignacion import TurnoAsignado

def seed_squadron():
    # 1. Crear/asegurar tablas en la base de datos
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    if db.query(Controlador).first():
        print("El personal ya se encuentra inicializado en la base de datos.")
        db.close()
        return

    # 2. Añadir turnos adicionales de la matriz institucional
    turnos_extra = [
        {"id": "VEL", "codigo": "VEL", "nombre": "Velásquez", "tipo_servicio": "Operativo", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 2},
        {"id": "CP", "codigo": "CP", "nombre": "Compensatorio", "tipo_servicio": "Operativo", "hora_inicio": datetime.time(7, 0), "hora_fin": datetime.time(13, 0), "peso_equity": 3},
        {"id": "VAC", "codigo": "VAC", "nombre": "Vacaciones", "tipo_servicio": "Novedad", "hora_inicio": None, "hora_fin": None, "peso_equity": 0},
        {"id": "REEN", "codigo": "REEN", "nombre": "Reentrenamiento Militar", "tipo_servicio": "Instruccion", "hora_inicio": datetime.time(7, 30), "hora_fin": datetime.time(12, 0), "peso_equity": 1},
        {"id": "PAT", "codigo": "PAT", "nombre": "Patrulla", "tipo_servicio": "Seguridad", "hora_inicio": datetime.time(6, 0), "hora_fin": datetime.time(18, 0), "peso_equity": 2},
        {"id": "INS", "codigo": "INS", "nombre": "Instrucción", "tipo_servicio": "Instruccion", "hora_inicio": datetime.time(8, 0), "hora_fin": datetime.time(12, 0), "peso_equity": 1},
    ]

    for t in turnos_extra:
        if not db.query(TurnoCat).filter(TurnoCat.codigo == t["codigo"]).first():
            db.add(TurnoCat(**t))
    db.commit()

    # 3. Datos del personal clave del escuadrón
    controladores_data = [
        {
            "id": "c1", "identificacion": "77001", "nombres": "DIEGO FERNANDO", "apellidos": "BUSTOS NIETO",
            "email": "diegobustos@fac.mil.co", "rol": "SUPERVISOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2027, 12, 31),
            "autonomias": [{"id": "aut1", "tipo": "SUP", "posicion": "SUPERVISOR GENERAL", "fecha_obtencion": datetime.date(2020, 1, 1), "fecha_vencimiento": datetime.date(2027, 12, 31)}]
        },
        {
            "id": "c2", "identificacion": "80002", "nombres": "JAIRO ALBERTO", "apellidos": "RAMIREZ TORRES",
            "email": "jairoramirez@fac.mil.co", "rol": "CONTROLADOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2027, 10, 15),
            "autonomias": [{"id": "aut2", "tipo": "TWR", "posicion": "TORRE DE CONTROL", "fecha_obtencion": datetime.date(2021, 5, 10), "fecha_vencimiento": datetime.date(2027, 10, 15)}]
        },
        {
            "id": "c3", "identificacion": "84003", "nombres": "DANIEL ALBERTO", "apellidos": "MORA VALDERRAMA",
            "email": "danielmora@fac.mil.co", "rol": "CONTROLADOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2027, 11, 20),
            "autonomias": [{"id": "aut3", "tipo": "ACC", "posicion": "CONTROL DE AREA", "fecha_obtencion": datetime.date(2022, 3, 1), "fecha_vencimiento": datetime.date(2027, 11, 20)}]
        },
        {
            "id": "c4", "identificacion": "86004", "nombres": "KEVIN ANDRES", "apellidos": "DEVIA AGUILAR",
            "email": "kevindevia@fac.mil.co", "rol": "CONTROLADOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2027, 8, 30),
            "autonomias": [{"id": "aut4", "tipo": "TWR", "posicion": "TORRE DE CONTROL", "fecha_obtencion": datetime.date(2022, 6, 15), "fecha_vencimiento": datetime.date(2027, 8, 30)}]
        },
        {
            "id": "c5", "identificacion": "88088", "nombres": "CARLOS ANDRES", "apellidos": "OLIVEROS MARIN",
            "email": "carlosoliveros@fac.mil.co", "rol": "SUPERVISOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2028, 4, 20),
            "autonomias": [
                {"id": "aut5_1", "tipo": "SUP", "posicion": "SUPERVISOR ATC", "fecha_obtencion": datetime.date(2023, 1, 1), "fecha_vencimiento": datetime.date(2028, 4, 20)},
                {"id": "aut5_2", "tipo": "TWR", "posicion": "TORRE", "fecha_obtencion": datetime.date(2021, 1, 1), "fecha_vencimiento": datetime.date(2028, 4, 20)}
            ]
        },
        {
            "id": "c6", "identificacion": "90090", "nombres": "ANYELICA VIVIANA", "apellidos": "TRIANA OROZCO",
            "email": "anyelicatriana@fac.mil.co", "rol": "CONTROLADOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2027, 9, 10),
            "autonomias": [{"id": "aut6", "tipo": "ACC", "posicion": "CONTROL DE AREA", "fecha_obtencion": datetime.date(2022, 9, 1), "fecha_vencimiento": datetime.date(2027, 9, 10)}]
        },
        {
            "id": "c7", "identificacion": "90091", "nombres": "ANDERSON ESNEIDER", "apellidos": "BUITRAGO GONZALEZ",
            "email": "andersonbuitrago@fac.mil.co", "rol": "CONTROLADOR", "activo": True,
            "aptitud_psicofisica_vencimiento": datetime.date(2027, 12, 1),
            "autonomias": [{"id": "aut7", "tipo": "TWR", "posicion": "TORRE", "fecha_obtencion": datetime.date(2023, 3, 1), "fecha_vencimiento": datetime.date(2027, 12, 1)}]
        }
    ]

    for c_data in controladores_data:
        autonomias_data = c_data.pop("autonomias")
        ctrl = Controlador(**c_data)
        db.add(ctrl)
        db.commit()
        for aut in autonomias_data:
            db.add(Autonomia(controlador_id=ctrl.id, **aut))
        db.commit()

    db.close()
    print("Escuadrón 115 inicializado con éxito.")

if __name__ == "__main__":
    seed_squadron()