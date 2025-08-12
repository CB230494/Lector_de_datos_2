import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

st.subheader("📈 Avances por meta")

# ---- Metas base (meta_total original) ----
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

# ---- Inicializar estado ----
for _, r in df_base.iterrows():
    f = int(r.fila)
    st.session_state.setdefault(f"meta_total_{f}", int(r.meta_total))       # meta original
    st.session_state.setdefault(f"avance_{f}", 0)                           # acumulado
    st.session_state.setdefault(f"restante_{f}", int(r.meta_total))         # restante
    st.session_state.setdefault(f"nota_{f}", "")                            # notas consolidadas
    st.session_state.setdefault(f"hist_{f}", [])                            # historial de movimientos
    st.session_state.setdefault(f"mov_str_{f}", "")                         # input de movimiento (texto)
    st.session_state.setdefault(f"nota_inline_{f}", "")                     # nota del movimiento



def parse_mov(s: str) -> int | None:
    s = (s or "").strip().replace(" ", "")
    if s == "":
        return None
    try:
        return int(s)  # acepta "+2", "2", "-3"
    except ValueError:
        return None

# ---- UI por fila: movimiento ± y guardar ----
for _, r in df_base.iterrows():
    f = int(r.fila)
    colA, colB = st.columns([2.2, 1])
    with colA:
        st.markdown(f"**{r.actividad}**  \nMeta original: **{st.session_state[f'meta_total_{f}']}**")
    with colB:
        st.metric("Límite restante", st.session_state[f"restante_{f}"])

    c1, c2, c3 = st.columns([1.1, 2, 1])
    with c1:
        st.text_input(
            "Movimiento (±)",
            key=f"mov_str_{f}",
            placeholder="+2 o -2",
            help="Ej.: +2 descuenta del restante; -2 devuelve al restante."
        )
    with c2:
        st.text_input(
            "Nota del movimiento (opcional)",
            key=f"nota_inline_{f}",
            placeholder="Breve descripción…"
        )
    with c3:
        if st.button("Guardar movimiento", key=f"guardar_{f}"):
            mov = parse_mov(st.session_state[f"mov_str_{f}"])
            if mov is None:
                st.warning("Ingrese un movimiento válido (ej.: +2 o -2).")
            else:
                meta_total = st.session_state[f"meta_total_{f}"]
                avance    = st.session_state[f"avance_{f}"]

                # Aplica con límites 0..meta_total
                nuevo_avance = max(0, min(meta_total, avance + mov))
                delta_real = nuevo_avance - avance  # por si hubo tope
                st.session_state[f"avance_{f}"] = nuevo_avance
                st.session_state[f"restante_{f}"] = meta_total - nuevo_avance

                # Guardar en historial
                nota_mov = st.session_state[f"nota_inline_{f}"].strip()
                st.session_state[f"hist_{f}"].append({
                    "fecha": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "movimiento": delta_real,
                    "nota": nota_mov
                })
                # Anexar también a las notas consolidadas (opcional)
                if nota_mov:
                    prefix = f"• (+{delta_real}) " if delta_real > 0 else (f"• ({delta_real}) " if delta_real < 0 else "• ")
                    st.session_state[f"nota_{f}"] += (("\n" if st.session_state[f"nota_{f}"] else "") +
                                                      prefix + nota_mov)

                # Reset de los inputs (no queda “estático”)
                st.session_state[f"mov_str_{f}"] = ""
                st.session_state[f"nota_inline_{f}"] = ""

                if hasattr(st, "toast"):
                    st.toast("Movimiento guardado", icon="✅")
                else:
                    st.success("Movimiento guardado")

    st.divider()

# ---- Construye DataFrame de salida ----
rows = []
for _, r in df_base.iterrows():
    f = int(r.fila)
    meta_total = st.session_state[f"meta_total_{f}"]
    avance = st.session_state[f"avance_{f}"]
    restante = st.session_state[f"restante_{f}"]
    pct = round((avance / meta_total) * 100, 1) if meta_total else 0.0
    estado = "Completa" if pct >= 100 else ("En curso" if avance > 0 else "Pendiente")
    rows.append({
        "fila": f,
        "actividad": r.actividad,
        "meta_total": meta_total,
        "avance": avance,
        "limite_restante": restante,
        "porcentaje": f"{pct:.1f}%",
        "estado": estado,
        "respaldo": st.session_state[f"nota_{f}"],
    })

df = pd.DataFrame(rows)

# ---- Tabla resumen ----
st.dataframe(df[["actividad", "meta_total", "avance", "limite_restante", "porcentaje", "estado"]],
             use_container_width=True)

# ---- Burbuja para respaldo + historial al hacer clic en el avance ----
st.markdown("#### Resumen interactivo (clic en el **avance** para ver/editar respaldo e historial)")
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
            st.markdown(f"**Respaldo — {r['actividad']}**")
            st.text_area(
                "Notas consolidadas (puedes editar)",
                key=f"nota_{f}",
                height=150
            )
            # Historial de movimientos
            hist = st.session_state.get(f"hist_{f}", [])
            if hist:
                st.markdown("**Historial de movimientos**")
                st.table(pd.DataFrame(hist))
            if st.button("Guardar notas", key=f"save_notas_{f}"):
                st.success("Notas guardadas")
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
# Convierte historial a texto legible para exportar
df_export = df.copy()
hist_cols = []
for _, r in df.iterrows():
    f = int(r["fila"])
    h = st.session_state.get(f"hist_{f}", [])
    hist_cols.append("; ".join([f"{i['fecha']} {i['movimiento']} ({i['nota']})" if i['nota'] else f"{i['fecha']} {i['movimiento']}" for i in h]))
df_export["historial"] = hist_cols
df_export.drop(columns=["fila"], inplace=True)
df_export.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button(
    "📥 Descargar desglose en Excel",
    buffer,
    file_name="avance_por_meta_movimientos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)





