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

if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst ein.")
    st.stop()

# --- INITIALISIERUNG ---
if "step" not in st.session_state: 
    st.session_state.step = 1

# Status-Flags für sämtliche Zustimmungen
status_keys = ["agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]
for key in status_keys:
    if key not in st.session_state: 
        st.session_state[key] = False

# Anamnese-Schlüssel initialisieren
health_keys = [
    "Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen",
    "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden",
    "Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"
]
for k in health_keys:
    if k not in st.session_state: 
        st.session_state[k] = False

defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", 
    "telefon": "", "adresse": "", "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", 
    "ziele": [], "signature": None
}
for key, val in defaults.items():
    if key not in st.session_state: 
        st.session_state[key] = val

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG (DATEN, TARIF, AGB, DATENSCHUTZ, UNTERSCHRIFT)
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
    st.subheader("👤 Persönliche Daten")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.vorname)
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.nachname)
        st.session_state.adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)", value=st.session_state.adresse)
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.telefon)
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.geburtsdatum)

    st.subheader("🏋️ Tarif & Ziele")
    tarife = [
        "Kurse 2x wöchentlich, 59€ pro Monat", 
        "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
        "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
    ]
    if st.session_state.tarif not in tarife:
        st.session_state.tarif = tarife[0]

    st.session_state.tarif = st.selectbox(
        "Wähle deinen Tarif:", 
        tarife, 
        index=tarife.index(st.session_state.tarif)
    )
    
    st.session_state.ziele = st.multiselect(
        "Was sind deine Hauptziele bei Hinkelfit?", 
        ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], 
        default=st.session_state.ziele
    )

    st.subheader("📄 Vertrag & Allgemeine Bedingungen")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz (Art. 9 DSGVO):**\nDas Mitglied willigt ausdrücklich ein, dass personenbezogene und gesundheitsbezogene Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt im geschützten Cloud-Speicher Google Drive. Diese Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden.""")
    if st.button("✅ Datenschutzerklärung akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅", key="btn_dsgvo"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ Digitale Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Bitte Pflichtfelder (Vorname, Nachname, E-Mail) ausfüllen!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte akzeptiere zuerst AGB und Datenschutz!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreibe!")
        else:
            st.session_state.signature = canvas_result.image_data
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE & RECHTLICHE ERKLÄRUNGEN
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    
    if st.button("⬅️ Zurück zur Anmeldung"):
        st.session_state.step = 1
        st.rerun()
    
    def btn_toggle(k): 
        st.session_state[k] = not st.session_state[k]
    
    st.subheader("1. Herz-Kreislauf-System und Gefäße")
    st.write("Leidest du unter Vorerkrankungen des Herz-Kreislauf-Systems?")
    for k in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): 
            btn_toggle(k)
    cardio_other = st.text_input("Sonstiges / Weitere Details zu Vorerkrankungen des Herz-Kreislauf-Sytems:")

    st.subheader("2. Bewegungsapparat, Gelenke und Wirbelsäule")
    st.write("Hast du Beschwerden im Bereich des Bewegungsapparates?")
    for k in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): 
            btn_toggle(k)
    ms_other = st.text_input("Sonstiges / Weitere Details zum Bewegungsapparat:")

    st.subheader("3. Stoffwechsel, Organe und Atmung")
    st.write("Liegen bei dir Stoffwechsel- oder Atemwegserkrankungen vor?")
    for k in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): 
            btn_toggle(k)
    met_other = st.text_input("Sonstiges / Weitere Details zu Stoffwechsel & Organen:")

    st.subheader("4. Operationen, Verletzungen und Medikamente")
    surgeries_meds = st.text_area("Gab es in den letzten 5 Jahren Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein, die das Training beeinträchtigen?")
    
    st.markdown("---")
    st.subheader("5. Wahrheitspflicht")
    st.info("""**Wahrheitsgemäße Angaben:**\n
• **Wahrheitspflicht:** Das Mitglied versichert, dass alle Angaben im Anamnesebogen vollständig und wahrheitsgemäß gemacht wurden. Veränderungen des Gesundheitszustandes sind dem Trainer vor jedem Training unaufgefordert mitzuteilen.\n
• **Ärztliche Abklärung:** Bei Zweifeln an der gesundheitlichen Eignung verpflichtet sich das Mitglied, vor der Teilnahme einen Arzt zu konsultieren.""")
    if st.button("✅ Wahrheitspflicht bestätigen" if not st.session_state.wahrheit_ok else "Wahrheitspflicht bestätigt ✅", key="btn_wahrheit"):
        st.session_state.wahrheit_ok = True

    st.subheader("6. Risikoaufklärung")
    st.info("""**Risikoaufklärung:**\n
• **Körperliche Belastung:** Dem Mitglied ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit hohen körperlichen Belastungen verbunden ist.\n
• **Verletzungsrisiko:** Trotz fachgerechter Anleitung und korrekter Übungsausführung können Verletzungen (z. B. Muskel-, Sehnen- und Gelenkverletzungen) nicht gänzlich ausgeschlossen worden sein.\n
• **Sofortiger Trainingsstopp:** Das Mitglied verpflichtet sich, das Training bei Schwindel, Unwohlsein oder akuten Schmerzen sofort abzubrechen und den Trainer zu informieren.""")
    if st.button("✅ Risikoaufklärung bestätigen" if not st.session_state.risiko_ok else "Risikoaufklärung bestätigt ✅", key="btn_risiko"):
        st.session_state.risiko_ok = True

    st.subheader("7. Haftungsausschluss")
    st.info("""**Haftungsbeschränkung:**\n
