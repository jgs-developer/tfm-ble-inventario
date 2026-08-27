"""Punto de entrada de la API REST."""

from contextlib import asynccontextmanager

from fastapi import FastAPI

from api.routers import detecciones, dispositivos
from db.database import init_db


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(
    title="TFM - Inventario BLE",
    description="Ingesta y consulta del inventario de dispositivos BLE detectados pasivamente.",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(detecciones.router)
app.include_router(dispositivos.router)
