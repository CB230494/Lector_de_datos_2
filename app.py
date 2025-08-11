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

df = pd.DataFrame(metas)

st.markdown("Ingresa el **avance acumulado** de cada meta (número de acciones realizadas):")

# Captura de avances por cada fila
avances = []
for _, r in df.iterrows():
    avance = st.number_input(
        f"Fila {int(r.fila)} — {r.actividad}",
        min_value=0, max_value=int(r.meta_total), step=1, value=0, key=f"av_{int(r.fila)}"
    )
    avances.append(avance)

df["avance"] = avances
df["pendiente"] = (df["meta_total"] - df["avance"]).clip(lower=0)
df["porcentaje"] = ((df["avance"] / df["meta_total"]) * 100).round(1)
df["estado"] = df["porcentaje"].apply(lambda x: "Completa" if x >= 100 else ("En curso" if x > 0 else "Pendiente"))

st.dataframe(
    df[["fila", "actividad", "meta_total", "avance", "pendiente", "porcentaje", "estado"]],
    use_container_width=True
)

# Métrica global
avance_total_pct = (df["avance"].sum() / df["meta_total"].sum()) * 100 if df["meta_total"].sum() else 0
st.metric("Avance total (todas las metas)", f"{avance_total_pct:.1f}%")

# Descargar Excel con el desglose
buffer = BytesIO()
df.to_excel(buffer, index=False)
buffer.seek(0)
st.download_button(
    "📥 Descargar desglose en Excel",
    buffer,
    file_name="avance_por_meta.xlsx",
    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
)



