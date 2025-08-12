# app.py
import streamlit as st
import pandas as pd
import sqlite3
from io import BytesIO
from datetime import datetime
from typing import List, Dict, Any

st.set_page_config(page_title="Avances por meta", layout="wide")
st.subheader("📈 Avances por meta")

# =========================
# 1) CONFIG DB & DATOS BASE
# =========================
DB_PATH = "avances.db"

METAS_BASE = [
    {"fila": 1,  "actividad": "Operativos interinstitucionales nocturnos",        "meta_total": 24},
    {"fila": 2,  "actividad": "Operativos presenciales nocturnos",                "meta_total": 184},
    {"fila": 3,  "actividad": "Gestión institucional (oficios)",                  "meta_total": 1},
    {"fila": 4,  "actividad": "Actividades cívico-policiales",                    "meta_total": 6},
    {"fila": 5,  "actividad": "Operativos mixtos nocturnos",                      "meta_total": 184},
    {"fila": 6,  "actividad": "Operativos interinstitucionales (control)",        "meta_total": 12},
    {"fila": 7,  "actividad": "Acciones preventivas en espacios públicos",        "meta_total": 12},
    {"fila": 8,  "actividad": "Talleres/capacitaciones seguridad comercial",      "meta_total": 1},
    {"fila": 9,  "actividad": "Operativos con análisis de inteligencia",          "meta_total": 6},
    {"fila": 10, "actividad": "Capacitaciones de Seguridad Comunitaria",          "meta_total": 1},
]

def get_conn():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.execute("PRAGMA journal_mode=WAL;")
    conn.execute("PRAGMA foreign_keys=ON;")
    return conn

def init_db():
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS metas (
            fila INTEGER PRIMARY KEY,
            actividad TEXT NOT NULL,
            meta_total INTEGER NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS movimientos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fila INTEGER NOT NULL,
            fecha TEXT NOT NULL,            -- formato DD-MM-YYYY
            cantidad INTEGER NOT NULL CHECK(cantidad >= 0),
            nota TEXT,
            delta INTEGER NOT NULL,         -- con signo
            FOREIGN KEY(fila) REFERENCES metas(fila)
        );
    """)
    conn.commit()
    # seed de metas si está vacío
    cur.execute("SELECT COUNT(*) FROM metas;")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO metas (fila, actividad, meta_total) VALUES (?, ?, ?);",
            [(m["fila"], m["actividad"], m["meta_total"]) for m in METAS_BASE]
        )
        conn.commit()
    conn.close()

init_db()

# =========================
# 2) CONSULTAS / ACCIONES DB
# =========================
def obtener_metas_df() -> pd.DataFrame:
    conn = get_conn()
    df = pd.read_sql_query("SELECT fila, actividad, meta_total FROM metas ORDER BY fila;", conn)
    conn.close()
    return df

def suma_delta_por_fila(fila: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT COALESCE(SUM(delta), 0) FROM movimientos WHERE fila=?;", (fila,))
    total = cur.fetchone()[0] or 0
    conn.close()
    return int(total)

def obtener_historial(fila: int) -> List[Dict[str, Any]]:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, fecha, cantidad, nota, delta
        FROM movimientos
        WHERE fila=?
        ORDER BY id ASC;
    """, (fila,))
    rows = cur.fetchall()
    conn.close()
    return [
        {"id": r[0], "fecha": r[1], "cantidad": int(r[2]), "nota": r[3] or "", "delta": int(r[4])}
        for r in rows
    ]

def meta_total_de_fila(fila: int) -> int:
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT meta_total FROM metas WHERE fila=?;", (fila,))
    row = cur.fetchone()
    conn.close()
    return int(row[0]) if row else 0

