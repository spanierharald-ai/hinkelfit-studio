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

# Session State für Stabilität auf Tablets
if "step" not in st.session_state: st.session_state.step = 1
# Initialisierung der Felder, falls noch nicht vorhanden
defaults = {
    "vorname": "", "nachname": "", "geburtsdatum": "", "email": "", "telefon": "", "adresse": "",
    "tarif": "Kurse 2x wöchentlich, 59€ pro Monat", "experience": "Anfänger", "main_goal": [],
    "agb": False, "haftung": False, "datenschutz": False, "signature": None
}
for key, val in defaults.items():
    if key not in st.session_state: st.session_state[key] = val

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Neues Mitglied anmelden")
    
    # 1. Persönliche Daten
    st.subheader("👤 1. Persönliche Daten")
    st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.vorname)
    st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.nachname)
    st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.geburtsdatum)
    st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
    st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.telefon)
    st.session_state.adresse = st.text_input("Adresse", value=st.session_state.adresse)

    # 2. Tarif & Ziele
    st.subheader("🏋️ 2. Tarif & Ziele")
    st.session_state.tarif = st.selectbox("Tarifauswahl", 
        ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"],
        index=["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"].index(st.session_state.tarif)
    )
    st.session_state.main_goal = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.main_goal)

    # 3. Rechtliches (JETZT MIT VIEL PLATZ)
    st.subheader("📄 3. Rechtliches & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n
• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n
• **Terminabsage & Stornierung:** 48 Stunden vorher.\n
• **Kündigungsfrist:** 2 Wochen zum Monatsende""")
    
    st.session_state.agb = st.checkbox("Ich akzeptiere die Vertragsbedingungen und AGB. *", value=st.session_state.agb)
    st.write("---")
    
    st.info("""**Haftungsausschluss:** Eigenverantwortung, Risikoaufklärung, Haftungsbeschränkung (Wahrheitspflicht, Sofortiger Trainingsstopp, etc.).""")
    st.session_state.haftung = st.checkbox("Ich habe die Risiko- und Haftungserklärung gelesen und akzeptiere diese. *", value=st.session_state.haftung)
    st.write("---")
    
    st.info("""**Datenschutz:** Einwilligung in die Datenverarbeitung (Art. 9 DSGVO).""")
    st.session_state.datenschutz = st.checkbox("Ich willige in die Verarbeitung meiner Gesundheitsdaten ein. *", value=st.session_state.datenschutz)

    # 4. Unterschrift
    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("✅ Weiter zur Anamnese"):
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
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen")
    # Hier gleiches Prinzip: Keine Forms, direkte Eingaben
    st.write("Herz-Kreislauf, Gelenke, etc. ... (deine Felder hier einfügen)")
    if st.button("✅ Registrierung abschließen"):
        # ... (Logik wie vorher)
        st.session_state.step = 3
        st.rerun()

elif st.session_state.step == 3:
    st.success("✅ Erledigt!")
    if st.button("🔄 Neues Mitglied"):
         st.session_state.step = 1
         st.rerun()
