import base64
import datetime
import io
import os
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.application import MIMEApplication
from streamlit_gsheets import GSheetsConnection
from streamlit_drawable_canvas import st_canvas
from PIL import Image

# ReportLab für PDF-Generierung
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Tarifwechsel & Pausierung", page_icon="🔄", layout="wide")

# Cloud-tauglicher Fallback für den Mitglieder-Ordner
MEMBERS_DIR = "mitglieder"
if not os.path.exists(MEMBERS_DIR):
    try:
        os.makedirs(MEMBERS_DIR, exist_ok=True)
    except:
        pass

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ZENTRALE E-MAIL FUNKTION MIT ANHANG & LOGO ---
def send_hinkelfit_email_with_pdf(to_email, to_name, subject, body_content_html, pdf_path):
    try:
        email_secrets = st.secrets.get("email", {})
        SENDER_EMAIL = email_secrets.get("absender", "fit@hinkelfit.de")
        SENDER_PASSWORD = email_secrets.get("passwort", "")
        SMTP_SERVER = email_secrets.get("smtp_server", "smtp.strato.de") 
        SMTP_PORT = int(email_secrets.get("smtp_port", 587))

        msg = MIMEMultipart("mixed")
        msg["From"] = SENDER_EMAIL
        msg["To"] = to_email
        msg["Subject"] = subject

        msg_related = MIMEMultipart("related")
        msg.attach(msg_related)

        full_html = f"""
        <html>
        <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.5;">
            <p>Hallo {to_name},</p>
            {body_content_html}
            <br>
            <p>Sportliche Grüße<br>Harald<br><b>Hinkelfit</b></p>
            <br>
            <img src="cid:logo" alt="Hinkelfit Logo" style="width: 250px;">
        </body>
        </html>
        """
        msg_related.attach(MIMEText(full_html, "html", "utf-8"))

        # Cloud-taugliche Suche nach dem Logo in verschiedenen möglichen Ordnern
        possible_logo_paths = [
            "Logo heller Hintergrund.jpg",
            "pdfs/Logo heller Hintergrund.jpg",
            os.path.join(os.path.dirname(__file__), "..", "Logo heller Hintergrund.jpg"),
            os.path.join(os.path.dirname(__file__), "..", "pdfs", "Logo heller Hintergrund.jpg")
        ]
        
        logo_path = None
        for p in possible_logo_paths:
            if os.path.exists(p):
                logo_path = p
                break

        if logo_path:
            with open(logo_path, "rb") as img_file:
                logo_part = MIMEImage(img_file.read())
                logo_part.add_header('Content-ID', '<logo>')
                logo_part.add_header('Content-Disposition', 'inline', filename="logo.jpg")
                msg_related.attach(logo_part)

        # PDF-Anhang hinzufügen
        if os.path.exists(pdf_path):
            with open(pdf_path, "rb") as f:
                pdf_attachment = MIMEApplication(f.read(), _subtype="pdf")
                pdf_attachment.add_header('Content-Disposition', 'attachment', filename=os.path.basename(pdf_path))
                msg.attach(pdf_attachment)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"E-Mail-Fehler: {e}")
        return False

