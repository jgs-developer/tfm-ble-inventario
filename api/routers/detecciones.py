from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api.deps import get_db
from api.schemas import DeteccionIn, DeteccionOut
from api.services.detecciones import registrar_deteccion

router = APIRouter(prefix="/detecciones", tags=["detecciones"])


@router.post("", response_model=DeteccionOut, status_code=201)
def crear_deteccion(datos: DeteccionIn, db: Session = Depends(get_db)) -> DeteccionOut:
    dispositivo, dispositivo_nuevo = registrar_deteccion(db, datos)
    return DeteccionOut(dispositivo_id=dispositivo.id, dispositivo_nuevo=dispositivo_nuevo)
