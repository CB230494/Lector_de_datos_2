# app_dashboard_plan_policial.py
import streamlit as st
import pandas as pd
import numpy as np
import io, re, textwrap
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from matplotlib.ticker import MaxNLocator

st.set_page_config(page_title="Plan Policial – Dashboard", layout="wide")

# ---------------- estilos ----------------
COLOR_ROJO = "#D32F2F"
COLOR_AZUL = "#1565C0"
PALETA = [
    "#1565C0", "#D32F2F", "#2E7D32", "#F9A825", "#6A1B9A",
    "#00838F", "#5D4037", "#C51162", "#455A64", "#7CB342"
]  # responsables: colores distintos
SOMBRA = [pe.withSimplePatchShadow(offset=(2,-2), shadow_rgbFace=(0,0,0), alpha=0.25, rho=0.98)]

def save_png(fig):
    buf = io.BytesIO(); fig.savefig(buf, format="png", bbox_inches="tight", dpi=170); buf.seek(0); return buf
def nonempty(s: pd.Series):
    return (s.dropna().map(lambda x: str(x).strip()).replace("", np.nan).dropna())
def wrap(labels, w=20): return ["\n".join(textwrap.wrap(str(x), width=w)) for x in labels]

# ---------------- normalizadores ----------------
PERI_MAP = {
    "diario":"Diario","diaria":"Diario","semanal":"Semanal","quincenal":"Quincenal",
    "mensual":"Mensual","bimestral":"Bimestral","trimestral":"Trimestral",
    "semestral":"Semestral","anual":"Anual"
}
def norm_peri(x):
    if pd.isna(x): return np.nan
    k = str(x).strip().lower(); return PERI_MAP.get(k, str(x).strip().title())

SEP_ZONAS = re.compile(r"\s*,\s*|\s+y\s+", flags=re.IGNORECASE)
def tokenizar_zonas_unicas(valor):
    if pd.isna(valor): return []
    partes = [p.strip() for p in SEP_ZONAS.split(str(valor)) if p and p.strip()]
    return sorted(set(re.sub(r"\s{2,}"," ",p) for p in partes))

# ---------------- lectura ----------------
st.title("📊 Plan Policial – Dashboard (ajustado)")
archivo = st.file_uploader("📁 Sube el Excel", type=["xlsx","xlsm"])
if not archivo:
    st.info("Sube el archivo para iniciar."); st.stop()
xls = pd.ExcelFile(archivo)
hoja = "Plan Policial" if "Plan Policial" in xls.sheet_names else xls.sheet_names[0]
df = pd.read_excel(xls, sheet_name=hoja)
st.success(f"✅ Hoja: **{hoja}** – {df.shape[0]} filas × {df.shape[1]} columnas")

# ---------------- columnas ----------------
COL_INDOLE = "Índole"                   # si no existe tomaremos columna B
COL_ZONA   = "Zona(s)de trabajo"
COL_RESP   = "Responsable"
COL_META   = "Meta cuantitativa"
COL_PERI   = "Peridiocidad"

# limpieza mínima
df = df.copy()
df["Meta_q"] = pd.to_numeric(df.get(COL_META), errors="coerce")
if COL_PERI in df: df["Peri_norm"] = df[COL_PERI].map(norm_peri)

# ======== GRAFICO 1 (único cuantitativo principal): Donut por Responsable ========
st.header("1) Meta cuantitativa por responsable (donut)")
df_mr = df.loc[df["Meta_q"].notna() & df[COL_RESP].notna(), [COL_RESP,"Meta_q"]]
if df_mr.empty:
    st.info("No hay datos de Meta y Responsable.")