# --- PDF GENERIERUNG IM MITGLIEDER-ORDNER MIT BILD-UNTERSCHRIFT ---
def generate_tariff_pdf(member_data, old_tariff, new_tariff, effective_date, sig_image_path):
    if not os.path.exists(MEMBERS_DIR):
        os.makedirs(MEMBERS_DIR, exist_ok=True)
        
    customer_dir = None
    member_id_str = str(member_data['Mitglieder_ID'])
    
    for dirname in os.listdir(MEMBERS_DIR):
        if dirname.startswith(member_id_str):
            customer_dir = os.path.join(MEMBERS_DIR, dirname)
            break
            
    if not customer_dir:
        safe_name = "".join(c for c in str(member_data['Name']) if c.isalnum() or c in (' ', '_', '-')).strip()
        customer_dir = os.path.join(MEMBERS_DIR, f"{member_id_str}_{safe_name}")
        
    if not os.path.exists(customer_dir):
        os.makedirs(customer_dir, exist_ok=True)
        
    pdf_filename = f"Tarifänderung_{datetime.date.today().strftime('%Y%m%d')}.pdf"
    pdf_path = os.path.join(customer_dir, pdf_filename)
    
    doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1f2937'),
        spaceAfter=15
    )
    normal_style = ParagraphStyle(
        'NormalStyle',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#374151'),
        spaceAfter=10,
        leading=14
    )
    
    story.append(Paragraph("<b>Hinkelfit – Bestätigung der Vertragsänderung</b>", title_style))
    story.append(Paragraph(f"Datum: {datetime.date.today().strftime('%d.%m.%Y')}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph(f"<b>Mitgliedsdaten:</b><br/>"
                           f"Name: {member_data['Name']}<br/>"
                           f"Mitglieder-ID: {member_data['Mitglieder_ID']}<br/>"
                           f"Anschrift: {member_data.get('Adresse', '-')}", normal_style))
    story.append(Spacer(1, 10))
    
    story.append(Paragraph("Hiermit wird die Änderung der Mitgliedschaft bei Hinkelfit wie folgt bestätigt:", normal_style))
    
    data = [
        [Paragraph("<b>Bisheriger Tarif:</b>", normal_style), Paragraph(old_tariff, normal_style)],
        [Paragraph("<b>Neuer Tarif:</b>", normal_style), Paragraph(new_tariff, normal_style)],
        [Paragraph("<b>Gültig ab:</b>", normal_style), Paragraph(effective_date, normal_style)]
    ]
    
    t = Table(data, colWidths=[150, 350])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f3f4f6')),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('BOTTOMPADDING', (0,0), (-1,-1), 8),
        ('TOPPADDING', (0,0), (-1,-1), 8),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db'))
    ]))
    
    story.append(t)
    story.append(Spacer(1, 15))
    story.append(Paragraph("Es gelten weiterhin die allgemeinen Geschäftsbedingungen und Vertragskonditionen der Hinkelfit-Mitgliedschaft.", normal_style))
    story.append(Spacer(1, 15))
    
    story.append(Paragraph(f"<b>Digitale Unterschrift:</b><br/>Erfasst am {datetime.date.today().strftime('%d.%m.%Y')}", normal_style))
    
    if sig_image_path and os.path.exists(sig_image_path):
        story.append(RLImage(sig_image_path, width=250, height=70))
    
    doc.build(story)
    return pdf_path


st.title("🔄 Vertragsänderungen, Tarifwechsel & Pausierung")

