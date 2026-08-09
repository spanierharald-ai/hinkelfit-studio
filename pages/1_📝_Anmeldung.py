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

for key in ["agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]:
    if key not in st.session_state: 
        st.session_state[key] = False

# Anamnese-Schlüssel sauber initialisieren
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
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
    st.subheader("👤 Deine Daten")
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

    st.subheader("📄 Vertrag & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können von dir bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz:** Ich willige ausdrücklich ein, dass meine personenbezogenen Daten zur Verwaltung der Mitgliedschaft durch Hinkelfit verarbeitet werden.""")
    if st.button("✅ Einwilligung Datenverarbeitung akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅", key="btn_dsgvo"):
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
# SCHRITT 2: ANAMNESE
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
    cardio_other = st.text_input("Sonstiges / Weitere Details zu Herz-Kreislauf:")

    st.subheader("2. Bewegungsapparat, Gelenke und Wirbelsäule")
    st.write("Hast du Beschwerden im Bereich des Bewegungsapparates?")
    for k in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): 
            btn_toggle(k)
    ms_other = st.text_input("Sonstiges / Weitere Details zum Bewegungsapparat:")

    st.subheader("3. Stoffwechsel, Organe und Atmung")
    st.write("Liegen bei dir Stoffwechsel- oder Atemwegserkrankungen vor?")
    for k in ["Diabetes", "Asthma", "Krämpfe", "Epilepsie", "Organerkrankungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): 
            btn_toggle(k)
    met_other = st.text_input("Sonstiges / Weitere Details zu Stoffwechsel & Organen:")

    st.subheader("4. Operationen, Verletzungen und Medikamente")
    surgeries_meds = st.text_area("Gab es in den letzten 5 Jahren Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein?")
    
    st.markdown("---")
    st.subheader("6. Risiko- und Haftungserklärung")
    st.info("""**1. Gesundheitliche Eigenverantwortung & Wahrheitsgemäße Angaben**
* **Eigenverantwortung:** Du versicherst, dass du gesund bist und keine gesundheitlichen Einschränkungen vorliegen, die einer Teilnahme am Training entgegenstehen.
* **Wahrheitspflicht:** Alle Angaben im Anamnesebogen wurden vollständig und wahrheitsgemäß gemacht. Veränderungen des Gesundheitszustandes teilst du mir vor jedem Training unaufgefordert mit.
* **Ärztliche Abklärung:** Bei Zweifeln an der gesundheitlichen Eignung verpflichtest du dich, vor der Teilnahme einen Arzt zu konsultieren.

**2. Risikoaufklärung**
* **Körperliche Belastung:** Dir ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit hohen körperlichen Belastungen verbunden ist.
* **Verletzungsrisiko:** Trotz fachgerechter Anleitung und korrekter Übungsausführung können Verletzungen (z. B. Muskel-, Sehnen- und Gelenkverletzungen) nicht gänzlich ausgeschlossen werden.
* **Sofortiger Trainingsstopp:** Du verpflichtest dich, das Training bei Schwindel, Unwohlsein oder akuten Schmerzen sofort abzubrechen und mich zu informieren.

**3. Haftungsbeschränkung**
* **Körperschäden:** Ich hafte unbeschränkt für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, die auf einer vorsätzlichen oder fahrlässigen Pflichtverletzung beruhen.
* **Sach- und Vermögensschäden:** Für sonstige Schäden hafte ich nur bei Vorsatz oder grober Fahrlässigkeit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt.
* **Wertgegenstände:** Für den Verlust oder Diebstahl von mitgebrachten Kleidungsstücken und Wertgegenständen wird keine Haftung übernommen.

**4. Befolgen von Anweisungen**
* Meinen Anweisungen bezüglich Übungsausführung und Sicherheitsbestimmungen ist stets Folge zu leisten. Eigenmächtiges Abweichen erfolgt auf eigene Gefahr.""")

    st.info("""**Einwilligung in die Datenverarbeitung (Art. 9 DSGVO):**
Ich willige ausdrücklich ein, dass meine gesundheitsbezogenen Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte (PDF) erfolgt im geschützten Cloud-Speicher Google Drive (Google Ireland Ltd.). Diese Einwilligung kann ich jederzeit mit Wirkung für die Zukunft widerrufen.""")
    
    if st.button("✅ Anamnese wahrheitsgemäß bestätigt" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅", key="b_ana"):
        st.session_state.anamnese_bestaetigt = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte bestätige zuerst die Wahrheitspflicht & Risikoaufklärung!")
        else:
            with st.spinner("Verarbeite Anmeldung..."):
                # Hier läuft die Logik (Google Sheets/E-Mail/Drive)...
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.balloons()
    st.success("🎉 Registrierung erfolgreich!")
    if st.button("🔄 Neues Mitglied"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"] + health_keys: 
             st.session_state[key] = (1 if key == "step" else False)
         st.session_state.vorname = ""
         st.session_state.nachname = ""
         st.session_state.email = ""
         st.rerun()
