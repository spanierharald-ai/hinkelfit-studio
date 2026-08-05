import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Studio-Dashboard", page_icon="📊", layout="wide")

st.title("📊 Hinkelfit Studio-Dashboard & KPIs")
st.write("Hier ist der aktuelle Überblick über dein Studio und die wichtigsten Kennzahlen.")

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- DATENBANK AUS DER CLOUD LADEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception:
    df_members = pd.DataFrame()

if df_members.empty:
    st.warning("Keine Mitgliederdaten in der Cloud gefunden. Lege zuerst Mitglieder an.")
    st.stop()

# Sicherstellen, dass notwendige Spalten da sind
needs_update = False
if "Status" not in df_members.columns:
    df_members["Status"] = "Aktiv"
    needs_update = True
if "Tarif" not in df_members.columns:
    df_members["Tarif"] = "Kurse 2x wöchentlich (59€)"
    needs_update = True

if needs_update:
    conn.update(spreadsheet=SHEET_URL, worksheet="Mitglieder", data=df_members)
    st.cache_data.clear()

# --- KPI BERECHNUNGEN ---
total_members = len(df_members)
active_members = len(df_members[df_members["Status"] == "Aktiv"])
paused_members = len(df_members[df_members["Status"] == "Pausiert"])
cancelled_members = len(df_members[df_members["Status"] == "Gekündigt"])

# Tarifpreise-Mapping für die Umsatzberechnung
tariff_prices = {
    "Kurse 2x wöchentlich (59€)": 59,
    "1x wöchentlich Kleingruppen-Personal-Training (99€)": 99,
    "2x wöchentlich Kleingruppen-Personaltraining (179€)": 179
}

def get_monthly_price(tariff_name):
    return tariff_prices.get(tariff_name, 59)

# Monatsumsatz nur aus aktiven Mitgliedern berechnen
active_df = df_members[df_members["Status"] == "Aktiv"]
monthly_revenue = active_df["Tarif"].apply(get_monthly_price).sum()

# --- KPI METRIKEN ANZEIGEN ---
col1, col2, col3, col4 = st.columns(4)
with col1:
    st.metric("Gesamt Mitglieder", total_members)
with col2:
    st.metric("Aktive Mitglieder", active_members)
with col3:
    st.metric("Pausierte Mitglieder", paused_members)
with col4:
    st.metric("Monatsumsatz (laufend)", f"{monthly_revenue:,.2f} €".replace(",", "X").replace(".", ",").replace("X", "."))

st.markdown("---")

# --- FILTER FÜR DIE ÜBERSICHT ---
st.subheader("📋 Mitglieder-Übersicht")

status_filter = st.radio(
    "Nach Status filtern:",
    ["Alle", "Aktiv", "Pausiert", "Gekündigt"],
    horizontal=True
)

if status_filter != "Alle":
    filtered_df = df_members[df_members["Status"] == status_filter]
else:
    filtered_df = df_members

# Anzeige der gefilterten Tabelle
st.dataframe(
    filtered_df[["Mitglieder_ID", "Name", "Tarif", "Status", "Beitrittsdatum", "Email"]],
    use_container_width=True
)