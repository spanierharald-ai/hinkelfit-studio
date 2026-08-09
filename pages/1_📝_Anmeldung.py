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
    st.warning("🔒 Bitte logge dich zuerst über die Startseite ein.")
    st.stop()

# --- INITIALISIERUNG ---
if "step" not in st.session_state: st.session_state.step = 1
# WICHTIG: Keys für persistente Checkboxen auf Tablets
if "agb" not in st.session_state: st.session_state.agb = False
if "haftung" not in st.session_state: st.session_state.haftung = False
if "datenschutz" not in st.session_state: st.session_state.datenschutz = False

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Neues Mitglied anmelden")

    # Layout: Persönliche Daten wieder in Spalten
    st.subheader("👤 Persönliche Daten")
    col1, col2 = st.columns(2)
    with col1:
        vorname = st.text_input("Vorname *")
        nachname = st.text_input("Nachname *")
        adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)")
    with col2:
        email = st.text_input("E-Mail-Adresse *")
        telefon = st.text_input("Telefonnummer")
        geburtsdatum = st.text_input("Geburtsdatum")

    st.subheader("🏋️ Tarif & Ziele")
    tarif = st.selectbox("Wähle deinen Tarif:", [
        "Kurse 2x wöchentlich, 59€ pro Monat", 
        "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
        "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
    ])
    ziele = st.text_area("Ziele des Trainings")

    st.subheader("📄 Vertrag & Haftung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung sofort per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Monatsende""")
    
    # Checkboxen hier einzeln, damit sie auf Tablets groß genug sind
    st.session_state.agb = st.checkbox("Ich stimme den Vertragsbedingungen, den AGB, der Hausordnung und der Datenschutzerklärung zu. *", value=st.session_state.agb)

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
    st.session_state.haftung = st.checkbox("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *", value=st.session_state.haftung)

    st.info("""**Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):**
Ich willige ausdrücklich ein, dass meine gesundheitsbezogenen Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte (PDF) erfolgt im geschützten Cloud-Speicher Google Drive. Diese Einwilligung kann ich jederzeit mit Wirkung für die Zukunft widerrufen.""")
    st.session_state.datenschutz = st.checkbox("Ich willige in die Verarbeitung meiner Gesundheitsdaten ein. *", value=st.session_state.datenschutz)

    st.subheader("🖋️ Digitale Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("✅ Vertrag unterzeichnen & Anamnese starten"):
        if not (vorname and nachname and email):
            st.error("Bitte fülle Name und E-Mail aus.")
        elif not (st.session_state.agb and st.session_state.haftung and st.session_state.datenschutz):
            st.error("Bitte bestätige alle drei Rechtstexte!")
        elif canvas_result.image_data is None:
            st.error("Bitte unterschreibe!")
        else:
            st.session_state.member_data = {"vorname": vorname, "nachname": nachname, "email": email, "tarif": tarif, "signature": canvas_result.image_data}
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE (Logik unverändert)
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    # Hier deinen restlichen Code (Anamnese + Submit) einfügen
    # ...
