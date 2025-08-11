# admin_app.py — Tablero y gestión de planes (SQLite)
import streamlit as st
import pandas as pd
import sqlite3
from datetime import date

st.set_page_config(page_title="Tablero Administrativo", layout="wide")

DB_PATH = "actividades.db"

# ========== DB ==========
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def init_db():
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
    conn.commit()
    conn.close()

init_db()

# ===== Helpers =====
def crear_plan(data_tuple):
    conn = get_connection()
    conn.execute("""
        INSERT INTO planes (sector, indole, actividad_estrategica, indicador, meta_total, responsable, actores, zona_trabajo, fecha_inicio, fecha_fin)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, data_tuple)
    conn.commit()
    conn.close()

def actualizar_plan(plan_id, meta_total=None, responsable=None, actores=None, zona_trabajo=None):
    conn = get_connection()
    sets = []
    vals = []
    if meta_total is not None:
        sets.append("meta_total = ?"); vals.append(int(meta_total))
    if responsable is not None:
        sets.append("responsable = ?"); vals.append(responsable)
    if actores is not None:
        sets.append("actores = ?"); vals.append(actores)
    if zona_trabajo is not None:
        sets.append("zona_trabajo = ?"); vals.append(zona_trabajo)
    if sets:
        vals.append(int(plan_id))
        conn.execute(f"UPDATE planes SET {', '.join(sets)} WHERE id = ?", vals)
        conn.commit()
    conn.close()

def eliminar_plan(plan_id):
    conn = get_connection()
    conn.execute("DELETE FROM planes WHERE id = ?", (int(plan_id),))
    conn.commit()
    conn.close()

def get_planes():
    conn = get_connection()
    df = pd.read_sql_query("SELECT * FROM planes ORDER BY id DESC", conn)
    conn.close()
    return df

def get_dashboard_df():
    conn = get_connection()
    query = """
        SELECT 
            p.id, p.sector, p.indole, p.indicador, p.actividad_estrategica, 
            p.meta_total, p.responsable, p.actores, p.zona_trabajo,
            COALESCE(SUM(a.cantidad),0) AS acumulado,
            MIN(100, ROUND(COALESCE(SUM(a.cantidad),0) * 100.0 / p.meta_total, 2)) AS porcentaje
        FROM planes p
        LEFT JOIN avances a ON a.plan_id = p.id
        GROUP BY p.id
        ORDER BY p.id DESC
    """
    df = pd.read_sql_query(query, conn)
    conn.close()
    return df

# ===== Seguridad simple opcional (password en secrets) =====
ADMIN_PASSWORD = st.secrets.get("ADMIN_PASSWORD", "")
pwd = st.text_input("🔐 Contraseña de administrador", type="password") if ADMIN_PASSWORD else None
if ADMIN_PASSWORD and pwd != ADMIN_PASSWORD:
    st.warning("Ingresa la contraseña para continuar.")
    st.stop()

st.title("📊 Tablero Administrativo")

tab1, tab2, tab3 = st.tabs(["➕ Crear plan", "🛠 Gestionar planes", "📈 Dashboard"])

with tab1:
    st.subheader("Nuevo plan")
    colA, colB = st.columns(2)
    with colA:
        sector = st.text_input("Sector", value="Santa Teresa")
        indole = st.selectbox("Índole", ["Operativo", "Preventivo", "Gestión administrativa"])
        indicador = st.selectbox("Indicador", ["Operativos", "Informe realizado"])
        meta_total = st.number_input("Meta cuantitativa (total)", min_value=1, value=20, step=1)
        zona = st.text_input("Zona(s) de trabajo", value="Santa Teresa")
    with colB:
        responsable = st.text_input("Responsable", value="Dirección Regional")
        actores = st.text_input("Actores involucrados", value="Tránsito/Migración")
        actividad = st.text_area("Actividad estratégica", value="Coordinar esfuerzos interinstitucionales para prevenir y reducir el robo de motocicletas.")
        f_ini = st.date_input("Fecha inicio", value=date.today())
        f_fin = st.date_input("Fecha fin", value=None)

    if st.button("Crear plan", type="primary"):
        try:
            crear_plan((
                sector.strip(), indole, actividad.strip(), indicador,
                int(meta_total), responsable.strip(), actores.strip(),
                zona.strip(), str(f_ini), (str(f_fin) if f_fin else None)
            ))
            st.success("Plan creado ✅")
        except Exception as e:
            st.error(f"Error al crear el plan: {e}")

with tab2:
    st.subheader("Editar / Eliminar")
    df = get_planes()
    if df.empty:
        st.info("No hay planes.")
    else:
        st.dataframe(df[["id","sector","indicador","meta_total","responsable","actores","zona_trabajo"]], use_container_width=True)
        ids = df["id"].tolist()
        plan_id = st.selectbox("Selecciona un plan (ID)", ids)
        psel = df[df["id"] == plan_id].iloc[0]

        c1, c2, c3, c4 = st.columns(4)
        meta_edit = c1.number_input("Meta total", min_value=1, value=int(psel["meta_total"]))
        resp_edit = c2.text_input("Responsable", value=psel["responsable"])
        actores_edit = c3.text_input("Actores", value=psel["actores"])
        zona_edit = c4.text_input("Zona(s)", value=psel["zona_trabajo"])

        col_btn1, col_btn2 = st.columns(2)
        if col_btn1.button("💾 Guardar cambios"):
            try:
                actualizar_plan(plan_id, meta_edit, resp_edit, actores_edit, zona_edit)
                st.success("Cambios guardados ✅")
            except Exception as e:
                st.error(f"Error: {e}")

        if col_btn2.button("🗑 Eliminar plan", type="secondary"):
            try:
                eliminar_plan(plan_id)
                st.success("Plan eliminado ✅")
            except Exception as e:
                st.error(f"Error: {e}")

with tab3:
    st.subheader("Estado de avance")
    dv = get_dashboard_df()
    if dv.empty:
        st.info("No hay datos para mostrar.")
    else:
        # Filtros
        colF1, colF2 = st.columns(2)
        sectores = ["Todos"] + sorted(dv["sector"].dropna().unique().tolist())
        indicadores = ["Todos"] + sorted(dv["indicador"].dropna().unique().tolist())
        f_sector = colF1.selectbox("Sector", sectores)
        f_indic = colF2.selectbox("Indicador", indicadores)

        df_show = dv.copy()
        if f_sector != "Todos":
            df_show = df_show[df_show["sector"] == f_sector]
        if f_indic != "Todos":
            df_show = df_show[df_show["indicador"] == f_indic]

        meta_global = int(df_show["meta_total"].sum()) if not df_show.empty else 0
        acum_global = int(df_show["acumulado"].sum()) if not df_show.empty else 0
        pct_global = 0 if meta_global == 0 else round(min(100, acum_global * 100.0 / meta_global), 2)

        m1, m2, m3 = st.columns(3)
        m1.metric("Meta global", meta_global)
        m2.metric("Acumulado global", acum_global)
        m3.metric("Avance global", f"{pct_global}%")
        st.progress(int(pct_global))

        st.markdown("#### Avance por plan")
        st.dataframe(df_show[[
            "id","sector","indicador","actividad_estrategica","meta_total","acumulado","porcentaje","responsable","actores","zona_trabajo"
        ]], use_container_width=True)

        # Gráfico (opcional)
        try:
            import matplotlib.pyplot as plt
            chart_df = df_show.sort_values("porcentaje", ascending=False)[["indicador","porcentaje","sector"]]
            if not chart_df.empty:
                st.markdown("#### % de avance por plan")
                fig = plt.figure()
                plt.barh(chart_df["indicador"] + " – " + chart_df["sector"].astype(str), chart_df["porcentaje"])
                plt.xlabel("% avance"); plt.ylabel("Plan")
                st.pyplot(fig)
        except Exception:
            st.info("Si quieres el gráfico, agrega `matplotlib` en requirements.")

        st.download_button(
            "⬇ Descargar CSV",
            data=df_show.to_csv(index=False).encode("utf-8"),
            file_name="planes_avance.csv",
            mime="text/csv",
        )
