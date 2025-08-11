import sqlite3
from pathlib import Path
from datetime import datetime
import streamlit as st
import pandas as pd

st.set_page_config(page_title="Registro de Avance", page_icon="✅")

DB_PATH = Path("planes.db")

# ========= Catálogo pre-cargado (solo lectura) =========
PLANS = [
    {
        "id": 1,
        "indole": "Operativo",
        "actividad": "Coordinación y ejecución de operativos interinstitucionales nocturnos con enfoque en objetivos estratégicos",
        "zona": "Tamarindo, Flamingo, Brasilito, Potrero, Surfside",
        "indicador": "Cantidad de operativos policiales",
        "meta": 24,
        "responsable": "Sub Director Regional",
    },
    {
        "id": 2,
        "indole": "Operativo",
        "actividad": "Despliegue de operativos presenciales en horarios nocturnos en zonas de interés",
        "zona": "Tamarindo",
        "indicador": "Cantidad de operativos policiales",
        "meta": 184,
        "responsable": "Jefe delegación Santa Cruz",
    },
    {
        "id": 3,
        "indole": "Gestión administrativa",
        "actividad": "Gestión institucional mediante oficio para asignación de recurso humano y transporte",
        "zona": "Tamarindo",
        "indicador": "Cantidad de oficios emitidos",
        "meta": 1,
        "responsable": "Director Regional",
    },
    {
        "id": 4,
        "indole": "Operativo",
        "actividad": "Implementar plan de intervención interinstitucional en zona de bares para prevenir delitos y riñas",
        "zona": "Santa Teresa",
        "indicador": "Operativos",
        "meta": 2,
        "responsable": "Dirección Regional",
    },
]
PLAN_BY_ID = {p["id"]: p for p in PLANS}

# ========= Conexión =========
def conn():
    return sqlite3.connect(DB_PATH, check_same_thread=False)

def ensure_tables():
    with conn() as c:
        c.executescript("""
        PRAGMA foreign_keys = ON;
        CREATE TABLE IF NOT EXISTS activity_progress (
          plan_id INTEGER PRIMARY KEY,
          completadas INTEGER NOT NULL DEFAULT 0,
          updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS progress_log (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          plan_id INTEGER NOT NULL,
          delta INTEGER NOT NULL,
          prev_value INTEGER NOT NULL,
          new_value INTEGER NOT NULL,
          at TEXT NOT NULL,
          reportado_por TEXT,
          nota TEXT
        );
        """)
        c.commit()

def get_progress_map():
    with conn() as c:
        rows = c.execute("SELECT plan_id, completadas FROM activity_progress;").fetchall()
    return {pid: comp for pid, comp in rows}

def add_movement(plan_id: int, delta: int, reportado_por: str | None, nota: str | None):
    meta = PLAN_BY_ID[plan_id]["meta"]
    now = datetime.utcnow().isoformat()
    with conn() as c:
        row = c.execute("SELECT completadas FROM activity_progress WHERE plan_id=?;", (plan_id,)).fetchone()
        if row is None:
            prev = 0
            newv = max(0, min(meta, delta))
            c.execute(
                "INSERT INTO activity_progress (plan_id, completadas, updated_at) VALUES (?, ?, ?);",
                (plan_id, newv, now)
            )
        else:
            prev = int(row[0])
            newv = max(0, min(meta, prev + delta))
            c.execute(
                "UPDATE activity_progress SET completadas=?, updated_at=? WHERE plan_id=?;",
                (newv, now, plan_id)
            )
        # log
        c.execute(
            "INSERT INTO progress_log (plan_id, delta, prev_value, new_value, at, reportado_por, nota) VALUES (?, ?, ?, ?, ?, ?, ?);",
            (plan_id, int(delta), prev, newv, now, (reportado_por or None), (nota or None))
        )
        c.commit()

# ========= UI =========
st.title("✅ Registro de avance (sin usuarios)")

if not DB_PATH.exists():
    st.warning("Crea/abre 'planes.db' y ejecuta el SQL de esquema. Aun así intentaré crear tablas.")
ensure_tables()

# Resumen actual
progress_map = get_progress_map()
rows = []
for p in PLANS:
    hechas = int(progress_map.get(p["id"], 0))
    meta = int(p["meta"])
    pct = 0 if meta == 0 else round(100 * hechas / meta, 1)
    rows.append({
        "Plan ID": p["id"],
        "Actividad estratégica": p["actividad"],
        "Meta": meta,
        "Completadas": hechas,
        "Pendientes": meta - hechas,
        "% Avance": pct
    })
df = pd.DataFrame(rows)
st.subheader("Estado actual")
st.dataframe(df[["Plan ID","Actividad estratégica","Meta","Completadas","Pendientes","% Avance"]],
             use_container_width=True, hide_index=True)

meta_total = int(df["Meta"].sum())
hechas_total = int(df["Completadas"].sum())
pct_total = 0 if meta_total == 0 else round(100 * hechas_total / meta_total, 1)
st.metric("Avance total", f"{pct_total} %", help=f"{hechas_total} de {meta_total}")
st.progress(0 if meta_total==0 else min(1.0, hechas_total/meta_total))

st.divider()
st.subheader("Registrar movimiento")

opciones = {f"[{p['id']}] {p['actividad'][:70]}": p["id"] for p in PLANS}
plan_sel = st.selectbox("Actividad", list(opciones.keys()))
delta = st.number_input("¿Cuánto sumar (o restar)?", value=1, step=1, format="%d")
reportado_por = st.text_input("¿Quién reporta? (opcional)")
nota = st.text_input("Nota (opcional)")

colA, colB = st.columns(2)
with colA:
    if st.button("💾 Guardar movimiento"):
        try:
            add_movement(opciones[plan_sel], int(delta), reportado_por.strip() or None, nota.strip() or None)
            st.success("Movimiento registrado. Recarga para ver cambios.")
        except Exception as e:
            st.error(str(e))
with colB:
    st.caption("Tip: números negativos para correcciones (restar).")

st.markdown("### 🧾 Historial")
st.dataframe(get_historial(plan_id), use_container_width=True, hide_index=True)



