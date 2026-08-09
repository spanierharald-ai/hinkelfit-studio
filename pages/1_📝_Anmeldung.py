import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import io
from datetime import datetime
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

# --- SICHERHEITSCHECK ---
if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst über die Startseite ein.")
    st.stop()

st.title("📝 Neues Mitglied anmelden")
st.write("Fülle das Formular gemeinsam mit dem neuen Mitglied aus und lass es unten auf dem Tablet unterschreiben.")

# --- FORMULAR ---
with st.form("anmeldung_form"):
    col1, col2 = st.columns(2)
    with col1:
        vorname = st.text_input("Vorname")
        nachname = st.text_input("Nachname")
    with col2:
        email = st.text_input("E-Mail-Adresse")
        telefon = st.text_input("Telefonnummer")

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

    with st.spinner("Verarbeite Anmeldung... (Google Tabelle, E-Mail & Cloud werden synchronisiert)"):
        try:
            # 1. DATEN IN GOOGLE SHEETS SPEICHERN
            conn = st.connection("gsheets", type=GSheetsConnection)
            # URL muss zu der aus deinen Secrets passen oder hier direkt hinterlegt sein
            SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)

            neues_mitglied = pd.DataFrame([{
                "Datum": datetime.now().strftime("%d.%m.%Y"),
                "Vorname": vorname,
                "Nachname": nachname,
                "E-Mail": email,
                "Telefon": telefon
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
                # Zugangsdaten aus dem connections.gsheets Block nutzen
                creds_dict = st.secrets["connections"]["gsheets"]
                scopes = ['https://www.googleapis.com/auth/drive']
                
                # Credentials aus den Secrets aufbauen
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

                # Unterordner erstellen
                file_metadata = {
                    'name': ordner_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [hauptordner_id]
                }
                folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                neu_ordner_id = folder.get('id')

                # Unterschrift als Bild formatieren
                img_data = canvas_result.image_data
                image = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                # Bild in den neuen Ordner hochladen
                media = MediaIoBaseUpload(img_byte_arr, mimetype='image/png', resumable=True)
                file_metadata_sig = {'name': 'Unterschrift.png', 'parents': [neu_ordner_id]}
                drive_service.files().create(body=file_metadata_sig, media_body=media, fields='id').execute()

            st.success(f"🎉 {vorname} {nachname} wurde erfolgreich angelegt, die E-Mail verschickt und der Cloud-Ordner erstellt!")

        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
import os
import io
from datetime import datetime
from PIL import Image
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

# --- SICHERHEITSCHECK ---
if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst über die Startseite ein.")
    st.stop()

st.title("📝 Neues Mitglied anmelden")
st.write("Fülle das Formular gemeinsam mit dem neuen Mitglied aus und lass es unten auf dem Tablet unterschreiben.")

# --- FORMULAR ---
with st.form("anmeldung_form"):
    col1, col2 = st.columns(2)
    with col1:
        vorname = st.text_input("Vorname")
        nachname = st.text_input("Nachname")
    with col2:
        email = st.text_input("E-Mail-Adresse")
        telefon = st.text_input("Telefonnummer")

    st.subheader("🖋️ Unterschrift")
    st.write("Bitte hier im weißen Feld unterschreiben:")
    
    # Das digitale Unterschriftsfeld
    canvas_result = st_canvas(
        fill_color="rgba(255, 255, 255, 1)", 
        stroke_width=3,
        stroke_color="#000000",
        background_color="#EEEEEE",
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

    with st.spinner("Verarbeite Anmeldung... (Google Tabelle, E-Mail & Cloud werden synchronisiert)"):
        try:
            # 1. DATEN IN GOOGLE SHEETS SPEICHERN
            conn = st.connection("gsheets", type=GSheetsConnection)
            SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
            df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)

            neues_mitglied = pd.DataFrame([{
                "Datum": datetime.now().strftime("%d.%m.%Y"),
                "Vorname": vorname,
                "Nachname": nachname,
                "E-Mail": email,
                "Telefon": telefon
            }])
            df_aktualisiert = pd.concat([df, neues_mitglied], ignore_index=True)
            conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_aktualisiert)

            # 2. WILLKOMMENS-E-MAIL MIT PDFS VERSENDEN
            sender_email = st.secrets["email"]["adresse"]
            sender_password = st.secrets["email"]["passwort"] 

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

            # E-Mail Absenden (Standard: Gmail-Server)
            server = smtplib.SMTP('smtp.ionos.de', 587)
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
            server.quit()

            # 3. GOOGLE DRIVE ORDNER ANLEGEN & UNTERSCHRIFT HOCHLADEN
            if canvas_result.image_data is not None:
                # Zugangsdaten (die gleichen, die du für die Tabelle nutzt)
                creds_dict = st.secrets["connections"]["gsheets"]
                scopes = ['https://www.googleapis.com/auth/drive']
                creds = service_account.Credentials.from_service_account_info(creds_dict, scopes=scopes)
                drive_service = build('drive', 'v3', credentials=creds)

                hauptordner_id = st.secrets["drive"]["hauptordner_id"]
                ordner_name = f"{nachname}_{vorname}_{datetime.now().strftime('%d%m%Y')}"

                # Unterordner erstellen
                file_metadata = {
                    'name': ordner_name,
                    'mimeType': 'application/vnd.google-apps.folder',
                    'parents': [hauptordner_id]
                }
                folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                neu_ordner_id = folder.get('id')

                # Unterschrift als Bild formatieren
                img_data = canvas_result.image_data
                image = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                # Bild in den neuen Ordner hochladen
                media = MediaIoBaseUpload(img_byte_arr, mimetype='image/png', resumable=True)
                file_metadata_sig = {'name': 'Unterschrift.png', 'parents': [neu_ordner_id]}
                drive_service.files().create(body=file_metadata_sig, media_body=media, fields='id').execute()

            st.success(f"🎉 {vorname} {nachname} wurde erfolgreich angelegt, die E-Mail verschickt und der Cloud-Ordner erstellt!")

        except Exception as e:
            st.error(f"❌ Fehler bei der Verarbeitung: {e}")import datetime
import os
import shutil
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
import pandas as pd
from PIL import Image, ImageDraw, ImageFont
from weasyprint import HTML
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration (Muss in Multipage-Apps ganz oben stehen)
st.set_page_config(
    page_title="Hinkelfit Onboarding", page_icon="💪", layout="centered"
)

# Session State initialisieren
if "step" not in st.session_state:
    st.session_state.step = 1
if "customer_name" not in st.session_state:
    st.session_state.customer_name = ""
if "selected_tariff" not in st.session_state:
    st.session_state.selected_tariff = ""

# Absolute Pfade für das Hinkelfit-System (PDFs & Ordnerstruktur bleiben lokal)
BASE_DIR = r"C:\Users\carol\Desktop\HinkelFit\Planung Wittislingen\Anmeldung"

# --- GOOGLE SHEETS VERBINDUNG (Ersetzt die lokale CSV) ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# -------------------------------------------------------------------------
# SCHRITT 1: VERTRAGSERSTELLUNG & TARIFAUSWAHL
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("Hinkelfit – Digitale Mitgliedschaft")
    st.write("Bitte gib deine Daten ein und wähle deinen Tarif, um den Vertrag abzuschließen.")

    with st.form("contract_form"):
        name = st.text_input("Vollständiger Name")
        address = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)")
        email = st.text_input("E-Mail-Adresse")
        phone = st.text_input("Telefonnummer / Mobilnummer (für WhatsApp & Rückfragen)")

        dob = st.date_input(
            "Geburtsdatum",
            value=datetime.date(1990, 1, 1),
            min_value=datetime.date(1900, 1, 1),
            max_value=datetime.date.today(),
            format="DD.MM.YYYY",
        )

        st.markdown("---")
        st.markdown("### Tarifwahl & Bedingungen")

        tariff = st.selectbox(
            "Wähle deinen Tarif:",
            [
                "1x die Woche - 99€ pro Monat",
                "2x die Woche - 179€ pro Monat",
                "Kurse 2x die Woche - 59€ pro Monat",
            ],
        )

        st.info(
            "**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** "
            "Die Vergütung ist nach Rechnungsstellung per Überweisung auf das in "
            "der Rechnung angegebene Bankkonto zu entrichten.\n\n"
            "• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden "
            "bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n"
            "• **Kündigungsfrist:** 2 Wochen zum Monatsende"
        )

        contract_accepted = st.checkbox(
            "Ich stimme den Vertragsbedingungen, den AGB, der Hausordnung und der Datenschutzerklärung zu. *"
        )

        st.markdown("### Digitale Unterschrift")
        typed_signature = st.text_input(
            "Tippe deinen vollständigen Namen als digitale rechtsverbindliche Unterschrift ein: *"
        )

        submit_contract = st.form_submit_button("Vertrag digital unterschreiben & Anamnesebogen starten")

        if submit_contract:
            if not name or not address or not email:
                st.error("Bitte fülle alle persönlichen Pflichtfelder (Name, Anschrift, E-Mail) aus.")
            elif not typed_signature.strip():
                st.error("Bitte tippe deinen Namen als digitale Unterschrift in das Textfeld ein.")
            elif not contract_accepted:
                st.error("Bitte akzeptiere die Vertragsbedingungen.")
            else:
                st.session_state.customer_name = name
                st.session_state.selected_tariff = tariff

                safe_name = name.strip().replace(" ", "_")
                member_dir = os.path.join(BASE_DIR, "mitglieder", safe_name)
                os.makedirs(member_dir, exist_ok=True)

                # --- 1. DATEN AUS GOOGLE SHEETS LESEN ---
                try:
                    df_central = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
                    # Leere Google-Zeilen entfernen
                    df_central = df_central.dropna(how="all")
                except Exception:
                    df_central = pd.DataFrame()

                # --- 2. NÄCHSTE MITGLIEDS-ID BERECHNEN ---
                if not df_central.empty and "Mitglieder_ID" in df_central.columns:
                    nums = []
                    for id_str in df_central["Mitglieder_ID"].dropna():
                        try:
                            num = int(str(id_str).replace("HF-", ""))
                            nums.append(num)
                        except:
                            pass
                    next_num = max(nums) + 1 if nums else 1
                else:
                    next_num = 1
                    
                member_id = f"HF-{next_num:03d}"

                # --- 3. NEUEN DATENSATZ ERSTELLEN ---
                new_record = pd.DataFrame([{
                    "Mitglieder_ID": member_id,
                    "Name": name,
                    "Anschrift": address,
                    "Email": email,
                    "Telefonnummer": phone,
                    "Geburtsdatum": str(dob.strftime("%d.%m.%Y")), 
                    "Tarif": tariff,
                    "Beitrittsdatum": str(datetime.date.today().strftime("%d.%m.%Y")),
                    "Status": "Aktiv",
                    "Gesundheits_Notizen": "" 
                }])

                if not df_central.empty:
                    df_central = pd.concat([df_central, new_record], ignore_index=True)
                else:
                    df_central = new_record
                    
                # --- 4. DATEN ZURÜCK IN GOOGLE SHEETS SCHREIBEN ---
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_central)
                st.cache_data.clear() # Wichtig, damit die App die neue Zeile sofort bemerkt

                # --- LOKALE PDF- & E-MAIL-VERARBEITUNG BLEIBT UNVERÄNDERT ---
                sig_path = os.path.join(member_dir, f"Unterschrift_{safe_name}.png")
                img = Image.new("RGB", (350, 80), color=(255, 255, 255))
                d = ImageDraw.Draw(img)
                try:
                    font = ImageFont.truetype("arial.ttf", 22)
                except:
                    font = ImageFont.load_default()
                d.text((15, 25), typed_signature, fill=(0, 0, 0), font=font)
                img.save(sig_path)

                html_contract = f"""
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.5; font-size: 13px; }}
                        h1 {{ color: #111; border-bottom: 2px solid #333; padding-bottom: 5px; font-size: 18px; }}
                        h3 {{ color: #444; margin-top: 15px; font-size: 14px; }}
                        .field {{ margin-bottom: 8px; }}
                        .label {{ font-weight: bold; color: #222; }}
                        .box {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 10px; margin-top: 10px; }}
                    </style>
                </head>
                <body>
                    <h1>Hinkelfit - Mitgliedschaftsvertrag</h1>
                    <div class="field"><span class="label">Mitglieds-ID:</span> {member_id}</div>
                    <div class="field"><span class="label">Studio:</span> Hinkelfit, Papiermühlweg 27, 89407 Wittislingen</div>
                    <div class="field"><span class="label">Datum:</span> {datetime.date.today().strftime('%d.%m.%Y')}</div>
                    
                    <h3>Mitgliedsdaten</h3>
                    <div class="field"><span class="label">Name:</span> {name}</div>
                    <div class="field"><span class="label">Anschrift:</span> {address}</div>
                    <div class="field"><span class="label">E-Mail:</span> {email}</div>
                    <div class="field"><span class="label">Telefon:</span> {phone if phone else 'Keine Angabe'}</div>
                    <div class="field"><span class="label">Geburtsdatum:</span> {dob.strftime('%d.%m.%Y')}</div>
                    
                    <h3>Gewählter Tarif & Konditionen</h3>
                    <div class="box">
                        <strong>Tarif:</strong> {tariff}<br><br>
                        • <strong>Zahlung:</strong> Nach Rechnungsstellung per Überweisung.<br>
                        • <strong>Kündigungsfrist:</strong> 2 Wochen zum Monatsende
                    </div>
                    
                    <h3>Digitale Unterschrift</h3>
                    <div class="field">Rechtsverbindlich digital unterschrieben von <strong>{typed_signature}</strong> am {datetime.date.today().strftime('%d.%m.%Y')}</div>
                    <img src="file:///{sig_path.replace(chr(92), '/')}" style="margin-top: 5px; border: 1px solid #ccc; width: 200px;">
                </body>
                </html>
                """

                contract_filename = os.path.join(member_dir, f"Vertrag_{safe_name}.pdf")
                try:
                    HTML(string=html_contract).write_pdf(contract_filename)
                except Exception as e:
                    st.error(f"Fehler bei der PDF-Erstellung: {e}")

                vorlagen = {
                    "AGB": os.path.join(BASE_DIR, "Allgemeine Geschäftsbedingungen.pdf"),
                    "Hausordnung": os.path.join(BASE_DIR, "Hausordnung.pdf"),
                    "Datenschutz": os.path.join(BASE_DIR, "Datenschutzerklärung.pdf"),
                    "Willkommen": os.path.join(BASE_DIR, "Willkommen.pdf"),
                    "Ernährungskompass": os.path.join(BASE_DIR, "Ernährungskompass.pdf"),
                }

                dateien_zum_senden = [contract_filename]
                for bezeichnung, absoluter_pfad in vorlagen.items():
                    if os.path.exists(absoluter_pfad):
                        ziel_pfad = os.path.join(member_dir, f"{bezeichnung}_{safe_name}.pdf")
                        shutil.copy(absoluter_pfad, ziel_pfad)
                        dateien_zum_senden.append(ziel_pfad)

                # E-MAIL VERSAND
                try:
                    email_secrets = st.secrets.get("email", {})
                    SENDER_EMAIL = email_secrets.get("absender", "fit@hinkelfit.de")
                    SENDER_PASSWORD = email_secrets.get("passwort", "")
                    SMTP_SERVER = email_secrets.get("smtp_server", "smtp.strato.de")
                    SMTP_PORT = int(email_secrets.get("smtp_port", 587))

                    msg = MIMEMultipart("mixed")
                    msg["From"] = SENDER_EMAIL
                    msg["To"] = email
                    msg["Subject"] = "Deine Mitgliedschaft bei Hinkelfit – Verträge & Unterlagen"

                    msg_related = MIMEMultipart("related")
                    msg.attach(msg_related)

                    vorname = name.split()[0] if name else "neues Mitglied"
                    
                    body_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <div style="display:none;font-size:1px;color:#333333;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
                            Vielen Dank für deinen Vertragsschluss! Hier sind deine Unterlagen.
                        </div>
                        <p>Hallo {vorname},</p>
                        <p>vielen Dank für deinen Vertragsschluss bei Hinkelfit! Deine Mitgliedsnummer ist {member_id}.</p>
                        <p>Im Anhang findest du deinen unterschriebenen Mitgliedschaftsvertrag sowie alle wichtigen Unterlagen und Willkommensinformationen.</p>
                        <br>
                        <p>Sportliche Grüße<br>Harald</p>
                        <br>
                        <img src="cid:logo" alt="Hinkelfit Logo" style="width: 250px;">
                    </body>
                    </html>
                    """
                    msg_related.attach(MIMEText(body_html, "html", "utf-8"))

                    logo_path = os.path.join(BASE_DIR, "Logo heller Hintergrund.jpg")
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as img_file:
                            logo_part = MIMEImage(img_file.read())
                            logo_part.add_header('Content-ID', '<logo>')
                            logo_part.add_header('Content-Disposition', 'inline', filename="logo.jpg")
                            msg_related.attach(logo_part)

                    for pfad in dateien_zum_senden:
                        if os.path.exists(pfad):
                            with open(pfad, "rb") as attachment:
                                part = MIMEBase("application", "octet-stream")
                                part.set_payload(attachment.read())
                            encoders.encode_base64(part)
                            filename = os.path.basename(pfad)
                            part.add_header("Content-Disposition", "attachment", filename=filename)
                            msg.attach(part)

                    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)
                    server.quit()

                except Exception as e:
                    st.warning(f"Hinweis zum E-Mail-Versand: {e}")

                st.session_state.step = 2
                st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESEBOGEN
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.success(f"Vielen Dank, {st.session_state.customer_name}! Dein Vertrag wurde erfolgreich unterzeichnet.")
    st.title("Hinkelfit – Anamnesebogen & Gesundheitsstatus")
    st.write("Bitte fülle nun den Anamnesebogen vollständig aus, um den Onboarding-Prozess abzuschließen.")

    with st.form("anamnesis_form"):
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

        st.subheader("5. Trainingserfahrung & Ziele")
        experience = st.selectbox(
            "Wie schätzt du deine Trainingserfahrung im Krafttraining ein?",
            ["Anfänger (weniger als 6 Monate)", "Leicht fortgeschritten (6 Monate bis 2 Jahre)", "Fortgeschritten (über 2 Jahre)"]
        )
        main_goal = st.multiselect(
            "Was sind deine Hauptziele bei Hinkelfit?",
            ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"]
        )

        st.markdown("---")
        st.subheader("6. Risiko- und Haftungserklärung")
        st.info("""**1. Gesundheitliche Eigenverantwortung & Wahrheitsgemäße Angaben**
