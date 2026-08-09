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
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseUpload
from PIL import Image, ImageDraw, ImageFont
from weasyprint import HTML
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
for key in ["agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]:
    if key not in st.session_state: st.session_state[key] = False

# Session State Keys
defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", "telefon": "", "adresse": "",
    "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", "ziele": [], "signature": None
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Anmeldung")
    st.write("Schön, dass du dabei bist! Lass uns gemeinsam deine Mitgliedschaft startklar machen.")
    
    st.subheader("👤 Deine Daten")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.vorname)
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.nachname)
        st.session_state.adresse = st.text_input("Anschrift (Straße, PLZ, Ort)", value=st.session_state.adresse)
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.telefon)
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.geburtsdatum)

    st.subheader("🏋️ Tarif & Ziele")
    st.session_state.tarif = st.selectbox("Wähle deinen Tarif:", [
        "Kurse 2x wöchentlich, 59€ pro Monat", 
        "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
        "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
    ])
    ziele = st.multiselect("Was sind deine Hauptziele bei Hinkelfit?", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"])

    st.subheader("📄 Vertrag & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können von dir bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz:** Ich willige ausdrücklich ein, dass meine personenbezogenen Daten zur Verwaltung der Mitgliedschaft durch Hinkelfit verarbeitet werden.""")
    if st.button("✅ Einwilligung Datenverarbeitung akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Bitte Pflichtfelder (Vorname, Nachname, E-Mail) ausfüllen!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte akzeptiere zuerst AGB und Datenschutz!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreibe!")
        else:
            st.session_state.member_data = {
                "vorname": st.session_state.vorname, "nachname": st.session_state.nachname, 
                "email": st.session_state.email, "tarif": st.session_state.tarif, "adresse": st.session_state.adresse, 
                "telefon": st.session_state.telefon, "dob": st.session_state.geburtsdatum, "ziele": ", ".join(ziele), 
                "signature": canvas_result.image_data
            }
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Dein Gesundheitsstatus")
    
    def btn_toggle(k): st.session_state[k] = not st.session_state[k]
    
    # Anamnese Felder (Du-Form)
    st.write("### Herz-Kreislauf-System")
    for k in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k) else ''}", key=f"b_{k}"): btn_toggle(k)
    
    st.write("### Bewegungsapparat & Wirbelsäule")
    for k in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Wirbelsäulenbeschwerden"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k) else ''}", key=f"b_{k}"): btn_toggle(k)
        
    st.write("### Stoffwechsel, Organe & Atmung")
    for k in ["Diabetes", "Asthma", "Krämpfe", "Epilepsie", "Organerkrankungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k) else ''}", key=f"b_{k}"): btn_toggle(k)
        
    surgeries_meds = st.text_area("Gab es in den letzten 5 Jahren Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein?")
    
    st.markdown("---")
    st.subheader("📄 Haftung & Wahrheitspflicht")
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
    
    if st.button("✅ Anamnese wahrheitsgemäß bestätigt" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅", key="b_ana"):
        st.session_state.anamnese_bestaetigt = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte bestätige zuerst die Wahrheitspflicht & Risikoaufklärung!")
        else:
            with st.spinner("Verarbeite Daten und erstelle deine Akte..."):
                # --- HIER WÜRDE DEINE DRIVE/SHEETS/EMAIL-LOGIK FOLGEN ---
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.balloons()
    st.success("🎉 Alles erledigt! Deine Mitgliedschaft bei Hinkelfit ist nun aktiv.")
    if st.button("🔄 Neues Mitglied"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]: 
             st.session_state[key] = (1 if key == "step" else False)
         st.session_state.member_data = {}
         st.rerun()
