import streamlit as st
import pandas as pd
from io import BytesIO
from datetime import datetime

st.subheader("📈 Avances por meta (movimientos con − / + y notas)")

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
    st.session_state.setdefault(f"meta_total_{f}", int(r.meta_total))   # meta original
    st.session_state.setdefault(f"avance_{f}", 0)                       # acumulado
    st.session_state.setdefault(f"restante_{f}", int(r.meta_total))     # restante
    st.session_state.setdefault(f"nota_{f}", "")                        # notas consolidadas
    st.session_state.setdefault(f"mov_val_{f}", 0)                      # input de movimiento (número)
    st.session_state.setdefault(f"nota_inline_{f}", "")                 # nota del movimiento
    st.session_state.setdefault(f"reset_mov_{f}", False)                # flag de reseteo del input

st.markdown(
    "Usa los botones **− / +** para ajustar el **Movimiento**. "
    "Al **guardar**, se aplica al acumulado, se actualiza el **límite restante** y el campo vuelve a **0**."
)

# ---- UI por fila (manejo de reset ANTES de crear el widget) ----
for _, r in df_base.iterrows():
    f = int(r.fila)

    # Si se marcó reset en el ciclo anterior, limpiar antes de renderizar el widget
    if st.session_state.get(f"reset_mov_{f}", False):
        st.session_state[f"mov_val_{f}"] = 0
        st.session_state[f"nota_inline_{f}"] = ""
        st.session_state[f"reset_mov_{f}"] = False

    colA, colB = st.columns([2.2, 1])
    with colA:
        st.markdown(f"**{r.actividad}**  \nMeta original: **{st.session_state[f'meta_total_{f}']}**")
    with colB:
        st.metric("Límite restante", st.session_state[f"restante_{f}"])

    c1, c2, c3 = st.columns([1.1, 2, 1])
    with c1:
        # Movimiento con stepper − / +
        st.number_input(
            "Movimiento",
            key=f"mov_val_{f}",
            step=1,
            format="%d",
            min_value=-st.session_state[f"meta_total_{f}"],
            max_value= st.session_state[f"meta_total_{f}"],
            help="Usa − / + para restar o sumar al avance. El campo inicia en 0."
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
            meta_total = st.session_state[f"meta_total_{f}"]
            avance    = st.session_state[f"avance_{f}"]

            # Aplica dentro de 0..meta_total
            nuevo_avance = max(0, min(meta_total, avance + mov))
            delta_real = nuevo_avance - avance
            st.session_state[f"avance_{f}"] = nuevo_avance
            st.session_state[f"restante_{f}"] = meta_total - nuevo_avance

            # Notas consolidadas (solo texto; no mostramos fecha/hora en la UI)
            nota_mov = st.session_state[f"nota_inline_{f}"].strip()
            if nota_mov:
                sign = f"+{delta_real}" if delta_real > 0 else (f"{delta_real}" if delta_real < 0 else "0")
                bullet = f"• ({sign}) {nota_mov}" if delta_real != 0 else f"• {nota_mov}"
                st.session_state[f"nota_{f}"] += (("\n" if st.session_state[f"nota_{f}"] else "") + bullet)

            # marcar reset para limpiar a 0 en el próximo rerun
            st.session_state[f"reset_mov_{f}"] = True

            if hasattr(st, "toast"):
                st.toast("Movimiento guardado", icon="✅")
            else:
                st.success("Movimiento guardado")

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
st.dataframe(
    df[["actividad", "meta_total", "avance", "limite_restante", "porcentaje", "estado"]],
    use_container_width=True
)

# ---- Burbuja con SOLO notas (sin fecha/hora ni historial) ----
st.markdown("#### Resumen interactivo (clic en el **avance** para ver/editar notas)")
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
            st.markdown(f"**Notas — {r['actividad']}**")
            st.text_area(
                "Notas (solo texto)",
                key=f"nota_{f}",  # única por fila
                height=160,
                placeholder="Escribe o edita las notas de respaldo…"
            )
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
df_export = df.drop(columns=["fila"]).copy()
df_export.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button(
    "📥 Descargar desglose en Excel",
    buffer,
    file_name="avance_por_meta_movimientos.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)




