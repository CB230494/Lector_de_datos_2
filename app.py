# app.py — Usuarios: DB SQLite con planes precargados desde Excel (ya incrustados)
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Seguimiento de Actividades", layout="wide")

DB_PATH = "actividades.db"

# ================== SEED: PLANES PRE-CARGADOS (extraídos de tu Excel) ==================
SEED_PLANES = [
 {'sector': 'Tamarindo',
  'indole': 'Operativo',
  'actividad_estrategica': 'Coordinación y ejecución de operativos interinstitucionales noc...oque en objetivos estratégicos dentro del área de intervención.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 24,
  'responsable': 'Sub Director Regional',
  'actores': 'Fuerza Pública\nPolicía de Tránsito\nPolicía de Migración\nPolicía Turística\nDIAC',
  'zona_trabajo': 'Tamarindo, Villareal, Flamingo, Brasilito, Potrero y Surfside',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Tamarindo',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Gestión administrativa',
  'actividad_estrategica': 'Gestión institucional mediante oficio para la asignación de recurso humano y transporte policial, con el propósito de garantizar la cobertura operativa diaria en zonas de interés.',
  'indicador': 'Cantidad de oficios emitidos',
  'meta_total': 1,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Tamarindo',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Santa Cruz',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Ejecución de actividades cívico-policiales en centros educativos, parques y espacios públicos para fortalecer la prevención y la convivencia ciudadana.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Santa Cruz',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Villarreal, 27 de Abril, Santa Cruz centro, Bolsón, Ortega, Portegolpe, La Garita, Cóbano, El Llano, Santa Bárbara',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Filadelfia',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Filadelfia',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Belén',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Belén',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Santa Cruz',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Santa Cruz',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Filadelfia',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Filadelfia',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Belén',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Belén',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Santa Cruz',
  'indole': 'Operativo',
  'actividad_estrategica': 'Despliegue de operativos presenciales en horarios nocturnos en zonas previamente identificadas como puntos de interés, con el objetivo de reforzar la vigilancia, la disuasión del delito y la presencia institucional.',
  'indicador': 'Cantidad de operativos policiales',
  'meta_total': 184,
  'responsable': 'Jefe de delegación policial de Santa Cruz',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Santa Cruz',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Tamarindo',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Villarreal',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Santa Cruz',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Santa Cruz',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Filadelfia',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Filadelfia',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Belén',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Belén',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Tamarindo',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Villarreal',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Villarreal',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Tamarindo',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Tamarindo',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Villarreal',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Villarreal',
  'fecha_inicio': None,
  'fecha_fin': None},
 {'sector': 'Santa Cruz',
  'indole': 'Preventivo',
  'actividad_estrategica': 'Charlas preventivas y acercamiento comunitario para fortalecer conductas seguras y la convivencia.',
  'indicador': 'Cantidad de actividades preventivas realizadas',
  'meta_total': 6,
  'responsable': 'Director Regional',
  'actores': 'Fuerza Pública',
  'zona_trabajo': 'Santa Cruz',
  'fecha_inicio': None,
  'fecha_fin': None}
]
# ================================================================================

