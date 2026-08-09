import datetime
import os
import pandas as pd
import streamlit as st
from supabase import create_client

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Mitglieder & Interessenten", page_icon="👥", layout="wide")

# --- SUPABASE VERBINDUNG INITIALISIEREN ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

st.title("👥 Mitglieder & Interessenten (Bürotag-Checkliste)")

# --- DATENBANKEN AUS DER CLOUD LADEN ---
try:
    res_members = supabase.table("Mitglieder").select("*").execute()
    df_members = pd.DataFrame(res_members.data)
except Exception as e:
    st.error("⚠️ Die Verbindung zur Supabase-Datenbank wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    df_members = pd.DataFrame()

if df_members.empty:
    st.warning("Keine Mitglieder in der Datenbank gefunden.")
    st.stop()

if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
    df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
else:
    df_members["Name"] = "Unbekannt"
    
if "Buero_Status" not in df_members.columns:
    df_members["Buero_Status"] = "Offen"

try:
    res_termine = supabase.table("Termine").select("*").execute()
    df_termine = pd.DataFrame(res_termine.data)
    if not df_termine.empty and "Teilnehmer" in df_termine.columns:
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
        df_neu = df_members[df_members["Buero_Status"].astype(str).str.strip() == "Offen"]
        
        if not df_neu.empty:
            st.info(f"Es gibt **{len(df_neu)}** offene Mitglied(er) zu bearbeiten.")
            
            for idx, row in df_neu.iterrows():
                beitritt = row.get('Datum', 'Unbekannt')
                with st.expander(f"🆕 {row['Name']} (ID: {row.get('Mitglieder_ID', 'N/A')} | Beitritt: {beitritt})"):
                    col_m1, col_m2, col_m3 = st.columns([2, 2, 1])
                    with col_m1:
                        st.write(f"**Tarif:** {row.get('Tarif', '-')}")
                        st.write(f"**Anschrift:** {row.get('Adresse', '-')}")
                    with col_m2:
                        st.write(f"**E-Mail:** {row.get('E-Mail', '-')}")
                        st.write(f"**Telefon:** {row.get('Telefon', '-')}")
                    with col_m3:
                        st.write("")
                        if st.button("✅ Erledigt / Abhaken", key=f"done_member_{row.get('Mitglieder_ID', idx)}"):
                            supabase.table("Mitglieder").update({"Buero_Status": "Erledigt"}).eq("Mitglieder_ID", row["Mitglieder_ID"]).execute()
                            
                            st.success(f"{row['Name']} als erledigt in der Cloud markiert!")
                            st.rerun()
        else:
            st.success("🎉 Hervorragend! Alle Mitglieder wurden für den Bürotag abgearbeitet.")
            
        st.markdown("---")
        with st.expander("📂 Bereits erledigte Mitglieder einsehen & zurücksetzen"):
            df_done = df_members[df_members["Buero_Status"].astype(str).str.strip() == "Erledigt"]
            if not df_done.empty:
                df_done_show = df_done.copy()
                df_done_show["Beitritt"] = df_done_show.get("Datum", "-")
                st.dataframe(df_done_show[["Mitglieder_ID", "Name", "Tarif", "Beitritt"]], use_container_width=True)
                if st.button("🔄 Alle auf 'Offen' zurücksetzen (z. B. für den nächsten Bürotag)"):
                    supabase.table("Mitglieder").update({"Buero_Status": "Offen"}).eq("Buero_Status", "Erledigt").execute()
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
        for _, row in df_termine.iterrows():
            t_idx = row.get("Termin_ID", _)
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
                        # Finde die Zeile anhand der Termin_ID
                        termin_row = df_termine[df_termine["Termin_ID"] == entry['Termin_ID']].iloc[0]
                        t_str = str(termin_row["Teilnehmer"])
                        parts = [p.strip() for p in t_str.split(",")]
                        parts = [p for p in parts if p != entry['Eintrag']]
                        new_t_str = ", ".join(parts)
                        
                        supabase.table("Termine").update({"Teilnehmer": new_t_str}).eq("Termin_ID", entry['Termin_ID']).execute()
                        
                        st.success("Interessent bearbeitet und aus der Cloud-Liste entfernt!")
                        st.rerun()
        else:
            st.success("Keine offenen Interessenten in den Terminen gefunden.")
    else:
        st.info("Keine Termine im System vorhanden.")