else:
    resumen = df_mr.groupby(COL_RESP)["Meta_q"].sum().sort_values(ascending=False)
    labels = list(resumen.index.astype(str))
    values = list(resumen.values)
    total = int(np.nansum(values))

    # donut con colores distintos
    fig, ax = plt.subplots(figsize=(9,6), constrained_layout=True)
    colors = [PALETA[i % len(PALETA)] for i in range(len(labels))]
    wedges, _, autotexts = ax.pie(
        values, startangle=90, pctdistance=0.78,
        autopct=lambda p: f"{p:.1f}%\n({int(round(p*total/100.0))})",
        colors=colors
    )
    for w in wedges: w.set_path_effects([pe.withStroke(linewidth=2, foreground="white", alpha=0.8)])
    ax.add_artist(plt.Circle((0,0),0.55,fc="white"))
    ax.set_title("Distribución de la meta cuantitativa por responsable")
    ax.legend(wedges, wrap(labels, 30), title="Responsable", loc="center left", bbox_to_anchor=(1, 0.5))
    st.pyplot(fig)
    st.download_button("🖼️ Descargar PNG", data=save_png(fig), file_name="donut_meta_responsable.png", mime="image/png")

    # texto claro
    top_name = labels[0]; top_val = int(values[0]); top_pct = round(top_val/total*100,1) if total>0 else 0
    st.markdown(
        f"**Resumen:** el responsable con mayor carga es **{top_name}** con **{top_val}** unidades "
        f"({top_pct}% del total). El **total de la meta** asciende a **{total}**. "
        "Este gráfico explica cómo se reparte la meta y justifica la priorización de seguimiento."
    )

st.markdown("---")

# ======== GRAFICO 2: Índole (solo 3 categorías) ========
st.header("2) Índole (Operativo, Preventivo, Gestión administrativa)")
# si no está la columna por nombre, usamos la columna B
serie_indole = df[COL_INDOLE] if COL_INDOLE in df.columns else (df.iloc[:,1] if df.shape[1]>1 else pd.Series(dtype=object))
# mapeo a 3 clases
MAP_INDOLE = {
    "operativo":"Operativo",
    "preventivo":"Preventivo",
    "gestión administrativa":"Gestión administrativa",
    "gestion administrativa":"Gestión administrativa",
}
def map_indole(v):
    if pd.isna(v): return np.nan
    k = str(v).strip().lower()
    for kk, vv in MAP_INDOLE.items():
        if kk in k: return vv
    # si coincide exactamente con tus valores, se respeta:
    if str(v).strip() in MAP_INDOLE.values(): return str(v).strip()
    return np.nan  # ignora otros textos largos

ind_clas = serie_indole.map(map_indole).dropna()
if ind_clas.empty:
    st.info("No hay valores de Índole válidos (Operativo/Preventivo/Gestión administrativa).")
else:
    counts = ind_clas.value_counts()[["Operativo","Preventivo","Gestión administrativa"]].fillna(0).astype(int)
    fig2, ax = plt.subplots(figsize=(7.5,4.6), constrained_layout=True)
    colors = [COLOR_ROJO, COLOR_AZUL, "#2E7D32"]
    bars = ax.bar(counts.index, counts.values, color=colors, alpha=0.95)
    for b in bars:
        b.set_path_effects(SOMBRA)
        ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{int(b.get_height())}", ha="center", va="bottom",
                path_effects=[pe.withStroke(linewidth=3, foreground="white")])
    ax.set_title("Índole – conteo real (solo 3 categorías)")
    ax.yaxis.set_major_locator(MaxNLocator(integer=True))
    ax.grid(axis="y", alpha=0.25)
    st.pyplot(fig2)
    st.download_button("🖼️ Descargar PNG", data=save_png(fig2), file_name="indole_3categorias.png", mime="image/png")
    st.markdown(
        "**Lectura:** predomina la índole **Operativo/Preventivo** frente a **Gestión administrativa**. "
        "Esto orienta el tipo de intervención prioritaria y la logística requerida."
    )

st.markdown("---")

