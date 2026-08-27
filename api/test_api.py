"""Tests de la API con pytest + TestClient (en memoria, sin uvicorn ni BD real)."""

from datetime import datetime
from unittest.mock import patch

import pytest
from bleak.exc import BleakError
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from api.deps import get_db
from api.main import app
from db.models import Base, DireccionDispositivo, VulnerabilidadFabricante


@pytest.fixture
def client():
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    # session_factory expuesta para tests que necesitan consultar la BD directamente.
    with TestClient(app) as c:
        c.session_factory = TestingSessionLocal
        yield c

    app.dependency_overrides.clear()
    engine.dispose()


# Company Identifiers del Bluetooth SIG (via tabla de bleak).
COMPANY_ID_APPLE = "76"
FABRICANTE_APPLE = "Apple, Inc."


def _post_deteccion(client, **campos):
    """POST /detecciones; 'direccion' es obligatoria."""
    campos.setdefault("direccion", "AA:BB:CC:DD:EE:FF")
    resp = client.post("/detecciones", json=campos)
    assert resp.status_code == 201, resp.text
    return resp.json()


def test_deteccion_nueva_crea_dispositivo_y_resuelve_fabricante(client):
    cuerpo = _post_deteccion(
        client,
        direccion="AA:BB:CC:DD:EE:01",
        manufacturer_data={COMPANY_ID_APPLE: "0215aabb"},
    )

    assert cuerpo["dispositivo_nuevo"] is True

    detalle = client.get(f"/dispositivos/{cuerpo['dispositivo_id']}").json()
    assert detalle["fabricante"] == FABRICANTE_APPLE


def test_misma_direccion_reutiliza_dispositivo_sin_duplicar_direccion(client):
    direccion = "AA:BB:CC:DD:EE:02"

    primera = _post_deteccion(client, direccion=direccion)
    segunda = _post_deteccion(client, direccion=direccion)

    assert primera["dispositivo_nuevo"] is True
    assert segunda["dispositivo_nuevo"] is False
    assert segunda["dispositivo_id"] == primera["dispositivo_id"]

    with client.session_factory() as db:
        filas = (
            db.query(DireccionDispositivo)
            .filter(DireccionDispositivo.direccion == direccion)
            .count()
        )
    assert filas == 1


def test_fabricante_solo_se_resuelve_en_la_primera_deteccion(client):
    direccion = "AA:BB:CC:DD:EE:03"

    _post_deteccion(
        client,
        direccion=direccion,
        manufacturer_data={COMPANY_ID_APPLE: "0215"},
    )
    # 301 = Sony Corporation: fabricante distinto para probar que no se sobrescribe.
    _post_deteccion(client, direccion=direccion, manufacturer_data={"301": "abcd"})
    _post_deteccion(client, direccion=direccion)

    disp_id = client.get("/dispositivos").json()[0]["id"]
    detalle = client.get(f"/dispositivos/{disp_id}").json()
    assert detalle["fabricante"] == FABRICANTE_APPLE


def test_nombre_se_sobrescribe_con_el_mas_reciente_no_vacio(client):
    direccion = "AA:BB:CC:DD:EE:04"

    _post_deteccion(client, direccion=direccion, nombre_anunciado="Nombre viejo")
    _post_deteccion(client, direccion=direccion, nombre_anunciado="Nombre nuevo")
    _post_deteccion(client, direccion=direccion)

    disp_id = client.get("/dispositivos").json()[0]["id"]
    detalle = client.get(f"/dispositivos/{disp_id}").json()
    assert detalle["nombre"] == "Nombre nuevo"


def test_clasificacion_persistente_vs_esporadico(client):
    persistente = "AA:BB:CC:DD:EE:05"
    _post_deteccion(client, direccion=persistente, fecha_hora="2026-08-01T10:00:00")
    _post_deteccion(client, direccion=persistente, fecha_hora="2026-08-02T10:00:00")

    esporadico = "AA:BB:CC:DD:EE:06"
    _post_deteccion(client, direccion=esporadico, fecha_hora="2026-08-01T11:00:00")

    por_direccion = {}
    for disp in client.get("/dispositivos").json():
        detalle = client.get(f"/dispositivos/{disp['id']}").json()
        for dir_obs in detalle["direcciones"]:
            por_direccion[dir_obs["direccion"]] = disp["clasificacion"]

    assert por_direccion[persistente] == "persistente"
    assert por_direccion[esporadico] == "esporadico"


def test_listado_filtra_por_rango_horario(client):
    _post_deteccion(client, direccion="AA:BB:CC:DD:EE:07", fecha_hora="2026-08-01T10:00:00")
    _post_deteccion(client, direccion="AA:BB:CC:DD:EE:08", fecha_hora="2026-08-05T10:00:00")

    en_rango = client.get(
        "/dispositivos", params={"desde": "2026-08-01T00:00:00", "hasta": "2026-08-02T00:00:00"}
    ).json()

    direcciones_en_rango = set()
    for disp in en_rango:
        detalle = client.get(f"/dispositivos/{disp['id']}").json()
        direcciones_en_rango.update(d["direccion"] for d in detalle["direcciones"])

    assert "AA:BB:CC:DD:EE:07" in direcciones_en_rango
    assert "AA:BB:CC:DD:EE:08" not in direcciones_en_rango


