# Sistema de Inventario de Dispositivos BLE

Anexo técnico del Trabajo Fin de Máster — Máster en Ciberseguridad.

Sistema de **descubrimiento pasivo** de dispositivos Bluetooth Low Energy (BLE): detecta dispositivos cercanos a partir de sus paquetes de Advertising, sin emparejarse ni conectarse a ellos, y construye un inventario con histórico de detecciones, clasificación automática de presencia y comprobación de vulnerabilidades conocidas por fabricante.

## Alcance

El escaneo continuo es **exclusivamente pasivo**: solo se lee lo que cada dispositivo anuncia públicamente. La única excepción es la herramienta de **exploración de características GATT**, que sí establece una conexión BLE real, activada manualmente dispositivo a dispositivo, y restringida a dispositivos propios del autor.

## Arquitectura

```
Dispositivos BLE → Agente (Python + Bleak) → API REST (FastAPI) → Base de datos (SQLite)
                                                                        ↓
                                                          Dashboard (Streamlit)
```

| Componente | Responsabilidad |
|---|---|
| **Agente** (`agente/`) | Escaneo periódico y envío de detecciones a la API |
| **API** (`api/`) | Resolución de identidad, fabricante, clasificación y vulnerabilidades |
| **Base de datos** (`db/`) | Persistencia (SQLite vía SQLAlchemy) |
| **Dashboard** (`dashboard/`) | Consulta visual del inventario, sin conocimientos técnicos |

**Tecnologías**: `Python 3.12` · `bleak` · `FastAPI` · `SQLAlchemy` + `SQLite` · `Streamlit`

## Instalación y puesta en marcha
Primero descarga toda la rama, para que no falte ningún archivo, si no el programa no arrancará

```bash
python -m venv venv
venv\Scripts\Activate.ps1          # Windows
source venv/bin/activate            # Linux / macOS

pip install -r requirements.txt
python init_db.py                    # solo la primera vez
```

Los tres procesos se ejecutan en terminales separadas. En el desarrollo de este proyecto se siguió este orden: la API arrancada en segundo plano, el agente escaneando y guardando detecciones a través de ella, y el dashboard abierto después para consultar los resultados acumulados. Para la puesta en marcha es muy importante tener el Bluetooth de nuestro dispositivo activado

```bash
uvicorn api.main:app --reload                   # 1. arrancar la API, docs en /docs
cd agente && python scanner_ble.py               # 2. arrancar el escaneo, Ctrl+C para detener
cd dashboard && streamlit run home.py             # 3. consultar los resultados en el dashboard
```

## Funcionalidades

- **Inventario** con filtro por rango horario y por fabricante.
- **Clasificación automática**: persistente (2+ días distintos) o esporádico.
- **Vulnerabilidades conocidas**: aviso automático por fabricante (dataset SweynTooth) y filtro "solo vulnerables".
- **Actividad**: línea de tiempo de presencia y dispositivos nuevos por día.
- **Exploración GATT** (acción activa, solo dispositivos propios): enumera servicios, características y sus propiedades, con aviso si hay superficie de escritura.

## Modelo de datos (resumen)

Las direcciones BLE rotan y no son un identificador estable, así que la identidad se separa en dos capas:

- `dispositivos` — entidad lógica del inventario
- `direcciones_dispositivo` — direcciones observadas, vinculadas a un dispositivo
- `detecciones` — registro crudo e inmutable de cada lectura
- `vulnerabilidades_fabricante` — CVEs conocidas, indexadas por Company Identifier
- `caracteristicas_dispositivo` — resultado de la última exploración GATT de un dispositivo

## Pruebas automatizadas

**19/19 casos superados**: 12 en la API (`pytest`), 1 de integración en el agente, 6 en el dashboard (`AppTest` de Streamlit, sin navegador).

```bash
python -m pytest api/test_api.py -v
cd agente && python test_Prueba.py
cd dashboard && python test_paginas.py    # con la API arrancada
```

## Limitaciones y trabajo futuro

- La resolución de identidad usa coincidencia exacta de dirección BLE; no reidentifica dispositivos que rotan de dirección sin otro dato persistente. Línea futura: fingerprinting a partir del payload de Advertising.
- Vulnerabilidades limitadas al dataset de SweynTooth; ampliable a otras fuentes.
- Volumen de datos validado en entorno doméstico; el escalado a miles de dispositivos de un entorno corporativo queda pendiente de validación.
