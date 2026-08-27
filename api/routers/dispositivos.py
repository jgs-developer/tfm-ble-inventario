from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import (
    CaracteristicaOut,
    DeteccionResumen,
    DireccionOut,
    DispositivoDetalle,
    DispositivoOut,
    ExploracionOut,
    VulnerabilidadOut,
)
from api.services.clasificacion import (
    calcular_clasificacion,
    dias_distintos_de,
    dias_distintos_por_dispositivo,
)
from api.services.gatt import ExploracionGattError
from api.services.gatt import explorar_caracteristicas as explorar_caracteristicas_gatt
from api.services.vulnerabilidades import obtener_vulnerabilidades
from db.models import CaracteristicaDispositivo, Deteccion, DireccionDispositivo, Dispositivo, VulnerabilidadFabricante

router = APIRouter(prefix="/dispositivos", tags=["dispositivos"])

LIMITE_ULTIMAS_DETECCIONES = 20

PROPIEDADES_ESCRITURA = {"write", "write-without-response"}


def _tiene_escritura(caracteristicas) -> bool:
    return any(PROPIEDADES_ESCRITURA & set(c.propiedades) for c in caracteristicas)


@router.get("", response_model=list[DispositivoOut])
def listar_dispositivos(
    desde: datetime | None = None,
    hasta: datetime | None = None,
    db: Session = Depends(get_db),
) -> list[DispositivoOut]:

    query = db.query(Dispositivo)

    if desde is not None or hasta is not None:
        ids_en_rango = db.query(Deteccion.dispositivo_id).distinct()
        if desde is not None:
            ids_en_rango = ids_en_rango.filter(Deteccion.fecha_hora >= desde)
        if hasta is not None:
            ids_en_rango = ids_en_rango.filter(Deteccion.fecha_hora <= hasta)
        query = query.filter(Dispositivo.id.in_(ids_en_rango.scalar_subquery()))

    dispositivos = query.all()
    dias_por_dispositivo = dias_distintos_por_dispositivo(db)
    company_ids_vulnerables = {
        row[0] for row in db.query(VulnerabilidadFabricante.company_id).distinct()
    }

    return [
        DispositivoOut(
            id=d.id,
            nombre=d.nombre,
            fabricante=d.fabricante,
            primera_deteccion=d.primera_deteccion,
            ultima_deteccion=d.ultima_deteccion,
            num_detecciones=d.num_detecciones,
            clasificacion=calcular_clasificacion(dias_por_dispositivo.get(d.id, 0)),
            es_vulnerable=d.fabricante_company_id in company_ids_vulnerables,
        )
        for d in dispositivos
    ]


@router.get("/{dispositivo_id}", response_model=DispositivoDetalle)
def obtener_dispositivo(dispositivo_id: int, db: Session = Depends(get_db)) -> DispositivoDetalle:
    dispositivo = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    ultimas_detecciones = (
        db.query(Deteccion)
        .filter(Deteccion.dispositivo_id == dispositivo_id)
        .order_by(Deteccion.fecha_hora.desc())
        .limit(LIMITE_ULTIMAS_DETECCIONES)
        .all()
    )

    vulnerabilidades = obtener_vulnerabilidades(db, dispositivo.fabricante_company_id)
    caracteristicas = (
        db.query(CaracteristicaDispositivo)
        .filter(CaracteristicaDispositivo.dispositivo_id == dispositivo_id)
        .all()
    )

    return DispositivoDetalle(
        id=dispositivo.id,
        nombre=dispositivo.nombre,
        fabricante=dispositivo.fabricante,
        primera_deteccion=dispositivo.primera_deteccion,
        ultima_deteccion=dispositivo.ultima_deteccion,
        num_detecciones=dispositivo.num_detecciones,
        clasificacion=calcular_clasificacion(dias_distintos_de(db, dispositivo_id)),
        es_vulnerable=len(vulnerabilidades) > 0,
        direcciones=[DireccionOut.model_validate(d) for d in dispositivo.direcciones],
        ultimas_detecciones=[DeteccionResumen.model_validate(d) for d in ultimas_detecciones],
        vulnerabilidades=[VulnerabilidadOut.model_validate(v) for v in vulnerabilidades],
        caracteristicas=[CaracteristicaOut.model_validate(c) for c in caracteristicas],
        tiene_escritura=_tiene_escritura(caracteristicas),
    )


@router.post(
    "/{dispositivo_id}/explorar-caracteristicas",
    response_model=ExploracionOut,
    status_code=201,
)
async def explorar_caracteristicas_dispositivo(
    dispositivo_id: int, db: Session = Depends(get_db)
) -> ExploracionOut:

    dispositivo = db.query(Dispositivo).filter(Dispositivo.id == dispositivo_id).first()
    if dispositivo is None:
        raise HTTPException(status_code=404, detail="Dispositivo no encontrado")

    direccion = (
        db.query(DireccionDispositivo)
        .filter(DireccionDispositivo.dispositivo_id == dispositivo_id)
        .order_by(DireccionDispositivo.ultima_vez_vista.desc())
        .first()
    )
    if direccion is None:
        raise HTTPException(
            status_code=404,
            detail="El dispositivo no tiene ninguna direccion registrada",
        )

    try:
        caracteristicas_encontradas = await explorar_caracteristicas_gatt(direccion.direccion)
    except ExploracionGattError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error

    db.query(CaracteristicaDispositivo).filter(
        CaracteristicaDispositivo.dispositivo_id == dispositivo_id
    ).delete()

    filas = [
        CaracteristicaDispositivo(dispositivo_id=dispositivo_id, **datos)
        for datos in caracteristicas_encontradas
    ]
    db.add_all(filas)
    db.flush()

    return ExploracionOut(
        dispositivo_id=dispositivo_id,
        direccion=direccion.direccion,
        caracteristicas=[CaracteristicaOut.model_validate(f) for f in filas],
    )
