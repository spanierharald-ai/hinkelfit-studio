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
st.set_page_config(page_title="Hinkelfit Zahlungen & Rechnungen", page_icon="💶", layout="wide")

# Lokaler Pfad (nur noch für das Hinkelfit Logo in der E-Mail benötigt)
BASE_DIR = r"C:\Users\carol\Desktop\HinkelFit\Planung Wittislingen\Anmeldung"

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
            <p>Sportliche Grüße<br>Harald</p>
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


# --- DATENBANK AUS DER CLOUD LADEN & SPALTEN SICHERSTELLEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception:
    df_members = pd.DataFrame()

needs_update = False
if not df_members.empty:
    if "Zahlungsstatus" not in df_members.columns:
        df_members["Zahlungsstatus"] = "Bezahlt"
        needs_update = True
    if "Offener_Betrag" not in df_members.columns:
        df_members["Offener_Betrag"] = 0.0
        needs_update = True
    if "Letzte_Zahlung" not in df_members.columns:
        df_members["Letzte_Zahlung"] = "-"
        needs_update = True
    if "Letzte_Rechnung_Monat" not in df_members.columns:
        df_members["Letzte_Rechnung_Monat"] = ""
        needs_update = True
        
    # Sicherstellen, dass Offener_Betrag eine Zahl ist
    df_members["Offener_Betrag"] = pd.to_numeric(df_members["Offener_Betrag"], errors="coerce").fillna(0.0)
        
    if needs_update:
        conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
        st.cache_data.clear()

st.title("💶 Zahlungen, LexOffice-Rechnungen & Mahnwesen")

if df_members.empty:
    st.warning("Keine Mitglieder in der Datenbank gefunden. Bitte zuerst über die Anmeldung Mitglieder anlegen.")
    st.stop()


# -------------------------------------------------------------------------
# FLEXIBLE ABRECHNUNGS-MONAT AUSWAHL (FÜR VORAUS-ABRECHNUNG)
# -------------------------------------------------------------------------
today = datetime.date.today()

# Generiere eine Auswahlliste von Monaten (z.B. letzter Monat, aktueller Monat, nächste 3 Monate)
months_options = []
for i in range(-1, 4): # -1 = Vormonat, 0 = Aktueller Monat, 1 = Nächster Monat (Standard bei Voraus), etc.
    y = today.year
    m = today.month + i
    while m > 12:
        m -= 12
        y += 1
    while m < 1:
        m += 1
        y -= 1
    months_options.append(f"{m:02d}.{y}")

# Standardmäßig den NÄCHSTEN Monat auswählen (da im Voraus abgerechnet wird, z.B. im August für September)
default_idx = 2 if len(months_options) > 2 else 0

st.subheader("🧾 LexOffice Rechnungs-Check (Voraus-Abrechnung)")
col_sel1, col_sel2 = st.columns([2, 3])
with col_sel1:
    selected_billing_month = st.selectbox("Welchen Abrechnungsmonat möchtest du prüfen/bearbeiten?", months_options, index=default_idx)
with col_sel2:
    st.info(f"💡 Du rechnest im Voraus ab. Ausgewählter Zielmonat: **{selected_billing_month}**")

df_active_inv = df_members[df_members["Status"].isin(["Aktiv", "Gekündigt"])]

# Prüfen, ob der ausgewählte Monat in der komma-getrennten Liste der erstellten Rechnungen des Mitglieds enthalten ist
def has_invoice_for_month(val, target_month):
    if pd.isna(val) or not str(val).strip():
        return False
    months = [m.strip() for m in str(val).split(",")]
    return target_month in months

df_missing_inv = df_active_inv[~df_active_inv["Letzte_Rechnung_Monat"].apply(lambda x: has_invoice_for_month(x, selected_billing_month))]

if not df_missing_inv.empty:
    st.warning(f"⚠️ Für **{len(df_missing_inv)}** Mitglied(er) wurde für den Monat **{selected_billing_month}** noch keine LexOffice-Rechnung erstellt:")
    
    for idx, row in df_missing_inv.iterrows():
        col_inv1, col_inv2, col_inv3 = st.columns([2, 2, 1])
        with col_inv1:
            st.markdown(f"**{row['Name']}** ({row['Mitglieder_ID']})")
            st.caption(f"Tarif: {row['Tarif']} | Beitritt: {row['Beitrittsdatum']}")
        with col_inv2:
            st.write(f"E-Mail: `{row['Email']}`")
        with col_inv3:
            if st.button("✅ In LexOffice erstellt", key=f"inv_done_{row['Mitglieder_ID']}"):
                m_idx = df_members.index[df_members["Mitglieder_ID"] == row["Mitglieder_ID"]].tolist()[0]
                current_val = str(df_members.at[m_idx, "Letzte_Rechnung_Monat"]) if pd.notna(df_members.at[m_idx, "Letzte_Rechnung_Monat"]) else ""
                months_list = [m.strip() for m in current_val.split(",") if m.strip()]
                if selected_billing_month not in months_list:
                    months_list.append(selected_billing_month)
                df_members.at[m_idx, "Letzte_Rechnung_Monat"] = ", ".join(months_list)
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
                st.cache_data.clear()
                
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
    
    df_open = df_members[(df_members["Offener_Betrag"] > 0) | (df_members["Zahlungsstatus"] == "Offen")]
    
    if not df_open.empty:
        st.warning(f"Achtung: Es gibt aktuell {len(df_open)} Mitglied(er) mit offenen Zahlungen.")
        
        for idx, row in df_open.iterrows():
            with st.expander(f"🔴 {row['Name']} (ID: {row['Mitglieder_ID']}) – Offener Betrag: {row['Offener_Betrag']} €"):
                col_info1, col_info2 = st.columns(2)
                with col_info1:
                    st.write(f"**Tarif:** {row['Tarif']}")
                    st.write(f"**E-Mail:** {row['Email']}")
                with col_info2:
                    st.write(f"**Letzte Zahlung:** {row['Letzte_Zahlung']}")
                    st.write(f"**Status:** {row['Zahlungsstatus']}")
                
                st.markdown("---")
                col_m1, col_m2 = st.columns(2)
                with col_m1:
                    custom_amount = st.number_input("Betrag für Zahlungserinnerung (€):", value=float(row['Offener_Betrag']), key=f"amount_{row['Mitglieder_ID']}")
                with col_m2:
                    st.write("")
                    st.write("")
                    if st.button(f"✉️ Zahlungserinnerung senden", key=f"btn_mail_{row['Mitglieder_ID']}"):
                        email = row.get("Email", "")
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


