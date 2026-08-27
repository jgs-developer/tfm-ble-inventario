"""Consulta vulnerabilidades BLE conocidas por Company Identifier del Bluetooth SIG."""

from sqlalchemy.orm import Session

from db.models import VulnerabilidadFabricante


def obtener_vulnerabilidades(db: Session, company_id: int | None) -> list[VulnerabilidadFabricante]:
    if company_id is None:
        return []

    return (
        db.query(VulnerabilidadFabricante)
        .filter(VulnerabilidadFabricante.company_id == company_id)
        .all()
    )
