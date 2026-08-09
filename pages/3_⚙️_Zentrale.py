import datetime
import os
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Zentrale", page_icon="⚙️", layout="wide")

# Lokaler Pfad nur noch für das Logo benötigt
BASE_DIR = r"C:\Users\carol\Desktop\HinkelFit\Planung Wittislingen\Anmeldung"

st.title("Hinkelfit - Studio Zentrale")

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- ZENTRALE E-MAIL FUNKTION ---
def send_hinkelfit_email(to_email, to_name, subject, body_content_html):
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
            <!-- UNSICHTBARER PREHEADER FÜR DIE POSTEINGANGS-VORSCHAU -->
            <div style="display:none;font-size:1px;color:#333333;line-height:1px;max-height:0px;max-width:0px;opacity:0;overflow:hidden;">
                {subject}
            </div>
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

        logo_path = os.path.join(BASE_DIR, "Logo heller Hintergrund.jpg")
        if os.path.exists(logo_path):
            with open(logo_path, "rb") as img_file:
                logo_part = MIMEImage(img_file.read())
                logo_part.add_header('Content-ID', '<logo>')
                logo_part.add_header('Content-Disposition', 'inline', filename="logo.jpg")
                msg_related.attach(logo_part)

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False

def notify_participants(teilnehmer_liste, df_members_check, subject, message_body):
    if not teilnehmer_liste: return
    for t in teilnehmer_liste:
        if "Interessent" in t:
            try:
                email = t.split("Interessent: ")[1].split(",")[0].strip()
                name = t.split(" (")[0].strip()
                if "@" in email:
                    send_hinkelfit_email(email, name, subject, message_body)
            except:
                pass
        else:
            member_row = df_members_check[df_members_check["Name"] == t.strip()]
            if not member_row.empty:
                email = member_row.iloc[0].get("E-Mail", "")
                name = t.strip().split()[0]
                if pd.notna(email) and email != "":
                    send_hinkelfit_email(email, name, subject, message_body)

def get_max_sessions(tarif):
    if pd.isna(tarif): return 0
    if "1x" in tarif: return 1
    if "2x" in tarif: return 2
    return 0

def check_limits(teilnehmer_liste, termin_datum_str, df_termine_check, df_members_check, exclude_termin_id=None):
    if df_termine_check.empty or not teilnehmer_liste: return []
    t_date = pd.to_datetime(termin_datum_str).date()
    start_w = t_date - datetime.timedelta(days=t_date.weekday())
    end_w = start_w + datetime.timedelta(days=6)
    
    df_week = df_termine_check.copy()
    df_week["Datum_dt"] = pd.to_datetime(df_week["Datum"]).dt.date
    df_week = df_week[(df_week["Datum_dt"] >= start_w) & (df_week["Datum_dt"] <= end_w)]
    
    if exclude_termin_id is not None and exclude_termin_id in df_week.index:
        df_week = df_week.drop(index=exclude_termin_id)
        
    overbooked = []
    for person in teilnehmer_liste:
        if "Interessent" in person: continue
        member_row = df_members_check[df_members_check["Name"] == person]
        if member_row.empty: continue
        limit = get_max_sessions(member_row.iloc[0]["Tarif"])
        
        count = 0
        for _, row in df_week.iterrows():
            t_str = str(row["Teilnehmer"])
            current_participants = [t.strip() for t in t_str.split(",")]
            if person in current_participants: count += 1
                
        if count + 1 > limit: overbooked.append((person, limit))
    return overbooked