# -------------------------------------------------------------------------
# TAB 2: ZAHLUNG ZUORDNEN
# -------------------------------------------------------------------------
with tab2:
    st.header("Eingegangene Zahlung zuordnen")
    st.write("Wähle ein Mitglied aus, um eine Zahlung zu verbuchen und den offenen Saldo auszugleichen.")
    
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
                df_members.at[sel_row_idx, "Offener_Betrag"] = new_due
                df_members.at[sel_row_idx, "Letzte_Zahlung"] = str(payment_date)
                if new_due == 0:
                    df_members.at[sel_row_idx, "Zahlungsstatus"] = "Bezahlt"
                
                conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
                st.cache_data.clear()
                
                st.success(f"Zahlung über {paid_amount:.2f} € für {df_members.at[sel_row_idx, 'Name']} verbucht! Neuer offener Saldo: {new_due:.2f} €.")
                st.rerun()


# -------------------------------------------------------------------------
# TAB 3: RECHNUNGS-STATUS VERWALTEN (LEXOFFICE)
# -------------------------------------------------------------------------
with tab3:
    st.header("LexOffice Rechnungsstatus verwalten")
    st.write("Hier kannst du einsehen, für welche Monate ein Mitglied bereits Rechnungen erhalten hat, und den Status bei Bedarf anpassen.")
    
    sel_member_inv = st.selectbox("Mitglied wählen:", df_members["Name"].tolist(), key="inv_select_tab")
    m_inv_idx = df_members.index[df_members["Name"] == sel_member_inv].tolist()[0]
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
            
            df_members.at[m_inv_idx, "Letzte_Rechnung_Monat"] = ", ".join(months_list)
            
            conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
            st.cache_data.clear()
            
            st.success(f"Rechnungsstatus für {sel_member_inv} ({manual_month}) aktualisiert.")
            st.rerun()


# -------------------------------------------------------------------------
# TAB 4: GESAMTÜBERSICHT
# -------------------------------------------------------------------------
with tab4:
    st.header("Gesamtübersicht Zahlungen & Rechnungen")
    
    with st.expander("➕ Offenen Monatsbeitrag / Posten manuell hinzufügen"):
        sel_member_due = st.selectbox("Mitglied:", df_members["Name"].tolist(), key="due_select")
        due_amount = st.number_input("Betrag (€):", value=99.0, key="due_amount_val")
        if st.button("Offenen Posten in Cloud buchen"):
            m_idx = df_members.index[df_members["Name"] == sel_member_due].tolist()[0]
            current_amount = float(df_members.at[m_idx, "Offener_Betrag"])
            df_members.at[m_idx, "Offener_Betrag"] = current_amount + float(due_amount)
            df_members.at[m_idx, "Zahlungsstatus"] = "Offen"
            
            conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
            st.cache_data.clear()
            
            st.success(f"Offener Posten über {due_amount} € für {sel_member_due} hinzugefügt.")
            st.rerun()
            
    st.markdown("---")
    
    # Übersichtstabelle für den gewählten Abrechnungsmonat
    df_overview = df_members.copy()
    df_overview[f"Rechnung ({selected_billing_month})"] = df_overview["Letzte_Rechnung_Monat"].apply(
        lambda x: f"Erstellt" if has_invoice_for_month(x, selected_billing_month) else "Offen"
    )
    
    def style_payment(val):
        if val in ['Offen', 'Offener Betrag']: return 'color: red; font-weight: bold;'
        return 'color: green;'
        
    cols_to_show = ['Mitglieder_ID', 'Name', 'Tarif', 'Zahlungsstatus', 'Offener_Betrag', f"Rechnung ({selected_billing_month})", 'Letzte_Zahlung']
    existing_cols = [c for c in cols_to_show if c in df_overview.columns]
    
    styled_pay_df = df_overview[existing_cols].style.map(style_payment, subset=['Zahlungsstatus'])
    st.dataframe(styled_pay_df, use_container_width=True)