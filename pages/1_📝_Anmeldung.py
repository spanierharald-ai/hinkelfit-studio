import base64
import io
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from weasyprint import HTML
from PIL import Image
import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import create_client

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst ein.")
    st.stop()

# --- SUPABASE VERBINDUNG INITIALISIEREN ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- HELPER: RESET ---
def reset_app():
    for key in ["step", "agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
        st.session_state[key] = (1 if key == "step" else False)
    for k in health_keys: 
        st.session_state[k] = False
    for key in ["vorname", "nachname", "email", "telefon", "adresse", "geburtsdatum", "vertragsstart", "signature", "pdf_bytes", "final_tarif"]:
        st.session_state[key] = ("" if key not in ["signature", "pdf_bytes"] else None)
    st.session_state.ziele = []

# --- INITIALISIERUNG ---
if "step" not in st.session_state: 
    st.session_state.step = 1

health_keys = [
    "Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen", 
    "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", 
    "Sonstige Wirbelsäulenbeschwerden", "Diabetes", "Asthma", 
    "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"
]

for k in health_keys:
    if k not in st.session_state: 
        st.session_state[k] = False

for key in ["agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
    if key not in st.session_state: 
        st.session_state[key] = False

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
    st.subheader("👤 Persönliche Daten")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.get("vorname", ""))
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.get("nachname", ""))
        st.session_state.adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)", value=st.session_state.get("adresse", ""))
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.get("email", ""))
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.get("telefon", ""))
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.get("geburtsdatum", ""))

    st.subheader("🏋️ Tarif & Ziele")
    tarife = [
        "Kurse: 1x wöchentlich 59€ pro Monat", 
        "Kleingruppen-Personaltraining 2x wöchentlich 179€ im Monat", 
        "Power Workshop 1x wöchentlich 99€ im Monat",
        "Firmenfitness (80€ je Stunde für alle 4 Mitarbeiter)"
    ]
    if st.session_state.get("tarif") not in tarife: 
        st.session_state.tarif = tarife[0]
        
    st.session_state.tarif = st.selectbox("Wähle deinen Tarif:", tarife, index=tarife.index(st.session_state.tarif))
    
    # NEU: Dynamische Berechnung für Firmenfitness
    final_tarif_wert = st.session_state.tarif
    if st.session_state.tarif == "Firmenfitness (80€ je Stunde für alle 4 Mitarbeiter)":
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            mitarbeiter = st.number_input("Anzahl der Mitarbeiter (in 4er Schritten):", min_value=4, step=4, value=4)
        with col_f2:
            stunden = st.number_input("Stunden pro Woche:", min_value=1, step=1, value=1)
            
        gruppen = mitarbeiter / 4
        wochen_summe = gruppen * 80 * stunden
        monats_summe = wochen_summe * 4  # (Ausgehend von 4 Wochen pro Monat)
        
        st.success(f"**Berechnete Endsumme:** {monats_summe:.2f} € pro Monat (entspricht {wochen_summe:.2f} € / Woche)")
        final_tarif_wert = f"Firmenfitness ({int(mitarbeiter)} MA, {int(stunden)} Std./Woche) - {monats_summe:.2f} € / Monat"

    st.session_state.final_tarif = final_tarif_wert

    st.session_state.ziele = st.multiselect(
        "Was sind deine Hauptziele bei Hinkelfit?", 
        ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], 
        default=st.session_state.get("ziele", [])
    )
    
    st.markdown("---")
    st.subheader("🗓️ Vertragsbeginn")
    st.session_state.vertragsstart = st.date_input("Ab wann soll der Vertrag gültig sein?", value=datetime.today())

    st.subheader("📄 Vertrag & Allgemeine Bedingungen")
    st.info("""**Allgemeine Vertragsbedingungen:**

- **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.


- **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.


- **Kündigungsfrist:** 4 Wochen zum Laufzeitende""")

    
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"): 
        st.session_state.agb_ok = True

    st.info("""**Datenschutz (Art. 9 DSGVO):**
Das Mitglied willigt ausdrücklich ein, dass personenbezogene und gesundheitsbezogene Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt in einer gesicherten Cloud-Datenbank (Supabase). Diese Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden.""")
    
    if st.button("✅ Datenschutzerklärung akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅", key="btn_dsgvo"): 
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ Digitale Unterschrift")
    canvas_result = st_canvas(fill_color="#fff", stroke_width=3, stroke_color="#000", background_color="#eee", height=200, width=7
