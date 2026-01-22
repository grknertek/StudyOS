import streamlit as st
import os
import subprocess
import sys
import time
import datetime
import json
import random
import pandas as pd

# --- 0. OTOMATİK YÜKLEYİCİ (GARANTİ) ---
def install_and_import(package):
    try:
        __import__(package)
    except ImportError:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        except: pass

# Kritik kütüphaneleri kontrol et
try:
    import plotly.express as px
    import plotly.graph_objects as go
except ImportError:
    install_and_import("plotly")
    import plotly.express as px
    import plotly.graph_objects as go

try:
    import google.generativeai as genai
except ImportError:
    install_and_import("google-generativeai")
    import google.generativeai as genai

import gspread
from oauth2client.service_account import ServiceAccountCredentials
from gspread.exceptions import APIError

# --- 1. AYARLAR ---
st.set_page_config(page_title="Study OS God Mode", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .stApp { background-color: #050505; background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 80%); color: #e0e0e0; font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Playfair Display', serif; color: #d4af37; letter-spacing: 1px; }
    .glass-card { background: rgba(25, 20, 15, 0.8); backdrop-filter: blur(20px); border: 1px solid rgba(212, 175, 55, 0.2); border-radius: 20px; padding: 25px; margin-bottom: 25px; box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7); }
    .painting-frame { width: 160px; height: 200px; object-fit: cover; border: 6px solid #4a3c31; border-radius: 4px; box-shadow: inset 0 0 20px rgba(0,0,0,0.9), 0 0 15px #d4af37; margin: 0 auto 15px auto; display: block; filter: contrast(1.1) sepia(0.3); }
    .painting-frame-gold { border-color: #d4af37 !important; box-shadow: 0 0 30px #d4af37, inset 0 0 20px #000 !important; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div { background-color: rgba(0, 0, 0, 0.5) !important; color: #d4af37 !important; border: 1px solid #554433 !important; }
    .stButton>button { background: linear-gradient(145deg, #3e3226, #1a1510); color: #d4af37; border: 1px solid #d4af37; font-family: 'Playfair Display', serif; }
    </style>
""", unsafe_allow_html=True)

# --- 2. BACKEND & API ---

if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])

RANKS = {0: "Mürekkep Çırağı 🖋️", 500: "Kütüphane Muhafızı 🗝️", 1500: "Hakikat Arayıcısı 🕯️", 3000: "Bilgelik Mimarı 🏛️", 5000: "Entelektüel Lord 👑"}

def get_rank(xp):
    current_rank = "Mürekkep Çırağı 🖋️"
    for limit in sorted(RANKS.keys()):
        if xp >= limit: current_rank = RANKS[limit]
    return current_rank

@st.cache_resource
def get_google_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# Geliştirilmiş Bağlantı Fonksiyonu (Exponential Backoff)
def get_db():
    retries = [2, 5, 10] # Bekleme süreleri: 2sn, 5sn, 10sn
    for wait_time in retries:
        try:
            client = get_google_sheet_client()
            sheet = client.open("StudyOS_DB")
            try: users_sheet = sheet.get_worksheet(0)
            except: users_sheet = sheet.add_worksheet(title="Users", rows=100, cols=10)
            try: chat_sheet = sheet.get_worksheet(1)
            except: chat_sheet = sheet.add_worksheet(title="OwlPost", rows=1000, cols=3)
            return users_sheet, chat_sheet
        except APIError as e:
            if e.response.status_code == 429:
                time.sleep(wait_time) # Kademeli bekle
                continue
            return None, None
        except:
            time.sleep(1)
    return None, None

@st.cache_data(ttl=60)
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
        # Sütun başlıklarını kontrol et
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
            
    new_user = {
        "Username": username.strip(), "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today()), 
        "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""
    }
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
        # Sıralı güncelleme (daha güvenli)
        users_sheet.update_cell(r, 2, user_data['XP'])
        users_sheet.update_cell(r, 4, json.dumps(user_data['History']))
        users_sheet.update_cell(r, 8, json.dumps(user_data['Inventory']))
        users_sheet.update_cell(r, 9, json.dumps(user_data['Active_Buffs']))
        users_sheet.update_cell(r, 10, str(user_data['Last_Oracle']))
        get_cached_leaderboard.clear()
    except: pass

def ask_oracle(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Eksik."
    try:
        model = genai.GenerativeModel('gemini-1.5-flash')
        return model.generate_content(f"Sen bilge bir kahinsin. Kısa ve gizemli cevap ver. Soru: {prompt}").text
    except Exception as e: return f"Bağlantı hatası: {e}"

def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    if stats.empty: return None
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
            with st.spinner("Parşömenler taranıyor..."):
                user_data = login_or_register(name)
                if user_data:
                    st.session_state.username = user_data['Username']
                    st.session_state.user_data = user_data
                    st.rerun()
                else:
                    st.warning("⏳ Sunucu çok yoğun (429). Lütfen 30 saniye bekleyip tekrar dene.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- ANA UYGULAMA ---
username = st.session_state.username
data = st.session_state.user_data
current_rank = get_rank(data['XP'])
if 'Inventory' not in data: data['Inventory'] = []
if 'Active_Buffs' not in data: data['Active_Buffs'] = []

gold_frame_class = "painting-frame-gold" if "Altın Çerçeve" in data['Inventory'] else ""
mushroom_badge = "🍄" if "Mantar Rozeti" in data['Inventory'] else ""

if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'oracle_response' not in st.session_state: st.session_state.oracle_response = ""

with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;">
        <img src="https://images.unsplash.com/photo-1543549790-8b5f4a028cfb?q=80&w=400" class="painting-frame {gold_frame_class}">
        <h2 style="margin:0;">{username} {mushroom_badge}</h2>
        <p style="color:#d4af37;">{current_rank}</p>
        <div style="border:1px solid #d4af37; border-radius:15px; padding:5px; margin-top:5px;">{data['XP']} XP</div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown("---")
    st.subheader("🎧 Atmosfer")
    snd = st.selectbox("Ses:", ["Sessiz 🔇", "Yağmurlu 🌧️", "Şömine 🔥", "Lofi ☕", "Brown Noise 🧠"])
    if "Yağmurlu" in snd: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in snd: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    if data['Active_Buffs']:
        st.markdown("---")
        for buff in data['Active_Buffs']: st.markdown(f"🧪 **{buff['name']}** (x{buff['multiplier']})")

st.title("Study OS")
tab1, tab2, tab3, tab4, tab5 = st.tabs(["🍄 Odaklan", "🔮 Kahin", "🎒 Dükkan", "🃏 Kader", "📜 Geçmiş"])

with tab1:
    c1, c2 = st.columns([2, 1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        mode = st.radio("Mod:", ["🍄 Mantar", "⏱️ Klasik"], horizontal=True, disabled=st.session_state.is_running)
        if "Mantar" in mode:
            dur = st.selectbox("Süre:", ["25 dk", "50 dk", "90 dk"], disabled=st.session_state.is_running)
            pomo_min = int(dur.split(" ")[0])
        topic = st.text_input("Konu:", placeholder="Matematik, Tarih...")
        
        if not st.session_state.is_running:
            if st.button("BAŞLAT"):
                if topic:
                    st.session_state.is_running = True
                    st.session_state.start_time = time.time()
                    st.session_state.focus_mode = mode
                    if "Mantar" in mode: st.session_state.pomo_duration = pomo_min
                    st.rerun()
                else: st.warning("Konu gir.")
        else:
            elapsed = int(time.time() - st.session_state.start_time)
            multiplier = 1.0
            if data['Active_Buffs']: multiplier = max([b['multiplier'] for b in data['Active_Buffs']])
            
            if "Mantar" in st.session_state.focus_mode:
                rem = (st.session_state.pomo_duration * 60) - elapsed
                if rem <= 0:
                    st.balloons(); st.session_state.is_running = False
                    final_xp = int((st.session_state.pomo_duration * 2) * multiplier)
                    data['XP'] += final_xp
                    data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": st.session_state.pomo_duration, "xp": final_xp})
                    data['Active_Buffs'] = []
                    sync_user_to_cloud(data)
                    st.success(f"Bitti! +{final_xp} XP"); st.rerun()
                mins, secs = divmod(rem, 60); color="#ff4b4b"
            else:
                mins, secs = divmod(elapsed, 60); color="#d4af37"
            
            st.markdown(f"<h1 style='text-align:center; font-size: 80px; color:{color};'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            if multiplier > 1.0: st.caption(f"⚡ İksir Aktif: x{multiplier}")
            if st.button("DURDUR"):
                st.session_state.is_running = False
                st.rerun()
            time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### 🕸️ Yetenek Ağı")
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)
        else: st.info("Grafik için veri bekleniyor...")

with tab2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🔮 Kahin'in Gözü")
    q = st.text_input("Sorunu sor:", key="oracle_input")
    if st.button("Danış"):
        with st.spinner("Kahin düşünüyor..."):
            st.session_state.oracle_response = ask_oracle(q)
    if st.session_state.oracle_response: st.markdown(f"**🦉 Kahin:** {st.session_state.oracle_response}")
    st.markdown('</div>', unsafe_allow_html=True)

with tab3:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🧪 Odak İksiri (x1.5 XP)"); st.caption("Fiyat: 200 XP")
        if st.button("Satın Al (200 XP)"):
            if data['XP'] >= 200:
                data['XP'] -= 200
                data['Active_Buffs'] = [{"name": "Odak İksiri", "multiplier": 1.5}]
                sync_user_to_cloud(data); st.toast("Gluk gluk... 🧪"); time.sleep(1); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_s2:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Altın Çerçeve"); st.caption("Fiyat: 500 XP")
        if "Altın Çerçeve" in data['Inventory']: st.success("Sahipsin")
        elif st.button("Al (500 XP)"):
            if data['XP'] >= 500:
                data['XP'] -= 500; data['Inventory'].append("Altın Çerçeve")
                sync_user_to_cloud(data); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

with tab4:
    st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
    st.subheader("🃏 Günün Kader Kartı")
    today = str(datetime.date.today())
    if data.get('Last_Oracle', "") != today:
        if st.button("Kart Çek"):
            c = random.choice([{"name":"Büyücü","desc":"(+50 XP)","xp":50}, {"name":"Ermiş","desc":"(+30 XP)","xp":30}, {"name":"Güç","desc":"(+100 XP)","xp":100}])
            st.session_state.card = c
            data['XP'] += c['xp']; data['Last_Oracle'] = today
            sync_user_to_cloud(data); st.rerun()
    else: st.info("Yarın gel.")
    if 'card' in st.session_state:
        st.markdown(f"<h2>{st.session_state.card['name']}</h2><p>{st.session_state.card['desc']}</p>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab5:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else: st.info("Kayıt yok.")
