import io
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from email.mime.base import MIMEBase
from email import encoders
from weasyprint import HTML
from PIL import Image
import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst ein.")
    st.stop()

# --- HELPER: RESET ---
def reset_app():
    for key in ["step", "agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
        st.session_state[key] = (1 if key == "step" else False)
    for k in health_keys: st.session_state[k] = False
    for key in ["vorname", "nachname", "email", "telefon", "adresse", "geburtsdatum", "signature", "pdf_bytes"]:
        st.session_state[key] = ("" if key not in ["signature", "pdf_bytes"] else None)
    st.session_state.ziele = []

# --- INITIALISIERUNG ---
if "step" not in st.session_state: st.session_state.step = 1
health_keys = ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen", "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden", "Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]
for k in health_keys:
    if k not in st.session_state: st.session_state[k] = False
for key in ["agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
    if key not in st.session_state: st.session_state[key] = False

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.get("vorname", ""))
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.get("nachname", ""))
        st.session_state.adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)", value=st.session_state.get("adresse", ""))
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.get("email", ""))
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.get("telefon", ""))
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.get("geburtsdatum", ""))

    st.session_state.tarif = st.selectbox("Wähle deinen Tarif:", ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"])
    st.session_state.ziele = st.multiselect("Was sind deine Hauptziele?", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.get("ziele", []))

    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"): st.session_state.agb_ok = True
    if st.button("✅ Datenschutzerklärung akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅", key="btn_dsgvo"): st.session_state.dsgvo_ok = True

    canvas_result = st_canvas(fill_color="#fff", stroke_width=3, stroke_color="#000", background_color="#eee", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Bitte alle Pflichtfelder ausfüllen!")
        else:
            st.session_state.signature = canvas_result.image_data
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE & RECHTSTEXTE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    if st.button("⬅️ Zurück"): st.session_state.step = 1; st.rerun()
    
    for k in health_keys:
        if st.button(f"{k} {'✅' if st.session_state[k] else ''}", key=f"b_{k}"): st.session_state[k] = not st.session_state[k]
    
    surgeries_meds = st.text_area("Operationen (letzte 5 Jahre) oder Medikamente?")
    
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

    st.info("""**Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):**\nDas Mitglied willigt ausdrücklich ein, dass personenbezogene und gesundheitsbezogene Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt im geschützten Cloud-Speicher. Diese Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden.""")

    if st.button("✅ Wahrheitspflicht bestätigen" if not st.session_state.wahrheit_ok else "Wahrheitspflicht bestätigt ✅", key="btn_wahrheit"): st.session_state.wahrheit_ok = True
    if st.button("✅ Risikoaufklärung bestätigen" if not st.session_state.risiko_ok else "Risikoaufklärung bestätigt ✅", key="btn_risiko"): st.session_state.risiko_ok = True
    if st.button("✅ Haftungsausschluss bestätigen" if not st.session_state.haftung_ok else "Haftungsausschluss bestätigt ✅", key="btn_haftung"): st.session_state.haftung_ok = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not (st.session_state.wahrheit_ok and st.session_state.risiko_ok and st.session_state.haftung_ok):
            st.error("⚠️ Bitte bestätige separat die Wahrheitspflicht, die Risikoaufklärung und den Haftungsausschluss!")
        else:
            with st.spinner("Erstelle Unterlagen..."):
                # PDF
                html = f"<h1>Mitgliedschaft: {st.session_state.vorname} {st.session_state.nachname}</h1>"
                pdf_bytes = HTML(string=html).write_pdf()
                st.session_state.pdf_bytes = pdf_bytes
                
                # E-Mail mit Logo
                sender = st.secrets["email"]["absender"]
                msg = MIMEMultipart("related")
                msg['From'] = sender
                msg['To'] = st.session_state.email
                msg['Bcc'] = sender
                msg['Subject'] = "Deine Unterlagen bei Hinkelfit"
                
                body = MIMEMultipart("alternative")
                body.attach(MIMEText("Hallo, anbei deine Unterlagen.", 'plain'))
                html_body = "<html><body><p>Hallo,</p><img src='cid:logo'></body></html>"
                body.attach(MIMEText(html_body, 'html'))
                msg.attach(body)
                
                # Logo anhängen
                with open("pdfs/Logo heller Hintergrund.jpg", "rb") as f:
                    logo = MIMEImage(f.read())
                    logo.add_header('Content-ID', '<logo>')
                    msg.attach(logo)
                
                # PDFs anhängen
                for p in ["Allgemeine Geschäftsbedingungen.pdf", "Datenschutzerklärung.pdf", "Ernährungskompass.pdf", "Hausordnung.pdf", "Willkommen.pdf"]:
                    with open(os.path.join("pdfs", p), "rb") as f:
                        part = MIMEApplication(f.read(), _subtype="pdf")
                        part.add_header('Content-Disposition', 'attachment', filename=p)
                        msg.attach(part)
                
                # Vertrag als PDF
                pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
                pdf_part.add_header('Content-Disposition', 'attachment', filename="Vertrag.pdf")
                msg.attach(pdf_part)
                
                server = smtplib.SMTP(st.secrets["email"]["smtp_server"], int(st.secrets["email"]["smtp_port"]))
                server.starttls(); server.login(sender, st.secrets["email"]["passwort"])
                server.send_message(msg); server.quit()
                
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.success("🎉 Anmeldung erledigt!")
    st.download_button("📥 Vertrag lokal speichern", data=st.session_state.pdf_bytes, file_name="Vertrag.pdf", mime="application/pdf")
    if st.button("🔄 Neues Mitglied"):
        reset_app()
        st.rerun()