def test_dispositivo_inexistente_devuelve_404(client):
    resp = client.get("/dispositivos/999999")
    assert resp.status_code == 404


# Company Identifier de Telink Semiconductor (fabricante de chip con CVEs
# curados en cargar_vulnerabilidades.py, incluida la Zero LTK Installation).
COMPANY_ID_TELINK = "529"


def test_dispositivo_con_fabricante_vulnerable_trae_sus_cve(client):
    with client.session_factory() as db:
        db.add(VulnerabilidadFabricante(
            company_id=529,
            fabricante="Telink Semiconductor Co. Ltd",
            cve_id="CVE-2019-19194",
            nombre_vulnerabilidad="Zero LTK Installation",
            descripcion="Permite instalar una clave de sesion (LTK) de longitud cero.",
            severidad="Critica",
            fuente_url="https://asset-group.github.io/disclosures/sweyntooth/",
        ))
        db.commit()

    cuerpo = _post_deteccion(
        client,
        direccion="AA:BB:CC:DD:EE:09",
        manufacturer_data={COMPANY_ID_TELINK: "aabb"},
    )

    listado = client.get("/dispositivos").json()
    fila = next(d for d in listado if d["id"] == cuerpo["dispositivo_id"])
    assert fila["es_vulnerable"] is True

    detalle = client.get(f"/dispositivos/{cuerpo['dispositivo_id']}").json()
    assert detalle["es_vulnerable"] is True
    cve_ids = [v["cve_id"] for v in detalle["vulnerabilidades"]]
    assert "CVE-2019-19194" in cve_ids


def test_dispositivo_sin_vulnerabilidades_conocidas_trae_lista_vacia(client):
    cuerpo = _post_deteccion(
        client,
        direccion="AA:BB:CC:DD:EE:10",
        manufacturer_data={COMPANY_ID_APPLE: "0215aabb"},
    )

    listado = client.get("/dispositivos").json()
    fila = next(d for d in listado if d["id"] == cuerpo["dispositivo_id"])
    assert fila["es_vulnerable"] is False

    detalle = client.get(f"/dispositivos/{cuerpo['dispositivo_id']}").json()
    assert detalle["es_vulnerable"] is False
    assert detalle["vulnerabilidades"] == []


class _CaracteristicaGattFalsa:
    def __init__(self, uuid, handle, properties):
        self.uuid = uuid
        self.handle = handle
        self.properties = properties


class _ServicioGattFalso:
    def __init__(self, uuid, characteristics):
        self.uuid = uuid
        self.characteristics = characteristics


class _BleakClientFalso:

    def __init__(self, direccion, timeout=10.0, **kwargs):
        self.direccion = direccion

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    @property
    def services(self):
        return [
            _ServicioGattFalso(
                uuid="0000180f-0000-1000-8000-00805f9b34fb",
                characteristics=[
                    _CaracteristicaGattFalsa(
                        uuid="00002a19-0000-1000-8000-00805f9b34fb",
                        handle=42,
                        # write-without-response es la propiedad tipica de los
                        # dispositivos genericos sin cifrar que motivaron este filtro.
                        properties=["read", "write-without-response"],
                    ),
                ],
            )
        ]


def test_explorar_caracteristicas_conecta_y_guarda(client):
    direccion = "AA:BB:CC:DD:EE:11"
    disp_id = _post_deteccion(client, direccion=direccion)["dispositivo_id"]

    with patch("api.services.gatt.BleakClient", _BleakClientFalso):
        resp = client.post(f"/dispositivos/{disp_id}/explorar-caracteristicas")

    assert resp.status_code == 201, resp.text
    cuerpo = resp.json()
    assert cuerpo["direccion"] == direccion
    assert len(cuerpo["caracteristicas"]) == 1
    fila = cuerpo["caracteristicas"][0]
    assert fila["caracteristica_uuid"] == "00002a19-0000-1000-8000-00805f9b34fb"
    assert fila["handle"] == 42
    assert "write-without-response" in fila["propiedades"]

    detalle = client.get(f"/dispositivos/{disp_id}").json()
    assert detalle["tiene_escritura"] is True
    assert len(detalle["caracteristicas"]) == 1


def test_explorar_caracteristicas_fallo_conexion_devuelve_error_claro(client):
    direccion = "AA:BB:CC:DD:EE:12"
    disp_id = _post_deteccion(client, direccion=direccion)["dispositivo_id"]

    with patch(
        "api.services.gatt.BleakClient",
        side_effect=BleakError("dispositivo fuera de rango"),
    ):
        resp = client.post(f"/dispositivos/{disp_id}/explorar-caracteristicas")

    assert resp.status_code == 502
    assert "dispositivo fuera de rango" in resp.json()["detail"]


def test_explorar_caracteristicas_dispositivo_inexistente_devuelve_404(client):
    resp = client.post("/dispositivos/999999/explorar-caracteristicas")
    assert resp.status_code == 404
