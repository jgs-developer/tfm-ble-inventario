"""Esquemas Pydantic de entrada/salida de la API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DeteccionIn(BaseModel):
    """Detección cruda tal como la envía el agente para una lectura de Advertising."""

    direccion: str
    tipo_direccion: str | None = None
    rssi: int | None = None
    nombre_anunciado: str | None = None
    uuids: list[str] | None = None
    # Clave: Company Identifier (Bluetooth SIG) como string decimal, ej. "76".
    # Valor: datos del fabricante en hexadecimal.
    manufacturer_data: dict[str, str] | None = None
    service_data: dict[str, str] | None = None
    fecha_hora: datetime | None = None


class DeteccionOut(BaseModel):
    dispositivo_id: int
    dispositivo_nuevo: bool


class DireccionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    direccion: str
    tipo_direccion: str | None
    primera_vez_vista: datetime
    ultima_vez_vista: datetime


class DeteccionResumen(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    fecha_hora: datetime
    rssi: int | None
    nombre_anunciado: str | None


class VulnerabilidadOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    cve_id: str | None
    nombre_vulnerabilidad: str
    descripcion: str
    severidad: str | None
    fuente_url: str


class DispositivoOut(BaseModel):
    id: int
    nombre: str | None
    fabricante: str | None
    primera_deteccion: datetime | None
    ultima_deteccion: datetime | None
    num_detecciones: int
    # "persistente" | "esporadico" - calculada al vuelo, ver services/clasificacion.py
    clasificacion: str
    # true si el fabricante (por company_id) tiene alguna fila en vulnerabilidades_fabricante
    es_vulnerable: bool


class CaracteristicaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    servicio_uuid: str
    servicio_nombre: str | None
    caracteristica_uuid: str
    caracteristica_nombre: str | None
    handle: int | None
    propiedades: list[str]


class ExploracionOut(BaseModel):
    """Respuesta de POST /dispositivos/{id}/explorar-caracteristicas."""

    dispositivo_id: int
    direccion: str
    caracteristicas: list[CaracteristicaOut]


class DispositivoDetalle(DispositivoOut):
    direcciones: list[DireccionOut]
    ultimas_detecciones: list[DeteccionResumen]
    vulnerabilidades: list[VulnerabilidadOut]
    # Vacía si nunca se ha explorado (POST /explorar-caracteristicas).
    caracteristicas: list[CaracteristicaOut]
    # true si alguna característica tiene "write" o "write-without-response".
    tiene_escritura: bool
