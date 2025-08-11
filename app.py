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

def nonempty(series):
    """Solo valores existentes (no NaN, no cadenas vacías/espacios)."""
    return (series.dropna()
                  .map(lambda x: str(x).strip())
                  .replace("", np.nan)
                  .dropna())

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
COL_INDOLE = "Índole"
COL_ACTIVIDAD = "Actividad estratégica"
COL_ZONA = "Zona(s)de trabajo"
COL_RESP = "Responsable"
COL_META = "Meta cuantitativa"

# detecta columna de resultados tipo "Resultados ..."
cand_result = [c for c in df.columns if str(c).lower().startswith("resultados ")]
if cand_result:
    COL_RESULT = st.selectbox("Columna de resultados", cand_result, index=0)
else:
    COL_RESULT = st.selectbox("Selecciona la columna de resultados", df.columns.tolist())

# ======== LIMPIEZA NUMÉRICA Y TEXTO ========
df = df.copy()

# Convierte metas/resultados a numérico y respeta solo los que existan
df["Meta_q"] = pd.to_numeric(df.get(COL_META), errors="coerce")
df["Resultado"] = pd.to_numeric(df.get(COL_RESULT), errors="coerce")

# Crea avance solo cuando hay ambos datos y meta>0
mask_avance = df["Meta_q"].notna() & (df["Meta_q"] > 0) & df["Resultado"].notna()
df.loc[mask_avance, "Avance_%"] = (df.loc[mask_avance, "Resultado"] / df.loc[mask_avance, "Meta_q"]) * 100

# ======== FILTROS (solo valores existentes) ========
with st.expander("🎛️ Filtros"):
    vals_indole = sorted(nonempty(df.get(COL_INDOLE, pd.Series(dtype=object))).unique()) if COL_INDOLE in df else []
    vals_resp   = sorted(nonempty(df.get(COL_RESP, pd.Series(dtype=object))).unique()) if COL_RESP in df else []
    vals_zona   = sorted(nonempty(df.get(COL_ZONA, pd.Series(dtype=object))).unique()) if COL_ZONA in df else []

    f_indole = st.multiselect("Índole", vals_indole, [])
    f_resp   = st.multiselect("Responsable", vals_resp, [])
    f_zona   = st.multiselect("Zona(s) de trabajo", vals_zona, [])

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

# ======== KPIs (solo cuentan celdas con datos reales) ========
total_acciones = len(df_f)
meta_total = df_f["Meta_q"].dropna().sum()
resultado_total = df_f["Resultado"].dropna().sum()
avance_global = (resultado_total / meta_total * 100) if (meta_total > 0 and not np.isnan(meta_total)) else np.nan

colA, colB, colC, colD = st.columns(4)
colA.metric("Acciones (filtradas)", f"{total_acciones:,}")
colB.metric("Meta total (solo celdas con dato)", f"{meta_total:,.0f}")
colC.metric("Resultado total (solo celdas con dato)", f"{resultado_total:,.0f}")
colD.metric("Avance global", f"{avance_global:,.1f}%" if pd.notna(avance_global) else "—")

st.markdown("---")

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

def barras_sumatoria(serie_sumas, titulo, usar_rojo=False):
    fig, ax = plt.subplots(figsize=(8.6, 4.8), constrained_layout=True)
    color = COLOR_AZUL if not usar_rojo else COLOR_ROJO
    serie_sumas = serie_sumas.sort_values(ascending=False)
    bars = ax.bar(serie_sumas.index.astype(str), serie_sumas.values, color=color, alpha=0.92)
    for b in bars:
        b.set_path_effects(SOMBRA)
    ax.set_title(titulo)
    ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(serie_sumas.values):
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
    ymax = 100 if len(yvals) == 0 else max(100, float(np.nanmax(yvals)) * 1.15)
    ax.set_ylim(0, ymax)
    ax.set_ylabel("%")
    ax.grid(True, alpha=0.3)
    plt.xticks(rotation=20, ha="right")
    return fig

# 1) Distribución por Índole (solo valores existentes)
if COL_INDOLE in df_f.columns:
    counts_indole = nonempty(df_f[COL_INDOLE]).value_counts()
    if not counts_indole.empty:
        st.subheader("Distribución por Índole (solo datos existentes)")
        fig1 = barras(counts_indole, "Índole – Conteo real", usar_rojo=False)
        st.pyplot(fig1)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig1), file_name="indole_conteo.png", mime="image/png")

st.markdown("---")