def insertar_movimiento(fila: int, mov: int, nota: str) -> bool:
    """
    Inserta un movimiento aplicando límites (0..meta_total).
    Guarda delta_real (con signo) y cantidad (valor absoluto). Devuelve True si insertó.
    """
    meta_total = meta_total_de_fila(fila)
    avance_actual = suma_delta_por_fila(fila)
    nuevo_avance = max(0, min(meta_total, avance_actual + int(mov)))
    delta_real = int(nuevo_avance - avance_actual)

    if delta_real == 0 and not (nota or "").strip():
        # No hay efecto y no hay nota -> no guarda nada
        return False

    fecha = datetime.now().strftime("%d-%m-%Y")
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO movimientos (fila, fecha, cantidad, nota, delta)
        VALUES (?, ?, ?, ?, ?);
    """, (fila, fecha, abs(delta_real), (nota or "").strip(), delta_real))
    conn.commit()
    conn.close()
    return True

def actualizar_movimiento(id_mov: int, fila: int, nueva_cant: int, nueva_nota: str):
    """
    Mantiene el signo original del movimiento. Recorta la cantidad para que
    la suma total (incluyendo este movimiento) quede dentro de 0..meta_total.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("SELECT delta FROM movimientos WHERE id=?;", (id_mov,))
    row = cur.fetchone()
    if not row:
        conn.close()
        return
    old_delta = int(row[0])
    sign = 1 if old_delta >= 0 else -1

    # Avance sin contar este movimiento
    cur.execute("SELECT COALESCE(SUM(delta),0) FROM movimientos WHERE fila=? AND id<>?;", (fila, id_mov))
    avance_sin = int(cur.fetchone()[0] or 0)

    meta_total = meta_total_de_fila(fila)
    nuevo_delta_deseado = sign * int(nueva_cant)

    min_allowed = -avance_sin                     # para no bajar de 0
    max_allowed = meta_total - avance_sin         # para no pasar la meta
    nuevo_delta = max(min_allowed, min(max_allowed, nuevo_delta_deseado))
    nueva_cant_recortada = abs(int(nuevo_delta))

    cur.execute("""
        UPDATE movimientos
        SET cantidad = ?, nota = ?, delta = ?
        WHERE id = ?;
    """, (nueva_cant_recortada, (nueva_nota or "").strip(), nuevo_delta, id_mov))
    conn.commit()
    conn.close()

def eliminar_movimiento(id_mov: int):
    conn = get_conn()
    cur = conn.cursor()
    cur.execute("DELETE FROM movimientos WHERE id=?;", (id_mov,))
    conn.commit()
    conn.close()

def obtener_resumen_df() -> pd.DataFrame:
    metas = obtener_metas_df()
    # Traer avances (sumas por fila)
    conn = get_conn()
    avances = pd.read_sql_query("""
        SELECT fila, COALESCE(SUM(delta),0) AS avance
        FROM movimientos
        GROUP BY fila;
    """, conn)
    conn.close()

    df = metas.merge(avances, on="fila", how="left").fillna({"avance": 0})
    df["avance"] = df["avance"].astype(int)
    df["limite_restante"] = df["meta_total"] - df["avance"]
    df["porcentaje_val"] = (df["avance"] / df["meta_total"] * 100).round(1)
    df["porcentaje"] = df["porcentaje_val"].map(lambda x: f"{x:.1f}%")
    df["estado"] = df.apply(
        lambda r: "Completa" if r["porcentaje_val"] >= 100 else ("En curso" if r["avance"] > 0 else "Pendiente"),
        axis=1
    )
    return df.sort_values("fila").reset_index(drop=True)

# ==================================
# 3) ESTADO DE UI (inputs por actividad)
# ==================================
if "reset_flags" not in st.session_state:
    st.session_state["reset_flags"] = {}

def set_reset_flag(fila: int, val: bool):
    st.session_state["reset_flags"][fila] = val

def get_reset_flag(fila: int) -> bool:
    return st.session_state["reset_flags"].get(fila, False)

def ensure_ui_keys_for_fila(fila: int):
    st.session_state.setdefault(f"mov_val_{fila}", 0)
    st.session_state.setdefault(f"nota_inline_{fila}", "")

# =========================
# 4) UI PRINCIPAL POR FILA
# =========================
df_base = obtener_metas_df()

