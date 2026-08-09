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

# Session State für alle Felder initialisieren, damit sie auf Tablets stabil bleiben
if "step" not in st.session_state: st.session_state.step = 1
defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", "telefon": "", "adresse": "",
    "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", "experience": "Anfänger (weniger als 6 Monate)",
    "main_goal": [], "agb": False, "haftung": False, "datenschutz": False, "signature": None
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

    st.markdown("---")
    st.subheader("🏋️ 2. Tarif & Ziele")
    st.session_state.tarif = st.selectbox("Tarifauswahl", 
        ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"],
        index=["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"].index(st.session_state.tarif)
    )
    st.session_state.experience = st.selectbox("Trainingserfahrung", ["Anfänger (weniger als 6 Monate)", "Leicht fortgeschritten (6 Monate bis 2 Jahre)", "Fortgeschritten (über 2 Jahre)"])
    st.session_state.main_goal = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.main_goal)

    st.markdown("---")
    st.subheader("📄 3. Rechtliches & Zustimmung")
    
    st.info("""**Allgemeine Vertragsbedingungen:**\n
• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n
• **Terminabsage & Stornierung:** 48 Stunden vorher.\n
• **Kündigungsfrist:** 2 Wochen zum Monatsende""")
    st.session_state.agb = st.checkbox("Ich akzeptiere die Vertragsbedingungen und AGB. *", value=st.session_state.agb)
    
    st.info("""**Haftungsausschluss:** ... (Kurzfassung für Platz) ...""")
    st.session_state.haftung = st.checkbox("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *", value=st.session_state.haftung)
    
    st.info("""**Datenschutz:** ... (Einwilligung Art. 9 DSGVO) ...""")
    st.session_state.datenschutz = st.checkbox("Ich willige in die Verarbeitung meiner Gesundheitsdaten ein. *", value=st.session_state.datenschutz)

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("✅ Mitglied anmelden & weiter zur Anamnese"):
        if not st.session_state.vorname or not st.session_state.nachname or not st.session_state.email:
            st.error("⚠️ Bitte Pflichtfelder ausfüllen!")
        elif not (st.session_state.agb and st.session_state.haftung and st.session_state.datenschutz):
            st.error("⚠️ Bitte alle Rechtshaken setzen!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreiben!")
        else:
            st.session_state.member_data["signature"] = canvas_result.image_data
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE (Wie gehabt)
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    # ... (Dein Anamnese-Code hier) ...
    # Wenn du hier auch Probleme mit Toggles hast, tausche einfach alle st.toggle gegen st.checkbox aus!
