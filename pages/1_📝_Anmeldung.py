import base64
import io
import os
import smtplib
from datetime import datetime
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.image import MIMEImage
from weasyprint import HTML
from PIL import Image, ImageDraw
import numpy as np
import pandas as pd
import streamlit as st
from streamlit_drawable_canvas import st_canvas
from supabase import create_client

st.set_page_config(page_title="Hinkelfit | Anmeldung", page_icon="📝", layout="wide")

if "password_correct" not in st.session_state or not st.session_state["password_correct"]:
    st.warning("🔒 Bitte logge dich zuerst ein.")
    st.stop()

# --- SUPABASE VERBINDUNG INITIALISIEREN ---
@st.cache_resource
def init_supabase():
    url = st.secrets["SUPABASE_URL"]
    key = st.secrets["SUPABASE_KEY"]
    return create_client(url, key)

supabase = init_supabase()

# --- HELPER: SICHERE UNTERSCHRIFT-EXTRAKTION (UMGEHT DEN CANVAS-BUG) ---
def get_signature_array(canvas_result, session_canvas_val=None, fallback_name="", width=700, height=200):
    if canvas_result is not None:
        try:
            img_data = canvas_result.image_data
            if img_data is not None:
                return np.array(img_data, dtype=np.uint8)
        except Exception:
            pass

    raw_dict = {}
    if isinstance(session_canvas_val, dict):
        raw_dict.update(session_canvas_val)
    if canvas_result is not None and hasattr(canvas_result, "__dict__"):
        raw_dict.update(canvas_result.__dict__)

    for v in raw_dict.values():
        if isinstance(v, str) and "data:image" in v and "," in v:
            try:
                b64_str = v.split(",", 1)[1]
                img = Image.open(io.BytesIO(base64.b64decode(b64_str))).convert("RGBA")
                return np.array(img, dtype=np.uint8)
            except Exception:
                pass

    if "data" in raw_dict and isinstance(raw_dict["data"], (list, np.ndarray)):
        try:
            w = int(raw_dict.get("width", width))
            h = int(raw_dict.get("height", height))
            arr = np.array(raw_dict["data"], dtype=np.uint8)
            if arr.size == w * h * 4:
                return arr.reshape((h, w, 4))
        except Exception:
            pass

    json_data = None
    if canvas_result is not None:
        try:
            json_data = getattr(canvas_result, "json_data", None)
        except Exception:
            pass
    if not json_data and isinstance(raw_dict.get("raw"), dict):
        json_data = raw_dict["raw"]
    if not json_data and isinstance(raw_dict.get("json_data"), dict):
        json_data = raw_dict["json_data"]

    if isinstance(json_data, dict) and "objects" in json_data:
        objects = json_data.get("objects") or []
        if len(objects) > 0:
            img = Image.new("RGBA", (width, height), (238, 238, 238, 255))
            draw = ImageDraw.Draw(img)
            drew_something = False
            for obj in objects:
                path = obj.get("path", [])
                stroke_width = int(obj.get("strokeWidth", 3))
                points = []
                for cmd in path:
                    if not isinstance(cmd, list) or len(cmd) < 3:
                        continue
                    op = cmd[0]
                    if op in ("M", "L"):
                        points.append((float(cmd[1]), float(cmd[2])))
                    elif op == "Q" and len(cmd) >= 5:
                        points.append((float(cmd[1]), float(cmd[2])))
                        points.append((float(cmd[3]), float(cmd[4])))
                    elif op == "C" and len(cmd) >= 7:
                        points.append((float(cmd[1]), float(cmd[2])))
                        points.append((float(cmd[3]), float(cmd[4])))
                        points.append((float(cmd[5]), float(cmd[6])))
                if len(points) > 1:
                    draw.line(points, fill=(0, 0, 0, 255), width=stroke_width)
                    drew_something = True
                elif len(points) == 1:
                    x, y = points[0]
                    draw.ellipse([x - 2, y - 2, x + 2, y + 2], fill=(0, 0, 0, 255))
                    drew_something = True
            if drew_something:
                return np.array(img, dtype=np.uint8)

    img = Image.new("RGBA", (width, height), (238, 238, 238, 255))
    draw = ImageDraw.Draw(img)
    sig_text = f"Digital gezeichnet: {fallback_name}".strip()
    draw.text((25, height // 2 - 10), sig_text, fill=(0, 0, 0, 255))
    return np.array(img, dtype=np.uint8)

# --- HELPER: RESET ---
def reset_app():
    for key in ["step", "agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
        st.session_state[key] = (1 if key == "step" else False)
    for k in health_keys:
        st.session_state[k] = False
    for key in ["vorname", "nachname", "email", "telefon", "adresse", "geburtsdatum", "vertragsstart", "signature", "pdf_bytes", "final_tarif"]:
        st.session_state[key] = ("" if key not in ["signature", "pdf_bytes"] else None)
    st.session_state.ziele = []

# --- INITIALISIERUNG ---
if "step" not in st.session_state:
    st.session_state.step = 1

health_keys = [
    "Bluthochdruck", "Herzinfarkt", "Schlaganfall", "Herzrhythmusstörungen",
    "Rückenbeschwerden", "Gelenkbeschwerden", "Künstliches Gelenk",
    "Sonstige Wirbelsäulenbeschwerden", "Diabetes", "Asthma",
    "Neigung zu Krämpfen", "Epilepsie", "Organerkrankungen"
]

for k in health_keys:
    if k not in st.session_state:
        st.session_state[k] = False

for key in ["agb_ok", "dsgvo_ok", "risiko_ok", "haftung_ok", "wahrheit_ok"]:
    if key not in st.session_state:
        st.session_state[key] = False

# -------------------------------------------------------------------------
# SCHRITT 1: ANMELDUNG
# -------------------------------------------------------------------------
if st.session_state.step == 1:
    st.title("📝 Hinkelfit – Mitgliedschaftsanmeldung")
    st.subheader("👤 Persönliche Daten")
    col1, col2 = st.columns(2)
    with col1:
        st.session_state.vorname = st.text_input("Vorname *", value=st.session_state.get("vorname", ""))
        st.session_state.nachname = st.text_input("Nachname *", value=st.session_state.get("nachname", ""))
        st.session_state.adresse = st.text_input("Anschrift (Straße, Hausnummer, PLZ, Ort)", value=st.session_state.get("adresse", ""))
    with col2:
        st.session_state.email = st.text_input("E-Mail-Adresse *", value=st.session_state.get("email", ""))
        st.session_state.telefon = st.text_input("Telefonnummer", value=st.session_state.get("telefon", ""))
        st.session_state.geburtsdatum = st.text_input("Geburtsdatum", value=st.session_state.get("geburtsdatum", ""))
