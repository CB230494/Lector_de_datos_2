# app_dashboard_plan_policial.py
import streamlit as st
import pandas as pd
import numpy as np
import io, re, textwrap, unicodedata, random
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MaxNLocator

st.set_page_config(page_title="Plan Policial – Dashboard", layout="wide")

# ===== Colores/estilo (rojo/azul + sombra) =====
COLOR_ROJO = "#D32F2F"
COLOR_AZUL = "#1565C0"
SOMBRA = [pe.withSimplePatchShadow(offset=(2,-2), shadow_rgbFace=(0,0,0), alpha=0.25, rho=0.98)]

def save_png(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=170); buf.seek(0); return buf
def nonempty(s: pd.Series):
    return (s.dropna().map(lambda x: str(x).strip()).replace("", np.nan).dropna())
def wrap_labels(labels, width=18):
    return ["\n".join(textwrap.wrap(str(x), width=width)) for x in labels]

# ===== Normalizadores =====
PERI_MAP = {
    "diario":"Diario","diaria":"Diario",
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
    return PERI_MAP.get(str(x).strip().lower(), str(x).strip().title())

# Tokenizar zonas: separa por coma o " y ", 1 por zona
SEP_ZONAS = re.compile(r"\s*,\s*|\s+y\s+", flags=re.IGNORECASE)
def tokenizar_zonas_unicas(valor):
    if pd.isna(valor): return []
    partes = [p.strip() for p in SEP_ZONAS.split(str(valor)) if p and p.strip()]
    partes = [re.sub(r"\s{2,}", " ", p) for p in partes]
    return sorted(set(partes))

# ===== Texto (cualitativo) =====
STOP_ES = set("""
a al algo algun alguna algunos algunas ante antes aquel aquella aquellas aquellos aqui
asi aun aunque cada como con contra cual cuales cualquier cualquiera dar de del desde donde
dos el ella ellas ellos en entre era eramos eran eres es esa esas ese eso esos esta estan
este esto estos fue fueron fui fuimos ha han hasta hay la las le les lo los mas mas alla
me mi mis mucha muchas mucho muchos muy nada ni no nos o para pero poco por porque que quien
quienes se sin sobre su sus tambien te tiene tienen tuve tuvo tuvimos tuvieron tu tus un una
uno unas unos ya y
""".split())
def quitar_acentos(s: str) -> str:
    s = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in s if unicodedata.category(ch) != "Mn")
TOKEN_RE = re.compile(r"[a-záéíóúñ]{3,}")

def tokens_es(texto: str):
    if not isinstance(texto, str): texto = str(texto) if pd.notna(texto) else ""
    t = quitar_acentos(texto.lower())
    toks = TOKEN_RE.findall(t)
    return [w for w in toks if w not in STOP_ES]

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
        if any(kw in base for kw in kws):
            return tema
    return "otro"

# ===== Lectura =====
st.title("📊 Plan Policial – Dashboard")
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

# ===== Campos clave (con respaldos) =====
COL_INDOLE = "Índole"                 # si no existe, usamos columna B
COL_ZONA   = "Zona(s)de trabajo"
COL_RESP   = "Responsable"
COL_META   = "Meta cuantitativa"
COL_PERI   = "Peridiocidad"           # viene así
# Cualitativo sugerido
CAND_CUALI = [c for c in ["Consideraciones","Efecto esperado","Actividad estratégica","Indicador de actividad"] if c in df.columns]
if not CAND_CUALI: CAND_CUALI = df.columns.tolist()

# ===== Limpieza =====
df = df.copy()
df["Meta_q"] = pd.to_numeric(df.get(COL_META), errors="coerce")
if COL_PERI in df: df["Peri_norm"] = df[COL_PERI].map(norm_peri)

# ===== Filtros =====
with st.sidebar:
    st.header("🎛️ Filtros")
    vals_resp = sorted(nonempty(df.get(COL_RESP, pd.Series(dtype=object))).unique()) if COL_RESP in df else []
    vals_peri = sorted(nonempty(df.get("Peri_norm", pd.Series(dtype=object))).unique()) if "Peri_norm" in df else []
    s_indole_all = df[COL_INDOLE] if COL_INDOLE in df else (df.iloc[:,1] if df.shape[1]>1 else pd.Series(dtype=object))
    vals_indole = sorted(nonempty(s_indole_all).unique()) if not s_indole_all.empty else []
    vals_zona = sorted(nonempty(df.get(COL_ZONA, pd.Series(dtype=object))).unique()) if COL_ZONA in df else []
    f_resp = st.multiselect("Responsable", vals_resp, [])
    f_peri = st.multiselect("Peridiocidad", vals_peri, [])
    f_indole = st.multiselect("Índole", vals_indole, [])
    f_zona = st.multiselect("Zona de trabajo (texto exacto)", vals_zona, [])
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

