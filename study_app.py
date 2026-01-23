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

# --- 1. AYARLAR & TASARIM (AGRESİF STİL) ---
st.set_page_config(page_title="Study OS Renaissance", page_icon="🦉", layout="wide")
import warnings
warnings.filterwarnings("ignore")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* 1. GENEL ARKA PLAN VE FONT */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 90%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* 2. BAŞLIKLAR VE METİNLER */
    h1, h2, h3, h4, .big-font {
        font-family: 'Playfair Display', serif !important;
        color: #d4af37 !important;
        letter-spacing: 1px;
        text-shadow: 0 4px 15px rgba(0,0,0,0.9);
    }
    
    /* 3. CAM KARTLAR (GLASSMORPHISM - GÜÇLENDİRİLMİŞ) */
    .glass-card {
        background: rgba(20, 15, 10, 0.7);
        backdrop-filter: blur(20px);
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    
    /* 4. INPUT ALANLARI (STANDART GRİYİ YOK ETME) */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #d4af37 !important;
        border: 1px solid #4a3c31 !important;
        border-radius: 8px !important;
        font-family: 'Inter', sans-serif !important;
    }
    .stTextInput input:focus {
        border-color: #d4af37 !important;
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.2) !important;
    }
    
    /* 5. BUTONLAR (ALTIN EFEKTİ) */
    .stButton > button {
        background: linear-gradient(145deg, #3e3226, #1a1510) !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        font-family: 'Playfair Display', serif !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: bold;
        transition: all 0.3s ease;
        padding: 0.5rem 1rem;
    }
    .stButton > button:hover {
        background: #d4af37 !important;
        color: #050505 !important;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.6);
        transform: translateY(-2px);
    }
    
    /* 6. TABLO ÇERÇEVESİ (PROFİL) */
    .painting-frame {
        width: 160px; height: 160px; object-fit: cover;
        border: 4px solid #4a3c31;
        outline: 2px solid #d4af37;
        border-radius: 50%; /* Yuvarlak Portre */
        box-shadow: 0 0 30px rgba(0,0,0,0.8), inset 0 0 20px rgba(0,0,0,0.8);
        margin: 0 auto 15px auto; display: block;
        filter: sepia(0.2) contrast(1.1);
    }
    .painting-frame-gold {
        border-color: #d4af37 !important;
        outline: 2px solid #fff !important;
        box-shadow: 0 0 40px #d4af37 !important;
    }
    
    /* 7. TAROT KARTI & DÜKKAN */
    .tarot-card {
        background: linear-gradient(180deg, #1a1510 0%, #000 100%);
        border: 2px solid #d4af37;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 0 25px rgba(212, 175, 55, 0.2);
        animation: fadeIn 1.5s ease-in-out;
    }
    .shop-item {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid #333;
        border-radius: 10px;
        padding: 15px;
        text-align: center;
        transition: transform 0.2s;
    }
    .shop-item:hover {
        border-color: #d4af37;
        transform: scale(1.02);
    }
    
    /* 8. SEKME (TABS) STİLİ */
    button[data-baseweb="tab"] {
        color: #888 !important;
        font-family: 'Playfair Display', serif !important;
    }
    button[data-baseweb="tab"][aria-selected="true"] {
        color: #d4af37 !important;
        background-color: transparent !important;
        border-bottom: 2px solid #d4af37 !important;
    }
    
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
""", unsafe_allow_html=True)

# --- 2. KAHİN: AKILLI MODEL SEÇİCİ ---
if "GEMINI_API_KEY" in st.secrets:
    try: genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except: pass

@st.cache_resource
def get_best_model():
    try:
        available_models = [m.name for m in genai.list_models() if 'generateContent' in m.supported_generation_methods]
        for m in available_models:
            if 'gemini-2.0-flash' in m: return m  # En yeni
        for m in available_models:
            if 'gemini-1.5-flash' in m: return m
        for m in available_models:
            if 'gemini-pro' in m: return m
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-1.5-flash"

def ask_oracle_smart(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Yok."
    model_name = get_best_model()
    try:
        model = genai.GenerativeModel(model_name)
        return model.generate_content(f"Sen 'Study OS' kütüphanesinin kadim koruyucusu bir baykuşsun. Kullanıcıya 'Gezgin' veya 'Çırak' diye hitap et. Cevapların kısa, bilgece, metaforlu ve hafif gizemli olsun. Soru: {prompt}").text
    except Exception as e: return f"Kahin uykuda... ({e})"

# --- 3. VERİTABANI (HYBRID) ---
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
    except: return None

def login_or_register(username):
    users_sheet = get_db()
    if not users_sheet:
        st.toast("⚠️ Çevrimdışı Mod (Veriler Kaydedilmez)")
        return {"Username": username, "XP": 100, "Level": 1, "History": [], "Tasks": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
    try:
        all_records = users_sheet.get_all_records()
        clean_username = username.strip().lower()
        for row in all_records:
            if str(row['Username']).strip().lower() == clean_username:
                for key in ['History', 'Tasks', 'Inventory', 'Active_Buffs']:
                    if isinstance(row.get(key), str):
                        try: row[key] = json.loads(row[key])
                        except: row[key] = []
                    elif key not in row: row[key] = []
                if 'Last_Oracle' not in row: row['Last_Oracle'] = ""
                return row
        new_user = {"Username": username, "XP": 0, "Level": 1, "History": [], "Tasks": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
        save_user = new_user.copy()
        for k in ['History', 'Tasks', 'Inventory', 'Active_Buffs']: save_user[k] = json.dumps(save_user[k])
        users_sheet.append_row(list(save_user.values()))
        return new_user
    except:
        return {"Username": username, "XP": 100, "Level": 1, "History": [], "Tasks": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}

def sync_user(user_data):
    sheet = get_db()
    if not sheet: return
    try:
        cell = sheet.find(user_data['Username'])
        r = cell.row
        sheet.update_cell(r, 2, user_data['XP'])
        sheet.update_cell(r, 4, json.dumps(user_data['History']))
        sheet.update_cell(r, 5, json.dumps(user_data['Tasks']))
        sheet.update_cell(r, 8, json.dumps(user_data['Inventory']))
        sheet.update_cell(r, 9, json.dumps(user_data['Active_Buffs']))
        sheet.update_cell(r, 10, str(user_data['Last_Oracle']))
    except: pass

@st.cache_data(ttl=600)
def get_leaderboard():
    sheet = get_db()
    if sheet:
        try: return sheet.get_all_records()
        except: return []
    return []

def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    fig = go.Figure(data=go.Scatterpolar(r=stats['duration'], theta=stats['course'], fill='toself', line_color='#d4af37', fillcolor='rgba(212, 175, 55, 0.3)'))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, showticklabels=False, linecolor='#555'), angularaxis=dict(linecolor='#555', color='#d4af37')), paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), font=dict(family="Playfair Display", color="#d4af37"))
    return fig

# --- UYGULAMA BAŞLANGICI ---
if 'username' not in st.session_state:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 80px;'>🦉</h1>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>Study OS <span style='font-size:20px; opacity:0.7'>Renaissance</span></h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Kapıdan Gir", use_container_width=True):
            with st.spinner("Parşömenler Taranıyor..."):
                u = login_or_register(name)
                st.session_state.username = u['Username']
                st.session_state.user_data = u
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- ANA EKRAN ---
username = st.session_state.username
data = st.session_state.user_data
# Veri Güvenliği
for k in ['Inventory', 'Active_Buffs', 'Tasks']:
    if k not in data: data[k] = []

with st.sidebar:
    # Profil Kartı
    gold_cls = "painting-frame-gold" if "Altın Çerçeve" in data['Inventory'] else ""
    mushroom = "🍄" if "Mantar Rozeti" in data['Inventory'] else ""
    
    st.markdown(f"""
    <div style="text-align:center; padding-bottom:20px;">
        <img src="https://images.unsplash.com/photo-1519052537078-e6302a4968d4?q=80&w=400" class="painting-frame {gold_cls}">
        <h2 style="margin:10px 0 5px 0;">{username} {mushroom}</h2>
        <div style="background: rgba(212,175,55,0.1); border:1px solid #d4af37; border-radius:20px; padding:5px 15px; display:inline-block;">
            <span style="color:#d4af37; font-weight:bold;">{data['XP']} XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🏆 Liderler")
    ldr = get_leaderboard()
    if ldr:
        sorted_users = sorted(ldr, key=lambda x: x['XP'], reverse=True)[:5]
        for rank, u in enumerate(sorted_users, 1):
            medal = "🥇" if rank==1 else "🥈" if rank==2 else "🥉" if rank==3 else f"#{rank}"
            st.markdown(f"<div style='display:flex; justify-content:space-between; margin-bottom:5px; font-size:14px;'><span style='color:#ccc'>{medal} {u['Username']}</span> <span style='color:#d4af37'>{u['XP']}</span></div>", unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🎧 Atmosfer")
    snd = st.selectbox("Ses:", ["Sessiz", "Yağmur 🌧️", "Şömine 🔥", "Lofi ☕", "Brown Noise 🧠"])
    if "Yağmur" in snd: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in snd: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    elif "Lofi" in snd: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in snd: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")

# Ana İçerik
t1, t2, t3, t4, t5, t6 = st.tabs(["🔥 Odaklan", "🔮 Kahin", "🎒 Dükkan", "🃏 Tarot", "📜 Ajanda", "🕰️ Geçmiş"])

with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🍄 Odaklanma Ritüeli")
        topic = st.text_input("Çalışma Konusu:", placeholder="Matematik, Edebiyat...")
        if st.button("🔥 25 Dakika Başlat", use_container_width=True):
            if topic:
                mult = 1.5 if any(b['name']=="Odak İksiri" for b in data['Active_Buffs']) else 1.0
                xp_gain = int(50 * mult)
                data['XP'] += xp_gain
                data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": 25})
                data['Active_Buffs'] = [] 
                sync_user(data)
                st.balloons()
                st.success(f"Oturum Bitti! +{xp_gain} XP")
                if mult > 1: st.toast("İksir etkisi kullanıldı! 🧪")
                time.sleep(2); st.rerun()
            else: st.warning("Bir konu yazmalısın.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### 🕸️ Yetenek Ağı")
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)
        else: st.info("Veri bekleniyor...")

with t2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🔮 Kahin'in Gözü")
    q = st.text_input("Sorunu sor:", placeholder="Evrenin sırlarını merak ediyorum...")
    if st.button("Danış", use_container_width=True):
        with st.spinner("Kahin küreye bakıyor..."):
            res = ask_oracle_smart(q)
            st.markdown(f"<div style='background:rgba(255,255,255,0.05); padding:20px; border-radius:10px; border-left:4px solid #d4af37;'>{res}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t3:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🧪 Odak İksiri (x1.5 XP)"); st.caption("200 XP")
        if st.button("Satın Al 🧪", use_container_width=True):
            if data['XP'] >= 200:
                data['XP'] -= 200; data['Active_Buffs'] = [{"name": "Odak İksiri", "multiplier": 1.5}]
                sync_user(data); st.toast("İçildi! Sıradaki oturum x1.5 XP"); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Altın Çerçeve"); st.caption("500 XP")
        if "Altın Çerçeve" in data['Inventory']: st.success("Sahipsin")
        elif st.button("Satın Al 🖼️", use_container_width=True):
            if data['XP'] >= 500:
                data['XP'] -= 500; data['Inventory'].append("Altın Çerçeve")
                sync_user(data); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)

with t4:
    st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
    st.subheader("🃏 Günün Kader Kartı")
    today = str(datetime.date.today())
    if data.get('Last_Oracle') != today:
        if st.button("Kart Çek", use_container_width=True):
            c = random.choice([{"name":"Büyücü","desc":"Yaratıcılığın zirvesindesin. (+50 XP)","xp":50}, {"name":"Güç","desc":"İçindeki gücü keşfet. (+100 XP)","xp":100}])
            st.session_state.card = c; data['XP'] += c['xp']; data['Last_Oracle'] = today
            sync_user(data); st.rerun()
    else: st.info("Kaderin bugünlük çizildi. Yarın gel.")
    if 'card' in st.session_state:
        st.markdown(f"<div class='tarot-card'><h2>{st.session_state.card['name']}</h2><p>{st.session_state.card['desc']}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t5:
    c_add, c_list = st.columns([1,2])
    with c_add:
        with st.form("task"):
            t = st.text_input("Görev:")
            if st.form_submit_button("Ekle", use_container_width=True) and t:
                data['Tasks'].append({"task": t, "done": False})
                sync_user(data); st.rerun()
    with c_list:
        if data['Tasks']:
            for i, task in enumerate(data['Tasks']):
                col_t, col_b = st.columns([5,1])
                col_t.markdown(f"📜 {task['task']}")
                if col_b.button("✅", key=f"done_{i}"):
                    data['XP'] += 20; data['Tasks'].pop(i); sync_user(data); st.rerun()
        else: st.caption("Yapılacak görev yok.")

with t6:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
