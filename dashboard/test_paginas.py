"""Prueba con AppTest: ejecuta las páginas sin navegador y comprueba que
no lanzan excepciones. Requiere la API arrancada"""

from streamlit.testing.v1 import AppTest

print("Probando home.py...")
app = AppTest.from_file("home.py").run(timeout=15)
assert not app.exception, f"home.py lanzó una excepción: {app.exception}"
assert len(app.dataframe) >= 1, "No se renderizó ninguna tabla de dispositivos"
tabla_html = app.dataframe[0].value.to_string()
assert "None" not in tabla_html, "Sigue apareciendo 'None' en crudo en la tabla de dispositivos"
print("OK -- home.py se ejecuta sin errores, pinta la tabla y no muestra 'None' en crudo.")

# Filtro por fabricante: seleccionar "Sony Corporation" debe reducir la tabla
total_filas_sin_filtro = len(app.dataframe[0].value)
app.multiselect[0].select("Sony Corporation").run(timeout=15)
assert not app.exception, f"Filtro por fabricante lanzó una excepción: {app.exception}"
filas_filtradas = len(app.dataframe[0].value)
assert filas_filtradas < total_filas_sin_filtro, (
    f"El filtro por fabricante no redujo la tabla ({filas_filtradas} vs {total_filas_sin_filtro})"
)
assert all(app.dataframe[0].value["Fabricante"] == "Sony Corporation")
print("OK -- el filtro por fabricante reduce la tabla correctamente.")

# Filtro por vulnerabilidad: "Solo vulnerables" debe dejar solo el Telink
app2 = AppTest.from_file("home.py").run(timeout=15)
total_sin_filtro = len(app2.dataframe[0].value)
app2.selectbox[0].select("Solo vulnerables").run(timeout=15)
assert not app2.exception, f"Filtro por vulnerabilidad lanzó una excepción: {app2.exception}"
filas_vulnerables = len(app2.dataframe[0].value)
assert filas_vulnerables < total_sin_filtro, (
    f"El filtro por vulnerabilidad no redujo la tabla ({filas_vulnerables} vs {total_sin_filtro})"
)
assert all(app2.dataframe[0].value["Vulnerabilidad"] == "🔴 Vulnerable")
print("OK -- el filtro por vulnerabilidad reduce la tabla correctamente.")


print("\nProbando pages/detalle_disp.py (navegacion real desde home.py)...")
# Ficha de detalle del dispositivo #9: vulnerabilidades conocidas por fabricante
app_detalle = AppTest.from_file("home.py")
app_detalle.session_state["dispositivo_id_seleccionado"] = 9
app_detalle.run(timeout=15)
app_detalle.switch_page("pages/detalle_disp.py")
app_detalle.run(timeout=15)
assert not app_detalle.exception, f"detalle_disp.py lanzó una excepción: {app_detalle.exception}"
assert len(app_detalle.dataframe) >= 1, "No se renderizó ninguna tabla en el detalle"
for tabla_df in app_detalle.dataframe:
    assert "None" not in tabla_df.value.to_string(), "Sigue apareciendo 'None' en crudo en el detalle"
texto_pagina_9 = " ".join(df.value.to_string() for df in app_detalle.dataframe)
assert "CVE-2019-19194" in texto_pagina_9, "No aparece el CVE esperado en la ficha de detalle"
print("OK -- detalle_disp.py (dispositivo #9) se ejecuta sin errores, pinta la ficha, las vulnerabilidades y no muestra 'None' en crudo.")

# Ficha de detalle del dispositivo #11: características GATT ya exploradas
app_gatt = AppTest.from_file("home.py")
app_gatt.session_state["dispositivo_id_seleccionado"] = 11
app_gatt.run(timeout=15)
app_gatt.switch_page("pages/detalle_disp.py")
app_gatt.run(timeout=15)
assert not app_gatt.exception, f"detalle_disp.py (dispositivo #11) lanzó una excepción: {app_gatt.exception}"
texto_pagina_11 = " ".join(df.value.to_string() for df in app_gatt.dataframe)
assert "write-without-response" in texto_pagina_11, "No aparece la propiedad de escritura esperada"
print("OK -- detalle_disp.py (dispositivo #11) muestra la propiedad de escritura esperada.")

avisos_11 = " ".join(w.value for w in app_gatt.warning) + " ".join(e.value for e in app_gatt.error)
assert "característica de escritura" in avisos_11, "No aparece el aviso de característica de escritura"
print("OK -- la sección de características GATT muestra el aviso de escritura correctamente.")

print("\nTodas las pruebas pasaron.")
