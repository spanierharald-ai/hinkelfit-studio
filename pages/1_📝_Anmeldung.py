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
    st.warning("🔒 Bitte logge dich zuerst ein.")
    st.stop()

# --- INITIALISIERUNG ---
if "step" not in st.session_state: st.session_state.step = 1
if "agb_ok" not in st.session_state: st.session_state.agb_ok = False
if "dsgvo_ok" not in st.session_state: st.session_state.dsgvo_ok = False
if "anamnese_bestaetigt" not in st.session_state: st.session_state.anamnese_bestaetigt = False

defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", "telefon": "", "adresse": "",
    "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", "experience": "Anfänger", "main_goal": [], "signature": None
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

    st.subheader("🏋️ 2. Tarif & Ziele")
    st.session_state.tarif = st.selectbox("Tarifauswahl", [
        "Kurse 2x wöchentlich, 59€ pro Monat", 
        "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
        "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
    ])
    st.session_state.main_goal = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.main_goal)

    st.subheader("📄 3. Vertrag & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** 48 Stunden vorher.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz:** Ich willige ausdrücklich ein, dass meine personenbezogenen Daten zur Verwaltung der Mitgliedschaft verarbeitet werden.""")
    if st.button("✅ Einwilligung Datenverarbeitung akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅", key="btn_dsgvo"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Weiter zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Bitte Pflichtfelder ausfüllen!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte bestätige AGB und Datenschutz!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreiben!")
        else:
            st.session_state.member_data = {
                "vorname": st.session_state.vorname, 
                "nachname": st.session_state.nachname, 
                "email": st.session_state.email, 
                "telefon": st.session_state.telefon,
                "geburtsdatum": st.session_state.geburtsdatum,
                "adresse": st.session_state.adresse,
                "tarif": st.session_state.tarif, 
                "ziele": ", ".join(st.session_state.main_goal),
                "signature": canvas_result.image_data
            }
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE & ABSCHLUSS
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen")
    
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
    
    st.markdown("---")
    st.info("""**Wahrheitspflicht & Risikoaufklärung:**\n
1. **Wahrheitspflicht:** Ich bestätige, dass alle meine Angaben wahrheitsgemäß und vollständig sind. Änderungen teile ich sofort mit.\n
2. **Risikoaufklärung:** Ich bin mir der körperlichen Belastung und des Verletzungsrisikos bewusst. Ich befolge die Anweisungen des Trainers.\n
3. **Haftung:** Ich akzeptiere die Haftungsbeschränkung für Sachschäden und Wertgegenstände.""")
    
    if st.button("✅ Anamnese wahrheitsgemäß bestätigt" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅", key="btn_anamnese"):
        st.session_state.anamnese_bestaetigt = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte bestätige zuerst die Wahrheitspflicht & Risikoaufklärung!")
        else:
            with st.spinner("Verarbeite Anmeldung (Google Tabelle, E-Mail & Cloud werden synchronisiert)..."):
                try:
                    # Gesundheitsnotizen zusammenfassen
                    cv_list = [c for c, cb in [("Bluthochdruck", cb_bluthochdruck), ("Herzinfarkt", cb_herzinfarkt), ("Schlaganfall", cb_schlaganfall), ("Rhythmusstörungen", cb_rhythmus)] if cb]
                    ms_list = [c for c, cb in [("LWS", cb_ruecken), ("Gelenke", cb_gelenke), ("Künstl. Gelenk", cb_artif_joint), ("Wirbelsäule", cb_wirbelsaeule)] if cb]
                    met_list = [c for c, cb in [("Diabetes", cb_diabetes), ("Asthma", cb_asthma), ("Krämpfe", cb_cramps), ("Epilepsie", cb_epilepsy), ("Organe", cb_organe)] if cb]
                    
                    warnhinweis = ", ".join(cv_list + ms_list + met_list + ([cardiovascular_other] if cardiovascular_other else []) + ([surgeries_meds] if surgeries_meds else []))

                    m_data = st.session_state.member_data

                    # 1. Google Sheets aktualisieren
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
                    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
                    
                    neues_mitglied = pd.DataFrame([{
                        "Datum": datetime.now().strftime("%d.%m.%Y"),
                        "Vorname": m_data["vorname"], 
                        "Nachname": m_data["nachname"],
                        "Geburtsdatum": m_data["geburtsdatum"], 
                        "E-Mail": m_data["email"],
                        "Telefon": m_data["telefon"], 
                        "Adresse": m_data["adresse"],
                        "Tarif": m_data["tarif"], 
                        "Ziele": m_data["ziele"], 
                        "Gesundheits_Notizen": warnhinweis
                    }])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=pd.concat([df, neues_mitglied], ignore_index=True))

                    # 2. E-Mail mit PDFs aus dem GitHub "pdfs"-Ordner versenden
                    sender_email = st.secrets["email"]["absender"]
                    server = smtplib.SMTP(st.secrets["email"]["smtp_server"], int(st.secrets["email"]["smtp_port"]))
                    server.starttls()
                    server.login(sender_email, st.secrets["email"]["passwort"])
                    
                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = m_data["email"]
                    msg['Subject'] = "Willkommen im Hinkelfit Studio! 🏋️"
                    
                    text_body = f"Hallo {m_data['vorname']},\n\nherzlich willkommen im Hinkelfit Studio! Wir freuen uns, dich an Bord zu haben.\n\nAnbei findest du deine Vertragsunterlagen, unsere Hausordnung sowie den Ernährungskompass als PDF-Dateien.\n\nSportliche Grüße,\nDein Hinkelfit-Team"
                    msg.attach(MIMEText(text_body, 'plain', 'utf-8'))
                    
                    pdf_liste = [
                        "Allgemeine Geschäftsbedingungen.pdf",
                        "Datenschutzerklärung.pdf",
                        "Ernährungskompass.pdf",
                        "Hausordnung.pdf",
                        "Willkommen.pdf"
                    ]

                    for pdf_name in pdf_liste:
                        pdf_pfad = os.path.join("pdfs", pdf_name)
                        if os.path.exists(pdf_pfad):
                            with open(pdf_pfad, "rb") as f:
                                attach = MIMEApplication(f.read(), _subtype="pdf")
                                attach.add_header('Content-Disposition', 'attachment', filename=pdf_name)
                                msg.attach(attach)
                        else:
                            st.warning(f"PDF im Repo nicht gefunden: {pdf_name}")

                    server.send_message(msg)
                    server.quit()

                    # 3. Google Drive Ordner anlegen & Unterschrift hochladen
                    creds_dict = st.secrets["connections"]["gsheets"]
                    scopes = ['https://www.googleapis.com/auth/drive']
                    creds = service_account.Credentials.from_service_account_info(
                        {
                            "type": creds_dict["type"],
                            "project_id": creds_dict["project_id"],
                            "private_key_id": creds_dict["private_key_id"],
                            "private_key": creds_dict["private_key"],
                            "client_email": creds_dict["client_email"],
                            "client_id": creds_dict["client_id"],
                            "auth_uri": creds_dict["auth_uri"],
                            "token_uri": creds_dict["token_uri"],
                            "auth_provider_x509_cert_url": creds_dict["auth_provider_x509_cert_url"],
                            "client_x509_cert_url": creds_dict["client_x509_cert_url"],
                        }, 
                        scopes=scopes
                    )
                    drive_service = build('drive', 'v3', credentials=creds)

                    hauptordner_id = st.secrets["drive"]["hauptordner_id"]
                    ordner_name = f"{m_data['nachname']}_{m_data['vorname']}_{datetime.now().strftime('%d%m%Y')}"

                    file_metadata = {
                        'name': ordner_name,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [hauptordner_id]
                    }
                    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                    neu_ordner_id = folder.get('id')

                    img_data = m_data["signature"]
                    image = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                    img_byte_arr = io.BytesIO()
                    image.save(img_byte_arr, format='PNG')
                    img_byte_arr.seek(0)

                    media = MediaIoBaseUpload(img_byte_arr, mimetype='image/png', resumable=True)
                    file_metadata_sig = {'name': 'Unterschrift.png', 'parents': [neu_ordner_id]}
                    drive_service.files().create(body=file_metadata_sig, media_body=media, fields='id').execute()

                    st.session_state.step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fehler bei der Verarbeitung: {e}")

# -------------------------------------------------------------------------
# SCHRITT 3: ABSCHLUSS
# -------------------------------------------------------------------------
elif st.session_state.step == 3:
    st.balloons()
    st.success("🎉 Alles erledigt! Die Registrierung ist vollständig abgeschlossen, die E-Mail wurde verschickt und die Unterlagen in der Cloud gespeichert.")
    if st.button("🔄 Nächstes Mitglied anlegen"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]: 
             st.session_state[key] = (1 if key == "step" else False)
         st.session_state.member_data = {}
         st.rerun()
