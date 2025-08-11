# app_dashboard_plan_policial.py
import streamlit as st
import pandas as pd
import numpy as np
import io, re, textwrap
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MaxNLocator

st.set_page_config(page_title="Dashboard – Plan Policial", layout="wide")

# ===== colores / estilos =====
COLOR_ROJO = "#D32F2F"
COLOR_AZUL = "#1565C0"
SOMBRA = [pe.withSimplePatchShadow(offset=(2,-2), shadow_rgbFace=(0,0,0), alpha=0.25, rho=0.98)]

def save_png(fig):
    buf = io.BytesIO()
    fig.savefig(buf, format="png", bbox_inches="tight", dpi=160)
    buf.seek(0)
    return buf

def nonempty(s: pd.Series):
    return (s.dropna().map(lambda x: str(x).strip()).replace("", np.nan).dropna())

def wrap_labels(labels, width=18):
    return ["\n".join(textwrap.wrap(str(x), width=width)) for x in labels]

def barras(series, titulo, usar_rojo=True, int_ticks=False):
    fig, ax = plt.subplots(figsize=(9.5, 5.2), constrained_layout=True)
    color = COLOR_ROJO if usar_rojo else COLOR_AZUL
    series = series.sort_values(ascending=False)
    bars = ax.bar(wrap_labels(series.index), series.values, color=color, alpha=0.92)
    for b in bars: b.set_path_effects(SOMBRA)
    ax.set_title(titulo)
    ax.grid(axis="y", alpha=0.25)
    # etiquetas de valor (enteros)
    for i, v in enumerate(series.values.astype(int)):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    if int_ticks:
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.xticks(rotation=20, ha="right")
    return fig

# === normalizadores ===
PERI_MAP = {
    "diario":"Diario", "diaria":"Diario",
    "semanal":"Semanal",
    "quincenal":"Quincenal",
    "mensual":"Mensual",
    "bimestral":"Bimestral",
    "trimestral":"Trimestral",
    "semestral":"Semestral",
    "anual":"Anual",
}
def norm_peri(x):
    if pd.isna(x): return np.nan
    k = str(x).strip().lower()
    return PERI_MAP.get(k, str(x).strip().title())

SEP_ZONAS = re.compile(r"\s*,\s*|\s+y\s+", flags=re.IGNORECASE)
def tokenizar_zonas_unicas_por_fila(valor):
    """Devuelve set de zonas únicas por fila (sin duplicados dentro de la misma celda)."""
    if pd.isna(valor): return []
    partes = [p.strip() for p in SEP_ZONAS.split(str(valor)) if p and p.strip()]
    # normalizar espacios
    partes = [re.sub(r"\s{2,}", " ", p) for p in partes]
    return list(set(partes))  # únicas por fila

def get_col(df: pd.DataFrame, preferred_name: str, fallback_index: int | None):
    if preferred_name in df.columns:
        return df[preferred_name]
    if fallback_index is not None and df.shape[1] > fallback_index:
        return df.iloc[:, fallback_index]
    # si nada, columna vacía
    return pd.Series(dtype=object)

# ===== lectura =====
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

# ===== campos =====
COL_INDOLE = "Índole"               # si no está, usamos columna B (índice 1)
COL_ZONA   = "Zona(s)de trabajo"
COL_RESP   = "Responsable"
COL_META   = "Meta cuantitativa"
COL_PERI   = "Peridiocidad"         # viene así en el archivo

# numéricos + normalizaciones
df = df.copy()
df["Meta_q"] = pd.to_numeric(df.get(COL_META), errors="coerce")
if COL_PERI in df:
    df["Peri_norm"] = df[COL_PERI].map(norm_peri)

# filtros
with st.expander("🎛️ Filtros"):
    vals_resp = sorted(nonempty(df.get(COL_RESP, pd.Series(dtype=object))).unique()) if COL_RESP in df else []
    vals_peri = sorted(nonempty(df.get("Peri_norm", pd.Series(dtype=object))).unique()) if "Peri_norm" in df else []
    vals_zona = sorted(nonempty(df.get(COL_ZONA, pd.Series(dtype=object))).unique()) if COL_ZONA in df else []
    # Índole puede venir con otro encabezado; si no, usamos B
    s_indole = get_col(df, COL_INDOLE, 1)
    vals_indole = sorted(nonempty(s_indole).unique()) if not s_indole.empty else []

    f_resp = st.multiselect("Responsable", vals_resp, [])
    f_peri = st.multiselect("Peridiocidad", vals_peri, [])
    f_zona = st.multiselect("Zona(s) de trabajo (texto original)", vals_zona, [])
    f_indole = st.multiselect("Índole", vals_indole, [])

df_f = df.copy()
if f_resp: df_f = df_f[df_f[COL_RESP].isin(f_resp)]
if f_peri: df_f = df_f[df_f["Peri_norm"].isin(f_peri)]
if f_zona and COL_ZONA in df_f: df_f = df_f[df_f[COL_ZONA].isin(f_zona)]
# Índole por nombre o por columna B
s_indole = get_col(df_f, COL_INDOLE, 1)
if f_indole and not s_indole.empty:
    df_f = df_f[s_indole.isin(f_indole)]

st.caption(f"Datos filtrados: {len(df_f)} filas.")
with st.expander("👀 Ver tabla filtrada"):
    st.dataframe(df_f, use_container_width=True, height=360)

