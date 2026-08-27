"""Explora servicios y características GATT de un dispositivo BLE mediante
conexión activa explícita """
from bleak import BleakClient
from bleak.exc import BleakError
from bleak.uuids import uuidstr_to_str


class ExploracionGattError(Exception):
    """La conexión BLE activa (no el escaneo pasivo) falló: timeout,
    dispositivo fuera de rango, o error del backend BLE."""


async def explorar_caracteristicas(direccion: str, timeout: float = 10.0) -> list[dict]:
    try:
        async with BleakClient(direccion, timeout=timeout) as client:
            return [
                {
                    "servicio_uuid": service.uuid,
                    "servicio_nombre": uuidstr_to_str(service.uuid),
                    "caracteristica_uuid": char.uuid,
                    "caracteristica_nombre": uuidstr_to_str(char.uuid),
                    "handle": char.handle,
                    "propiedades": list(char.properties),
                }
                for service in client.services
                for char in service.characteristics
            ]
    except (BleakError, TimeoutError, OSError) as error:
        raise ExploracionGattError(
            f"No se pudo conectar con {direccion}: {error}"
        ) from error
