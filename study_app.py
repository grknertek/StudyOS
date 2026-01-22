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

# --- 1. PREMIUM GÖRSEL AYARLAR ---
st.set_page_config(page_title="Study OS God Mode", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 80%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    h1, h2, h3, h4 { font-family: 'Playfair Display', serif; color: #d4af37; letter-spacing: 1px; }
    
    .glass-card {
        background: rgba(25, 20, 15, 0.8);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(212, 175, 55, 0.2);
        border-radius: 20px;
        padding: 25px;
        margin-bottom: 25px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.7);
    }
    .painting-frame {
        width: 160px; height: 200px; object-fit: cover;
        border: 6px solid #4a3c31; border-radius: 4px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9), 0 0 15px #d4af37;
        margin: 0 auto 15px auto; display: block; filter: contrast(1.1) sepia(0.3);
    }
    .painting-frame-gold {
        border-color: #d4af37 !important; box-shadow: 0 0 30px #d4af37, inset 0 0 20px #000 !important;
    }
    .tarot-card {
        border: 2px solid #d4af37; border-radius: 10px; padding: 20px;
        text-align: center; background: linear-gradient(145deg, #2b221a, #000);
        animation: fadeIn 2s;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    .chat-row {
        padding: 10px; margin-bottom: 10px; border-radius: 10px;
        background: rgba(255, 255, 255, 0.05); border-left: 3px solid #d4af37;
    }
    .shop-item {
        border: 1px solid #444; padding: 15px; border-radius: 10px; text-align: center;
        background: rgba(0,0,0,0.3); transition: transform 0.2s;
    }
    .shop-item:hover { transform: scale(1.03); border-color: #d4af37; }
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(0, 0, 0, 0.5) !important;
        color: #d4af37 !important;
        border: 1px solid #554433 !important;
    }
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #1a1510); color: #d4af37; 
        border: 1px solid #d4af37; font-family: 'Playfair Display', serif;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BACKEND & API AYARLARI ---

# Gemini API Yapılandırma (YENİ MODEL: 1.5 Flash)
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    # Hata vermesin diye sessizce geçiyoruz, fonksiyonda uyaracağız
    pass

RANKS = {
    0: "Mürekkep Çırağı 🖋️", 500: "Kütüphane Muhafızı 🗝️",
    1500: "Hakikat Arayıcısı 🕯️", 3000: "Bilgelik Mimarı 🏛️", 5000: "Entelektüel Lord 👑"
}

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
        row_num = cell.row
        
        users_sheet.update_cell(row_num, 2, user_data['XP'])
        users_sheet.update_cell(row_num, 4, json.dumps(user_data['History']))
        users_sheet.update_cell(row_num, 5, json.dumps(user_data['Tasks']))
        users_sheet.update_cell(row_num, 6, json.dumps(user_data['Cards']))
        users_sheet.update_cell(row_num, 7, str(datetime.date.today()))
        users_sheet.update_cell(row_num, 8, json.dumps(user_data['Inventory']))
        users_sheet.update_cell(row_num, 9, json.dumps(user_data['Active_Buffs']))
        users_sheet.update_cell(row_num, 10, str(user_data['Last_Oracle']))
        
        get_cached_leaderboard.clear()
    except: pass

# --- ÖZELLİK 1: KAHİN (GEMINI 1.5 FLASH) ---
def ask_oracle(prompt):
    if "GEMINI_API_KEY" not in st.secrets:
        return "⚠️ Hata: API Anahtarı eksik. Lütfen Secrets ayarlarını kontrol et."
    
    try:
        # GÜNCEL MODEL: gemini-1.5-flash (Daha hızlı ve ücretsiz kota dostu)
        model = genai.GenerativeModel('gemini-1.5-flash')
        system_instruction = "Sen 'Study OS' adlı mistik bir kütüphanenin kadim koruyucususun. Adın 'Kahin'. Dark Academia estetiğiyle, bilgece, metaforlu ve hafif gizemli konuşursun. Kullanıcı bir öğrenci. Cevapların kısa, öz ama derin olsun."
        response = model.generate_content(f"{system_instruction}\n\nSoru: {prompt}")
        return response.text
    except Exception as e:
        return f"⚠️ Kahin Bağlantı Hatası: {e}"

# --- ÖZELLİK 4: ÖRÜMCEK AĞI ---
def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    
    stats = df.groupby('course')['duration'].sum().reset_index()
    if stats.empty: return None

    fig = go.Figure(data=go.Scatterpolar(
      r=stats['duration'],
      theta=stats['course'],
      fill='toself',
      line_color='#d4af37',
      fillcolor='rgba(212, 175, 55, 0.2)'
    ))
    fig.update_layout(
      polar=dict(
        radialaxis=dict(visible=True, showticklabels=False, linecolor='#444'),
        bgcolor='rgba(0,0,0,0)'
      ),
      paper_bgcolor='rgba(0,0,0,0)',
      plot_bgcolor='rgba(0,0,0,0)',
      font=dict(color='#d4af37', family="Playfair Display"),
      showlegend=False,
      margin=dict(l=40, r=40, t=20, b=20)
    )
    return fig

# --- CHAT ---
def send_chat_message(username, message):
    _, chat_sheet = get_db()
    if chat_sheet:
        try: chat_sheet.append_row([datetime.datetime.now().strftime("%H:%M"), username, message])
        except: pass

def get_chat_messages():
    _, chat_sheet = get_db()
    if chat_sheet:
        try: 
            all_rows = chat_sheet.get_all_values()
            return all_rows[-20:] if len(all_rows) > 1 else []
        except: return []
    return []

# --- GİRİŞ ---
if 'username' not in st.session_state:
    st.markdown("<br><br><h1 style='text-align: center;'>🦉 Study OS <span style='font-size:20px'>God Mode</span></h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            name_input = st.text_input("Kod Adın:", placeholder="Gezgin...")
            if st.form_submit_button("Kapıdan Gir"):
                with st.spinner("Ruhun tartılıyor..."):
                    user_data = login_or_register(name_input)
                    if user_data:
                        st.session_state.username = user_data['Username']
                        st.session_state.user_data = user_data
                        st.rerun()
                    else: st.error("Sunucu kapalı (Veritabanı bağlantısı yok).")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- ANA DÖNGÜ ---
username = st.session_state.username
data = st.session_state.user_data
current_rank = get_rank(data['XP'])
if 'Inventory' not in data: data['Inventory'] = []
if 'Active_Buffs' not in data: data['Active_Buffs'] = []

# State init
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'oracle_response' not in st.session_state: st.session_state.oracle_response = ""

# Sidebar
gold_frame_class = "painting-frame-gold" if "Altın Çerçeve" in data['Inventory'] else ""
mushroom_badge = "🍄" if "Mantar Rozeti" in data['Inventory'] else ""

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
    elif "Lofi" in snd: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in snd: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")
    if data['Active_Buffs']:
        st.markdown("---")
        st.caption("✨ Aktif İksirler:")
        for buff in data['Active_Buffs']: st.markdown(f"🧪 **{buff['name']}** (x{buff['multiplier']})")

# Ana Ekran
st.title("Study OS")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🍄 Odaklan", "🔮 Kahin", "🧪 Simya & Dükkan", "🃏 Kader", "🦉 Posta", "📜 Geçmiş"])

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
                if "Klasik" in st.session_state.focus_mode:
                    dm = elapsed // 60
                    if dm >= 1:
                        final_xp = int((dm * 2) * multiplier)
                        data['XP'] += final_xp
                        data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": dm, "xp": final_xp})
                        data['Active_Buffs'] = []
                        sync_user_to_cloud(data)
                        st.success(f"Kaydedildi: +{final_xp} XP")
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
    st.subheader("🔮 Kahin'in Gözü (AI)")
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
        st.markdown(f"<div class='tarot-card'><h2>{st.session_state.card['name']}</h2><p>{st.session_state.card['desc']}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with tab5:
    with st.form("chat"):
        c1, c2 = st.columns([4,1])
        m = c1.text_input("Mesaj:", label_visibility="collapsed")
        if c2.form_submit_button("Yolla") and m: send_chat_message(username, m); st.rerun()
    for msg in reversed(get_chat_messages()):
        if len(msg)>=3 and msg[1]!="Username":
            col = "#d4af37" if msg[1]==username else "#ccc"
            st.markdown(f"<div class='chat-row'><b style='color:{col}'>{msg[1]}</b> <i style='float:right;size:10px'>{msg[0]}</i><br>{msg[2]}</div>", unsafe_allow_html=True)
    if st.button("Yenile"): st.rerun()

with tab6:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else: st.info("Kayıt yok.")
