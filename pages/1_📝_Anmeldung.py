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
for key in ["agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]:
    if key not in st.session_state: st.session_state[key] = False

# Session State für Anamnese
health_keys = ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen", 
               "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden",
               "Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]
for k in health_keys:
    if k not in st.session_state: st.session_state[k] = False

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
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
    ziele = st.multiselect("Was sind deine Hauptziele bei Hinkelfit?", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"])

    st.subheader("📄 Vertrag & Zustimmung")
    st.info("""**Allgemeine Vertragsbedingungen:**
• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.
• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.
• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅"):
        st.session_state.agb_ok = True
    
    st.info("""**Datenschutz:** Ich willige ausdrücklich ein, dass meine personenbezogenen Daten zur Verwaltung der Mitgliedschaft durch Hinkelfit verarbeitet werden.""")
    if st.button("✅ Einwilligung Datenverarbeitung akzeptieren" if not st.session_state.dsgvo_ok else "Datenverarbeitung akzeptiert ✅"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ Digitale Unterschrift")
    canvas_result = st_canvas(fill_color="rgba(255, 255, 255, 1)", stroke_width=3, stroke_color="#000000", background_color="#EEEEEE", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not (vorname and nachname and email):
            st.error("⚠️ Bitte Pflichtfelder ausfüllen!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte bestätige AGB und Datenschutz!")
        elif canvas_result.image_data is None:
            st.error("⚠️ Bitte unterschreibe!")
        else:
            st.session_state.member_data = {"vorname": vorname, "nachname": nachname, "email": email, "tarif": tarif, "adresse": adresse, "telefon": telefon, "dob": geburtsdatum, "ziele": ", ".join(ziele), "signature": canvas_result.image_data}
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    
    def btn_toggle(k): st.session_state[k] = not st.session_state[k]

    st.write("### 1. Herz-Kreislauf-System")
    st.write("Leiden Sie unter Vorerkrankungen des Herz-Kreislauf-Systems?")
    for k in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"]:
        if st.button(f"{k} {'✅' if st.session_state[k] else ''}", key=f"b_{k}"): btn_toggle(k)
    cardio_other = st.text_input("Sonstiges/Details zum Herz-Kreislauf-System:")

    st.write("### 2. Bewegungsapparat & Wirbelsäule")
    st.write("Haben Sie Beschwerden im Bereich des Bewegungsapparates?")
    for k in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"]:
        if st.button(f"{k} {'✅' if st.session_state[k] else ''}", key=f"b_{k}"): btn_toggle(k)
    ms_other = st.text_input("Sonstiges/Details zum Bewegungsapparat:")

    st.write("### 3. Stoffwechsel & Organe")
    st.write("Liegen bei Ihnen Stoffwechsel- oder Atemwegserkrankungen vor?")
    for k in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]:
        if st.button(f"{k} {'✅' if st.session_state[k] else ''}", key=f"b_{k}"): btn_toggle(k)
    met_other = st.text_input("Sonstiges/Details Stoffwechsel & Organe:")

    surgeries_meds = st.text_area("Gab es Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein?")
    
    st.markdown("---")
    st.subheader("📄 Rechtliche Bestätigung")
    st.info("""**Wahrheitspflicht & Risikoaufklärung:**\n
1. **Wahrheitspflicht:** Ich bestätige, dass alle meine Angaben im Anamnesebogen vollständig und wahrheitsgemäß sind. Veränderungen meines Gesundheitszustandes teile ich dem Trainer vor jedem Training unaufgefordert mit.\n
2. **Risikoaufklärung:** Mir ist bewusst, dass intensives Kraft-, Ausdauer- und Funktionstraining mit körperlichen Belastungen verbunden ist. Ich verpflichte mich bei Schwindel oder Schmerzen zum sofortigen Trainingsstopp.\n
3. **Haftung:** Ich akzeptiere die Haftungsbeschränkung für Sachschäden und den Verlust von mitgebrachten Wertgegenständen.""")
    
    if st.button("✅ Ich bestätige die Wahrheitspflicht & Risikoaufklärung" if not st.session_state.anamnese_bestaetigt else "Bestätigt ✅"):
        st.session_state.anamnese_bestaetigt = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not st.session_state.anamnese_bestaetigt:
            st.error("⚠️ Bitte bestätige zuerst die Wahrheitspflicht & Risikoaufklärung!")
        else:
            with st.spinner("Verarbeite Anmeldung..."):
                # Hier läuft dein gewohnter Code (Google Sheets/Drive/E-Mail)...
                st.session_state.step = 3
                st.rerun()

elif st.session_state.step == 3:
    st.balloons()
    st.success("🎉 Registrierung erfolgreich!")
    if st.button("🔄 Neues Mitglied"):
         for key in ["step", "agb_ok", "dsgvo_ok", "anamnese_bestaetigt"] + health_keys: 
             st.session_state[key] = (1 if key == "step" else False)
         st.rerun()
