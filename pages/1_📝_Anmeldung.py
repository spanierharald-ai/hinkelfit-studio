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

# Session State initialisieren, um zwischen Anmeldung und Anamnese zu wechseln
if "step" not in st.session_state:
    st.session_state.step = 1
if "member_data" not in st.session_state:
    st.session_state.member_data = {}

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG & VERTRAG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Neues Mitglied anmelden")
    st.write("Fülle das Formular gemeinsam mit dem neuen Mitglied aus und lass es unten auf dem Tablet unterschreiben.")

    # Außerhalb der form, damit Checkboxen direkt klickbar reagieren
    st.subheader("📄 Rechtliches & Zustimmung")
    
    st.info("""**Allgemeine Vertragsbedingungen:**\n
• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n
• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n
• **Kündigungsfrist:** 2 Wochen zum Monatsende""")
    agb_akzeptiert = st.checkbox("Ich akzeptiere die Vertragsbedingungen und AGB. *", key="agb_check")

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
    haftungsausschluss = st.checkbox("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *", key="haftung_check")

    st.info("""**Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):**
Ich willige ausdrücklich ein, dass meine gesundheitsbezogenen Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt im geschützten Cloud-Speicher Google Drive (Google Ireland Ltd.). Diese Einwilligung kann ich jederzeit mit Wirkung für die Zukunft widerrufen.""")
    datenschutz_akzeptiert = st.checkbox("Ich willige in die Verarbeitung meiner gesundheitsbezogenen Daten ein. *", key="dsgvo_check")

    with st.form("anmeldung_form"):
        st.subheader("👤 1. Persönliche Daten")
        col1, col2 = st.columns(2)
        with col1:
            vorname = st.text_input("Vorname *")
            nachname = st.text_input("Nachname *")
            geburtsdatum = st.text_input("Geburtsdatum")
        with col2:
            email = st.text_input("E-Mail-Adresse *")
            telefon = st.text_input("Telefonnummer")
            adresse = st.text_input("Adresse (Straße, PLZ, Ort)")

        st.subheader("🏋️ 2. Tarif & Ziele")
        tarif = st.selectbox(
            "Tarifauswahl", 
            [
                "Kurse 2x wöchentlich 59€", 
                "Kleingruppen-Personal-Training 1x wöchentlich 99€", 
                "Kleingruppen-Personal-Training 2x wöchentich 179€"
            ]
        )
        experience = st.selectbox(
            "Wie schätzt du deine Trainingserfahrung im Krafttraining ein?",
            ["Anfänger (weniger als 6 Monate)", "Leicht fortgeschritten (6 Monate bis 2 Jahre)", "Fortgeschritten (über 2 Jahre)"]
        )
        main_goal = st.multiselect(
            "Was sind deine Hauptziele bei Hinkelfit?",
            ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"]
        )

        st.subheader("🖋️ 3. Unterschrift")
        st.write("Bitte hier im weißen Feld unterschreiben:")
        
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

        submit_button = st.form_submit_button("✅ Mitglied anmelden & weiter zur Anamnese")

    # --- LOGIK BEIM ABSENDEN (SCHRITT 1) ---
    if submit_button:
        if not vorname or not nachname or not email:
            st.error("⚠️ Bitte mindestens Vorname, Nachname und E-Mail ausfüllen!")
            st.stop()
            
        if not agb_akzeptiert or not datenschutz_akzeptiert or not haftungsausschluss:
            st.error("⚠️ Bitte bestätige alle rechtlichen Bedingungen (AGB, Haftungsausschluss, Datenschutz) oberhalb des Formulars!")
            st.stop()
            
        if canvas_result.image_data is None:
             st.error("⚠️ Bitte eine Unterschrift eintragen!")
             st.stop()

        # Daten zwischenspeichern für Schritt 2
        st.session_state.member_data = {
            "vorname": vorname,
            "nachname": nachname,
            "geburtsdatum": geburtsdatum,
            "email": email,
            "telefon": telefon,
            "adresse": adresse,
            "tarif": tarif,
            "experience": experience,
            "main_goal": main_goal,
            "signature": canvas_result.image_data
        }
        
        st.session_state.step = 2
        st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESEBOGEN
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    st.write(f"Vielen Dank, {st.session_state.member_data['vorname']}! Bitte fülle nun den Anamnesebogen aus.")

    with st.form("anamnese_form"):
        st.write("**Herz-Kreislauf-System und Gefäße**")
        cb_bluthochdruck = st.checkbox("Bluthochdruck")
        cb_herzinfarkt = st.checkbox("Herzinfarkt (in der Vergangenheit)")
        cb_schlaganfall = st.checkbox("Schlaganfall (in der Vergangenheit)")
        cb_rhythmus = st.checkbox("Herzrhythmusstörungen")
        cardiovascular_other = st.text_input("Sonstiges / Weitere Details zu Herz-Kreislauf:")

        st.write("**Bewegungsapparat, Gelenke und Wirbelsäule**")
        cb_ruecken = st.checkbox("Beschwerden im unteren Rücken / Lendenwirbelsäule")
        cb_gelenke = st.checkbox("Gelenkbeschwerden (z. B. Schulter, Knie)")
        cb_artif_joint = st.checkbox("Künstliches Gelenk vorhanden")
        cb_wirbelsaeule = st.checkbox("Sonstige Wirbelsäulenbeschwerden")
        musculoskeletal_other = st.text_input("Sonstiges / Weitere Details zum Bewegungsapparat:")

        st.write("**Stoffwechsel, Organe und Atmung**")
        cb_diabetes = st.checkbox("Diabetes mellitus")
        cb_asthma = st.checkbox("Asthma oder chronische Atemwegserkrankungen")
        cb_cramps = st.checkbox("Neigung zu Krämpfen")
        cb_epilepsy = st.checkbox("Epilepsie")
        cb_organe = st.checkbox("Erkrankungen der inneren Organe (Niere, Leber etc.)")
        metabolism_other = st.text_input("Sonstiges / Weitere Details zu Stoffwechsel & Organen:")

        st.write("**Operationen, Verletzungen und Medikamente**")
        surgeries_meds = st.text_area("Gab es Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein?")

        submit_anamnese = st.form_submit_button("✅ Registrierung abschließen")

    # --- LOGIK BEIM ABSENDEN (SCHRITT 2) ---
    if submit_anamnese:
        with st.spinner("Verarbeite Anmeldung... (Google Tabelle, E-Mail & Cloud werden synchronisiert)"):
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

                # Daten aus Session State holen
                m_data = st.session_state.member_data

                # 1. DATEN IN GOOGLE SHEETS SPEICHERN
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
                    "Erfahrung": m_data["experience"],
                    "Ziele": ", ".join(m_data["main_goal"]),
                    "Gesundheits_Notizen": warnhinweis
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
                    else:
                        st.warning(f"Angehängte Datei nicht gefunden: {pdf_name}")

                server = smtplib.SMTP(smtp_server, smtp_port)
                server.starttls()
                server.login(sender_email, sender_password)
                server.send_message(msg)
                server.quit()

                # 3. GOOGLE DRIVE ORDNER ANLEGEN & UNTERSCHRIFT HOCHLADEN
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

                # Unterschrift aus dem State holen und speichern
                img_data = m_data["signature"]
                image = Image.fromarray(img_data.astype('uint8'), 'RGBA')
                img_byte_arr = io.BytesIO()
                image.save(img_byte_arr, format='PNG')
                img_byte_arr.seek(0)

                media = MediaIoBaseUpload(img_byte_arr, mimetype='image/png', resumable=True)
                file_metadata_sig = {'name': 'Unterschrift.png', 'parents': [neu_ordner_id]}
                drive_service.files().create(body=file_metadata_sig, media_body=media, fields='id').execute()

                st.success(f"🎉 {m_data['vorname']} {m_data['nachname']} wurde erfolgreich angelegt, die E-Mail verschickt und der Cloud-Ordner erstellt!")
                
                # Zurücksetzen für das nächste Mitglied
                if st.button("🔄 Nächste Anmeldung starten"):
                     st.session_state.step = 1
                     st.session_state.member_data = {}
                     st.rerun()

            except Exception as e:
                st.error(f"❌ Fehler bei der Verarbeitung: {e}")
