import datetime
import os
import pandas as pd
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Mitglieder & Interessenten", page_icon="👥", layout="wide")

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

st.title("👥 Mitglieder & Interessenten (Bürotag-Checkliste)")

# --- DATENBANKEN AUS DER CLOUD LADEN & SPALTEN SICHERSTELLEN ---
needs_member_update = False
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception:
    df_members = pd.DataFrame()

if not df_members.empty:
    if "Buero_Status" not in df_members.columns:
        df_members["Buero_Status"] = "Offen"
        needs_member_update = True
        
    if needs_member_update:
        conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
        st.cache_data.clear()

try:
    df_termine = conn.read(spreadsheet=SHEET_URL, worksheet="Termine", ttl=0)
    df_termine = df_termine.dropna(how="all")
    if "Teilnehmer" in df_termine.columns:
        df_termine["Teilnehmer"] = df_termine["Teilnehmer"].fillna("").astype(str)
except Exception:
    df_termine = pd.DataFrame()


# --- TABS DEFINIEREN ---
tab1, tab2 = st.tabs(["🆕 Neue Mitglieder", "📋 Interessenten (Probetraining)"])


# -------------------------------------------------------------------------
# TAB 1: NEUE MITGLIEDER
# -------------------------------------------------------------------------
with tab1:
    st.header("Neue Mitglieder für den Bürotag")
    st.write("Hier siehst du alle Mitglieder, deren Aufnahme und Bearbeitung (z. B. LexOffice-Anlage) noch für deinen Bürotag ansteht.")
    
    if not df_members.empty:
        df_neu = df_members[df_members["Buero_Status"] == "Offen"]
        
        if not df_neu.empty:
            st.info(f"Es gibt **{len(df_neu)}** offene Mitglied(er) zu bearbeiten.")
            
            for idx, row in df_neu.iterrows():
                with st.expander(f"🆕 {row['Name']} (ID: {row['Mitglieder_ID']} | Beitritt: {row['Beitrittsdatum']})"):
                    col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
                    with col_m1:
                        st.write(f"**Tarif:** {row['Tarif']}")
                        st.write(f"**Anschrift:** {row['Anschrift']}")
                    with col_m2:
                        st.write(f"**E-Mail:** {row['Email']}")
                        st.write(f"**Telefon:** {row['Telefonnummer']}")
                    with col_m3:
                        st.write("")
                        if st.button("✅ Erledigt / Abhaken", key=f"done_member_{row['Mitglieder_ID']}"):
                            m_idx = df_members.index[df_members["Mitglieder_ID"] == row["Mitglieder_ID"]].tolist()[0]
                            df_members.at[m_idx, "Buero_Status"] = "Erledigt"
                            
                            conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
                            st.cache_data.clear()
                            
                            st.success(f"{row['Name']} als erledigt in der Cloud markiert!")
                            st.rerun()
        else:
            st.success("🎉 Hervorragend! Alle Mitglieder wurden für den Bürotag abgearbeitet.")
            
        st.markdown("---")
        with st.expander("📂 Bereits erledigte Mitglieder einsehen & zurücksetzen"):
            df_done = df_members[df_members["Buero_Status"] == "Erledigt"]
            if not df_done.empty:
                st.dataframe(df_done[["Mitglieder_ID", "Name", "Tarif", "Beitrittsdatum"]], use_container_width=True)
                if st.button("🔄 Alle auf 'Offen' zurücksetzen (z. B. für den nächsten Bürotag)"):
                    df_members["Buero_Status"] = "Offen"
                    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
                    st.cache_data.clear()
                    st.success("Alle Mitglieder wurden wieder auf 'Offen' gesetzt!")
                    st.rerun()
            else:
                st.info("Keine erledigten Mitglieder vorhanden.")
    else:
        st.warning("Keine Mitglieder in der Datenbank gefunden.")


# -------------------------------------------------------------------------
# TAB 2: INTERESSENTEN
# -------------------------------------------------------------------------
with tab2:
    st.header("Interessenten (aus Probetrainings)")
    st.write("Hier werden alle Interessenten aufgelistet, die sich über Probetrainings angemeldet haben.")
    
    if not df_termine.empty:
        interessenten_entries = []
        for t_idx, row in df_termine.iterrows():
            teilnehmer_str = str(row["Teilnehmer"])
            if "Interessent" in teilnehmer_str:
                for t in teilnehmer_str.split(","):
                    t = t.strip()
                    if "Interessent" in t:
                        interessenten_entries.append({
                            "Termin_ID": t_idx,
                            "Datum": row["Datum"],
                            "Uhrzeit": row["Uhrzeit"],
                            "Eintrag": t
                        })
                        
        if interessenten_entries:
            st.info(f"Es wurden **{len(interessenten_entries)}** Interessenten-Einträge in den Terminen gefunden.")
            
            for entry in interessenten_entries:
                with st.expander(f"📋 {entry['Eintrag'].split(' (')[0]} (Termin: {entry['Datum']} um {entry['Uhrzeit']} Uhr)"):
                    st.write(f"**Kontaktdaten:** {entry['Eintrag']}")
                    if st.button("🗑️ Aus Liste entfernen / Erledigt", key=f"done_int_{entry['Termin_ID']}_{entry['Eintrag'][:10]}"):
                        t_str = str(df_termine.at[entry['Termin_ID'], "Teilnehmer"])
                        parts = [p.strip() for p in t_str.split(",")]
                        parts = [p for p in parts if p != entry['Eintrag']]
                        df_termine.at[entry['Termin_ID'], "Teilnehmer"] = ", ".join(parts)
                        
                        conn.update(spreadsheet=SHEET_URL, worksheet="Termine", data=df_termine)
                        st.cache_data.clear()
                        
                        st.success("Interessent bearbeitet und aus der Cloud-Liste entfernt!")
                        st.rerun()
        else:
            st.success("Keine offenen Interessenten in den Terminen gefunden.")
    else:
        st.info("Keine Termine im System vorhanden.")