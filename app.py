# app_dashboard_plan_policial.py
import streamlit as st
import pandas as pd
import numpy as np
import io
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

st.success(f"✅ Hoja leída: **{hoja}** – {df.shape[0]} filas × {df.shape[1]} columnas")

# ======== CAMPOS ESPERADOS ========
COL_NUM = "#"
COL_INDOLE = "Índole"
COL_ACTIVIDAD = "Actividad estratégica"
COL_ZONA = "Zona(s)de trabajo"
COL_ACTORES = "Actores involucrados"
COL_INDICADOR = "Indicador de actividad"
COL_CONSID = "Consideraciones"
COL_PERIOD = "Peridiocidad"  # viene así
COL_META = "Meta cuantitativa"
COL_RESP = "Responsable"
COL_EFECTO = "Efecto esperado"
# Actualiza esta fecha si cambia el nombre de la columna de resultados
COL_RESULT = [c for c in df.columns if str(c).lower().startswith("resultados ")]

if not COL_RESULT:
    st.warning("No encontré la columna de resultados (ej. 'Resultados 6 de ago 2025'). Puedes editar abajo para elegirla.")
    COL_RESULT = st.selectbox("Selecciona la columna de resultados", df.columns.tolist())
else:
    # si hay varias "Resultados X", toma la primera por defecto pero permite elegir
    COL_RESULT = st.selectbox("Columna de resultados", COL_RESULT)

# ======== LIMPIEZA BÁSICA ========
for c in [COL_META, COL_RESULT]:
    if c in df.columns:
        df[c] = pd.to_numeric(df[c], errors="coerce")

df["Meta_q"] = df.get(COL_META, np.nan)
df["Resultado"] = df.get(COL_RESULT, np.nan)
df["Avance_%"] = np.where(df["Meta_q"] > 0, (df["Resultado"] / df["Meta_q"]) * 100, np.nan)

# ======== KPIs ========
total_acciones = len(df)
meta_total = df["Meta_q"].sum(skipna=True) if "Meta_q" in df.columns else np.nan
resultado_total = df["Resultado"].sum(skipna=True) if "Resultado" in df.columns else np.nan
avance_global = (resultado_total / meta_total * 100) if (meta_total and meta_total > 0) else np.nan

colA, colB, colC, colD = st.columns(4)
colA.metric("Acciones totales", f"{total_acciones:,}")
colB.metric("Meta total", f"{(meta_total or 0):,.0f}")
colC.metric("Resultado total", f"{(resultado_total or 0):,.0f}")
colD.metric("Avance global", f"{avance_global:,.1f}%" if not pd.isna(avance_global) else "—")

st.markdown("---")

# ======== FILTROS ========
with st.expander("🎛️ Filtros"):
    f_indole = st.multiselect("Índole", sorted(df[COL_INDOLE].dropna().unique()) if COL_INDOLE in df else [], [])
    f_resp = st.multiselect("Responsable", sorted(df[COL_RESP].dropna().unique()) if COL_RESP in df else [], [])
    f_zona = st.multiselect("Zona(s) de trabajo", sorted(df[COL_ZONA].dropna().unique()) if COL_ZONA in df else [], [])

df_f = df.copy()
if f_indole:
    df_f = df_f[df_f[COL_INDOLE].isin(f_indole)]
if f_resp:
    df_f = df_f[df_f[COL_RESP].isin(f_resp)]
if f_zona:
    df_f = df_f[df_f[COL_ZONA].isin(f_zona)]

st.caption(f"Datos filtrados: {len(df_f)} filas.")

with st.expander("👀 Ver tabla filtrada"):
    st.dataframe(df_f, use_container_width=True, height=360)

# ======== GRÁFICOS ========
def barras(series, titulo, usar_rojo=True):
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
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

def barras_sumatoria(df_sum, titulo, usar_rojo=False):
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    color = COLOR_AZUL if not usar_rojo else COLOR_ROJO
    df_sum = df_sum.sort_values(ascending=False)
    bars = ax.bar(df_sum.index.astype(str), df_sum.values, color=color, alpha=0.92)
    for b in bars:
        b.set_path_effects(SOMBRA)
    ax.set_title(titulo)
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(df_sum.values):
        ax.text(i, v, f"{v:,.0f}", ha="center", va="bottom",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    plt.xticks(rotation=20, ha="right")
    return fig

def linea_avance(xcats, yvals, titulo):
    fig, ax = plt.subplots(figsize=(8.8, 4.4), constrained_layout=True)
    (ln,) = ax.plot(xcats, yvals, marker="o", linewidth=2.6, color=COLOR_AZUL)
    ln.set_path_effects([pe.withStroke(linewidth=4, foreground="black", alpha=0.2)])
    ax.fill_between(range(len(xcats)), yvals, alpha=0.15, color=COLOR_AZUL)
    ax.set_title(titulo)
    ax.set_ylim(0, max(100, np.nanmax(yvals)*1.15 if len(yvals) else 100))
    ax.set_ylabel("%")
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=20, ha="right")
    return fig