# ========== DB ==========
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db_and_seed():
    conn = get_connection()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS planes (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sector TEXT NOT NULL,
        indole TEXT NOT NULL,
        actividad_estrategica TEXT NOT NULL,
        indicador TEXT NOT NULL,
        meta_total INTEGER NOT NULL CHECK (meta_total > 0),
        responsable TEXT NOT NULL,
        actores TEXT NOT NULL,
        zona_trabajo TEXT NOT NULL,
        fecha_inicio TEXT,
        fecha_fin TEXT
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
    # Seed solo si no hay planes
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM planes;")
    count = cur.fetchone()[0]
    if count == 0 and SEED_PLANES:
        cur.executemany("""
            INSERT INTO planes (sector, indole, actividad_estrategica, indicador, meta_total, responsable, actores, zona_trabajo, fecha_inicio, fecha_fin)
            VALUES (:sector, :indole, :actividad_estrategica, :indicador, :meta_total, :responsable, :actores, :zona_trabajo, :fecha_inicio, :fecha_fin)
        """, SEED_PLANES)
        conn.commit()
    conn.close()

init_db_and_seed()

# ========== Helpers ==========
def fetch_planes(sector=None):
    conn = get_connection()
    if sector and sector != "Todos":
        df = pd.read_sql_query("SELECT * FROM planes WHERE sector = ? ORDER BY id DESC", conn, params=(sector,))
    else:
        df = pd.read_sql_query("SELECT * FROM planes ORDER BY id DESC", conn)
    conn.close()
    return df

def fetch_avance(plan_id: int) -> int:
    conn = get_connection()
    df = pd.read_sql_query("SELECT cantidad FROM avances WHERE plan_id = ?", conn, params=(plan_id,))
    conn.close()
    return int(df["cantidad"].sum()) if not df.empty else 0

def insertar_avance(plan_id: int, cantidad: int, fecha_reg: date, obs: str, usuario: str):
    conn = get_connection()
    conn.execute("""
        INSERT INTO avances (plan_id, cantidad, fecha, observaciones, registrado_por)
        VALUES (?, ?, ?, ?, ?)
    """, (plan_id, int(cantidad), str(fecha_reg), (obs or None), (usuario or None)))
    conn.commit()
    conn.close()

# ========== UI ==========
st.title("📋 Registro de avances")

# Sectores
conn = get_connection()
sectores_db = pd.read_sql_query("SELECT DISTINCT sector FROM planes ORDER BY sector", conn)
conn.close()
sectores = ["Todos"] + sectores_db["sector"].tolist()

colA, colB = st.columns([1, 3])
sector = colA.selectbox("Sector", sectores, index=0)

df_planes = fetch_planes(None if sector == "Todos" else sector)
if df_planes.empty:
    st.info("No hay planes creados.")
    st.stop()

df_planes["label"] = df_planes.apply(
    lambda r: f"[{r['sector']}] {r['indicador']} • Meta {r['meta_total']} • Resp. {r['responsable']}",
    axis=1
)
plan_sel = colB.selectbox("Plan disponible", df_planes["label"].tolist())
plan = df_planes.loc[df_planes["label"] == plan_sel].iloc[0]

# Resumen
acumulado = fetch_avance(int(plan["id"]))
meta = int(plan["meta_total"])
porcentaje = min(100, round((acumulado * 100.0) / meta, 2)) if meta else 0

st.markdown("### 📌 Detalle del plan")
c1, c2, c3, c4 = st.columns(4)
c1.metric("Meta total", meta)
c2.metric("Acumulado", acumulado)
c3.metric("Restante", max(0, meta - acumulado))
c4.metric("% Avance", f"{porcentaje}%")
st.progress(int(porcentaje))

with st.expander("Ver más detalles"):
    st.write({
        "Índole": plan["indole"],
        "Actividad estratégica": plan["actividad_estrategica"],
        "Indicador": plan["indicador"],
        "Responsable": plan["responsable"],
        "Actores": plan["actores"],
        "Zona(s) de trabajo": plan["zona_trabajo"],
        "Periodo": f"{plan['fecha_inicio'] or ''} - {plan['fecha_fin'] or ''}",
    })

# Registrar avance
st.markdown("### ➕ Registrar avance")
col1, col2, col3 = st.columns([1, 1, 2])
cantidad = col1.number_input("Cantidad realizada", min_value=1, value=1, step=1)
fecha_reg = col2.date_input("Fecha", value=date.today())
usuario = col3.text_input("Registrado por (opcional)")
obs = st.text_area("Observaciones (opcional)")

if st.button("Guardar avance", type="primary"):
    try:
        insertar_avance(int(plan["id"]), cantidad, fecha_reg, obs, usuario)
        st.success("Avance registrado ✅")
        st.rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Historial
st.markdown("### 🧾 Historial reciente")
conn = get_connection()
hist = pd.read_sql_query(
    "SELECT fecha, cantidad, registrado_por AS usuario, observaciones FROM avances WHERE plan_id = ? ORDER BY id DESC LIMIT 50",
    conn, params=(int(plan["id"]),)
)
conn.close()
st.dataframe(hist, use_container_width=True)

