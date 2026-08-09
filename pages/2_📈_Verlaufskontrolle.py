import streamlit as st
import pandas as pd
import os
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors
from streamlit_gsheets import GSheetsConnection

# Seitenkonfiguration
st.set_page_config(page_title="Hinkelfit Trainingspläne & Vorlagen", page_icon="🏋️", layout="wide")

st.title("🏋️ Trainingspläne, Vorlagen & Leistungsverlauf")
st.write("Verwalte eigene Templates für Zirkel, EMOMs und Kraftblöcke, erfasse Einheiten und tracke den Fortschritt.")

# --- GOOGLE SHEETS VERBINDUNG ---
SHEET_URL = "https://docs.google.com/spreadsheets/d/1uFLWb2XHLgyuYkNdZv-9T7L1ZV6Ocp-WweeGye-QpNk/edit?gid=1776466270#gid=1776466270"
conn = st.connection("gsheets", type=GSheetsConnection)

# --- MITGLIEDER AUS DER CLOUD LADEN ---
try:
    df_members = conn.read(spreadsheet=SHEET_URL, worksheet="Mitglieder", ttl=0)
    df_members = df_members.dropna(how="all")
except Exception:
    df_members = pd.DataFrame()

if df_members.empty:
    st.warning("Keine Mitglieder in der Cloud gefunden. Bitte lege zuerst Mitglieder an.")
    st.stop()

# --- SAUBERE LÖSUNG: Hilfsspalte "Name" für das Dropdown ---
if "Vorname" in df_members.columns and "Nachname" in df_members.columns:
    df_members["Name"] = df_members["Vorname"].astype(str) + " " + df_members["Nachname"].astype(str)
else:
    df_members["Name"] = "Unbekannt"

# --- MITGLIED AUSWÄHLEN ---
member_options = df_members.apply(
    lambda x: f"{x['Mitglieder_ID']} | {x['Name']}", 
    axis=1
).tolist()

selected_member_str = st.selectbox("Mitglied auswählen:", member_options)
sel_id = selected_member_str.split(" | ")[0]
sel_name = selected_member_str.split(" | ")[1]

# Lokaler Pfad nur für PDF-Export-Downloads benötigt
BASE_DIR = r"C:\Users\carol\Desktop\HinkelFit\Planung Wittislingen\Anmeldung"
MEMBERS_DIR = os.path.join(BASE_DIR, "mitglieder")
safe_member_name = "".join([c if c.isalnum() else "_" for c in sel_name])
member_folder = os.path.join(MEMBERS_DIR, f"{sel_id}_{safe_member_name}")
os.makedirs(member_folder, exist_ok=True)

st.markdown("---")

# --- HISTORIE AUS GOOGLE SHEETS LADEN ---
try:
    df_hist_all = conn.read(spreadsheet=SHEET_URL, worksheet="Historie", ttl=0)
    df_hist_all = df_hist_all.dropna(how="all")
except Exception:
    df_hist_all = pd.DataFrame()

# Filtern nach ausgewähltem Mitglied (entweder über ID oder Name)
if not df_hist_all.empty and "Name" in df_hist_all.columns:
    df_hist_check = df_hist_all[df_hist_all["Name"] == sel_name].copy()
else:
    df_hist_check = pd.DataFrame()

if not df_hist_check.empty:
    df_hist_check["Datum_Parsed"] = pd.to_datetime(df_hist_check["Datum"], errors="coerce")
    latest_date = df_hist_check["Datum_Parsed"].max()
    
    if pd.notna(latest_date):
        latest_str = latest_date.strftime("%Y-%m-%d")
        df_last_session = df_hist_check[df_hist_check["Datum"] == latest_str]
        
        with st.expander(f"👀 Letzte Trainingseinheit vom {latest_str} (Zum Vergleichen anklicken)"):
            cols_to_show = [c for c in ["Block", "Modus", "Uebung", "Sätze/Runden", "Wiederholungen/Distanz", "Gewicht", "Pause_Belastung", "Notizen"] if c in df_last_session.columns]
            st.dataframe(
                df_last_session[cols_to_show],
                use_container_width=True,
                hide_index=True
            )

# --- TABS FÜR HAUPTSTRUKTUR ---
tab1, tab2, tab3, tab4 = st.tabs([
    "📝 Plan & aktuelle Werte erfassen", 
    "⚙️ Vorlagen verwalten (Templates)", 
    "📈 Leistungsverlauf", 
    "📄 PDF Export"
])

