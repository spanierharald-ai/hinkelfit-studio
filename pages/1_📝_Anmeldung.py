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
from streamlit_gsheets import GSheetsConnection

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst ein.")
    st.stop()

# --- HELPER: RESET ---
def reset_app():
    for key in ["step", "agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
        st.session_state[key] = (1 if key == "step" else False)
    for k in health_keys: st.session_state[k] = False
    for key in ["vorname", "nachname", "email", "telefon", "adresse", "geburtsdatum", "signature", "pdf_bytes"]:
        st.session_state[key] = ("" if key not in ["signature", "pdf_bytes"] else None)
    st.session_state.ziele = []

# --- INITIALISIERUNG ---
if "step" not in st.session_state: st.session_state.step = 1
health_keys = ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen", "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden", "Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]
for k in health_keys:
    if k not in st.session_state: st.session_state[k] = False
for key in ["agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
    if key not in st.session_state: st.session_state[key] = False

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
    tarife = ["Kurse 2x wöchentlich, 59€ pro Monat", "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat", "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"]
    if st.session_state.get("tarif") not in tarife: st.session_state.tarif = tarife[0]
    st.session_state.tarif = st.selectbox("Wähle deinen Tarif:", tarife, index=tarife.index(st.session_state.tarif))
    st.session_state.ziele = st.multiselect("Was sind deine Hauptziele bei Hinkelfit?", ["Kraftaufbau & Muskelaufbau", "Fettabbau / Allgemeine Fitness", "Gesunder Rücken / Schmerzfreiheit", "Ausdauer verbessern", "Kleingruppen-Personaltraining"], default=st.session_state.get("ziele", []))

    st.subheader("📄 Vertrag & Allgemeine Bedingungen")
    st.info("""**Allgemeine Vertragsbedingungen:**\n\n• **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n• **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n• **Kündigungsfrist:** 2 Wochen zum Laufzeitende""")
    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"): st.session_state.agb_ok = True

    st.info("""**Datenschutz (Art. 9 DSGVO):**\nDas Mitglied willigt ausdrücklich ein, dass personenbezogene und gesundheitsbezogene Daten von Hinkelfit (Harald Spanier) zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt im geschützten Cloud-Speicher. Diese Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden.""")
    if st.button("✅ Datenschutzerklärung akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅", key="btn_dsgvo"): st.session_state.dsgvo_ok = True

    st.subheader("🖋️ Digitale Unterschrift")
    canvas_result = st_canvas(fill_color="#fff", stroke_width=3, stroke_color="#000", background_color="#eee", height=200, width=700, drawing_mode="freedraw", key="canvas")

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
# SCHRITT 2: ANAMNESE & RECHTSTEXTE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    if st.button("⬅️ Zurück zur Anmeldung"): st.session_state.step = 1; st.rerun()
    
    def btn_toggle(k): st.session_state[k] = not st.session_state[k]
    
    st.subheader("1. Herz-Kreislauf-System und Gefäße")
    st.write("Leidest du unter Vorerkrankungen des Herz-Kreislauf-Systems?")
    for k in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): btn_toggle(k)
    cardio_other = st.text_input("Sonstiges / Weitere Details zu Herz-Kreislauf:")

    st.subheader("2. Bewegungsapparat, Gelenke und Wirbelsäule")
    st.write("Hast du Beschwerden im Bereich des Bewegungsapparates?")
    for k in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): btn_toggle(k)
    ms_other = st.text_input("Sonstiges / Weitere Details zum Bewegungsapparat:")

    st.subheader("3. Stoffwechsel, Organe und Atmung")
    st.write("Liegen bei dir Stoffwechsel- oder Atemwegserkrankungen vor?")
    for k in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"): btn_toggle(k)
    met_other = st.text_input("Sonstiges / Weitere Details zu Stoffwechsel & Organen:")

    st.subheader("4. Operationen, Verletzungen und Medikamente")
    surgeries_meds = st.text_area("Gab es in den letzten 5 Jahren Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein, die das Training beeinträchtigen?")
    
    st.markdown("---")
    
    st.subheader("5. Wahrheitspflicht")
    st.info("""**Wahrheitsgemäße Angaben:**\n
• **Wahrheitspflicht:** Das Mitglied versichert, dass alle Angaben im Anamnesebogen vollständig und wahrheitsgemäß gemacht wurden. Veränderungen des Gesundheitszustandes sind dem Trainer vor jedem Training unaufgefordert mitzuteilen.\n
• **Ärztliche Abklärung:** Bei Zweifeln an der gesundheitlichen Eignung verpflichtet sich das Mitglied, vor der Teilnahme einen Arzt zu konsultieren.""")
    if st.button("✅ Wahrheitspflicht bestätigen" if not st.session_state.wahrheit_ok else "Wahrheitspflicht bestätigt ✅", key="btn_wahrheit"): st.session_state.wahrheit_ok = True

    st.subheader("6. Risikoaufklärung")
    st.info("""**Risikoaufklärung:**\n
• **Körperliche Belastung:** Dem Mitglied ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit hohen körperlichen Belastungen verbunden ist.\n
• **Verletzungsrisiko:** Trotz fachgerechter Anleitung und korrekter Übungsausführung können Verletzungen (z. B. Muskel-, Sehnen- und Gelenkverletzungen) nicht gänzlich ausgeschlossen werden.\n
• **Sofortiger Trainingsstopp:** Das Mitglied verpflichtet sich, das Training bei Schwindel, Unwohlsein oder akuten Schmerzen sofort abzubrechen und den Trainer zu informieren.""")
    if st.button("✅ Risikoaufklärung bestätigen" if not st.session_state.risiko_ok else "Risikoaufklärung bestätigt ✅", key="btn_risiko"): st.session_state.risiko_ok = True

    st.subheader("7. Haftungsausschluss")
    st.info("""**Haftungsbeschränkung:**\n
• **Körperschäden:** Der Dienstleister haftet unbeschränkt für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, die auf einer vorsätzlichen oder fahrlässigen Pflichtverletzung beruhen.\n
• **Sach- und Vermögensschäden:** Für sonstige Schäden haftet der Dienstleister nur bei Vorsatz oder grober Fahrlässigkeit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt.\n
• **Wertgegenstände:** Für den Verlust oder Diebstahl von mitgebrachten Kleidungsstücken und Wertgegenständen wird keine Haftung übernommen.\n
• **Befolgen von Anweisungen:** Den Anweisungen des Trainers bezüglich Übungsausführung und Sicherheitsbestimmungen ist stets Folge zu leisten. Eigenmächtiges Abweichen erfolgt auf eigene Gefahr.""")
    if st.button("✅ Haftungsausschluss bestätigen" if not st.session_state.haftung_ok else "Haftungsausschluss bestätigt ✅", key="btn_haftung"): st.session_state.haftung_ok = True

    st.markdown("---")
    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not (st.session_state.wahrheit_ok and st.session_state.risiko_ok and st.session_state.haftung_ok):
            st.error("⚠️ Bitte bestätige separat die Wahrheitspflicht, die Risikoaufklärung und den Haftungsausschluss!")
        else:
            with st.spinner("Verarbeite Anmeldung, speichere Daten und versende E-Mail..."):
                try:
                    cv_list = [c for c in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"] if st.session_state.get(c)]
                    if cardio_other: cv_list.append(cardio_other)
                    ms_list = [c for c in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"] if st.session_state.get(c)]
                    if ms_other: ms_list.append(ms_other)
                    met_list = [c for c in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"] if st.session_state.get(c)]
                    if met_other: met_list.append(met_other)
                    
                    all_notes = cv_list + ms_list + met_list
                    if surgeries_meds.strip(): all_notes.append(f"OPs/Meds: {surgeries_meds}")
                    warnhinweis = ", ".join(all_notes)

                    # Google Sheets Update
                    conn = st.connection("gsheets", type=GSheetsConnection)
                    SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1985436937#gid=1985436937"
                    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
                    
                    neues_mitglied = pd.DataFrame([{
                        "Datum": datetime.now().strftime("%d.%m.%Y"),
                        "Vorname": st.session_state.vorname, 
                        "Nachname": st.session_state.nachname,
                        "Geburtsdatum": st.session_state.geburtsdatum, 
                        "E-Mail": st.session_state.email,
                        "Telefon": st.session_state.telefon, 
                        "Adresse": st.session_state.adresse,
                        "Tarif": st.session_state.tarif, 
                        "Ziele": ", ".join(st.session_state.ziele), 
                        "Gesundheits_Notizen": warnhinweis
                    }])
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=pd.concat([df, neues_mitglied], ignore_index=True))

                    # PDF generieren
                   # Unterschrift in Base64 umwandeln für das HTML-PDF
          img_base64 = ""
          if st.session_state.get("signature") is not None:
            sig_img = Image.fromarray(
                st.session_state.signature.astype("uint8"), "RGBA"
            )
            buffered = io.BytesIO()
            sig_img.save(buffered, format="PNG")
            img_base64 = base64.b64encode(buffered.getvalue()).decode()

          # Professionelles HTML für den Vertrag erstellen
          html_contract = f"""
                    <html>
                    <head>
                        <meta charset="utf-8">
                        <style>
                            body {{ font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.5; font-size: 13px; margin: 30px; }}
                            h1 {{ color: #111; border-bottom: 2px solid #333; padding-bottom: 5px; font-size: 18px; }}
                            h3 {{ color: #444; margin-top: 20px; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 3px; }}
                            .field {{ margin-bottom: 6px; }}
                            .label {{ font-weight: bold; color: #222; }}
                            .box {{ background-color: #f9f9f9; border: 1px solid #ddd; padding: 12px; margin-top: 10px; }}
                        </style>
                    </head>
                    <body>
                        <h1>Hinkelfit – Mitgliedschaftsvertrag</h1>
                        <div class="field"><span class="label">Dienstleister:</span> Hinkelfit (Inh. Harald Spanier), Papiermühlweg 27, 89407 Wittislingen</div>
                        <div class="field"><span class="label">Vertragsdatum:</span> {datetime.now().strftime('%d.%m.%Y')}</div>
                        
                        <h3>Mitgliedsdaten</h3>
                        <div class="field"><span class="label">Name:</span> {st.session_state.vorname} {st.session_state.nachname}</div>
                        <div class="field"><span class="label">Anschrift:</span> {st.session_state.adresse}</div>
                        <div class="field"><span class="label">E-Mail:</span> {st.session_state.email}</div>
                        <div class="field"><span class="label">Telefon:</span> {st.session_state.telefon if st.session_state.telefon else 'Keine Angabe'}</div>
                        <div class="field"><span class="label">Geburtsdatum:</span> {st.session_state.geburtsdatum if st.session_state.geburtsdatum else 'Keine Angabe'}</div>
                        
                        <h3>Gewählter Tarif & Konditionen</h3>
                        <div class="box">
                            <strong>Tarif:</strong> {st.session_state.tarif}<br><br>
                            • <strong>Zahlung & Rechnungsstellung:</strong> Die Vergütung ist nach Rechnungsstellung sofort per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.<br>
                            • <strong>Terminabsage & Stornierung:</strong> Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.<br>
                            • <strong>Kündigungsfrist:</strong> 2 Wochen zum Laufzeitende
                        </div>
                        
                        <h3>Digitale Unterschrift</h3>
                        <div class="field">Rechtsverbindlich digital unterschrieben von <strong>{st.session_state.vorname} {st.session_state.nachname}</strong> am {datetime.now().strftime('%d.%m.%Y')}</div>
                        {'<img src="data:image/png;base64,' + img_base64 + '" style="margin-top: 10px; border: 1px solid #ccc; width: 250px;">' if img_base64 else ''}
                    </body>
                    </html>
                    """

          pdf_bytes = HTML(string=html_contract).write_pdf()
          st.session_state.pdf_bytes = pdf_bytes

                    # E-Mail Versand mit Anhängen und Logo
                    sender = st.secrets["email"]["absender"]
                    msg = MIMEMultipart("related")
                    msg['From'] = sender
                    msg['To'] = st.session_state.email
                    msg['Bcc'] = sender
                    msg['Subject'] = "Deine Unterlagen bei Hinkelfit"
                    
                    body = MIMEMultipart("alternative")
                    body.attach(MIMEText(f"Hallo {st.session_state.vorname},\n\nvielen Dank für deine Anmeldung bei Hinkelfit! Im Anhang findest du deine Unterlagen.\n\nSportliche Grüße\nHarald", 'plain'))
                    html_body = f"<html><body><p>Hallo {st.session_state.vorname},</p><p>vielen Dank für deine Anmeldung bei Hinkelfit! Im Anhang findest du deine Unterlagen.</p><br><p>Sportliche Grüße<br>Harald</p><br><img src='cid:logo' style='width:200px;'></body></html>"
                    body.attach(MIMEText(html_body, 'html'))
                    msg.attach(body)
                    
                    logo_path = os.path.join("pdfs", "Logo heller Hintergrund.jpg")
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as f:
                            logo = MIMEImage(f.read())
                            logo.add_header('Content-ID', '<logo>')
                            msg.attach(logo)
                    
                    pdf_liste = ["Allgemeine Geschäftsbedingungen.pdf", "Datenschutzerklärung.pdf", "Ernährungskompass.pdf", "Hausordnung.pdf", "Willkommen.pdf"]
                    for p in pdf_liste:
                        pdf_path = os.path.join("pdfs", p)
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f:
                                part = MIMEApplication(f.read(), _subtype="pdf")
                                part.add_header('Content-Disposition', 'attachment', filename=p)
                                msg.attach(part)
                    
                    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
                    pdf_part.add_header('Content-Disposition', 'attachment', filename="Vertrag.pdf")
                    msg.attach(pdf_part)
                    
                    server = smtplib.SMTP(st.secrets["email"]["smtp_server"], int(st.secrets["email"]["smtp_port"]))
                    server.starttls()
                    server.login(sender, st.secrets["email"]["passwort"])
                    server.send_message(msg)
                    server.quit()

                    st.session_state.step = 3
                    st.rerun()
                except Exception as e:
                    st.error(f"❌ Fehler bei der Verarbeitung: {e}")

elif st.session_state.step == 3:
    st.success("🎉 Anmeldung erfolgreich! Die Daten wurden gespeichert, die E-Mail mit allen Anhängen wurde versendet.")
    st.download_button("📥 Vertrag lokal speichern", data=st.session_state.pdf_bytes, file_name="Vertrag.pdf", mime="application/pdf")
    if st.button("🔄 Neues Mitglied anlegen"):
        reset_app()
        st.rerun()
