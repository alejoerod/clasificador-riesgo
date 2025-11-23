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
# EXPORTAR EXCEL
# ===============================================================
def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultados")
    return output.getvalue()

# ===============================================================
# APP
# ===============================================================
st.title("🔍 Sistema de Alarma Temprana – Clasificación de Riesgo")
st.write("Subí el archivo CSV exportado desde Google Sheets.")

archivo = st.file_uploader("📂 Cargar CSV", type=["csv"])

if archivo is not None:

    # -----------------------------------------------------------
    # 1) LECTURA DEL CSV (UTF-8 + tolerancia)
    # -----------------------------------------------------------
    try:
        df_new = pd.read_csv(archivo, encoding="utf-8", engine="python")
    except:
        df_new = pd.read_csv(archivo, encoding_errors="ignore")

    # NORMALIZAR COLUMNAS — FUNDAMENTAL PARA TU CSV
    df_new.columns = df_new.columns.str.strip()               # quitar espacios
    df_new.columns = df_new.columns.str.replace(r"\s+", " ", regex=True)  # doble espacio → uno
    df_new.columns = df_new.columns.str.rstrip()

    st.success("CSV cargado correctamente.")
    st.dataframe(df_new.head())

    # -----------------------------------------------------------
    # 2) MAPEO DE COLUMNAS (ROBUSTO, POR COINCIDENCIA PARCIAL)
    # -----------------------------------------------------------
    map_columnas = {
        "Cuantas veces fuiste atacado físicamente": "q15",
        "¿con qué frecuencia te sentiste solo": "q22",
        "¿con qué frecuencia estuviste tan preocupado": "q23",
        "¿Cuántos amigos o amigas muy cercanos": "q27",
        "cuando probaste un cigarrillo": "q28",
        "cuántos días usaste otra forma de tabaco": "q30",
        "primer trago de alcohol": "q34",
        "cuántas veces tuviste problemas con tu familia": "q39",
        "cuando usaste drogas por primera vez": "q40",
        "cuando tuviste relaciones sexuales por primera vez": "q45",
        "mayoría de los estudiantes fueron amables": "q54",
        "entendieron tus padres o cuidadores tus problemas": "q56",
        "realmente sabían lo que estabas haciendo": "q57",
        "intimidaron en la escuela": "q66",
        "intimidaron cuando no estabas en la escuela": "q67",
        "intimidaron por internet": "q68",
        "Con quién tomas alcohol habitualmente": "q74",
        "frecuencia tus padres o cuidadores te hicieron sentir ridículo": "q80"
    }

    columnas_originales = df_new.columns.tolist()

    for col in columnas_originales:
        normalizado = col.lower()
        for key, destino in map_columnas.items():
            if key.lower() in normalizado:
                df_new = df_new.rename(columns={col: destino})

    # -----------------------------------------------------------
    # 3) MAPEO DE RESPUESTAS
    # -----------------------------------------------------------

    # FRECUENCIA
    map_frec = {
        "Nunca": 1,
        "Rara vez": 2,
        "A veces": 3,
        "Algunas veces": 3,
        "Casi siempre": 4,
        "Con frecuencia": 4,
        "Frecuentemente": 4,
        "Siempre": 5
    }

    for col in ["q22", "q23", "q54", "q56", "q57", "q80"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(map_frec)

    # EDAD
    map_edad = {
        "Nunca": 1,
        "7 años o menos": 2,
        "8 o 9 años": 3,
        "10 o 11 años": 4,
        "12 o 13 años": 5,
        "14 o 15 años": 6,
        "16 o 17 años": 7,
        "18 años o más": 8
    }

    for col in ["q28", "q34", "q40", "q45"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(map_edad)

    # CANTIDADES / DÍAS
    map_q15 = {
        "Ninguna": 1,
        "1 vez": 2,
        "2 o 3 veces": 3,
        "4 o 5 veces": 4,
        "6 o 7 veces": 5,
        "8 o 9 veces": 6,
        "10 u 11 veces": 7,
        "12 o mas veces": 8
    }

    map_q27 = {
        "0": 1,
        "1": 2,
        "2": 3,
        "3 o más": 4
    }

    map_q39 = {
        "0 veces": 1,
        "1 o 2 veces": 2,
        "3 a 9 veces": 3,
        "10 o más veces": 4
    }

    map_q30 = {
        "0 días": 1,
        "1 o 2 días": 2,
        "3 a 5 días": 3,
        "6 a 9 días": 4,
        "10 a 19 días": 5,
        "20 a 29 días": 6,
        "Los 30 días": 7
    }

    for col, mapa in [("q15", map_q15), ("q27", map_q27), ("q39", map_q39), ("q30", map_q30)]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(mapa)

    # BULLYING — Sí/No
    map_bull = {"Si": 1, "Sí": 1, "No": 2}
    for col in ["q66", "q67", "q68"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(map_bull)

    # ALCOHOL
    map_q74 = {
        "No tomo alcohol": 1,
        "Con mis amigos": 2,
        "Con mi familia": 3,
        "Con gente que recién conocí": 4,
        "Usualmente tomo solo/a": 5
    }
    if "q74" in df_new.columns:
        df_new["q74"] = df_new["q74"].replace(map_q74)

    # -----------------------------------------------------------
    # 4) VALIDAR QUE TODAS LAS COLUMNAS EXISTAN
    # -----------------------------------------------------------
    faltantes = [c for c in columnas_modelo if c not in df_new.columns]
    if faltantes:
        st.error("Faltan columnas necesarias para el modelo:")
        st.write(faltantes)
        st.stop()

    # -----------------------------------------------------------
    # 5) PREPARAR DATASET PARA EL MODELO
    # -----------------------------------------------------------
    df_used = df_new[columnas_modelo].copy()

    for col in columnas_modelo:
        df_used[col] = pd.to_numeric(df_used[col], errors="coerce")

        if df_used[col].notna().sum() > 0:
            df_used[col] = df_used[col].fillna(df_used[col].median())
        else:
            df_used[col] = 1   # fallback seguro

    # -----------------------------------------------------------
    # 6) PREDICCIÓN
    # -----------------------------------------------------------
    probs = modelo.predict_proba(df_used)[:, 1]
    umbral = 0.45

    df_result = df_new.copy()
    df_result["probabilidad"] = probs
    df_result["riesgo_predicho"] = (probs >= umbral).astype(int)

    def etiqueta_riesgo(p):
        if p >= 0.75:
            return "🔴 Alto"
        elif p >= 0.45:
            return "🟠 Moderado"
        return "🟢 Bajo"

    df_result["riesgo_texto"] = df_result["probabilidad"].apply(etiqueta_riesgo)
    df_result = df_result.sort_values("probabilidad", ascending=False)

    # -----------------------------------------------------------
    # 7) MOSTRAR RESULTADOS
    # -----------------------------------------------------------
    st.subheader("📊 Estudiantes Identificados")
    columnas_id = [c for c in ["Nombre", "Apellido", "DNI", "nombre", "apellido", "dni"] if c in df_result.columns]
    columnas_id = list(dict.fromkeys(columnas_id))  # eliminar duplicados

    columnas_mostrar = columnas_id + ["probabilidad", "riesgo_predicho", "riesgo_texto"]

    st.dataframe(df_result[columnas_mostrar])

    # -----------------------------------------------------------
    # 8) DESCARGA
    # -----------------------------------------------------------
    excel_bytes = exportar_excel(df_result)

    st.download_button(
        label="⬇ Descargar informe completo (Excel)",
        data=excel_bytes,
        file_name="resultado_clasificado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )
