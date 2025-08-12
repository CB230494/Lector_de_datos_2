import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime
import sqlite3

# ===== Conexión existente =====
DB_PATH = r"C:\Users\Usuario\Desktop\Proyectos\Seguimiento Planes\avances.db"
CONN = sqlite3.connect(DB_PATH, check_same_thread=False)
CONN.execute("PRAGMA foreign_keys = ON")
print("DB usada:", CONN.execute("PRAGMA database_list").fetchall())
print("Movs totales:", CONN.execute("SELECT COUNT(*) FROM movimientos").fetchone()[0])

# ===== Helpers de BD =====
def db_insert_mov(fila, fecha, cantidad, delta, nota):
    cur = CONN.cursor()
    cur.execute(
        "INSERT INTO movimientos (fila, fecha, cantidad, delta, nota) VALUES (?,?,?,?,?)",
        (int(fila), fecha, int(cantidad), int(delta), nota),
    )
    CONN.commit()
    return cur.lastrowid

def db_update_mov(mov_id, cantidad, delta, nota):
    cur = CONN.cursor()
    cur.execute(
        "UPDATE movimientos SET cantidad=?, delta=?, nota=? WHERE id=?",
        (int(cantidad), int(delta), nota, int(mov_id)),
    )
    CONN.commit()

def db_delete_mov(mov_id):
    cur = CONN.cursor()
    cur.execute("DELETE FROM movimientos WHERE id=?", (int(mov_id),))
    CONN.commit()

def db_load_hist(fila):
    cur = CONN.cursor()
    cur.execute(
        "SELECT id, fecha, cantidad, delta, nota FROM movimientos WHERE fila=? ORDER BY id",
        (int(fila),)
    )
    rows = cur.fetchall()
    return [
        {"fecha": r[1], "cantidad": int(r[2]), "nota": r[4] or "", "delta": int(r[3]), "db_id": int(r[0])}
        for r in rows
    ]

