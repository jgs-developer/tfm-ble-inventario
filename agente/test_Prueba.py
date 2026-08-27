"""Testing del agente: simula un dispositivo BLE y una API local
para validar el flujo completo sin hardware real."""

import asyncio
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

recibido = []


class FakeAPIHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        largo = int(self.headers["Content-Length"])
        cuerpo = json.loads(self.rfile.read(largo))
        recibido.append(cuerpo)
        self.send_response(201)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        respuesta = {"dispositivo_id": len(recibido), "dispositivo_nuevo": True}
        self.wfile.write(json.dumps(respuesta).encode())

    def log_message(self, format, *args):
        pass  # silenciar logs del servidor de prueba


def _dispositivos_falsos():
    device = SimpleNamespace(address="AA:BB:CC:DD:EE:01", name="AirTag falso")
    adv = SimpleNamespace(
        rssi=-55,
        service_uuids=["0000180f-0000-1000-8000-00805f9b34fb"],
        manufacturer_data={76: b"\x02\x15\xaa\xbb\xcc\xdd\xee\xff"},
        service_data={},
    )
    return {"AA:BB:CC:DD:EE:01": (device, adv)}


async def _run():
    servidor = HTTPServer(("127.0.0.1", 8000), FakeAPIHandler)
    hilo = threading.Thread(target=servidor.serve_forever, daemon=True)
    hilo.start()

    with patch(
        "scanner_ble.BleakScanner.discover",
        new=AsyncMock(return_value=_dispositivos_falsos()),
    ):
        from scanner_ble import _ejecutar_sesion_de_escaneo

        await _ejecutar_sesion_de_escaneo()

    servidor.shutdown()

    assert len(recibido) == 1, f"Se esperaba 1 peticion recibida, llegaron {len(recibido)}"
    payload = recibido[0]
    assert payload["direccion"] == "AA:BB:CC:DD:EE:01"
    assert payload["manufacturer_data"] == {"76": "0215aabbccddeeff"}
    assert payload["service_data"] is None  # dict vacio -> None, tratado como "sin datos"
    print("OK -- payload recibido por el servidor: ")
    print(json.dumps(payload, indent=2))


if __name__ == "__main__":
    asyncio.run(_run())
