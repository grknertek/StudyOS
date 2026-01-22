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
    
    /* GÖRSEL EFEKTLER */
    .painting-frame {
        width: 160px; height: 200px; object-fit: cover;
        border: 6px solid #4a3c31; border-radius: 4px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9), 0 0 15px #d4af37;
        margin: 0 auto 15px auto; display: block; filter: contrast(1.1) sepia(0.3);
    }
    .tarot-card {
        border: 2px solid #d4af37; border-radius: 10px; padding: 20px;
        text-align: center; background: linear-gradient(145deg, #2b221a, #000);
        animation: fadeIn 2s;
    }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    
    /* CHAT & GENEL */
    .chat-row {
        padding: 10px; margin-bottom: 10px; border-radius: 10px;
        background: rgba(255, 255, 255, 0.05); border-left: 3px solid #d4af37;
    }
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

# Gemini API Yapılandırma
if "GEMINI_API_KEY" in st.secrets:
    genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
else:
    st.warning("⚠️ Gemini API Key bulunamadı! Kahin çalışmaz.")

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
    
    # Başlık Kontrolü (Yeni Sütunlar: Active_Buffs, Last_Oracle)
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
        users_sheet.update_cell(row_num, 9, json.dumps(user_data['Active_Buffs'])) # İksirler
        users_sheet.update_cell(row_num, 10, str(user_data['Last_Oracle'])) # Tarot
        
        get_cached_leaderboard.clear()
    except: pass

# --- ÖZELLİK 1: KAHİN (AI) ---
def ask_oracle(prompt):
    try:
        model = genai.GenerativeModel('gemini-pro')
        system_instruction = "Sen 'Study OS' adlı mistik bir kütüphanenin kadim koruyucususun. Adın 'Kahin'. Dark Academia estetiğiyle, bilgece, metaforlu ve hafif gizemli konuşursun. Kullanıcı bir öğrenci. Cevapların kısa, öz ama derin olsun."
        response = model.generate_content(f"{system_instruction}\n\nSoru: {prompt}")
        return response.text
    except:
        return "Kahin şu an meditasyonda... (API Hatası)"

# --- ÖZELLİK 4: ÖRÜMCEK AĞI (RADAR CHART) ---
def create_radar_chart(history):
    if not history: return None
    
    df = pd.DataFrame(history)
    if 'course' not in df.columns: return None
    
    # Konulara göre toplam süre
    stats = df.groupby('course')['duration'].sum().reset_index()
    
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

# --- CHAT SİSTEMİ ---
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

# --- 3. GİRİŞ ---
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
                    else: st.error("Sunucu kapalı.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. ANA DÖNGÜ ---
username = st.session_state.username
data = st.session_state.user_data
current_rank = get_rank(data['XP'])

# State init
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'oracle_response' not in st.session_state: st.session_state.oracle_response = ""

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;">
        <img src="https://images.unsplash.com/photo-1543549790-8b5f4a028cfb?q=80&w=400" class="painting-frame">
        <h2 style="margin:0;">{username}</h2>
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
    
    # AKTİF BUFF GÖSTERGESİ
    if data.get('Active_Buffs'):
        st.markdown("---")
        st.caption("✨ Aktif İksirler:")
        for buff in data['Active_Buffs']:
            st.markdown(f"🧪 **{buff['name']}** (x{buff['multiplier']})")

# --- ANA EKRAN ---
st.title("Study OS")
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["🍄 Odaklan", "🔮 Kahin", "🧪 Simya & Dükkan", "🃏 Kader", "🦉 Posta", "📜 Geçmiş"])

# --- TAB 1: ODAKLANMA + ÖRÜMCEK AĞI ---
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
            # İksir Kontrolü
            multiplier = 1.0
            if data.get('Active_Buffs'):
                multiplier = max([b['multiplier'] for b in data['Active_Buffs']])
            
            if "Mantar" in st.session_state.focus_mode:
                rem = (st.session_state.pomo_duration * 60) - elapsed
                if rem <= 0:
                    st.balloons(); st.session_state.is_running = False
                    base_xp = st.session_state.pomo_duration * 2
                    final_xp = int(base_xp * multiplier)
                    
                    data['XP'] += final_xp
                    data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": st.session_state.pomo_duration, "xp": final_xp})
                    
                    # İksiri Tüket
                    data['Active_Buffs'] = []
                    sync_user_to_cloud(data)
                    st.success(f"Bitti! +{final_xp} XP (Çarpan: x{multiplier})")
                    st.rerun()
                mins, secs = divmod(rem, 60); color="#ff4b4b"
            else:
                mins, secs = divmod(elapsed, 60); color="#d4af37"
            
            st.markdown(f"<h1 style='text-align:center; font-size: 80px; color:{color};'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            if multiplier > 1.0: st.caption(f"⚡ İksir Aktif: x{multiplier} XP")
            
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
        # ÖRÜMCEK AĞI (YETENEK ANALİZİ)
        st.markdown("### 🕸️ Yetenek Ağı")
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)
        else: st.info("Veri bekleniyor...")

# --- TAB 2: KAHİN (AI) ---
with tab2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🔮 Kahin'in Gözü")
    st.caption("Kadim kütüphanenin koruyucusuna danış. (Örn: 'Bana Fransız İhtilali'ni özetle')")
    
    oracle_q = st.text_input("Sorunu sor:", key="oracle_input")
    if st.button("Danış"):
        with st.spinner("Kahin küreye bakıyor..."):
            resp = ask_oracle(oracle_q)
            st.session_state.oracle_response = resp
            
    if st.session_state.oracle_response:
        st.markdown(f"**🦉 Kahin:** {st.session_state.oracle_response}")
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: SİMYA & DÜKKAN ---
with tab3:
    col_shop1, col_shop2 = st.columns(2)
    with col_shop1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🧪 Odak İksiri (x1.5 XP)")
        st.caption("Bir sonraki çalışma seansında %50 daha fazla XP kazandırır.")
        st.markdown("**Fiyat: 200 XP**")
        if st.button("Satın Al & İç (200 XP)"):
            if data['XP'] >= 200:
                data['XP'] -= 200
                data['Active_Buffs'] = [{"name": "Odak İksiri", "multiplier": 1.5}]
                sync_user_to_cloud(data)
                st.toast("Gluk gluk... İksir içildi! 🧪")
                time.sleep(1); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)
        
    with col_shop2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Altın Çerçeve")
        st.caption("Profil resmini parlatır. (Kalıcı)")
        st.markdown("**Fiyat: 500 XP**")
        if "Altın Çerçeve" in data['Inventory']: st.success("Sahipsin")
        elif st.button("Al (500 XP)"):
            if data['XP'] >= 500:
                data['XP'] -= 500; data['Inventory'].append("Altın Çerçeve")
                sync_user_to_cloud(data); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 4: KADER KARTLARI ---