• **Körperschäden:** Der Dienstleister haftet unbeschränkt für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, die auf einer vorsätzlichen oder fahrlässigen Pflichtverletzung beruhen.\n
• **Sach- und Vermögensschäden:** Für sonstige Schäden haftet der Dienstleister nur bei Vorsatz oder grober Fahrlässigkeit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt.\n
• **Wertgegenstände:** Für den Verlust oder Diebstahl von mitgebrachten Kleidungsstücken und Wertgegenständen wird keine Haftung übernommen.\n
• **Befolgen von Anweisungen:** Den Anweisungen des Trainers bezüglich Übungsausführung und Sicherheitsbestimmungen ist stets Folge zu leisten. Eigenmächtiges Abweichen erfolgt auf eigene Gefahr.""")
    if st.button("✅ Haftungsausschluss bestätigen" if not st.session_state.haftung_ok else "Haftungsausschluss bestätigt ✅", key="btn_haftung"):
        st.session_state.haftung_ok = True

    st.markdown("---")
    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not (st.session_state.wahrheit_ok and st.session_state.risiko_ok and st.session_state.haftung_ok):
            st.error("⚠️ Bitte bestätige separat die Wahrheitspflicht, die Risikoaufklärung und den Haftungsausschluss!")
        else:
            with st.spinner("Verarbeite Anmeldung, speichere Daten und versende E-Mail..."):
                try:
                    # Gesundheitsnotizen zusammenfassen
                    cv_list = [c for c in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"] if st.session_state.get(c)]
                    if cardio_other: cv_list.append(cardio_other)
                    
                    ms_list = [c for c in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"] if st.session_state.get(c)]
                    if ms_other: ms_list.append(ms_other)
                    
                    met_list = [c for c in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"] if st.session_state.get(c)]
                    if met_other: met_list.append(met_other)
                    
                    all_notes = cv_list + ms_list + met_list
                    if surgeries_meds.strip():
                        all_notes.append(f"OPs/Meds: {surgeries_meds}")
                    warnhinweis = ", ".join(all_notes)

                    # 1. Google Sheets aktualisieren
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
                    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
                    
                    neues_mitglied = pd.DataFrame([{
                        "Datum": datetime.now().strftime("%d.%m.%Y"),
                        "Vorname": st.session_state.vorname, 
                        "Nachname": st.session_state.nachname,
                        "Geburtsdatum": st.session_state.geburtsdatum, 
                        "E-Mail": st.session_state.email,
                        "Telefon": st.session_state.telefon, 
                        "Adresse": st.session_state.adresse,
                        "Tarif": st.session_state.tarif, 
                        "Ziele": ", ".join(st.session_state.ziele), 
                        "Gesundheits_Notizen": warnhinweis
                    }])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=pd.concat([df, neues_mitglied], ignore_index=True))

                    # 2. E-Mail mit Anhängen aus dem GitHub-Ordner "pdfs" versenden
                    sender_email = st.secrets["email"]["absender"]
                    server = smtplib.SMTP(st.secrets["email"]["smtp_server"], int(st.secrets["email"]["smtp_port"]))
                    server.starttls()
                    server.login(sender_email, st.secrets["email"]["passwort"])
                    
                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    msg['To'] = st.session_state.email
                    msg['Subject'] = "Willkommen im Hinkelfit Studio! 🏋️"
                    
                    text_body = f"Hallo {st.session_state.vorname},\n\nherzlich willkommen im Hinkelfit Studio! Wir freuen uns, dich an Bord zu haben.\n\nAnbei findest du deine Vertragsunterlagen, unsere Hausordnung sowie den Ernährungskompass als PDF-Dateien.\n\nSportliche Grüße,\nDein Hinkelfit-Team"
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
                    ordner_name = f"{st.session_state.nachname}_{st.session_state.vorname}_{datetime.now().strftime('%d%m%Y')}"

                    file_metadata = {
                        'name': ordner_name,
                        'mimeType': 'application/vnd.google-apps.folder',
                        'parents': [hauptordner_id]
                    }
                    folder = drive_service.files().create(body=file_metadata, fields='id').execute()
                    neu_ordner_id = folder.get('id')

                    img_data = st.session_state.signature
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

elif st.session_state.step == 3:
    st.balloons()
    st.success("🎉 Registrierung erfolgreich! Die Daten wurden gespeichert, die E-Mail mit den Anhängen wurde versendet und der Google Drive Ordner wurde erstellt.")
    if st.button("🔄 Neues Mitglied anlegen"):
         # Alle Status-Flags, Anamnese-Zweige und Eingabefelder komplett leeren
         for key in ["step", "agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"] + health_keys: 
             st.session_state[key] = (1 if key == "step" else False)
         st.session_state.vorname = ""
         st.session_state.nachname = ""
         st.session_state.email = ""
         st.session_state.telefon = ""
         st.session_state.adresse = ""
         st.session_state.geburtsdatum = ""
         st.session_state.ziele = []
         st.session_state.signature = None
         st.rerun()
