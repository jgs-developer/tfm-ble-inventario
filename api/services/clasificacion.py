"""Clasifica un dispositivo como persistente o esporádico según los días distintos en que fue detectado."""

from sqlalchemy import func
from sqlalchemy.orm import Session

from db.models import Deteccion

UMBRAL_DIAS_PERSISTENTE = 2


def calcular_clasificacion(dias_distintos: int) -> str:
    return "persistente" if dias_distintos >= UMBRAL_DIAS_PERSISTENTE else "esporadico"


def dias_distintos_por_dispositivo(db: Session) -> dict[int, int]:
    filas = (
        db.query(
            Deteccion.dispositivo_id,
            func.count(func.distinct(func.date(Deteccion.fecha_hora))),
        )
        .group_by(Deteccion.dispositivo_id)
        .all()
    )
    return dict(filas)


def dias_distintos_de(db: Session, dispositivo_id: int) -> int:
    return (
        db.query(func.count(func.distinct(func.date(Deteccion.fecha_hora))))
        .filter(Deteccion.dispositivo_id == dispositivo_id)
        .scalar()
        or 0
    )