def ensure_schema(conn, metas_seed):
    cur = conn.cursor()
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS metas (
      fila       INTEGER PRIMARY KEY,
      actividad  TEXT    NOT NULL,
      meta_total INTEGER NOT NULL CHECK (meta_total >= 0)
    );
    CREATE TABLE IF NOT EXISTS movimientos (
      id         INTEGER PRIMARY KEY AUTOINCREMENT,
      fila       INTEGER NOT NULL REFERENCES metas(fila) ON DELETE CASCADE ON UPDATE CASCADE,
      fecha      TEXT    NOT NULL,
      cantidad   INTEGER NOT NULL CHECK (cantidad >= 0),
      delta      INTEGER NOT NULL,
      nota       TEXT    DEFAULT '',
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE TABLE IF NOT EXISTS movimientos_log (
      log_id       INTEGER PRIMARY KEY AUTOINCREMENT,
      action       TEXT NOT NULL CHECK (action IN ('INSERT','UPDATE','DELETE')),
      id           INTEGER,
      fila         INTEGER,
      fecha        TEXT,
      cantidad_old INTEGER,
      cantidad_new INTEGER,
      delta_old    INTEGER,
      delta_new    INTEGER,
      nota_old     TEXT,
      nota_new     TEXT,
      action_at    DATETIME DEFAULT CURRENT_TIMESTAMP
    );
    CREATE INDEX IF NOT EXISTS idx_mov_fila ON movimientos(fila);

    CREATE TRIGGER IF NOT EXISTS movimientos_ai
    AFTER INSERT ON movimientos
    BEGIN
      INSERT INTO movimientos_log(action,id,fila,fecha,cantidad_new,delta_new,nota_new)
      VALUES('INSERT', NEW.id, NEW.fila, NEW.fecha, NEW.cantidad, NEW.delta, NEW.nota);
    END;

    CREATE TRIGGER IF NOT EXISTS movimientos_au
    AFTER UPDATE ON movimientos
    BEGIN
      INSERT INTO movimientos_log(action,id,fila,fecha,
                                  cantidad_old,cantidad_new,
                                  delta_old,delta_new,
                                  nota_old,nota_new)
      VALUES('UPDATE', NEW.id, NEW.fila, NEW.fecha,
             OLD.cantidad, NEW.cantidad,
             OLD.delta,    NEW.delta,
             OLD.nota,     NEW.nota);
    END;

    CREATE TRIGGER IF NOT EXISTS movimientos_ad
    AFTER DELETE ON movimientos
    BEGIN
      INSERT INTO movimientos_log(action,id,fila,fecha,cantidad_old,delta_old,nota_old)
      VALUES('DELETE', OLD.id, OLD.fila, OLD.fecha, OLD.cantidad, OLD.delta, OLD.nota);
    END;

    CREATE VIEW IF NOT EXISTS resumen_por_meta AS
    WITH s AS (
      SELECT m.fila, m.actividad, m.meta_total, COALESCE(SUM(t.delta),0) AS avance_raw
      FROM metas m
      LEFT JOIN movimientos t ON t.fila = m.fila
      GROUP BY m.fila, m.actividad, m.meta_total
    ),
    c AS (
      SELECT fila, actividad, meta_total,
             CASE WHEN avance_raw < 0 THEN 0
                  WHEN avance_raw > meta_total THEN meta_total
                  ELSE avance_raw END AS avance
      FROM s
    )
    SELECT
      fila,
      actividad,
      meta_total,
      avance,
      (meta_total - avance) AS limite_restante,
      (ROUND(100.0 * avance / meta_total, 1) || '%') AS porcentaje,
      CASE
        WHEN avance >= meta_total THEN 'Completa'
        WHEN avance > 0           THEN 'En curso'
        ELSE 'Pendiente'
      END AS estado
    FROM c
    ORDER BY fila;

    CREATE VIEW IF NOT EXISTS historial_por_meta AS
    SELECT id, fila, fecha, cantidad, nota, delta, created_at
    FROM movimientos
    ORDER BY fila, id;
    """)
    cur.execute("SELECT COUNT(*) FROM metas")
    if cur.fetchone()[0] == 0:
        cur.executemany(
            "INSERT INTO metas (fila, actividad, meta_total) VALUES (?, ?, ?)",
            [(m["fila"], m["actividad"], m["meta_total"]) for m in metas_seed]
        )
    conn.commit()

st.subheader("📈 Avances por meta")

# ---- Metas base ----
metas = [
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
df_base = pd.DataFrame(metas)
ensure_schema(CONN, metas)

# ---- Inicializar estado ----
for _, r in df_base.iterrows():
    f = int(r.fila)
    st.session_state.setdefault(f"meta_total_{f}", int(r.meta_total))
    st.session_state.setdefault(f"avance_{f}", 0)
    st.session_state.setdefault(f"restante_{f}", int(r.meta_total))
    # historial: [{fecha, cantidad, nota, delta, db_id}]
    st.session_state.setdefault(f"hist_{f}", [])
    st.session_state.setdefault(f"mov_val_{f}", 0)
    st.session_state.setdefault(f"nota_inline_{f}", "")
    st.session_state.setdefault(f"reset_mov_{f}", False)

# ---- Cargar historial una vez ----
st.session_state.setdefault("loaded_from_db", {})
for _, r in df_base.iterrows():
    f = int(r.fila)
    if not st.session_state["loaded_from_db"].get(f, False):
        hist_db = db_load_hist(f)
        if hist_db:
            st.session_state[f"hist_{f}"] = hist_db
            meta_total = st.session_state[f"meta_total_{f}"]
            suma = sum(i["delta"] for i in hist_db)
            avance_clamped = max(0, min(meta_total, suma))
            st.session_state[f"avance_{f}"] = avance_clamped
            st.session_state[f"restante_{f}"] = meta_total - avance_clamped
        st.session_state["loaded_from_db"][f] = True

# ---- UI por fila ----
for _, r in df_base.iterrows():
    f = int(r.fila)

    if st.session_state.get(f"reset_mov_{f}", False):
        st.session_state[f"mov_val_{f}"] = 0
        st.session_state[f"nota_inline_{f}"] = ""
        st.session_state[f"reset_mov_{f}"] = False

    colA, colB = st.columns([2.2, 1])
    with colA:
        st.markdown(f"**{r.actividad}**  \nMeta original: **{st.session_state[f'meta_total_{f}']}**")
    with colB:
        st.metric("Límite restante", st.session_state[f"restante_{f}"])

    c1, c2, c3 = st.columns([1.1, 2.2, 1])
    with c1:
        st.number_input(
            "Movimiento",
            key=f"mov_val_{f}",
            step=1, format="%d",
            min_value=-st.session_state[f"meta_total_{f}"],
            max_value= st.session_state[f"meta_total_{f}"],
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
            # ====== CAMBIO CLAVE: signo del movimiento ======
            mov_ui = int(st.session_state[f"mov_val_{f}"])
            mov = -mov_ui  # negativo en UI => avanzar; positivo => devolver

            meta_total = st.session_state[f"meta_total_{f}"]
            avance    = st.session_state[f"avance_{f}"]

            nuevo_avance = max(0, min(meta_total, avance + mov))
            delta_real = nuevo_avance - avance
            st.session_state[f"avance_{f}"] = nuevo_avance
            st.session_state[f"restante_{f}"] = meta_total - nuevo_avance

            nota_mov = (st.session_state[f"nota_inline_{f}"] or "").strip()
            cantidad = abs(int(delta_real))
            if nota_mov or cantidad > 0:
                item = {
                    "fecha": datetime.now().strftime("%d-%m-%Y"),
                    "cantidad": int(cantidad),
                    "nota": nota_mov,
                    "delta": int(delta_real),
                }
                new_id = db_insert_mov(f, item["fecha"], item["cantidad"], item["delta"], item["nota"])
                item["db_id"] = new_id
                st.session_state[f"hist_{f}"].append(item)

            st.session_state[f"reset_mov_{f}"] = True
            st.rerun()

    st.divider()

# ---- DataFrame resumen ----
rows = []
for _, r in df_base.iterrows():
    f = int(r.fila)
    meta_total = st.session_state[f"meta_total_{f}"]
    avance = st.session_state[f"avance_{f}"]
    restante = st.session_state[f"restante_{f}"]
    pct = round((avance / meta_total) * 100, 1) if meta_total else 0.0
    estado = "Completa" if pct >= 100 else ("En curso" if avance > 0 else "Pendiente")
    notas = [i.get("nota", "") for i in st.session_state.get(f"hist_{f}", []) if i.get("nota", "")]
    respaldo = " | ".join(notas)
    rows.append({
        "fila": f,
        "actividad": r.actividad,
        "meta_total": meta_total,
        "avance": avance,
        "limite_restante": restante,
        "porcentaje": f"{pct:.1f}%",
        "estado": estado,
        "respaldo": respaldo,
    })
df = pd.DataFrame(rows)

st.dataframe(
    df[["actividad", "meta_total", "avance", "limite_restante", "porcentaje", "estado"]],
    use_container_width=True
)

st.markdown("#### Resumen interactivo (clic en el **avance** para ver/editar historial)")
for _, r in df.iterrows():
    f = int(r["fila"])
    c1, c2, c3, c4, c5, c6 = st.columns([4, 1.1, 1.1, 1.1, 1.2, 1.8])
    with c1:
        st.markdown(f"**{r['actividad']}**")
    with c2:
        st.caption("meta")
        st.write(int(r["meta_total"]))
    with c3:
        st.caption("límite restante")
        st.write(int(r["limite_restante"]))
    with c4:
        st.caption("avance")
        with st.popover(f"{int(r['avance'])}"):
            st.markdown(f"**Historial — {r['actividad']}**")

            hist = st.session_state.get(f"hist_{f}", [])
            if not hist:
                st.caption("Sin movimientos registrados aún.")
            else:
                df_hist_view = pd.DataFrame([
                    {"Fecha": i["fecha"], "Cantidad": i["cantidad"], "Nota": i.get("nota", "")}
                    for i in hist
                ])
                st.table(df_hist_view)

                st.markdown("**Editar / eliminar**")
                for i, item in enumerate(hist):
                    ec1, ec2, ec3, ec4 = st.columns([1, 1, 3, 1.2])
                    with ec1:
                        st.text_input("Fecha", value=item["fecha"], key=f"edit_fecha_{f}_{i}", disabled=True)
                    with ec2:
                        nueva_cant = st.number_input(
                            "Cantidad", min_value=0, step=1,
                            value=int(item["cantidad"]),
                            key=f"edit_cant_{f}_{i}"
                        )
                    with ec3:
                        nueva_nota = st.text_input(
                            "Nota", value=item.get("nota",""),
                            key=f"edit_nota_{f}_{i}"
                        )
                    with ec4:
                        if st.button("💾 Guardar", key=f"save_edit_{f}_{i}"):
                            old_delta = int(item.get("delta", item["cantidad"]))
                            sign = 1 if old_delta >= 0 else -1
                            new_delta = sign * int(nueva_cant)

                            delta_diff = new_delta - old_delta
                            meta_total = st.session_state[f"meta_total_{f}"]
                            new_avance = max(0, min(meta_total, st.session_state[f"avance_{f}"] + delta_diff))
                            st.session_state[f"avance_{f}"] = new_avance
                            st.session_state[f"restante_{f}"] = meta_total - new_avance

                            item["cantidad"] = int(nueva_cant)
                            item["nota"] = nueva_nota
                            item["delta"] = int(new_delta)

                            mov_id = item.get("db_id", None)
                            if mov_id:
                                db_update_mov(mov_id, nueva_cant, new_delta, nueva_nota)

                            st.rerun()

                        if st.button("🗑️ Eliminar", key=f"del_{f}_{i}"):
                            old_delta = int(item.get("delta", item["cantidad"]))
                            meta_total = st.session_state[f"meta_total_{f}"]
                            new_avance = max(0, min(meta_total, st.session_state[f"avance_{f}"] - old_delta))
                            st.session_state[f"avance_{f}"] = new_avance
                            st.session_state[f"restante_{f}"] = meta_total - new_avance

                            mov_id = item.get("db_id", None)
                            if mov_id:
                                db_delete_mov(mov_id)

                            del st.session_state[f"hist_{f}"][i]
                            st.rerun()

    with c5:
        st.caption("porcentaje")
        st.write(r["porcentaje"])
    with c6:
        st.caption("estado")
        st.write(r["estado"])
    st.divider()

# ---- Métrica global ----
meta_total_sum = df["meta_total"].sum()
avance_total = df["avance"].sum()
pct_total = (avance_total / meta_total_sum) * 100 if meta_total_sum else 0
st.metric("Avance total (todas las metas)", f"{pct_total:.1f}%")

# ---- Descargar Excel ----
buffer = BytesIO()
df_export = df.drop(columns=["fila"]).copy()
hist_texts = []
for _, row in df.iterrows():
    f = int(row["fila"])
    h = st.session_state.get(f"hist_{f}", [])
    hist_texts.append("; ".join([f"{i.get('fecha','')} — {i.get('cantidad',0)} — {i.get('nota','')}" for i in h]))
df_export["historial"] = hist_texts
df_export.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button(
    "📥 Descargar desglose en Excel",
    buffer,
    file_name="avance_por_meta_movimientos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)









