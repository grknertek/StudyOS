import streamlit as st
import pandas as pd
import datetime
import time
import json
import random
import gspread
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError

# --- 1. AYARLAR ---
st.set_page_config(page_title="Study OS God Mode", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; color: #d4af37; }
    .glass-card { background: rgba(25, 20, 15, 0.8); border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 20px; padding: 25px; margin-bottom: 25px; }
    .stButton>button { background: linear-gradient(145deg, #3e3226, #1a1510); color: #d4af37; border: 1px solid #d4af37; }
    </style>
""", unsafe_allow_html=True)

# --- 2. BACKEND (AKILLI BAĞLANTI) ---

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

@st.cache_resource
def get_google_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# YENİ: Hata Yakalayan ve Tekrar Deneyen Bağlantı Fonksiyonu
def get_db():
    max_retries = 3
    for attempt in range(max_retries):
        try:
            client = get_google_sheet_client()
            sheet = client.open("StudyOS_DB")
            try: users_sheet = sheet.get_worksheet(0)
            except: users_sheet = sheet.add_worksheet(title="Users", rows=100, cols=10)
            try: chat_sheet = sheet.get_worksheet(1)
            except: chat_sheet = sheet.add_worksheet(title="OwlPost", rows=1000, cols=3)
            return users_sheet, chat_sheet
        except APIError as e:
            if e.response.status_code == 429: # Kota doldu hatası
                time.sleep(2) # 2 saniye bekle ve tekrar dene
                continue
            else:
                st.error(f"Google API Hatası: {e}")
                return None, None
        except Exception as e:
            # Eğer son deneme de başarısızsa hatayı göster
            if attempt == max_retries - 1:
                st.error(f"Bağlantı Hatası (Detay): {e}")
            time.sleep(1)
            
    return None, None

@st.cache_data(ttl=60) # 1 Dakika Önbellek
def get_cached_leaderboard():
    users_sheet, _ = get_db()
    if users_sheet:
        try: return users_sheet.get_all_records()
        except: return []
    return []

def login_or_register(username):
    users_sheet, _ = get_db()
    if not users_sheet: return None
    
    # Veri Çekme (Hata korumalı)
    try: all_records = users_sheet.get_all_records()
    except: return None
    
    clean_username = username.strip().lower()
    
    for row in all_records:
        if str(row['Username']).strip().lower() == clean_username:
            # Veri onarımı
            for key in ['History', 'Tasks', 'Cards', 'Inventory', 'Active_Buffs']:
                if key not in row: row[key] = []
                elif isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            if 'Last_Oracle' not in row: row['Last_Oracle'] = ""
            return row
            
    # Yeni Kullanıcı
    new_user = {
        "Username": username.strip(), "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today()), 
        "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""
    }
    # Kaydetmek için string'e çevir
    save_user = new_user.copy()
    for key in ['History', 'Tasks', 'Cards', 'Inventory', 'Active_Buffs']:
        save_user[key] = json.dumps(save_user[key])
    
    try: users_sheet.append_row(list(save_user.values()))
    except: pass
    return new_user

def sync_user_to_cloud(user_data):
    users_sheet, _ = get_db()
    if not users_sheet: return
    try:
        cell = users_sheet.find(user_data['Username'])
        r = cell.row
        # Tek tek güncellemek yerine toplu güncelleme (Kotayı korur)
        # Ancak gspread'de batch update biraz karmaşıktır, şimdilik kritik olanları güncelleyelim
        users_sheet.update_cell(r, 2, user_data['XP'])
        users_sheet.update_cell(r, 4, json.dumps(user_data['History']))
        users_sheet.update_cell(r, 5, json.dumps(user_data['Tasks']))
        users_sheet.update_cell(r, 8, json.dumps(user_data['Inventory']))
        users_sheet.update_cell(r, 9, json.dumps(user_data['Active_Buffs']))
        users_sheet.update_cell(r, 10, str(user_data['Last_Oracle']))
        get_cached_leaderboard.clear()
    except: pass

# --- KAHİN & GRAFİK ---
def ask_oracle(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Eksik."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(f"Sen bilge bir kahinsin. Kısa cevap ver. Soru: {prompt}").text
    except Exception as e: return f"Hata: {e}"

def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    fig = go.Figure(data=go.Scatterpolar(r=stats['duration'], theta=stats['course'], fill='toself', line_color='#d4af37'))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, showticklabels=False)), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#d4af37'))
    return fig

# --- GİRİŞ EKRANI ---
if 'username' not in st.session_state:
    st.markdown("<br><br><h1 style='text-align: center;'>🦉 Study OS <span style='font-size:20px'>God Mode</span></h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Kapıdan Gir"):
            with st.spinner("Bağlanılıyor... (Lütfen bekleyin)"):
                user_data = login_or_register(name)
                if user_data:
                    st.session_state.username = user_data['Username']
                    st.session_state.user_data = user_data
                    st.rerun()
                else:
                    st.warning("Sunucu yoğunluğu (429). Lütfen 30 saniye bekleyip tekrar deneyin.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- ANA UYGULAMA ---
username = st.session_state.username
data = st.session_state.user_data
if 'Inventory' not in data: data['Inventory'] = []
if 'Active_Buffs' not in data: data['Active_Buffs'] = []

# Sidebar
with st.sidebar:
    st.title(f"🦉 {username}")
    st.write(f"**XP:** {data['XP']}")
    if st.button("Çıkış Yap"):
        del st.session_state['username']
        st.rerun()

# Ana Sayfa
st.title("Study OS")
t1, t2, t3, t4 = st.tabs(["🍄 Odaklan", "🔮 Kahin", "🎒 Dükkan", "📜 Geçmiş"])

with t1:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        if st.button("🔥 25 Dk Başlat"):
            data['XP'] += 50
            data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": "Genel", "duration": 25, "xp": 50})
            sync_user_to_cloud(data)
            st.success("Oturum Bitti! +50 XP")
            time.sleep(1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)

with t2:
    q = st.text_input("Kahin'e Sor:")
    if st.button("Sor"):
        st.write(ask_oracle(q))

with t3:
    st.write("Dükkan yakında...")
    
with t4:
    st.dataframe(pd.DataFrame(data['History']))
