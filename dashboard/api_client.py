"""Cliente HTTP hacia la API del inventario BLE."""

from datetime import datetime
from typing import Optional

import requests

from config import API_URL


def obtener_dispositivos(
    desde: Optional[datetime] = None, hasta: Optional[datetime] = None
) -> list[dict]:
    parametros = {}
    if desde is not None:
        parametros["desde"] = desde.isoformat()
    if hasta is not None:
        parametros["hasta"] = hasta.isoformat()

    respuesta = requests.get(f"{API_URL}/dispositivos", params=parametros, timeout=5)
    respuesta.raise_for_status()
    return respuesta.json()


def obtener_dispositivo(dispositivo_id: int) -> dict:
    respuesta = requests.get(f"{API_URL}/dispositivos/{dispositivo_id}", timeout=5)
    respuesta.raise_for_status()
    return respuesta.json()


def explorar_caracteristicas(dispositivo_id: int) -> dict:
    respuesta = requests.post(
        f"{API_URL}/dispositivos/{dispositivo_id}/explorar-caracteristicas",
        timeout=20,
    )
    respuesta.raise_for_status()
    return respuesta.json()
