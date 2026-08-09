import io
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image
import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

# --- SICHERHEITSCHECK ---
if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst über die Startseite ein.")
    st.stop()

# Session State initialisieren
if "step" not in st.session_state: st.session_state.step = 1
defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", "telefon": "", "adresse": "",
    "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", "experience": "Anfänger (weniger als 6 Monate)",
    "main_goal": [], "agb": False, "haftung": False, "datenschutz": False, "signature": None
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Neues Mitglied anmelden")

    st.subheader("👤 1. Persönliche Daten")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.vorname)
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.nachname)
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.geburtsdatum)
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.telefon)
        st.session_state.adresse = st.text_input("Adresse", value=st.session_state.adresse)

    st.markdown("---")
    st.subheader("🏋️ 2. Tarif & Ziele")
    st.session_state.tarif = st.selectbox("Tarifauswahl", 
        ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"]
    )
    st.session_state.experience = st.selectbox("Trainingserfahrung", ["Anfänger (weniger als 6 Monate)", "Leicht fortgeschritten (6 Monate bis 2 Jahre)", "Fortgeschritten (über 2 Jahre)"])
    st.session_state.main_goal = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"])

    st.markdown("---")
    st.subheader("📄 3. Rechtliches & Zustimmung")
    
    st.info("""**Allgemeine Vertragsbedingungen:**\n
• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n
• **Terminabsage & Stornierung:** 48 Stunden vorher.\n
• **Kündigungsfrist:** 2 Wochen zum Monatsende""")
    st.session_state.agb = st.checkbox("Ich akzeptiere die Vertragsbedingungen und AGB. *", value=st.session_state.agb)
    
    st.info("""**Haftungsausschluss:** Eigenverantwortung, Risikoaufklärung, Haftungsbeschränkung (siehe Details im Anamnesebogen).""")
    st.session_state.haftung = st.checkbox("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *", value=st.session_state.haftung)
    
    st.info("""**Datenschutz:** Einwilligung in die Datenverarbeitung (Art. 9 DSGVO).""")
    st.session_state.datenschutz = st.checkbox("Ich willige in die Verarbeitung meiner Gesundheitsdaten ein. *", value=st.session_state.datenschutz)

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("✅ Mitglied anmelden & weiter zur Anamnese"):
        if not st.session_state.vorname or not st.session_state.nachname or not st.session_state.email:
            st.error("⚠️ Bitte Pflichtfelder ausfüllen!")
        elif not (st.session_state.agb and st.session_state.haftung and st.session_state.datenschutz):
            st.error("⚠️ Bitte alle Rechtshaken setzen!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreiben!")
        else:
            st.session_state.member_data["signature"] = canvas_result.image_data
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    
    cb_bluthochdruck = st.checkbox("Bluthochdruck")
    cb_herzinfarkt = st.checkbox("Herzinfarkt (in der Vergangenheit)")
    cb_schlaganfall = st.checkbox("Schlaganfall (in der Vergangenheit)")
    cb_rhythmus = st.checkbox("Herzrhythmusstörungen")
    cardiovascular_other = st.text_input("Sonstiges Herz-Kreislauf:")

    st.markdown("---")
    cb_ruecken = st.checkbox("Beschwerden im unteren Rücken / LWS")
    cb_gelenke = st.checkbox("Gelenkbeschwerden")
    cb_artif_joint = st.checkbox("Künstliches Gelenk")
    cb_wirbelsaeule = st.checkbox("Sonstige Wirbelsäulenbeschwerden")
    musculoskeletal_other = st.text_input("Sonstiges Bewegungsapparat:")

    st.markdown("---")
    cb_diabetes = st.checkbox("Diabetes mellitus")
    cb_asthma = st.checkbox("Asthma / chron. Atemwegserkrankungen")
    cb_cramps = st.checkbox("Neigung zu Krämpfen")
    cb_epilepsy = st.checkbox("Epilepsie")
    cb_organe = st.checkbox("Organerkrankungen")
    metabolism_other = st.text_input("Sonstiges Stoffwechsel/Organe:")

    surgeries_meds = st.text_area("Operationen, Verletzungen oder Medikamente?")

    if st.button("✅ Registrierung abschließen"):
        with st.spinner("Verarbeite Daten..."):
            try:
                # Daten sammeln
                cv_list = [c for c, cb in [("Bluthochdruck", cb_bluthochdruck), ("Herzinfarkt", cb_herzinfarkt), ("Schlaganfall", cb_schlaganfall), ("Rhythmusstörungen", cb_rhythmus)] if cb]
                ms_list = [c for c, cb in [("LWS", cb_ruecken), ("Gelenke", cb_gelenke), ("Künstl. Gelenk", cb_artif_joint), ("Wirbelsäule", cb_wirbelsaeule)] if cb]
                met_list = [c for c, cb in [("Diabetes", cb_diabetes), ("Asthma", cb_asthma), ("Krämpfe", cb_cramps), ("Epilepsie", cb_epilepsy), ("Organe", cb_organe)] if cb]
                
                warnhinweis = ", ".join(cv_list + ms_list + met_list + ([cardiovascular_other] if cardiovascular_other else []) + ([surgeries_meds] if surgeries_meds else []))

                m_data = st.session_state.member_data

                # GSheets & E-Mail & Drive Logik...
                conn = st.connection("gsheets", type=GSheetsConnection)
                SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
                df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
                
                neues_mitglied = pd.DataFrame([{
                    "Datum": datetime.now().strftime("%d.%m.%Y"),
                    "Vorname": m_data["vorname"], "Nachname": m_data["nachname"],
                    "Geburtsdatum": m_data["geburtsdatum"], "E-Mail": m_data["email"],
                    "Telefon": m_data["telefon"], "Adresse": m_data["adresse"],
                    "Tarif": m_data["tarif"], "Erfahrung": m_data["experience"],
                    "Ziele": ", ".join(m_data["main_goal"]), "Gesundheits_Notizen": warnhinweis
                }])
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=pd.concat([df, neues_mitglied], ignore_index=True))

                # E-Mail
                sender_email = st.secrets["email"]["absender"]
                server = smtplib.SMTP(st.secrets["email"]["smtp_server"], int(st.secrets["email"]["smtp_port"]))
                server.starttls()
                server.login(sender_email, st.secrets["email"]["passwort"])
                
                msg = MIMEMultipart()
                msg['From'] = sender_email
                msg['To'] = m_data["email"]
                msg['Subject'] = "Willkommen im Hinkelfit Studio!"
                msg.attach(MIMEText("Willkommen! Im Anhang findest du deine Unterlagen.", 'plain'))
                
                # PDFs anhängen
                for f in ["Allgemeine Geschäftsbedingungen.pdf", "Datenschutzerklärung.pdf", "Ernährungskompass.pdf", "Hausordnung.pdf", "Willkommen.pdf"]:
                    path = os.path.join("pdfs", f)
                    if os.path.exists(path):
                        with open(path, "rb") as file:
                            part = MIMEApplication(file.read(), _subtype="pdf")
                            part.add_header('Content-Disposition', 'attachment', filename=f)
                            msg.attach(part)
                server.send_message(msg)
                server.quit()

                # Drive Upload
                creds = service_account.Credentials.from_service_account_info(st.secrets["connections"]["gsheets"], scopes=['https://www.googleapis.com/auth/drive'])
                service = build('drive', 'v3', credentials=creds)
                
                folder_meta = {'name': f"{m_data['nachname']}_{m_data['vorname']}", 'mimeType': 'application/vnd.google-apps.folder', 'parents': [st.secrets["drive"]["hauptordner_id"]]}
                folder_id = service.files().create(body=folder_meta, fields='id').execute()['id']
                
                img_io = io.BytesIO()
                Image.fromarray(m_data["signature"].astype('uint8'), 'RGBA').save(img_io, format='PNG')
                img_io.seek(0)
                service.files().create(body={'name': 'Unterschrift.png', 'parents': [folder_id]}, media_body=MediaIoBaseUpload(img_io, mimetype='image/png')).execute()

                st.session_state.step = 3
                st.rerun()
            except Exception as e:
                st.error(f"Fehler: {e}")

elif st.session_state.step == 3:
    st.balloons()
    st.success("✅ Erledigt!")
    if st.button("🔄 Neues Mitglied"):
         st.session_state.step = 1; st.session_state.member_data = {}; st.rerun()
