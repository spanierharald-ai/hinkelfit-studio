import datetime
import pandas as pd
import streamlit as st
from supabase import create_client
import re

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Anwesenheit", page_icon="📍", layout="wide")

st.title("📍 Anwesenheit & Termin-Check-in")

# --- SUPABASE VERBINDUNG INITIALISIEREN ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- DATENBANKEN AUS DER CLOUD LADEN ---
try:
    res_members = supabase.table("Mitglieder").select("*").execute()
    df_members = pd.DataFrame(res_members.data)
except Exception as e:
    st.error("⚠️ Die Verbindung zur Supabase-Datenbank wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    df_members = pd.DataFrame()

if not df_members.empty:
    if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
        df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
    else:
        df_members["Name"] = "Unbekannt"

try:
    res_termine = supabase.table("Termine").select("*").execute()
    df_termine = pd.DataFrame(res_termine.data)
    if not df_termine.empty and "Teilnehmer" in df_termine.columns:
        df_termine["Teilnehmer"] = df_termine["Teilnehmer"].fillna("").astype(str)
except Exception:
    df_termine = pd.DataFrame()

try:
    res_att = supabase.table("Anwesenheit").select("*").execute()
    df_att = pd.DataFrame(res_att.data)
    if df_att.empty:
        df_att = pd.DataFrame(columns=["Datum", "Mitglieder_ID", "Name", "Termin_ID"])
except Exception:
    df_att = pd.DataFrame(columns=["Datum", "Mitglieder_ID", "Name", "Termin_ID"])

# Fallback, falls die Spalte in Supabase noch fehlt
if "Termin_ID" not in df_att.columns:
    df_att["Termin_ID"] = ""


# --- TABS DEFINIEREN ---
tab1, tab2 = st.tabs(["📅 Kurs-Check-in nach Terminplan", "📊 Inaktivitäts-Check"])


# -------------------------------------------------------------------------
# TAB 1: KURS-CHECK-IN NACH TERMINPLAN
# -------------------------------------------------------------------------
with tab1:
    st.header("Check-in via Terminplan")
    st.write("Wähle das Datum aus. Klicke auf die Teilnehmer und speichere die Anwesenheit pro Kurs ab.")
    
    col_d1, col_d2 = st.columns([2, 3])
    with col_d1:
        selected_date = st.date_input("Datum:", value=datetime.date.today())
    with col_d2:
        st.info(f"Ausgewählter Tag: **{selected_date.strftime('%d.%m.%Y')}**")
        
    date_str = str(selected_date)
    st.markdown("---")
    
    if not df_termine.empty:
        df_day_termine = df_termine[df_termine["Datum"] == date_str].copy()
        
        if not df_day_termine.empty:
            df_day_termine = df_day_termine.sort_values("Uhrzeit").reset_index(drop=True)
            
            for t_idx, t_row in df_day_termine.iterrows():
                termin_titel = str(t_row.get("Art", "Training / Kurs")).strip()
                uhrzeit = str(t_row.get("Uhrzeit", "00:00")).strip()
                teilnehmer_raw = str(t_row.get("Teilnehmer", ""))
                
                # Eindeutige ID pro Termin
                raw_t_id = str(t_row.get("Termin_ID", "")).strip()
                if raw_t_id in ["", "nan", "None"]:
                    db_termin_id = f"Kurs_{uhrzeit}_{termin_titel}".replace(" ", "_").replace(":", "")
                else:
                    db_termin_id = raw_t_id
                
                # Anwesende für diesen exakten Kurs abfragen
                already_checked_names = []
                if not df_att.empty:
                    df_today = df_att[df_att["Datum"] == date_str]
                    already_checked_names = df_today[df_today["Termin_ID"] == db_termin_id]["Name"].tolist()
                    
                    # Fallback für alte Einträge, wo Termin_ID noch komplett leer war
                    if not already_checked_names and raw_t_id in ["", "nan", "None"]:
                        already_checked_names = df_today[df_today["Termin_ID"].isin(["", "nan", "None", None])]["Name"].tolist()
                
                with st.expander(f"🏋️‍♂️ {uhrzeit} Uhr – {termin_titel} (Teilnehmer: {teilnehmer_raw})", expanded=True):
                    if not teilnehmer_raw.strip():
                        st.warning("Für diesen Termin sind noch keine Teilnehmer im Kalender eingetragen.")
                        continue
                    
                    teilnehmer_list = [t.strip() for t in teilnehmer_raw.split(",") if t.strip()]
                    
                    # WICHTIG: Das Formular erzwingt einen manuellen Speichern-Button und verhindert UI-Freezes
                    with st.form(f"checkin_form_{t_idx}"):
                        checked_participants = {}
                        cols = st.columns(min(len(teilnehmer_list), 3) if len(teilnehmer_list) > 0 else 1)
                        
                        for p_idx, participant in enumerate(teilnehmer_list):
                            c_idx = p_idx % 3
                            is_present = participant in already_checked_names
                            
                            with cols[c_idx]:
                                checked_participants[participant] = st.checkbox(
                                    participant, 
                                    value=is_present, 
                                    key=f"chk_{t_idx}_{p_idx}"
                                )
                        
                        submit_session = st.form_submit_button(f"💾 Anwesenheit speichern")
                        
                        if submit_session:
                            for name, checked in checked_participants.items():
                                m_id = "-"
                                if not df_members.empty:
                                    match = df_members[df_members["Name"] == name]
                                    if not match.empty:
                                        m_id = str(match.iloc[0]["Mitglieder_ID"])
                                
                                # Lösche immer zuerst den Eintrag für DIESEN Termin
                                supabase.table("Anwesenheit").delete().eq("Datum", date_str).eq("Name", name).eq("Termin_ID", db_termin_id).execute()
                                
                                # Bei alten Terminen sicherheitshalber auch die leeren Termin_IDs löschen
                                if raw_t_id in ["", "nan", "None"]:
                                    supabase.table("Anwesenheit").delete().eq("Datum", date_str).eq("Name", name).eq("Termin_ID", "").execute()
                                    
                                if checked:
                                    supabase.table("Anwesenheit").insert({
                                        "Datum": date_str, 
                                        "Mitglieder_ID": m_id, 
                                        "Name": name, 
                                        "Termin_ID": db_termin_id
                                    }).execute()
                            
                            st.success(f"Anwesenheit für '{termin_titel}' am {date_str} gespeichert!")
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