# ================= TAB 1: PLAN & EINTRAGUNG =================
with tab1:
    st.subheader("Trainingseinheit für Mitglied zusammenstellen")
    
    # Vorlagen aus Google Sheets laden, falls vorhanden
    template_names = ["Keine (Manuell starten)"]
    try:
        df_templates_list = conn.read(spreadsheet=SHEET_URL, worksheet="Vorlagen", ttl=0)
        df_templates_list = df_templates_list.dropna(how="all")
        if not df_templates_list.empty and "Template_Name" in df_templates_list.columns:
            template_names += df_templates_list["Template_Name"].unique().tolist()
    except Exception:
        pass
            
    selected_template = st.selectbox("⚡ Eigene Vorlage (Template) laden:", template_names)
    
    # Daten initialisieren
    initial_editor_data = [
        {"Block": "Kraft", "Modus": "Normal", "Uebung": "Kniebeuge", "Sätze/Runden": "5", "Wiederholungen/Distanz": "5", "Gewicht": "100 kg", "Pause_Belastung": "2 Min."},
    ]
    initial_block_name = "Starting Strength"
    
    if selected_template != "Keine (Manuell starten)":
        try:
            df_t_load = conn.read(spreadsheet=SHEET_URL, worksheet="Vorlagen", ttl=0)
            df_filtered_t = df_t_load[df_t_load["Template_Name"] == selected_template]
            if not df_filtered_t.empty:
                initial_block_name = selected_template
                initial_editor_data = df_filtered_t[["Block", "Modus", "Uebung", "Sätze/Runden", "Wiederholungen/Distanz", "Gewicht", "Pause_Belastung"]].to_dict(orient="records")
        except Exception:
            pass

    col_date, col_block = st.columns(2)
    with col_date:
        training_date = st.date_input("Datum der Einheit:", value=datetime.today())
    with col_block:
        block_name = st.text_input("Bezeichnung des Blocks / der Einheit:", value=initial_block_name)

    st.markdown("Passe die Übungen, Modi (z.B. EMOM, Zirkel, Normal) und Werte für diese Session an:")

    edited_df = st.data_editor(
        pd.DataFrame(initial_editor_data),
        num_rows="dynamic",
        use_container_width=True,
        key="training_input_editor"
    )
    
    notes_input = st.text_area("Trainer-Notizen (z.B. Technik, Tagesform, Besonderheiten):", value="")

    if st.button("💾 Werte in Cloud-Historie speichern & Plan sichern"):
        if edited_df.empty or edited_df["Uebung"].astype(str).str.strip().eq("").all():
            st.error("Bitte mindestens eine gültige Übung eintragen.")
        else:
            new_rows = []
            date_str = training_date.strftime("%Y-%m-%d")
            
            for _, row in edited_df.iterrows():
                uebung = str(row["Uebung"]).strip()
                if uebung:
                    new_rows.append({
                        "Name": sel_name,
                        "Datum": date_str,
                        "Block": str(row["Block"]),
                        "Modus": str(row["Modus"]),
                        "Uebung": uebung,
                        "Sätze/Runden": str(row["Sätze/Runden"]),
                        "Wiederholungen/Distanz": str(row["Wiederholungen/Distanz"]),
                        "Gewicht": str(row["Gewicht"]),
                        "Pause_Belastung": str(row["Pause_Belastung"]),
                        "Notizen": notes_input
                    })
            
            df_new_entries = pd.DataFrame(new_rows)
            
            if not df_hist_all.empty:
                df_combined = pd.concat([df_hist_all, df_new_entries], ignore_index=True)
            else:
                df_combined = df_new_entries
                
            conn.update(spreadsheet=SHEET_URL, worksheet="Historie", data=df_combined)
            st.cache_data.clear()
            st.success("Trainingsdaten erfolgreich in der Cloud-Historie gespeichert!")
            st.rerun()


