# app.py — Registro de avances (SQLite) con planes precargados o pegados como CSV (sin Excel)
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date
from io import StringIO

st.set_page_config(page_title="Seguimiento de Actividades", layout="wide")

DB_PATH = "actividades.db"

# ================== 1) PLANES PRE-CARGADOS (opcional) ==================
# Reemplaza los 10 dicts por TUS 10 FILAS exactas (sin duplicados).
# Si lo dejas vacío, podrás pegarlos como CSV desde la app (una sola vez).
SEED_PLANES = [
    # EJEMPLOS — borra/ajusta y deja TUS 10
    # {
    #     "sector": "Tamarindo",
    #     "indole": "Operativo",
    #     "actividad_estrategica": "Despliegue de operativos nocturnos en puntos de interés para reforzar vigilancia y disuasión del delito.",
    #     "indicador": "Cantidad de operativos policiales",
    #     "meta_total": 184,
    #     "responsable": "Jefe de delegación policial de Santa Cruz",
    #     "actores": "Fuerza Pública",
    #     "zona_trabajo": "Tamarindo",
    #     "fecha_inicio": None, "fecha_fin": None,
    # },
    # {
    #     "sector": "Flamingo",
    #     "indole": "Operativo",
    #     "actividad_estrategica": "Despliegue de operativos nocturnos en puntos de interés para reforzar vigilancia y disuasión del delito.",
    #     "indicador": "Cantidad de operativos policiales",
    #     "meta_total": 184,
    #     "responsable": "Jefe de delegación policial de Santa Cruz",
    #     "actores": "Fuerza Pública",
    #     "zona_trabajo": "Flamingo",
    #     "fecha_inicio": None, "fecha_fin": None,
    # },
    # ... agrega aquí el resto hasta completar tus 10 filas ...
]
# =======================================================================

# ================== 2) DB ==================
def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
    conn = get_conn()
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
        fecha_fin TEXT,
        -- Clave única SIN usar zona para evitar duplicar por lugar
        UNIQUE (sector, indole, indicador, actividad_estrategica, meta_total, responsable)
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
    conn.commit()

    # si hay seed en el código y la tabla está vacía, siembra
    if SEED_PLANES:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM planes;")
        if cur.fetchone()[0] == 0:
            cur.executemany("""
                INSERT OR IGNORE INTO planes
                (sector, indole, actividad_estrategica, indicador, meta_total, responsable, actores, zona_trabajo, fecha_inicio, fecha_fin)
                VALUES (:sector, :indole, :actividad_estrategica, :indicador, :meta_total, :responsable, :actores, :zona_trabajo, :fecha_inicio, :fecha_fin)
            """, SEED_PLANES)
            conn.commit()

    conn.close()

init_db()

# ================== 3) Helpers ==================
def fetch_planes(sector=None):
    conn = get_conn()
    if sector and sector != "Todos":
        df = pd.read_sql_query("SELECT * FROM planes WHERE sector = ? ORDER BY id", conn, params=(sector,))
    else:
        df = pd.read_sql_query("SELECT * FROM planes ORDER BY id", conn)
    conn.close()
    return df

def fetch_avance(plan_id: int) -> int:
    conn = get_conn()
    df = pd.read_sql_query("SELECT cantidad FROM avances WHERE plan_id = ?", conn, params=(plan_id,))
    conn.close()
    return int(df["cantidad"].sum()) if not df.empty else 0

def insertar_avance(plan_id: int, cantidad: int, fecha_reg: date, obs: str, usuario: str):
    conn = get_conn()
    conn.execute("""
        INSERT INTO avances (plan_id, cantidad, fecha, observaciones, registrado_por)
        VALUES (?, ?, ?, ?, ?)
    """, (plan_id, int(cantidad), str(fecha_reg), (obs or None), (usuario or None)))
    conn.commit()
    conn.close()

