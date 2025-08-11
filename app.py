# app_dashboard_plan_policial.py
import streamlit as st
import pandas as pd
import numpy as np
import io, re, textwrap, unicodedata, random
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MaxNLocator

st.set_page_config(page_title="Plan Policial – Dashboard Cuantitativo y Cualitativo", layout="wide", initial_sidebar_state="expanded")

# ===== Estilos / colores =====
COLOR_ROJO = "#D32F2F"
COLOR_AZUL = "#1565C0"
SOMBRA = [pe.withSimplePatchShadow(offset=(2,-2), shadow_rgbFace=(0,0,0), alpha=0.25, rho=0.98)]
def save_png(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=160); buf.seek(0); return buf
def nonempty(s: pd.Series):
    return (s.dropna().map(lambda x: str(x).strip()).replace("", np.nan).dropna())
def wrap_labels(labels, width=18):
    return ["\n".join(textwrap.wrap(str(x), width=width)) for x in labels]

# ===== Normalizadores =====
PERI_MAP = {
    "diario":"Diario","diaria":"Diario","semanal":"Semanal","quincenal":"Quincenal","mensual":"Mensual",
    "bimestral":"Bimestral","trimestral":"Trimestral","semestral":"Semestral","anual":"Anual"
}
def norm_peri(x):
    if pd.isna(x): return np.nan
    k = str(x).strip().lower(); return PERI_MAP.get(k, str(x).strip().title())

# Tokenizar zonas: separa por coma o " y ", y cuenta 1 por zona por fila
SEP_ZONAS = re.compile(r"\s*,\s*|\s+y\s+", flags=re.IGNORECASE)
def tokenizar_zonas_unicas_por_fila(valor):
    if pd.isna(valor): return []
    partes = [p.strip() for p in SEP_ZONAS.split(str(valor)) if p and p.strip()]
    partes = [re.sub(r"\s{2,}", " ", p) for p in partes]
    return list(set(partes))

