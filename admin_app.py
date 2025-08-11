import sqlite3
from pathlib import Path
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Panel Admin", page_icon="📊", layout="wide")

DB_PATH = Path("planes.db")

# ===== Catálogo embebido (igual que app.py) =====
PLANS = [
    {"id":1,"indole":"Operativo","actividad":"Coordinación y ejecución de operativos interinstitucionales nocturnos con enfoque en objetivos estratégicos","zona":"Tamarindo, Flamingo, Brasilito, Potrero, Surfside","indicador":"Cantidad de operativos policiales","meta":24,"responsable":"Sub Director Regional"},
    {"id":2,"indole":"Operativo","actividad":"Despliegue de operativos presenciales en horarios nocturnos en zonas de interés","zona":"Tamarindo","indicador":"Cantidad de operativos policiales","meta":184,"responsable":"Jefe delegación Santa Cruz"},
    {"id":3,"indole":"Gestión administrativa","actividad":"Gestión institucional mediante oficio para asignación de recurso humano y transporte","zona":"Tamarindo","indicador":"Cantidad de oficios emitidos","meta":1,"responsable":"Director Regional"},
    {"id":4,"indole":"Operativo","actividad":"Implementar plan de intervención interinstitucional en zona de bares para prevenir delitos y riñas","zona":"Santa Teresa","indicador":"Operativos","meta":2,"responsable":"Dirección Regional"},
]
PLAN_BY_ID = {p["id"]: p for p in PLANS}

def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

if not DB_PATH.exists():
    st.error("No encuentro 'planes.db'. Crea/abre la base y ejecuta el SQL de esquema.")
    st.stop()

st.title("📊 Panel administrativo (sin usuarios)")

with conn() as c:
    prog = c.execute("SELECT plan_id, completadas, updated_at FROM activity_progress;").fetchall()
    logs = c.execute("""
        SELECT id, at, plan_id, delta, prev_value, new_value, reportado_por, nota
        FROM progress_log ORDER BY at DESC, id DESC;
    """).fetchall()

# ---- Resumen por actividad ----
progress_map = {pid: comp for (pid, comp, _) in prog}
det_rows = []
meta_total_global = 0
hechas_global = 0

for p in PLANS:
    hechas = int(progress_map.get(p["id"], 0))
    meta = int(p["meta"])
    meta_total_global += meta
    hechas_global += hechas
    det_rows.append({
        "Plan ID": p["id"],
        "Índole": p["indole"],
        "Actividad estratégica": p["actividad"],
        "Meta": meta,
        "Completadas": hechas,
        "Pendientes": meta - hechas,
        "% Avance": (0 if meta==0 else round(100 * hechas / meta, 1))
    })
df_det = pd.DataFrame(det_rows)

st.subheader("Avance por actividad")
st.dataframe(df_det, use_container_width=True, hide_index=True)

st.subheader("Indicadores globales")
pct_global = 0 if meta_total_global==0 else round(100 * hechas_global / meta_total_global, 1)
k1, k2, k3 = st.columns(3)
k1.metric("Meta total global", f"{meta_total_global}")
k2.metric("Acciones realizadas", f"{hechas_global}")
k3.metric("Avance global", f"{pct_global} %")
st.progress(0 if meta_total_global==0 else min(1.0, hechas_global/meta_total_global))

# ---- Bitácora ----
st.subheader("Bitácora de movimientos")
log_rows = []
for (_id, at, pid, delta, prevv, newv, quien, nota) in logs:
    act = PLAN_BY_ID.get(pid, {"actividad": f"Plan {pid}"} )["actividad"]
    log_rows.append({
        "Fecha (UTC)": at,
        "Plan ID": pid,
        "Actividad": act,
        "Δ": delta,
        "Antes": prevv,
        "Ahora": newv,
        "Reportado por": quien or "",
        "Nota": nota or ""
    })
df_log = pd.DataFrame(log_rows)

# Filtros simples
c1, c2 = st.columns(2)
with c1:
    f_plan = st.multiselect("Filtrar por Plan ID", sorted(df_log["Plan ID"].unique()))
with c2:
    f_quien = st.text_input("Buscar en 'Reportado por'")

tmp = df_log.copy()
if f_plan:
    tmp = tmp[tmp["Plan ID"].isin(f_plan)]
if f_quien.strip():
    sub = f_quien.strip().lower()
    tmp = tmp[tmp["Reportado por"].str.lower().str.contains(sub, na=False)]

st.dataframe(tmp, use_container_width=True, hide_index=True)
