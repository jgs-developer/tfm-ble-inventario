"""Resuelve el fabricante a partir del Company Identifier de manufacturer_data (tabla de bleak)."""

from bleak.backends._manufacturers import MANUFACTURERS


def resolver_fabricante(manufacturer_data: dict[str, str] | None) -> tuple[str | None, int | None]:
    if not manufacturer_data:
        return None, None

    primera_clave = next(iter(manufacturer_data))
    try:
        company_id = int(primera_clave)
    except ValueError:
        return None, None

    return MANUFACTURERS.get(company_id), company_id
