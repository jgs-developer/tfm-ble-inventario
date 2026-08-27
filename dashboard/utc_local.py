"""Conversión entre UTC y hora local en el dashboard, manteniendo la API y la BD en UTC."""

from datetime import datetime
from zoneinfo import ZoneInfo

ZONA_LOCAL = ZoneInfo("Europe/Madrid")
UTC = ZoneInfo("UTC")


def local_a_utc_naive(dt_local: datetime) -> datetime:
    return dt_local.replace(tzinfo=ZONA_LOCAL).astimezone(UTC).replace(tzinfo=None)


def utc_naive_a_local(dt_utc: datetime) -> datetime:
    return dt_utc.replace(tzinfo=UTC).astimezone(ZONA_LOCAL).replace(tzinfo=None)
