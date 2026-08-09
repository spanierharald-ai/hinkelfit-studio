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

# Session State initialisieren
if "step" not in st.session_state: st.session_state.step = 1
# Status für die Buttons
if "agb_ok" not in st.session_state: st.session_state.agb_ok = False
if "haftung_ok" not in st.session_state: st.session_state.haftung_ok = False
if "dsgvo_ok" not in st.session_state: st.session_state.dsgvo_ok = False

defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", "telefon": "", "adresse": "",
    "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", "experience": "Anfänger", "main_goal": [], "signature": None
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

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
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.geburtsdatum)
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.telefon)
        st.session_state.adresse = st.text_input("Adresse", value=st.session_state.adresse)

    st.subheader("🏋️ 2. Tarif & Ziele")
    st.session_state.tarif = st.selectbox("Tarifauswahl", 
        ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"])
    st.session_state.experience = st.selectbox("Trainingserfahrung", ["Anfänger (weniger als 6 Monate)", "Leicht fortgeschritten (6 Monate bis 2 Jahre)", "Fortgeschritten (über 2 Jahre)"])
    st.session_state.main_goal = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.main_goal)

    st.subheader("📄 3. Vertrag & Haftung")
    
    # AGB
    st.info("**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung sofort per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** 48 Stunden vorher.\n\n• **Kündigungsfrist:** 2 Wochen zum Monatsende")
    if st.button("✅ AGB akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅"):
        st.session_state.agb_ok = True
    
    # Haftung
    st.info("**Risiko- und Haftungserklärung:** Eigenverantwortung, Wahrheitspflicht, ärztliche Abklärung, Risikoaufklärung (körperliche Belastung, Verletzungsrisiko), Haftungsbeschränkung für Sach- und Personenschäden.")
    if st.button("✅ Haftungsausschluss akzeptieren" if not st.session_state.haftung_ok else "Haftungsausschluss akzeptiert ✅"):
        st.session_state.haftung_ok = True
        
    # Datenschutz
    st.info("**Datenschutz:** Einwilligung in die Datenverarbeitung (Art. 9 DSGVO) zur individuellen Trainingsplanung.")
    if st.button("✅ Datenschutz akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Anmeldung abschließen & weiter zur Anamnese"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Bitte Name und E-Mail ausfüllen!")
        elif not (st.session_state.agb_ok and st.session_state.haftung_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte erst alle drei Zustimmungen anklicken!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreiben!")
        else:
            st.session_state.member_data["signature"] = canvas_result.image_data
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen")
    cb_bluthochdruck = st.checkbox("Bluthochdruck")
    cb_herzinfarkt = st.checkbox("Herzinfarkt")
    cb_ruecken = st.checkbox("Rückenbeschwerden")
    surgeries_meds = st.text_area("Operationen oder Medikamente?")
    
    if st.button("✅ Registrierung finalisieren"):
        # Hier läuft deine bestehende Logik zum E-Mail-Versand und Drive-Upload...
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    st.success("✅ Alles erledigt!")
    if st.button("🔄 Neues Mitglied"):
         st.session_state.step = 1; st.session_state.member_data = {}; st.rerun()