# ===== Helpers de gráfico =====
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

def donut(labels, values, titulo):
    fig, ax = plt.subplots(figsize=(8.5, 6.5), constrained_layout=True)
    total = int(np.nansum(values))
    wedges, texts, autotexts = ax.pie(
        values, labels=None, autopct=lambda p: f"{p:.1f}%\n({int(round(p*total/100.0))})",
        startangle=90, pctdistance=0.8, labeldistance=1.1,
        colors=[COLOR_AZUL if i%2==0 else COLOR_ROJO for i in range(len(values))]
    )
    for w in wedges: w.set_path_effects([pe.withStroke(linewidth=2, foreground="white", alpha=0.8)])
    centre_circle = plt.Circle((0,0),0.55,fc='white'); fig.gca().add_artist(centre_circle)
    ax.set_title(titulo)
    ax.legend(wedges, labels, title="Responsable", loc="center left", bbox_to_anchor=(1, 0.5))
    return fig, total

# =======================
# 1) ÍND0LE (bar) + texto
# =======================
st.markdown("## 1) Índole")
s_indole = df_f[COL_INDOLE] if COL_INDOLE in df_f else (df_f.iloc[:,1] if df_f.shape[1]>1 else pd.Series(dtype=object))
vals_ind = nonempty(s_indole)
if not vals_ind.empty:
    counts_ind = vals_ind.value_counts()
    figA = barras(counts_ind, "Índole – Conteo real", usar_rojo=True, int_ticks=True)
    st.pyplot(figA)
    st.download_button("🖼️ Descargar PNG", data=save_png(figA), file_name="indole_conteo.png", mime="image/png")

    # Texto automático
    top = counts_ind.head(3)
    tot = int(counts_ind.sum())
    pct = (top / tot * 100).round(1)
    st.markdown(
        f"**Resumen:** predomina **{top.index[0]}** ({top.iloc[0]}; {pct.iloc[0]}%), "
        f"seguido de **{top.index[1] if len(top)>1 else '—'}** "
        f"({top.iloc[1] if len(top)>1 else 0}; {pct.iloc[1] if len(top)>1 else 0}%) "
        f"y **{top.index[2] if len(top)>2 else '—'}** "
        f"({top.iloc[2] if len(top)>2 else 0}; {pct.iloc[2] if len(top)>2 else 0}%). "
        "Esto orienta el tipo de intervención (operativa, preventiva o de gestión) prioritaria en el periodo."
    )
else:
    st.info("No hay datos de Índole (si el encabezado no existe, asegúrate de que la **columna B** sea Índole).")

st.markdown("---")

# =============================
# 2) ZONAS (tokenizadas) + texto
# =============================
st.markdown("## 2) Zonas de trabajo")
if COL_ZONA in df_f.columns:
    zonas_tokens = df_f[COL_ZONA].dropna().apply(tokenizar_zonas_unicas)
    tokens = [z for zs in zonas_tokens for z in zs if z]
    zonas_sr = nonempty(pd.Series(tokens, dtype=object))
    if not zonas_sr.empty:
        counts_zona = zonas_sr.value_counts().astype(int)
        topZ = st.slider("Top zonas a mostrar", 5, max(5, min(30, len(counts_zona))), min(12, len(counts_zona)))
        figB = barras(counts_zona.head(topZ), "Zonas de trabajo (conteo entero)", usar_rojo=False, int_ticks=True)
        st.pyplot(figB)
        st.download_button("🖼️ Descargar PNG", data=save_png(figB), file_name="zonas_trabajo.png", mime="image/png")

        # Texto automático
        top = counts_zona.head(3)
        st.markdown(
            f"**Resumen:** las zonas más mencionadas son **{', '.join(top.index.tolist())}**. "
            "Cada mención en el plan suma 1 por zona, incluso si una fila incluye varias zonas. "
            "Este gráfico ayuda a focalizar recursos y coordinación interinstitucional en los puntos con mayor recurrencia."
        )
    else:
        st.info("No hay zonas válidas para contar.")