def get_upcoming_slots(tarif, df_termine_promo, start_of_week, end_of_week):
    today = datetime.date.today()
    if df_termine_promo.empty: return "Leider sind in dieser Woche keine weiteren Termine verfügbar."
    
    df_t = df_termine_promo.copy()
    df_t["Datum_dt"] = pd.to_datetime(df_t["Datum"]).dt.date
    min_date = max(today, start_of_week)
    df_week = df_t[(df_t["Datum_dt"] >= min_date) & (df_t["Datum_dt"] <= end_of_week)]
    
    if "Kurse" in tarif:
        df_week = df_week[df_week["Art"].isin(["Kurs", "Probetraining"])]
    elif tarif == "Probetraining":
        df_week = df_week[df_week["Art"] == "Probetraining"]
    else:
        df_week = df_week[df_week["Art"].isin(["Personaltraining (Kleingruppe)", "Probetraining"])]
        
    if df_week.empty: return "Leider sind in dieser Woche in deinem Bereich keine Termine mehr verfügbar."
        
    df_week = df_week.sort_values(by=["Datum_dt", "Uhrzeit"])
    wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
    slots = []
    for _, row in df_week.iterrows():
        d_obj = row["Datum_dt"]
        day_name = wochentage[d_obj.weekday()]
        slots.append(f"&bull; {day_name}, {d_obj.strftime('%d.%m.')} um {row['Uhrzeit']} Uhr")
        
    return "<br>".join(slots)

# --- VERTRAGS-BERECHNUNG LOGIK ---
def calculate_contract_end(beitrittsdatum_str, kuendigung_eingang_date):
    """Berechnet das Vertragsende basierend auf monatlicher Laufzeit und 2 Wochen Kündigungsfrist."""
    try:
        beitritt_dt = datetime.datetime.strptime(beitrittsdatum_str, "%d.%m.%Y").date()
    except:
        beitritt_dt = kuendigung_eingang_date
        
    day_of_month = beitritt_dt.day
    y = kuendigung_eingang_date.year
    m = kuendigung_eingang_date.month
    
    # Finde die nächsten monatlichen Stichtage ab dem Eingangsdatum
    for _ in range(24): # max 2 Jahre in die Zukunft schauen
        try:
            period_end = datetime.date(y, m, day_of_month)
        except ValueError:
            # Monatsüberlauf abfangen (z.B. 31. in kürzerem Monat -> Monatsletzter)
            if m == 2:
                period_end = datetime.date(y, m, 28)
            else:
                period_end = datetime.date(y, m, 30)
                
        if period_end >= kuendigung_eingang_date:
            # 2 Wochen (14 Tage) Frist prüfen
            notice_deadline = period_end - datetime.timedelta(days=14)
            if kuendigung_eingang_date <= notice_deadline:
                return period_end
            else:
                # Zu spät für diesen Stichtag -> gilt zum nächsten Monat
                if m == 12:
                    y += 1
                    m = 1
                else:
                    m += 1
                try:
                    next_period_end = datetime.date(y, m, day_of_month)
                except ValueError:
                    next_period_end = datetime.date(y, m, 28)
                return next_period_end
        else:
            if m == 12:
                y += 1
                m = 1
            else:
                m += 1
                
    return kuendigung_eingang_date + datetime.timedelta(days=30)


# --- DATENBANKEN AUS GOOGLE SHEETS LADEN & LEBENSZYKLUS PRÜFEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception:
    df_members = pd.DataFrame()

if not df_members.empty:
    # --- SAUBERE LÖSUNG: Spalte "Name" global für das ganze Skript anlegen ---
    if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
        df_members["Name"] = df_members["Vorname"] + " " + df_members["Nachname"]
    else:
        df_members["Name"] = "Unbekannt"

    # Sicherstellen, dass alle nötigen Spalten existieren
    needs_update = False
    if "Status" not in df_members.columns:
        df_members["Status"] = "Aktiv"
        needs_update = True
    if "Mitglieder_ID" not in df_members.columns:
        df_members.insert(0, "Mitglieder_ID", [f"HF-{i:03d}" for i in range(1, len(df_members) + 1)])
        needs_update = True
    if "Kündigungs_Eingang" not in df_members.columns:
        df_members["Kündigungs_Eingang"] = ""
        needs_update = True
    if "Vertrags_Ende" not in df_members.columns:
        df_members["Vertrags_Ende"] = ""
        needs_update = True
        
    # --- AUTOMATISCHER STATUS-CHECK (Gekündigt -> Inaktiv nach Ablauf) ---
    today_date = datetime.date.today()
    for idx, row in df_members.iterrows():
        if row["Status"] == "Gekündigt" and pd.notna(row["Vertrags_Ende"]) and str(row["Vertrags_Ende"]).strip() != "":
            try:
                end_dt = datetime.datetime.strptime(str(row["Vertrags_Ende"]), "%Y-%m-%d").date()
                if today_date > end_dt:
                    df_members.at[idx, "Status"] = "Inaktiv"
                    needs_update = True
            except:
                pass
                
    if needs_update:
        conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
        st.cache_data.clear()

