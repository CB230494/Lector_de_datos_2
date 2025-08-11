# app_dashboard_plan_policial.py
import streamlit as st
import pandas as pd
import numpy as np
import io
import re
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe

st.set_page_config(page_title="Dashboard – Plan Policial", layout="wide")

# ======== COLORES Y SOMBRA ========
COLOR_ROJO = "#D32F2F"
COLOR_AZUL = "#1565C0"
SOMBRA = [pe.withSimplePatchShadow(offset=(2,-2), shadow_rgbFace=(0,0,0), alpha=0.25, rho=0.98)]

def save_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
    buf.seek(0)
    return buf

def nonempty(series):
    return (series.dropna()
                  .map(lambda x: str(x).strip())
                  .replace("", np.nan)
                  .dropna())

# --- tokenización de zonas: separa por coma o por " y "
SEP_ZONAS = re.compile(r"\s*,\s*|\s+y\s+", flags=re.IGNORECASE)
def tokenizar_zonas(valor):
    if pd.isna(valor): return []
    partes = [p.strip() for p in SEP_ZONAS.split(str(valor)) if p and p.strip()]
    # opcional: normalizar espacios dobles
    return [re.sub(r"\s{2,}", " ", p) for p in partes]

# ======== LECTURA ========
st.title("📊 Dashboard – Plan Policial")
archivo = st.file_uploader("📁 Sube el Excel 'Plan de Policial.xlsx'", type=["xlsx","xlsm"])
if not archivo:
    st.info("Sube el archivo para iniciar.")
    st.stop()

try:
    xls = pd.ExcelFile(archivo)
    hoja = "Plan Policial" if "Plan Policial" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=hoja)
except Exception as e:
    st.error(f"No pude leer el archivo/hoja: {e}")
    st.stop()

st.success(f"✅ Hoja: **{hoja}** – {df.shape[0]} filas × {df.shape[1]} columnas")

# ======== CAMPOS ESPERADOS ========
COL_INDOLE = "Índole"
COL_ZONA = "Zona(s)de trabajo"
COL_RESP = "Responsable"
COL_META = "Meta cuantitativa"
COL_PERI = "Peridiocidad"  # así viene escrito en el xlsx

# detectar columna de resultados si luego la quieres usar (no necesaria para estos 3 gráficos)
cand_result = [c for c in df.columns if str(c).lower().startswith("resultados ")]
if cand_result:
    _ = st.selectbox("Columna de resultados (opcional)", cand_result, index=0)

# ======== LIMPIEZA NUMÉRICA Y TEXTO ========
df = df.copy()
df["Meta_q"] = pd.to_numeric(df.get(COL_META), errors="coerce")

# ======== FILTROS (solo valores reales) ========
with st.expander("🎛️ Filtros"):
    vals_indole = sorted(nonempty(df.get(COL_INDOLE, pd.Series(dtype=object))).unique()) if COL_INDOLE in df else []
    vals_resp   = sorted(nonempty(df.get(COL_RESP, pd.Series(dtype=object))).unique()) if COL_RESP in df else []
    vals_peri   = sorted(nonempty(df.get(COL_PERI, pd.Series(dtype=object))).unique()) if COL_PERI in df else []

    f_indole = st.multiselect("Índole", vals_indole, [])
    f_resp   = st.multiselect("Responsable", vals_resp, [])
    f_peri   = st.multiselect("Peridiocidad", vals_peri, [])

df_f = df.copy()
if f_indole:
    df_f = df_f[df_f[COL_INDOLE].isin(f_indole)]
if f_resp:
    df_f = df_f[df_f[COL_RESP].isin(f_resp)]
if f_peri:
    df_f = df_f[df_f[COL_PERI].isin(f_peri)]

st.caption(f"Datos filtrados: {len(df_f)} filas.")
with st.expander("👀 Ver tabla filtrada"):
    st.dataframe(df_f, use_container_width=True, height=360)

# ======== helpers de gráficos ========
def barras(series, titulo, usar_rojo=True):
    fig, ax = plt.subplots(figsize=(8.8, 5), constrained_layout=True)
    color = COLOR_ROJO if usar_rojo else COLOR_AZUL
    series = series.sort_values(ascending=False)
    bars = ax.bar(series.index.astype(str), series.values, color=color, alpha=0.92)
    for b in bars:
        b.set_path_effects(SOMBRA)
    ax.set_title(titulo)
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(series.values):
        ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    plt.xticks(rotation=20, ha="right")
    return fig

