import datetime
import os
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
import smtplib
from fpdf import FPDF
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import pandas as pd
import streamlit as st
import altair as alt
from streamlit_gsheets import GSheetsConnection

class ModernPDFReport(FPDF):
    def header(self):
        self.set_fill_color(15, 23, 42)
        self.rect(0, 0, 210, 15, "F")

        self.set_font("Arial", "B", 12)
        self.set_text_color(255, 255, 255)
        self.set_xy(10, 3)
        self.cell(
            0,
            10,
            "HINKELFIT - MONATLICHE ERFOLGSMESSUNG".encode("latin-1", "replace").decode("latin-1"),
            0,
            0,
            "L",
        )
        self.ln(20)

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "I", 8)
        self.set_text_color(148, 163, 184)
        page_text = (
            f"Hinkelfit Wittislingen | Erstellt am"
            f" {datetime.date.today().strftime('%d.%m.%Y')} | Seite"
            f" {str(self.page_no())}"
        )
        self.cell(
            0,
            10,
            page_text.encode("latin-1", "replace").decode("latin-1"),
            0,
            0,
            "C",
        )

st.set_page_config(
    page_title="Hinkelfit Leistungsverlauf", page_icon="📈", layout="centered"
)

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# Basis-Ordner für PDF-Zwischenspeicherung & Bilder bleibt lokal
BASE_DIR = r"C:\Users\carol\Desktop\HinkelFit\Planung Wittislingen\Anmeldung"

st.title("Hinkelfit - Monatliche Erfolgsmessung")
st.write("Erfasse und verfolge die Trainingsdaten, Leistungen und den Fortschritt der Mitglieder.")

# --- DATEN AUS GOOGLE SHEETS LESEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception:
    df_members = pd.DataFrame()