# ================= TAB 2: VORLAGEN VERWALTEN =================
with tab2:
    st.subheader("⚙️ Eigene Trainingsvorlagen erstellen & bearbeiten")
    st.write("Hier kannst du wiederkehrende Zirkel (z.B. EMOM-Formate) oder Kraftpläne einmalig anlegen und unter einem Namen abspeichern.")

    new_template_name = st.text_input("Name der neuen Vorlage (z.B. Freitag EMOM & Core):", value="")
    
    template_builder_data = [
        {"Block": "Zirkel", "Modus": "EMOM 15 Min", "Uebung": "Kreuzheben", "Sätze/Runden": "1 Min.", "Wiederholungen/Distanz": "5 Wd.", "Gewicht": "90 kg", "Pause_Belastung": "Rest der Minute"},
        {"Block": "Zirkel", "Modus": "EMOM 15 Min", "Uebung": "Airbike", "Sätze/Runden": "1 Min.", "Wiederholungen/Distanz": "200m", "Gewicht": "High Pace", "Pause_Belastung": "Rest der Minute"},
        {"Block": "Zirkel", "Modus": "EMOM 15 Min", "Uebung": "Burpees", "Sätze/Runden": "1 Min.", "Wiederholungen/Distanz": "10 Wd.", "Gewicht": "Bodyweight", "Pause_Belastung": "Rest der Minute"},
    ]
    
    edited_template_df = st.data_editor(
        pd.DataFrame(template_builder_data),
        num_rows="dynamic",
        use_container_width=True,
        key="template_builder_editor"
    )

    if st.button("💾 Vorlage dauerhaft in Cloud speichern"):
        if not new_template_name.strip():
            st.error("Bitte gib einen Namen für die Vorlage an.")
        else:
            t_rows = []
            for _, r in edited_template_df.iterrows():
                if str(r["Uebung"]).strip():
                    t_rows.append({
                        "Template_Name": new_template_name.strip(),
                        "Block": str(r["Block"]),
                        "Modus": str(r["Modus"]),
                        "Uebung": str(r["Uebung"]),
                        "Sätze/Runden": str(r["Sätze/Runden"]),
                        "Wiederholungen/Distanz": str(r["Wiederholungen/Distanz"]),
                        "Gewicht": str(r["Gewicht"]),
                        "Pause_Belastung": str(r["Pause_Belastung"])
                    })
            df_new_t = pd.DataFrame(t_rows)
            
            try:
                df_all_t = conn.read(spreadsheet=SHEET_URL, worksheet="Vorlagen", ttl=0)
                df_all_t = df_all_t.dropna(how="all")
            except Exception:
                df_all_t = pd.DataFrame()
                
            if not df_all_t.empty and "Template_Name" in df_all_t.columns:
                df_all_t = df_all_t[df_all_t["Template_Name"] != new_template_name.strip()]
                df_all_t = pd.concat([df_all_t, df_new_t], ignore_index=True)
            else:
                df_all_t = df_new_t
                
            conn.update(spreadsheet=SHEET_URL, worksheet="Vorlagen", data=df_all_t)
            st.cache_data.clear()
            st.success(f"Vorlage '{new_template_name}' erfolgreich in der Cloud gespeichert!")
            st.rerun()

    st.markdown("---")
    st.subheader("Vorhandene Vorlagen löschen")
    try:
        df_existing_t = conn.read(spreadsheet=SHEET_URL, worksheet="Vorlagen", ttl=0)
        df_existing_t = df_existing_t.dropna(how="all")
    except Exception:
        df_existing_t = pd.DataFrame()

    if not df_existing_t.empty and "Template_Name" in df_existing_t.columns:
        existing_t_names = df_existing_t["Template_Name"].unique().tolist()
        del_template_choice = st.selectbox("Vorlage zum Löschen wählen:", existing_t_names)
        if st.button("🗑️ Ausgewählte Vorlage löschen"):
            df_existing_t = df_existing_t[df_existing_t["Template_Name"] != del_template_choice]
            conn.update(spreadsheet=SHEET_URL, worksheet="Vorlagen", data=df_existing_t)
            st.cache_data.clear()
            st.success(f"Vorlage '{del_template_choice}' gelöscht.")
            st.rerun()
    else:
        st.info("Keine gespeicherten Vorlagen in der Cloud vorhanden.")


