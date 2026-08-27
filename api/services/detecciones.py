"""Resuelve dirección -> dispositivo (1 dirección = 1 dispositivo) y registra la detección."""

from datetime import datetime, timezone

from sqlalchemy.orm import Session

from api.schemas import DeteccionIn
from api.services.fabricante import resolver_fabricante
from db.models import Deteccion, DireccionDispositivo, Dispositivo


def registrar_deteccion(db: Session, datos: DeteccionIn) -> tuple[Dispositivo, bool]:

    fecha_hora = datos.fecha_hora or datetime.now(timezone.utc)

    direccion = (
        db.query(DireccionDispositivo)
        .filter(DireccionDispositivo.direccion == datos.direccion)
        .first()
    )
    dispositivo_nuevo = direccion is None

    if direccion is None:
        # Fabricante: se resuelve UNA sola vez, al crear el dispositivo.
        # El hardware no cambia de fabricante con el tiempo (a diferencia
        # del nombre anunciado), así que no se vuelve a tocar después.
        fabricante, fabricante_company_id = resolver_fabricante(datos.manufacturer_data)
        dispositivo = Dispositivo(
            fabricante=fabricante,
            fabricante_company_id=fabricante_company_id,
            primera_deteccion=fecha_hora,
            num_detecciones=0,
        )
        db.add(dispositivo)
        db.flush()  # asigna dispositivo.id

        direccion = DireccionDispositivo(
            dispositivo_id=dispositivo.id,
            direccion=datos.direccion,
            tipo_direccion=datos.tipo_direccion,
            primera_vez_vista=fecha_hora,
            ultima_vez_vista=fecha_hora,
        )
        db.add(direccion)
        db.flush()  # asigna direccion.id
    else:
        dispositivo = direccion.dispositivo
        direccion.ultima_vez_vista = fecha_hora

    # Nombre: se sobrescribe en cada detección con el último no vacío.
    if datos.nombre_anunciado:
        dispositivo.nombre = datos.nombre_anunciado

    dispositivo.num_detecciones += 1
    dispositivo.ultima_deteccion = fecha_hora
    if dispositivo.primera_deteccion is None:
        dispositivo.primera_deteccion = fecha_hora

    deteccion = Deteccion(
        direccion_id=direccion.id,
        dispositivo_id=dispositivo.id,
        fecha_hora=fecha_hora,
        rssi=datos.rssi,
        nombre_anunciado=datos.nombre_anunciado,
        uuids=datos.uuids,
        manufacturer_data=datos.manufacturer_data,
        service_data=datos.service_data,
    )
    db.add(deteccion)

    return dispositivo, dispositivo_nuevo
