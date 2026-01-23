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
st.set_page_config(page_title="Study OS Smart Oracle", page_icon="🦉", layout="wide")
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

# --- 2. KAHİN İÇİN AKILLI MODEL SEÇİCİ (YENİ) ---
if "GEMINI_API_KEY" in st.secrets:
    try:
        genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except: pass

@st.cache_resource
def get_best_model():
    """Google'a sorar: Elinde ne var? En iyisini seçer."""
    try:
        # Mevcut modelleri listele
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                available_models.append(m.name)
        
        # Öncelik sırasına göre kontrol et
        # 1. Flash (Hızlı ve Yeni)
        for m in available_models:
            if 'flash' in m and '1.5' in m: return m
        
        # 2. Pro (Güçlü)
        for m in available_models:
            if 'pro' in m and '1.5' in m: return m
            
        # 3. Eski Pro (Yedek)
        for m in available_models:
            if 'gemini-pro' in m: return m
            
        return "models/gemini-pro" # Hiçbir şey bulamazsa varsayılan
    except Exception as e:
        return None

# --- 3. VERİTABANI BAĞLANTISI ---
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
        try: chat_sheet = sheet.get_worksheet(1)
        except: chat_sheet = sheet.add_worksheet(title="OwlPost", rows=1000, cols=3)
        return users_sheet, chat_sheet
    except: return None, None

@st.cache_data(ttl=300) 
def get_cached_leaderboard():
    users_sheet, _ = get_db()
    if users_sheet:
        try: return users_sheet.get_all_records()
        except: return []
    return []

def login_or_register(username):
    users_sheet, _ = get_db()
    if not users_sheet: return None
    try:
        if not users_sheet.row_values(1):
            users_sheet.append_row(["Username", "XP", "Level", "History", "Tasks", "Cards", "Last_Login", "Inventory", "Active_Buffs", "Last_Oracle"])
    except: pass
    try: all_records = users_sheet.get_all_records()
    except: return None
    
    clean_username = username.strip().lower()
    for row in all_records:
        if str(row['Username']).strip().lower() == clean_username:
            for key in ['History', 'Tasks', 'Cards', 'Inventory', 'Active_Buffs']:
                if key not in row: row[key] = []
                elif isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            if 'Last_Oracle' not in row: row['Last_Oracle'] = ""
            return row
            
    new_user = {"Username": username.strip(), "XP": 0, "Level": 1, "History": [], "Tasks": [], "Cards": [], "Last_Login": str(datetime.date.today()), "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
    save_user = new_user.copy()
    for key in ['History', 'Tasks', 'Cards', 'Inventory', 'Active_Buffs']: save_user[key] = json.dumps(save_user[key])
    try: users_sheet.append_row(list(save_user.values()))
    except: pass
    return new_user

def sync_user_to_cloud(user_data):
    users_sheet, _ = get_db()
    if not users_sheet: return
    try:
        cell = users_sheet.find(user_data['Username'])
        r = cell.row
        users_sheet.update_cell(r, 2, user_data['XP'])
        users_sheet.update_cell(r, 4, json.dumps(user_data['History']))
        users_sheet.update_cell(r, 8, json.dumps(user_data['Inventory']))
        users_sheet.update_cell(r, 9, json.dumps(user_data['Active_Buffs']))
        users_sheet.update_cell(r, 10, str(user_data['Last_Oracle']))
        get_cached_leaderboard.clear()
    except: pass

def ask_oracle_dynamic(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Yok."
    
    model_name = get_best_model() # Dinamik Seçim
    if not model_name: return "⚠️ Model listesi alınamadı."
    
    try:
        model = genai.GenerativeModel(model_name)
        return model.generate_content(f"Sen bilge bir kahinsin. Soru: {prompt}").text
    except Exception as e: return f"Hata ({model_name}): {e}"

def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    if stats.empty: return None
    fig = go.Figure(data=go.Scatterpolar(r=stats['duration'], theta=stats['course'], fill='toself', line_color='#d4af37'))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, showticklabels=False)), paper_bgcolor='rgba(0,0,0,0)', font=dict(color='#d4af37'))
    return fig

def send_chat(u, m):
    _, c = get_db()
    if c: 
        try: c.append_row([datetime.datetime.now().strftime("%H:%M"), u, m])
        except: pass
def get_chat():
    _, c = get_db()
    if c:
        try: return c.get_all_values()[-20:]
        except: return []
    return []

# --- APP ---
if 'username' not in st.session_state:
    st.markdown("<br><br><h1 style='text-align: center;'>🦉 Study OS <span style='font-size:20px'>Smart Oracle</span></h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Giriş"):
            with st.spinner("Kontrol ediliyor..."):
                u = login_or_register(name)
                if u:
                    st.session_state.username = u['Username']
                    st.session_state.user_data = u
                    st.rerun()
                else: st.warning("Sunucu yoğun (429). Biraz bekle.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

username = st.session_state.username
data = st.session_state.user_data
if 'Inventory' not in data: data['Inventory'] = []
if 'Active_Buffs' not in data: data['Active_Buffs'] = []

with st.sidebar:
    st.title(f"🦉 {username}")
    st.write(f"**XP:** {data['XP']}")
    st.markdown("---")
    snd = st.selectbox("Ses:", ["Sessiz", "Yağmur", "Şömine", "Lofi"])
    if snd=="Yağmur": st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif snd=="Şömine": st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")

st.title("Study OS")
t1, t2, t3, t4 = st.tabs(["🍄 Odaklan", "🔮 Kahin", "🎒 Dükkan", "📜 Geçmiş"])

with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        topic = st.text_input("Konu:")
        if st.button("🔥 25 Dk Başlat") and topic:
            data['XP'] += 50
            data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": 25, "xp": 50})
            sync_user_to_cloud(data)
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
            res = ask_oracle_dynamic(q)
            st.write(f"**Cevap:** {res}")
    st.markdown('</div>', unsafe_allow_html=True)

with t3:
    st.write("Dükkan yakında...")
with t4:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
