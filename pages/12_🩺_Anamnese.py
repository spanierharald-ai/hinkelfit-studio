import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from datetime import datetime

st.set_page_config(page_title="Hinkelfit | Anamnese", page_icon="🩺", layout="wide")

# --- SICHERHEITSCHECK ---
if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst über die Startseite ein.")
    st.stop()

# Prüfen, ob wir von der Anmeldung kommen
if 'anamnese_vorname' not in st.session_state:
    st.info("Bitte starte den Prozess über die Seite 'Anmeldung'.")
    st.stop()

vorname = st.session_state['anamnese_vorname']
nachname = st.session_state['anamnese_nachname']
email = st.session_state['anamnese_email']

st.title(f"🩺 Gesundheits-Anamnese für {vorname} {nachname}")
st.write("Bitte fülle die folgenden gesundheitlichen Details gemeinsam mit dem Mitglied aus. Diese Daten sind sensibel und lösen im System automatisch Warnhinweise aus (z.B. in der Tagesansicht).")

with st.form("anamnese_form"):
    st.subheader("🫀 Herz-Kreislauf-System")
    herz_kreislauf = st.text_area("Gibt es Vorerkrankungen? (z.B. Bluthochdruck, Asthma, Herzfehler, Herzinfarkt in der Vergangenheit)")
    
    st.subheader("🦴 Bewegungsapparat")
    gelenke = st.text_area("Gibt es Probleme mit Gelenken, Knochen, Bändern oder der Wirbelsäule? (z.B. Bandscheibenvorfall)")
    
    st.subheader("🩸 Stoffwechsel & Innere Organe")
    stoffwechsel = st.text_area("Gibt es Stoffwechselerkrankungen? (z.B. Diabetes, Schilddrüsenunterfunktion)")
    
    st.subheader("🏥 Operationen & Verletzungen")
    operationen = st.text_area("Gab es in der Vergangenheit relevante Operationen oder schwere Verletzungen, die das Training beeinflussen könnten?")
    
    st.subheader("💊 Medikamente")
    medikamente = st.text_area("Werden regelmäßig Medikamente eingenommen? Wenn ja, welche und wogegen?")

    submit = st.form_submit_button("💾 Gesundheitsdaten (Anamnese) speichern")

if submit:
    with st.spinner("Speichere Gesundheitsdaten sicher ab..."):
        try:
            conn = st.connection("gsheets", type=GSheetsConnection)
            SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
            
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Anamnese", ttl=0)

            neue_anamnese = pd.DataFrame([{
                "Datum": datetime.now().strftime("%d.%m.%Y"),
                "Vorname": vorname,
                "Nachname": nachname,
                "E-Mail": email,
                "Herz-Kreislauf": herz_kreislauf,
                "Bewegungsapparat": gelenke,
                "Stoffwechsel": stoffwechsel,
                "Operationen": operationen,
                "Medikamente": medikamente
            }])
            
            df_aktualisiert = pd.concat([df, neue_anamnese], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Anamnese", data=df_aktualisiert)
            
            st.success(f"✅ Die Anamnese für {vorname} wurde erfolgreich gespeichert und ist für die Tagesansicht abrufbar!")
            st.balloons()
            
            # Speicher nach Abschluss bereinigen
            del st.session_state['anamnese_vorname']
            del st.session_state['anamnese_nachname']
            
        except Exception as e:
            st.error(f"❌ Fehler beim Speichern: {e}")
