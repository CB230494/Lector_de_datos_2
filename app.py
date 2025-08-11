# app_lector_excel.py
import streamlit as st
import pandas as pd
import io
import re
import unicodedata
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

st.set_page_config(page_title="Lector + Dashboard – Plan Policial", layout="wide")

st.title("📘 Lector de Excel + 📊 Dashboard")
st.write("Sube tu archivo Excel, ajusta opciones y visualiza un dashboard automático.")

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

def intentar_parsear_fechas(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    for col in df.columns:
        if df[col].dtype == object:
            try:
                parsed = pd.to_datetime(df[col], errors="ignore", dayfirst=True, infer_datetime_format=True)
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

# --- Estilo de gráficos rojo/azul con sombreado ---
COLOR_ROJO = "#D32F2F"
COLOR_AZUL = "#1565C0"
SOMBRA = [pe.withSimplePatchShadow(offset=(2,-2), shadow_rgbFace=(0,0,0), alpha=0.25, rho=0.98)]

def guardar_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
    buf.seek(0)
    return buf

def barras_rojo_azul(series, titulo, usar_rojo=True):
    fig, ax = plt.subplots(figsize=(8, 4.6), constrained_layout=True)
    color = COLOR_ROJO if usar_rojo else COLOR_AZUL
    series = series.sort_values(ascending=False)
    bars = ax.bar(series.index.astype(str), series.values, color=color, alpha=0.9)
    for b in bars:
        b.set_path_effects(SOMBRA)
    ax.set_title(titulo)
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(series.values):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom", fontsize=10,
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    plt.xticks(rotation=20, ha="right")
    return fig

def linea_rojo_azul(x, y, titulo, usar_rojo=False):
    fig, ax = plt.subplots(figsize=(8.4, 4.2), constrained_layout=True)
    color = COLOR_AZUL if usar_rojo else COLOR_ROJO
    (ln,) = ax.plot(x, y, marker="o", linewidth=2.5, color=color)
    ln.set_path_effects([pe.withStroke(linewidth=4, foreground="black", alpha=0.2)])
    ax.fill_between(x, y, alpha=0.15, color=color)
    ax.set_title(titulo)
    ax.grid(True, alpha=0.3)
    return fig

# ---------------- UI: carga ----------------
files = st.file_uploader("📁 Sube archivos .xlsx / .xlsm", type=["xlsx", "xlsm"], accept_multiple_files=True)

st.sidebar.header("⚙️ Opciones")
limpiar_columnas = st.sidebar.checkbox("Normalizar nombres de columnas", value=True)
parsear_fechas = st.sidebar.checkbox("Detectar y parsear fechas", value=True)
eliminar_columnas_vacias = st.sidebar.checkbox("Eliminar columnas totalmente vacías", value=True)
unir_archivos = st.sidebar.checkbox("Unir todos los archivos/hojas en una sola tabla", value=True)

if not files:
    st.info("Sube al menos un archivo para comenzar.")
    st.stop()

# ---------------- Lectura flexible (similar a tu flujo anterior) ----------------
dataframes = []
for idx, f in enumerate(files, start=1):
    st.markdown(f"### 📄 Archivo {idx}: `{f.name}`")
    try:
        xls = pd.ExcelFile(f)
        sheet = st.selectbox("Selecciona la hoja", xls.sheet_names, key=f"sheet_{f.name}")

        df_preview_raw = pd.read_excel(xls, sheet_name=sheet, header=None, nrows=12)
        with st.expander("👀 Vista previa cruda (primeras filas)"):
            st.dataframe(df_preview_raw, use_container_width=True, height=220)

        use_header = st.number_input("Fila de encabezado (0=primera fila)", 0, 50, 0, 1, key=f"hdr_{f.name}")
        skiprows = st.number_input("Filas a omitir antes del encabezado", 0, 200, 0, 1, key=f"skip_{f.name}")

        df = pd.read_excel(xls, sheet_name=sheet, header=use_header, skiprows=skiprows)

        if eliminar_columnas_vacias:
            df = df.dropna(axis=1, how="all")
        if limpiar_columnas:
            df = normalizar_nombres_columnas(df)
        if parsear_fechas:
            df = intentar_parsear_fechas(df)

        st.success(f"✅ {df.shape[0]} filas × {df.shape[1]} columnas")
        st.dataframe(df, use_container_width=True, height=320)

        st.download_button("⬇️ Descargar Excel (limpio)", data=df_to_excel_bytes(df),
                           file_name=f"{f.name.rsplit('.',1)[0]}_limpio.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        dataframes.append(df)
    except Exception as e:
        st.error(f"❌ Error al leer '{f.name}': {e}")

# ---------------- Unificación + Dashboard ----------------
if unir_archivos and dataframes:
    st.markdown("---")
    df = pd.concat(dataframes, ignore_index=True, sort=False)
    if eliminar_columnas_vacias:
        df = df.dropna(axis=1, how="all")

    st.header("📊 Dashboard")
    with st.expander("📄 Ver tabla unificada"):
        st.dataframe(df, use_container_width=True, height=380)

    # === KPIs básicos ===
    total_filas = len(df)
    total_cols = df.shape[1]
    columnas_fecha = [c for c in df.columns if pd.api.types.is_datetime64_any_dtype(df[c])]
    rango_fechas = "—"
    if columnas_fecha:
        c0 = columnas_fecha[0]
        fechas_validas = df[c0].dropna()
        if not fechas_validas.empty:
            rango_fechas = f"{fechas_validas.min().date()} → {fechas_validas.max().date()}"
    colA, colB, colC = st.columns(3)
    colA.metric("Registros", f"{total_filas:,}")
    colB.metric("Columnas", f"{total_cols:,}")
    colC.metric("Rango de fechas", rango_fechas)

    # === Sugerencias de campos comunes (ajusta a tu Excel) ===
    # Si tu archivo “Plan de Policial.xlsx” tiene columnas tipo delegacion, linea_accion, estado, etc.,
    # cámbialas aquí para que el dashboard las grafique.
    posibles_dims = [
        "delegacion", "linea", "linea_accion", "accion", "indicador", "estado",
        "peticion", "preocupacion", "lugar", "franja", "seguridad_descriptor"
    ]
    dims_existentes = [c for c in posibles_dims if c in df.columns]

    # Selector de dimensión para gráfico de barras azul
    if dims_existentes:
        st.subheader("📌 Distribuciones principales")
        col1, col2 = st.columns(2, vertical_alignment="top")

        with col1:
            dim1 = st.selectbox("Dimensión A (barras azul)", dims_existentes, key="dimA")
            counts1 = df[dim1].astype(str).replace({"nan":"(sin dato)"}).value_counts()
            fig1 = barras_rojo_azul(counts1, f"Distribución por {dim1}", usar_rojo=False)
            st.pyplot(fig1)
            st.download_button("🖼️ Descargar gráfico (PNG)", data=guardar_png(fig1),
                               file_name=f"dist_{dim1}.png", mime="image/png")

        with col2:
            # otra dimensión opcional para barras rojas
            dims2 = [d for d in dims_existentes if d != dim1] or dims_existentes
            dim2 = st.selectbox("Dimensión B (barras rojo)", dims2, key="dimB")
            counts2 = df[dim2].astype(str).replace({"nan":"(sin dato)"}).value_counts()
            fig2 = barras_rojo_azul(counts2, f"Distribución por {dim2}", usar_rojo=True)
            st.pyplot(fig2)
            st.download_button("🖼️ Descargar gráfico (PNG)", data=guardar_png(fig2),
                               file_name=f"dist_{dim2}.png", mime="image/png")
    else:
        st.info("No detecté columnas típicas para distribuir (como 'delegacion', 'linea_accion', 'estado'). "
                "Puedes renombrar en el Excel o decirme cómo se llaman para ajustarlo aquí mismo.")

    # === Tendencia temporal (si hay alguna fecha) ===
    if columnas_fecha:
        st.subheader("🕒 Tendencia temporal")
        cfecha = st.selectbox("Columna de fecha", columnas_fecha, index=0)
        serie = df[cfecha].dropna().dt.date.value_counts().sort_index()
        if not serie.empty:
            fig_t = linea_rojo_azul(list(serie.index), list(serie.values),
                                    f"Registros por día ({cfecha})", usar_rojo=False)
            st.pyplot(fig_t)
            st.download_button("🖼️ Descargar tendencia (PNG)", data=guardar_png(fig_t),
                               file_name=f"tendencia_{cfecha}.png", mime="image/png")
        else:
            st.info("No hay fechas válidas para trazar.")

    st.caption("🎨 Paleta usada: rojo #D32F2F y azul #1565C0 con sombra sutil.")




