import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

# --- PASSWORT-ABFRAGE (DER TÜRSTEHER) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Login Hinkelfit Studio")
    st.write("Bitte gib das Studio-Passwort ein, um fortzufahren.")
    
    pwd_input = st.text_input("Passwort", type="password")
    
    if st.button("Einloggen"):
        if pwd_input == st.secrets["studio_passwort"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Falsches Passwort.")
            
    return False

# --- HAUPTPROGRAMM ---
if not check_password():
    st.stop()

# Ab hier startet deine Startseite (nur sichtbar, wenn eingeloggt)
st.title("🏋️ Willkommen im Hinkelfit Studio Dashboard")
st.write("Erfolgreich eingeloggt! Nutze das Menü auf der linken Seite.")
st.info("💡 **Tipp für das Tablet:** Du bleibst solange eingeloggt, bis du den Browser-Tab auf dem Tablet schließt.")

st.divider()

# --- DATENBANK HERZSCHLAG-TEST ---
st.subheader("📡 System-Check: Cloud-Datenbank")
st.write("Prüfe Verbindung zu Google Sheets...")

# Exakte Tabellen-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"

try:
    # 1. Verbindung aufbauen
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. Versuch, das Tabellenblatt zu lesen (ttl=0 verhindert veralteten Cache)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    
    # 3. Erfolgsmeldung
    st.success("✅ **Verbindung erfolgreich!** Dein System spricht live mit Google Sheets.")
    st.dataframe(df)

except Exception as e:
    st.error("❌ **Verbindungsfehler!** Die App kann die Tabelle nicht erreichen.")
    st.write(f"Fehlermeldung vom System: {e}")
    st.info("Tipp: Überprüfe, ob das Tabellenblatt in Google Sheets zu 100% exakt 'Mitglieder' heißt (Groß-/Kleinschreibung beachten!).")import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

# --- PASSWORT-ABFRAGE (DER TÜRSTEHER) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Login Hinkelfit Studio")
    st.write("Bitte gib das Studio-Passwort ein, um fortzufahren.")
    
    pwd_input = st.text_input("Passwort", type="password")
    
    if st.button("Einloggen"):
        if pwd_input == st.secrets["studio_passwort"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Falsches Passwort.")
            
    return False

# --- HAUPTPROGRAMM ---
if not check_password():
    st.stop()

# Ab hier startet deine Startseite (nur sichtbar, wenn eingeloggt)
st.title("🏋️ Willkommen im Hinkelfit Studio Dashboard")
st.write("Erfolgreich eingeloggt! Nutze das Menü auf der linken Seite.")
st.info("💡 **Tipp für das Tablet:** Du bleibst solange eingeloggt, bis du den Browser-Tab auf dem Tablet schließt.")

st.divider()

# --- DATENBANK HERZSCHLAG-TEST ---
st.subheader("📡 System-Check: Cloud-Datenbank")
st.write("Prüfe Verbindung zu Google Sheets...")

# Exakte Tabellen-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"

try:
    # 1. Verbindung aufbauen
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. Versuch, das Tabellenblatt zu lesen (ttl=0 verhindert veralteten Cache)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    
    # 3. Erfolgsmeldung
    st.success("✅ **Verbindung erfolgreich!** Dein System spricht live mit Google Sheets.")
    st.dataframe(df)

except Exception as e:
    st.error("❌ **Verbindungsfehler!** Die App kann die Tabelle nicht erreichen.")
    st.write(f"Fehlermeldung vom System: {e}")
    st.info("Tipp: Überprüfe, ob das Tabellenblatt in Google Sheets zu 100% exakt 'Mitglieder' heißt (Groß-/Kleinschreibung beachten!).")import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

# --- PASSWORT-ABFRAGE (DER TÜRSTEHER) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Login Hinkelfit Studio")
    st.write("Bitte gib das Studio-Passwort ein, um fortzufahren.")
    
    pwd_input = st.text_input("Passwort", type="password")
    
    if st.button("Einloggen"):
        if pwd_input == st.secrets["studio_passwort"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Falsches Passwort.")
            
    return False

# --- HAUPTPROGRAMM ---
if not check_password():
    st.stop()

# Ab hier startet deine Startseite (nur sichtbar, wenn eingeloggt)
st.title("🏋️ Willkommen im Hinkelfit Studio Dashboard")
st.write("Erfolgreich eingeloggt! Nutze das Menü auf der linken Seite.")
st.info("💡 **Tipp für das Tablet:** Du bleibst solange eingeloggt, bis du den Browser-Tab auf dem Tablet schließt.")

st.divider()

# --- DATENBANK HERZSCHLAG-TEST ---
st.subheader("📡 System-Check: Cloud-Datenbank")
st.write("Prüfe Verbindung zu Google Sheets...")

# Exakte Tabellen-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"

try:
    # 1. Verbindung aufbauen
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. Versuch, das Tabellenblatt zu lesen (ttl=0 verhindert veralteten Cache)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    
    # 3. Erfolgsmeldung
    st.success("✅ **Verbindung erfolgreich!** Dein System spricht live mit Google Sheets.")
    st.dataframe(df)

except Exception as e:
    st.error("❌ **Verbindungsfehler!** Die App kann die Tabelle nicht erreichen.")
    st.write(f"Fehlermeldung vom System: {e}")
    st.info("Tipp: Überprüfe, ob das Tabellenblatt in Google Sheets zu 100% exakt 'Mitglieder' heißt (Groß-/Kleinschreibung beachten!).")import streamlit as st

st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

st.title("🏋️ Hinkelfit Studio - Minimaltest")
st.success("✅ Die App läuft und lädt in unter 2 Sekunden!")import streamlit as st

st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

st.title("🏋️ Hinkelfit Studio - Minimaltest")
st.success("✅ Die App läuft und lädt in unter 2 Sekunden!")import streamlit as st

st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

st.title("🏋️ Hinkelfit Studio - Minimaltest")
st.success("✅ Die App läuft und lädt in unter 2 Sekunden!")import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

# --- PASSWORT-ABFRAGE (DER TÜRSTEHER) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Login Hinkelfit Studio")
    st.write("Bitte gib das Studio-Passwort ein, um fortzufahren.")
    
    pwd_input = st.text_input("Passwort", type="password")
    
    if st.button("Einloggen"):
        if pwd_input == st.secrets["studio_passwort"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Falsches Passwort.")
            
    return False

# --- HAUPTPROGRAMM ---
if not check_password():
    st.stop()

# Ab hier startet deine Startseite (nur sichtbar, wenn eingeloggt)
st.title("🏋️ Willkommen im Hinkelfit Studio Dashboard")
st.write("Erfolgreich eingeloggt! Nutze das Menü auf der linken Seite.")
st.info("💡 **Tipp für das Tablet:** Du bleibst solange eingeloggt, bis du den Browser-Tab auf dem Tablet schließt.")

st.divider()

# --- DATENBANK HERZSCHLAG-TEST ---
st.subheader("📡 System-Check: Cloud-Datenbank")
st.write("Prüfe Verbindung zu Google Sheets...")

# Exakte Tabellen-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"

try:
    # 1. Verbindung aufbauen
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. Versuch, das Tabellenblatt zu lesen (ttl=0 verhindert veralteten Cache)
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    
    # 3. Erfolgsmeldung
    st.success("✅ **Verbindung erfolgreich!** Dein System spricht live mit Google Sheets.")
    st.dataframe(df)

except Exception as e:
    st.error("❌ **Verbindungsfehler!** Die App kann die Tabelle nicht erreichen.")
    st.write(f"Fehlermeldung vom System: {e}")
    st.info("Tipp: Überprüfe, ob das Tabellenblatt in Google Sheets zu 100% exakt 'Mitglieder' heißt (Groß-/Kleinschreibung beachten!).")import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Studio", page_icon="🏋️", layout="wide")

# --- PASSWORT-ABFRAGE (DER TÜRSTEHER) ---
def check_password():
    if "password_correct" not in st.session_state:
        st.session_state["password_correct"] = False

    if st.session_state["password_correct"]:
        return True

    st.title("🔒 Login Hinkelfit Studio")
    st.write("Bitte gib das Studio-Passwort ein, um fortzufahren.")
    
    pwd_input = st.text_input("Passwort", type="password")
    
    if st.button("Einloggen"):
        if pwd_input == st.secrets["studio_passwort"]:
            st.session_state["password_correct"] = True
            st.rerun()
        else:
            st.error("❌ Falsches Passwort.")
            
    return False

# --- HAUPTPROGRAMM ---
if not check_password():
    st.stop()

# Ab hier startet deine Startseite (nur sichtbar, wenn eingeloggt)
st.title("🏋️ Willkommen im Hinkelfit Studio Dashboard")
st.write("Erfolgreich eingeloggt! Nutze das Menü auf der linken Seite.")
st.info("💡 **Tipp für das Tablet:** Du bleibst solange eingeloggt, bis du den Browser-Tab auf dem Tablet schließt.")

st.divider()

# --- DATENBANK HERZSCHLAG-TEST ---
st.subheader("📡 System-Check: Cloud-Datenbank")
st.write("Prüfe Verbindung zu Google Sheets...")

# Hier ist deine exakte Tabellen-URL
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"

try:
    # 1. Verbindung aufbauen
    conn = st.connection("gsheets", type=GSheetsConnection)
    
    # 2. Versuch, das leere Tabellenblatt "Mitglieder" zu lesen
    df = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder")
    
    # 3. Wenn das klappt, zeige eine Erfolgsmeldung!
    st.success("✅ **Verbindung erfolgreich!** Dein System spricht live mit Google Sheets.")
    
    # Zeigt eine (noch leere) Tabelle an, als endgültigen Beweis
    st.dataframe(df)

except Exception as e:
    st.error("❌ **Verbindungsfehler!** Die App kann die Tabelle nicht erreichen.")
    st.write(f"Fehlermeldung vom System: {e}")
    st.info("Tipp: Hast du die E-Mail-Adresse des Roboters wirklich in der Tabelle als 'Mitarbeiter' hinzugefügt?")
