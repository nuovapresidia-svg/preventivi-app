import streamlit as st
from fpdf import FPDF
from datetime import datetime, timedelta
import pandas as pd
import os
import gspread
from google.oauth2.service_account import Credentials

# --- CONFIGURAZIONE ---
COMPANY_NAME = "Presidia Group srl"
COMPANY_ADDR = "Via Vittorio Veneto, 180/1 - AREZZO"
COMPANY_P_IVA = "P.IVA 07141051214"
COMPANY_WEB = "www.presidiagroup.it"
LOGO_PATH = "logo.png"
SHEET_NAME = "DB_Preventivi"

# --- LISTA UTENTI AUTORIZZATI ---
USERS_LIST = [
    "Seleziona Utente...", 
    "MAX",
    "LUCIA VENEZIANO",
    "SAMANTHA CAPORALINI",
    "STEFANIA PRETE",
    "CARLA CAROLEI"
]

# Colori del Brand
COLOR_PRIMARY = (230, 159, 42)     
COLOR_TEXT = (40, 40, 40)          
COLOR_LIGHT_GRAY = (248, 248, 248) 
COLOR_BONUS_BG = (255, 250, 225)   
COLOR_OPTIONAL_BG = (255, 253, 245) 

LISTA_ZONE = [
    "Tutta Italia", "Nord Italia", "Centro Italia", "Sud Italia e Isole",
    "Lombardia", "Lazio", "Abruzzo", "Basilicata", "Calabria", "Emilia Romagna", "Liguria", "Marche", "Molise", "Sardegna", "Trentino AA", "Umbria", "Valle d Aosta", "Friuli VG", "Veneto", "Emilia Romagna", "Toscana", 
    "Piemonte", "Campania", "Sicilia", "Puglia", "Estero (UE)", "Estero (Extra UE)"
]
PREZZI_ANALISI = {0: 0.00, 1: 5.00, 5: 22.50, 10: 40.00, 15: 52.50, 20: 60.00}

# --- CONNESSIONE GOOGLE SHEETS ---
def get_google_sheet():
    scopes = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
    client = gspread.authorize(creds)
    return client.open(SHEET_NAME).sheet1

def get_next_preventivo_number():
    try:
        sheet = get_google_sheet()
        col_values = sheet.col_values(1)
        if len(col_values) <= 1: return 1
        ids = [int(val) for val in col_values[1:] if str(val).isdigit()]
        return max(ids) + 1 if ids else 1
    except:
        return 1

# SALVATAGGIO COMPLETO DI TUTTI I CAMPI
def save_data_gsheet(data):
    try:
        sheet = get_google_sheet()
        # Convertiamo la lista zone in stringa per salvarla in una cella sola
        zone_str = ", ".join(data['zone'])
        
        new_row = [
            data['preventivo_id'],
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            data['user_name'],
            data['cliente'],
            f"{data['prezzo_1']:.2f}".replace('.', ','),
            data['pagamento'],
            # NUOVI CAMPI PER RISTAMPA
            data['email'],
            f"{data['prezzo_2']:.2f}".replace('.', ','),
            zone_str,
            data['tipologia'],
            data['esiti'],
            data['analisibando_qty'],
            data['scadenza_rate'],
            data['validita'],
            data['note']
        ]
        sheet.append_row(new_row)
        return True
    except Exception as e:
        if "200" in str(e): return True
        st.error(f"Errore salvataggio DB: {e}")
        return False

def load_data_from_gsheet():
    try:
        sheet = get_google_sheet()
        data = sheet.get_all_records()
        if not data: return pd.DataFrame()
        return pd.DataFrame(data)
    except:
        return pd.DataFrame()

# --- FUNZIONI DI UTILITÀ ---
def clean_text(text):
    if not isinstance(text, str): return str(text)
    replacements = {'\u2022': '-', '\u201c': '"', '\u201d': '"', '\u2018': "'", '\u2019': "'", '\u2013': '-', '\u20ac': 'Euro'}
    for k, v in replacements.items(): text = text.replace(k, v)
    return text.encode('latin-1', 'replace').decode('latin-1')

def clear_form():
    st.session_state["k_cliente"] = ""
    st.session_state["k_email"] = ""
    st.session_state["k_prezzo1"] = 0.0
    st.session_state["k_opz_biennale"] = False
    st.session_state["k_prezzo2"] = 0.0
    st.session_state["k_zone"] = ["Tutta Italia"]
    st.session_state["k_tipologia"] = ""
    st.session_state["k_esiti"] = "Sì" 
    st.session_state["k_analisi"] = 0
    st.session_state["k_pagamento"] = "Bonifico Bancario 30gg d.f."
    st.session_state["k_scadenza"] = "Unica Soluzione / Semestrale"
    st.session_state["k_validita"] = 15
    st.session_state["k_note"] = ""

