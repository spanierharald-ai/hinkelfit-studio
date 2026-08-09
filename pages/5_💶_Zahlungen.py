import datetime
import os
import pandas as pd
import streamlit as st
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from supabase import create_client

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Zahlungen & Rechnungen", page_icon="💶", layout="wide")

# Lokaler Pfad (nur noch für das Hinkelfit Logo in der E-Mail benötigt)
BASE_DIR = r"C:\Users\carol\Desktop\HinkelFit\Planung Wittislingen\Anmeldung"

# --- SUPABASE VERBINDUNG INITIALISIEREN ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

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

        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SENDER_EMAIL, SENDER_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        return False


# --- DATENBANK AUS SUPABASE LADEN ---
try:
    res_members = supabase.table("Mitglieder").select("*").execute()
    df_members = pd.DataFrame(res_members.data)
except Exception as e:
    st.error("⚠️ Die Verbindung zur Supabase-Datenbank wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    st.stop()

if df_members.empty:
    st.warning("Keine Mitglieder in der Datenbank gefunden. Bitte zuerst über die Anmeldung Mitglieder anlegen.")
    st.stop()

# --- SAUBERE LÖSUNG: Hilfsspalte "Name" anlegen ---
if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
    df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
else:
    df_members["Name"] = "Unbekannt"
    
# Sicherstellen, dass Offener_Betrag eine Zahl ist
if "Offener_Betrag" in df_members.columns:
    df_members["Offener_Betrag"] = pd.to_numeric(df_members["Offener_Betrag"], errors="coerce").fillna(0.0)

st.title("💶 Zahlungen, LexOffice-Rechnungen & Mahnwesen")

# -------------------------------------------------------------------------
# FLEXIBLE ABRECHNUNGS-MONAT AUSWAHL (FÜR VORAUS-ABRECHNUNG)
# -------------------------------------------------------------------------
today = datetime.date.today()

months_options = []
for i in range(-1, 4):
    y = today.year
    m = today.month + i
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 1
        y -= 1
    months_options.append(f"{m:02d}.{y}")

default_idx = 2 if len(months_options) > 2 else 0

st.subheader("🧾 LexOffice Rechnungs-Check (Voraus-Abrechnung)")
col_sel1, col_sel2 = st.columns([2, 3])
with col_sel1:
    selected_billing_month = st.selectbox("Welchen Abrechnungsmonat möchtest du prüfen/bearbeiten?", months_options, index=default_idx)
with col_sel2:
    st.info(f"💡 Du rechnest im Voraus ab. Ausgewählter Zielmonat: **{selected_billing_month}**")

df_active_inv = df_members[df_members["Status"].isin(["Aktiv", "Gekündigt"])]

def has_invoice_for_month(val, target_month):
    if pd.isna(val) or not str(val).strip():
        return False
    months = [m.strip() for m in str(val).split(",")]
    return target_month in months

if "Letzte_Rechnung_Monat" in df_active_inv.columns:
    df_missing_inv = df_active_inv[~df_active_inv["Letzte_Rechnung_Monat"].apply(lambda x: has_invoice_for_month(x, selected_billing_month))]
else:
    df_missing_inv = df_active_inv

if not df_missing_inv.empty:
    st.warning(f"⚠️ Für **{len(df_missing_inv)}** Mitglied(er) wurde für den Monat **{selected_billing_month}** noch keine LexOffice-Rechnung erstellt:")
    
    for idx, row in df_missing_inv.iterrows():
        col_inv1, col_inv2, col_inv3 = st.columns([2, 2, 1])
        with col_inv1:
            st.markdown(f"**{row['Name']}** ({row['Mitglieder_ID']})")
            st.caption(f"Tarif: {row.get('Tarif', '-')} | Beitritt: {row.get('Datum', 'Unbekannt')}")
        with col_inv2:
            st.write(f"E-Mail: `{row.get('E-Mail', 'Keine')}`")
        with col_inv3:
            if st.button("✅ In LexOffice erstellt", key=f"inv_done_{row['Mitglieder_ID']}"):
                current_val = str(row.get("Letzte_Rechnung_Monat", "")) if pd.notna(row.get("Letzte_Rechnung_Monat")) else ""
                months_list = [m.strip() for m in current_val.split(",") if m.strip()]
                if selected_billing_month not in months_list:
                    months_list.append(selected_billing_month)
                new_val = ", ".join(months_list)
                
                # Punktuelles Update in Supabase
                supabase.table("Mitglieder").update({"Letzte_Rechnung_Monat": new_val}).eq("Mitglieder_ID", row["Mitglieder_ID"]).execute()
                
                st.success(f"Rechnung für {row['Name']} ({selected_billing_month}) als erstellt markiert!")
                st.rerun()
else:
    st.success(f"✨ Perfekt! Für alle aktiven Mitglieder wurde für den Monat **{selected_billing_month}** eine LexOffice-Rechnung hinterlegt.")

st.markdown("---")

# --- TABS DEFINIEREN ---
tab1, tab2, tab3, tab4 = st.tabs(["⚠️ Offene Beiträge & Mahnungen", "📥 Zahlung zuordnen", "🧾 Rechnungs-Status verwalten", "📊 Gesamtübersicht"])

# -------------------------------------------------------------------------
# TAB 1: OFFENE BEITRÄGE & MAHNUNGEN
# -------------------------------------------------------------------------
with tab1:
    st.header("Offene Beiträge & Zahlungserinnerungen")
    st.write("Hier siehst du alle Mitglieder mit ausstehenden Beiträgen und kannst direkt per E-Mail mahnen.")
    
    if "Offener_Betrag" in df_members.columns and "Zahlungsstatus" in df_members.columns:
        df_open = df_members[(df_members["Offener_Betrag"] > 0) | (df_members["Zahlungsstatus"] == "Offen")]
        
        if not df_open.empty:
            st.warning(f"Achtung: Es gibt aktuell {len(df_open)} Mitglied(er) mit offenen Zahlungen.")
            
            for idx, row in df_open.iterrows():
                with st.expander(f"🔴 {row['Name']} (ID: {row['Mitglieder_ID']}) – Offener Betrag: {row['Offener_Betrag']} €"):
                    col_info1, col_info2 = st.columns(2)
                    with col_info1:
                        st.write(f"**Tarif:** {row.get('Tarif', '-')}")
                        st.write(f"**E-Mail:** {row.get('E-Mail', 'Keine')}")
                    with col_info2:
                        st.write(f"**Letzte Zahlung:** {row.get('Letzte_Zahlung', '-')}")
                        st.write(f"**Status:** {row.get('Zahlungsstatus', '-')}")
                    
                    st.markdown("---")
                    col_m1, col_m2 = st.columns(2)
                    with col_m1:
                        custom_amount = st.number_input("Betrag für Zahlungserinnerung (€):", value=float(row['Offener_Betrag']), key=f"amount_{row['Mitglieder_ID']}")
                    with col_m2:
                        st.write("")
                        st.write("")
                        if st.button(f"✉️ Zahlungserinnerung senden", key=f"btn_mail_{row['Mitglieder_ID']}"):
                            email = row.get("E-Mail", "")
                            name = row.get("Name", "").split()[0]
                            if pd.notna(email) and "@" in str(email):
                                subject = "Zahlungserinnerung – Offener Mitgliedsbeitrag bei Hinkelfit"
                                body = f"""
                                <p>bei der Durchsicht meiner Buchhaltung ist aufgefallen, dass für deine Mitgliedschaft bei Hinkelfit noch ein offener Betrag in Höhe von <strong>{custom_amount:.2f} €</strong> aussteht.</p>
                                <p>Bitte überweise den Betrag zeitnah auf das in den Rechnungen angegebene Bankkonto.</p>
                                <p>Falls sich die Zahlung mit deiner Überweisung überschnitten haben sollte, betrachte diese Nachricht bitte als hinfällig. Vielen Dank!</p>
                                """
                                if send_hinkelfit_email(email, name, subject, body):
                                    st.success(f"Zahlungserinnerung erfolgreich an {row['Name']} gesendet!")
                                else:
                                    st.error("Fehler beim E-Mail-Versand.")
                            else:
                                st.error("Keine gültige E-Mail-Adresse hinterlegt.")
        else:
            st.success("🎉 Hervorragend! Es gibt aktuell keine offenen Beiträge im System.")
    else:
        st.info("Bitte lege die Zahlungs-Spalten in Supabase an, um diesen Bereich zu nutzen.")

# -------------------------------------------------------------------------
# TAB 2: ZAHLUNG ZUORDNEN
# -------------------------------------------------------------------------
with tab2:
    st.header("Eingegangene Zahlung zuordnen")
    st.write("Wähle ein Mitglied aus, um eine Zahlung zu verbuchen und den offenen Saldo auszugleichen.")
    
    if "Offener_Betrag" in df_members.columns:
        member_options = df_members.apply(lambda x: f"{x['Mitglieder_ID']} | {x['Name']} (Offen: {x['Offener_Betrag']} €)", axis=1).tolist()
        selected_member_pay = st.selectbox("Mitglied auswählen:", member_options, key="pay_select")
        
        if selected_member_pay:
            sel_id = selected_member_pay.split(" | ")[0]
            sel_row_idx = df_members.index[df_members["Mitglieder_ID"] == sel_id].tolist()[0]
            
            current_due = float(df_members.at[sel_row_idx, "Offener_Betrag"])
            
            with st.form("payment_form"):
                col_p1, col_p2 = st.columns(2)
                with col_p1:
                    paid_amount = st.number_input("Gezahlter Betrag (€):", value=current_due if current_due > 0 else 99.0)
                    payment_date = st.date_input("Zahlungseingangsdatum:", value=datetime.date.today())
                with col_p2:
                    payment_note = st.text_input("Verwendungszweck / Notiz (z.B. Monatsbeitrag):")
                
                submit_payment = st.form_submit_button("💾 Zahlung in Cloud verbuchen")
                
                if submit_payment:
                    new_due = max(0.0, current_due - float(paid_amount))
                    update_data = {
                        "Offener_Betrag": new_due,
                        "Letzte_Zahlung": str(payment_date)
                    }
                    if new_due == 0:
                        update_data["Zahlungsstatus"] = "Bezahlt"
                    
                    # Punktuelles Update in Supabase
                    supabase.table("Mitglieder").update(update_data).eq("Mitglieder_ID", sel_id).execute()
                    
                    st.success(f"Zahlung über {paid_amount:.2f} € für {df_members.at[sel_row_idx, 'Name']} verbucht! Neuer offener Saldo: {new_due:.2f} €.")
                    st.rerun()

# -------------------------------------------------------------------------
# TAB 3: RECHNUNGS-STATUS VERWALTEN (LEXOFFICE)
# -------------------------------------------------------------------------
with tab3:
    st.header("LexOffice Rechnungsstatus verwalten")
    st.write("Hier kannst du einsehen, für welche Monate ein Mitglied bereits Rechnungen erhalten hat, und den Status bei Bedarf anpassen.")
    
    if "Letzte_Rechnung_Monat" in df_members.columns:
        sel_member_inv = st.selectbox("Mitglied wählen:", df_members["Name"].tolist(), key="inv_select_tab")
        m_inv_idx = df_members.index[df_members["Name"] == sel_member_inv].tolist()[0]
        sel_id = df_members.at[m_inv_idx, "Mitglieder_ID"]
        curr_inv_val = str(df_members.at[m_inv_idx, "Letzte_Rechnung_Monat"])
        
        st.write(f"Erfasste Rechnungsmonate für **{sel_member_inv}**: `{curr_inv_val if curr_inv_val and curr_inv_val != 'nan' else 'Keine'}`")
        
        col_st1, col_st2 = st.columns(2)
        with col_st1:
            manual_month = st.selectbox("Monat für Statusänderung:", months_options, key="man_m_select")
            is_invoiced = has_invoice_for_month(curr_inv_val, manual_month)
            action_type = st.radio("Aktion für diesen Monat:", ["Als 'Erstellt' markieren", "Als 'Offen' (löschen) markieren"], index=0 if not is_invoiced else 1)
        with col_st2:
            st.write("")
            st.write("")
            if st.button("💾 Status für diesen Monat in Cloud speichern"):
                months_list = [m.strip() for m in curr_inv_val.split(",") if m.strip() and m.strip() != 'nan']
                if "Erstellt" in action_type:
                    if manual_month not in months_list:
                        months_list.append(manual_month)
                else:
                    if manual_month in months_list:
                        months_list.remove(manual_month)
                
                new_val = ", ".join(months_list)
                
                supabase.table("Mitglieder").update({"Letzte_Rechnung_Monat": new_val}).eq("Mitglieder_ID", sel_id).execute()
                
                st.success(f"Rechnungsstatus für {sel_member_inv} ({manual_month}) aktualisiert.")
                st.rerun()

# -------------------------------------------------------------------------
# TAB 4: GESAMTÜBERSICHT
# -------------------------------------------------------------------------
with tab4:
    st.header("Gesamtübersicht Zahlungen & Rechnungen")
    
    if "Offener_Betrag" in df_members.columns:
        with st.expander("➕ Offenen Monatsbeitrag / Posten manuell hinzufügen"):
            sel_member_due = st.selectbox("Mitglied:", df_members["Name"].tolist(), key="due_select")
            due_amount = st.number_input("Betrag (€):", value=99.0, key="due_amount_val")
            if st.button("Offenen Posten in Cloud buchen"):
                m_idx = df_members.index[df_members["Name"] == sel_member_due].tolist()[0]
                sel_id = df_members.at[m_idx, "Mitglieder_ID"]
                current_amount = float(df_members.at[m_idx, "Offener_Betrag"])
                new_amount = current_amount + float(due_amount)
                
                update_data = {
                    "Offener_Betrag": new_amount,
                    "Zahlungsstatus": "Offen"
                }
                supabase.table("Mitglieder").update(update_data).eq("Mitglieder_ID", sel_id).execute()
                
                st.success(f"Offener Posten über {due_amount} € für {sel_member_due} hinzugefügt.")
                st.rerun()
                
        st.markdown("---")
        
        df_overview = df_members.copy()
        if "Letzte_Rechnung_Monat" in df_overview.columns:
            df_overview[f"Rechnung ({selected_billing_month})"] = df_overview["Letzte_Rechnung_Monat"].apply(
                lambda x: f"Erstellt" if has_invoice_for_month(x, selected_billing_month) else "Offen"
            )
        
        def style_payment(val):
            if val in ['Offen', 'Offener Betrag']: return 'color: red; font-weight: bold;'
            return 'color: green;'
            
        cols_to_show = ['Mitglieder_ID', 'Name', 'Tarif', 'Zahlungsstatus', 'Offener_Betrag', f"Rechnung ({selected_billing_month})", 'Letzte_Zahlung']
        existing_cols = [c for c in cols_to_show if c in df_overview.columns]
        
        if existing_cols:
            styled_pay_df = df_overview[existing_cols].style.map(style_payment, subset=['Zahlungsstatus'])
            st.dataframe(styled_pay_df, use_container_width=True)