# 1) Distribución por Índole
if COL_INDOLE in df_f:
    counts_indole = df_f[COL_INDOLE].fillna("(sin dato)").value_counts()
    st.subheader("Distribución por Índole")
    fig1 = barras(counts_indole, "Acciones por Índole (conteo)", usar_rojo=False)
    st.pyplot(fig1)
    st.download_button("🖼️ Descargar PNG", data=save_png(fig1), file_name="indole_conteo.png", mime="image/png")

st.markdown("---")

# 2) Meta y Resultado por Índole
if COL_INDOLE in df_f and "Meta_q" in df_f and "Resultado" in df_f:
    meta_por_indole = df_f.groupby(COL_INDOLE, dropna=False)["Meta_q"].sum()
    res_por_indole = df_f.groupby(COL_INDOLE, dropna=False)["Resultado"].sum()

    col1, col2 = st.columns(2)
    with col1:
        fig2 = barras_sumatoria(meta_por_indole.fillna(0), "Meta cuantitativa por Índole (suma)", usar_rojo=True)
        st.pyplot(fig2)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig2), file_name="meta_por_indole.png", mime="image/png")
    with col2:
        fig3 = barras_sumatoria(res_por_indole.fillna(0), "Resultado por Índole (suma)", usar_rojo=False)
        st.pyplot(fig3)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig3), file_name="resultado_por_indole.png", mime="image/png")

st.markdown("---")

# 3) Top actividades estratégicas
if COL_ACTIVIDAD in df_f:
    top_k = st.slider("Top actividades estratégicas (por frecuencia)", 3, 20, 10)
    top_acts = df_f[COL_ACTIVIDAD].fillna("(sin dato)").value_counts().head(top_k)
    st.subheader("Top actividades estratégicas")
    fig4 = barras(top_acts, f"Top {top_k} Actividades (conteo)", usar_rojo=True)
    st.pyplot(fig4)
    st.download_button("🖼️ Descargar PNG", data=save_png(fig4), file_name="top_actividades.png", mime="image/png")

st.markdown("---")

# 4) Avance % por Responsable (cuando hay meta/resultado)
if COL_RESP in df_f and df_f["Meta_q"].notna().any() and df_f["Resultado"].notna().any():
    avances = df_f.groupby(COL_RESP, dropna=False).apply(
        lambda x: (x["Resultado"].sum() / x["Meta_q"].sum() * 100) if x["Meta_q"].sum() > 0 else np.nan
    ).dropna()
    if not avances.empty:
        st.subheader("Avance % por Responsable")
        fig5 = linea_avance(list(avances.index.astype(str)), list(avances.values), "Porcentaje de avance por Responsable")
        st.pyplot(fig5)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig5), file_name="avance_por_responsable.png", mime="image/png")

st.markdown("---")

# 5) Distribución por Zona(s) de trabajo y Actores involucrados (opcional)
colZ, colR = st.columns(2)
if COL_ZONA in df_f:
    counts_zona = df_f[COL_ZONA].fillna("(sin dato)").value_counts().head(12)
    with colZ:
        st.subheader("Zonas más mencionadas")
        fig6 = barras(counts_zona, "Zonas de trabajo (conteo)", usar_rojo=False)
        st.pyplot(fig6)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig6), file_name="zonas_conteo.png", mime="image/png")

if COL_RESP in df_f:
    counts_resp = df_f[COL_RESP].fillna("(sin dato)").value_counts().head(12)
    with colR:
        st.subheader("Responsables más frecuentes")
        fig7 = barras(counts_resp, "Responsables (conteo)", usar_rojo=True)
        st.pyplot(fig7)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig7), file_name="responsables_conteo.png", mime="image/png")

st.markdown("---")

# ======== EXPORTAR ========
with st.expander("⬇️ Descargar datos filtrados"):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_f.to_excel(w, index=False, sheet_name="Filtrado")
    st.download_button("Descargar Excel filtrado", data=out.getvalue(),
                       file_name="plan_policial_filtrado.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.caption("🎨 Paleta: rojo #D32F2F / azul #1565C0 con sombra sutil.")