# ===== 1) Meta por Responsable y Peridiocidad (barras agrupadas) =====
st.markdown("## 1) Meta cuantitativa por Responsable y Peridiocidad")
if {"Meta_q", COL_RESP}.issubset(df_f.columns) and "Peri_norm" in df_f:
    df_meta = df_f.loc[df_f["Meta_q"].notna() & df_f[COL_RESP].notna() & df_f["Peri_norm"].notna(),
                       [COL_RESP, "Peri_norm", "Meta_q"]].copy()
    if not df_meta.empty:
        # top N responsables por suma de meta (para que no quede ilegible)
        topN = st.slider("Ver top responsables por suma de meta", 5, 30, 12, step=1)
        top_resp = (df_meta.groupby(COL_RESP)["Meta_q"].sum().sort_values(ascending=False).head(topN)).index
        df_meta = df_meta[df_meta[COL_RESP].isin(top_resp)]

        tabla = (df_meta.groupby([COL_RESP, "Peri_norm"], as_index=False)["Meta_q"].sum())
        pivot = tabla.pivot(index=COL_RESP, columns="Peri_norm", values="Meta_q").fillna(0.0)

        # ordenar columnas de peri en una secuencia lógica
        orden_peri = ["Diario","Semanal","Quincenal","Mensual","Bimestral","Trimestral","Semestral","Anual"]
        cols = [c for c in orden_peri if c in pivot.columns] + [c for c in pivot.columns if c not in orden_peri]
        pivot = pivot[cols]

        # gráfico agrupado bonito
        categorias = list(pivot.index.astype(str))
        grupos = list(pivot.columns.astype(str))
        x = np.arange(len(categorias))
        n = len(grupos)
        width = 0.8 / max(n,1)

        fig, ax = plt.subplots(figsize=(11.5, 6), constrained_layout=True)
        for i, col in enumerate(grupos):
            vals = pivot[col].values
            color = COLOR_AZUL if i % 2 == 0 else COLOR_ROJO
            bars = ax.bar(x + i*width - (n-1)*width/2, vals, width, label=col, color=color, alpha=0.92)
            for b, v in zip(bars, vals):
                b.set_path_effects(SOMBRA)
                if v > 0:
                    ax.text(b.get_x() + b.get_width()/2, v, f"{int(v):,}", ha="center", va="bottom",
                            path_effects=[pe.withStroke(linewidth=3, foreground="white")], fontsize=9)
        ax.set_title("Meta cuantitativa (suma) por Responsable y Peridiocidad")
        ax.set_xticks(x)
        ax.set_xticklabels(wrap_labels(categorias), rotation=10, ha="center")
        ax.grid(axis="y", alpha=0.25)
        ax.yaxis.set_major_locator(MaxNLocator(integer=True))
        leg = ax.legend(title="Peridiocidad", ncol=min(4, n), frameon=True)
        for txt in leg.get_texts(): txt.set_fontsize(9)
        st.pyplot(fig)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig),
                           file_name="meta_por_responsable_peridiocidad.png", mime="image/png")
    else:
        st.info("No hay datos suficientes de Meta/Responsable/Peridiocidad.")
else:
    st.info("Faltan columnas para este gráfico.")

st.markdown("---")

# ===== 2) Distribución por Índole (columna B si no hay encabezado) =====
st.markdown("## 2) Distribución por Índole (solo datos reales)")
s_indole = get_col(df_f, COL_INDOLE, 1)  # usa B si no existe 'Índole'
vals_ind = nonempty(s_indole)
if not vals_ind.empty:
    counts_indole = vals_ind.value_counts()
    figB = barras(counts_indole, "Índole – Conteo real", usar_rojo=True, int_ticks=True)
    st.pyplot(figB)
    st.download_button("🖼️ Descargar PNG", data=save_png(figB),
                       file_name="indole_conteo.png", mime="image/png")
else:
    st.info("No hay datos de Índole (verifica que la columna B corresponda a Índole).")

st.markdown("---")

# ===== 3) Zonas de trabajo (tokenizadas, únicas por fila, enteros) =====
st.markdown("## 3) Zonas de trabajo (tokenizadas, únicas por fila)")
if COL_ZONA in df_f.columns:
    zonas_tokens = df_f[COL_ZONA].dropna().apply(tokenizar_zonas_unicas_por_fila)
    # aplano y quito vacíos
    tokens = []
    for zs in zonas_tokens:
        tokens.extend([z for z in zs if z])
    zonas_sr = pd.Series(tokens, dtype=object)
    zonas_sr = nonempty(zonas_sr)

    if not zonas_sr.empty:
        counts_zona = zonas_sr.value_counts().astype(int)  # asegurar enteros
        # Top N para claridad
        topZ = st.slider("Mostrar top zonas", 5, max(5, min(30, len(counts_zona))), min(12, len(counts_zona)))
        counts_zona = counts_zona.head(topZ)
        figC = barras(counts_zona, "Zonas de trabajo (conteo entero)", usar_rojo=False, int_ticks=True)
        st.pyplot(figC)
        st.download_button("🖼️ Descargar PNG", data=save_png(figC),
                           file_name="zonas_trabajo_tokenizadas.png", mime="image/png")
    else:
        st.info("No hay zonas válidas para contar.")
else:
    st.info("No se encontró la columna 'Zona(s)de trabajo'.")

st.caption("🎨 Rojo/Azul con sombra. Zonas: cada mención cuenta 1; sin decimales. Índole: si no existe por nombre, se toma columna B.")

