import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
import io

st.set_page_config(page_title="Configuratore Attuatore + Riduttore", layout="centered")
st.title("⚙️ Configuratore Attuatore con Curve Motori e Riduttore")

# Upload file
ciclo_file = st.file_uploader("📄 Ciclo di lavoro (.xlsx)", type=["xlsx"])
viti_file = st.file_uploader("🔩 Database viti (.xlsx)", type=["xlsx"])
motori_file = st.file_uploader("⚙️ Database motori (.xlsx)", type=["xlsx"])
riduttori_file = st.file_uploader("🔻 Database riduttori (.xlsx)", type=["xlsx"])
curve_folder = st.file_uploader("📈 Curve motori (uno o più .xlsx)", type=["xlsx"], accept_multiple_files=True)

if st.button("Calcola") and all([ciclo_file, viti_file, motori_file, riduttori_file]) and len(curve_folder) > 0:
    df_ciclo = pd.read_excel(ciclo_file)
    df_viti = pd.read_excel(viti_file)
    df_motori = pd.read_excel(motori_file)
    df_riduttori = pd.read_excel(riduttori_file)

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
    rpm_vite = (velocita_media / passo) * 60
    torque_vite = Feq * passo / (2 * np.pi * 0.9)

    st.success(f"✅ Vite selezionata: {vite['codice']}")
    st.write(f"**RPM vite richiesti:** {rpm_vite:.0f} rpm")
    st.write(f"**Coppia richiesta su vite:** {torque_vite:.2f} Nm")

    st.subheader("🔻 Selezione Riduttore")
    riduttori_validi = []
    for _, row in df_riduttori.iterrows():
        rpm_motore = rpm_vite * row["rapporto"]
        coppia_motore = torque_vite / (row["rapporto"] * row["rendimento"])
        riduttori_validi.append({
            "codice": row["codice"],
            "rapporto": row["rapporto"],
            "rendimento": row["rendimento"],
            "rpm_motore": rpm_motore,
            "torque_motore": coppia_motore
        })

    df_r_validi = pd.DataFrame(riduttori_validi)
    st.dataframe(df_r_validi)

    # Verifica curve motore per ogni riduttore
    st.subheader("📈 Verifica compatibilità motori per ogni riduttore")
    for idx, rid in df_r_validi.iterrows():
        st.markdown(f"**Riduttore {rid['codice']}** - Motore: {rid['rpm_motore']:.0f} rpm, {rid['torque_motore']:.2f} Nm")
        compatibili = []
        for file in curve_folder:
            curva = pd.read_excel(file)
            nome = os.path.splitext(file.name)[0]
            try:
                t_nom = np.interp(rid["rpm_motore"], curva["rpm"], curva["coppia_nominale"])
                t_max = np.interp(rid["rpm_motore"], curva["rpm"], curva["coppia_massima"])
                if t_max >= rid["torque_motore"]:
                    compatibili.append((nome, t_nom, t_max))
            except:
                continue
        if compatibili:
            for mot in compatibili:
                st.write(f"✅ {mot[0]} - Coppia nominale {mot[1]:.1f} Nm, Max {mot[2]:.1f} Nm")
        else:
            st.warning("❌ Nessun motore compatibile per questo riduttore.")

    # Grafico
    st.subheader("📊 Ciclo di lavoro")
    fig, ax = plt.subplots()
    ax.plot(df_ciclo["tempo"], df_ciclo["posizione"], label="Posizione (mm)")
    ax2 = ax.twinx()
    ax2.plot(df_ciclo["tempo"], df_ciclo["forza"], color="red", linestyle="--", label="Forza (N)")
    st.pyplot(fig)