# ======== (Opcional) GRAFICO 3: Zonas tokenizadas ========
with st.expander("3) Zonas de trabajo (si deseas mostrarlo)"):
    if "Zona(s)de trabajo" in df.columns:
        zonas_tokens = df["Zona(s)de trabajo"].dropna().apply(tokenizar_zonas_unicas)
        tokens = [z for zs in zonas_tokens for z in zs if z]
        zonas_sr = nonempty(pd.Series(tokens, dtype=object))
        if not zonas_sr.empty:
            counts_z = zonas_sr.value_counts().astype(int)
            topZ = st.slider("Top zonas", 5, max(5, min(30, len(counts_z))), min(10, len(counts_z)))
            figZ, ax = plt.subplots(figsize=(9,5), constrained_layout=True)
            sub = counts_z.head(topZ)
            bars = ax.bar(wrap(sub.index, 22), sub.values, color=COLOR_AZUL, alpha=0.95)
            for b in bars:
                b.set_path_effects(SOMBRA)
                ax.text(b.get_x()+b.get_width()/2, b.get_height(), f"{int(b.get_height())}", ha="center", va="bottom",
                        path_effects=[pe.withStroke(linewidth=3, foreground="white")])
            ax.set_title("Zonas de trabajo (conteo entero)")
            ax.yaxis.set_major_locator(MaxNLocator(integer=True))
            ax.grid(axis="y", alpha=0.25)
            st.pyplot(figZ)
            st.download_button("🖼️ Descargar PNG", data=save_png(figZ), file_name="zonas_trabajo.png", mime="image/png")
            st.markdown("**Lectura:** cada mención suma 1 por zona; útil para priorización territorial.")
        else:
            st.info("No hay zonas válidas para contar.")
    else:
        st.info("No se encontró la columna 'Zona(s)de trabajo'.")

st.markdown("---")

# ===================== INFORME CUALITATIVO (con tus textos) =====================
st.header("Informe cualitativo (resumen editable)")
st.caption("Solo se muestran bloques con contenido (se omiten NA o vacíos).")

# --- Actividad estratégica (lista) ---
st.subheader("Actividad estratégica")
txt_actividad = st.text_area("Pega/edita las actividades estratégicas (una por línea):", value="""Coordinación y ejecución de operativos interinstitucionales nocturnos con enfoque en objetivos estratégicos dentro del área de intervención.
Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.
Gestión institucional mediante oficio para la asignación de recurso humano y transporte policial necesario para garantizar la cobertura operativa diaria en zonas de interés.
Ejecución de actividades cívico-policiales en espacios públicos y centros educativos, orientadas a fortalecer los vínculos comunitarios, promover la cultura de paz y fomentar la convivencia ciudadana desde un enfoque preventivo.
Despliegue de operativos presenciales en horarios mixtos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.
Desarrollo de operativos interinstitucionales de control dirigidos a la regulación de ventas informales y actividades no autorizadas de cobro de parqueo en la zona costera.
Implementación de acciones preventivas, lideradas por programas policiales, orientadas a la recuperación y apropiación positiva de espacios públicos.
Ejecución de talleres y jornadas de sensibilización en seguridad comercial, dirigidas a fortalecer las capacidades preventivas del sector empresarial y comercial.
Ejecución de operativos policiales focalizados para el abordaje e identificación de personas y vehículos vinculados a delitos de robo en viviendas, con base en análisis previo de información e inteligencia policial.
Capacitaciones en Seguridad Comunitaria, dirigidas a residentes extranjeros angloparlantes, con el fin de fortalecer su integración y participación en los esfuerzos preventivos locales.""")
acts = [a.strip() for a in txt_actividad.split("\n") if a.strip() and a.strip().upper()!="NA"]
if acts:
    st.markdown("\n".join([f"- {a}" for a in acts]))