* **Eigenverantwortung:** Der Kunde versichert, dass er gesund ist und keine gesundheitlichen Einschränkungen vorliegen, die einer Teilnahme am Training entgegenstehen.
* **Wahrheitspflicht:** Alle Angaben im Anamnesebogen wurden vollständig und wahrheitsgemäß gemacht. Veränderungen des Gesundheitszustandes sind dem Trainer vor jedem Training unaufgefordert mitzuteilen.
* **Ärztliche Abklärung:** Bei Zweifeln an der gesundheitlichen Eignung verpflichtet sich der Kunde, vor der Teilnahme einen Arzt zu konsultieren.

**2. Risikoaufklärung**
* **Körperliche Belastung:** Dem Kunden ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit hohen körperlichen Belastungen verbunden ist.
* **Verletzungsrisiko:** Trotz fachgerechter Anleitung und korrekter Übungsausführung können Verletzungen (z. B. Muskel-, Sehnen- und Gelenkverletzungen) nicht gänzlich ausgeschlossen werden.
* **Sofortiger Trainingsstopp:** Der Kunde verpflichtet sich, das Training bei Schwindel, Unwohlsein oder akuten Schmerzen sofort abzubrechen und den Trainer zu informieren.

**3. Haftungsbeschränkung**
* **Körperschäden:** Der Dienstleister haftet unbeschränkt für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, die auf einer vorsätzlichen oder fahrlässigen Pflichtverletzung beruhen.
* **Sach- und Vermögensschäden:** Für sonstige Schäden haftet der Dienstleister nur bei Vorsatz oder grober Fahrlässigkeit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt.
* **Wertgegenstände:** Für den Verlust oder Diebstahl von mitgebrachten Kleidungsstücken und Wertgegenständen wird keine Haftung übernommen.

