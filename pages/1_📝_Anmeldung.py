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
# Buttons für den Status
if "agb_ok" not in st.session_state: st.session_state.agb_ok = False
if "dsgvo_ok" not in st.session_state: st.session_state.dsgvo_ok = False
if "anamnese_bestaetigt" not in st.session_state: st.session_state.anamnese_bestaetigt = False

# Session State Keys für Stabilität
if "vorname" not in st.session_state: st.session_state.vorname = ""
if "nachname" not in st.session_state: st.session_state.nachname = ""
if "email" not in st.session_state: st.session_state.email = ""

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
        adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)")
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
        telefon = st.text_input("Telefonnummer")
        geburtsdatum = st.text_input("Geburtsdatum")

    st.subheader("🏋️ 2. Tarif & Ziele")
    tarif = st.selectbox("Tarifauswahl", [
        "Kurse 2x wöchentlich, 59€ pro Monat", 
        "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
        "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
    ])
    ziele = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"])

    st.subheader("📄 3. Vertrag & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="b_agb"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz:** Ich willige ausdrücklich ein, dass meine personenbezogenen Daten zur Verwaltung der Mitgliedschaft verarbeitet werden.""")
    if st.button("✅ Einwilligung Datenverarbeitung akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅", key="b_dsgvo"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not st.session_state.vorname:
            st.error("⚠️ Vorname fehlt!")
        elif not st.session_state.nachname:
            st.error("⚠️ Nachname fehlt!")
        elif not st.session_state.email:
            st.error("⚠️ E-Mail-Adresse fehlt!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte akzeptiere zuerst AGB und Datenschutz!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreibe!")
        else:
            st.session_state.member_data = {
                "vorname": st.session_state.vorname, "nachname": st.session_state.nachname, 
                "email": st.session_state.email, "tarif": tarif, "adresse": adresse, 
                "telefon": telefon, "dob": geburtsdatum, "ziele": ", ".join(ziele), 
                "signature": canvas_result.image_data
            }
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: AUSFÜHRLICHER ANAMNESEBOGEN
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    st.write(f"Vielen Dank, {st.session_state.member_data['vorname']}! Bitte fülle nun den Anamnesebogen aus.")

    st.subheader("1. Herz-Kreislauf-System und Gefäße")
    cb_bluthochdruck = st.checkbox("Bluthochdruck")
    cb_herzinfarkt = st.checkbox("Herzinfarkt (in der Vergangenheit)")
    cb_schlaganfall = st.checkbox("Schlaganfall (in der Vergangenheit)")
    cb_rhythmus = st.checkbox("Herzrhythmusstörungen")
    cardiovascular_other = st.text_input("Sonstiges / Weitere Details zu Herz-Kreislauf:")

    st.subheader("2. Bewegungsapparat, Gelenke und Wirbelsäule")
    cb_ruecken = st.checkbox("Beschwerden im unteren Rücken / Lendenwirbelsäule")
    cb_gelenke = st.checkbox("Gelenkbeschwerden (z. B. Schulter, Knie)")
    cb_artif_joint = st.checkbox("Künstliches Gelenk vorhanden")
    cb_wirbelsaeule = st.checkbox("Sonstige Wirbelsäulenbeschwerden")
    musculoskeletal_other = st.text_input("Sonstiges / Weitere Details zum Bewegungsapparat:")

    st.subheader("3. Stoffwechsel, Organe und Atmung")
    cb_diabetes = st.checkbox("Diabetes mellitus")
    cb_asthma = st.checkbox("Asthma oder chronische Atemwegserkrankungen")
    cb_cramps = st.checkbox("Neigung zu Krämpfen")
    cb_epilepsy = st.checkbox("Epilepsie")
    cb_organe = st.checkbox("Erkrankungen der inneren Organe (Niere, Leber etc.)")
    metabolism_other = st.text_input("Sonstiges / Weitere Details zu Stoffwechsel & Organen:")

    st.subheader("4. Operationen, Verletzungen und Medikamente")
    surgeries_meds = st.text_area("Gab es Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein?")
    
    st.markdown("---")
    st.subheader("5. Wahrheitspflicht & Risikoaufklärung")
    st.info("""**Wahrheitspflicht & Risikoaufklärung:**\n
1. **Wahrheitspflicht:** Ich bestätige, dass alle meine Angaben im Anamnesebogen vollständig und wahrheitsgemäß sind. Veränderungen des Gesundheitszustandes teile ich dem Trainer vor jedem Training unaufgefordert mit.\n
2. **Risikoaufklärung:** Mir ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit körperlichen Belastungen und Verletzungsrisiken verbunden ist. Ich verpflichte mich zum sofortigen Trainingsstopp bei Beschwerden.\n
3. **Haftung:** Ich akzeptiere die Haftungsbeschränkung für Sachschäden, Vermögensschäden und mitgebrachte Wertgegenstände.""")
    
    if st.button("✅ Anamnese wahrheitsgemäß bestätigt" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅", key="b_ana"):
        st.session_state.anamnese_bestaetigt = True

    st.markdown("---")
    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte bestätige zuerst die Wahrheitspflicht & Risikoaufklärung per Button!")
        else:
            with st.spinner("Verarbeite Anmeldung (Google Sheets, E-Mail & Cloud)..."):
                try:
                    # Anamnese-Daten zusammenfassen
                    cv_list, ms_list, met_list = [], [], []
                    if cb_bluthochdruck: cv_list.append("Bluthochdruck")
                    if cb_herzinfarkt: cv_list.append("Herzinfarkt")
                    if cb_schlaganfall: cv_list.append("Schlaganfall")
                    if cb_rhythmus: cv_list.append("Herzrhythmusstörungen")
                    if cardiovascular_other: cv_list.append(cardiovascular_other)

                    if cb_ruecken: ms_list.append("LWS/Rücken")
                    if cb_gelenke: ms_list.append("Gelenke")
                    if cb_artif_joint: ms_list.append("Künstl. Gelenk")
                    if cb_wirbelsaeule: ms_list.append("Wirbelsäule")
                    if musculoskeletal_other: ms_list.append(musculoskeletal_other)

                    if cb_diabetes: met_list.append("Diabetes")
                    if cb_asthma: met_list.append("Asthma")
                    if cb_cramps: met_list.append("Krämpfe")
                    if cb_epilepsy: met_list.append("Epilepsie")
                    if cb_organe: met_list.append("Organe")
                    if metabolism_other: met_list.append(metabolism_other)

                    alle_beschwerden = cv_list + ms_list + met_list
                    if surgeries_meds.strip():
                        alle_beschwerden.append("OPs/Meds beachten")
                    warnhinweis = ", ".join(alle_beschwerden)

                    m_data = st.session_state.member_data

                    # 1. Daten in Google Sheets speichern
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
                    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)

                    neues_mitglied = pd.DataFrame([{
                        "Datum": datetime.now().strftime("%d.%m.%Y"),
                        "Vorname": m_data["vorname"],
                        "Nachname": m_data["nachname"],
                        "Geburtsdatum": m_data["dob"],
                        "E-Mail": m_data["email"],
                        "Telefon": m_data["telefon"],
                        "Adresse": m_data["adresse"],
                        "Tarif": m_data["tarif"],
                        "Ziele": m_data["ziele"],
                        "Gesundheits_Notizen": warnhinweis
                    }])
                    df_aktualisiert = pd.concat([df, neues_mitglied], ignore_index=True)
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_aktualisiert)

                    # 2. E-Mail mit PDFs aus dem GitHub-Ordner "pdfs" versenden
                    sender_email = st.secrets["email"]["absender"]
                    sender_password = st.secrets["email"]["passwort"] 
                    smtp_server = st.secrets["email"]["smtp_server"]
                    smtp_port = st.secrets["email"]["smtp_port"]

                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = m_data["email"]
                    msg['Subject'] = "Willkommen im Hinkelfit Studio! 🏋️"

                    text = f"Hallo {m_data['vorname']},\n\nherzlich willkommen im Hinkelfit Studio! Wir freuen uns, dich an Bord zu haben.\n\nAnbei findest du deine Vertragsunterlagen, unsere Hausordnung sowie den Ernährungskompass als PDF-Dateien.\n\nSportliche Grüße,\nDein Hinkelfit-Team"
                    msg.attach(MIMEText(text, 'plain', 'utf-8'))

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

                    server = smtplib.SMTP(smtp_server, smtp_port)
                    server.starttls()
                    server.login(sender_email, sender_password)
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
    st.success("🎉 Alles erledigt! Die Registrierung ist vollständig abgeschlossen, die E-Mail wurde verschickt und der Cloud-Ordner erstellt.")
    if st.button("🔄 Nächstes Mitglied anlegen"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]: 
             st.session_state[key] = (1 if key == "step" else False)
         st.session_state.vorname = ""
         st.session_state.nachname = ""
         st.session_state.email = ""
         st.session_state.member_data = {}
         st.rerun()