# --- Actores – Indicador – Consideraciones (tabla) ---
st.subheader("Actores involucrados / Indicador / Consideraciones")
txt_tabla = st.text_area("Pega la tabla (3 columnas separadas por TAB o punto y coma ';'):", value=
"""Fuerza Pública|Policía de Tránsito|Policía de Migración|Policía Turística|DIAC;Cantidad de operativos policiales;1-Es necesario reforzar el personal del DIAC para esclarecer los objetivos a intervenir durante los operativos.\n2-Se requiere la presencia de la unidad de policía canina.\n3-La ubicación de los operativos debe ser aleatoria, según análisis previo de la zona.\n4-Los operativos deben ser fugaces, con una duración máxima de 40 minutos por zona.
Fuerza Pública;Cantidad de operativos policiales;1-Se requiere el apoyo constante de al menos 12 funcionarios del personal de gestión durante todos los días de ejecución, con el fin de garantizar la efectividad de la acción policial.\n2-Es necesario disponer de al menos una unidad policial adicional (recurso móvil) para asegurar una cobertura operativa adecuada y fortalecer la intervención en campo.
Fuerza Pública;Cantidad de oficios emitidos;
Fuerza Pública;Cantidad de cívicos policiales;NA
Fuerza Pública;Cantidad de operativos policiales;1-Se requiere el apoyo constante de al menos 12 funcionarios del personal de gestión durante todos los días de ejecución, con el fin de garantizar la efectividad de la acción policial.\n2-Es necesario disponer de al menos una unidad policial adicional (recurso móvil) para asegurar una cobertura operativa adecuada y fortalecer la intervención en campo.
Fuerza Pública|Policía de Tránsito|Policía de Migración|Policía Turística|DIAC;Cantidad de operativos policiales;NA
Fuerza Pública;Cantidad de acciones preventivas;NA
Fuerza Pública;Cantidad de talleres;NA
Fuerza Pública;Cantidad de operativos policiales;NA
Fuerza Pública;Cantidad de capacitaciones;NA"""
)
rows = []
for line in txt_tabla.splitlines():
    if not line.strip(): continue
    parts = [p.strip() for p in re.split(r";|\t", line, maxsplit=2)]
    if len(parts)<3: parts += [""]*(3-len(parts))
    actores, indicador, consid = parts
    if (not actores) and (not indicador) and (not consid): continue
    if consid.upper()=="NA": consid = ""
    rows.append({"Actores": actores.replace("|", ", "), "Indicador": indicador, "Consideraciones": consid})
if rows:
    tabla = pd.DataFrame(rows)
    tabla = tabla[(tabla["Actores"]!="") | (tabla["Indicador"]!="") | (tabla["Consideraciones"]!="")]
    st.dataframe(tabla, use_container_width=True)

# --- Efecto esperado (lista) ---
st.subheader("Efecto esperado")
txt_efecto = st.text_area("Pega/edita efectos (uno por línea):", value="""Reducción de actividades ilícitas y fortalecimiento de la presencia institucional en horarios de mayor riesgo.
Aumento de la percepción policial en puntos críticos mediante presencia policial visible.
Asegurar una presencia policial continua y eficaz en las zonas priorizadas, mediante la dotación oportuna del personal y los medios logísticos requeridos.
Fortalecer el vínculo entre la comunidad y la Fuerza Pública, promoviendo una cultura de paz, prevención y convivencia por medio de la interacción positiva en espacios públicos y centros educativos.
Recuperar el orden en el espacio público, reducir la informalidad y garantizar condiciones más seguras y reguladas para residentes, turistas y comercios formales.
Transformar los espacios públicos en entornos seguros y activos, fomentando su uso positivo por parte de la comunidad y reduciendo su vulnerabilidad ante actividades delictivas
Mejorar la percepción de seguridad y fortalecer la capacidad de prevención del delito en el sector comercial, mediante la adopción de buenas prácticas y la articulación con la Fuerza Pública.
Reducir la incidencia de robos a viviendas mediante la identificación oportuna de objetivos vinculados, así como el fortalecimiento de la capacidad de respuesta y disuasión policial en zonas residenciales vulnerables.
Mejorar el nivel de conocimiento y la capacidad de respuesta de la población extranjera residente, promoviendo su vinculación con las estrategias de seguridad comunitaria y fortaleciendo la cohesión social.""")
efectos = [e.strip() for e in txt_efecto.split("\n") if e.strip() and e.strip().upper()!="NA"]
if efectos: st.markdown("\n".join([f"- {e}" for e in efectos]))

