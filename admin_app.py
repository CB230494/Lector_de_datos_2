# admin_app.py — Dashboard (SQLite) — Planes ya vienen precargados
import streamlit as st
import pandas as pd
import sqlite3

st.set_page_config(page_title="Tablero Administrativo", layout="wide")

DB_PATH = "actividades.db"

def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

st.title("📊 Dashboard de avances")

# Asegura tablas (por si abre primero el admin)
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
dv = pd.read_sql_query(query, conn)
conn.close()

if dv.empty:
    st.info("Aún no hay datos. Asegúrate de abrir la app de usuarios al menos una vez para que precargue los planes y registrar avances.")
else:
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

    # Gráfico opcional
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
        st.info("Para ver el gráfico, agrega `matplotlib` en requirements.")

    st.download_button(
        "⬇ Descargar CSV",
        data=df_show.to_csv(index=False).encode("utf-8"),
        file_name="planes_avance.csv",
        mime="text/csv",
    )