else:
    st.info("No se encontró la columna 'Zona(s)de trabajo'.")

st.markdown("---")

# ===============================================================
# 3) PERIDIOCIDAD–META–RESPONSABLE (DONUT) + texto y total de meta
# ===============================================================
st.markdown("## 3) Meta cuantitativa por Responsable (torta/donut)")
ok_cols = {"Meta_q", COL_RESP}.issubset(df_f.columns)
if ok_cols:
    df_meta = df_f.loc[df_f["Meta_q"].notna() & df_f[COL_RESP].notna(), [COL_RESP, "Meta_q"]]
    if not df_meta.empty:
        resumen = df_meta.groupby(COL_RESP, as_index=True)["Meta_q"].sum().sort_values(ascending=False)
        figC, total_meta = donut(list(resumen.index.astype(str)), list(resumen.values), "Distribución de la meta por responsable")
        st.pyplot(figC)
        st.download_button("🖼️ Descargar PNG", data=save_png(figC), file_name="meta_por_responsable.png", mime="image/png")

        # Texto automático claro
        mayor = resumen.index[0]; val_mayor = int(resumen.iloc[0])
        pct_mayor = round(val_mayor/total_meta*100,1) if total_meta>0 else 0
        st.markdown(
            f"**Resumen:** el responsable con mayor carga es **{mayor}** con **{val_mayor}** unidades "
            f"({pct_mayor}% del total). El **total de la meta cuantitativa** es **{int(total_meta)}**. "
            "Este gráfico justifica la asignación de recursos y seguimiento diferenciado por responsable."
        )

        with st.expander("📋 Ver tabla de meta por responsable"):
            st.dataframe(resumen.rename("Meta (suma)").to_frame(), use_container_width=True)
    else:
        st.info("No hay datos de Meta cuantitativa y Responsable.")
else:
    st.info("Faltan columnas de Meta cuantitativa o Responsable.")

st.markdown("---")
st.markdown("## 4) Módulo cualitativo (palabras clave, temas y citas)")

texto_series = df_f[cuali_col] if cuali_col in df_f.columns else pd.Series(dtype=object)
texto_series = nonempty(texto_series)
if texto_series.empty:
    st.info("No hay texto en la columna seleccionada.")
else:
    # Palabras clave
    tokens = [t for txt in texto_series for t in tokens_es(txt)]
    freq = pd.Series(tokens, dtype=object).value_counts()
    if not freq.empty:
        topK = st.slider("Top palabras clave", 5, min(40, max(5, len(freq))), min(15, len(freq)))
        fig_kw = barras(freq.head(topK), f"Top {topK} palabras en “{cuali_col}”", usar_rojo=False, int_ticks=True)
        st.pyplot(fig_kw)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig_kw), file_name="palabras_clave.png", mime="image/png")

    # Temas y citas
    df_cod = pd.DataFrame({"texto": texto_series})
    df_cod["tema"] = df_cod["texto"].map(clasificar_tema)
    counts_tema = df_cod["tema"].value_counts()
    if not counts_tema.empty:
        fig_t = barras(counts_tema, "Temas detectados (reglas simples)", usar_rojo=True, int_ticks=True)
        st.pyplot(fig_t)
        st.download_button("🖼️ Descargar PNG", data=save_png(fig_t), file_name="temas_detectados.png", mime="image/png")

        tema_sel = st.selectbox("Ver citas ejemplo del tema", counts_tema.index.tolist())
        ejemplos = df_cod[df_cod["tema"]==tema_sel]["texto"].tolist()
        random.shuffle(ejemplos)
        st.markdown(f"**Citas ejemplo – {tema_sel}:**")
        for cita in ejemplos[:5]:
            st.markdown(f"- “{cita}”")

        with st.expander("⬇️ Descargar cualitativo (CSV)"):
            out = io.BytesIO(); df_cod.to_csv(out, index=False, encoding="utf-8-sig"); out.seek(0)
            st.download_button("Descargar CSV", data=out.getvalue(), file_name="cualitativo_codificado.csv", mime="text/csv")

st.caption("🎨 Rojo/Azul con sombra. Zonas cuentan 1 por mención. Índole usa la columna 'Índole' o, si falta, la **columna B**. La torta suma la Meta por Responsable e incluye total y % para facilitar la explicación en el informe.")