if df_members.empty:
    st.warning("Keine Mitglieder in der Cloud gefunden. Bitte zuerst über die Anmeldung Mitglieder anlegen.")
    st.stop()

# Aktive & in der Kündigungsfrist befindliche Mitglieder dürfen trainieren
df_training_eligible = df_members[df_members["Status"].isin(["Aktiv", "Gekündigt"])]
# Nur wirklich aktive für reine Promos (oder wer noch läuft)
df_active_members = df_members[df_members["Status"] == "Aktiv"]

# Termine aus Google Sheets laden
try:
    df_termine_global = conn.read(spreadsheet=SHEET_URL, worksheet="Termine", ttl=0)
    df_termine_global = df_termine_global.dropna(how="all")
    if "Teilnehmer" in df_termine_global.columns:
        df_termine_global["Teilnehmer"] = df_termine_global["Teilnehmer"].fillna("").astype(str)
except Exception:
    df_termine_global = pd.DataFrame()


# --- TABS DEFINIEREN ---
tab1, tab2, tab3, tab4 = st.tabs(["📅 Termin-Planer", "🎂 Geburtstags-Manager", "👥 Mitglieder-Liste", "✉️ Auslastung & Promo"])


# -------------------------------------------------------------------------
# TAB 1: TERMIN-PLANER
# -------------------------------------------------------------------------
with tab1:
    st.header("Termine planen & verwalten")
    with st.form("new_termin"):
        col1, col2 = st.columns(2)
        with col1:
            termin_datum = st.date_input("Datum")
            termin_uhrzeit = st.time_input("Uhrzeit", value=datetime.time(18, 0))
        with col2:
            termin_art = st.selectbox("Terminart", ["Personaltraining (Kleingruppe)", "Kurs", "Probetraining"])
            termin_dauer = st.selectbox("Dauer", ["60 Minuten", "90 Minuten"])

        i_name, i_email, i_tel = "", "", ""
        if termin_art == "Kurs": 
            eligible_members = df_training_eligible[df_training_eligible["Tarif"].str.contains("Kurse", na=False, case=False)]
        elif termin_art == "Probetraining": 
            eligible_members = df_training_eligible
            st.markdown("---")
            st.markdown("📝 **Neuen Interessenten anlegen (Optional):**")
            col_p1, col_p2, col_p3 = st.columns(3)
            with col_p1: i_name = st.text_input("Name des Interessenten")
            with col_p2: i_email = st.text_input("E-Mail")
            with col_p3: i_tel = st.text_input("Handynummer")
            st.markdown("---")
        else: 
            eligible_members = df_training_eligible[~df_training_eligible["Tarif"].str.contains("Kurse", na=False, case=False)]

        teilnehmer = st.multiselect(
            f"Mitglieder hinzufügen (Optional - Filter: {termin_art})", 
            eligible_members["Name"].tolist() if not eligible_members.empty else []
        )
        submitted = st.form_submit_button("Neuen Termin in die Cloud speichern")

        if submitted:
            conflict = False
            termin_dt = datetime.datetime.combine(termin_datum, termin_uhrzeit)
            termin_end_dt = termin_dt + datetime.timedelta(minutes=75)
            
            if not df_termine_global.empty:
                for _, row in df_termine_global.iterrows():
                    row_date = datetime.datetime.strptime(str(row["Datum"]), "%Y-%m-%d").date()
                    if row_date == termin_datum:
                        exist_start = datetime.datetime.combine(row_date, datetime.datetime.strptime(str(row["Uhrzeit"]), "%H:%M").time())
                        exist_end = exist_start + datetime.timedelta(minutes=75)
                        if termin_dt < exist_end and termin_end_dt > exist_start:
                            conflict = True
                            break

            if termin_art == "Probetraining" and i_name.strip() != "":
                teilnehmer.append(f"{i_name.strip()} (Interessent: {i_email}, {i_tel})")
                
            overbooked_members = check_limits(teilnehmer, str(termin_datum), df_termine_global, df_members)

            if overbooked_members:
                for person, limit in overbooked_members: st.error(f"⚠️ {person} kann nicht hinzugefügt werden! Wochenlimit ({limit}) erreicht.")
            elif conflict:
                st.error(f"⚠️ Buchungskonflikt: Überschneidung mit bestehendem Termin.")
            else:
                new_termin = pd.DataFrame([{
                    "Datum": str(termin_datum), "Uhrzeit": termin_uhrzeit.strftime("%H:%M"),
                    "Art": termin_art, "Dauer": termin_dauer, "Teilnehmer": ", ".join(teilnehmer) if teilnehmer else ""
                }])
                df_to_save = pd.concat([df_termine_global, new_termin], ignore_index=True) if not df_termine_global.empty else new_termin
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Termine", data=df_to_save)
                st.cache_data.clear()
                st.success("✅ Termin erfolgreich in Google Sheets gespeichert!")
                st.rerun()

    st.markdown("---")
    st.subheader("Geplante Termine (Übersicht)")
    if not df_termine_global.empty:
        df_show = df_termine_global.copy()
        df_show["Datum_Sort"] = pd.to_datetime(df_show["Datum"])
        df_show = df_show.sort_values(by=["Datum_Sort", "Uhrzeit"])
        df_show = df_show.drop(columns=["Datum_Sort"])
        
        st.dataframe(df_show, use_container_width=True)
        st.markdown("---")
        st.subheader("⚙️ Bestehende Termine bearbeiten, verschieben & stornieren")
        
        edit_id = st.selectbox(
            "Wähle den Termin aus, den du bearbeiten möchtest:", 
            df_show.index, 
            format_func=lambda x: f"{df_show.loc[x, 'Datum']} - {df_show.loc[x, 'Uhrzeit']} Uhr ({df_show.loc[x, 'Art']})"
        )
        
        selected_termin = df_show.loc[edit_id]
        termin_art_edit = selected_termin["Art"]
        termin_datum_edit = str(selected_termin["Datum"])
        termin_uhrzeit_edit = str(selected_termin["Uhrzeit"])
        current_teilnehmer_list = [t.strip() for t in str(selected_termin["Teilnehmer"]).split(",")] if str(selected_termin["Teilnehmer"]).strip() else []

        col_edit1, col_edit2, col_edit3 = st.columns([1.5, 1.2, 1])
        with col_edit1:
            st.write("**1. Teilnehmer anpassen**")
            
            if termin_art_edit == "Kurs": 
                eligible_members_edit = df_training_eligible[df_training_eligible["Tarif"].str.contains("Kurse", na=False, case=False)]
            elif termin_art_edit == "Probetraining": 
                eligible_members_edit = df_training_eligible
            else: 
                eligible_members_edit = df_training_eligible[~df_training_eligible["Tarif"].str.contains("Kurse", na=False, case=False)]
            
            all_names = eligible_members_edit["Name"].tolist()
            
            for t in current_teilnehmer_list:
                if t in df_members["Name"].tolist() and t not in all_names:
                    all_names.append(t)
                    
            valid_members = [t for t in current_teilnehmer_list if t in all_names]
            interessenten = [t for t in current_teilnehmer_list if "Interessent" in t]

            new_teilnehmer = st.multiselect("Mitglieder hinzufügen / entfernen:", options=all_names, default=valid_members, key=f"multi_edit_{edit_id}")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("💾 Aktualisieren"):
                    final_teilnehmer = new_teilnehmer + interessenten
                    overbooked = check_limits(final_teilnehmer, termin_datum_edit, df_termine_global, df_members, exclude_termin_id=edit_id)
                    if overbooked:
                        for p, l in overbooked: st.error(f"⚠️ {p} hat das Wochenlimit ({l}) erreicht.")
                    else:
                        df_show.at[edit_id, "Teilnehmer"] = ", ".join(final_teilnehmer)
                        conn.update(spreadsheet=SHEET_URL, worksheet="Termine", data=df_show)
                        st.cache_data.clear()
                        st.success("Liste in der Cloud aktualisiert!")
                        st.rerun()
            with col_btn2:
                if st.button("🧹 Alle entfernen"):
                    df_show.at[edit_id, "Teilnehmer"] = ""
                    conn.update(spreadsheet=SHEET_URL, worksheet="Termine", data=df_show)
                    st.cache_data.clear()
                    st.success("Liste geleert!")
                    st.rerun()

        with col_edit2:
            st.write("**2. Termin verschieben**")
            cur_date_obj = datetime.datetime.strptime(termin_datum_edit, "%Y-%m-%d").date()
            cur_time_obj = datetime.datetime.strptime(termin_uhrzeit_edit, "%H:%M").time()
            
            new_date = st.date_input("Neues Datum", value=cur_date_obj, key=f"d_{edit_id}")
            new_time = st.time_input("Neue Uhrzeit", value=cur_time_obj, key=f"t_{edit_id}")
            
            if st.button("🔄 Verschieben & Mail senden"):
                if new_date == cur_date_obj and new_time == cur_time_obj: st.warning("Keine Änderung.")
                else:
                    conflict = False
                    termin_dt = datetime.datetime.combine(new_date, new_time)
                    termin_end_dt = termin_dt + datetime.timedelta(minutes=75)
                    for idx, row in df_show.iterrows():
                        if idx == edit_id: continue 
                        r_date = datetime.datetime.strptime(str(row["Datum"]), "%Y-%m-%d").date()
                        if r_date == new_date:
                            e_start = datetime.datetime.combine(r_date, datetime.datetime.strptime(str(row["Uhrzeit"]), "%H:%M").time())
                            if termin_dt < e_start + datetime.timedelta(minutes=75) and termin_end_dt > e_start:
                                conflict = True
                                break
                    if conflict: st.error("⚠️ Buchungskonflikt am neuen Termin!")
                    else:
                        df_show.at[edit_id, "Datum"] = str(new_date)
                        df_show.at[edit_id, "Uhrzeit"] = new_time.strftime("%H:%M")
                        conn.update(spreadsheet=SHEET_URL, worksheet="Termine", data=df_show)
                        st.cache_data.clear()
                        if current_teilnehmer_list:
                            body = f"<p>dein Training ({termin_art_edit}) wurde von mir verschoben.</p><p><strong>Neuer Termin:</strong> {new_date.strftime('%d.%m.%Y')} um {new_time.strftime('%H:%M')} Uhr.</p><p>Bitte trage dir die neue Zeit ein. Falls du da nicht kannst, antworte mir einfach kurz auf diese E-Mail.</p>"
                            notify_participants(current_teilnehmer_list, df_members, "Dein Hinkelfit Termin wurde verschoben", body)
                        st.success("Verschoben & Teilnehmer informiert!")
                        st.rerun()

        with col_edit3:
            st.write("**3. Termin stornieren**")
            st.info("Sagt das Training ab und schlägt Alternativ-Termine vor.")
            if st.button("🗑️ Stornieren & Mail senden"):
                if current_teilnehmer_list:
                    cur_date_obj = datetime.datetime.strptime(termin_datum_edit, "%Y-%m-%d").date()
                    start_w = cur_date_obj - datetime.timedelta(days=cur_date_obj.weekday())
                    temp_df = df_show.drop(index=edit_id)
                    
                    for t in current_teilnehmer_list:
                        email, name, tarif = None, "", ""
                        if "Interessent" in t:
                            try:
                                email = t.split("Interessent: ")[1].split(",")[0].strip()
                                name = t.split(" (")[0].strip()
                                tarif = "Probetraining"
                            except: pass
                        else:
                            mrow = df_members[df_members["Name"] == t.strip()]
                            if not mrow.empty:
                                email, name, tarif = mrow.iloc[0].get("E-Mail", ""), t.strip().split()[0], mrow.iloc[0].get("Tarif", "")
                        
                        if email and "@" in email:
                            slots_html = get_upcoming_slots(tarif, temp_df, start_w, start_w + datetime.timedelta(days=6))
                            if "Leider" in slots_html: slots_section = "<p>Aktuell habe ich in dieser Woche leider keine weiteren freien Termine. Bitte antworte mir kurz, damit wir eine individuelle Lösung finden.</p>"
                            else: slots_section = f"<p>Als Ersatz schlage ich dir folgende noch freie Termine für diese Woche vor:</p><p>{slots_html}</p><p>Bitte antworte mir kurz, welchen Termin du wahrnehmen möchtest.</p>"
                            body = f"<p>dein Training ({termin_art_edit}) am {cur_date_obj.strftime('%d.%m.%Y')} um {termin_uhrzeit_edit} Uhr muss ich leider absagen.</p><p>Dein Kontingent für diese Woche ist damit wieder freigegeben.</p>{slots_section}"
                            send_hinkelfit_email(email, name, "Dein Hinkelfit Termin wurde abgesagt", body)
                            
                df_show = df_show.drop(index=edit_id)
                conn.update(spreadsheet=SHEET_URL, worksheet="Termine", data=df_show)
                st.cache_data.clear()
                st.success("Termin storniert, aus der Cloud entfernt & Teilnehmer informiert!")
                st.rerun()
    else: st.info("Es sind aktuell keine Termine geplant.")