def barras_agrupadas_por_categoria(pivot_df, titulo):
    """
    pivot_df: índice = Responsable, columnas = Peridiocidad, valores = sum(Meta_q)
    """
    categorias = list(pivot_df.index.astype(str))
    grupos = list(pivot_df.columns.astype(str))
    x = np.arange(len(categorias))
    n = len(grupos)
    width = 0.8 / max(n,1)

    fig, ax = plt.subplots(figsize=(10.5, 5.8), constrained_layout=True)
    for i, col in enumerate(grupos):
        vals = pivot_df[col].fillna(0).values
        color = COLOR_AZUL if i % 2 == 0 else COLOR_ROJO
        bars = ax.bar(x + i*width - (n-1)*width/2, vals, width, label=col, color=color, alpha=0.92)
        for b in bars:
            b.set_path_effects(SOMBRA)

    ax.set_title(titulo)
    ax.set_xticks(x)
    ax.set_xticklabels(categorias, rotation=20, ha="right")
    ax.grid(axis="y", alpha=0.25)
    ax.legend(title="Peridiocidad")
    return fig

st.markdown("## 1) Meta cuantitativa por Responsable y Peridiocidad")
# solo responsables/peridiocidad con métricas reales
df_meta = df_f.loc[df_f["Meta_q"].notna() & df_f[COL_RESP].notna(), [COL_RESP, COL_PERI, "Meta_q"]].copy()
if not df_meta.empty:
    tabla = (df_meta
             .groupby([COL_RESP, COL_PERI], dropna=True, as_index=False)["Meta_q"].sum())
    pivot = tabla.pivot(index=COL_RESP, columns=COL_PERI, values="Meta_q").sort_index()
    figA = barras_agrupadas_por_categoria(pivot, "Meta cuantitativa (suma) por Responsable, separada por Peridiocidad")
    st.pyplot(figA)
    st.download_button("🖼️ Descargar PNG", data=save_png(figA),
                       file_name="meta_por_responsable_peridiocidad.png", mime="image/png")
else:
    st.info("No hay datos suficientes de Meta/Responsable/Peridiocidad.")

st.markdown("---")
st.markdown("## 2) Distribución por Índole (solo datos existentes)")
if COL_INDOLE in df_f.columns:
    counts_indole = nonempty(df_f[COL_INDOLE]).value_counts()
    if not counts_indole.empty:
        figB = barras(counts_indole, "Índole – Conteo real", usar_rojo=True)
        st.pyplot(figB)
        st.download_button("🖼️ Descargar PNG", data=save_png(figB),
                           file_name="indole_conteo.png", mime="image/png")
    else:
        st.info("No hay datos de Índole.")
else:
    st.info("No se encontró la columna 'Índole'.")

st.markdown("---")
st.markdown("## 3) Zonas de trabajo (tokenizadas, conteo real)")
if COL_ZONA in df_f.columns:
    # expandir filas en tokens de zona
    zonas_series = df_f[COL_ZONA].dropna().apply(tokenizar_zonas)
    # “explode” manual sin usar pandas>=1.3 explode list -> series
    zonas_list = []
    for zs in zonas_series:
        zonas_list.extend(zs)
    zonas_sr = pd.Series(zonas_list, dtype=object)
    zonas_sr = nonempty(zonas_sr)

    if not zonas_sr.empty:
        counts_zona = zonas_sr.value_counts()
        figC = barras(counts_zona, "Zonas de trabajo", usar_rojo=False)
        st.pyplot(figC)
        st.download_button("🖼️ Descargar PNG", data=save_png(figC),
                           file_name="zonas_trabajo_tokenizadas.png", mime="image/png")
    else:
        st.info("No hay zonas válidas para contar.")
else:
    st.info("No se encontró la columna 'Zona(s)de trabajo'.")

st.caption("🎨 Barras azul/rojo con sombra. Solo se cuentan celdas con dato real. Zonas: cada mención cuenta por separado (tokenización por coma o 'y').")

