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

# --- INITIALISIERUNG ---
if "step" not in st.session_state: st.session_state.step = 1
# Buttons für den Status
if "agb_ok" not in st.session_state: st.session_state.agb_ok = False
if "dsgvo_ok" not in st.session_state: st.session_state.dsgvo_ok = False
if "anamnese_bestaetigt" not in st.session_state: st.session_state.anamnese_bestaetigt = False

# Session State Keys für Stabilität
if "vorname" not in st.session_state: st.session_state.vorname = ""
if "nachname" not in st.session_state: st.session_state.nachname = ""
if "email" not in st.session_state: st.session_state.email = ""

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
        adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)")
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.email)
        telefon = st.text_input("Telefonnummer")
        geburtsdatum = st.text_input("Geburtsdatum")

    st.subheader("🏋️ 2. Tarif & Ziele")
    tarif = st.selectbox("Tarifauswahl", [
        "Kurse 2x wöchentlich, 59€ pro Monat", 
        "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", 
        "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
    ])
    ziele = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"])

    st.subheader("📄 3. Vertrag & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="b_agb"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz:** Ich willige ausdrücklich ein, dass meine personenbezogenen Daten zur Verwaltung der Mitgliedschaft verarbeitet werden.""")
    if st.button("✅ Einwilligung Datenverarbeitung akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅", key="b_dsgvo"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        # Hier die explizite Validierung:
        if not st.session_state.vorname:
            st.error("⚠️ Vorname fehlt!")
        elif not st.session_state.nachname:
            st.error("⚠️ Nachname fehlt!")
        elif not st.session_state.email:
            st.error("⚠️ E-Mail-Adresse fehlt!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte akzeptiere zuerst AGB und Datenschutz!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreibe!")
        else:
            st.session_state.member_data = {
                "vorname": st.session_state.vorname, "nachname": st.session_state.nachname, 
                "email": st.session_state.email, "tarif": tarif, "adresse": adresse, 
                "telefon": telefon, "dob": geburtsdatum, "ziele": ", ".join(ziele), 
                "signature": canvas_result.image_data
            }
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
    
    st.markdown("---")
    st.info("""**Wahrheitspflicht & Risikoaufklärung:**\n
1. **Wahrheitspflicht:** Ich bestätige, dass alle meine Angaben wahrheitsgemäß und vollständig sind. Änderungen teile ich sofort mit.\n
2. **Risikoaufklärung:** Ich bin mir der körperlichen Belastung und des Verletzungsrisikos bewusst. Ich befolge die Anweisungen des Trainers.\n
3. **Haftung:** Ich akzeptiere die Haftungsbeschränkung für Sachschäden und Wertgegenstände.""")
    
    if st.button("✅ Anamnese wahrheitsgemäß bestätigt" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅", key="b_ana"):
        st.session_state.anamnese_bestaetigt = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte bestätige zuerst die Wahrheitspflicht & Risikoaufklärung!")
        else:
            with st.spinner("Verarbeite Anmeldung..."):
                # Hier kommt dein Code für Sheets/E-Mail/Drive...
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.success("✅ Alles erledigt!")
    if st.button("🔄 Neues Mitglied"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]: st.session_state[key] = (1 if key == "step" else False)
         st.session_state.vorname = ""; st.session_state.nachname = ""; st.session_state.email = ""
         st.rerun()
