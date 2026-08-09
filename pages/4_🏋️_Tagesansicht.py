import datetime
import pandas as pd
import streamlit as st
from supabase import create_client

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Tagesansicht", page_icon="🏋️", layout="wide")

st.title("🏋️ Trainer-Tagesansicht")
st.write("Dein Cockpit für den heutigen Tag: Wer trainiert, wann geht's los und worauf musst du achten?")

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
    st.error("⚠️ Die Verbindung zu Supabase wurde kurzzeitig unterbrochen. Bitte lade die Seite (F5) neu.")
    st.stop()

if df_members.empty:
    st.warning("Keine Mitgliederdatenbank in der Cloud gefunden. Bitte zuerst Mitglieder anlegen.")
    st.stop()

# --- SAUBERE LÖSUNG: Hilfsspalte "Name" für die Suche/Anzeige anlegen ---
if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
    df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
else:
    df_members["Name"] = "Unbekannt"

# Termine laden
try:
    res_termine = supabase.table("Termine").select("*").execute()
    df_termine = pd.DataFrame(res_termine.data)
    if not df_termine.empty and "Teilnehmer" in df_termine.columns:
        df_termine["Teilnehmer"] = df_termine["Teilnehmer"].fillna("").astype(str)
except Exception:
    df_termine = pd.DataFrame()


# --- DATUMSAUSWAHL ---
col_date1, col_date2 = st.columns([1, 2])
with col_date1:
    selected_date = st.date_input("🗓️ Welchen Tag möchtest du ansehen?", value=datetime.date.today())
    
st.markdown("---")

# --- TERMINE FÜR DEN GEWÄHLTEN TAG FILTERN ---
if not df_termine.empty:
    df_day = df_termine[df_termine["Datum"] == str(selected_date)].copy()
    
    if not df_day.empty:
        # Sortieren nach Uhrzeit
        df_day["Uhrzeit_Sort"] = pd.to_datetime(df_day["Uhrzeit"], format="%H:%M").dt.time
        df_day = df_day.sort_values("Uhrzeit_Sort")
        
        # Wochentag für die Überschrift ermitteln
        wochentage = ["Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag", "Sonntag"]
        wochentag_name = wochentage[selected_date.weekday()]
        
        st.subheader(f"Trainingsplan für {wochentag_name}, den {selected_date.strftime('%d.%m.%Y')}")
        st.write("") # Abstand
        
        # Jeden Termin des Tages als "Karte" anzeigen
        for _, row in df_day.iterrows():
            uhrzeit = str(row["Uhrzeit"])
            art = str(row["Art"])
            dauer = str(row["Dauer"])
            teilnehmer_str = str(row["Teilnehmer"])
            
            with st.container():
                st.markdown(f"### 🕒 {uhrzeit} Uhr - {art} ({dauer})")
                
                teilnehmer_liste = [t.strip() for t in teilnehmer_str.split(",")] if teilnehmer_str.strip() else []
                
                if not teilnehmer_liste:
                    st.info("Noch keine Teilnehmer für diesen Kurs eingetragen.")
                else:
                    for person in teilnehmer_liste:
                        if "Interessent" in person:
                            st.markdown(f"👤 **{person}**")
                        else:
                            # Mitglieder-Daten abrufen
                            member_row = df_members[df_members["Name"] == person]
                            if not member_row.empty:
                                name = member_row.iloc[0]["Name"]
                                warnung = member_row.iloc[0].get("Gesundheits_Notizen", "")
                                
                                if pd.notna(warnung) and str(warnung).strip() != "":
                                    st.error(f"👤 **{name}** ➔ ⚠️ **ACHTUNG:** {warnung}")
                                else:
                                    st.success(f"👤 **{name}** (Keine Einschränkungen hinterlegt)")
                            else:
                                st.write(f"👤 **{person}**")
                
                st.markdown("---")
    else:
        st.success(f"Für den {selected_date.strftime('%d.%m.%Y')} sind aktuell keine Termine geplant. Zeit für administrative Aufgaben (oder eigenes Training)! 💪")
else:
    st.info("Es wurden noch gar keine Termine im System angelegt.")


# --- QUICK-EDIT FÜR GESUNDHEITS-WARNUNGEN ---
st.write("")
st.write("")
with st.expander("⚙️ Gesundheits-Warnungen & Notizen für das Dashboard pflegen"):
    st.write("Übertrage hier einmalig die wichtigsten Einschränkungen aus dem PDF-Anamnesebogen. Diese Notizen leuchten an Trainingstagen in der Übersicht rot auf.")
    
    auswahl_name = st.selectbox("Mitglied auswählen:", ["Bitte wählen..."] + df_members["Name"].tolist())
    
    if auswahl_name != "Bitte wählen...":
        aktuelle_notiz = df_members.loc[df_members["Name"] == auswahl_name, "Gesundheits_Notizen"].values[0]
        if pd.isna(aktuelle_notiz):
            aktuelle_notiz = ""
            
        neue_notiz = st.text_input(f"Kurze Warnung/Notiz für {auswahl_name}:", value=str(aktuelle_notiz).replace('nan', ''), placeholder="z.B. LWS Vorfall 2024, Keine Überkopfbewegungen")
        
        if st.button("💾 Notiz in Cloud speichern"):
            # ID des gewählten Mitglieds ermitteln
            member_id = df_members.loc[df_members["Name"] == auswahl_name, "Mitglieder_ID"].values[0]
            
            # Punktuelles Update direkt in der Supabase-Datenbank
            supabase.table("Mitglieder").update({"Gesundheits_Notizen": neue_notiz}).eq("Mitglieder_ID", member_id).execute()
            
            st.success("Notiz erfolgreich gespeichert! Sie wird ab sofort im Tagesplan angezeigt.")
            st.rerun()