# -------------------------------------------------------------------------
# TAB 2: GEBURTSTAGS-MANAGER
# -------------------------------------------------------------------------
with tab2:
    st.header("🎂 Geburtstags-Manager")
    today = datetime.date.today()
    upcoming_bdays, bdays_today = [], []
    
    for _, row in df_active_members.iterrows():
        try:
            dob = datetime.datetime.strptime(str(row.get("Geburtsdatum", "")), "%d.%m.%Y").date()
            next_bday = datetime.date(today.year, dob.month, dob.day)
            if next_bday < today: next_bday = datetime.date(today.year + 1, dob.month, dob.day)
            days_until = (next_bday - today).days
            info = {"Name": row["Name"], "Email": row.get("E-Mail", ""), "Wird ... Jahre alt": next_bday.year - dob.year, "In ... Tagen": days_until}
            if days_until == 0: bdays_today.append(info)
            elif 1 <= days_until <= 30: upcoming_bdays.append(info)
        except: pass 
            
    if bdays_today:
        st.balloons()
        st.error("🎉 **HEUTE HABEN GEBURTSTAG!** 🎉")
        for bkid in bdays_today:
            col_b1, col_b2 = st.columns([2, 1])
            with col_b1: st.markdown(f"**{bkid['Name']}** wird heute **{bkid['Wird ... Jahre alt']} Jahre** alt!")
            with col_b2:
                if st.button(f"✉️ Geschenk-E-Mail senden", key=f"mail_{bkid['Name']}"):
                    name = bkid['Name'].split()[0] if bkid['Name'] else "liebes Mitglied"
                    body = "<p>ich wünsche dir alles erdenklich Gute zum Geburtstag! Bleib gesund, stark und weiterhin so motiviert.</p><p>Als kleines Geschenk möchte ich dir 15% Nachlass auf deinen nächsten Kauf eines Kleingruppen-Personal-Trainings geben!</p><p>Melde dich einfach beim nächsten Mal bei mir im Studio, um den Rabatt einzulösen.</p>"
                    if send_hinkelfit_email(bkid["Email"], name, "Herzlichen Glückwunsch zum Geburtstag! 🎉", body):
                        st.success("E-Mail gesendet!")
    st.subheader("Vorschau: Nächste 30 Tage (Aktive Mitglieder)")
    if upcoming_bdays: st.dataframe(pd.DataFrame(upcoming_bdays).drop(columns=["Email"]).sort_values("In ... Tagen"), use_container_width=True)
    else: st.info("Keine Geburtstage aktiver Mitglieder in den nächsten 30 Tagen.")