# 2) Meta y Resultado por Índole (solo cuando existen)
if COL_INDOLE in df_f.columns:
    df_mr = df_f.loc[df_f["Meta_q"].notna() | df_f["Resultado"].notna(), [COL_INDOLE, "Meta_q", "Resultado"]].copy()
    if not df_mr.empty:
        meta_por_indole = df_mr.groupby(COL_INDOLE, dropna=True)["Meta_q"].sum(min_count=1).dropna()
        res_por_indole  = df_mr.groupby(COL_INDOLE, dropna=True)["Resultado"].sum(min_count=1).dropna()

        col1, col2 = st.columns(2)
        if not meta_por_indole.empty:
            with col1:
                fig2 = barras_sumatoria(meta_por_indole, "Meta cuantitativa por Índole (suma de celdas con dato)", usar_rojo=True)
                st.pyplot(fig2)
                st.download_button("🖼️ Descargar PNG", data=save_png(fig2), file_name="meta_por_indole.png", mime="image/png")
        if not res_por_indole.empty:
            with col2:
                fig3 = barras_sumatoria(res_por_indole, "Resultado por Índole (suma de celdas con dato)", usar_rojo=False)
                st.pyplot(fig3)
                st.download_button("🖼️ Descargar PNG", data=save_png(fig3), file_name="resultado_por_indole.png", mime="image/png")

st.markdown("---")

# 3) Top actividades estratégicas (solo existentes)
if COL_ACTIVIDAD in df_f.columns:
    top_k = st.slider("Top actividades estratégicas (por frecuencia)", 3, 20, 10)
    top_acts = nonempty(df_f[COL_ACTIVIDAD]).value_counts().head(top_k)
    if not top_acts.empty:
        st.subheader("Top actividades estratégicas (conteo real)")
        fig4 = barras(top_acts, f"Top {top_k} Actividades", usar_rojo=True)
        st.pyplot(fig4)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig4), file_name="top_actividades.png", mime="image/png")

st.markdown("---")

# 4) Avance % por Responsable (solo responsables con datos de meta y resultado)
if COL_RESP in df_f.columns:
    df_resp = df_f.loc[df_f["Meta_q"].notna() & (df_f["Meta_q"] > 0) & df_f["Resultado"].notna(), [COL_RESP, "Meta_q", "Resultado"]]
    if not df_resp.empty:
        avances = (df_resp.groupby(COL_RESP)
                         .apply(lambda x: (x["Resultado"].sum() / x["Meta_q"].sum() * 100)
                                if x["Meta_q"].sum() > 0 else np.nan)
                         .dropna())
        if not avances.empty:
            st.subheader("Avance % por Responsable (solo con datos presentes)")
            fig5 = linea_avance(list(avances.index.astype(str)), list(avances.values),
                                "Porcentaje de avance por Responsable")
            st.pyplot(fig5)
            st.download_button("🖼️ Descargar PNG", data=save_png(fig5), file_name="avance_por_responsable.png", mime="image/png")

st.markdown("---")

# 5) Zonas y Responsables más frecuentes (solo existentes)
colZ, colR = st.columns(2)
if COL_ZONA in df_f.columns:
    counts_zona = nonempty(df_f[COL_ZONA]).value_counts().head(12)
    if not counts_zona.empty:
        with colZ:
            st.subheader("Zonas de trabajo (conteo real)")
            fig6 = barras(counts_zona, "Zonas de trabajo", usar_rojo=False)
            st.pyplot(fig6)
            st.download_button("🖼️ Descargar PNG", data=save_png(fig6), file_name="zonas_conteo.png", mime="image/png")
if COL_RESP in df_f.columns:
    counts_resp = nonempty(df_f[COL_RESP]).value_counts().head(12)
    if not counts_resp.empty:
        with colR:
            st.subheader("Responsables (conteo real)")
            fig7 = barras(counts_resp, "Responsables", usar_rojo=True)
            st.pyplot(fig7)
            st.download_button("🖼️ Descargar PNG", data=save_png(fig7), file_name="responsables_conteo.png", mime="image/png")

st.markdown("---")

# ======== EXPORTAR (solo lo filtrado) ========
with st.expander("⬇️ Descargar datos filtrados"):
    out = io.BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as w:
        df_f.to_excel(w, index=False, sheet_name="Filtrado")
    st.download_button("Descargar Excel filtrado", data=out.getvalue(),
                       file_name="plan_policial_filtrado.xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

st.caption("🎨 Solo se cuentan celdas con dato real. Paleta: rojo #D32F2F / azul #1565C0.")


