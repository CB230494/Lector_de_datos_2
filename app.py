# app.py — Seguimiento de actividades (SQLite) con 10 planes precargados
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Seguimiento de Actividades", layout="wide")

DB_PATH = "actividades.db"

# ===================== 10 PLANES PRE-CARGADOS =====================
SEED_PLANES = [
    {
        "indole": "Operativo",
        "actividad_estrategica": (
            "Coordinación y ejecución de operativos interinstitucionales nocturnos "
            "con enfoque en objetivos estratégicos dentro del área de intervención."
        ),
        "zona_trabajo": "Tamarindo, Villarreal, Flamingo, Brasilito, Potrero y Surfside",
        "actores": "Fuerza Pública; Policía de Tránsito; Policía de Migración; Policía Turística; DIAC",
        "indicador": "Cantidad de operativos policiales",
        "consideraciones": (
            "1-Es necesario reforzar al personal del DIAC para esclarecer los objetivos a intervenir durante los operativos.\n"
            "2-Se requiere la presencia de la unidad de policía canina.\n"
            "3-La ubicación de los operativos debe ser aleatoria, según análisis previo de la zona."
        ),
        "periodicidad": "Semanal",
        "meta_total": 24,
        "responsable": "Sub Director Regional",
        "efecto_esperado": (
            "Reducción de actividades ilícitas y fortalecimiento de la presencia institucional en horarios de mayor riesgo."
        ),
    },
    {
        "indole": "Operativo",
        "actividad_estrategica": (
            "Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, "
            "con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional."
        ),
        "zona_trabajo": "Tamarindo",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de operativos policiales",
        "consideraciones": (
            "1-Se requiere el apoyo constante de al menos 12 funcionarios del personal de gestión durante todos los días de ejecución, "
            "con el fin de garantizar la efectividad de la acción policial.\n"
            "2-Es necesario disponer de al menos una unidad policial adicional (recurso móvil) para asegurar una cobertura."
        ),
        "periodicidad": "Diario",
        "meta_total": 184,
        "responsable": "Jefe de delegación policial de Santa Cruz",
        "efecto_esperado": "Aumento de la percepción policial en puntos críticos mediante presencia policial visible.",
    },
    {
        "indole": "Gestión administrativa",
        "actividad_estrategica": (
            "Gestión institucional mediante oficio para la asignación de recurso humano y transporte policial necesario para "
            "garantizar la cobertura operativa diaria en zonas de interés."
        ),
        "zona_trabajo": "Tamarindo",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de oficios emitidos",
        "consideraciones": "",
        "periodicidad": "Semestral",
        "meta_total": 1,
        "responsable": "Director Regional",
        "efecto_esperado": (
            "Asegurar una presencia policial continua y eficaz en las zonas priorizadas, mediante la dotación oportuna de recurso "
            "personal y los medios logísticos requeridos."
        ),
    },
    {
        "indole": "Preventivo",
        "actividad_estrategica": (
            "Ejecución de actividades cívico‑policiales en espacios públicos y centros educativos, orientadas a fortalecer "
            "los vínculos comunitarios, promover la cultura de paz y fomentar la convivencia ciudadana desde un enfoque preventivo."
        ),
        "zona_trabajo": "Villarreal",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de cívicos policiales",
        "consideraciones": "NA",
        "periodicidad": "Mensual",
        "meta_total": 6,
        "responsable": "Director Regional",
        "efecto_esperado": (
            "Fortalecer el vínculo entre la comunidad y la Fuerza Pública, promoviendo una cultura de paz, prevención y convivencia "
            "por medio de la interacción positiva en espacios públicos y centros educativos."
        ),
    },
    {
        "indole": "Operativo",
        "actividad_estrategica": (
            "Despliegue de operativos presenciales en horarios mixtos en zonas previamente identificadas como puntos de interés, "
            "con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional."
        ),
        "zona_trabajo": "Flamingo",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de operativos policiales",
        "consideraciones": (
            "1-Se requiere el apoyo constante de al menos 12 funcionarios del personal de gestión durante todos los días de la ejecución, "
            "con el fin de garantizar la efectividad de la acción policial.\n"
            "2-Es necesario disponer de al menos una unidad policial adicional (recurso móvil) para asegurar una cobertura."
        ),
        "periodicidad": "Diario",
        "meta_total": 184,
        "responsable": "Jefe de delegación policial de Santa Cruz",
        "efecto_esperado": "Aumento de la percepción policial en puntos críticos mediante presencia policial visible.",
    },
    {
        "indole": "Operativo",
        "actividad_estrategica": (
            "Desarrollo de operativos interinstitucionales de control dirigidos a la regulación de ventas informales y actividades no autorizadas "
            "de cobro de parqueo en zona costera."
        ),
        "zona_trabajo": "Flamingo y Brasilito",
        "actores": "Fuerza Pública; Policía de Tránsito; Policía de Migración; Policía Turística; DIAC",
        "indicador": "Cantidad de operativos policiales",
        "consideraciones": "NA",
        "periodicidad": "Quincenal",
        "meta_total": 12,
        "responsable": "Jefe de delegación policial de Santa Cruz",
        "efecto_esperado": (
            "Recuperar el orden en el espacio público, reducir la informalidad y garantizar condiciones más seguras y reguladas para "
            "residentes, turistas y comercios formales."
        ),
    },
    {
        "indole": "Preventivo",
        "actividad_estrategica": (
            "Implementación de acciones preventivas, lideradas por programas policiales, orientadas a la recreación y apropiación positiva "
            "de espacios públicos."
        ),
        "zona_trabajo": "Brasilito",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de acciones preventivas",
        "consideraciones": "NA",
        "periodicidad": "Quincenal",
        "meta_total": 12,
        "responsable": "Director Regional",
        "efecto_esperado": (
            "Transformar los espacios públicos en entornos seguros y activos, fomentando su uso positivo por parte de la comunidad y "
            "reduciendo su vulnerabilidad a actividades delictivas."
        ),
    },
    {
        "indole": "Preventivo",
        "actividad_estrategica": (
            "Ejecución de talleres y jornadas de sensibilización en seguridad comercial, dirigidas a fortalecer las capacidades preventivas "
            "del sector empresarial."
        ),
        "zona_trabajo": "Brasilito",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de talleres",
        "consideraciones": "NA",
        "periodicidad": "Semestral",
        "meta_total": 6,
        "responsable": "Director Regional",
        "efecto_esperado": (
            "Mejorar la percepción de seguridad y fortalecer la capacidad de prevención del delito en el sector comercial, mediante la adopción "
            "de buenas prácticas y la actualización continua."
        ),
    },
    {
        "indole": "Operativo",
        "actividad_estrategica": (
            "Ejecución de operativos policiales focalizados para abordaje e identificación de personas y vehículos vinculados a delitos de "
            "robo en viviendas, en coordinación con unidades de información e inteligencia policial."
        ),
        "zona_trabajo": "Surfside",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de operativos policiales",
        "consideraciones": "NA",
        "periodicidad": "Mensual",
        "meta_total": 6,
        "responsable": "Jefe de delegación policial de Santa Cruz",
        "efecto_esperado": (
            "Reducir la incidencia de robos a viviendas mediante la identificación oportuna de objetivos vinculados, así como el fortalecimiento "
            "de la capacidad de respuesta y disuasión policial en zonas residenciales vulnerables."
        ),
    },
    {
        "indole": "Preventivo",
        "actividad_estrategica": (
            "Capacitaciones en Seguridad Comunitaria, dirigidas a residentes extranjeros angloparlantes, con el fin de mejorar su integración "
            "y participación en los servicios preventivos locales."
        ),
        "zona_trabajo": "Surfside",
        "actores": "Fuerza Pública",
        "indicador": "Cantidad de capacitaciones",
        "consideraciones": "NA",
        "periodicidad": "Semestral",
        "meta_total": 1,
        "responsable": "Director Regional",
        "efecto_esperado": (
            "Mejorar el nivel de conocimiento y la capacidad de respuesta de la población extranjera residente, promoviendo su vinculación con "
            "las estrategias de seguridad comunitaria y fortaleciendo la cohesión social."
        ),
    },
]
# ================================================================

