import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import io

st.set_page_config(page_title="Configuratore Attuatore + Curve Motore", layout="centered")
st.title("⚙️ Configuratore Attuatore con Curve Motori")

# Upload file
ciclo_file = st.file_uploader("📄 Ciclo di lavoro (.xlsx)", type=["xlsx"])
viti_file = st.file_uploader("🔩 Database viti (.xlsx)", type=["xlsx"])
motori_file = st.file_uploader("⚙️ Database motori (.xlsx)", type=["xlsx"])
curve_folder = st.file_uploader("📈 Curve motori (uno o più .xlsx)", type=["xlsx"], accept_multiple_files=True)

if st.button("Calcola") and all([ciclo_file, viti_file, motori_file]) and len(curve_folder) > 0:
    df_ciclo = pd.read_excel(ciclo_file)
    df_viti = pd.read_excel(viti_file)
    df_motori = pd.read_excel(motori_file)

    df_ciclo["F3"] = df_ciclo["forza"]**3
    Feq = (df_ciclo["F3"].mean())**(1/3)
    corsa_per_ciclo = df_ciclo["posizione"].max() - df_ciclo["posizione"].min()
    tempo_ciclo = df_ciclo["tempo"].max() - df_ciclo["tempo"].min()
    velocita_media = df_ciclo["velocita"].mean()

    st.subheader("📊 Calcolo Carico Equivalente")
    st.write(f"**Carico equivalente:** {Feq:.2f} N")
    st.write(f"**Corsa per ciclo:** {corsa_per_ciclo:.0f} mm")
    st.write(f"**Durata ciclo:** {tempo_ciclo:.2f} s")

    # Selezione vite
    vite_sel = df_viti[df_viti["C"] >= Feq * 1.2].copy()
    vite_sel["L10"] = (vite_sel["C"] / Feq)**3 * 1e6

    if vite_sel.empty or corsa_per_ciclo == 0:
        st.error("❌ Nessuna vite idonea trovata o corsa nulla.")
        st.stop()

    vite = vite_sel.iloc[0]
    passo = float(vite["codice"].split("x")[-1])
    rpm_richiesti = (velocita_media / passo) * 60
    torque_richiesta = Feq * passo / (2 * np.pi * 0.9)

    st.success(f"✅ Vite selezionata: {vite['codice']}")
    st.write(f"**Velocità vite richiesta:** {rpm_richiesti:.0f} rpm")
    st.write(f"**Coppia richiesta:** {torque_richiesta:.2f} Nm")

    # Valutazione curve motori
    st.subheader("📈 Verifica compatibilità curve motore")
    motori_validi = []
    for file in curve_folder:
        try:
            curva = pd.read_excel(file)
            nome = os.path.splitext(file.name)[0]
            torque_nom = np.interp(rpm_richiesti, curva["rpm"], curva["coppia_nominale"])
            torque_max = np.interp(rpm_richiesti, curva["rpm"], curva["coppia_massima"])
            if torque_max >= torque_richiesta:
                motori_validi.append((nome, torque_nom, torque_max))
        except:
            st.warning(f"⚠️ Errore nel file curva: {file.name}")

    if motori_validi:
        st.success("✅ Motori compatibili trovati:")
        for mot in motori_validi:
            st.write(f"• {mot[0]} | Coppia max: {mot[2]:.1f} Nm | Coppia nom.: {mot[1]:.1f} Nm")
    else:
        st.error("❌ Nessun motore compatibile con le curve caricate.")

    # Grafico posizione e forza
    st.subheader("📊 Ciclo di lavoro")
    fig, ax = plt.subplots()
    ax.plot(df_ciclo["tempo"], df_ciclo["posizione"], label="Posizione (mm)")
    ax2 = ax.twinx()
    ax2.plot(df_ciclo["tempo"], df_ciclo["forza"], color="red", linestyle="--", label="Forza (N)")
    st.pyplot(fig)