# -------------------------------------------------------------------------
# TAB 3: MITGLIEDER-LISTE & VERTRAGSKÜNDIGUNG
# -------------------------------------------------------------------------
with tab3:
    st.header("👥 Mitglieder-Liste & Vertragsmanagement")
    
    def style_status(val):
        if val == 'Gekündigt': return 'color: orange; font-weight: bold;'
        elif val == 'Inaktiv': return 'color: red;'
        return 'color: green;'
    
    # Drop 'Name' for visual representation so it matches your old table if desired (optional)
    styled_df = df_members.drop(columns=["Name"], errors="ignore").style.map(style_status, subset=['Status'])
    st.dataframe(styled_df, use_container_width=True)
    
    st.markdown("---")
    st.subheader("⚙️ Vertragsstatus & Kündigung bearbeiten")
    
    member_options = df_members.apply(lambda x: f"{x['Mitglieder_ID']} | {x['Name']} (Status: {x['Status']})", axis=1).tolist()
    manage_member_selection = st.selectbox("Mitglied auswählen:", member_options)
    
    if manage_member_selection:
        selected_id = manage_member_selection.split(" | ")[0]
        selected_name = manage_member_selection.split(" | ")[1].split(" (Status:")[0]
        
        member_idx = df_members.index[df_members["Mitglieder_ID"] == selected_id].tolist()[0]
        current_status = df_members.at[member_idx, "Status"]
        member_email = df_members.at[member_idx, "E-Mail"]
        beitrittsdatum = df_members.at[member_idx, "Datum"] if "Datum" in df_members.columns else ""
        kuendigung_eingang_db = df_members.at[member_idx, "Kündigungs_Eingang"]
        vertrags_ende_db = df_members.at[member_idx, "Vertrags_Ende"]
        
        st.write(f"Ausgewähltes Mitglied: **{selected_name}** ({selected_id}) | Aktueller Status: `{current_status}`")
        if pd.notna(vertrags_ende_db) and str(vertrags_ende_db).strip() != "":
            st.info(f"ℹ️ Kündigungseingang: {kuendigung_eingang_db} | Offizielles Vertragsende: **{vertrags_ende_db}**")
            
        action_choice = st.radio("Aktion wählen:", ["Status manuell ändern", "Vertrag regulär kündigen"], horizontal=True)
        
        if action_choice == "Vertrag regulär kündigen":
            st.write("Berechnet automatisch das Vertragsende (1 Monat Laufzeit, 2 Wochen Kündigungsfrist) und informiert das Mitglied per E-Mail.")
            
            default_date = datetime.date.today()
            kuendigung_datum = st.date_input("Kündigungseingangsdatum:", value=default_date)
            
            if st.button("🚀 Kündigung in der Cloud erfassen & Bestätigungs-Mail senden"):
                # Vertragsende berechnen
                vertrags_ende_date = calculate_contract_end(str(beitrittsdatum), kuendigung_datum)
                
                # In Datenbank schreiben
                df_members.at[member_idx, "Status"] = "Gekündigt"
                df_members.at[member_idx, "Kündigungs_Eingang"] = str(kuendigung_datum)
                df_members.at[member_idx, "Vertrags_Ende"] = str(vertrags_ende_date)
                
                # Wir droppen die Name Spalte beim Speichern, um die Ursprungs-Datenbank sauber zu halten
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
                st.cache_data.clear()
                
                # E-Mail versenden
                if pd.notna(member_email) and "@" in str(member_email):
                    vorname = df_members.at[member_idx, "Vorname"]
                    subject = "Bestätigung deiner Kündigung bei Hinkelfit"
                    
                    body = f"""
                    <p>schade, dass du uns verlässt! Hiermit bestätige ich dir den Eingang deiner Kündigung vom <strong>{kuendigung_datum.strftime('%d.%m.%Y')}</strong>.</p>
                    <p>Gemäß unserer Vertragskonditionen (monatliche Laufzeit bei 2 Wochen Kündigungsfrist) läuft dein Vertrag und damit deine Mitgliedschaft regulär noch bis zum <strong>{vertrags_ende_date.strftime('%d.%m.%Y')}</strong>.</p>
                    <p>Bis dahin kannst du natürlich wie gewohnt am Training teilnehmen.</p>
                    <p>Solltest du es dir irgendwann anders überlegen, bist du jederzeit wieder herzlich willkommen. Ich wünsche dir für deine Zukunft alles Gute!</p>
                    """
                    
                    erfolg = send_hinkelfit_email(member_email, vorname, subject, body)
                    if erfolg:
                        st.success(f"✅ Kündigung erfasst. Vertragsende: {vertrags_ende_date.strftime('%d.%m.%Y')}. Bestätigungs-Mail wurde versendet!")
                    else:
                        st.warning("⚠️ Kündigung in der Cloud gespeichert, aber E-Mail-Versand ist fehlgeschlagen.")
                else:
                    st.success(f"✅ Kündigung erfasst. Vertragsende: {vertrags_ende_date.strftime('%d.%m.%Y')}.")
                st.rerun()
                
        else:
            new_manual_status = st.selectbox("Status auf einen Wert setzen:", ["Aktiv", "Gekündigt", "Inaktiv"], index=["Aktiv", "Gekündigt", "Inaktiv"].index(current_status) if current_status in ["Aktiv", "Gekündigt", "Inaktiv"] else 0)
            if st.button("💾 Manuellen Status speichern"):
                df_members.at[member_idx, "Status"] = new_manual_status
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members.drop(columns=["Name"], errors="ignore"))
                st.cache_data.clear()
                st.success(f"Status von {selected_name} auf '{new_manual_status}' in der Cloud geändert.")
                st.rerun()