# --- DATENBANK AUS DER CLOUD LADEN & SPALTEN SICHERSTELLEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception as e:
    st.error("⚠️ Die Verbindung zu Google Sheets wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    df_members = pd.DataFrame()

if df_members.empty:
    st.warning("Keine Mitglieder in der Datenbank gefunden.")
    st.stop()

# --- TYP-KONFLIKTE VERHINDERN (WICHTIG FÜR TEXTSPALTEN) ---
text_columns = ['Mitglieder_ID', 'Vorname', 'Nachname', 'E-Mail', 'Adresse', 'Tarif', 'Status', 'Pausiert_Bis', 'Notizen', 'Datum']
for col in text_columns:
    if col in df_members.columns:
        df_members[col] = df_members[col].astype(object)

# --- SAUBERE LÖSUNG: Hilfsspalte "Name" anlegen ---
if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
    df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
else:
    df_members["Name"] = "Unbekannt"

needs_update = False
if "Status" not in df_members.columns:
    df_members["Status"] = "Aktiv"
    needs_update = True
if "Pausiert_Bis" not in df_members.columns:
    df_members["Pausiert_Bis"] = "-"
    needs_update = True
if "Notizen" not in df_members.columns:
    df_members["Notizen"] = ""
    needs_update = True
    
if needs_update:
    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
    st.cache_data.clear()


# --- MITGLIED AUSWÄHLEN ---
member_options = df_members.apply(
    lambda x: f"{x['Mitglieder_ID']} | {x['Name']} (Tarif: {x['Tarif']} | Status: {x['Status']})", 
    axis=1
).tolist()

selected_member_str = st.selectbox("Mitglied für Vertragsänderung auswählen:", member_options)

if selected_member_str:
    sel_id = selected_member_str.split(" | ")[0]
    m_idx = df_members.index[df_members["Mitglieder_ID"] == sel_id].tolist()[0]
    row = df_members.loc[m_idx]
    
    st.markdown("---")
    col_info1, col_info2, col_info3 = st.columns(3)
    with col_info1:
        st.write(f"**Name:** {row['Name']}")
        st.write(f"**Mitglieder-ID:** {row['Mitglieder_ID']}")
    with col_info2:
        st.write(f"**Aktueller Tarif:** {row['Tarif']}")
        st.write(f"**Aktueller Status:** {row['Status']}")
    with col_info3:
        st.write(f"**Beitrittsdatum:** {row.get('Datum', '-')}")
        pausiert_info = row.get("Pausiert_Bis", "-")
        st.write(f"**Pausiert bis:** {pausiert_info if pd.notna(pausiert_info) and str(pausiert_info).strip() != 'nan' else '-'}")
        
    st.markdown("---")
    
    tab1, tab2 = st.tabs(["🔀 Tarif wechseln", "⏸️ Mitgliedschaft pausieren / reaktivieren"])
    
    # -------------------------------------------------------------------------
    # TAB 1: TARIF WECHSELN
    # -------------------------------------------------------------------------
    with tab1:
        st.subheader("Tarifwechsel durchführen & Digitale Unterschrift")
        st.write("Wähle den neuen Tarif aus und unterschreibe im Feld zur Bestätigung.")
        
        current_tariff = row['Tarif']
        
        available_tariffs = [
            "Kurse 2x wöchentlich, 59€ pro Monat",
            "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat",
            "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
        ]
        
        default_index = available_tariffs.index(current_tariff) if current_tariff in available_tariffs else 0
        
        new_tariff = st.selectbox("Neuer Tarif:", available_tariffs, index=default_index, key="tf_new_tariff")
        effective_date_input = st.date_input("Gültig ab Datum:", value=datetime.date.today(), key="tf_eff_date")
        tariff_note = st.text_input("Grund / Notiz zum Tarifwechsel (optional):", value="", key="tf_note")
        
        st.markdown("---")
        st.write("🖋️ **Digitale Unterschrift des Mitglieds:**")
        canvas_result = st_canvas(
            fill_color="#fff", 
            stroke_width=3, 
            stroke_color="#000", 
            background_color="#eee", 
            height=150, 
            width=600, 
            drawing_mode="freedraw", 
            key="tariff_canvas"
        )
        
        if st.button("💾 Tarifänderung in Cloud bestätigen, PDF generieren & senden", key="btn_submit_tariff"):
            if canvas_result.image_data is None:
                st.error("⚠️ Bitte unterschreibe im Feld, um den Tarifwechsel abzuschließen.")
            else:
                effective_str = effective_date_input.strftime("%d.%m.%Y")
                
                # Unterschrift als temporäres Bild speichern
                sig_img = Image.fromarray(canvas_result.image_data.astype("uint8"), "RGBA")
                sig_buffered = io.BytesIO()
                sig_img.save(sig_buffered, format="PNG")
                
                temp_sig_path = "temp_signature.png"
                with open(temp_sig_path, "wb") as f:
                    f.write(sig_buffered.getvalue())
                
                # 1. PDF generieren mit Bild-Unterschrift
                pdf_path = generate_tariff_pdf(row, current_tariff, new_tariff, effective_str, temp_sig_path)
                
                # Aufräumen
                if os.path.exists(temp_sig_path):
                    os.remove(temp_sig_path)
                
                # 2. In Cloud-Datenbank aktualisieren
                df_members.at[m_idx, "Tarif"] = new_tariff
                timestamp_str = datetime.date.today().strftime("%d.%m.%Y")
                current_notes = str(df_members.at[m_idx, "Notizen"]) if pd.notna(df_members.at[m_idx, "Notizen"]) and str(df_members.at[m_idx, "Notizen"]).strip() != 'nan' else ""
                new_note = f"[{timestamp_str}] Tarifwechsel von '{current_tariff}' zu '{new_tariff}' (Gültig ab {effective_str}). Digital unterschrieben. {tariff_note}".strip()
                df_members.at[m_idx, "Notizen"] = f"{current_notes} | {new_note}" if current_notes else new_note
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
                st.cache_data.clear()
                
                # 3. E-Mail mit PDF versenden (Singular: "ich")
                email = row.get("E-Mail", "")
                first_name = row.get("Vorname", "Mitglied")
                
                if pd.notna(email) and "@" in str(email):
                    subject = f"Bestätigung deiner Tarifänderung bei Hinkelfit"
                    body = f"""
                    <p>ich habe deinen Wunsch nach einem Tarifwechsel entgegengenommen und im System hinterlegt.</p>
                    <p>Im Anhang findest du die offizielle Bestätigung deiner Tarifänderung auf <strong>{new_tariff}</strong> (gültig ab dem {effective_str}), versehen mit deiner digitalen Unterschrift.</p>
                    <p>Vielen Dank und sportliche Grüße!</p>
                    """
                    if send_hinkelfit_email_with_pdf(email, first_name, subject, body, pdf_path):
                        st.success(f"✅ Tarifänderung erfolgreich gespeichert, PDF erstellt und E-Mail erfolgreich an {row['Name']} gesendet!")
                    else:
                        st.warning("⚠️ Tarif wurde geändert und PDF im Ordner gespeichert, aber beim E-Mail-Versand gab es ein Problem.")
                else:
                    st.success(f"✅ Tarif erfolgreich in der Cloud geändert und unterschriebene PDF im Ordner abgelegt! (Keine E-Mail-Adresse für den Versand hinterlegt).")
                
                st.rerun()
                
    # -------------------------------------------------------------------------
    # TAB 2: PAUSIEREN / REAKTIVIEREN
    # -------------------------------------------------------------------------
    with tab2:
        st.subheader("Mitgliedschaft pausieren oder reaktivieren")
        current_status = row['Status']
        
        if current_status != "Pausiert":
            st.write("Setze die Mitgliedschaft temporär aus (z. B. wegen Urlaub oder Verletzung).")
            
            with st.form("pause_form"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    pause_start = st.date_input("Pausen-Startdatum:", value=datetime.date.today())
                with col_p2:
                    pause_end = st.date_input("Pausen-Enddatum (voraussichtlich):", value=datetime.date.today() + datetime.timedelta(days=30))
                
                pause_reason = st.text_input("Grund für die Pause (z. B. Urlaub, Verletzung):")
                submit_pause = st.form_submit_button("⏸️ Mitgliedschaft pausieren & in Cloud speichern")
                
                if submit_pause:
                    df_members.at[m_idx, "Status"] = "Pausiert"
                    df_members.at[m_idx, "Pausiert_Bis"] = str(pause_end)
                    
                    timestamp_str = datetime.date.today().strftime("%d.%m.%Y")
                    current_notes = str(df_members.at[m_idx, "Notizen"]) if pd.notna(df_members.at[m_idx, "Notizen"]) and str(df_members.at[m_idx, "Notizen"]).strip() != 'nan' else ""
                    new_note = f"[{timestamp_str}] Pausiert von {pause_start} bis {pause_end}. Grund: {pause_reason}".strip()
                    df_members.at[m_idx, "Notizen"] = f"{current_notes} | {new_note}" if current_notes else new_note
                    
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
                    st.cache_data.clear()
                    
                    st.success(f"Mitgliedschaft für {row['Name']} wurde bis zum {pause_end.strftime('%d.%m.%Y')} pausiert!")
                    st.rerun()
        else:
            st.success(f"⚠️ Diese Mitgliedschaft ist aktuell **pausiert** (bis voraussichtlich {row.get('Pausiert_Bis', 'unbekannt')}).")
            
            if st.button("▶️ Mitgliedschaft jetzt reaktivieren (Status in Cloud auf 'Aktiv' setzen)"):
                df_members.at[m_idx, "Status"] = "Aktiv"
                df_members.at[m_idx, "Pausiert_Bis"] = "-"
                
                timestamp_str = datetime.date.today().strftime("%d.%m.%Y")
                current_notes = str(df_members.at[m_idx, "Notizen"]) if pd.notna(df_members.at[m_idx, "Notizen"]) and str(df_members.at[m_idx, "Notizen"]).strip() != 'nan' else ""
                new_note = f"[{timestamp_str}] Reaktiviert und Status auf 'Aktiv' gesetzt."
                df_members.at[m_idx, "Notizen"] = f"{current_notes} | {new_note}" if current_notes else new_note
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
                st.cache_data.clear()
                
                st.success(f"Mitgliedschaft für {row['Name']} wurde erfolgreich reaktiviert!")
                st.rerun()
