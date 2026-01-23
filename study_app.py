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

# --- 1. AYARLAR & TASARIM (DARK ACADEMIA) ---
st.set_page_config(page_title="Study OS Golden Age", page_icon="🦉", layout="wide")

# Tasarım Kodları (CSS)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* GENEL ARKA PLAN */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 80%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* BAŞLIKLAR (Playfair Fontu) */
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif;
        color: #d4af37; /* Altın */
        letter-spacing: 1px;
        text-shadow: 0 4px 10px rgba(0,0,0,0.8);
    }
    
    /* CAM KARTLAR (GLASSMORPHISM) */
    .glass-card {
        background: rgba(25, 20, 15, 0.75);
        backdrop-filter: blur(16px);
        -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(212, 175, 55, 0.25);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
        transition: transform 0.3s ease;
    }
    .glass-card:hover {
        border-color: rgba(212, 175, 55, 0.5);
    }
    
    /* TABLO GİBİ PROFİL RESMİ */
    .painting-frame {
        width: 160px; height: 200px; object-fit: cover;
        border: 8px solid #4a3c31; 
        border-radius: 4px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9), 0 10px 30px rgba(0,0,0,0.8), 0 0 0 2px #d4af37;
        margin: 0 auto 15px auto; display: block; 
        filter: contrast(1.1) sepia(0.3);
    }
    
    /* INPUT ALANLARI */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(0, 0, 0, 0.5) !important;
        color: #d4af37 !important;
        border: 1px solid #554433 !important;
        border-radius: 10px;
    }
    
    /* BUTONLAR (Altın Efektli) */
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #1a1510);
        color: #d4af37;
        border: 1px solid #d4af37;
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        padding: 10px 24px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        background: #d4af37;
        color: #000;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.6);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. KAHİN: GEMINI 2.5 FLASH ---
if "GEMINI_API_KEY" in st.secrets:
    try: genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except: pass

@st.cache_resource
def get_model_name():
    # Öncelikli olarak senin bulduğun 2.5 modelini deniyoruz
    target_model = "models/gemini-2.5-flash"
    try:
        # Eğer model listesinde varsa onu döndür
        for m in genai.list_models():
            if 'gemini-2.5-flash' in m.name:
                return m.name
        # Yoksa 1.5 Flash'a düş
        return "models/gemini-1.5-flash"
    except:
        return "models/gemini-pro" # En kötü ihtimalle Pro

def ask_oracle(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Eksik."
    
    model_name = get_model_name()
    try:
        model = genai.GenerativeModel(model_name)
        response = model.generate_content(f"Sen 'Study OS' kütüphanesinin kadim koruyucususun. Kullanıcıya 'Gezgin' diye hitap et. Cevapların kısa, öz, bilgece ve hafif gizemli olsun. Soru: {prompt}")
        return response.text
    except Exception as e:
        return f"Kahin derin uykuda... (Hata: {e})"

# --- 3. VERİTABANI (HYBRID SİSTEM) ---
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
        return None # Hata verirse (429 dahil) sessizce None dön

def login_or_register(username):
    users_sheet = get_db()
    
    # OFFLINE MOD (Sunucu Yoğunsa)
    if not users_sheet:
        st.toast("⚠️ Sunucu Yoğun: Çevrimdışı Moddasın (Kayıt yapılmaz)")
        return {"Username": username, "XP": 100, "History": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
    
    # ONLINE MOD
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
        return {"Username": username, "XP": 100, "History": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}

def sync_user(user_data):
    sheet = get_db()
    if not sheet: return
    try:
        cell = sheet.find(user_data['Username'])
        sheet.update_cell(cell.row, 2, user_data['XP'])
        sheet.update_cell(cell.row, 4, json.dumps(user_data['History']))
    except: pass

# --- GRAFİKLER ---
def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    
    fig = go.Figure(data=go.Scatterpolar(
        r=stats['duration'], theta=stats['course'], fill='toself',
        line_color='#d4af37', fillcolor='rgba(212, 175, 55, 0.3)'
    ))
    fig.update_layout(
        polar=dict(
            bgcolor='rgba(0,0,0,0)',
            radialaxis=dict(visible=True, showticklabels=False, linecolor='#555'),
            angularaxis=dict(linecolor='#555', color='#d4af37')
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        margin=dict(l=20, r=20, t=20, b=20),
        font=dict(family="Playfair Display", size=14, color="#d4af37")
    )
    return fig

# --- UYGULAMA ---
if 'username' not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 3rem;'>🦉 Study OS <span style='font-size:1.5rem; color:#888'>Golden Age</span></h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Kapıdan Gir", use_container_width=True):
            with st.spinner("Ruhun tartılıyor..."):
                u = login_or_register(name)
                st.session_state.username = u['Username']
                st.session_state.user_data = u
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# Giriş Yapıldı
username = st.session_state.username
data = st.session_state.user_data
if 'Inventory' not in data: data['Inventory'] = []

with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;">
        <img src="https://images.unsplash.com/photo-1543549790-8b5f4a028cfb?q=80&w=400" class="painting-frame">
        <h2 style="margin:10px 0 0 0;">{username}</h2>
        <div style="border:1px solid #d4af37; border-radius:20px; padding:5px 15px; margin-top:10px; display:inline-block; background:rgba(212,175,55,0.1);">
            <span style="color:#fff; font-weight:bold;">{data['XP']} XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.caption(f"🧠 Model: {get_model_name().split('/')[-1]}")
    
    st.subheader("🎧 Atmosfer")
    snd = st.selectbox("Ses:", ["Sessiz 🔇", "Yağmurlu Kütüphane 🌧️", "Şömine Ateşi 🔥", "Lofi & Chill ☕", "Brown Noise (Odak) 🧠"])
    if "Yağmur" in snd: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in snd: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    elif "Lofi" in snd: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in snd: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")

# Ana Ekran
t1, t2, t3 = st.tabs(["🔥 Odaklan", "🔮 Kahin", "📜 Geçmiş"])

with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🍄 Odaklanma Ritüeli")
        topic = st.text_input("Çalışma Konusu:")
        
        if st.button("🔥 25 Dakika Başlat", use_container_width=True):
            if topic:
                with st.spinner("Odaklanılıyor..."):
                    time.sleep(2) # Efekt
                    data['XP'] += 50
                    data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": 25})
                    sync_user(data)
                    st.balloons()
                    st.success(f"Oturum Tamamlandı! +50 XP kazandın.")
                    time.sleep(2)
                    st.rerun()
            else:
                st.warning("Lütfen bir konu yaz.")
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
        with st.spinner("Kahin parşömenleri inceliyor..."):
            res = ask_oracle(q)
            st.markdown(f"""
            <div style="background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; border-left:3px solid #d4af37;">
                <b style="color:#d4af37;">🦉 Kahin:</b><br>{res}
            </div>
            """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t3:
    if data['History']:
        st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else:
        st.info("Henüz bir kayıt yok, çırak.")
