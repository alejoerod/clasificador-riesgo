import streamlit as st
import pandas as pd
import numpy as np
import pickle
import unicodedata
from io import BytesIO


# =========================
# FUNCIONES AUXILIARES
# =========================

def normalizar_texto(valor):
    if pd.isna(valor):
        return valor
    valor = str(valor).strip()
    valor = " ".join(valor.split())  # elimina espacios duplicados
    valor = valor.lower()
    valor = unicodedata.normalize("NFKD", valor).encode("ascii", "ignore").decode("utf-8")
    return valor


def exportar_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Resultados")
    return output.getvalue()


@st.cache_resource
def cargar_modelo():
    modelo = pickle.load(open("modelo_gbt.pkl", "rb"))
    columnas = pickle.load(open("columnas_modelo.pkl", "rb"))
    return modelo, columnas


# =========================
# CARGA DEL MODELO
# =========================

modelo, columnas_modelo = cargar_modelo()


# =========================
# APLICACION WEB
# =========================

st.title("🔍 Sistema de Alarma Temprana – Clasificación de Riesgo")
st.write("Subí el archivo CSV exportado desde Google Sheets.")

archivo = st.file_uploader("📂 Cargar CSV", type=["csv"])

if archivo is not None:

    # =========================
    # 1) LECTURA DEL CSV
    # =========================
    try:
        df_new = pd.read_csv(archivo, encoding="utf-8", engine="python")
    except:
        df_new = pd.read_csv(archivo, encoding_errors="ignore")

    # Normalización de nombres de columnas
    df_new.columns = df_new.columns.str.strip()
    df_new.columns = df_new.columns.str.replace(r"\s+", " ", regex=True)
    df_new.columns = df_new.columns.str.rstrip()

    st.success("CSV cargado correctamente.")
    st.dataframe(df_new.head())

    # Guardamos una copia original para poder mostrar valores reales si hay errores
    df_original = df_new.copy()

    # Normalizar valores de texto en todo el dataframe
    for col in df_new.columns:
        if df_new[col].dtype == "object":
            df_new[col] = df_new[col].apply(normalizar_texto)

    # =========================
    # 2) MAPEO DE COLUMNAS
    # =========================
    map_columnas = {
        "cuantas veces fuiste atacado fisicamente": "q15",
        "con que frecuencia te sentiste solo": "q22",
        "con que frecuencia estuviste tan preocupado": "q23",
        "cuantos amigos o amigas muy cercanos": "q27",
        "cuando probaste un cigarrillo": "q28",
        "cuantos dias usaste otra forma de tabaco": "q30",
        "primer trago de alcohol": "q34",
        "cuantas veces tuviste problemas con tu familia": "q39",
        "cuando usaste drogas por primera vez": "q40",
        "cuando tuviste relaciones sexuales por primera vez": "q45",
        "mayoria de los estudiantes fueron amables": "q54",
        "entendieron tus padres o cuidadores tus problemas": "q56",
        "realmente sabian lo que estabas haciendo": "q57",
        "intimidaron en la escuela": "q66",
        "intimidaron cuando no estabas en la escuela": "q67",
        "intimidaron por internet": "q68",
        "con quien tomas alcohol habitualmente": "q74",
        "frecuencia tus padres o cuidadores te hicieron sentir ridiculo": "q80"
    }

    columnas_originales = df_new.columns.tolist()

    renombres = {}
    for col in columnas_originales:
        col_normalizada = normalizar_texto(col)
        for key, destino in map_columnas.items():
            if key in col_normalizada:
                renombres[col] = destino
                break

    df_new = df_new.rename(columns=renombres)
    df_original = df_original.rename(columns=renombres)

    # =========================
    # 3) MAPEO DE RESPUESTAS
    # =========================

    # Frecuencias
    map_frec = {
        "nunca": 1,
        "rara vez": 2,
        "a veces": 3,
        "algunas veces": 3,
        "casi siempre": 4,
        "con frecuencia": 4,
        "frecuentemente": 4,
        "siempre": 5
    }

    for col in ["q22", "q23", "q54", "q56", "q57", "q80"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(map_frec)

    # Edades
    map_edad = {
        "nunca": 1,
        "7 anos o menos": 2,
        "8 o 9 anos": 3,
        "10 u 11 anos": 4,
        "12 o 13 anos": 5,
        "14 o 15 anos": 6,
        "16 o 17 anos": 7,
        "18 anos o mas": 8
    }

    for col in ["q28", "q34", "q40", "q45"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(map_edad)

    # Cantidades / días
    map_q15 = {
        "ninguna": 1,
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
        "3 o mas": 4
    }

    map_q39 = {
        "0 veces": 1,
        "1 o 2 veces": 2,
        "3 a 9 veces": 3,
        "10 o mas veces": 4
    }

    map_q30 = {
        "0 dias": 1,
        "1 o 2 dias": 2,
        "3 a 5 dias": 3,
        "6 a 9 dias": 4,
        "10 a 19 dias": 5,
        "20 a 29 dias": 6,
        "los 30 dias": 7
    }

    for col, mapa in [("q15", map_q15), ("q27", map_q27), ("q39", map_q39), ("q30", map_q30)]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(mapa)

    # Sí / No
    map_bull = {
        "si": 1,
        "no": 2
    }

    for col in ["q66", "q67", "q68"]:
        if col in df_new.columns:
            df_new[col] = df_new[col].replace(map_bull)

    # Consumo de alcohol
    map_q74 = {
        "no tomo alcohol": 1,
        "con mis amigos": 2,
        "con mi familia": 3,
        "con gente que recien conoci": 4,
        "usualmente tomo solo/a": 5,
        "usualmente tomo solo": 5,
        "usualmente tomo sola": 5
    }

    if "q74" in df_new.columns:
        df_new["q74"] = df_new["q74"].replace(map_q74)

    # =========================
    # 4) VALIDAR COLUMNAS NECESARIAS
    # =========================
    faltantes = [c for c in columnas_modelo if c not in df_new.columns]

    if faltantes:
        st.error("Faltan columnas necesarias para el modelo:")
        st.write(faltantes)
        st.subheader("Columnas detectadas en el archivo")
        st.write(df_new.columns.tolist())
        st.stop()

    # =========================
    # 5) PREPARACION DEL DATASET
    # =========================
    df_used = df_new[columnas_modelo].copy()

    # Detectar problemas de conversión antes de predecir
    errores_mapeo = []

    for col in columnas_modelo:
        serie_original_mapeada = df_used[col].copy()
        serie_numerica = pd.to_numeric(serie_original_mapeada, errors="coerce")

        mask_error = serie_numerica.isna() & serie_original_mapeada.notna()

        if mask_error.any():
            for idx in df_used.index[mask_error]:
                valor_original_archivo = df_original.loc[idx, col] if col in df_original.columns else None
                valor_luego_mapeo = df_new.loc[idx, col]

                errores_mapeo.append({
                    "fila": int(idx),
                    "columna": col,
                    "valor_original_csv": valor_original_archivo,
                    "valor_luego_del_mapeo": valor_luego_mapeo
                })

        df_used[col] = serie_numerica

    # Detectar nulos reales (vacíos en el archivo)
    nulos_reales = []

    for col in columnas_modelo:
        mask_nulo = df_used[col].isna()

        if mask_nulo.any():
            for idx in df_used.index[mask_nulo]:
                valor_original_archivo = df_original.loc[idx, col] if col in df_original.columns else None
                valor_luego_mapeo = df_new.loc[idx, col]

                nulos_reales.append({
                    "fila": int(idx),
                    "columna": col,
                    "valor_original_csv": valor_original_archivo,
                    "valor_luego_del_mapeo": valor_luego_mapeo
                })

    if errores_mapeo:
        st.error("Se encontraron valores que no pudieron convertirse a número luego del mapeo.")
        st.write("Esto indica que hay respuestas en el CSV que no coinciden exactamente con los diccionarios de mapeo.")
        st.dataframe(pd.DataFrame(errores_mapeo))
        st.stop()

    if nulos_reales:
        st.error("Se encontraron valores nulos en columnas requeridas por el modelo.")
        st.write("Revisá si en el CSV hay respuestas vacías en esas preguntas.")
        st.dataframe(pd.DataFrame(nulos_reales))
        st.stop()

    # =========================
    # 6) PREDICCION
    # =========================
    probs = modelo.predict_proba(df_used)[:, 1]
    umbral = 0.45

    df_result = df_original.copy()
    df_result["probabilidad"] = probs
    df_result["riesgo_predicho"] = (probs >= umbral).astype(int)

    def etiqueta_riesgo(p):
        if p >= 0.8:
            return "Alto"
        elif p >= 0.45:
            return "Moderado"
        return "Bajo"

    df_result["riesgo_descripcion"] = df_result["probabilidad"].apply(etiqueta_riesgo)
    df_result = df_result.sort_values("probabilidad", ascending=False)

    # Mostrar porcentaje
    df_result["probabilidad"] = (df_result["probabilidad"] * 100).round(2).astype(str) + "%"

    # =========================
    # 7) RESULTADOS
    # =========================
    st.subheader("📊 Estudiantes Identificados")

    columnas_id = [c for c in ["Nombre", "Apellido", "DNI", "nombre", "apellido", "dni"] if c in df_result.columns]
    columnas_id = list(dict.fromkeys(columnas_id))

    columnas_mostrar = columnas_id + ["probabilidad", "riesgo_predicho", "riesgo_descripcion"]

    st.dataframe(df_result[columnas_mostrar])

    # =========================
    # 8) GRAFICO DE BARRAS
    # =========================
    st.subheader("📊 Distribución de Alumnos por Nivel de Riesgo")

    import matplotlib.pyplot as plt
    from matplotlib.ticker import MaxNLocator

    conteo_riesgo = df_result["riesgo_descripcion"].value_counts()

    niveles = ["Bajo", "Moderado", "Alto"]
    valores = [conteo_riesgo.get(nivel, 0) for nivel in niveles]

    fig, ax = plt.subplots(figsize=(4, 2.5))

    colores = ["#2ca02c", "#ff7f0e", "#d62728"]
    barras = ax.bar(niveles, valores, color=colores, width=0.5)

    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))

    ax.set_ylabel("Cantidad")
    ax.set_xlabel("")
    ax.set_title("Distribución por Nivel de Riesgo", fontsize=10)

    for barra in barras:
        altura = barra.get_height()
        ax.text(
            barra.get_x() + barra.get_width() / 2,
            altura,
            f"{int(altura)}",
            ha="center",
            va="bottom",
            fontsize=8
        )

    plt.tight_layout()

    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.pyplot(fig)

    # =========================
    # 9) DESCARGA DE EXCEL
    # =========================
    excel_bytes = exportar_excel(df_result)

    st.download_button(
        label="⬇ Descargar informe completo (Excel)",
        data=excel_bytes,
        file_name="resultado_clasificado.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )