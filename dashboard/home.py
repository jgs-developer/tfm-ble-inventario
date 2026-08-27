"""Página principal: listado de dispositivos con filtro por rango horario."""

from datetime import datetime, time

import altair as alt
import pandas as pd
import requests
import streamlit as st

from api_client import obtener_dispositivos
from utc_local import local_a_utc_naive, utc_naive_a_local

st.set_page_config(page_title="TFM - Inventario BLE", layout="wide")

st.title("Inventario de dispositivos BLE")
st.caption("Descubrimiento pasivo por Advertising -- sin conexion ni emparejamiento.")

CLASIFICACION_ETIQUETA = {
    "persistente": "🟢 Persistente",
    "esporadico": "🟡 Esporádico",
}

st.subheader("Filtro por rango horario")
usar_filtro = st.checkbox(
    "Filtrar por rango horario de detección",
    help="El escaneo es iterativo: se acumulan sesiones a lo largo del tiempo. "
    "Sin filtro se muestran todos los dispositivos detectados hasta ahora.",
)

desde = hasta = None
if usar_filtro:
    columna_desde, columna_hasta = st.columns(2)
    with columna_desde:
        fecha_desde = st.date_input("Desde", value=datetime.now().date())
    with columna_hasta:
        fecha_hasta = st.date_input("Hasta", value=datetime.now().date())
    # El selector de fechas es en hora local; la API espera y guarda en UTC.
    desde = local_a_utc_naive(datetime.combine(fecha_desde, time.min))
    hasta = local_a_utc_naive(datetime.combine(fecha_hasta, time.max))

try:
    dispositivos = obtener_dispositivos(desde=desde, hasta=hasta)
except requests.exceptions.RequestException:
    st.error(
        "No se pudo conectar con la API. Comprueba que está arrancada "
        "(`uvicorn api.main:app --reload`)."
    )
    st.stop()

if not dispositivos:
    st.info("No hay dispositivos que coincidan con el filtro seleccionado.")
    st.stop()

st.subheader("Filtro por fabricante")
fabricantes_disponibles = sorted(
    {d["fabricante"] or "Desconocido" for d in dispositivos}
)
fabricantes_elegidos = st.multiselect(
    "Filtrar por fabricante",
    options=fabricantes_disponibles,
    placeholder="Todos los fabricantes",
    help="Sin selección se muestran todos los fabricantes.",
)
if fabricantes_elegidos:
    dispositivos = [
        d for d in dispositivos
        if (d["fabricante"] or "Desconocido") in fabricantes_elegidos
    ]

if not dispositivos:
    st.info("Ningún dispositivo coincide con los fabricantes seleccionados.")
    st.stop()

st.subheader("Filtro por vulnerabilidad conocida")
opcion_vulnerabilidad = st.selectbox(
    "Filtrar por vulnerabilidad",
    options=["Todos", "Solo vulnerables", "Solo no vulnerables"],
    help="Vulnerable = el fabricante del dispositivo tiene CVEs conocidos en nuestra base curada.",
)
if opcion_vulnerabilidad == "Solo vulnerables":
    dispositivos = [d for d in dispositivos if d.get("es_vulnerable")]
elif opcion_vulnerabilidad == "Solo no vulnerables":
    dispositivos = [d for d in dispositivos if not d.get("es_vulnerable")]

if not dispositivos:
    st.info("Ningún dispositivo coincide con el filtro de vulnerabilidad seleccionado.")
    st.stop()

st.caption(f"{len(dispositivos)} dispositivo(s) encontrado(s).")

tabla = pd.DataFrame(dispositivos)
tabla["nombre"] = tabla["nombre"].fillna("—")
tabla["fabricante"] = tabla["fabricante"].fillna("—")
tabla["clasificacion"] = tabla["clasificacion"].map(CLASIFICACION_ETIQUETA)
tabla["es_vulnerable"] = tabla["es_vulnerable"].map(
    {True: "🔴 Vulnerable", False: "—"}
)
tabla["primera_deteccion"] = pd.to_datetime(
    tabla["primera_deteccion"], format="ISO8601"
).apply(utc_naive_a_local)
tabla["ultima_deteccion"] = pd.to_datetime(
    tabla["ultima_deteccion"], format="ISO8601"
).apply(utc_naive_a_local)