**4. Befolgen von Anweisungen**
* Den Anweisungen des Trainers bezüglich Übungsausführung und Sicherheitsbestimmungen ist stets Folge zu leisten. Eigenmächtiges Abweichen erfolgt auf eigene Gefahr.""")

        liability_accepted = st.checkbox("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *")

        st.subheader("7. Datenschutzerklärung")
        st.info("""**Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):**
Ich willige ausdrücklich ein, dass meine gesundheitsbezogenen Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte (PDF) erfolgt im geschützten Cloud-Speicher Google Drive (Google Ireland Ltd.). Diese Einwilligung kann ich jederzeit mit Wirkung für die Zukunft widerrufen.""")

        privacy_accepted = st.checkbox("Ich willige in die Verarbeitung meiner gesundheitsbezogenen Daten ein. *")

        anamnese_submitted = st.form_submit_button("Anamnesebogen absenden & abschließen")

        if anamnese_submitted:
            if not liability_accepted or not privacy_accepted:
                st.error("Bitte akzeptiere sowohl den Haftungsausschluss als auch die Datenschutzerklärung.")
            else:
                safe_name = st.session_state.customer_name.strip().replace(" ", "_")
                member_dir = os.path.join(BASE_DIR, "mitglieder", safe_name)
                os.makedirs(member_dir, exist_ok=True)

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
                
                # --- GESUNDHEITS-NOTIZEN IN GOOGLE SHEETS SCHREIBEN ---
                try:
                    df_central = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
                    df_central = df_central.dropna(how="all")
                    
                    if "Gesundheits_Notizen" not in df_central.columns:
                        df_central["Gesundheits_Notizen"] = ""
                        
                    df_central["Gesundheits_Notizen"] = df_central["Gesundheits_Notizen"].astype(str)
                    df_central.loc[df_central["Name"] == st.session_state.customer_name, "Gesundheits_Notizen"] = warnhinweis
                    
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_central)
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Fehler beim Speichern der Notizen in der Cloud: {e}")
                # ------------------------------------------------

                html_anamnese = f"""
                <html>
                <head>
                    <meta charset="utf-8">
                    <style>
                        body {{ font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.4; font-size: 12px; }}
                        h1 {{ color: #111; border-bottom: 2px solid #333; padding-bottom: 5px; font-size: 16px; }}
                        h3 {{ color: #444; margin-top: 10px; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 2px; }}
                        .field {{ margin-bottom: 8px; }}
                        .label {{ font-weight: bold; color: #222; }}
                        .box {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 8px; margin-top: 5px; font-size: 11px; }}
                        .legal-text {{ font-size: 10px; color: #444; margin-bottom: 10px; line-height: 1.3; text-align: justify; }}
                    </style>
                </head>
                <body>
                    <h1>Hinkelfit - Anamnesebogen</h1>
                    <div class="field"><span class="label">Mitglied:</span> {st.session_state.customer_name}</div>
                    <div class="field"><span class="label">Gewählter Tarif:</span> {st.session_state.selected_tariff}</div>
                    <div class="field"><span class="label">Datum:</span> {datetime.date.today().strftime('%d.%m.%Y')}</div>
                    
                    <h3>1. Herz-Kreislauf-System und Gefäße</h3>
                    <div class="field">Beschwerden / Angaben: {', '.join(cv_list) if cv_list else 'Keine Auffälligkeiten'}</div>
                    
                    <h3>2. Bewegungsapparat, Gelenke und Wirbelsäule</h3>
                    <div class="field">Beschwerden / Angaben: {', '.join(ms_list) if ms_list else 'Keine Auffälligkeiten'}</div>
                    
                    <h3>3. Stoffwechsel, Organe und Atmung</h3>
                    <div class="field">Beschwerden / Angaben: {', '.join(met_list) if met_list else 'Keine Auffälligkeiten'}</div>
                    
                    <h3>4. Operationen, Verletzungen und Medikamente</h3>
                    <div class="field">{surgeries_meds if surgeries_meds else 'Keine Angaben'}</div>
                    
                    <h3>5. Trainingserfahrung & Ziele</h3>
                    <div class="field"><span class="label">Krafttraining-Erfahrung:</span> {experience}</div>
                    <div class="field"><span class="label">Hauptziele bei Hinkelfit:</span> {', '.join(main_goal) if main_goal else 'Keine Angaben'}</div>
                    
                    <h3>6. Risiko- und Haftungserklärung</h3>
                    <div class="legal-text">
                        <strong>1. Gesundheitliche Eigenverantwortung & Wahrheitsgemäße Angaben</strong><br>
                        <strong>Eigenverantwortung:</strong> Der Kunde versichert, dass er gesund ist und keine gesundheitlichen Einschränkungen vorliegen, die einer Teilnahme am Training entgegenstehen.<br>
                        <strong>Wahrheitspflicht:</strong> Alle Angaben im Anamnesebogen wurden vollständig und wahrheitsgemäß gemacht. Veränderungen des Gesundheitszustandes sind dem Trainer vor jedem Training unaufgefordert mitzuteilen.<br>
                        <strong>Ärztliche Abklärung:</strong> Bei Zweifeln an der gesundheitlichen Eignung verpflichtet sich der Kunde, vor der Teilnahme einen Arzt zu konsultieren.<br><br>

                        <strong>2. Risikoaufklärung</strong><br>
                        <strong>Körperliche Belastung:</strong> Dem Kunden ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit hohen körperlichen Belastungen verbunden ist.<br>
                        <strong>Verletzungsrisiko:</strong> Trotz fachgerechter Anleitung und korrekter Übungsausführung können Verletzungen (z. B. Muskel-, Sehnen- und Gelenkverletzungen) nicht gänzlich ausgeschlossen werden.<br>
                        <strong>Sofortiger Trainingsstopp:</strong> Der Kunde verpflichtet sich, das Training bei Schwindel, Unwohlsein oder akuten Schmerzen sofort abzubrechen und den Trainer zu informieren.<br><br>

                        <strong>3. Haftungsbeschränkung</strong><br>
                        <strong>Körperschäden:</strong> Der Dienstleister haftet unbeschränkt für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, die auf einer vorsätzlichen oder fahrlässigen Pflichtverletzung beruhen.<br>
                        <strong>Sach- und Vermögensschäden:</strong> Für sonstige Schäden haftet der Dienstleister nur bei Vorsatz oder grober Fahrlässigkeit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt.<br>
                        <strong>Wertgegenstände:</strong> Für den Verlust oder Diebstahl von mitgebrachten Kleidungsstücken und Wertgegenständen wird keine Haftung übernommen.<br><br>

                        <strong>4. Befolgen von Anweisungen</strong><br>
                        Den Anweisungen des Trainers bezüglich Übungsausführung und Sicherheitsbestimmungen ist stets Folge zu leisten. Eigenmächtiges Abweichen erfolgt auf eigene Gefahr.
                    </div>
                    
                    <h3>7. Datenschutzerklärung</h3>
                    <div class="legal-text">
                        <strong>Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):</strong><br>
                        Ich willige ausdrücklich ein, dass meine gesundheitsbezogenen Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte (PDF) erfolgt im geschützten Cloud-Speicher Google Drive (Google Ireland Ltd.). Diese Einwilligung kann ich jederzeit mit Wirkung für die Zukunft widerrufen.
                    </div>
                    
                    <div class="box" style="margin-top: 15px;">
                        <strong>Bestätigung:</strong> Die Risiko- und Haftungserklärung sowie die Datenschutzerklärung wurden durch den Kunden digital akzeptiert am {datetime.date.today().strftime('%d.%m.%Y')} um {datetime.datetime.now().strftime('%H:%M')} Uhr.
                    </div>
                </body>
                </html>
                """

                anamnese_filename = os.path.join(member_dir, f"Anamnese_{safe_name}.pdf")
                try:
                    HTML(string=html_anamnese).write_pdf(anamnese_filename)
                except Exception as e:
                    st.error(f"Fehler bei der Anamnese-PDF-Erstellung: {e}")

                st.balloons()
                st.success("Vielen Dank! Deine Registrierung, der Vertrag und der Anamnesebogen wurden erfolgreich im System hinterlegt.")
                
    st.markdown("---")
    if st.button("🔄 Neues Mitglied anlegen (Reset)"):
        st.session_state.step = 1
        st.session_state.customer_name = ""
        st.session_state.selected_tariff = ""
        st.rerun()