# -------------------------------------------------------------------------
# TAB 4: AUSLASTUNG & PROMO
# -------------------------------------------------------------------------
with tab4:
    st.header("✉️ Auslastung & Promo-Mails")
    selected_date = st.date_input("Woche wählen:", value=datetime.date.today())
    start_w = selected_date - datetime.timedelta(days=selected_date.weekday())
    end_w = start_w + datetime.timedelta(days=6)
    
    termine_this_week = pd.DataFrame()
    if not df_termine_global.empty:
        df_t = df_termine_global.copy()
        df_t["Datum_dt"] = pd.to_datetime(df_t["Datum"]).dt.date
        termine_this_week = df_t[(df_t["Datum_dt"] >= start_w) & (df_t["Datum_dt"] <= end_w)]
    
    promo_list = []
    for _, m in df_active_members.iterrows():
        limit = get_max_sessions(m["Tarif"])
        booked = 0
        if not termine_this_week.empty:
            for t in termine_this_week["Teilnehmer"]:
                if m["Name"] in [x.strip() for x in str(t).split(",")]: booked += 1
        offen = limit - booked
        if offen > 0 and m.get("E-Mail", ""):
            promo_list.append({"Name": m["Name"], "Email": m["E-Mail"], "Tarif": m["Tarif"], "Gebucht": booked, "Erlaubt": limit, "Offen": offen})
            
    if promo_list:
        df_promo = pd.DataFrame(promo_list)
        st.write("Folgende **aktive Mitglieder** haben noch offene Kontingente:")
        st.dataframe(df_promo[["Name", "Tarif", "Gebucht", "Erlaubt", "Offen"]], use_container_width=True)
        if st.button("🚀 Promo-E-Mails senden"):
            count = 0
            for _, p in df_promo.iterrows():
                slots_html = get_upcoming_slots(p["Tarif"], df_termine_global, start_w, end_w)
                body = f"<p>ich habe gesehen, dass du in der Woche vom {start_w.strftime('%d.%m.')} bis {end_w.strftime('%d.%m.')} noch {p['Offen']} Trainingseinheit(en) aus deinem Tarif offen hast.</p><p>Hier sind die für dich infrage kommenden, noch anstehenden Termine:</p><p>{slots_html}</p><p>Bitte antworte mir kurz, damit ich dich eintragen kann.</p>"
                if send_hinkelfit_email(p["Email"], p['Name'].split()[0], "Dein Hinkelfit Training – Sichere dir deinen Platz!", body): count += 1
            st.success(f"Erfolgreich {count} Promo-E-Mails versendet!")
    else: st.success("Alle aktiven Mitglieder haben ihre Kontingente vollständig ausgeschöpft!")
