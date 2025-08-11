# app_lector_excel.py
import streamlit as st
import pandas as pd
import io
import re
import unicodedata
from datetime import datetime

st.set_page_config(page_title="Lector de Excel – Plan Policial", layout="wide")

st.title("📘 Lector de Excel")
st.write("Sube tu archivo Excel y ajusta la hoja/encabezado para visualizar, limpiar y exportar datos.")

# ---------------- utilidades ----------------
def limpiar_nombre_columna(s: str) -> str:
    if not isinstance(s, str): s = str(s)
    s = s.strip().lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
    s = re.sub(r"[^a-z0-9_ ]+", "", s)
    s = re.sub(r"\s+", "_", s)
    return s

def normalizar_nombres_columnas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df.columns = [limpiar_nombre_columna(c) for c in df.columns]
    return df

def detectar_header_row(df_preview: pd.DataFrame, max_check_rows=6) -> int:
    """
    Heurística simple: busca la fila (0..max_check_rows-1) con más valores de texto no vacíos,
    asumiendo que es la mejor candidata a cabecera.
    """
    best_row = 0
    best_score = -1
    filas = min(max_check_rows, len(df_preview))
    for r in range(filas):
        row = df_preview.iloc[r]
        score = sum(1 for x in row if pd.notna(x) and str(x).strip() not in ("", "nan"))
        if score > best_score:
            best_score = score
            best_row = r
    return best_row

def intentar_parsear_fechas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        # Intenta parsear como fecha si parece tener fechas
        if df[col].dtype == object:
            try:
                parsed = pd.to_datetime(df[col], errors="ignore", dayfirst=True, infer_datetime_format=True)
                # Solo reemplaza si hay al menos una fecha reconocida
                if getattr(parsed, "dt", None) is not None and parsed.dt.notna().sum() > 0:
                    df[col] = parsed
            except Exception:
                pass
    return df

def df_to_excel_bytes(df: pd.DataFrame, sheet_name="Datos"):
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as w:
        df.to_excel(w, index=False, sheet_name=sheet_name)
    buf.seek(0)
    return buf.getvalue()

# ---------------- UI: carga ----------------
files = st.file_uploader("📁 Sube archivos .xlsx / .xlsm", type=["xlsx", "xlsm"], accept_multiple_files=True)

if not files:
    st.info("Sube al menos un archivo para comenzar.")
    st.stop()

st.sidebar.header("⚙️ Opciones de lectura")
unir_archivos = st.sidebar.checkbox("Unir todos los archivos/hojas en una sola tabla", value=False)
limpiar_columnas = st.sidebar.checkbox("Normalizar nombres de columnas", value=True)
parsear_fechas = st.sidebar.checkbox("Detectar y parsear fechas", value=True)
eliminar_columnas_vacias = st.sidebar.checkbox("Eliminar columnas totalmente vacías", value=True)

dataframes = []

for idx, f in enumerate(files, start=1):
    st.markdown(f"### 📄 Archivo {idx}: `{f.name}`")
    try:
        xls = pd.ExcelFile(f)
        sheet = st.selectbox("Selecciona la hoja", xls.sheet_names, key=f"sheet_{f.name}")
        # Vista previa “tal cual” para ayudar a decidir header/skiprows
        df_preview_raw = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=12)
        with st.expander("👀 Vista previa cruda (primeras filas, sin encabezado)"):
            st.dataframe(df_preview_raw, use_container_width=True, height=280)

        sugerida = detectar_header_row(df_preview_raw)
        use_header = st.number_input("Fila de encabezado (0=primera fila)", min_value=0, max_value=50, value=int(sugerida), step=1, key=f"hdr_{f.name}")
        skiprows = st.number_input("Filas a omitir antes del encabezado", min_value=0, max_value=200, value=0, step=1, key=f"skip_{f.name}")

        # Lee con parámetros del usuario
        df = pd.read_excel(xls, sheet_name=sheet, header=use_header, skiprows=skiprows)
        # A veces header + skiprows pueden solaparse; si quedaron columnas Unnamed, intenta repararlas
        if any(str(c).startswith("Unnamed") for c in df.columns):
            # Reintento: sin skiprows, solo header sugerida
            try:
                df_alt = pd.read_excel(xls, sheet_name=sheet, header=use_header)
                if df_alt.shape[1] >= df.shape[1]:
                    df = df_alt
            except Exception:
                pass

        if eliminar_columnas_vacias:
            df = df.dropna(axis=1, how="all")

        if limpiar_columnas:
            df = normalizar_nombres_columnas(df)

        if parsear_fechas:
            df = intentar_parsear_fechas(df)

        # Columnas seleccionables
        with st.expander("🧩 Seleccionar columnas a mantener"):
            cols = st.multiselect("Columnas", list(df.columns), default=list(df.columns), key=f"cols_{f.name}")
            if cols:
                df = df[cols]

        st.success(f"✅ {df.shape[0]} filas × {df.shape[1]} columnas")
        st.dataframe(df, use_container_width=True, height=360)

        # Descargas individuales
        c1, c2 = st.columns(2)
        csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
        with c1:
            st.download_button("⬇️ Descargar CSV", data=csv_bytes, file_name=f"{f.name.rsplit('.',1)[0]}_{sheet}.csv", mime="text/csv")
        with c2:
            st.download_button("⬇️ Descargar Excel", data=df_to_excel_bytes(df), file_name=f"{f.name.rsplit('.',1)[0]}_{sheet}.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        dataframes.append(df)

    except Exception as e:
        st.error(f"❌ Error al leer '{f.name}': {e}")

# ---------------- Unificación opcional ----------------
if unir_archivos and dataframes:
    st.markdown("---")
    st.header("🧮 Tabla unificada")
    try:
        # Unifica columnas por nombre; rellena faltantes
        df_union = pd.concat(dataframes, ignore_index=True, sort=False)
        if eliminar_columnas_vacias:
            df_union = df_union.dropna(axis=1, how="all")
        st.success(f"🔗 Unificado: {df_union.shape[0]} filas × {df_union.shape[1]} columnas")
        st.dataframe(df_union, use_container_width=True, height=420)

        c1, c2 = st.columns(2)
        with c1:
            st.download_button("⬇️ Unificado CSV", data=df_union.to_csv(index=False).encode("utf-8-sig"),
                               file_name="unificado.csv", mime="text/csv")
        with c2:
            st.download_button("⬇️ Unificado Excel", data=df_to_excel_bytes(df_union),
                               file_name="unificado.xlsx",
                               mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
    except Exception as e:
        st.error(f"No se pudo unificar: {e}")