st.dataframe(
    tabla.rename(
        columns={
            "id": "ID",
            "nombre": "Nombre",
            "fabricante": "Fabricante",
            "primera_deteccion": "Primera detección",
            "ultima_deteccion": "Última detección",
            "num_detecciones": "Nº detecciones",
            "clasificacion": "Clasificación",
            "es_vulnerable": "Vulnerabilidad",
        }
    ),
    width="stretch",
    hide_index=True,
)

st.subheader("Actividad de los dispositivos")

datos_grafico = tabla.copy()
datos_grafico["etiqueta"] = (
    "#" + datos_grafico["id"].astype(str) + " · " + datos_grafico["fabricante"]
)

rango_total = (
    datos_grafico["ultima_deteccion"].max() - datos_grafico["primera_deteccion"].min()
)
duracion_minima = max(rango_total * 0.006, pd.Timedelta(minutes=5))
datos_grafico["fin_visual"] = datos_grafico["ultima_deteccion"]
demasiado_corta = (
    datos_grafico["fin_visual"] - datos_grafico["primera_deteccion"]
) < duracion_minima
datos_grafico.loc[demasiado_corta, "fin_visual"] = (
    datos_grafico.loc[demasiado_corta, "primera_deteccion"] + duracion_minima
)

linea_tiempo = (
    alt.Chart(datos_grafico)
    .mark_bar(height=14, cornerRadius=3, stroke="#F7F6F3", strokeWidth=0.5)
    .encode(
        x=alt.X(
            "primera_deteccion:T",
            title="Fecha",
            axis=alt.Axis(format="%d %b", tickCount=10, labelAngle=0),
        ),
        x2="fin_visual:T",
        y=alt.Y(
            "etiqueta:N",
            sort=alt.EncodingSortField(field="primera_deteccion", order="ascending"),
            title=None,
        ),
        color=alt.Color(
            "clasificacion:N",
            title="Clasificación",
            scale=alt.Scale(
                domain=["🟢 Persistente", "🟡 Esporádico"],
                range=["#16A34A", "#D97706"],
            ),
        ),
        tooltip=[
            alt.Tooltip("etiqueta:N", title="Dispositivo"),
            alt.Tooltip("primera_deteccion:T", title="Primera detección"),
            alt.Tooltip("ultima_deteccion:T", title="Última detección"),
            alt.Tooltip("num_detecciones:Q", title="Nº detecciones"),
        ],
    )
    .properties(
        height=alt.Step(24),
        title="Línea de tiempo de presencia",
        background="transparent",
    )
    .configure_view(strokeWidth=0)
    .configure_axis(
        gridColor="#E5E3DD",
        domainColor="#D8D6CF",
        labelColor="#6B7280",
        titleColor="#374151",
    )
    .configure_title(fontSize=15, fontWeight=500, color="#1F2937", anchor="start", offset=8)
    .configure_legend(labelColor="#374151", titleColor="#1F2937")
)
st.altair_chart(linea_tiempo, width="stretch")

por_dia = (
    datos_grafico.groupby(datos_grafico["primera_deteccion"].dt.date)
    .size()
    .reset_index(name="Nº dispositivos")
    .rename(columns={"primera_deteccion": "Fecha"})
)

grafico_por_dia = (
    alt.Chart(por_dia)
    .mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4, color="#2563EB")
    .encode(
        x=alt.X("Fecha:T", title=None),
        y=alt.Y("Nº dispositivos:Q", title="Nº dispositivos"),
        tooltip=["Fecha:T", "Nº dispositivos:Q"],
    )
    .properties(title="Dispositivos nuevos por día", height=220, background="transparent")
    .configure_view(strokeWidth=0)
    .configure_axis(
        gridColor="#E5E3DD",
        domainColor="#D8D6CF",
        labelColor="#6B7280",
        titleColor="#374151",
    )
    .configure_title(fontSize=15, fontWeight=500, color="#1F2937", anchor="start", offset=8)
)
st.altair_chart(grafico_por_dia, width="stretch")

st.subheader("Ver ficha de un dispositivo")
opciones = {
    f"#{d['id']} · {d['fabricante'] or 'Fabricante desconocido'} "
    f"({d['num_detecciones']} detecciones)": d["id"]
    for d in dispositivos
}
seleccion = st.selectbox("Selecciona un dispositivo", options=list(opciones.keys()))

if st.button("Ver ficha completa →"):
    st.session_state["dispositivo_id_seleccionado"] = opciones[seleccion]
    st.switch_page("pages/detalle_disp.py")