# ===================== SQLite =====================
def conn():
    c = sqlite3.connect(DB_PATH, check_same_thread=False)
    c.execute("PRAGMA foreign_keys = ON;")
    return c

def init_db():
    c = conn()
    c.executescript("""
    CREATE TABLE IF NOT EXISTS planes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        indole TEXT NOT NULL,
        actividad_estrategica TEXT NOT NULL,
        zona_trabajo TEXT NOT NULL,
        actores TEXT NOT NULL,
        indicador TEXT NOT NULL,
        consideraciones TEXT,
        periodicidad TEXT,
        meta_total INTEGER NOT NULL CHECK (meta_total > 0),
        responsable TEXT NOT NULL,
        efecto_esperado TEXT,
        -- Clave única para evitar duplicados (sin usar la zona como clave)
        UNIQUE (indole, actividad_estrategica, indicador, meta_total, responsable)
    );
    CREATE TABLE IF NOT EXISTS avances (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        plan_id INTEGER NOT NULL,
        cantidad INTEGER NOT NULL CHECK (cantidad > 0),
        fecha TEXT,
        observaciones TEXT,
        registrado_por TEXT,
        FOREIGN KEY(plan_id) REFERENCES planes(id) ON DELETE CASCADE
    );
    """)
    # sembrar si está vacío
    cur = c.cursor()
    cur.execute("SELECT COUNT(*) FROM planes;")
    if cur.fetchone()[0] == 0:
        cur.executemany("""
            INSERT OR IGNORE INTO planes
            (indole, actividad_estrategica, zona_trabajo, actores, indicador, consideraciones, periodicidad, meta_total, responsable, efecto_esperado)
            VALUES (:indole, :actividad_estrategica, :zona_trabajo, :actores, :indicador, :consideraciones, :periodicidad, :meta_total, :responsable, :efecto_esperado)
        """, SEED_PLANES)
        c.commit()
    c.close()

