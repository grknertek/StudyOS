import streamlit as st
import pandas as pd
import datetime
import time
import json
import random
import plotly.express as px
import plotly.graph_objects as go
import google.generativeai as genai
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError

# --- 1. AYARLAR ---
st.set_page_config(page_title="Study OS Hybrid", page_icon="🦉", layout="wide")
import warnings
warnings.filterwarnings("ignore")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    .stApp { background-color: #050505; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; color: #d4af37; }
    .glass-card { background: rgba(25, 20, 15, 0.8); border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 20px; padding: 25px; margin-bottom: 25px; }
    .stTextInput input { background-color: rgba(0,0,0,0.5) !important; color: #d4af37 !important; border: 1px solid #554433 !important; }
    .stButton>button { background: linear-gradient(145deg, #3e3226, #1a1510); color: #d4af37; border: 1px solid #d4af37; }
    </style>
""", unsafe_allow_html=True)

# --- 2. KAHİN: AKILLI MODEL SEÇİCİ (Senin İstediğin Özellik) ---
if "GEMINI_API_KEY" in st.secrets:
    try: genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except: pass

@st.cache_resource
def get_best_model():
    """Google'daki mevcut modelleri listeler ve en iyisini seçer."""
    try:
        available_models = []
        # Listeyi çek
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # 1. Öncelik: Flash (Hızlı)
        for m in available_models:
            if 'flash' in m and '1.5' in m: return m
        # 2. Öncelik: Pro (Güçlü)
        for m in available_models:
            if 'pro' in m and '1.5' in m: return m
        # 3. Öncelik: Standart Pro
        for m in available_models:
            if 'gemini-pro' in m: return m
            
        return "models/gemini-pro" # Hiçbiri yoksa varsayılan
    except:
        return "models/gemini-1.5-flash" # Liste çekilemezse tahmin et

def ask_oracle_smart(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Yok."
    
    model_name = get_best_model() # Dinamik Seçim
    try:
        model = genai.GenerativeModel(model_name)
        return model.generate_content(f"Sen bilge bir kahinsin. Soru: {prompt}").text
    except Exception as e: 
        return f"Hata ({model_name}): {e}"

# --- 3. VERİTABANI (HATA VARSA OFFLINE MODA GEÇER) ---
@st.cache_resource
def get_google_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(dict(st.secrets["gcp_service_account"]), scope)
    return gspread.authorize(creds)

def get_db():
    try:
        client = get_google_sheet_client()
        sheet = client.open("StudyOS_DB")
        try: users_sheet = sheet.get_worksheet(0)
        except: users_sheet = sheet.add_worksheet(title="Users", rows=100, cols=10)
        return users_sheet
    except: 
        return None # Hata verirse sessizce None dön (Offline Modu Tetikler)

def login_or_register(username):
    users_sheet = get_db()
    
    # EĞER SUNUCU DOLUYSA (429) -> OFFLINE MODA GEÇ
    if not users_sheet:
        st.toast("⚠️ Sunucu Yoğun: Çevrimdışı Moddasın (Veriler Kaydedilmez)")
        return {"Username": username, "XP": 100, "History": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
    
    # EĞER SUNUCU AÇIKSA -> NORMAL GİRİŞ
    try:
        all_records = users_sheet.get_all_records()
        clean_username = username.strip().lower()
        for row in all_records:
            if str(row['Username']).strip().lower() == clean_username:
                for key in ['History', 'Inventory', 'Active_Buffs']:
                    if isinstance(row.get(key), str):
                        try: row[key] = json.loads(row[key])
                        except: row[key] = []
                return row
        
        # Yeni Kullanıcı
        new_user = {"Username": username, "XP": 0, "Level": 1, "History": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
        save_user = new_user.copy()
        for k in ['History', 'Inventory', 'Active_Buffs']: save_user[k] = json.dumps(save_user[k])
        users_sheet.append_row(list(save_user.values()))
        return new_user
    except:
        # Okurken hata olursa da Offline'a düş
        return {"Username": username, "XP": 100, "History": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}

def sync_user(user_data):
    sheet = get_db()
    if not sheet: return # Offline isek kaydetme
    try:
        cell = sheet.find(user_data['Username'])
        sheet.update_cell(cell.row, 2, user_data['XP'])
        sheet.update_cell(cell.row, 4, json.dumps(user_data['History']))
    except: pass

def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    fig = go.Figure(data=go.Scatterpolar(r=stats['duration'], theta=stats['course'], fill='toself', line_color='#d4af37'))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, showticklabels=False)), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#d4af37'))
    return fig

# --- APP ---
if 'username' not in st.session_state:
    st.markdown("<br><br><h1 style='text-align: center;'>🦉 Study OS <span style='font-size:20px'>Hybrid</span></h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Giriş"):
            u = login_or_register(name)
            st.session_state.username = u['Username']
            st.session_state.user_data = u
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

username = st.session_state.username
data = st.session_state.user_data
if 'Inventory' not in data: data['Inventory'] = []

with st.sidebar:
    st.title(f"🦉 {username}")
    st.write(f"**XP:** {data['XP']}")
    st.caption("🟢 Model: " + (get_best_model() if "GEMINI_API_KEY" in st.secrets else "Yok"))

st.title("Study OS")
t1, t2, t3 = st.tabs(["🍄 Odaklan", "🔮 Kahin", "📜 Geçmiş"])

with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        topic = st.text_input("Konu:")
        if st.button("🔥 25 Dk Başlat") and topic:
            data['XP'] += 50
            data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": 25})
            sync_user(data)
            st.success("Bitti! +50 XP"); time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)

with t2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    q = st.text_input("Kahin'e Sor:")
    if st.button("Danış"):
        with st.spinner("Kahin modelleri tarıyor..."):
            res = ask_oracle_smart(q)
            st.write(res)
    st.markdown('</div>', unsafe_allow_html=True)

with t3:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