# --- Actividades en desarrollo (tabla) ---
st.subheader("Actividades en desarrollo – Dirección Regional de Chorotega")
txt_desarrollo = st.text_area("Pega/edita lista numerada (una por línea):", value="""1. Reunión cerrada con personal de crimen organizado y Fiscalía de Santa Cruz, DIAC y GAO.
2. Creación de un chat de coordinación interinstitucional para operativos.
3. Planificación de operativos en la zona, en conjunto con transito, OIJ, Migración, GAO, Fiscalía, Unidad Canina y Policía Turística.
4. Georreferenciación de los puntos de venta de drogas y viviendas de los lideres de las organizaciones.
5. Fotografiar los vehículos en que se movilizan las estructuras criminales, así como la reseña de los mismos.
6. Facilitar los insumos al OIJ y Fiscalía con el fin de poder llevar a cabo los allanamientos correspondientes en la zona.
7. Crear una base de datos compartida entre OIJ, Policía Turística, Fiscalía y GAO.
8. Realizar reuniones quincenales de orden cerrado con el fin de definir los objetivos de mas interés e intercambiar información""")
items = [re.sub(r"^\s*\d+[\).]?\s*","",x).strip() for x in txt_desarrollo.splitlines() if x.strip()]
if items:
    st.dataframe(pd.DataFrame({"#": range(1,len(items)+1), "Actividad": items}), use_container_width=True)

# --- Listados Operativo / Preventivo (si quieres mostrarlos) ---
with st.expander("Notas operativas y preventivas (opcional)"):
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("**Operativo**")
        st.text_area("Pega aquí las notas de OPERATIVO (una por línea)", value="""GAO, Turistica, OIJ, Policía Municipal, Transito
Reseña a sujetos, identidad y modalidad
600 espacios para decomiso de motos
Impacto visual
Reventaron los bunker de Brasilito y Dylan Manuel Morales Méndez se fue del lugar; sin embargo ahora esta Marenco.
El recorrido se hace planificado, con grupos de trabajos que se vieran más y más efectivos
Se quiere intensificar a tres operaciones por semana, actualemnte son 2
decomiso con AK47 y se genera un vínculo con la estructura del Diablo
Deportación de Colombianos dedicados a la venta de droga; estrategia efectiva en vez de la judialización
Se han identificado a 4 oficiales involucrados con el crimen organizado como choferes, brindar información, entre otros.
Se estan planificando 2 allanamientos más para la estructura de Marenco
Hay una movilización de vivienda a miembros de la estructura criminal
Detención de unos sujetos y un vehículo relacionados a asaltos en locales comerciales (Villareal, Tempate, 27 de abril)
Existe una disputa entre la banda de Marenco y la de "W", la banda de los Colombianos de unió al de Marenco
Una operación con resultado de 7 personas con orden de captura""", height=220)
    with col2:
        st.markdown("**Preventivo**")
        st.text_area("Pega aquí las notas de PREVENTIVO (una por línea)", value="""Capacitaciones a la comunidad de Pinilla en seguridad comunitaria en Inglés
Brasilito seguimiento a las comunidades en conjunto de la policía Turística
Acciones preventivas comunales involucrados para mejorar la imagen de Fuerza Pública y acercamiento comunitario
Se presenta una planificación de los 4 meses que faltan del año en Villareal, Brasilito, Surfside y Potrero
Iniciaron en Julio las Ligas Atleticas en Brasilito""", height=220)

st.caption("🎨 Gráficos: rojo/azul con sombra. Donut con colores únicos por responsable. Índole limitada a 3 categorías. Los bloques cualitativos son editables y omiten filas vacías/NA.")


