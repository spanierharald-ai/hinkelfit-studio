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

st.title("📝 Neues Mitglied anmelden")
st.write("Fülle das Formular gemeinsam mit dem neuen Mitglied aus und lass es unten auf dem Tablet unterschreiben.")

# --- FORMULAR ---
with st.form("anmeldung_form"):
    st.subheader("👤 Persönliche Daten")
    col1, col2 = st.columns(2)
    with col1:
        vorname = st.text_input("Vorname")
        nachname = st.text_input("Nachname")
        geburtsdatum = st.text_input("Geburtsdatum")
    with col2:
        email = st.text_input("E-Mail-Adresse")
        telefon = st.text_input("Telefonnummer")
        adresse = st.text_input("Adresse (Straße, PLZ, Ort)")

    st.subheader("🏋️ Training & Vertrag")
    col_t1, col_t2 = st.columns(2)
    with col_t1:
        tarif = st.selectbox(
            "Tarifauswahl", 
            [
                "Kurse 2x wöchentlich 59€", 
                "Kleingruppen-Personal-Training 1x wöchentlich 99€", 
                "Kleingruppen-Personal-Training 2x wöchentich 179€"
            ]
        )
        erfahrung = st.selectbox("Bisherige Trainingserfahrung", ["Keine", "Anfänger", "Fortgeschritten", "Profi"])
    with col_t2:
        ziele = st.text_area("Ziele des Trainings")

    st.subheader("📄 Rechtliches & Zustimmung")
    
    st.markdown("""
    **Allgemeine Vertragsbedingungen:**

    • **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.

    • **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.

    • **Kündigungsfrist:** 2 Wochen zum Monatsende
    """)
    
    agb_akzeptiert = st.checkbox("Ich akzeptiere die Vertragsbedingungen und AGB.")
    datenschutz_akzeptiert = st.checkbox("Ich stimme der Datenverarbeitung gemäß Datenschutzerklärung zu.")
    haftungsausschluss = st.checkbox("Haftungsausschluss zur Kenntnis genommen.")

    st.subheader("🖋️ Unterschrift")
    st.write("Bitte hier im weißen Feld unterschreiben:")
    
    # Das digitale Unterschriftsfeld
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 1)", 
        stroke_width=3,
        stroke_color="#000000",
        background_color="#FFFFFF",
        height=200,
        width=700,
        drawing_mode="freedraw",
        key="canvas",
    )

    submit_button = st.form_submit_button("✅ Mitglied verbindlich anmelden")

# --- LOGIK BEIM ABSENDEN ---
if submit_button:
    if not vorname or not nachname or not email:
        st.error("⚠️ Bitte mindestens Vorname, Nachname und E-Mail ausfüllen!")
        st.stop()
        
    if not agb_akzeptiert or not datenschutz_akzeptiert or not haftungsausschluss:
        st.error("⚠️ Bitte bestätige alle rechtlichen Bedingungen (AGB, Datenschutz, Haftungsausschluss)!")
        st.stop()

    with st.spinner("Verarbeite Anmeldung... (Google Tabelle, E-Mail & Cloud werden synchronisiert)"):
        try:
            # 1. DATEN IN GOOGLE SHEETS SPEICHERN
            conn = st.connection("gsheets", type=GSheetsConnection)
            SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)

            neues_mitglied = pd.DataFrame([{
                "Datum": datetime.now().strftime("%d.%m.%Y"),
                "Vorname": vorname,
                "Nachname": nachname,
                "Geburtsdatum": geburtsdatum,
                "E-Mail": email,
                "Telefon": telefon,
                "Adresse": adresse,
                "Tarif": tarif,
                "Erfahrung": erfahrung,
                "Ziele": ziele
            }])
            df_aktualisiert = pd.concat([df, neues_mitglied], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_aktualisiert)

            # 2. WILLKOMMENS-E-MAIL MIT PDFS VERSENDEN
            sender_email = st.secrets["email"]["absender"]
            sender_password = st.secrets["email"]["passwort"] 
            smtp_server = st.secrets["email"]["smtp_server"]
            smtp_port = st.secrets["email"]["smtp_port"]

            msg = MIMEMultipart()
            msg['From'] = sender_email
            msg['To'] = email
            msg['Subject'] = "Willkommen im Hinkelfit Studio! 🏋️"

            text = f"Hallo {vorname},\n\nherzlich willkommen im Hinkelfit Studio! Wir freuen uns, dich an Bord zu haben.\n\nAnbei findest du deine Vertragsunterlagen, unsere Hausordnung sowie den Ernährungskompass als PDF-Dateien.\n\nSportliche Grüße,\nDein Hinkelfit-Team"
            msg.attach(MIMEText(text, 'plain', 'utf-8'))

            # PDFs aus dem GitHub-Ordner anhängen
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
                    st.warning(f"Angehängte Datei nicht gefunden: {pdf_name}")

            # E-Mail Absenden über IONOS
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            # 3. GOOGLE DRIVE ORDNER ANLEGEN & UNTERSCHRIFT HOCHLADEN
            if canvas_result.image_data is not None:
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
                ordner_name = f"{nachname}_{vorname}_{datetime.now().strftime('%d%m%Y')}"

                file_metadata = {
                    'name': ordner_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [hauptordner_id]
                }
                folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                neu_ordner_id = folder.get('id')

                img_data = canvas_result.image_data
                image = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                media = MediaIoBaseUpload(img_byte_arr, mimetype='image/png', resumable=True)
                file_metadata_sig = {'name': 'Unterschrift.png', 'parents': [neu_ordner_id]}
                drive_service.files().create(body=file_metadata_sig, media_body=media, fields='id').execute()

            st.success(f"🎉 {vorname} {nachname} wurde erfolgreich angelegt, die E-Mail verschickt und der Cloud-Ordner erstellt!")

        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")