with tab4:
    st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
    st.subheader("🃏 Günün Kader Kartı")
    
    today = str(datetime.date.today())
    last_oracle = data.get('Last_Oracle', "")
    
    if last_oracle != today:
        if st.button("Kart Çek"):
            cards = [
                {"name": "Büyücü", "desc": "Yaratıcılığın zirvesindesin. (+50 XP)", "xp": 50},
                {"name": "Ermiş", "desc": "Yalnızlık sana güç verecek. (+30 XP)", "xp": 30},
                {"name": "Güç", "desc": "Zorlukların üstesinden geleceksin. (+100 XP)", "xp": 100},
                {"name": "Yıldız", "desc": "Umut ışığı parlıyor. (+20 XP)", "xp": 20}
            ]
            drawn = random.choice(cards)
            st.session_state.card_result = drawn
            
            data['XP'] += drawn['xp']
            data['Last_Oracle'] = today
            sync_user_to_cloud(data)
            st.rerun()
    else:
        st.info("Bugün zaten kaderine baktın. Yarın gel.")
        
    if 'card_result' in st.session_state:
        c = st.session_state.card_result
        st.markdown(f"""
        <div class="tarot-card">
            <h2>{c['name']}</h2>
            <p>{c['desc']}</p>
        </div>
        """, unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 5: POSTA ---
with tab5:
    with st.form("chat"):
        c1, c2 = st.columns([4,1])
        msg = c1.text_input("Mesaj:", label_visibility="collapsed")
        if c2.form_submit_button("Yolla"):
            send_chat_message(username, msg); st.rerun()
    
    msgs = get_chat_messages()
    for m in reversed(msgs):
        if len(m)>=3 and m[1]!="Username":
            col = "#d4af37" if m[1]==username else "#ccc"
            st.markdown(f"<div class='chat-row'><b style='color:{col}'>{m[1]}</b> <i style='float:right; font-size:10px'>{m[0]}</i><br>{m[2]}</div>", unsafe_allow_html=True)
    if st.button("Yenile"): st.rerun()

# --- TAB 6: GEÇMİŞ ---
with tab6:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else: st.info("Boş.")
