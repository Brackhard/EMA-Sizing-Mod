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
        if st.button("▶️ Calcola"):

        df = pd.read_excel(ciclo_file)
        df.columns = [c.strip().lower() for c in df.columns]
        st.write("📋 Colonne caricate:", list(df.columns))
        if not {'tempo', 'posizione', 'forza'}.issubset(df.columns):
            st.error("❌ Il file deve contenere le colonne: 'tempo', 'posizione', 'forza'.")
            st.stop()

        df = df.sort_values("tempo")
        df["velocita"] = np.gradient(df["posizione"], df["tempo"])
        df["accelerazione"] = np.gradient(df["velocita"], df["tempo"])
        df["jerk"] = np.gradient(df["accelerazione"], df["tempo"])

        max_acc = df["accelerazione"].abs().max()
        max_jerk = df["jerk"].abs().max()

        st.subheader("📊 Analisi del ciclo")
        st.write(f"**Accelerazione max:** {max_acc:.1f} mm/s²  \n**Jerk max:** {max_jerk:.1f} mm/s³")

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