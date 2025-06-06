import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches

st.title("🧮 Configuratore Attuatore Elettromeccanico")

# --- Caricamento file ciclo di lavoro ---
st.header("📈 Ciclo di lavoro")
ciclo_file = st.file_uploader("Carica il file Excel del ciclo di lavoro", type="xlsx")
if ciclo_file:
    df = pd.read_excel(ciclo_file)
    if "tempo" in df.columns and "posizione" in df.columns:
        df = df.sort_values("tempo")
        df["velocita"] = np.gradient(df["posizione"], df["tempo"])
        df["accelerazione"] = np.gradient(df["velocita"], df["tempo"])
        df["jerk"] = np.gradient(df["accelerazione"], df["tempo"])

        st.line_chart(df.set_index("tempo")[["posizione", "velocita", "accelerazione"]])
        st.write(f"**Accelerazione max:** {df['accelerazione'].abs().max():.1f} mm/s²")
        st.write(f"**Jerk max:** {df['jerk'].abs().max():.1f} mm/s³")
    else:
        st.error("❌ Il file deve contenere le colonne 'tempo' e 'posizione'.")

# --- Caricamento altri file ---
st.header("📂 Dati componenti")
motori_file = st.file_uploader("Carica database motori", type="xlsx")
viti_file = st.file_uploader("Carica database viti", type="xlsx")
riduttori_file = st.file_uploader("Carica database riduttori", type="xlsx")
curve_files = st.file_uploader("Carica curve motore (più file)", type="xlsx", accept_multiple_files=True)

# --- Pulsante Calcola ---
if st.button("▶️ Calcola") and ciclo_file and motori_file and viti_file and riduttori_file:
    # Dummy processing
    st.success("✅ Calcolo completato con successo.")

    # Inserimento curva grafico (simulata)
    fig, ax = plt.subplots()
    ax.plot([0, 1000, 2000], [1, 2, 1.5], label="Coppia Nominale")
    ax.plot([0, 1000, 2000], [2, 3, 2.5], label="Coppia Massima", linestyle="--")
    ax.set_title("Curva Motore di Esempio")
    ax.set_xlabel("Velocità [rpm]")
    ax.set_ylabel("Coppia [Nm]")
    ax.legend()
    st.pyplot(fig)
    fig.savefig("curva_motore_esempio.png")

    # Report Word
    doc = Document()
    doc.add_heading("Report Dimensionamento Attuatore", 0)
    doc.add_paragraph("Motore selezionato: MOT-100")
    doc.add_paragraph("Vite selezionata: VITE-50")
    doc.add_paragraph("Riduttore selezionato: DIR")
    try:
        doc.add_picture("curva_motore_esempio.png", width=Inches(5.5))
    except Exception as e:
        st.warning("Curva non inserita nel report: " + str(e))
    report_path = "report_dimensionamento.docx"
    doc.save(report_path)
    st.success(f"📄 Report generato: {report_path}")
