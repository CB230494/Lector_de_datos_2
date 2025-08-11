import streamlit as st
import pandas as pd
from io import BytesIO

st.subheader("📈 Avances por meta (10 filas)")

# Metas según la tabla de tu imagen
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

st.markdown("Ingresa el **avance acumulado** de cada meta (acciones realizadas). El **límite** es la meta total.")

# --- Entradas de avance (sin texto aún, para evitar llaves duplicadas) ---
avances = []
for _, r in df_base.iterrows():
    # preparar estados iniciales
    st.session_state.setdefault(f"av_{int(r.fila)}", 0)
    st.session_state.setdefault(f"nota_{int(r.fila)}", "")

    avance = st.number_input(
        f"{r.actividad} (límite {int(r.meta_total)})",
        min_value=0, max_value=int(r.meta_total), step=1,
        value=st.session_state[f"av_{int(r.fila)}"],
        key=f"av_{int(r.fila)}"
    )
    avances.append(avance)

# --- Cálculos ---
df = df_base.copy()
df["avance"] = avances
df["pendiente"] = (df["meta_total"] - df["avance"]).clip(lower=0)
df["porcentaje_num"] = ((df["avance"] / df["meta_total"]) * 100).round(1)
df["porcentaje"] = df["porcentaje_num"].map(lambda x: f"{x:.1f}%")
df["estado"] = df["porcentaje_num"].apply(lambda x: "Completa" if x >= 100 else ("En curso" if x > 0 else "Pendiente"))
df["respaldo"] = [st.session_state.get(f"nota_{int(f)}", "") for f in df["fila"]]

# --- Vista rápida con % y vista previa del respaldo ---
df_preview = df.copy()
df_preview["respaldo_preview"] = df_preview["respaldo"].apply(lambda t: (t[:80] + "…") if len(t) > 80 else t)
st.dataframe(
    df_preview[["actividad", "meta_total", "avance", "pendiente", "porcentaje", "estado", "respaldo_preview"]],
    use_container_width=True
)

# --- Resumen interactivo con burbuja y botón Guardar ---
st.markdown("#### Resumen interactivo (haz clic en el número de **avance** para ver/agregar respaldo)")
for _, r in df.iterrows():
    c1, c2, c3, c4, c5, c6 = st.columns([4, 1, 1.1, 1.1, 1.2, 1.6])
    with c1:
        st.markdown(f"**{r['actividad']}**")
    with c2:
        st.caption("límite")
        st.write(int(r["meta_total"]))
    with c3:
        st.caption("avance")
        # El número abre el popover
        with st.popover(f"{int(r['avance'])}"):
            st.markdown(f"**Respaldo — {r['actividad']}**")
            # ÚNICO text_area por fila (evita el error de llaves duplicadas)
            _ = st.text_area(
                "Describe lo realizado (opcional)",
                key=f"nota_{int(r['fila'])}",
                placeholder="Agrega notas o evidencia cualitativa...",
                height=120
            )
            # Botón Guardar (guarda en session_state)
            if st.button("Guardar", key=f"save_{int(r['fila'])}"):
                # El binding del text_area ya actualizó session_state; solo notificamos
                if hasattr(st, "toast"):
                    st.toast("Respaldo guardado", icon="✅")
                else:
                    st.success("Respaldo guardado")
    with c4:
        st.caption("pendiente")
        st.write(int(r["pendiente"]))
    with c5:
        st.caption("porcentaje")
        st.write(r["porcentaje"])
    with c6:
        st.caption("estado")
        st.write(r["estado"])
    st.divider()

# --- Métrica global ---
avance_total_pct = (df["avance"].sum() / df["meta_total"].sum()) * 100 if df["meta_total"].sum() else 0
st.metric("Avance total (todas las metas)", f"{avance_total_pct:.1f}%")

# --- Descargar Excel con respaldo completo ---
buffer = BytesIO()
df_export = df[["actividad", "meta_total", "avance", "pendiente", "porcentaje", "estado", "respaldo"]].copy()
df_export.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button(
    "📥 Descargar desglose en Excel",
    buffer,
    file_name="avance_por_meta_con_respaldo.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)




