import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os

st.set_page_config(page_title="Configuratore Completo", layout="centered")
st.title("⚙️ Configuratore Attuatore - Ciclo, Vite, Riduttore, Motore")

# Upload
ciclo_file = st.file_uploader("📄 Carica ciclo posizione-tempo (.xlsx)", type=["xlsx"])
viti_file = st.file_uploader("🔩 Database viti (.xlsx)", type=["xlsx"])
motori_file = st.file_uploader("⚙️ Database motori (.xlsx)", type=["xlsx"])
riduttori_file = st.file_uploader("🔻 Database riduttori (.xlsx)", type=["xlsx"])
curve_folder = st.file_uploader("📈 Curve motori (.xlsx)", type=["xlsx"], accept_multiple_files=True)

corsa_totale_input = st.number_input("📏 Corsa totale attuatore (mm)", min_value=1.0, step=1.0)
limite_acc = st.number_input("⏱️ Limite accelerazione [mm/s²]", min_value=0.0, value=5000.0)
limite_jerk = st.number_input("⚡ Limite jerk [mm/s³]", min_value=0.0, value=50000.0)

if all([ciclo_file, viti_file, motori_file, riduttori_file, curve_folder]) and corsa_totale_input > 0:
    df = pd.read_excel(ciclo_file)
df.columns = [c.strip().lower() for c in df.columns]
    if not {'tempo', 'posizione', 'forza'}.issubset(df.columns):
        st.error("❌ Il file deve contenere colonne: 'tempo', 'posizione', 'forza'.")
        st.stop()

    df = df.sort_values("tempo")
    df["velocita"] = np.gradient(df["posizione"], df["tempo"])
    df["accelerazione"] = np.gradient(df["velocita"], df["tempo"])
    df["jerk"] = np.gradient(df["accelerazione"], df["tempo"])

    max_acc = df["accelerazione"].abs().max()
    max_jerk = df["jerk"].abs().max()

    st.subheader("📊 Analisi del ciclo")
    st.write(f"**Accelerazione max:** {max_acc:.1f} mm/s²  
**Jerk max:** {max_jerk:.1f} mm/s³")

    if max_acc > limite_acc:
        st.warning(f"⚠️ Accelerazione oltre limite: {max_acc:.1f} > {limite_acc}")
    if max_jerk > limite_jerk:
        st.warning(f"⚠️ Jerk oltre limite: {max_jerk:.1f} > {limite_jerk}")
    if max_acc <= limite_acc and max_jerk <= limite_jerk:
        st.success("✅ Profilo conforme a jerk e accelerazione.")

    fig, axs = plt.subplots(4, 1, figsize=(8, 10), sharex=True)
    axs[0].plot(df["tempo"], df["posizione"])
    axs[0].set_ylabel("Posizione [mm]")
    axs[1].plot(df["tempo"], df["velocita"])
    axs[1].set_ylabel("Velocità [mm/s]")
    axs[2].plot(df["tempo"], df["accelerazione"])
    axs[2].set_ylabel("Accelerazione [mm/s²]")
    axs[3].plot(df["tempo"], df["jerk"])
    axs[3].set_ylabel("Jerk [mm/s³]")
    axs[3].set_xlabel("Tempo [s]")
    st.pyplot(fig)

    # Calcoli meccanici
    Feq = (df["forza"]**3).mean()**(1/3)
    corsa_ciclo = df["posizione"].max() - df["posizione"].min()
    tempo_ciclo = df["tempo"].max() - df["tempo"].min()
    velocita_media = df["velocita"].mean()

    if corsa_totale_input < corsa_ciclo:
        st.error("❌ Corsa attuatore insufficiente.")
        st.stop()

    df_viti = pd.read_excel(viti_file)
    E = 2.1e5
    K = 2.0
    L = corsa_totale_input

    df_viti["I"] = (np.pi / 64) * df_viti["nocciolo"]**4
    df_viti["F_punta"] = (np.pi**2 * E * df_viti["I"]) / ((K * L)**2)
    df_viti["F_punta_amm"] = 0.8 * df_viti["F_punta"]
    df_viti["n_critica"] = 9.87 * df_viti["nocciolo"] / (L**2) * 1e6
    df_viti["n_max_ammissibile"] = 0.8 * df_viti["n_critica"]

    df_viti_filtrate = df_viti[
        (df_viti["C"] >= Feq * 1.2) &
        (df_viti["F_punta_amm"] >= Feq)
    ].copy()

    vite_valida = None
    for _, row in df_viti_filtrate.iterrows():
        rpm_operativi = (velocita_media / row["passo"]) * 60
        if rpm_operativi <= row["n_max_ammissibile"]:
            vite_valida = row
            break

    if vite_valida is None:
        st.error("❌ Nessuna vite idonea.")
        st.stop()

    st.success(f"✅ Vite selezionata: {vite_valida['codice']}")
    passo = vite_valida["passo"]
    rendimento_vite = vite_valida["rendimento"]
    torque_vite = Feq * passo / (2 * np.pi * rendimento_vite)

    # Vita utile
    L10 = (vite_valida["C"] / Feq)**3 * 1e6
    vita_cicli = L10 / corsa_ciclo if corsa_ciclo > 0 else 0
    vita_ore = (vita_cicli * tempo_ciclo) / 3600
    vita_anni = vita_ore / (16 * 365)
    st.write(f"**Vita utile stimata:** {vita_cicli:,.0f} cicli - {vita_anni:.1f} anni (16h/giorno)")

    # Riduttore
    df_riduttori = pd.read_excel(riduttori_file)
    df_riduttori = pd.concat([pd.DataFrame([{
        "codice": "Trasmissione Diretta",
        "rapporto": 1.0,
        "rendimento": 1.0
    }]), df_riduttori], ignore_index=True)

    rid_sel = st.selectbox("🔻 Seleziona riduttore", df_riduttori["codice"].tolist())
    rid_info = df_riduttori[df_riduttori["codice"] == rid_sel].iloc[0]
    rpm_motore = rpm_operativi * rid_info["rapporto"]
    torque_motore = torque_vite / (rid_info["rapporto"] * rid_info["rendimento"])

    st.write(f"**RPM motore:** {rpm_motore:.0f}, **Coppia richiesta:** {torque_motore:.2f} Nm")

    # Motori
    st.subheader("📈 Verifica motori compatibili")
    motori_validi = []
    for file in curve_folder:
        curva = pd.read_excel(file)
        nome = os.path.splitext(file.name)[0]
        try:
            t_nom = np.interp(rpm_motore, curva["rpm"], curva["coppia_nominale"])
            t_max = np.interp(rpm_motore, curva["rpm"], curva["coppia_massima"])
            if t_max >= torque_motore:
                motori_validi.append((nome, t_nom, t_max))
        except:
            continue

    if motori_validi:
        for mot in motori_validi:
            st.write(f"✅ {mot[0]} - Nominale {mot[1]:.1f} Nm, Massima {mot[2]:.1f} Nm")
    else:
        st.warning("❌ Nessun motore compatibile trovato.")
