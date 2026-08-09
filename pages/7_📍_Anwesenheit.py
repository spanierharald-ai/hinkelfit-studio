import datetime
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Anwesenheit", page_icon="📍", layout="wide")

st.title("📍 Anwesenheit & Termin-Check-in")

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATENBANKEN AUS DER CLOUD LADEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception as e:
    st.error("⚠️ Die Verbindung zu Google Sheets wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    df_members = pd.DataFrame()

if not df_members.empty:
    # --- SAUBERE LÖSUNG: Hilfsspalte "Name" für die Abgleiche anlegen ---
    if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
        df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
    else:
        df_members["Name"] = "Unbekannt"

try:
    df_termine = conn.read(spreadsheet=SHEET_URL, worksheet="Termine", ttl=0)
    df_termine = df_termine.dropna(how="all")
    if "Teilnehmer" in df_termine.columns:
        df_termine["Teilnehmer"] = df_termine["Teilnehmer"].fillna("").astype(str)
except Exception:
    df_termine = pd.DataFrame()

try:
    df_att = conn.read(spreadsheet=SHEET_URL, worksheet="Anwesenheit", ttl=0)
    df_att = df_att.dropna(how="all")
except Exception:
    # Falls das Blatt komplett leer ist, initialisieren
    df_att = pd.DataFrame(columns=["Datum", "Mitglieder_ID", "Name"])


# --- TABS DEFINIEREN ---
tab1, tab2 = st.tabs(["📅 Kurs-Check-in nach Terminplan", "📊 Inaktivitäts-Check"])


# -------------------------------------------------------------------------
# TAB 1: KURS-CHECK-IN NACH TERMINPLAN
# -------------------------------------------------------------------------
with tab1:
    st.header("Check-in via Terminplan")
    st.write("Wähle das Datum aus. Das System zeigt dir alle geplanten Termine/Kurse an diesem Tag und die dafür eingetragenen Teilnehmer.")
    
    col_d1, col_d2 = st.columns([2, 3])
    with col_d1:
        selected_date = st.date_input("Datum:", value=datetime.date.today())
    with col_d2:
        st.info(f"Ausgewählter Tag: **{selected_date.strftime('%d.%m.%Y')}**")
        
    date_str = str(selected_date)
    st.markdown("---")
    
    if not df_termine.empty:
        # Finde alle Termine für dieses Datum
        df_day_termine = df_termine[df_termine["Datum"] == date_str]
        
        if not df_day_termine.empty:
            # Bereits eingecheckte Personen an diesem Datum holen
            if not df_att.empty and "Datum" in df_att.columns:
                already_checked_names = df_att[df_att["Datum"] == date_str]["Name"].tolist()
            else:
                already_checked_names = []
            
            for t_idx, t_row in df_day_termine.iterrows():
                termin_titel = t_row.get("Art", "Training / Kurs") 
                uhrzeit = t_row.get("Uhrzeit", "00:00")
                teilnehmer_raw = str(t_row.get("Teilnehmer", ""))
                
                with st.expander(f"🏋️‍♂️ {uhrzeit} Uhr – {termin_titel} (Teilnehmer: {teilnehmer_raw})", expanded=True):
                    if not teilnehmer_raw.strip():
                        st.warning("Für diesen Termin sind noch keine Teilnehmer im Kalender eingetragen.")
                        continue
                    
                    # Teilnehmerliste aufteilen
                    teilnehmer_list = [t.strip() for t in teilnehmer_raw.split(",") if t.strip()]
                    
                    with st.form(f"form_termin_{t_idx}"):
                        checked_participants = {}
                        cols = st.columns(min(len(teilnehmer_list), 3) if len(teilnehmer_list) > 0 else 1)
                        
                        for p_idx, participant in enumerate(teilnehmer_list):
                            c_idx = p_idx % 3
                            # Ist die Person an diesem Tag bereits in der Anwesenheitsliste?
                            is_already_present = participant in already_checked_names
                            
                            with cols[c_idx]:
                                checked_participants[participant] = st.checkbox(
                                    f"{participant}", 
                                    value=is_already_present, 
                                    key=f"chk_{t_idx}_{p_idx}"
                                )
                        
                        submit_session = st.form_submit_button(f"💾 Anwesenheit für '{termin_titel}' in Cloud speichern")
                        
                        if submit_session:
                            df_att_new = df_att.copy()
                            if df_att_new.empty:
                                df_att_new = pd.DataFrame(columns=["Datum", "Mitglieder_ID", "Name"])
                                
                            for name, is_present in checked_participants.items():
                                m_id = "-"
                                if not df_members.empty:
                                    match_row = df_members[df_members["Name"].astype(str).str.contains(name, case=False, na=False)]
                                    if not match_row.empty:
                                        m_id = str(match_row.iloc[0]["Mitglieder_ID"])
                                
                                exists_mask = (df_att_new["Datum"] == date_str) & (df_att_new["Name"] == name)
                                
                                if is_present:
                                    if df_att_new[exists_mask].empty:
                                        new_row = pd.DataFrame([{"Datum": date_str, "Mitglieder_ID": m_id, "Name": name}])
                                        df_att_new = pd.concat([df_att_new, new_row], ignore_index=True)
                                else:
                                    df_att_new = df_att_new[~exists_mask]
                            
                            conn.update(spreadsheet=SHEET_URL, worksheet="Anwesenheit", data=df_att_new)
                            st.cache_data.clear()
                            
                            st.success(f"Anwesenheit für '{termin_titel}' erfolgreich in der Cloud aktualisiert!")
                            st.rerun()
        else:
            st.info(f"Für den {selected_date.strftime('%d.%m.%Y')} sind keine Termine/Kurse im Planer eingetragen.")
    else:
        st.warning("Keine Termine in der Cloud-Datenbank gefunden.")


# -------------------------------------------------------------------------
# TAB 2: INAKTIVITÄTS-CHECK
# -------------------------------------------------------------------------
with tab2:
    st.header("Inaktive Mitglieder (Letzte Trainingseinheiten)")
    st.write("Hier siehst du, wer in den letzten **14 Tagen** laut Anwesenheit nicht beim Training war.")
    
    if not df_att.empty and not df_members.empty:
        df_att_check = df_att.copy()
        df_att_check["Parsed_Date"] = pd.to_datetime(df_att_check["Datum"])
        today_ts = pd.Timestamp(datetime.date.today())
        
        last_seen = df_att_check.groupby(["Mitglieder_ID", "Name"])["Parsed_Date"].max().reset_index()
        last_seen["Tage_her"] = (today_ts - last_seen["Parsed_Date"]).dt.days
        
        df_active = df_members[df_members["Status"].isin(["Aktiv", "Gekündigt"])]
        active_ids = df_active["Mitglieder_ID"].astype(str).tolist()
        
        never_seen = df_active[~df_active["Mitglieder_ID"].astype(str).isin(last_seen["Mitglieder_ID"].astype(str))]
        
        col_warn1, col_warn2 = st.columns(2)
        
        with col_warn1:
            st.subheader("⚠️ Noch nie eingetragen:")
            if not never_seen.empty:
                for _, row in never_seen.iterrows():
                    beitritt = row.get('Datum', 'Unbekannt')
                    st.write(f"- {row['Name']} (Beitritt: {beitritt})")
            else:
                st.success("Alle aktiven Mitglieder waren mindestens einmal da.")
                
        with col_warn2:
            st.subheader("⚠️ Länger als 14 Tage abwesend:")
            long_time_absent = last_seen[(last_seen["Tage_her"] > 14) & (last_seen["Mitglieder_ID"].astype(str).isin(active_ids))]
            
            if not long_time_absent.empty:
                for _, row in long_time_absent.iterrows():
                    st.warning(f"- **{row['Name']}**: Letztes Training vor {row['Tage_her']} Tagen")
            else:
                st.success("Top! Alle aktiven Mitglieder waren in den letzten 2 Wochen im Training.")
    else:
        st.info("Noch nicht genügend Anwesenheits-Daten vorhanden.")