if not df_members.empty and "Name" in df_members.columns:
    st.subheader("Mitglied auswählen")
    selected_member_name = st.selectbox("Mitglied:", df_members["Name"].tolist())

    member_data = df_members[df_members["Name"] == selected_member_name].iloc[0]
    member_email = member_data["Email"]

    st.markdown("---")
    st.markdown(f"**Aktuelles Mitglied:** {member_data['Name']}")
    st.markdown(f"**E-Mail-Adresse:** {member_email}")
    st.markdown(f"**Gewählter Tarif:** {member_data['Tarif']}")
    st.markdown(f"**Mitglied seit:** {member_data['Beitrittsdatum']}")
    st.markdown("---")

    st.subheader("Monatlichen Erfolg dokumentieren")
    training_date = st.date_input("Datum des Check-ups", value=datetime.date.today())

    exercise_type = st.selectbox(
        "Trainingsschwerpunkt",
        ["Krafttraining", "Funktionelles Training", "Kondition"],
    )

    with st.form("performance_form"):
        st.markdown("### Basis Check")
        col_base1, col_base2 = st.columns(2)
        with col_base1:
            koerpergewicht = st.number_input(
                "Körpergewicht (kg)", min_value=0.0, step=0.1, format="%.1f", value=0.0
            )
        with col_base2:
            schmerzen = st.selectbox(
                "Aktuelle Schmerzen / Beschwerden",
                ["Keine", "Leicht", "Mittel", "Stark"],
            )

        st.markdown("---")
        details = {}

        if exercise_type == "Krafttraining":
            st.markdown("### Krafttraining Details")
            
            c1, c2 = st.columns(2)
            with c1:
                details["Drueckende_Uebung"] = st.selectbox("Drückende Übung", ["Bankdrücken", "Über-Kopf-Drücken"])
            with c2:
                details["Gewicht_Drueckende_Uebung"] = st.number_input("Gewicht Drückende Übung (kg)", min_value=0.0, step=0.5, format="%.1f", value=0.0)

            c_pull1, c_pull2 = st.columns(2)
            with c_pull1:
                st.text("Ziehende Übung")
                details["Ziehende_Uebung"] = "Chinesische Ruderbank"
            with c_pull2:
                details["Gewicht_Chinesische_Ruderbank"] = st.number_input("Gewicht Chinesische Ruderbank (kg)", min_value=0.0, step=0.5, format="%.1f", value=0.0)

            c3, c4 = st.columns(2)
            with c3:
                st.text("Kniebeuge")
                details["Uebung_Kniebeuge"] = "Kniebeuge"
            with c4:
                details["Gewicht_Kniebeuge"] = st.number_input("Gewicht Kniebeuge (kg)", min_value=0.0, step=0.5, format="%.1f", value=0.0)

            c5, c6 = st.columns(2)
            with c5:
                st.text("Kreuzheben")
                details["Uebung_Kreuzheben"] = "Kreuzheben"
            with c6:
                details["Gewicht_Kreuzheben"] = st.number_input("Gewicht Kreuzheben (kg)", min_value=0.0, step=0.5, format="%.1f", value=0.0)

        elif exercise_type == "Funktionelles Training":
            st.markdown("### Funktionelles Training Details")
            details["Sandsack_Uebung"] = "Sandsack über Schulter"
            details["Sandsack_Gewicht"] = st.number_input("Sandsack über Schulter - Gewicht (kg)", min_value=0.0, step=0.5, format="%.1f", value=0.0)

            details["KB_Uebung"] = "Kettlebell Swings 10 Minuten"
            details["KB_Wdh"] = st.number_input("Kettlebell Swings 10 Minuten - Wiederholungen", min_value=0, step=1, value=0)

            details["SS_Uebung"] = "Secret Service Snatch Test 10 Minuten"
            details["SS_Wdh"] = st.number_input("Secret Service Snatch Test 10 Minuten - Wiederholungen", min_value=0, step=1, value=0)

        elif exercise_type == "Kondition":
            st.markdown("### Kondition Details")
            c1, c2 = st.columns(2)
            with c1:
                details["Ausdauer_Geraet"] = st.selectbox("Gerät (1000 Meter)", ["Airbike", "Ruderergometer"])
            with c2:
                details["Ausdauer_Zeit"] = st.text_input("Zeit für 1000 Meter", placeholder="z.B. 3:45 min")

            details["Zirkel_Uebung"] = "400er Zirkel"
            details["Zirkel_Zeit"] = st.text_input("Zeit für 400er Zirkel", placeholder="Zeit eingeben")

            details["Tragen_Uebung"] = "Sandsack 50 Meter tragen"
            details["Tragen_Gewicht"] = st.number_input("Sandsack 50 Meter tragen - Gewicht (kg)", min_value=0.0, step=0.5, format="%.1f", value=0.0)

        trainer_notes = st.text_area("Trainer-Notizen & Feedback", placeholder="Notizen hier eintragen...")

        col_save, col_mail = st.columns(2)
        with col_save:
            submit_performance = st.form_submit_button("Leistungsdaten speichern")
        with col_mail:
            submit_email = st.form_submit_button("Auswertung per E-Mail senden")

        safe_name = selected_member_name.strip().replace(" ", "_")
        member_dir = os.path.join(BASE_DIR, "mitglieder", safe_name)

        if submit_performance or submit_email:
            os.makedirs(member_dir, exist_ok=True)

            row_data = {
                "Name": selected_member_name,  # WICHTIG: Damit wir wissen, wem der Eintrag in der zentralen Historie gehört
                "Datum": str(training_date),
                "Koerpergewicht": koerpergewicht,
                "Schmerzen": schmerzen,
                "Bereich": exercise_type,
                "Notizen": trainer_notes,
            }
            row_data.update(details)

            new_entry = pd.DataFrame([row_data])

            # --- HISTORIE AUS GOOGLE SHEETS LADEN & UPDATEN ---
            try:
                df_history_all = conn.read(spreadsheet=SHEET_URL, worksheet="Historie", ttl=0)
                df_history_all = df_history_all.dropna(how="all")
            except Exception:
                df_history_all = pd.DataFrame()

            if not df_history_all.empty:
                df_history_all = pd.concat([df_history_all, new_entry], ignore_index=True, sort=False)
            else:
                df_history_all = new_entry

            # Zurück in Google Sheets schreiben
            conn.update(spreadsheet=SHEET_URL, worksheet="Historie", data=df_history_all)
            st.cache_data.clear() # Cache leeren, damit die neue Zeile sofort sichtbar ist

            # Nur die Daten dieses speziellen Mitglieds für die PDF-Erstellung filtern
            df_history = df_history_all[df_history_all["Name"] == selected_member_name].copy()

            if submit_performance:
                st.success(f"Die Leistungsdaten für {selected_member_name} wurden zentral in der Cloud gespeichert!")

            if submit_email:
                try:
                    pdf_filename = os.path.join(member_dir, f"Erfolgsmessung_{training_date.strftime('%Y-%m-%d')}.pdf")

                    df_plot = df_history.copy()
                    if "Datum" in df_plot.columns:
                        df_plot["Datum"] = pd.to_datetime(df_plot["Datum"])
                        df_plot = df_plot.sort_values("Datum")

                    plt.style.use("seaborn-v0_8-whitegrid" if "seaborn-v0_8-whitegrid" in plt.style.available else "default")

                    chart_weight_path = os.path.join(member_dir, "temp_weight_chart.png")
                    if not df_plot.empty and "Koerpergewicht" in df_plot.columns and df_plot["Koerpergewicht"].sum() > 0:
                        fig, ax = plt.subplots(figsize=(6.5, 2.2))
                        ax.plot(
                            df_plot["Datum"], df_plot["Koerpergewicht"], marker="o", color="#2563eb",
                            linewidth=2.5, markersize=6, markerfacecolor="#ffffff", markeredgewidth=2, markeredgecolor="#2563eb"
                        )
                        ax.set_title("Körpergewicht-Verlauf (kg)", fontsize=10, fontweight="bold", color="#1e293b", pad=10)
                        ax.set_xlabel("Kalendertag", fontsize=8, color="#1e293b")
                        ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
                        ax.tick_params(axis="both", labelsize=8, colors="#475569")
                        ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
                        fig.tight_layout()
                        fig.savefig(chart_weight_path, dpi=300)
                        plt.close(fig)

                    chart_area_path = os.path.join(member_dir, "temp_area_chart.png")
                    df_area_plot = df_plot[df_plot["Bereich"] == exercise_type]
                    if not df_area_plot.empty:
                        fig, ax = plt.subplots(figsize=(6.5, 2.5))
                        plotted_cols = False
                        colors = ["#0284c7", "#10b981", "#f59e0b", "#8b5cf6"]

                        if exercise_type == "Krafttraining":
                            cols_to_plot = [c for c in ["Gewicht_Drueckende_Uebung", "Gewicht_Chinesische_Ruderbank", "Gewicht_Kniebeuge", "Gewicht_Kreuzheben"] if c in df_area_plot.columns]
                            if cols_to_plot:
                                for i, col in enumerate(cols_to_plot):
                                    ax.plot(df_area_plot["Datum"], df_area_plot[col], marker="o", linewidth=2, markersize=5, label=col.replace("_", " "), color=colors[i % len(colors)])
                                plotted_cols = True
                        elif exercise_type == "Funktionelles Training":
                            cols_to_plot = [c for c in ["Sandsack_Gewicht", "KB_Wdh", "SS_Wdh"] if c in df_area_plot.columns]
                            if cols_to_plot:
                                for i, col in enumerate(cols_to_plot):
                                    ax.plot(df_area_plot["Datum"], df_area_plot[col], marker="o", linewidth=2, markersize=5, label=col.replace("_", " "), color=colors[i % len(colors)])
                                plotted_cols = True
                        elif exercise_type == "Kondition":
                            cols_to_plot = [c for c in ["Tragen_Gewicht"] if c in df_area_plot.columns]
                            if cols_to_plot:
                                for i, col in enumerate(cols_to_plot):
                                    ax.plot(df_area_plot["Datum"], df_area_plot[col], marker="o", linewidth=2, markersize=5, label=col.replace("_", " "), color=colors[i % len(colors)])
                                plotted_cols = True

                        if plotted_cols:
                            ax.set_title(f"Verlauf für Schwerpunkt: {exercise_type}", fontsize=10, fontweight="bold", color="#1e293b", pad=10)
                            ax.set_xlabel("Kalendertag", fontsize=8, color="#1e293b")
                            ax.set_ylabel("Gewicht", fontsize=8, color="#1e293b")
                            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m.%Y'))
                            ax.tick_params(axis="both", labelsize=8, colors="#475569")
                            ax.legend(fontsize=8, loc="upper left", frameon=True)
                            ax.grid(True, linestyle="--", alpha=0.5, color="#cbd5e1")
                            fig.tight_layout()
                            fig.savefig(chart_area_path, dpi=300)
                            plt.close(fig)

                    pdf = ModernPDFReport()
                    pdf.add_page()
                    pdf.set_fill_color(248, 250, 252)
                    pdf.set_draw_color(226, 232, 240)
                    pdf.rect(10, 20, 190, 28, "DF")

                    pdf.set_xy(15, 23)
                    pdf.set_font("Arial", "B", 11)
                    pdf.set_text_color(15, 23, 42)
                    pdf.cell(95, 6, txt=f"Mitglied: {selected_member_name}".encode("latin-1", "replace").decode("latin-1"), ln=0)
                    pdf.cell(85, 6, txt=f"Tarif: {member_data['Tarif']}".encode("latin-1", "replace").decode("latin-1"), ln=1)

                    pdf.set_x(15)
                    pdf.set_font("Arial", "", 9)
                    pdf.set_text_color(71, 85, 105)
                    pdf.cell(95, 6, txt=f"Check-up Datum: {training_date.strftime('%d.%m.%Y')}", ln=0)
                    pdf.cell(85, 6, txt=f"Mitglied seit: {member_data['Beitrittsdatum']}", ln=1)

                    pdf.set_x(15)
                    pdf.cell(95, 6, txt=f"Schwerpunkt: {exercise_type}".encode("latin-1", "replace").decode("latin-1"), ln=1)

                    pdf.ln(12)
                    pdf.set_font("Arial", "B", 11)
                    pdf.set_text_color(15, 23, 42)
                    pdf.cell(0, 6, txt=f"Erfasste Werte vom {training_date.strftime('%d.%m.%Y')}".encode("latin-1", "replace").decode("latin-1"), ln=True)
                    pdf.ln(2)

                    pdf.set_fill_color(30, 41, 59)
                    pdf.set_text_color(255, 255, 255)
                    pdf.set_font("Arial", "B", 9)
                    pdf.cell(110, 7, " Parameter / Übung", 1, 0, "L", True)
                    pdf.cell(80, 7, " Erfasster Wert ", 1, 1, "R", True)

                    pdf.set_font("Arial", "", 9)
                    pdf.set_text_color(30, 41, 59)
                    fill_toggle = False

                    all_pdf_data = {
                        "Körpergewicht (kg)": koerpergewicht,
                        "Schmerzen / Beschwerden": schmerzen,
                    }
                    all_pdf_data.update(details)

                    for key, val in all_pdf_data.items():
                        clean_key = (
                            key.replace("_", " ")
                            .replace("Drueckende Uebung", "Gewählte Drückende Übung")
                            .replace("Ziehende Uebung", "Gewählte Ziehende Übung")
                            .replace("Uebung", "Übung")
                        )
                        pdf.set_fill_color(248, 250, 252) if fill_toggle else pdf.set_fill_color(255, 255, 255)
                        pdf.cell(110, 6.5, txt=f"  {clean_key}".encode("latin-1", "replace").decode("latin-1"), border=1, ln=0, align="L", fill=True)
                        pdf.cell(80, 6.5, txt=f"{str(val)}   ".encode("latin-1", "replace").decode("latin-1"), border=1, ln=1, align="R", fill=True)
                        fill_toggle = not fill_toggle

                    if os.path.exists(chart_weight_path):
                        pdf.ln(4)
                        pdf.image(chart_weight_path, x=15, w=180)

                    if os.path.exists(chart_area_path):
                        pdf.ln(2)
                        pdf.image(chart_area_path, x=15, w=180)

                    pdf.ln(4)
                    pdf.set_font("Arial", "B", 11)
                    pdf.cell(0, 6, txt="Trainer-Feedback & Notizen", ln=True)
                    pdf.ln(2)

                    pdf.set_font("Arial", "", 9)
                    pdf.set_fill_color(248, 250, 252)
                    pdf.set_draw_color(226, 232, 240)

                    notes_text = trainer_notes if trainer_notes else "Keine zusätzlichen Notizen erfasst."
                    pdf.multi_cell(190, 6.5, txt=f" {notes_text}".encode("latin-1", "replace").decode("latin-1"), border=1, fill=True, align="L")
                    pdf.output(pdf_filename)

                    if os.path.exists(chart_weight_path): os.remove(chart_weight_path)
                    if os.path.exists(chart_area_path): os.remove(chart_area_path)

                    # E-MAIL VERSAND INKLUSIVE INLINE-LOGO & PREHEADER
                    email_secrets = st.secrets.get("email", {})
                    SENDER_EMAIL = email_secrets.get("absender", "fit@hinkelfit.de")
                    SENDER_PASSWORD = email_secrets.get("passwort", "")
                    SMTP_SERVER = email_secrets.get("smtp_server", "smtp.strato.de") 
                    SMTP_PORT = int(email_secrets.get("smtp_port", 587))

                    msg = MIMEMultipart("mixed")
                    msg["From"] = SENDER_EMAIL
                    msg["To"] = member_email
                    msg["Subject"] = "Deine monatliche Erfolgsmessung bei Hinkelfit"

                    msg_related = MIMEMultipart("related")
                    msg.attach(msg_related)

                    vorname = selected_member_name.split()[0] if selected_member_name else "liebes Mitglied"
                    
                    body_html = f"""
                    <html>
                    <body style="font-family: Arial, sans-serif; color: #333;">
                        <!-- UNSICHTBARER PREHEADER FÜR DIE POSTEINGANGS-VORSCHAU -->
                        <div style="display:none;font-size:1px;color:#333333;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
                            Deine aktuelle Erfolgsmessung ist da! Sieh dir deine Fortschritte an.
                        </div>
                        <p>Hallo {vorname},</p>
                        <p>anbei erhältst du die Dokumentation deiner monatlichen Erfolgsmessung vom {training_date.strftime('%d.%m.%Y')} als PDF-Auswertung inklusive deiner Verlaufskurven.</p>
                        <br>
                        <p>Sportliche Grüße<br>Harald</p>
                        <br>
                        <img src="cid:logo" alt="Hinkelfit Logo" style="width: 250px;">
                    </body>
                    </html>
                    """
                    msg_related.attach(MIMEText(body_html, "html", "utf-8"))

                    # Bild einbetten mit Umbenennung
                    logo_path = os.path.join(BASE_DIR, "Logo heller Hintergrund.jpg")
                    if os.path.exists(logo_path):
                        with open(logo_path, "rb") as img_file:
                            logo_part = MIMEImage(img_file.read())
                            logo_part.add_header('Content-ID', '<logo>')
                            logo_part.add_header('Content-Disposition', 'inline', filename="logo.jpg")
                            msg_related.attach(logo_part)

                    with open(pdf_filename, "rb") as f:
                        attach = MIMEApplication(f.read(), Name=os.path.basename(pdf_filename))
                        attach["Content-Disposition"] = f'attachment; filename="{os.path.basename(pdf_filename)}"'
                        msg.attach(attach)

                    server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
                    server.starttls()
                    server.login(SENDER_EMAIL, SENDER_PASSWORD)
                    server.send_message(msg)
                    server.quit()
                    
                    st.success(f"Die Auswertung wurde als PDF erfolgreich an {member_email} gesendet!")
                except Exception as e:
                    st.warning(f"Fehler beim E-Mail-Versand: {e}")

    # --- ANZEIGE DER HISTORIE AM ENDE DER SEITE ---
    try:
        df_history_show_all = conn.read(spreadsheet=SHEET_URL, worksheet="Historie", ttl=0)
        df_history_show_all = df_history_show_all.dropna(how="all")
        
        # Nur Historie für ausgewähltes Mitglied anzeigen
        if not df_history_show_all.empty and "Name" in df_history_show_all.columns:
            df_history_show = df_history_show_all[df_history_show_all["Name"] == selected_member_name].copy()
        else:
            df_history_show = pd.DataFrame()
    except Exception:
        df_history_show = pd.DataFrame()

    if not df_history_show.empty:
        st.markdown("---")
        st.markdown("### Bisherige Historie & Verlauf")
        
        # Den Namen in der Tabelle verstecken, da wir ja eh schon wissen, wessen Profil es ist
        st.dataframe(df_history_show.drop(columns=["Name"], errors="ignore"), use_container_width=True)

        st.markdown("### Leistungs- und Gewichts-Visualisierung")
        df_filtered_chart = df_history_show.copy()

        if not df_filtered_chart.empty and "Datum" in df_filtered_chart.columns:
            df_filtered_chart["Datum"] = pd.to_datetime(df_filtered_chart["Datum"])
            df_filtered_chart = df_filtered_chart.sort_values("Datum")

            if "Koerpergewicht" in df_filtered_chart.columns and df_filtered_chart["Koerpergewicht"].sum() > 0:
                st.markdown("#### Körpergewicht-Verlauf")
                chart_kg = alt.Chart(df_filtered_chart).mark_line(point=True, strokeWidth=3).encode(
                    x=alt.X('Datum:T', title='Kalendertag', axis=alt.Axis(format='%d.%m.%Y')),
                    y=alt.Y('Koerpergewicht:Q', title='Gewicht (kg)', scale=alt.Scale(zero=False)),
                    tooltip=['Datum:T', 'Koerpergewicht:Q']
                ).interactive()
                st.altair_chart(chart_kg, use_container_width=True)

            df_area_chart = df_filtered_chart[df_filtered_chart["Bereich"] == exercise_type]
            if not df_area_chart.empty:
                st.markdown(f"#### Verlauf für Schwerpunkt: {exercise_type}")
                
                cols_to_plot = []
                if exercise_type == "Krafttraining":
                    cols_to_plot = [c for c in ["Gewicht_Drueckende_Uebung", "Gewicht_Chinesische_Ruderbank", "Gewicht_Kniebeuge", "Gewicht_Kreuzheben"] if c in df_area_chart.columns]
                elif exercise_type == "Funktionelles Training":
                    cols_to_plot = [c for c in ["Sandsack_Gewicht", "KB_Wdh", "SS_Wdh"] if c in df_area_chart.columns]
                elif exercise_type == "Kondition":
                    cols_to_plot = [c for c in ["Tragen_Gewicht"] if c in df_area_chart.columns]
                
                if cols_to_plot:
                    df_melted = df_area_chart.melt(id_vars=["Datum"], value_vars=cols_to_plot, var_name="Übung", value_name="Wert")
                    
                    chart_area = alt.Chart(df_melted).mark_line(point=True, strokeWidth=3).encode(
                        x=alt.X('Datum:T', title='Kalendertag', axis=alt.Axis(format='%d.%m.%Y')),
                        y=alt.Y('Wert:Q', title='Gewicht', scale=alt.Scale(zero=False)),
                        color=alt.Color('Übung:N', legend=alt.Legend(title="Parameter")),
                        tooltip=['Datum:T', 'Übung:N', 'Wert:Q']
                    ).interactive()
                    st.altair_chart(chart_area, use_container_width=True)
    else:
        st.info("Noch keine Daten für Charts vorhanden.")
else:
    st.warning("Die zentrale Mitglieder-Datenbank konnte in Google Sheets nicht geladen werden oder ist leer.")