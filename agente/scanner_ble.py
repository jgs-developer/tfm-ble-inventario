"""Agente BLE: sesiones de escaneo pasivo periódicas, envía cada detección a la API."""

import asyncio
import logging

import requests
from bleak import BleakScanner

from config import API_URL, SCAN_DURATION_SECONDS, SCAN_INTERVAL_SECONDS

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("agente_ble")

DETECCIONES_ENDPOINT = f"{API_URL}/detecciones"


def _bytes_a_hex(data: dict) -> dict:
    return {str(clave): valor.hex() for clave, valor in data.items()}


def _construir_payload(device, adv) -> dict:
    return {
        "direccion": device.address,
        "rssi": adv.rssi,
        "nombre_anunciado": device.name,
        "uuids": list(adv.service_uuids) if adv.service_uuids else None,
        "manufacturer_data": (
            _bytes_a_hex(adv.manufacturer_data) if adv.manufacturer_data else None
        ),
        "service_data": (
            _bytes_a_hex(adv.service_data) if adv.service_data else None
        ),
    }


def _enviar_deteccion(payload: dict) -> None:
    """Envía una detección a la API. Si falla, loggea y continúa."""
    try:
        respuesta = requests.post(DETECCIONES_ENDPOINT, json=payload, timeout=5)
        respuesta.raise_for_status()
        cuerpo = respuesta.json()
        estado = "nuevo" if cuerpo.get("dispositivo_nuevo") else "existente"
        logger.info(
            "Deteccion enviada: %s (dispositivo %s, id=%s)",
            payload["direccion"],
            estado,
            cuerpo.get("dispositivo_id"),
        )
    except requests.exceptions.RequestException as error:
        logger.error(
            "No se pudo enviar la deteccion de %s: %s", payload["direccion"], error
        )


async def _ejecutar_sesion_de_escaneo() -> None:
    logger.info("Iniciando sesion de escaneo (%ss)...", SCAN_DURATION_SECONDS)
    dispositivos = await BleakScanner.discover(
        timeout=SCAN_DURATION_SECONDS, return_adv=True
    )
    logger.info("Sesion completada: %d dispositivos detectados.", len(dispositivos))

    for _, (device, adv) in dispositivos.items():
        payload = _construir_payload(device, adv)
        _enviar_deteccion(payload)


async def main() -> None:
    logger.info("Agente BLE arrancado. API destino: %s", API_URL)
    while True:
        await _ejecutar_sesion_de_escaneo()
        logger.info(
            "Esperando %ss antes de la siguiente sesion...", SCAN_INTERVAL_SECONDS
        )
        await asyncio.sleep(SCAN_INTERVAL_SECONDS)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Agente detenido por el usuario (Ctrl+C).")
