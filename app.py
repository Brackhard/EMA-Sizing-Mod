import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches
import os

st.title("⚙️ Configuratore Attuatore Elettromeccanico")

# --- Ciclo di lavoro ---
st.header("📈 Ciclo di lavoro")
ciclo_file = st.file_uploader("Carica ciclo di lavoro (xlsx con tempo, posizione)", type="xlsx")
if ciclo_file:
    ciclo_df = pd.read_excel(ciclo_file)
    if "tempo" in ciclo_df.columns and "posizione" in ciclo_df.columns:
        ciclo_df = ciclo_df.sort_values("tempo")
        ciclo_df["velocita"] = np.gradient(ciclo_df["posizione"], ciclo_df["tempo"])
        ciclo_df["accelerazione"] = np.gradient(ciclo_df["velocita"], ciclo_df["tempo"])
        ciclo_df["jerk"] = np.gradient(ciclo_df["accelerazione"], ciclo_df["tempo"])
        st.line_chart(ciclo_df.set_index("tempo")[["posizione", "velocita", "accelerazione"]])
        st.write(f"**Accelerazione max:** {ciclo_df['accelerazione'].abs().max():.1f} mm/s²")
        st.write(f"**Jerk max:** {ciclo_df['jerk'].abs().max():.1f} mm/s³")
    else:
        st.error("Il file deve contenere le colonne 'tempo' e 'posizione'.")

# --- Componenti ---
st.header("📂 Componenti")
viti_file = st.file_uploader("Database viti", type="xlsx")
motori_file = st.file_uploader("Database motori", type="xlsx")
riduttori_file = st.file_uploader("Database riduttori", type="xlsx")
curve_files = st.file_uploader("Curve motore (puoi caricare più file)", type="xlsx", accept_multiple_files=True)
corsa_totale_input = st.number_input("Corsa totale attuatore [mm]", min_value=10.0, value=100.0)

# --- Calcolo e selezione ---
report_path = "/mnt/data/report_dimensionamento.docx"

if st.button("▶️ Calcola") and ciclo_file and viti_file and motori_file and riduttori_file:
    corsa_effettiva = ciclo_df["posizione"].max() - ciclo_df["posizione"].min()
    if corsa_effettiva > corsa_totale_input:
        st.error("❌ Corsa richiesta superiore alla corsa disponibile")
    else:
        viti_df = pd.read_excel(viti_file)
        motori_df = pd.read_excel(motori_file)
        riduttori_df = pd.read_excel(riduttori_file)

        viti_compatibili = viti_df[viti_df["corsa_mm"] >= corsa_effettiva]
        if viti_compatibili.empty:
            st.error("❌ Nessuna vite compatibile")
        else:
            vite_sel = viti_compatibili.iloc[0]
            st.success(f"✅ Vite: {vite_sel['codice']}")

            riduttore_sel = riduttori_df.iloc[0]
            st.success(f"⚙️ Riduttore: {riduttore_sel['codice']}")

            motore_sel = motori_df.iloc[0]
            codice_motore = motore_sel["codice"]
            st.success(f"🔋 Motore: {codice_motore}")

            curva_df = None
            for f in curve_files:
                if codice_motore in f.name:
                    curva_df = pd.read_excel(f)
                    break

            curva_img_path = None
            if curva_df is not None:
                fig, ax = plt.subplots()
                ax.plot(curva_df["rpm"], curva_df["tau_nom"], label="Coppia Nominale")
                ax.plot(curva_df["rpm"], curva_df["tau_max"], label="Coppia Massima", linestyle="--")
                ax.set_xlabel("Velocità [rpm]")
                ax.set_ylabel("Coppia [Nm]")
                ax.set_title(f"Curva motore {codice_motore}")
                ax.legend()
                curva_img_path = f"curva_{codice_motore}.png"
                fig.savefig(curva_img_path)
                st.pyplot(fig)
            else:
                st.warning("⚠️ Nessuna curva trovata per il motore")

            # --- Generazione report Word ---
            doc = Document()
            doc.add_heading("Report Dimensionamento Attuatore", 0)
            doc.add_paragraph(f"Motore selezionato: {codice_motore}")
            doc.add_paragraph(f"Vite selezionata: {vite_sel['codice']}")
            doc.add_paragraph(f"Riduttore selezionato: {riduttore_sel['codice']}")
            if curva_img_path and os.path.exists(curva_img_path):
                doc.add_picture(curva_img_path, width=Inches(5.5))
            doc.save(report_path)
            st.success("📄 Report generato!")

# --- Pulsante download report ---
if os.path.exists(report_path):
    with open(report_path, "rb") as file:
        st.download_button(
            label="📥 Scarica il report Word",
            data=file,
            file_name="report_dimensionamento.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