# ===== Utilidades texto (ES) para cualitativo =====
STOP_ES = set("""
a al algo algun alguna algunos algunas ante antes aquel aquella aquellas aquellos aqui
asi aun aunque cada como con contra cual cuales cualquier cualquiera dar de del desde donde
dos el ella ellas ellos en entre era eramos eran eres es esa esas ese eso esos esta estan
este esto estos fue fueron fui fuimos ha han hasta hay la las le les lo los mas mas alla
me mi mis mucha muchas mucho muchos muy nada ni no nos o para pero poco por porque que quien
quienes se sin sobre su sus tambien te tiene tienen tuve tuvo tuve tuvimos tuvieron tu tus un una
uno unas unos ya y
""".split())
def quitar_acentos(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
TOKEN_RE = re.compile(r"[a-záéíóúñ]{3,}")  # evita tokens de 1-2 letras y números

def limpiar_y_tokenizar(texto: str):
    if not isinstance(texto, str): texto = str(texto) if pd.notna(texto) else ""
    t = quitar_acentos(texto.lower())
    toks = TOKEN_RE.findall(t)
    toks = [w for w in toks if w not in STOP_ES]
    return toks

# Reglas de temas simples (puedes editar palabras clave)
TEMAS = {
    "iluminacion": ["luz","ilumin","alumbrad","farol"],
    "drogas": ["droga","narco","microtr","consum"],
    "robos/asaltos": ["robo","asalt","hurto","arrebato","ladron"],
    "violencia": ["violenc","agres","homicid","asesin","pelea"],
    "convivencia/ruidos": ["ruido","bulla","fiesta","escandalo"],
    "tránsito": ["transit","trafic","velocidad","accident"],
    "organizacion comunitaria": ["comunal","comunidad","comite","vecinal","organizacion","red"],
    "tecnologia/camaras": ["camara","cctv","drone","monitoreo","tecnolog"],
    "patrullaje/presencia": ["patrull","presencia","ronda","recorrido"]
}
def clasificar_tema(texto: str):
    base = quitar_acentos((texto or "").lower())
    for tema, kws in TEMAS.items():
        for kw in kws:
            if kw in base:
                return tema
    return "otro"

# ===== Lectura =====
st.title("📊 Plan Policial – Dashboard Cuantitativo y Cualitativo")
archivo = st.file_uploader("📁 Sube el Excel", type=["xlsx","xlsm"])
if not archivo:
    st.info("Sube el archivo para iniciar."); st.stop()

try:
    xls = pd.ExcelFile(archivo)
    hoja = "Plan Policial" if "Plan Policial" in xls.sheet_names else xls.sheet_names[0]
    df = pd.read_excel(xls, sheet_name=hoja)
except Exception as e:
    st.error(f"No pude leer el archivo/hoja: {e}"); st.stop()

st.success(f"✅ Hoja: **{hoja}** – {df.shape[0]} filas × {df.shape[1]} columnas")

# ===== Campos esperados (con respaldos) =====
COL_INDOLE = "Índole"                 # si no existe, usamos columna B
COL_ZONA   = "Zona(s)de trabajo"
COL_RESP   = "Responsable"
COL_META   = "Meta cuantitativa"
COL_PERI   = "Peridiocidad"           # así viene
# Cualitativo – sugeridas:
CAND_CUALI = [c for c in ["Consideraciones","Efecto esperado","Actividad estratégica","Indicador de actividad"]
              if c in df.columns]
if not CAND_CUALI:
    # si no hay ninguna, permite elegir cualquiera
    CAND_CUALI = df.columns.tolist()

# ===== Limpieza / normalización =====
df = df.copy()
df["Meta_q"] = pd.to_numeric(df.get(COL_META), errors="coerce")
if COL_PERI in df: df["Peri_norm"] = df[COL_PERI].map(norm_peri)

# ===== Filtros =====
with st.sidebar:
    st.header("🎛️ Filtros")
    vals_resp = sorted(nonempty(df.get(COL_RESP, pd.Series(dtype=object))).unique()) if COL_RESP in df else []
    vals_peri = sorted(nonempty(df.get("Peri_norm", pd.Series(dtype=object))).unique()) if "Peri_norm" in df else []
    vals_zona = sorted(nonempty(df.get(COL_ZONA, pd.Series(dtype=object))).unique()) if COL_ZONA in df else []
    s_indole_all = df[COL_INDOLE] if COL_INDOLE in df else (df.iloc[:,1] if df.shape[1]>1 else pd.Series(dtype=object))
    vals_indole = sorted(nonempty(s_indole_all).unique()) if not s_indole_all.empty else []

    f_resp = st.multiselect("Responsable", vals_resp, [])
    f_peri = st.multiselect("Peridiocidad", vals_peri, [])
    f_zona = st.multiselect("Zona(s) de trabajo – texto exacto", vals_zona, [])
    f_indole = st.multiselect("Índole", vals_indole, [])
    cuali_col = st.selectbox("Columna cualitativa", CAND_CUALI, index=0)

df_f = df.copy()
if f_resp: df_f = df_f[df_f[COL_RESP].isin(f_resp)]
if f_peri: df_f = df_f[df_f["Peri_norm"].isin(f_peri)]
if f_zona and COL_ZONA in df_f: df_f = df_f[df_f[COL_ZONA].isin(f_zona)]
s_indole = df_f[COL_INDOLE] if COL_INDOLE in df_f else (df_f.iloc[:,1] if df_f.shape[1]>1 else pd.Series(dtype=object))
if f_indole and not s_indole.empty: df_f = df_f[s_indole.isin(f_indole)]

st.caption(f"Datos filtrados: {len(df_f)} filas.")
with st.expander("👀 Ver tabla filtrada"):
    st.dataframe(df_f, use_container_width=True, height=360)

# ====== Helpers de gráfico ======
def barras(series, titulo, usar_rojo=True, int_ticks=False):
    fig, ax = plt.subplots(figsize=(9.8, 5.4), constrained_layout=True)
    color = COLOR_ROJO if usar_rojo else COLOR_AZUL
    series = series.sort_values(ascending=False)
    bars = ax.bar(wrap_labels(series.index), series.values, color=color, alpha=0.92)
    for b in bars: b.set_path_effects(SOMBRA)
    ax.set_title(titulo); ax.grid(axis="y", alpha=0.25)
    for i, v in enumerate(series.values.astype(int)):
        ax.text(i, v, f"{v:,}", ha="center", va="bottom",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    if int_ticks: ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    plt.xticks(rotation=15, ha="right")
    return fig

def barras_group(pivot_df, titulo):
    categorias = list(pivot_df.index.astype(str))
    grupos = list(pivot_df.columns.astype(str))
    x = np.arange(len(categorias)); n = max(1, len(grupos)); width = 0.8/n
    fig, ax = plt.subplots(figsize=(11.5, 6), constrained_layout=True)
    for i, col in enumerate(grupos):
        vals = pivot_df[col].fillna(0).values
        color = COLOR_AZUL if i % 2 == 0 else COLOR_ROJO
        bars = ax.bar(x + i*width - (n-1)*width/2, vals, width, label=col, color=color, alpha=0.92)
        for b, v in zip(bars, vals):
            b.set_path_effects(SOMBRA)
            if v > 0:
                ax.text(b.get_x()+b.get_width()/2, v, f"{int(v):,}", ha="center", va="bottom",
                        path_effects=[pe.withStroke(linewidth=3, foreground="white")], fontsize=9)
    ax.set_title(titulo); ax.set_xticks(x); ax.set_xticklabels(wrap_labels(categorias), rotation=10, ha="center")
    ax.grid(axis="y", alpha=0.25); ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    leg = ax.legend(title=pivot_df.columns.name or "Grupo", ncol=min(4, len(grupos))); 
    for txt in leg.get_texts(): txt.set_fontsize(9)
    return fig

st.markdown("## 🔴🔵 Cuantitativo")
# 1) Meta por Responsable y Peridiocidad
if {"Meta_q", COL_RESP}.issubset(df_f.columns) and "Peri_norm" in df_f:
    df_meta = df_f.loc[df_f["Meta_q"].notna() & df_f[COL_RESP].notna() & df_f["Peri_norm"].notna(),
                       [COL_RESP, "Peri_norm", "Meta_q"]]
    if not df_meta.empty:
        topN = st.slider("Top responsables por suma de meta", 5, 30, 12)
        top_resp = (df_meta.groupby(COL_RESP)["Meta_q"].sum().sort_values(ascending=False).head(topN)).index
        tabla = (df_meta[df_meta[COL_RESP].isin(top_resp)]
                 .groupby([COL_RESP,"Peri_norm"], as_index=False)["Meta_q"].sum())
        pivot = tabla.pivot(index=COL_RESP, columns="Peri_norm", values="Meta_q").fillna(0.0)
        orden = ["Diario","Semanal","Quincenal","Mensual","Bimestral","Trimestral","Semestral","Anual"]
        pivot = pivot[[c for c in orden if c in pivot.columns] + [c for c in pivot.columns if c not in orden]]
        figA = barras_group(pivot, "Meta cuantitativa (suma) por Responsable y Peridiocidad"); st.pyplot(figA)
        st.download_button("🖼️ Descargar PNG", data=save_png(figA),
                           file_name="meta_por_responsable_peridiocidad.png", mime="image/png")
    else:
        st.info("No hay datos suficientes de Meta/Responsable/Peridiocidad.")

# 2) Índole (columna B si no existe encabezado)
s_indole = df_f[COL_INDOLE] if COL_INDOLE in df_f else (df_f.iloc[:,1] if df_f.shape[1]>1 else pd.Series(dtype=object))
vals_ind = nonempty(s_indole)
if not vals_ind.empty:
    figB = barras(vals_ind.value_counts(), "Índole – Conteo real", usar_rojo=True, int_ticks=True); st.pyplot(figB)
    st.download_button("🖼️ Descargar PNG", data=save_png(figB), file_name="indole_conteo.png", mime="image/png")

# 3) Zonas de trabajo (tokenizadas, únicas por fila)
if "Zona(s)de trabajo" in df_f.columns:
    zonas_tokens = df_f["Zona(s)de trabajo"].dropna().apply(tokenizar_zonas_unicas_por_fila)
    tokens = [z for zs in zonas_tokens for z in zs if z]
    zonas_sr = nonempty(pd.Series(tokens, dtype=object))
    if not zonas_sr.empty:
        topZ = st.slider("Top zonas", 5, max(5, min(30, len(zonas_sr.value_counts()))), min(12, len(zonas_sr.value_counts())))
        figC = barras(zonas_sr.value_counts().astype(int).head(topZ), "Zonas de trabajo (conteo entero)", usar_rojo=False, int_ticks=True); st.pyplot(figC)
        st.download_button("🖼️ Descargar PNG", data=save_png(figC), file_name="zonas_trabajo.png", mime="image/png")

st.markdown("---")
st.markdown("## 📝 Cualitativo (automático)")

# ===== Construcción del corpus cualitativo =====
texto_series = df_f[cuali_col] if cuali_col in df_f.columns else pd.Series(dtype=object)
texto_series = nonempty(texto_series)
if texto_series.empty:
    st.info("No hay texto en la columna seleccionada.")
else:
    # Tokens y frecuencias
    tokens_total = []
    for t in texto_series:
        tokens_total.extend(limpiar_y_tokenizar(t))
    freq = pd.Series(tokens_total, dtype=object).value_counts()
    topK = st.slider("Top palabras clave", 5, min(40, max(5, len(freq))), min(15, len(freq)))
    if not freq.empty:
        fig_kw = barras(freq.head(topK), f"Top {topK} palabras en “{cuali_col}” (conteo)", usar_rojo=False, int_ticks=True)
        st.pyplot(fig_kw)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig_kw), file_name="palabras_clave.png", mime="image/png")

    # Clasificación por temas
    df_cod = pd.DataFrame({"texto": texto_series})
    df_cod["tema"] = df_cod["texto"].map(clasificar_tema)
    counts_tema = df_cod["tema"].value_counts()
    if not counts_tema.empty:
        fig_tema = barras(counts_tema, "Temas detectados (reglas simples)", usar_rojo=True, int_ticks=True)
        st.pyplot(fig_tema)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig_tema), file_name="temas_detectados.png", mime="image/png")

        # Citas ejemplo por tema
        tema_sel = st.selectbox("Ver citas ejemplo del tema", counts_tema.index.tolist())
        ejemplos = df_cod[df_cod["tema"]==tema_sel]["texto"].tolist()
        random.shuffle(ejemplos)
        st.markdown(f"**Ejemplos (hasta 5) – {tema_sel}:**")
        for cita in ejemplos[:5]:
            st.markdown(f"- “{cita}”")

        # Descargar matriz codificada
        with st.expander("⬇️ Descargar cualitativo codificado"):
            out = io.BytesIO()
            df_cod.to_csv(out, index=False, encoding="utf-8-sig"); out.seek(0)
            st.download_button("CSV con tema por fila", data=out.getvalue(), file_name="cualitativo_codificado.csv", mime="text/csv")

st.caption("🎨 Rojo/Azul con sombra. Cuantitativo: solo celdas con datos reales. Cualitativo: limpieza en español, palabras clave, temas y citas. Ajusta reglas de TEMAS si lo requieres.")

