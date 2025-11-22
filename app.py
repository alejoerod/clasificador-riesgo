import streamlit as st
import pandas as pd
import numpy as np
import pickle
from io import BytesIO

# ===============================================================
# CARGAR MODELO
# ===============================================================
@st.cache_resource
def cargar_modelo():
    modelo = pickle.load(open("modelo_gbt.pkl", "rb"))
    columnas = pickle.load(open("columnas_modelo.pkl", "rb"))
    return modelo, columnas

modelo, columnas_modelo = cargar_modelo()


# ===============================================================
# FUNCIÓN PARA EXPORTAR A EXCEL
# ===============================================================
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Resultados')
    return output.getvalue()


# ===============================================================
# INTERFAZ DE STREAMLIT
# ===============================================================
st.title("🔍 Clasificador de Riesgo – Intento de Suicidio")
st.write("Subí un archivo CSV con las nuevas respuestas para clasificarlas automáticamente.")

archivo = st.file_uploader("📂 Seleccionar archivo CSV", type=["csv"])

if archivo is not None:
    try:
        df_new = pd.read_csv(archivo, encoding="latin1")
        st.success("Archivo cargado correctamente.")

        st.subheader("Vista previa del archivo cargado")
        st.dataframe(df_new.head())

        # ------------------------------
        # Validar columnas predictoras
        # ------------------------------
        faltantes = [c for c in columnas_modelo if c not in df_new.columns]
        if faltantes:
            st.error("El archivo no contiene las columnas necesarias.")
            st.write("Faltan estas columnas:")
            st.write(faltantes)
            st.stop()

        # Dataset usado para el modelo
        df_used = df_new[columnas_modelo].copy()

        # Asegurar tipo numérico
        for col in columnas_modelo:
            df_used[col] = pd.to_numeric(df_used[col], errors="coerce")
            df_used[col] = df_used[col].fillna(df_used[col].median())

        # ------------------------------
        # Predicción
        # ------------------------------
        probs = modelo.predict_proba(df_used)[:, 1]
        umbral = 0.45

        df_result = df_new.copy()
        df_result["probabilidad"] = probs
        df_result["riesgo_predicho"] = (probs >= umbral).astype(int)

        st.subheader("📊 Resultados")
        st.dataframe(df_result.head())

        # Descargar Excel
        excel_bytes = exportar_excel(df_result)

        st.download_button(
            label="⬇ Descargar resultados en Excel",
            data=excel_bytes,
            file_name="resultado_clasificado.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    except Exception as e:
        st.error("Ocurrió un error procesando el archivo.")
        st.write(e)