init_db()

# ===================== Helpers =====================
def get_planes():
    c = conn()
    df = pd.read_sql_query(
        "SELECT id, indole, indicador, meta_total, responsable, zona_trabajo FROM planes ORDER BY id", c
    )
    c.close()
    return df

def get_plan(plan_id: int):
    c = conn()
    df = pd.read_sql_query("SELECT * FROM planes WHERE id = ?", c, params=(plan_id,))
    c.close()
    return df.iloc[0]

def get_acumulado(plan_id: int) -> int:
    c = conn()
    df = pd.read_sql_query("SELECT SUM(cantidad) AS s FROM avances WHERE plan_id = ?", c, params=(plan_id,))
    c.close()
    return int(df.s.fillna(0).iloc[0])

def add_avance(plan_id: int, cantidad: int, fecha: date, obs: str, user: str):
    c = conn()
    c.execute(
        "INSERT INTO avances (plan_id, cantidad, fecha, observaciones, registrado_por) VALUES (?,?,?,?,?)",
        (plan_id, int(cantidad), str(fecha), (obs or None), (user or None)),
    )
    c.commit()
    c.close()

def get_historial(plan_id: int):
    c = conn()
    df = pd.read_sql_query(
        "SELECT fecha, cantidad, registrado_por AS usuario, observaciones FROM avances WHERE plan_id = ? ORDER BY id DESC",
        c, params=(plan_id,),
    )
    c.close()
    return df

# ===================== UI =====================
st.title("📋 Registro de avances")

df_planes = get_planes()
if df_planes.empty:
    st.error("No se cargaron los planes. Avísame y los pego de nuevo.")
    st.stop()

# Tabla compacta (1 fila = 1 plan)
st.markdown("### 📑 Planes disponibles")
st.dataframe(
    df_planes.rename(columns={
        "id": "ID", "indole": "Índole", "indicador": "Indicador",
        "meta_total": "Meta", "responsable": "Responsable", "zona_trabajo": "Zona(s)"
    }),
    use_container_width=True, hide_index=True
)

# Selector por ID
plan_id = st.selectbox(
    "Selecciona un plan por ID",
    options=df_planes["id"].tolist(),
    format_func=lambda i: f"ID {i} – {df_planes.loc[df_planes['id']==i, 'indicador'].values[0]}",
)

plan = get_plan(plan_id)
acum = get_acumulado(plan_id)
meta = int(plan["meta_total"])
pct = min(100, round(acum * 100.0 / meta, 2)) if meta else 0

st.markdown("### 📌 Resumen del avance")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Meta total", meta)
c2.metric("Acumulado", acum)
c3.metric("Restante", max(0, meta - acum))
c4.metric("% Avance", f"{pct}%")
st.progress(int(pct))

st.markdown("### 🧾 Detalles del plan")
d1, d2 = st.columns(2)
with d1:
    st.markdown(f"**Índole:** {plan['indole']}")
    st.markdown(f"**Indicador:** {plan['indicador']}")
    st.markdown(f"**Periodicidad:** {plan['periodicidad'] or '-'}")
    st.markdown(f"**Responsable:** {plan['responsable']}")
with d2:
    st.markdown(f"**Actores:** {plan['actores']}")
    st.markdown(f"**Zona(s) de trabajo:** {plan['zona_trabajo']}")
st.markdown("**Actividad estratégica:**")
st.write(plan["actividad_estrategica"])
if plan["consideraciones"]:
    st.markdown("**Consideraciones:**")
    st.write(plan["consideraciones"])
if plan["efecto_esperado"]:
    st.markdown("**Efecto esperado:**")
    st.write(plan["efecto_esperado"])

st.markdown("### ➕ Registrar avance")
col1, col2, col3 = st.columns([1, 1, 2])
cantidad = col1.number_input("Cantidad", min_value=1, value=1, step=1)
fecha = col2.date_input("Fecha", value=date.today())
user = col3.text_input("Registrado por (opcional)")
obs = st.text_area("Observaciones (opcional)")

if acum + cantidad > meta:
    st.warning(f"Este registro superaría la meta ({acum}+{cantidad} > {meta}). Ajusta la cantidad.")

if st.button("Guardar avance", type="primary"):
    if acum + cantidad > meta:
        st.error("No se guardó porque sobrepasa la meta.")
    else:
        add_avance(plan_id, cantidad, fecha, obs, user)
        st.success("Avance registrado ✅")
        st.rerun()

st.markdown("### 🧾 Historial")
st.dataframe(get_historial(plan_id), use_container_width=True, hide_index=True)


