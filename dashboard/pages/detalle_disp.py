"""Ficha de detalle: datos del dispositivo, direcciones y últimas detecciones."""

from datetime import datetime

import pandas as pd
import requests
import streamlit as st

from api_client import explorar_caracteristicas, obtener_dispositivo
from utc_local import utc_naive_a_local

st.set_page_config(page_title="Detalle de dispositivo", layout="wide")

CLASIFICACION_ETIQUETA = {
    "persistente": "🟢 Persistente",
    "esporadico": "🟡 Esporádico",
}

dispositivo_id = st.session_state.get("dispositivo_id_seleccionado")

if dispositivo_id is None:
    st.warning("No se ha seleccionado ningún dispositivo todavía.")
    st.page_link("home.py", label="← Volver al listado")
    st.stop()

try:
    dispositivo = obtener_dispositivo(dispositivo_id)
except requests.exceptions.HTTPError:
    st.error(f"El dispositivo #{dispositivo_id} ya no existe.")
    st.page_link("home.py", label="← Volver al listado")
    st.stop()
except requests.exceptions.RequestException:
    st.error(
        "No se pudo conectar con la API. Comprueba que está arrancada "
        "(`uvicorn api.main:app --reload`)."
    )
    st.stop()

st.page_link("home.py", label="← Volver al listado")

st.title(f"Dispositivo #{dispositivo['id']}")
st.caption(dispositivo["nombre"] or "Sin nombre anunciado")

columna_1, columna_2, columna_3, columna_4 = st.columns(4)
columna_1.metric("Fabricante", dispositivo["fabricante"] or "Desconocido")
columna_2.metric("Nº detecciones", dispositivo["num_detecciones"])
columna_3.metric(
    "Clasificación",
    CLASIFICACION_ETIQUETA.get(dispositivo["clasificacion"], dispositivo["clasificacion"]),
)
primera_local = utc_naive_a_local(datetime.fromisoformat(dispositivo["primera_deteccion"]))
columna_4.metric("Primera detección", primera_local.strftime("%Y-%m-%d"))

st.subheader("Vulnerabilidades conocidas")
SEVERIDAD_ETIQUETA = {"Critica": "🔴 Crítica", "Media": "🟠 Media"}
vulnerabilidades = dispositivo.get("vulnerabilidades") or []
if vulnerabilidades:
    st.warning(
        f"El fabricante de este dispositivo tiene {len(vulnerabilidades)} "
        "vulnerabilidad(es) conocida(s) en nuestra base curada."
    )
    tabla_vuln = pd.DataFrame(vulnerabilidades)
    tabla_vuln["severidad"] = tabla_vuln["severidad"].map(SEVERIDAD_ETIQUETA).fillna(
        tabla_vuln["severidad"]
    )
    st.dataframe(
        tabla_vuln.rename(
            columns={
                "cve_id": "CVE",
                "nombre_vulnerabilidad": "Nombre",
                "descripcion": "Descripción",
                "severidad": "Severidad",
                "fuente_url": "Fuente",
            }
        ),
        width="stretch",
        hide_index=True,
        column_config={"Fuente": st.column_config.LinkColumn()},
    )
else:
    st.caption(
        "Sin vulnerabilidades conocidas para este fabricante en nuestra base "
        "curada (no implica que el dispositivo esté libre de otras)."
    )

st.subheader("Direcciones observadas")
st.caption(
    "Un dispositivo puede tener varias direcciones si BLE le asignó una "
    "aleatoria que rotó con el tiempo."
)
direcciones = pd.DataFrame(dispositivo["direcciones"])
direcciones["tipo_direccion"] = direcciones["tipo_direccion"].fillna("—")
direcciones["primera_vez_vista"] = pd.to_datetime(
    direcciones["primera_vez_vista"], format="ISO8601"
).apply(utc_naive_a_local)
direcciones["ultima_vez_vista"] = pd.to_datetime(
    direcciones["ultima_vez_vista"], format="ISO8601"
).apply(utc_naive_a_local)
st.dataframe(
    direcciones.rename(
        columns={
            "direccion": "Dirección",
            "tipo_direccion": "Tipo",
            "primera_vez_vista": "Primera vez vista",
            "ultima_vez_vista": "Última vez vista",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.subheader("Últimas detecciones")
detecciones = pd.DataFrame(dispositivo["ultimas_detecciones"])
if not detecciones.empty:
    detecciones["nombre_anunciado"] = detecciones["nombre_anunciado"].fillna("—")
    detecciones["fecha_hora"] = pd.to_datetime(
        detecciones["fecha_hora"], format="ISO8601"
    ).apply(utc_naive_a_local)

    if len(detecciones) > 1:
        st.line_chart(
            detecciones.set_index("fecha_hora")["rssi"], width="stretch"
        )

    st.dataframe(
        detecciones.rename(
            columns={
                "fecha_hora": "Fecha y hora",
                "rssi": "RSSI",
                "nombre_anunciado": "Nombre anunciado",
            }
        ),
        width="stretch",
        hide_index=True,
    )
else:
    st.info("Sin detecciones registradas todavía.")

st.divider()
st.subheader("Características GATT (conexión activa)")
st.warning(
    "⚠️ A diferencia del resto del sistema, esta acción establece una "
    "**conexión BLE real** con el dispositivo (no es escaneo pasivo). "
)

if st.button("🔌 Explorar características ahora"):
    with st.spinner("Conectando por BLE y enumerando características…"):
        try:
            explorar_caracteristicas(dispositivo_id)
            st.rerun()
        except requests.exceptions.HTTPError as error:
            if error.response is not None and error.response.status_code == 502:
                detalle = error.response.json().get("detail", "")
                st.error(
                    f"No se pudo conectar con el dispositivo: {detalle}. "
                    "Asegúrate de que está encendido y en rango."
                )
            else:
                st.error(f"La API devolvió un error inesperado: {error}")
        except requests.exceptions.RequestException:
            st.error("No se pudo conectar con la API.")

caracteristicas = dispositivo.get("caracteristicas") or []
if caracteristicas:
    if dispositivo.get("tiene_escritura"):
        st.error(
            "🔴 Este dispositivo tiene al menos una característica de "
            "escritura (write o write-without-response) — posible "
            "superficie de ataque tipo replay si no va cifrada."
        )
    else:
        st.caption("Ninguna característica de escritura detectada.")

    tabla_carac = pd.DataFrame(caracteristicas)
    tabla_carac["servicio_nombre"] = tabla_carac["servicio_nombre"].fillna("—")
    tabla_carac["caracteristica_nombre"] = tabla_carac["caracteristica_nombre"].fillna("—")
    tabla_carac["propiedades"] = tabla_carac["propiedades"].apply(", ".join)
    st.dataframe(
        tabla_carac.rename(
            columns={
                "servicio_uuid": "UUID servicio",
                "servicio_nombre": "Servicio",
                "caracteristica_uuid": "UUID característica",
                "caracteristica_nombre": "Característica",
                "handle": "Handle",
                "propiedades": "Propiedades",
            }
        ),
        width="stretch",
        hide_index=True,
    )
else:
    st.caption("Todavía no se ha explorado este dispositivo.")