# ================= TAB 3: DIAGRAMM & VERLAUF =================
with tab3:
    st.subheader("📈 Kraft- & Leistungsverlauf")
    
    if df_hist_check.empty:
        st.info("Noch keine Trainingshistorie für dieses Mitglied vorhanden.")
    else:
        available_exercises = df_hist_check["Uebung"].dropna().unique().tolist()
        selected_exercise = st.selectbox("Kernübung für das Verlaufskurven-Diagramm wählen:", available_exercises)
        
        df_exercise = df_hist_check[df_hist_check["Uebung"] == selected_exercise].copy()
        
        df_exercise["Gewicht_Num"] = (
            df_exercise["Gewicht"]
            .astype(str)
            .str.extract(r'([\d\.,]+)')[0]
            .str.replace(',', '.')
            .astype(float)
        )
        
        df_exercise["Datum"] = pd.to_datetime(df_exercise["Datum"])
        df_exercise = df_exercise.sort_values("Datum")
        
        if not df_exercise.empty and df_exercise["Gewicht_Num"].notna().any():
            st.write(f"Verlauf für **{selected_exercise}** (Gewicht/Wert):")
            chart_data = df_exercise.set_index("Datum")["Gewicht_Num"]
            st.line_chart(chart_data)
            
            with st.expander("Tabellarische Historie für diese Übung"):
                cols_hist = [c for c in ["Datum", "Block", "Modus", "Uebung", "Sätze/Runden", "Wiederholungen/Distanz", "Gewicht", "Pause_Belastung", "Notizen"] if c in df_exercise.columns]
                st.dataframe(df_exercise[cols_hist], use_container_width=True, hide_index=True)
        else:
            st.warning(f"Für '{selected_exercise}' konnten keine numerischen Gewichtsdaten für ein Diagramm extrahiert werden.")


# ================= TAB 4: PDF EXPORT =================
with tab4:
    st.subheader("📄 Trainingsplan als PDF exportieren")
    
    pdf_date = st.date_input("Datum für PDF-Ausdruck:", value=datetime.today(), key="pdf_date_input")
    
    if st.button("🖨️ PDF-Plan generieren"):
        pdf_filename = f"Trainingsplan_{sel_id}_{pdf_date.strftime('%Y-%m-%d')}.pdf"
        pdf_path = os.path.join(member_folder, pdf_filename)
        
        doc = SimpleDocTemplate(pdf_path, pagesize=A4, rightMargin=25, leftMargin=25, topMargin=30, bottomMargin=30)
        styles = getSampleStyleSheet()
        
        title_style = ParagraphStyle(
            'TitleStyle', parent=styles['Heading1'], fontName='Helvetica-Bold', fontSize=15, textColor=colors.HexColor('#1f2937'), spaceAfter=4
        )
        subtitle_style = ParagraphStyle(
            'SubTitleStyle', parent=styles['Normal'], fontName='Helvetica', fontSize=10, textColor=colors.HexColor('#4b5563'), spaceAfter=12
        )
        
        elements = [
            Paragraph("HINKELFIT – TRAININGSDOKUMENTATION", title_style),
            Paragraph(f"Mitglied: <b>{sel_name}</b> (ID: {sel_id}) | Stand: {pdf_date.strftime('%d.%m.%Y')}", subtitle_style),
            Spacer(1, 10)
        ]
        
        if not df_hist_check.empty:
            df_pdf_data = df_hist_check[df_hist_check["Datum"] == pdf_date.strftime("%Y-%m-%d")]
        else:
            df_pdf_data = pd.DataFrame()
            
        if df_pdf_data.empty:
            st.warning("Keine Einträge für dieses Datum gefunden. Nutze im ersten Tab den Editor und speichere die Werte ab.")
        else:
            table_data = [["Block", "Modus", "Übung", "Runden", "Wd./Dist.", "Gewicht", "Pause"]]
            for _, r in df_pdf_data.iterrows():
                table_data.append([
                    str(r.get("Block", "")),
                    str(r.get("Modus", "")),
                    str(r.get("Uebung", "")),
                    str(r.get("Sätze/Runden", "")),
                    str(r.get("Wiederholungen/Distanz", "")),
                    str(r.get("Gewicht", "")),
                    str(r.get("Pause_Belastung", ""))
                ])
                
            t = Table(table_data, colWidths=[70, 80, 100, 50, 65, 75, 65])
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#374151')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 6),
                ('BACKGROUND', (0,1), (-1,-1), colors.HexColor('#f9fafb')),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#d1d5db')),
                ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
                ('FONTSIZE', (0,1), (-1,-1), 8.5),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,1), (-1,-1), 5),
                ('BOTTOMPADDING', (0,1), (-1,-1), 5),
            ]))
            
            elements.append(t)
            doc.build(elements)
            
            st.success(f"PDF erfolgreich erstellt unter:\n`{pdf_path}`")
            with open(pdf_path, "rb") as f:
                st.download_button(
                    label="📥 PDF herunterladen",
                    data=f,
                    file_name=pdf_filename,
                    mime="application/pdf"
                )
