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
from PIL import Image, ImageDraw
import numpy as np
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

# --- HELPER: SICHERE UNTERSCHRIFT-EXTRAKTION (UMGEHT DEN CANVAS-BUG) ---
def get_signature_array(canvas_result, session_canvas_val=None, fallback_name="", width=700, height=200):
    if canvas_result is not None:
        try:
            img_data = canvas_result.image_data
            if img_data is not None:
                return np.array(img_data, dtype=np.uint8)
        except Exception:
            pass

    raw_dict = {}
    if isinstance(session_canvas_val, dict):
        raw_dict.update(session_canvas_val)
    if canvas_result is not None and hasattr(canvas_result, "__dict__"):
        raw_dict.update(canvas_result.__dict__)

    for v in raw_dict.values():
        if isinstance(v, str) and "data:image" in v and "," in v:
            try:
                b64_str = v.split(",", 1)[1]
                img = Image.open(io.BytesIO(base64.b64decode(b64_str))).convert("RGBA")
                return np.array(img, dtype=np.uint8)
            except Exception:
                pass

    if "data" in raw_dict and isinstance(raw_dict["data"], (list, np.ndarray)):
        try:
            w = int(raw_dict.get("width", width))
            h = int(raw_dict.get("height", height))
            arr = np.array(raw_dict["data"], dtype=np.uint8)
            if arr.size == w * h * 4:
                return arr.reshape((h, w, 4))
        except Exception:
            pass

    json_data = None
    if canvas_result is not None:
        try:
            json_data = getattr(canvas_result, "json_data", None)
        except Exception:
            pass
    if not json_data and isinstance(raw_dict.get("raw"), dict):
        json_data = raw_dict["raw"]
    if not json_data and isinstance(raw_dict.get("json_data"), dict):
        json_data = raw_dict["json_data"]

    if isinstance(json_data, dict) and "objects" in json_data:
        objects = json_data.get("objects") or []
        if len(objects) > 0:
            img = Image.new("RGBA", (width, height), (238, 238, 238, 255))
            draw = ImageDraw.Draw(img)
            drew_something = False
            for obj in objects:
                path = obj.get("path", [])
                stroke_width = int(obj.get("strokeWidth", 3))
                points = []
                for cmd in path:
                    if not isinstance(cmd, list) or len(cmd) < 3:
                        continue
                    op = cmd[0]
                    if op in ("M", "L"):
                        points.append((float(cmd[1]), float(cmd[2])))
                    elif op == "Q" and len(cmd) >= 5:
                        points.append((float(cmd[1]), float(cmd[2])))
                        points.append((float(cmd[3]), float(cmd[4])))
                    elif op == "C" and len(cmd) >= 7:
                        points.append((float(cmd[1]), float(cmd[2])))
                        points.append((float(cmd[3]), float(cmd[4])))
                        points.append((float(cmd[5]), float(cmd[6])))
                if len(points) > 1:
                    draw.line(points, fill=(0, 0, 0, 255), width=stroke_width)
                    drew_something = True
                elif len(points) == 1:
                    x, y = points[0]
                    draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(0, 0, 0, 255))
                    drew_something = True
            if drew_something:
                return np.array(img, dtype=np.uint8)

    img = Image.new("RGBA", (width, height), (238, 238, 238, 255))
    draw = ImageDraw.Draw(img)
    sig_text = f"Digital gezeichnet: {fallback_name}".strip()
    draw.text((25, height // 2 - 10), sig_text, fill=(0, 0, 0, 255))
    return np.array(img, dtype=np.uint8)

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

    final_tarif_wert = st.session_state.tarif
    if st.session_state.tarif == "Firmenfitness (80€ je Stunde für alle 4 Mitarbeiter)":
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            mitarbeiter = st.number_input("Anzahl der Mitarbeiter (in 4er Schritten):", min_value=4, step=4, value=4)
        with col_f2:
            stunden = st.number_input("Stunden pro Woche:", min_value=1, step=1, value=1)

        gruppen = mitarbeiter / 4
        wochen_summe = gruppen * 80 * stunden
        monats_summe = wochen_summe * 4

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
    agb_text = (
        "**Allgemeine Vertragsbedingungen:**\n\n"
        "- **Zahlung & Rechnungsstellung:** Die Vergütung ist nach Rechnungsstellung **sofort** per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.\n\n"
        "- **Terminabsage & Stornierung:** Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.\n\n"
        "- **Kündigungsfrist:** 4 Wochen zum Laufzeitende"
    )
    st.info(agb_text)

    if st.button("✅ AGB & Vertragsbedingungen akzeptieren" if not st.session_state.agb_ok else "AGB akzeptiert ✅", key="btn_agb"):
        st.session_state.agb_ok = True

    dsgvo_text = (
        "**Datenschutz (Art. 9 DSGVO):**\n"
        "Das Mitglied willigt ausdrücklich ein, dass personenbezogene und gesundheitsbezogene Daten von Hinkelfit (Harald Spanier) "
        "zur individuellen Trainingsplanung und -betreuung verarbeitet werden. Die Speicherung der digitalen Kundenakte erfolgt in einer "
        "gesicherten Cloud-Datenbank (Supabase). Diese Einwilligung kann jederzeit mit Wirkung für die Zukunft widerrufen werden."
    )
    st.info(dsgvo_text)

    if st.button("✅ Datenschutzerklärung akzeptieren" if not st.session_state.dsgvo_ok else "Datenschutz akzeptiert ✅", key="btn_dsgvo"):
        st.session_state.dsgvo_ok = True

    st.subheader("🖋️ Digitale Unterschrift")
    canvas_result = st_canvas(fill_color="#fff", stroke_width=3, stroke_color="#000", background_color="#eee", height=200, width=700, drawing_mode="freedraw", key="canvas")

    if st.button("🚀 Vertrag unterzeichnen & zum Anamnesebogen"):
        if not (st.session_state.vorname and st.session_state.nachname and st.session_state.email):
            st.error("⚠️ Bitte Pflichtfelder (Vorname, Nachname, E-Mail) ausfüllen!")
        elif not (st.session_state.agb_ok and st.session_state.dsgvo_ok):
            st.error("⚠️ Bitte akzeptiere zuerst AGB und Datenschutz!")
        else:
            full_name = f"{st.session_state.vorname} {st.session_state.nachname}".strip()
            st.session_state.signature = get_signature_array(
                canvas_result,
                session_canvas_val=st.session_state.get("canvas"),
                fallback_name=full_name
            )
            st.session_state.step = 2
            st.rerun()

# -------------------------------------------------------------------------
# SCHRITT 2: ANAMNESE & RECHTSTEXTE
# -------------------------------------------------------------------------
elif st.session_state.step == 2:
    st.title("🩺 Anamnesebogen & Gesundheitsstatus")
    if st.button("⬅️ Zurück zur Anmeldung"):
        st.session_state.step = 1
        st.rerun()

    def btn_toggle(k):
        st.session_state[k] = not st.session_state[k]

    st.subheader("1. Herz-Kreislauf-System und Gefäße")
    st.write("Leidest du unter Vorerkrankungen des Herz-Kreislauf-Systems?")
    for k in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"):
            btn_toggle(k)
    cardio_other = st.text_input("Sonstiges / Weitere Details zu Herz-Kreislauf:")

    st.subheader("2. Bewegungsapparat, Gelenke und Wirbelsäule")
    st.write("Hast du Beschwerden im Bereich des Bewegungsapparates?")
    for k in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"):
            btn_toggle(k)
    ms_other = st.text_input("Sonstiges / Weitere Details zum Bewegungsapparat:")

    st.subheader("3. Stoffwechsel, Organe und Atmung")
    st.write("Liegen bei dir Stoffwechsel- oder Atemwegserkrankungen vor?")
    for k in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"]:
        if st.button(f"{k} {'✅' if st.session_state.get(k, False) else ''}", key=f"b_{k}"):
            btn_toggle(k)
    met_other = st.text_input("Sonstiges / Weitere Details zu Stoffwechsel & Organen:")

    st.subheader("4. Operationen, Verletzungen und Medikamente")
    surgeries_meds = st.text_area("Gab es in den letzten 5 Jahren Operationen oder schwerwiegende Verletzungen? Nimmst du regelmäßige Medikamente ein, die das Training beeinträchtigen?")

    st.markdown("---")

    st.subheader("5. Wahrheitspflicht")
    wahrheit_text = (
        "**Wahrheitsgemäße Angaben:**\n\n"
        "- **Wahrheitspflicht:** Das Mitglied versichert, dass alle Angaben im Anamnesebogen vollständig und wahrheitsgemäß gemacht wurden. "
        "Veränderungen des Gesundheitszustandes sind dem Trainer vor jedem Training unaufgefordert mitzuteilen.\n\n"
        "- **Ärztliche Abklärung:** Bei Zweifeln an der gesundheitlichen Eignung verpflichtet sich das Mitglied, vor der Teilnahme einen Arzt zu konsultieren."
    )
    st.info(wahrheit_text)

    if st.button("✅ Wahrheitspflicht bestätigen" if not st.session_state.wahrheit_ok else "Wahrheitspflicht bestätigt ✅", key="btn_wahrheit"):
        st.session_state.wahrheit_ok = True

    st.subheader("6. Risikoaufklärung")
    risiko_text = (
        "**Risikoaufklärung:**\n\n"
        "- **Körperliche Belastung:** Dem Mitglied ist bekannt, dass intensives Kraft-, Ausdauer- und Funktionstraining mit hohen körperlichen Belastungen verbunden ist.\n\n"
        "- **Verletzungsrisiko:** Trotz fachgerechter Anleitung und korrekter Übungsausführung können Verletzungen (z. B. Muskel-, Sehnen- und Gelenkverletzungen) nicht gänzlich ausgeschlossen werden.\n\n"
        "- **Sofortiger Trainingsstopp:** Das Mitglied verpflichtet sich, das Training bei Schwindel, Unwohlsein oder akuten Schmerzen sofort abzubrechen und den Trainer zu informieren."
    )
    st.info(risiko_text)

    if st.button("✅ Risikoaufklärung bestätigen" if not st.session_state.risiko_ok else "Risikoaufklärung bestätigt ✅", key="btn_risiko"):
        st.session_state.risiko_ok = True

    st.subheader("7. Haftungsausschluss")
    haftung_text = (
        "**Haftungsbeschränkung:**\n\n"
        "- **Körperschäden:** Der Dienstleister haftet unbeschränkt für Schäden aus der Verletzung des Lebens, des Körpers oder der Gesundheit, die auf einer vorsätzlichen oder fahrlässigen Pflichtverletzung beruhen.\n\n"
        "- **Sach- und Vermögensschäden:** Für sonstige Schäden haftet der Dienstleister nur bei Vorsatz oder grober Fahrlässigkeit. Bei leicht fahrlässiger Verletzung wesentlicher Vertragspflichten ist die Haftung auf den vertragstypischen, vorhersehbaren Schaden begrenzt.\n\n"
        "- **Wertgegenstände:** Für den Verlust oder Diebstahl von mitgebrachten Kleidungsstücken und Wertgegenständen wird keine Haftung übernommen.\n\n"
        "- **Befolgen von Anweisungen:** Den Anweisungen des Trainers bezüglich Übungsausführung und Sicherheitsbestimmungen ist stets Folge zu leisten. Eigenmächtiges Abweichen erfolgt auf eigene Gefahr."
    )
    st.info(haftung_text)

    if st.button("✅ Haftungsausschluss bestätigen" if not st.session_state.haftung_ok else "Haftungsausschluss bestätigt ✅", key="btn_haftung"):
        st.session_state.haftung_ok = True

    st.markdown("---")

    if st.button("🚀 Jetzt verbindlich anmelden"):
        if not (st.session_state.wahrheit_ok and st.session_state.risiko_ok and st.session_state.haftung_ok):
            st.error("⚠️ Bitte bestätige separat die Wahrheitspflicht, die Risikoaufklärung und den Haftungsausschluss!")
        else:
            with st.spinner("Verarbeite Anmeldung, speichere Daten in Supabase und versende E-Mail..."):
                try:
                    cv_list = [c for c in ["Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen"] if st.session_state.get(c)]
                    if cardio_other:
                        cv_list.append(cardio_other)
                    ms_list = [c for c in ["Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk", "Sonstige Wirbelsäulenbeschwerden"] if st.session_state.get(c)]
                    if ms_other:
                        ms_list.append(ms_other)
                    met_list = [c for c in ["Diabetes", "Asthma", "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"] if st.session_state.get(c)]
                    if met_other:
                        met_list.append(met_other)

                    all_notes = cv_list + ms_list + met_list
                    if surgeries_meds.strip():
                        all_notes.append(f"OPs/Meds: {surgeries_meds}")
                    warnhinweis = ", ".join(all_notes)

                    response = supabase.table("Mitglieder").select("Mitglieder_ID").execute()
                    daten = response.data

                    if daten:
                        ids = []
                        for row in daten:
                            m_id = row.get("Mitglieder_ID", "")
                            if "-" in m_id:
                                try:
                                    ids.append(int(m_id.split("-")[1]))
                                except ValueError:
                                    pass
                        naechste_nr = max(ids) + 1 if ids else 1
                    else:
                        naechste_nr = 1

                    neue_id = f"HF-{naechste_nr:03d}"

                    neues_mitglied = {
                        "Mitglieder_ID": neue_id,
                        "Status": "Aktiv",
                        "Kündigungs_Eingang": "",
                        "Vertrags_Ende": "",
                        "Datum": st.session_state.vertragsstart.strftime("%d.%m.%Y"),
                        "Vorname": st.session_state.vorname,
                        "Nachname": st.session_state.nachname,
                        "Geburtsdatum": st.session_state.geburtsdatum,
                        "E-Mail": st.session_state.email,
                        "Telefon": st.session_state.telefon,
                        "Adresse": st.session_state.adresse,
                        "Tarif": st.session_state.final_tarif,
                        "Ziele": ", ".join(st.session_state.ziele),
                        "Gesundheits_Notizen": warnhinweis
                    }

                    supabase.table("Mitglieder").insert(neues_mitglied).execute()

                    telefon_str = st.session_state.telefon if st.session_state.telefon else "Keine Angabe"
                    geburtsdatum_str = st.session_state.geburtsdatum if st.session_state.geburtsdatum else "Keine Angabe"
                    heute_str = datetime.now().strftime("%d.%m.%Y")

                    img_base64 = ""
                    if st.session_state.get("signature") is not None:
                        sig_img = Image.fromarray(
                            st.session_state.signature.astype("uint8"), "RGBA"
                        )
                        buffered = io.BytesIO()
                        sig_img.save(buffered, format="PNG")
                        img_base64 = base64.b64encode(buffered.getvalue()).decode()

                    sig_html = f'<img src="data:image/png;base64,{img_base64}" style="margin-top: 10px; border: 1px solid #ccc; width: 250px;">' if img_base64 else ""

                    vertragsstart_str = st.session_state.vertragsstart.strftime("%d.%m.%Y")
                    html_contract = (
                        "<html><head><meta charset='utf-8'><style>"
                        "body { font-family: Helvetica, Arial, sans-serif; color: #333; line-height: 1.5; font-size: 13px; margin: 30px; }"
                        "h1 { color: #111; border-bottom: 2px solid #333; padding-bottom: 5px; font-size: 18px; }"
                        "h3 { color: #444; margin-top: 20px; font-size: 14px; border-bottom: 1px solid #ddd; padding-bottom: 3px; }"
                        ".field { margin-bottom: 6px; }"
                        ".label { font-weight: bold; color: #222; }"
                        ".box { background-color: #f9f9f9; border: 1px solid #ddd; padding: 12px; margin-top: 10px; }"
                        "</style></head><body>"
                        "<h1>Hinkelfit – Mitgliedschaftsvertrag</h1>"
                        "<div class='field'><span class='label'>Dienstleister:</span> Hinkelfit (Inh. Harald Spanier), Papiermühlweg 27, 89426 Wittislingen</div>"
                        f"<div class='field'><span class='label'>Vertragsabschluss am:</span> {heute_str}</div>"
                        f"<div class='field'><span class='label'>Vertragsbeginn (Gültig ab):</span> {vertragsstart_str}</div>"
                        "<h3>Mitgliedsdaten</h3>"
                        f"<div class='field'><span class='label'>Name:</span> {st.session_state.vorname} {st.session_state.nachname}</div>"
                        f"<div class='field'><span class='label'>Anschrift:</span> {st.session_state.adresse}</div>"
                        f"<div class='field'><span class='label'>E-Mail:</span> {st.session_state.email}</div>"
                        f"<div class='field'><span class='label'>Telefon:</span> {telefon_str}</div>"
                        f"<div class='field'><span class='label'>Geburtsdatum:</span> {geburtsdatum_str}</div>"
                        "<h3>Gewählter Tarif & Konditionen</h3>"
                        "<div class='box'>"
                        f"<strong>Tarif:</strong> {st.session_state.final_tarif}<br><br>"
                        "• <strong>Zahlung & Rechnungsstellung:</strong> Die Vergütung ist nach Rechnungsstellung sofort per Überweisung auf das in der Rechnung angegebene Bankkonto zu entrichten.<br>"
                        "• <strong>Terminabsage & Stornierung:</strong> Vereinbarte Termine können vom Kunden bis zu 48 Stunden vor Trainingsbeginn kostenfrei abgesagt oder verschoben werden.<br>"
                        "• <strong>Kündigungsfrist:</strong> 4 Wochen zum Laufzeitende"
                        "</div>"
                        "<h3>Digitale Unterschrift</h3>"
                        f"<div class='field'>Rechtsverbindlich digital unterschrieben von <strong>{st.session_state.vorname} {st.session_state.nachname}</strong> am {heute_str}</div>"
                        f"{sig_html}"
                        "</body></html>"
                    )

                    pdf_bytes = HTML(string=html_contract).write_pdf()
                    st.session_state.pdf_bytes = pdf_bytes

                    sender = st.secrets["email"]["absender"]
                    msg = MIMEMultipart("related")
                    msg["From"] = sender
                    msg["To"] = st.session_state.email
                    msg["Bcc"] = sender
                    msg["Subject"] = "Deine Unterlagen bei Hinkelfit"

                    body = MIMEMultipart("alternative")
                    body_text = (
                        f"Hallo {st.session_state.vorname},\n\n"
                        "vielen Dank für deine Anmeldung bei Hinkelfit! Im Anhang findest du deine Unterlagen.\n\n"
                        "Sportliche Grüße\nHarald\nHinkelfit"
                    )
                    body.attach(MIMEText(body_text, "plain"))

                    html_body = (
                        f"<html><body><p>Hallo {st.session_state.vorname},</p>"
                        "<p>vielen Dank für deine Anmeldung bei Hinkelfit! Im Anhang findest du deine Unterlagen.</p><br>"
                        "<p>Sportliche Grüße<br>Harald<br><b>Hinkelfit</b></p><br>"
                        "<img src='cid:logo' style='width:200px;' alt='Hinkelfit Logo'></body></html>"
                    )
                    body.attach(MIMEText(html_body, "html"))
                    msg.attach(body)

                    logo_path = os.path.join("pdfs", "Logo heller Hintergrund.jpg")
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as f:
                            logo = MIMEImage(f.read())
                            logo.add_header("Content-ID", "<logo>")
                            logo.add_header("Content-Disposition", "inline", filename="logo.jpg")
                            msg.attach(logo)

                    pdf_liste = ["Allgemeine Geschäftsbedingungen.pdf", "Datenschutzerklärung.pdf", "Ernährungskompass.pdf", "Hausordnung.pdf", "Willkommen.pdf"]
                    for p in pdf_liste:
                        pdf_path = os.path.join("pdfs", p)
                        if os.path.exists(pdf_path):
                            with open(pdf_path, "rb") as f:
                                part = MIMEApplication(f.read(), _subtype="pdf")
                                part.add_header("Content-Disposition", "attachment", filename=p)
                                msg.attach(part)

                    pdf_part = MIMEApplication(pdf_bytes, _subtype="pdf")
                    pdf_part.add_header("Content-Disposition", "attachment", filename="Vertrag.pdf")
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

# -------------------------------------------------------------------------
# SCHRITT 3: ERFOLG
# -------------------------------------------------------------------------
elif st.session_state.step == 3:
    st.success("🎉 Anmeldung erfolgreich! Die Daten wurden in Supabase gespeichert, die E-Mail mit allen Anhängen wurde versendet.")
    st.download_button("📥 Vertrag lokal speichern", data=st.session_state.pdf_bytes, file_name="Vertrag.pdf", mime="application/pdf")
    if st.button("🔄 Neues Mitglied anlegen"):
        reset_app()
        st.rerun()