def insertar_planes_desde_df(df: pd.DataFrame):
    # Espera columnas: sector,indole,actividad_estrategica,indicador,meta_total,responsable,actores,zona_trabajo,fecha_inicio,fecha_fin
    req = ["sector","indole","actividad_estrategica","indicador","meta_total","responsable","actores","zona_trabajo"]
    faltantes = [c for c in req if c not in df.columns]
    if faltantes:
        raise ValueError(f"Faltan columnas: {faltantes}")
    df = df.copy()
    df["meta_total"] = pd.to_numeric(df["meta_total"], errors="coerce").fillna(0).astype(int)
    df = df[df["meta_total"] > 0]
    if "fecha_inicio" not in df.columns: df["fecha_inicio"] = None
    if "fecha_fin" not in df.columns: df["fecha_fin"] = None
    conn = get_conn()
    conn.executemany("""
        INSERT OR IGNORE INTO planes
        (sector, indole, actividad_estrategica, indicador, meta_total, responsable, actores, zona_trabajo, fecha_inicio, fecha_fin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, df[["sector","indole","actividad_estrategica","indicador","meta_total","responsable","actores","zona_trabajo","fecha_inicio","fecha_fin"]].values.tolist())
    conn.commit()
    conn.close()

# ================== 4) UI ==================
st.title("📋 Registro de avances")

# Si no hay planes, mostrar un cargador rápido (sin Excel): pegar CSV y crear los 10
df_planes_existentes = fetch_planes()
if df_planes_existentes.empty:
    with st.expander("➕ Cargar los 10 planes (pegar CSV aquí)"):
        st.caption("Formato esperado: sector,indole,actividad_estrategica,indicador,meta_total,responsable,actores,zona_trabajo[,fecha_inicio][,fecha_fin]")
        ejemplo = (
            "sector,indole,actividad_estrategica,indicador,meta_total,responsable,actores,zona_trabajo,fecha_inicio,fecha_fin\n"
            "Tamarindo,Operativo,Despliegue de operativos nocturnos...,Cantidad de operativos policiales,184,Jefe de delegación policial de Santa Cruz,Fuerza Pública,Tamarindo,,\n"
            "Flamingo,Operativo,Despliegue de operativos nocturnos...,Cantidad de operativos policiales,184,Jefe de delegación policial de Santa Cruz,Fuerza Pública,Flamingo,,\n"
            "Tamarindo,Operativo,Coordinación y ejecución de operativos interinstitucionales...,Cantidad de operativos policiales,24,Sub Director Regional,Fuerza Pública; Tránsito; Migración; Turística; DIAC,Tamarindo, , \n"
            "Tamarindo,Gestión administrativa,Oficios para asignar recurso humano y transporte...,Cantidad de oficios emitidos,1,Director Regional,Fuerza Pública,Tamarindo,,\n"
            "Santa Cruz,Preventivo,Charlas preventivas y acercamiento comunitario...,Cantidad de actividades preventivas realizadas,6,Director Regional,Fuerza Pública,Santa Cruz,,\n"
            "----- agrega aquí tus 5 filas restantes (hasta 10 en total) -----"
        )
        csv_text = st.text_area("Pega aquí el CSV (10 filas)", value=ejemplo, height=220)
        if st.button("Cargar planes", type="primary"):
            try:
                df_in = pd.read_csv(StringIO(csv_text))
                insertar_planes_desde_df(df_in)
                st.success(f"Se cargaron {len(df_in)} planes ✅")
                st.experimental_rerun()
            except Exception as e:
                st.error(f"Error al cargar: {e}")
    st.stop()

# Filtro por sector
conn = get_conn()
sectores_db = pd.read_sql_query("SELECT DISTINCT sector FROM planes ORDER BY sector", conn)
conn.close()
sectores = ["Todos"] + sectores_db["sector"].tolist()

col_f1, col_f2 = st.columns([1, 2])
sector_sel = col_f1.selectbox("Sector", sectores, index=0)

df_planes = fetch_planes(None if sector_sel == "Todos" else sector_sel)
if df_planes.empty:
    st.info("No hay planes para este sector.")
    st.stop()

# Tabla 1 fila = 1 plan
st.markdown("### 📑 Planes disponibles")
tabla = df_planes[["id","sector","indicador","meta_total","responsable","zona_trabajo"]].rename(columns={
    "id":"ID","sector":"Sector","indicador":"Indicador","meta_total":"Meta","responsable":"Responsable","zona_trabajo":"Zona(s) de trabajo"
})
st.dataframe(tabla, use_container_width=True, hide_index=True)

# Selección por ID (compacta)
ids = df_planes["id"].tolist()
plan_id = col_f2.selectbox(
    "Selecciona un plan por ID",
    options=ids,
    format_func=lambda i: f"ID {i} – {df_planes.loc[df_planes['id']==i, 'indicador'].values[0]}",
)
plan = df_planes[df_planes["id"] == plan_id].iloc[0]

# Resumen del avance
acumulado = fetch_avance(int(plan["id"]))
meta = int(plan["meta_total"])
porcentaje = min(100, round((acumulado * 100.0) / meta, 2)) if meta else 0

st.markdown("### 📌 Resumen del avance")
m1, m2, m3, m4 = st.columns(4)
m1.metric("Meta total", meta)
m2.metric("Acumulado", acumulado)
m3.metric("Restante", max(0, meta - acumulado))
m4.metric("% Avance", f"{porcentaje}%")
st.progress(int(porcentaje))

# Detalles limpios
st.markdown("### 🧾 Detalles del plan")
d1, d2 = st.columns(2)
with d1:
    st.markdown(f"**Sector:** {plan['sector']}")
    st.markdown(f"**Índole:** {plan['indole']}")
    st.markdown(f"**Indicador:** {plan['indicador']}")
    st.markdown(f"**Responsable:** {plan['responsable']}")
with d2:
    st.markdown(f"**Actores involucrados:** {plan['actores']}")
    st.markdown(f"**Zona(s) de trabajo:** {plan['zona_trabajo']}")
    periodo = f"{plan['fecha_inicio'] or ''} - {plan['fecha_fin'] or ''}"
    st.markdown(f"**Periodo:** {periodo}")
st.markdown("**Actividad estratégica:**")
st.write(plan["actividad_estrategica"])

# Registro de avances (evitando superar la meta)
st.markdown("### ➕ Registrar avance")
c1, c2, c3 = st.columns([1, 1, 2])
cantidad = c1.number_input("Cantidad realizada", min_value=1, value=1, step=1)
fecha_reg = c2.date_input("Fecha", value=date.today())
usuario = c3.text_input("Registrado por (opcional)")
obs = st.text_area("Observaciones (opcional)")

if acumulado + cantidad > meta:
    st.warning(f"Este registro superaría la meta ({acumulado}+{cantidad} > {meta}). Ajusta la cantidad.")

if st.button("Guardar avance", type="primary"):
    try:
        if acumulado + cantidad > meta:
            st.error("No se guardó porque sobrepasa la meta.")
        else:
            insertar_avance(int(plan["id"]), cantidad, fecha_reg, obs, usuario)
            st.success("Avance registrado ✅")
            st.experimental_rerun()
    except Exception as e:
        st.error(f"Error al guardar: {e}")

# Historial
st.markdown("### 🧾 Historial del plan")
conn = get_conn()
hist = pd.read_sql_query(
    "SELECT fecha, cantidad, registrado_por AS usuario, observaciones FROM avances WHERE plan_id = ? ORDER BY id DESC",
    conn, params=(int(plan["id"]),),
)
conn.close()
st.dataframe(hist, use_container_width=True, hide_index=True)
