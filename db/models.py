"""Modelos SQLAlchemy: dispositivos, direcciones observadas y detecciones."""

from datetime import datetime, timezone

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON, Index
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Dispositivo(Base):

    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True)
    nombre = Column(String, nullable=True)
    fabricante = Column(String, nullable=True)
    fabricante_company_id = Column(Integer, nullable=True, index=True)
    primera_deteccion = Column(DateTime, nullable=True)
    ultima_deteccion = Column(DateTime, nullable=True)
    num_detecciones = Column(Integer, nullable=False, default=0)

    direcciones = relationship(
        "DireccionDispositivo",
        back_populates="dispositivo",
        cascade="all, delete-orphan",
    )
    detecciones = relationship(
        "Deteccion",
        back_populates="dispositivo",
        cascade="all, delete-orphan",
    )


class DireccionDispositivo(Base):

    __tablename__ = "direcciones_dispositivo"

    id = Column(Integer, primary_key=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    direccion = Column(String, nullable=False, unique=True, index=True)
    tipo_direccion = Column(String, nullable=True)
    primera_vez_vista = Column(DateTime, nullable=False, default=utcnow)
    ultima_vez_vista = Column(DateTime, nullable=False, default=utcnow)

    dispositivo = relationship("Dispositivo", back_populates="direcciones")


class Deteccion(Base):
    __tablename__ = "detecciones"

    id = Column(Integer, primary_key=True)
    direccion_id = Column(
        Integer, ForeignKey("direcciones_dispositivo.id"), nullable=False
    )
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)
    fecha_hora = Column(DateTime, nullable=False, default=utcnow)
    rssi = Column(Integer, nullable=True)
    nombre_anunciado = Column(String, nullable=True)
    uuids = Column(JSON, nullable=True)
    manufacturer_data = Column(JSON, nullable=True)
    service_data = Column(JSON, nullable=True)

    dispositivo = relationship("Dispositivo", back_populates="detecciones")
    direccion = relationship("DireccionDispositivo")

    __table_args__ = (
        Index("ix_detecciones_fecha_dispositivo", "fecha_hora", "dispositivo_id"),
        Index("ix_detecciones_dispositivo_fecha", "dispositivo_id", "fecha_hora"),
    )


class VulnerabilidadFabricante(Base):
    __tablename__ = "vulnerabilidades_fabricante"

    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, nullable=False, index=True)
    fabricante = Column(String, nullable=False)
    cve_id = Column(String, nullable=True)
    nombre_vulnerabilidad = Column(String, nullable=False)
    descripcion = Column(String, nullable=False)
    severidad = Column(String, nullable=True)
    fuente_url = Column(String, nullable=False)


class CaracteristicaDispositivo(Base):
    __tablename__ = "caracteristicas_dispositivo"

    id = Column(Integer, primary_key=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False, index=True)
    servicio_uuid = Column(String, nullable=False)
    servicio_nombre = Column(String, nullable=True)
    caracteristica_uuid = Column(String, nullable=False)
    caracteristica_nombre = Column(String, nullable=True)
    handle = Column(Integer, nullable=True)
    propiedades = Column(JSON, nullable=False)  # p.ej. ["read", "write", "notify"]
    fecha_exploracion = Column(DateTime, nullable=False, default=utcnow)

    dispositivo = relationship("Dispositivo")