# --- 1. AUTENTICAZIONE ---
def check_password():
    if "logged_in" not in st.session_state:
        st.session_state["logged_in"] = False
        st.session_state["user_name"] = ""

    if not st.session_state["logged_in"]:
        st.title("🔒 Accesso Area Preventivi")
        col1, col2 = st.columns([2,1])
        with col1:
            user = st.selectbox("Seleziona Commerciale", USERS_LIST)
            pwd = st.text_input("Password", type="password")
            if st.button("Accedi"):
                if pwd == "Presidia2024" and user != "Seleziona Utente...":
                    st.session_state["logged_in"] = True
                    st.session_state["user_name"] = user.upper()
                    st.rerun()
                elif user == "Seleziona Utente...":
                    st.warning("Seleziona un utente.")
                else:
                    st.error("Password errata.")
        return False
    return True

# --- 2. PDF GENERATOR ---
class PDF(FPDF):
    def header(self):
        if os.path.exists(LOGO_PATH): self.image(LOGO_PATH, 10, 8, 45) 
        self.set_font('Helvetica', 'B', 9)
        self.set_text_color(*COLOR_TEXT)
        self.set_xy(100, 8)
        self.cell(100, 4, COMPANY_NAME, ln=True, align='R')
        self.set_font('Helvetica', '', 8)
        self.cell(0, 4, COMPANY_ADDR, ln=True, align='R')
        self.cell(0, 4, COMPANY_P_IVA, ln=True, align='R')
        self.set_text_color(*COLOR_PRIMARY)
        self.cell(0, 4, COMPANY_WEB, ln=True, align='R')
        self.set_xy(10, 32)
        self.set_draw_color(*COLOR_PRIMARY)
        self.set_line_width(0.8)
        self.line(10, 32, 200, 32)
    def footer(self):
        self.set_y(-12)
        self.set_font('Helvetica', 'I', 7)
        self.set_text_color(150, 150, 150)
        self.cell(0, 4, f'Presidia Group srl - {COMPANY_WEB} - Pagina {self.page_no()}', ln=True, align='C')