for _, r in df_base.iterrows():
    f = int(r["fila"])
    ensure_ui_keys_for_fila(f)

    # si se marcó reset en el ciclo anterior, limpiar antes de dibujar widgets
    if get_reset_flag(f):
        st.session_state[f"mov_val_{f}"] = 0
        st.session_state[f"nota_inline_{f}"] = ""
        set_reset_flag(f, False)

    # datos actuales desde DB
    meta_total = int(r["meta_total"])
    avance = int(suma_delta_por_fila(f))
    restante = meta_total - avance

    colA, colB = st.columns([2.2, 1])
    with colA:
        st.markdown(f"**{r['actividad']}**  \nMeta original: **{meta_total}**")
    with colB:
        st.metric("Límite restante", restante)

    c1, c2, c3 = st.columns([1.1, 2.2, 1])
    with c1:
        st.number_input(
            "Movimiento",
            key=f"mov_val_{f}",
            step=1, format="%d",
            min_value=-meta_total,
            max_value= meta_total,
            help="− resta (avanza), + suma (devuelve). Empieza en 0."
        )
    with c2:
        st.text_input(
            "Nota del movimiento (opcional)",
            key=f"nota_inline_{f}",
            placeholder="Breve descripción…"
        )
    with c3:
        if st.button("Guardar movimiento", key=f"guardar_{f}"):
            mov = int(st.session_state[f"mov_val_{f}"])
            nota_mov = (st.session_state[f"nota_inline_{f}"] or "").strip()
            inserted = insertar_movimiento(f, mov, nota_mov)
            # marcar reset para limpiar inputs y refrescar
            set_reset_flag(f, True)
            st.rerun()

    st.divider()

# =========================
# 5) TABLA RESUMEN
# =========================
df = obtener_resumen_df()
st.dataframe(
    df[["actividad", "meta_total", "avance", "limite_restante", "porcentaje", "estado"]],
    use_container_width=True
)

# =========================
# 6) BURBUJAS: VER/EDITAR/ELIMINAR HISTORIAL
# =========================
st.markdown("#### Resumen interactivo (clic en el **avance** para ver/editar historial)")

for _, row in df.iterrows():
    f = int(row["fila"])
    c1, c2, c3, c4, c5, c6 = st.columns([4, 1.1, 1.1, 1.1, 1.2, 1.8])
    with c1:
        st.markdown(f"**{row['actividad']}**")
    with c2:
        st.caption("meta")
        st.write(int(row["meta_total"]))
    with c3:
        st.caption("límite restante")
        st.write(int(row["limite_restante"]))
    with c4:
        st.caption("avance")
        with st.popover(f"{int(row['avance'])}"):
            st.markdown(f"**Historial — {row['actividad']}**")

            hist = obtener_historial(f)
            if not hist:
                st.caption("Sin movimientos registrados aún.")
            else:
                # Vista simple del historial
                df_hist_view = pd.DataFrame([
                    {"Fecha": i["fecha"], "Cantidad": i["cantidad"], "Nota": i.get("nota", "")}
                    for i in hist
                ])
                st.table(df_hist_view)

                st.markdown("**Editar / eliminar**")
                # Controles por registro
                for item in hist:
                    id_mov = int(item["id"])
                    ec1, ec2, ec3, ec4 = st.columns([1, 1, 3, 1.2])
                    with ec1:
                        st.text_input("Fecha", value=item["fecha"], key=f"edit_fecha_{f}_{id_mov}", disabled=True)
                    with ec2:
                        nueva_cant = st.number_input(
                            "Cantidad", min_value=0, step=1,
                            value=int(item["cantidad"]),
                            key=f"edit_cant_{f}_{id_mov}"
                        )
                    with ec3:
                        nueva_nota = st.text_input(
                            "Nota", value=item.get("nota",""),
                            key=f"edit_nota_{f}_{id_mov}"
                        )
                    with ec4:
                        if st.button("💾 Guardar", key=f"save_edit_{f}_{id_mov}"):
                            actualizar_movimiento(id_mov, f, int(nueva_cant), nueva_nota)
                            st.rerun()

                        if st.button("🗑️ Eliminar", key=f"del_{f}_{id_mov}"):
                            eliminar_movimiento(id_mov)
                            st.rerun()

    with c5:
        st.caption("porcentaje")
        st.write(row["porcentaje"])
    with c6:
        st.caption("estado")
        st.write(row["estado"])
    st.divider()

# =========================
# 7) MÉTRICA GLOBAL
# =========================
meta_total_sum = int(df["meta_total"].sum())
avance_total = int(df["avance"].sum())
pct_total = (avance_total / meta_total_sum) * 100 if meta_total_sum else 0
st.metric("Avance total (todas las metas)", f"{pct_total:.1f}%")

# =========================
# 8) DESCARGAR EXCEL
# =========================
buffer = BytesIO()
# construir columna historial como texto "DD-MM-YYYY — cantidad — nota"
hist_texts = []
for _, r in df.iterrows():
    f = int(r["fila"])
    h = obtener_historial(f)
    hist_texts.append("; ".join([f"{i.get('fecha','')} — {i.get('cantidad',0)} — {i.get('nota','')}" for i in h]))

