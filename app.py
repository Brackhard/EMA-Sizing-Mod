import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import io

st.set_page_config(page_title="Configuratore Attuatore", layout="centered")
st.title("⚙️ Configuratore Attuatore Elettromeccanico")

# Upload file (solo .xlsx)
ciclo_file = st.file_uploader("📄 Carica ciclo di lavoro (.xlsx)", type=["xlsx"])
viti_file = st.file_uploader("📄 Carica database viti (.xlsx)", type=["xlsx"])
motori_file = st.file_uploader("📄 Carica database motori (.xlsx)", type=["xlsx"])
riduttori_file = st.file_uploader("📄 Carica database riduttori (.xlsx)", type=["xlsx"])

def dati_validi(df, colonne):
    return all(col in df.columns for col in colonne) and len(df) > 1

if st.button("Calcola") and all([ciclo_file, viti_file, motori_file, riduttori_file]):
    try:
        df_ciclo = pd.read_excel(ciclo_file)
        df_viti = pd.read_excel(viti_file)
        df_motori = pd.read_excel(motori_file)
        df_riduttori = pd.read_excel(riduttori_file)
    except Exception as e:
        st.error(f"Errore nel caricamento dei file: {e}")
        st.stop()

    if not dati_validi(df_ciclo, ["tempo", "posizione", "velocita", "forza"]):
        st.error("❌ Il file del ciclo di lavoro deve contenere almeno due righe e le colonne: tempo, posizione, velocita, forza")
        st.stop()

    try:
        df_ciclo["F3"] = df_ciclo["forza"]**3
        Feq = (df_ciclo["F3"].mean())**(1/3)
        distanza_totale = df_ciclo["velocita"].sum() * df_ciclo["tempo"].diff().fillna(0).sum()
        corsa_per_ciclo = df_ciclo["posizione"].max() - df_ciclo["posizione"].min()
        tempo_ciclo = df_ciclo["tempo"].max() - df_ciclo["tempo"].min()

        vite_sel = df_viti[df_viti["C"] >= Feq * 1.2].copy()
        vite_sel["L10"] = (vite_sel["C"] / Feq)**3 * 1e6

        result_data = {}

        st.subheader("🔍 Risultati")
        st.write(f"**Carico equivalente:** {Feq:.2f} N")
        st.write(f"**Distanza stimata:** {distanza_totale:.0f} mm")
        st.write(f"**Corsa utile per ciclo:** {corsa_per_ciclo:.0f} mm")
        st.write(f"**Durata ciclo:** {tempo_ciclo:.2f} s")

        if not vite_sel.empty and corsa_per_ciclo > 0 and tempo_ciclo > 0:
            vite = vite_sel.iloc[0]
            durata_mm = vite["L10"]
            durata_cicli = durata_mm / corsa_per_ciclo
            cicli_per_giorno = (16 * 3600) / tempo_ciclo
            durata_anni = durata_cicli / (cicli_per_giorno * 365)

            result_data = {
                "vite": vite["codice"],
                "Feq": Feq,
                "L10_mm": durata_mm,
                "durata_cicli": durata_cicli,
                "durata_anni": durata_anni
            }

            st.success(f"✅ Vite selezionata: {vite['codice']}")
            st.write(f"**Durata stimata (L10):** {durata_mm:,.0f} mm")
            st.write(f"**Durata stimata in cicli:** {durata_cicli:,.0f} cicli")
            st.write(f"**Durata stimata in anni (16h/giorno):** {durata_anni:.1f} anni")

            st.subheader("📈 Grafico Ciclo di Lavoro")
            fig, ax = plt.subplots()
            ax.plot(df_ciclo["tempo"], df_ciclo["posizione"], label="Posizione (mm)")
            ax.set_xlabel("Tempo (s)")
            ax.set_ylabel("Posizione (mm)")
            ax2 = ax.twinx()
            ax2.plot(df_ciclo["tempo"], df_ciclo["forza"], color="red", label="Forza (N)", linestyle="--")
            ax2.set_ylabel("Forza (N)")
            st.pyplot(fig)

            st.subheader("🧠 Motore e Riduttore (coppia semplificata)")
            velocita_media = df_ciclo["velocita"].mean()
            vite_passo = vite["codice"].split("x")[-1]
            try:
                passo = float(vite_passo)
                rpm_vite = (velocita_media / passo) * 60
                torque_required = Feq * passo / (2 * 3.1416 * 0.9)

                motori_ok = df_motori[df_motori["coppia"] >= torque_required]
                riduttori_ok = df_riduttori[rpm_vite <= df_riduttori["rpm_max"]]

                if not motori_ok.empty:
                    st.write(f"Motore suggerito: {motori_ok.iloc[0]['codice']}")
                else:
                    st.warning("⚠️ Nessun motore soddisfa la coppia richiesta.")

                if not riduttori_ok.empty:
                    st.write(f"Riduttore suggerito: {riduttori_ok.iloc[0]['codice']}")
                else:
                    st.warning("⚠️ Nessun riduttore compatibile con RPM.")
            except:
                st.warning("⚠️ Passo vite non valido per il calcolo della coppia.")

            st.subheader("📤 Esportazione risultati")
            df_export = pd.DataFrame([result_data])
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='xlsxwriter') as writer:
                df_export.to_excel(writer, index=False, sheet_name='Risultati')
            st.download_button(label="📥 Scarica risultati in Excel", data=buffer.getvalue(),
                               file_name="risultati_configuratore.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")

        else:
            st.error("⚠️ Nessuna vite soddisfa i criteri o corsa/tempo ciclo non validi.")
    except Exception as e:
        st.error(f"Errore nel calcolo: {e}")