def create_pdf(data):
    pdf = PDF()
    pdf.set_auto_page_break(auto=True, margin=10)
    pdf.add_page()
    pdf.set_y(36)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(80, 80, 80)
    commerciale = data.get('user_name', 'N.D.')
    pdf.cell(0, 4, f"COMMERCIALE DI RIFERIMENTO: {clean_text(commerciale)}", ln=True)
    pdf.set_y(44)
    pdf.set_font('Helvetica', 'B', 13)
    pdf.set_text_color(*COLOR_PRIMARY)
    title = "PREVENTIVO SERVIZI DI\nABBONAMENTO INFO GARE ED ESITI"
    y_start = pdf.get_y()
    pdf.multi_cell(95, 6, title)
    pdf.set_xy(110, y_start) 
    pdf.set_fill_color(*COLOR_LIGHT_GRAY)
    pdf.set_draw_color(220, 220, 220)
    pdf.set_line_width(0.2)
    pdf.rect(110, y_start, 90, 28, 'FD') 
    pdf.set_xy(115, y_start + 3)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(80, 5, clean_text(f"Spett.le {data['cliente']}"), ln=True)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_x(115)
    pdf.cell(80, 5, clean_text(f"Email: {data['email']}"), ln=True)
    pdf.set_x(115)
    anno = datetime.now().year
    pdf.cell(80, 5, f"Preventivo N.: {anno}/{str(data['preventivo_id']).zfill(3)}", ln=True)
    pdf.set_x(115)
    pdf.cell(80, 5, f"Data: {datetime.now().strftime('%d/%m/%Y')}", ln=True)
    pdf.set_y(y_start + 34)

    def draw_box(title, z, t):
        pdf.set_font('Helvetica', 'B', 10)
        pdf.set_text_color(255, 255, 255)
        pdf.set_fill_color(*COLOR_PRIMARY)
        pdf.cell(190, 7, f"  {title}", 0, 1, 'L', True)
        y = pdf.get_y()
        pdf.set_text_color(*COLOR_TEXT)
        pdf.set_fill_color(255, 255, 255)
        pdf.set_y(y + 3)
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(45, 5, "COPERTURA GEOGRAFICA:", 0, 0)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(130, 5, clean_text(z))
        pdf.set_x(15)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(45, 5, "TIPOLOGIA GARE:", 0, 0)
        pdf.set_font('Helvetica', '', 9)
        pdf.multi_cell(130, 5, clean_text(t))
        pdf.ln(2)
        h = pdf.get_y() - y
        pdf.set_draw_color(200, 200, 200)
        pdf.rect(10, y, 190, h, 'D')
        pdf.ln(4)

    z_str = ", ".join(data['zone'])
    draw_box("CARATTERISTICHE SERVIZIO INFO GARE", z_str, data['tipologia'])
    st_es = "SI" if data['esiti'] == "Sì" else "NO"
    draw_box(f"CARATTERISTICHE SERVIZIO INFO ESITI ({st_es})", z_str, data['tipologia'])
    
    pdf.ln(4)
    pdf.set_font('Helvetica', 'B', 11)
    pdf.set_text_color(*COLOR_PRIMARY)
    pdf.cell(0, 8, 'PROPOSTA ECONOMICA', ln=True)
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(95, 7, '  Tipologia Servizio', 0, 0, 'L', True)
    pdf.cell(30, 7, 'Imponibile', 0, 0, 'R', True)
    pdf.cell(25, 7, 'IVA (22%)', 0, 0, 'R', True)
    pdf.cell(40, 7, 'Totale  ', 0, 1, 'R', True)
    
    def add_row(d, p):
        iva = p * 0.22
        tot = p + iva
        pdf.set_text_color(0, 0, 0)
        pdf.set_font('Helvetica', '', 9)
        x = pdf.get_x()
        y = pdf.get_y()
        pdf.set_draw_color(230, 230, 230)
        pdf.line(x, y+8, x+190, y+8)
        pdf.cell(95, 8, "  " + clean_text(d), 0, 0, 'L')
        pdf.cell(30, 8, f"E. {p:,.2f}", 0, 0, 'R')
        pdf.cell(25, 8, f"E. {iva:,.2f}", 0, 0, 'R')
        pdf.set_font('Helvetica', 'B', 9)
        pdf.cell(40, 8, f"E. {tot:,.2f}  ", 0, 1, 'R')

    add_row('Abbonamento Annuale (12 Mesi)', data['prezzo_1'])
    if data['prezzo_2'] > 0: add_row('Abbonamento Biennale (24 Mesi)', data['prezzo_2'])
    if data['analisibando_qty'] > 0: add_row(f"Pacchetto ANALISI BANDO PRO ({data['analisibando_qty']} Report)", PREZZI_ANALISI[data['analisibando_qty']])
    
    pdf.ln(8)
    by = pdf.get_y()
    pdf.set_fill_color(*COLOR_BONUS_BG)
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.rect(10, by, 190, 20, 'FD')
    pdf.set_xy(15, by + 4)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.set_text_color(0, 0, 0)
    pdf.cell(30, 4, "BONUS INCLUSO:", ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_xy(45, by + 4)
    pdf.multi_cell(150, 4, "In caso di sottoscrizione del servizio entro il periodo di validita del presente Preventivo, sara riconosciuto un bonus di 2 Polizze Fideiussorie Gratuite del valore di 70 euro (per importi cauzionali fino a 19.000,00 euro).")
    pdf.set_y(by + 26)

    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(25, 6, "Pagamento:", ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(60, 6, clean_text(data['pagamento']), ln=False)
    pdf.set_font('Helvetica', 'B', 9)
    pdf.cell(30, 6, "Scadenza Rate:", ln=False)
    pdf.set_font('Helvetica', '', 9)
    pdf.cell(0, 6, clean_text(data['scadenza_rate']), ln=True)
    scad = (datetime.now() + timedelta(days=int(data['validita']))).strftime('%d/%m/%Y')
    pdf.set_font('Helvetica', 'I', 9)
    pdf.set_text_color(100, 100, 100)
    pdf.cell(0, 6, f"Offerta valida fino al: {scad}", ln=True)
    
    if data['note']:
        pdf.ln(3)
        pdf.set_font('Helvetica', 'B', 9)
        pdf.set_text_color(*COLOR_PRIMARY)
        pdf.cell(0, 5, 'NOTE:', ln=True)
        pdf.set_font('Helvetica', '', 8)
        pdf.set_text_color(0, 0, 0)
        pdf.multi_cell(0, 4, clean_text(data['note']))

    y_curr = pdf.get_y()
    y_start_box = max(y_curr + 10, 238)
    if y_curr > 230 and y_curr < 250: y_start_box = y_curr + 5
    elif y_curr >= 250:
         pdf.add_page()
         y_start_box = 30
    pdf.set_y(y_start_box)
    pdf.set_fill_color(*COLOR_PRIMARY)
    pdf.rect(10, y_start_box, 190, 7, 'F')
    pdf.set_xy(10, y_start_box + 1.5)
    pdf.set_font('Helvetica', 'B', 10)
    pdf.set_text_color(255, 255, 255)
    pdf.cell(190, 5, "SERVIZI OPZIONALI OFFERTI DA PRESIDIA GROUP", ln=True, align='C')
    pdf.set_fill_color(*COLOR_OPTIONAL_BG)
    pdf.set_draw_color(*COLOR_PRIMARY)
    pdf.rect(10, y_start_box + 7, 190, 28, 'FD')
    pdf.set_xy(15, y_start_box + 10)
    pdf.set_font('Helvetica', '', 9)
    pdf.set_text_color(*COLOR_TEXT)
    pdf.cell(4, 6, "-", ln=False)
    pdf.cell(85, 6, "Business Intelligence su Analisi Ribassi Storici", ln=True)
    pdf.set_x(15)
    pdf.cell(4, 6, "-", ln=False)
    pdf.cell(85, 6, "Assistenza Legale di 1 Livello", ln=True)
    pdf.set_xy(105, y_start_box + 10)
    pdf.cell(4, 6, "-", ln=False)
    pdf.multi_cell(85, 6, "Preparazione Documentale di Gara\n(Predisposizione e Caricamento sul Portale)")
    pdf.set_xy(105, pdf.get_y() + 1)
    pdf.cell(4, 6, "-", ln=False)
    pdf.cell(85, 6, "Avvalimenti", ln=True)
    
    return pdf.output(dest='S').encode('latin-1', 'replace')

# --- 4. INTERFACCIA ---
def main():
    st.set_page_config(page_title="Presidia Preventivi", page_icon="📄", layout="wide")
    if not check_password(): return

    col1, col2 = st.columns([1, 4])
    with col1:
        if os.path.exists(LOGO_PATH): st.image(LOGO_PATH, width=90)
    with col2:
        st.title("Generatore Preventivi")
        st.write(f"Commerciale: **{st.session_state['user_name']}**")
    st.markdown("---")

    tab1, tab2 = st.tabs(["📝 Genera Preventivo", "🔍 Cerca & Ristampa"])

    # === SCHEDA GENERA ===
    with tab1:
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("1. Dati Cliente")
            cliente = st.text_input("Ragione Sociale", key="k_cliente")
            email = st.text_input("Email", key="k_email")
            st.subheader("2. Proposta Economica")
            prezzo_1 = st.number_input("Prezzo Annuale (€)", step=50.0, key="k_prezzo1")
            opz_biennale = st.checkbox("Opzione Biennale?", key="k_opz_biennale")
            prezzo_2 = 0.0
            if opz_biennale: prezzo_2 = st.number_input("Prezzo Biennale (€)", step=50.0, key="k_prezzo2")
        with c2:
            st.subheader("3. Dettagli Servizio")
            zone = st.multiselect("Zone", options=LISTA_ZONE, default=["Tutta Italia"], key="k_zone")
            tipologia = st.text_area("Tipologia Gare", height=100, key="k_tipologia")
            esiti = st.radio("Includere Servizio Esiti?", ["Sì", "No"], horizontal=True, key="k_esiti")
            st.markdown("**Opzioni Extra:**")
            analisibando_qty = st.selectbox("Analisi Bando Pro (Quantità)", options=[0, 1, 5, 10, 15, 20], key="k_analisi")
        st.markdown("---")
        c3, c4 = st.columns(2)
        with c3:
            pagamento = st.text_input("Modalità di Pagamento", value="Bonifico Bancario 30gg d.f.", key="k_pagamento")
            scadenza_rate = st.text_input("Scadenza Rate", value="Unica Soluzione / Semestrale", key="k_scadenza")
        with c4:
            validita = st.number_input("Validità Offerta (giorni)", value=15, step=1, key="k_validita")
            note = st.text_area("Note aggiuntive", height=68, key="k_note")
        st.markdown("---")
        
        b1, b2 = st.columns([1,1])
        with b1:
            gen_btn = st.button("📄 Genera e Salva PDF", type="primary")
        with b2:
            st.button("🔄 Reset Campi", on_click=clear_form)

        if gen_btn:
            s_esiti = st.session_state["k_esiti"]
            if not cliente: st.error("Inserire Cliente")
            elif prezzo_1 <= 0: st.error("Inserire Prezzo")
            else:
                try:
                    with st.spinner("Salvataggio..."):
                        next_id = get_next_preventivo_number()
                        data_form = {
                            'preventivo_id': next_id,
                            'user_name': st.session_state['user_name'],
                            'cliente': cliente,
                            'email': email,
                            'prezzo_1': prezzo_1,
                            'prezzo_2': prezzo_2,
                            'zone': zone,
                            'tipologia': tipologia,
                            'esiti': s_esiti,
                            'analisibando_qty': analisibando_qty,
                            'pagamento': pagamento,
                            'scadenza_rate': scadenza_rate,
                            'validita': validita,
                            'note': note
                        }
                        
                        pdf_bytes = create_pdf(data_form)
                        file_name = f"Preventivo_{next_id}_{cliente.replace(' ', '_')}.pdf"
                        
                        if save_data_gsheet(data_form):
                            st.success(f"✅ Preventivo N. {next_id} Salvato!")
                            st.download_button("⬇️ Scarica PDF", pdf_bytes, file_name, 'application/pdf')
                except Exception as e:
                    st.error(f"Errore: {e}")

    # === SCHEDA RICERCA E RISTAMPA ===
    with tab2:
        st.subheader("🔍 Archivio e Ristampa")
        df = load_data_from_gsheet()
        
        if not df.empty:
            # Filtri
            c_fil1, c_fil2 = st.columns(2)
            with c_fil1: 
                search_text = st.text_input("Cerca (Cliente o ID)", placeholder="Es. Rossi...")
            with c_fil2:
                user_filter = st.selectbox("Filtra Commerciale", ["Tutti"] + USERS_LIST[1:])

            # Applicazione Filtri
            df_filt = df.copy()
            if search_text:
                mask = df_filt.astype(str).apply(lambda x: x.str.contains(search_text, case=False)).any(axis=1)
                df_filt = df_filt[mask]
            
            if user_filter != "Tutti":
                df_filt = df_filt[df_filt['Venditrice'].astype(str) == user_filter]

            # Selezione Preventivo per Dettaglio
            if not df_filt.empty:
                st.write(f"Trovati: {len(df_filt)}")
                
                # Creiamo una lista per la selectbox
                options = df_filt.apply(lambda x: f"ID: {x['ID_Preventivo']} - {x['Cliente']} ({x['Data']})", axis=1)
                selected_option = st.selectbox("Seleziona preventivo da visualizzare:", options)
                
                # Estraiamo l'ID selezionato
                selected_id = int(selected_option.split(" - ")[0].replace("ID: ", ""))
                
                # Recuperiamo la riga completa
                row = df[df['ID_Preventivo'] == selected_id].iloc[0]
                
                st.markdown("---")
                # Mostra Dettagli in JSON espandibile
                with st.expander("📋 Vedi Dettagli Completi", expanded=True):
                    st.write(row.to_dict())

                # Tasto Ristampa
                if st.button("🖨️ RIGENERA PDF"):
                    try:
                        # Ricostruiamo il dizionario dati per il PDF
                        # Dobbiamo convertire i prezzi da stringa (es "1.000,00") a float
                        p1 = float(str(row['Prezzo Tot']).replace('.', '').replace(',', '.'))
                        p2 = float(str(row['Prezzo Biennale']).replace('.', '').replace(',', '.')) if row['Prezzo Biennale'] else 0.0
                        
                        data_reprint = {
                            'preventivo_id': row['ID_Preventivo'],
                            'user_name': row['Venditrice'],
                            'cliente': row['Cliente'],
                            'email': row['Email'],
                            'prezzo_1': p1,
                            'prezzo_2': p2,
                            'zone': str(row['Zone']).split(", "), # Riconvertiamo stringa in lista
                            'tipologia': row['Tipologia'],
                            'esiti': row['Esiti'],
                            'analisibando_qty': int(row['Analisi Qty']),
                            'pagamento': row['Pagamento'],
                            'scadenza_rate': row['Scadenza Rate'],
                            'validita': int(row['Validita']),
                            'note': row['Note']
                        }
                        
                        pdf_bytes_re = create_pdf(data_reprint)
                        file_name_re = f"Ristampa_Prev_{row['ID_Preventivo']}_{row['Cliente']}.pdf"
                        
                        st.download_button("⬇️ Scarica PDF Rigenerato", pdf_bytes_re, file_name_re, 'application/pdf')
                        
                    except Exception as e:
                        st.error(f"Errore rigenerazione: {e}. Verifica che i dati nel foglio siano corretti.")

            else:
                st.warning("Nessun preventivo corrisponde alla ricerca.")
        else:
            st.info("Database vuoto.")

if __name__ == "__main__":
    main()









