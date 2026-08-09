import io
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from weasyprint import HTML
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
if "step" not in st.session_state: st.session_state.step = 1
for key in ["agb_ok", "dsgvo_ok", "anamnese_bestaetigt"]:
    if key not in st.session_state: st.session_state[key] = False

health_keys = ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen", "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden", "Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]
for k in health_keys:
    if k not in st.session_state: st.session_state[k] = False

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.get("vorname", ""))
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.get("nachname", ""))
        st.session_state.adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)", value=st.session_state.get("adresse", ""))
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.get("email", ""))
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.get("telefon", ""))
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.get("geburtsdatum", ""))

    st.session_state.tarif = st.selectbox("Wähle deinen Tarif:", ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"])
    st.session_state.ziele = st.multiselect("Hauptziele:", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.get("ziele", []))

    if st.button("✅ AGB akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅"): st.session_state.agb_ok = True
    if st.button("✅ Datenschutz akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅"): st.session_state.dsgvo_ok = True

    canvas_result = st_canvas(fill_color="#fff", stroke_width=3, stroke_color="#000", background_color="#eee", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Pflichtfelder ausfüllen!")
        else:
            st.session_state.signature = canvas_result.image_data
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen")
    if st.button("⬅️ Zurück"): st.session_state.step = 1; st.rerun()
    
    for k in health_keys:
        if st.button(f"{k} {'✅' if st.session_state[k] else ''}", key=f"b_{k}"): st.session_state[k] = not st.session_state[k]
    
    surgeries_meds = st.text_area("Operationen (letzte 5 Jahre) oder Medikamente?")
    
    if st.button("✅ Wahrheitspflicht bestätigen" if not st.session_state.wahrheit_ok else "Wahrheitspflicht bestätigt ✅"): st.session_state.wahrheit_ok = True
    if st.button("✅ Risikoaufklärung bestätigen" if not st.session_state.risiko_ok else "Risikoaufklärung bestätigt ✅"): st.session_state.risiko_ok = True
    if st.button("✅ Haftungsausschluss bestätigen" if not st.session_state.haftung_ok else "Haftungsausschluss bestätigt ✅"): st.session_state.haftung_ok = True

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not (st.session_state.wahrheit_ok and st.session_state.risiko_ok and st.session_state.haftung_ok):
            st.error("⚠️ Bitte bestätige alles!")
        else:
            with st.spinner("Erstelle Dokumente & versende E-Mail..."):
                # 1. PDF generieren
                html = f"<h1>Mitgliedschaft: {st.session_state.vorname} {st.session_state.nachname}</h1>"
                pdf_bytes = HTML(string=html).write_pdf()
                st.session_state.pdf_bytes = pdf_bytes
                
                # 2. E-Mail an Kunde + Kopie an Harald
                sender = st.secrets["email"]["absender"]
                msg = MIMEMultipart()
                msg['From'] = sender
                msg['To'] = st.session_state.email
                msg['Bcc'] = sender 
                msg.attach(MIMEText("Hallo, anbei dein Vertrag.", 'plain'))
                
                pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
                pdf_part.add_header('Content-Disposition', 'attachment', filename="Vertrag.pdf")
                msg.attach(pdf_part)
                
                server = smtplib.SMTP(st.secrets["email"]["smtp_server"], int(st.secrets["email"]["smtp_port"]))
                server.starttls(); server.login(sender, st.secrets["email"]["passwort"])
                server.send_message(msg); server.quit()
                
                st.session_state.step = 3
                st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 3: ABSCHLUSS
# -------------------------------------------------------------------------
elif st.session_state.step == 3:
    st.success("🎉 Anmeldung erledigt! E-Mail wurde an dich und den Kunden versendet.")
    st.download_button("📥 Vertrag lokal speichern", data=st.session_state.pdf_bytes, file_name="Vertrag.pdf", mime="application/pdf")
    if st.button("🔄 Neues Mitglied"):
        # Reset aller Felder
        for key in ["step", "agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"] + health_keys: st.session_state[key] = (1 if key == "step" else False)
        for key in ["vorname", "nachname", "email", "telefon", "adresse", "geburtsdatum"]: st.session_state[key] = ""
        st.rerun()
