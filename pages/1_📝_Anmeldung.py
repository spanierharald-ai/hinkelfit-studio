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
# Buttons für Status
for key in ["agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]:
    if key not in st.session_state: st.session_state[key] = False

# Anamnese-Zustände (Buttons statt Checkboxen)
health_keys = ["bluthochdruck", "herzinfarkt", "schlaganfall", "rhythmus", "ruecken", "gelenke", "artif_joint", "wirbelsaeule", "diabetes", "asthma", "cramps", "epilepsy", "organe"]
for k in health_keys:
    if k not in st.session_state: st.session_state[k] = False

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
    tarif = st.selectbox("Tarifauswahl", ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"])
    ziele = st.multiselect("Hauptziele", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.main_goal)

    st.subheader("📄 3. Vertrag & Zustimmung")
    st.info("**Allgemeine Vertragsbedingungen:** Zahlung sofort, 48h Storno, 2 Wochen Kündigungsfrist zum Laufzeitende.")
    if st.button("✅ AGB akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅"): st.session_state.agb_ok = True
    
    st.info("**Datenschutz:** Einwilligung in die Datenverarbeitung.")
    if st.button("✅ Datenschutz akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅"): st.session_state.dsgvo_ok = True

    st.subheader("🖋️ 4. Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Weiter zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Pflichtfelder fehlen!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte AGB & Datenschutz akzeptieren!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreiben!")
        else:
            st.session_state.member_data = {"vorname": st.session_state.vorname, "nachname": st.session_state.nachname, "email": st.session_state.email, "tarif": tarif, "adresse": st.session_state.adresse, "telefon": st.session_state.telefon, "dob": st.session_state.geburtsdatum, "ziele": ", ".join(ziele), "signature": canvas_result.image_data}
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen")
    
    # Helfer für Buttons
    def toggle(k): st.session_state[k] = not st.session_state[k]
    
    st.write("**Herz-Kreislauf-System**")
    for k in ["bluthochdruck", "herzinfarkt", "schlaganfall", "rhythmus"]:
        if st.button(f"{k.capitalize()} {'✅' if st.session_state[k] else ''}"): toggle(k)
    cardiovascular_other = st.text_input("Sonstiges Herz-Kreislauf:")

    st.write("**Bewegungsapparat**")
    for k in ["ruecken", "gelenke", "artif_joint", "wirbelsaeule"]:
        if st.button(f"{k.capitalize()} {'✅' if st.session_state[k] else ''}"): toggle(k)
    musculoskeletal_other = st.text_input("Sonstiges Bewegungsapparat:")

    st.write("**Stoffwechsel & Organe**")
    for k in ["diabetes", "asthma", "cramps", "epilepsy", "organe"]:
        if st.button(f"{k.capitalize()} {'✅' if st.session_state[k] else ''}"): toggle(k)
    metabolism_other = st.text_input("Sonstiges Stoffwechsel/Organe:")

    surgeries_meds = st.text_area("Operationen oder Medikamente?")
    
    st.markdown("---")
    st.info("**Wahrheitspflicht & Risikoaufklärung:** Ich bestätige alle Angaben wahrheitsgemäß und bin mir der körperlichen Risiken bewusst.")
    
    if st.button("✅ Anamnese wahrheitsgemäß bestätigt" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅"):
        st.session_state.anamnese_bestaetigt = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte Anamnese bestätigen!")
        else:
            with st.spinner("Verarbeite Anmeldung..."):
                # Hier kommt dein Code...
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.success("🎉 Alles erledigt!")
    if st.button("🔄 Neues Mitglied"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"] + health_keys: st.session_state[key] = (1 if key == "step" else False)
         st.session_state.vorname = ""; st.session_state.nachname = ""; st.session_state.email = ""
         st.rerun()