df_export = df[["fila", "actividad", "meta_total", "avance", "limite_restante", "porcentaje", "estado"]].copy()
df_export["historial"] = hist_texts
df_export.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button(
    "📥 Descargar desglose en Excel",
    buffer,
    file_name="avance_por_meta_movimientos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)
# =========================
# 9) 📊 Visualizaciones por meta (ocultas hasta seleccionar)
# =========================
st.markdown("### 📊 Visualizaciones por meta")

import matplotlib.pyplot as plt
import numpy as np

# Colores vivos
BLUE = "#1E88E5"   # azul intenso
RED  = "#E53935"   # rojo intenso

def _prep_fig():
    # Tema oscuro
    fig, ax = plt.subplots(figsize=(8, 4.5), facecolor="black")
    ax.set_facecolor("black")
    ax.tick_params(colors="white")
    ax.spines["bottom"].set_color("white")
    ax.spines["left"].set_color("white")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    ax.grid(axis="y", alpha=0.15, color="white")
    return fig, ax

# Opciones de metas
_df_opts = df[["fila", "actividad", "meta_total", "avance", "limite_restante", "porcentaje_val"]].copy()
_df_opts["op"] = _df_opts["fila"].astype(str) + " — " + _df_opts["actividad"]
placeholder = "— Selecciona una meta —"
options = [placeholder] + _df_opts["op"].tolist()

sel = st.selectbox("Elegí la meta a visualizar", options, index=0, key="sel_meta_uno")

# Si no hay selección válida, no mostramos nada
if sel == placeholder:
    st.info("Seleccioná una meta para mostrar el gráfico.")
else:
    fila_sel = int(_df_opts.loc[_df_opts["op"] == sel, "fila"].iloc[0])
    row_sel = df.loc[df["fila"] == fila_sel].iloc[0]

    meta = int(row_sel["meta_total"])
    avance = int(row_sel["avance"])
    restante = max(0, meta - avance)
    pct = float(row_sel["porcentaje_val"])  # 1 decimal

    tipo = st.radio("Tipo de gráfico", ["Barras", "Circular"], index=0, horizontal=True, key="tipo_uno_por_uno")

    if tipo == "Barras":
        fig, ax = _prep_fig()
        vals = [avance, restante]
        labels = ["Avance", "Restante"]
        x = np.arange(len(labels))
        width = 0.6

        # Sombra
        ax.bar(x + 0.03, vals, width=width, color="black", alpha=0.35, zorder=0)

        # Barras principales azul/rojo con borde blanco
        bars = ax.bar(
            x, vals, width=width, color=[BLUE, RED], alpha=0.95,
            edgecolor="white", linewidth=1.2, zorder=1
        )
        y_max = max(meta, max(vals), 1)
        ax.set_ylim(0, y_max * 1.15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, color="white")
        ax.set_ylabel("Cantidad", color="white")
        ax.set_title(f"{row_sel['actividad']} — Meta {meta}  |  Avance total: {pct:.1f}%", color="white")

        # Etiquetas (valor y % real con 1 decimal)
        for b, val in zip(bars, vals):
            perc = (val / meta * 100) if meta else 0.0
            ax.text(
                b.get_x() + b.get_width()/2, b.get_height() + (y_max * 0.03),
                f"{val}  ({perc:.1f}%)", ha="center", va="bottom", color="white", fontsize=10
            )

        st.pyplot(fig, clear_figure=True)

    elif tipo == "Circular":
        fig, ax = _prep_fig()
        datos = [max(avance, 0), max(restante, 0)]
        etiquetas = ["Avance", "Restante"]

        if sum(datos) == 0:
            datos, etiquetas = [1], ["Sin datos"]

        def autopct_fmt(p):
            return f"{p:.1f}%"

        wedges, texts, autotexts = ax.pie(
            datos,
            labels=etiquetas,
            autopct=autopct_fmt,
            startangle=90,
            colors=[BLUE, RED],
            shadow=True,  # sombreado
            wedgeprops=dict(edgecolor="white", linewidth=1.2)
        )
        for t in texts + autotexts:
            t.set_color("white")
        ax.axis("equal")
        ax.set_title(f"{row_sel['actividad']} — Meta {meta}  |  Avance total: {pct:.1f}%", color="white")

        st.pyplot(fig, clear_figure=True)











