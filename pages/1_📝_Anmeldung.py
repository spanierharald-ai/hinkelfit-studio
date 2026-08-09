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

if "step" not in st.session_state:
    st.session_state.step = 1
if "member_data" not in st.session_state:
    st.session_state.member_data = {}

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Neues Mitglied anmelden")
    
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

    st.markdown("---")
    st.subheader("🏋️ 2. Tarif & Ziele")
    tarif = st.selectbox(
        "Tarifauswahl", 
        [
            "Kurse 2x wöchentlich, 59€ pro Monat", 
            "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
            "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
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

    st.markdown("---")
    st.subheader("📄 3. Rechtliches & Zustimmung")
    
    st.info("""**Allgemeine Vertragsbedingungen:**\n
• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n
• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n
• **Kündigungsfrist:** 2 Wochen zum Monatsende""")
    agb_akzeptiert = st.toggle("Ich akzeptiere die Vertragsbedingungen und AGB. *")
    
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
    haftungsausschluss = st.toggle("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *")
    
    st.info("""**Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):**
Ich willige ausdrücklich ein, dass meine gesundheitsbezogenen Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt im geschützten Cloud-Speicher Google Drive (Google Ireland Ltd.). Diese Einwilligung kann ich jederzeit mit Wirkung für die Zukunft widerrufen.""")
    datenschutz_akzeptiert = st.toggle("Ich willige in die Verarbeitung meiner gesundheitsbezogenen Daten ein. *")

    st.markdown("---")
    st.subheader("🖋️ 4. Unterschrift")
    st.write("Bitte hier im Feld unterschreiben:")
    
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

    if st.button("✅ Mitglied anmelden & weiter zur Anamnese"):
        if not vorname or not nachname or not email:
            st.error("⚠️ Bitte mindestens Vorname, Nachname und E-Mail ausfüllen!")
        elif not agb_akzeptiert or not datenschutz_akzeptiert or not haftungsausschluss:
            st.error("⚠️ Bitte aktiviere alle drei rechtlichen Schalter!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte eine Unterschrift eintragen!")
        else:
            st.session_state.member_data = {
                "vorname": vorname, "nachname": nachname, "geburtsdatum": geburtsdatum,
                "email": email, "telefon": telefon, "adresse": adresse,
                "tarif": tarif, "experience": experience, "main_goal": main_goal,
                "signature": canvas_result.image_data
            }
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESEBOGEN
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    
    # Hier können wir die Toggles direkt lassen, da sie hier keine Probleme machen
    st.write("**Herz-Kreislauf-System und Gefäße**")
    cb_bluthochdruck = st.toggle("Bluthochdruck")
    cb_herzinfarkt = st.toggle("Herzinfarkt (in der Vergangenheit)")
    cb_schlaganfall = st.toggle("Schlaganfall (in der Vergangenheit)")
    cb_rhythmus = st.toggle("Herzrhythmusstörungen")
    cardiovascular_other = st.text_input("Sonstiges / Weitere Details:")

    st.write("**Bewegungsapparat, Gelenke und Wirbelsäule**")
    cb_ruecken = st.toggle("Beschwerden im unteren Rücken / LWS")
    cb_gelenke = st.toggle("Gelenkbeschwerden (z. B. Schulter, Knie)")
    cb_artif_joint = st.toggle("Künstliches Gelenk")
    cb_wirbelsaeule = st.toggle("Sonstige Wirbelsäulenbeschwerden")
    musculoskeletal_other = st.text_input("Sonstiges / Weitere Details:")

    st.write("**Stoffwechsel, Organe und Atmung**")
    cb_diabetes = st.toggle("Diabetes mellitus")
    cb_asthma = st.toggle("Asthma / chron. Atemwegserkrankungen")
    cb_cramps = st.toggle("Neigung zu Krämpfen")
    cb_epilepsy = st.toggle("Epilepsie")
    cb_organe = st.toggle("Organerkrankungen (Niere, Leber etc.)")
    metabolism_other = st.text_input("Sonstiges / Weitere Details:")

    surgeries_meds = st.text_area("Operationen, Verletzungen oder Medikamente?")

    if st.button("✅ Registrierung abschließen"):
        with st.spinner("Verarbeite Anmeldung..."):
            try:
                # ... [DEINE BESTEHENDE LOGIK ZUR VERARBEITUNG BLEIBT HIER GLEICH] ...
                # (Ich habe den Block zur besseren Lesbarkeit hier verkürzt, 
                # der Code aus der vorherigen Nachricht funktioniert hier direkt weiter!)
                
                # [HIER WIRD DEIN LOGIK-BLOCK EINGEFÜGT]
                # ...
                st.session_state.step = 3
                st.rerun()
            except Exception as e:
                st.error(f"❌ Fehler: {e}")

elif st.session_state.step == 3:
    st.balloons()
    st.success("✅ Alles erledigt!")
    if st.button("🔄 Neues Mitglied anlegen"):
         st.session_state.step = 1
         st.rerun()
