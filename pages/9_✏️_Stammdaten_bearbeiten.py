import streamlit as st
import pandas as pd
from supabase import create_client

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Stammdaten-Editor", page_icon="✏️", layout="wide")

st.title("✏️ Mitglieder-Stammdaten bearbeiten")
st.write("Hier kannst du Kontaktdaten, Tarife und Status bestehender Mitglieder anpassen.")

# --- SUPABASE VERBINDUNG INITIALISIEREN ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- DATENBANK AUS DER CLOUD LADEN ---
try:
    res_members = supabase.table("Mitglieder").select("*").execute()
    df_members = pd.DataFrame(res_members.data)
except Exception as e:
    st.error("⚠️ Die Verbindung zur Supabase-Datenbank wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    st.stop()

if df_members.empty:
    st.warning("Keine Mitglieder in der Datenbank gefunden.")
    st.stop()

# --- TYP-KONFLIKTE VERHINDERN ---
text_columns = ['Vorname', 'Nachname', 'E-Mail', 'Adresse', 'Tarif', 'Status', 'Notizen']
for col in text_columns:
    if col in df_members.columns:
        df_members[col] = df_members[col].astype(object)

# --- SAUBERE LÖSUNG: Hilfsspalte "Name" für die Suche/Anzeige ---
if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
    df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
else:
    df_members["Name"] = "Unbekannt"

# Fallback für die App, falls die Spalten in der Supabase noch nicht angelegt sind
if "Status" not in df_members.columns:
    df_members["Status"] = "Aktiv"
if "Notizen" not in df_members.columns:
    df_members["Notizen"] = ""
    df_members['Notizen'] = df_members['Notizen'].astype(object)

# --- MITGLIEDERSUCHE ---
search_query = st.text_input("🔍 Mitglied suchen (Name oder ID eingeben):", value="")

if search_query.strip():
    # Filtern nach Name oder Mitglieder-ID (Groß-/Kleinschreibung egal)
    filtered_df = df_members[
        df_members['Name'].astype(str).str.contains(search_query, case=False, na=False) |
        df_members['Mitglieder_ID'].astype(str).str.contains(search_query, case=False, na=False)
    ]
else:
    filtered_df = df_members

if filtered_df.empty:
    st.warning("Kein Mitglied gefunden, das deiner Suche entspricht.")
    st.stop()

# --- MITGLIED AUSWÄHLEN ---
member_options = filtered_df.apply(
    lambda x: f"{x['Mitglieder_ID']} | {x['Name']} (E-Mail: {x.get('E-Mail', '-')})", 
    axis=1
).tolist()

selected_member_str = st.selectbox("Mitglied zum Bearbeiten auswählen:", member_options)

if selected_member_str:
    sel_id = selected_member_str.split(" | ")[0]
    # Wichtig: Den echten Index im Haupt-DataFrame ermitteln
    m_idx = df_members.index[df_members["Mitglieder_ID"].astype(str) == str(sel_id)].tolist()[0]
    row = df_members.loc[m_idx]
    
    with st.form("edit_member_form"):
        st.subheader(f"Daten bearbeiten für: {row['Name']} (ID: {row['Mitglieder_ID']})")
        
        col1, col2 = st.columns(2)
        
        with col1:
            # An die echte Datenbank-Struktur angepasst (Vorname/Nachname getrennt)
            new_vorname = st.text_input("Vorname:", value=str(row.get('Vorname', '')).replace('nan', ''))
            new_nachname = st.text_input("Nachname:", value=str(row.get('Nachname', '')).replace('nan', ''))
            new_email = st.text_input("E-Mail-Adresse:", value=str(row.get('E-Mail', '')).replace('nan', ''))
            new_adresse = st.text_area("Adresse:", value=str(row.get('Adresse', '')).replace('nan', ''))
            
        with col2:
            # Tarife exakt an die Formulierungen aus der Anmeldung angepasst
            available_tariffs = [
                "Kurse 2x wöchentlich, 59€ pro Monat",
                "Kleingruppen-Personal-Training 1x wöchentlich, 99€ pro Monat",
                "Kleingruppen-Personal-Training 2x wöchentlich, 179€ pro Monat"
            ]
            current_tariff = row.get('Tarif', available_tariffs[0])
            tariff_index = available_tariffs.index(current_tariff) if current_tariff in available_tariffs else 0
            new_tariff = st.selectbox("Tarif:", available_tariffs, index=tariff_index)
            
            available_statuses = ["Aktiv", "Pausiert", "Gekündigt", "Inaktiv"]
            current_status = row.get('Status', 'Aktiv')
            status_index = available_statuses.index(current_status) if current_status in available_statuses else 0
            new_status = st.selectbox("Status:", available_statuses, index=status_index)
            
            new_notes = st.text_area("Notizen / Historie:", value=str(row.get('Notizen', '')).replace('nan', ''))
            
        submit_edit = st.form_submit_button("💾 Änderungen in die Cloud speichern")
        
        if submit_edit:
            update_data = {
                'Vorname': new_vorname,
                'Nachname': new_nachname,
                'E-Mail': new_email,
                'Adresse': new_adresse,
                'Tarif': new_tariff,
                'Status': new_status,
                'Notizen': new_notes
            }
            
            # Punktuelles Update in Supabase
            supabase.table("Mitglieder").update(update_data).eq("Mitglieder_ID", sel_id).execute()
            
            st.success(f"Die Stammdaten für {new_vorname} {new_nachname} wurden erfolgreich aktualisiert!")
            st.rerun()
