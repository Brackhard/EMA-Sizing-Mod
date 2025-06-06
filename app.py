import streamlit as st
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from docx import Document
from docx.shared import Inches
import os

st.set_page_config(page_title="EMA Configuratore", layout="wide")
st.title("⚙️ Configuratore Attuatore Elettromeccanico")
st.markdown("Semplifica la selezione di vite, motore e riduttore per il tuo sistema.")

# --- CICLO DI LAVORO ---
st.header("📈 Ciclo di lavoro")
col1, col2 = st.columns(2)
with col1:
    ciclo_file = st.file_uploader("Carica file ciclo (xlsx con tempo, posizione, forza)", type="xlsx")

# Inizializziamo dataframe
ciclo_df = None
report_path = "report_dimensionamento.docx"

if ciclo_file:
    ciclo_df = pd.read_excel(ciclo_file)
    if "tempo" in ciclo_df.columns and "posizione" in ciclo_df.columns:
        ciclo_df = ciclo_df.sort_values("tempo")
        ciclo_df["velocita"] = np.gradient(ciclo_df["posizione"], ciclo_df["tempo"])
        ciclo_df["accelerazione"] = np.gradient(ciclo_df["velocita"], ciclo_df["tempo"])
        ciclo_df["jerk"] = np.gradient(ciclo_df["accelerazione"], ciclo_df["tempo"])

        st.subheader("📊 Grafici ciclo")
        fig, ax = plt.subplots(4, 1, figsize=(8, 10), sharex=True)
        ax[0].plot(ciclo_df["tempo"], ciclo_df["posizione"])
        ax[0].set_ylabel("Posizione [mm]")
        ax[1].plot(ciclo_df["tempo"], ciclo_df["velocita"])
        ax[1].set_ylabel("Velocità [mm/s]")
        ax[2].plot(ciclo_df["tempo"], ciclo_df["accelerazione"])
        ax[2].set_ylabel("Accelerazione [mm/s²]")
        ax[3].plot(ciclo_df["tempo"], ciclo_df["jerk"])
        ax[3].set_ylabel("Jerk [mm/s³]")
        ax[3].set_xlabel("Tempo [s]")
        st.pyplot(fig)

        st.success(f"✅ Accelerazione max: {ciclo_df['accelerazione'].abs().max():.1f} mm/s²")
        st.success(f"✅ Jerk max: {ciclo_df['jerk'].abs().max():.1f} mm/s³")
    else:
        st.error("❌ Il file deve contenere almeno 'tempo' e 'posizione'.")

# --- INPUT COMPONENTI ---
st.header("📂 Componenti e Parametri")
col_v, col_m, col_r = st.columns(3)
viti_file = col_v.file_uploader("🔩 Database Viti", type="xlsx")
motori_file = col_m.file_uploader("🔋 Database Motori", type="xlsx")
riduttori_file = col_r.file_uploader("⚙️ Database Riduttori", type="xlsx")
curve_files = st.file_uploader("📈 Curve Motore (puoi caricare più file)", type="xlsx", accept_multiple_files=True)
corsa_totale_input = st.number_input("📏 Corsa totale disponibile [mm]", min_value=10.0, value=100.0)

# --- CALCOLO COMPLETO ---
if st.button("▶️ Calcola") and ciclo_df is not None and viti_file and motori_file and riduttori_file:
    corsa_effettiva = ciclo_df["posizione"].max() - ciclo_df["posizione"].min()
    st.info(f"Corsa effettiva del ciclo: {corsa_effettiva:.1f} mm")

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
            st.success(f"✅ Vite selezionata: {vite_sel['codice']}")

            lunghezza_libera = corsa_totale_input
            K = 9.87
            diametro = 20
            E = 2.1e5
            v_cr = (K * np.pi / lunghezza_libera)**2 * E * (np.pi * diametro**4 / 64) / 1e6
            st.warning(f"🔄 Velocità critica stimata: {v_cr:.0f} rpm")

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

            curva_img_path = f"curva_{codice_motore}.png"
            if curva_df is not None:
                fig2, ax2 = plt.subplots()
                ax2.plot(curva_df["rpm"], curva_df["tau_nom"], label="Coppia Nominale")
                ax2.plot(curva_df["rpm"], curva_df["tau_max"], label="Coppia Massima", linestyle="--")
                ax2.set_xlabel("Velocità [rpm]")
                ax2.set_ylabel("Coppia [Nm]")
                ax2.set_title(f"Curva motore {codice_motore}")
                ax2.legend()
                fig2.savefig(curva_img_path)
                st.pyplot(fig2)

            # --- GENERA REPORT ---
            doc = Document()
            doc.add_heading("📄 Report Dimensionamento", 0)
            doc.add_paragraph(f"Motore selezionato: {codice_motore}")
            doc.add_paragraph(f"Vite selezionata: {vite_sel['codice']}")
            doc.add_paragraph(f"Riduttore selezionato: {riduttore_sel['codice']}")
            doc.add_paragraph(f"Corsa effettiva: {corsa_effettiva:.1f} mm")
            doc.add_paragraph(f"Accelerazione max: {ciclo_df['accelerazione'].abs().max():.1f} mm/s²")
            doc.add_paragraph(f"Jerk max: {ciclo_df['jerk'].abs().max():.1f} mm/s³")
            doc.add_paragraph(f"Velocità critica stimata: {v_cr:.0f} rpm")

            # Vita utile stimata
            vita_cicli = 1e6
            ore_giornaliere = 16
            sec_per_ciclo = ciclo_df["tempo"].iloc[-1] - ciclo_df["tempo"].iloc[0]
            cicli_giornalieri = (ore_giornaliere * 3600) / sec_per_ciclo if sec_per_ciclo > 0 else 0
            anni = vita_cicli / (cicli_giornalieri * 365) if cicli_giornalieri > 0 else 0
            doc.add_paragraph(f"Vita utile stimata: {vita_cicli:.0f} cicli")
            doc.add_paragraph(f"Vita utile stimata: {anni:.1f} anni")

            if curva_df is not None:
                doc.add_picture(curva_img_path, width=Inches(5.5))
                table = doc.add_table(rows=1, cols=3)
                hdr_cells = table.rows[0].cells
                hdr_cells[0].text = "RPM"
                hdr_cells[1].text = "Coppia Nominale [Nm]"
                hdr_cells[2].text = "Coppia Massima [Nm]"
                for _, row in curva_df.iterrows():
                    row_cells = table.add_row().cells
                    row_cells[0].text = str(row["rpm"])
                    row_cells[1].text = str(row["tau_nom"])
                    row_cells[2].text = str(row["tau_max"])

            doc.save(report_path)
            st.success("📄 Report generato con successo!")

# --- DOWNLOAD REPORT ---
if os.path.exists(report_path):
    with open(report_path, "rb") as f:
        st.download_button(
            label="📥 Scarica il report Word",
            data=f,
            file_name="report_dimensionamento.docx",
            mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
