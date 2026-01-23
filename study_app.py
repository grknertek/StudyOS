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

# --- 1. AYARLAR & TASARIM (FULL DARK ACADEMIA) ---
st.set_page_config(page_title="Study OS Complete", page_icon="🦉", layout="wide")
import warnings
warnings.filterwarnings("ignore")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* GENEL */
    .stApp { background-color: #050505; background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 80%); color: #e0e0e0; font-family: 'Inter', sans-serif; }
    h1, h2, h3, h4 { font-family: 'Playfair Display', serif; color: #d4af37; letter-spacing: 1px; text-shadow: 0 4px 10px rgba(0,0,0,0.8); }
    
    /* CAM KARTLAR */
    .glass-card {
        background: rgba(25, 20, 15, 0.75); backdrop-filter: blur(16px); -webkit-backdrop-filter: blur(16px);
        border: 1px solid rgba(212, 175, 55, 0.25); border-radius: 20px; padding: 25px; margin-bottom: 25px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6); transition: transform 0.3s ease;
    }
    .glass-card:hover { border-color: rgba(212, 175, 55, 0.5); }
    
    /* TABLO ÇERÇEVESİ */
    .painting-frame {
        width: 150px; height: 180px; object-fit: cover; border: 6px solid #4a3c31; border-radius: 4px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.9), 0 5px 15px rgba(0,0,0,0.8), 0 0 0 2px #d4af37;
        margin: 0 auto 15px auto; display: block; filter: contrast(1.1) sepia(0.3);
    }
    .painting-frame-gold { border-color: #d4af37 !important; box-shadow: 0 0 30px #d4af37, inset 0 0 20px #000 !important; }
    
    /* DÜKKAN & TAROT */
    .shop-item { border: 1px solid #444; padding: 15px; border-radius: 10px; text-align: center; background: rgba(0,0,0,0.3); transition: transform 0.2s; margin-bottom: 10px; }
    .shop-item:hover { transform: scale(1.03); border-color: #d4af37; }
    .tarot-card { border: 2px solid #d4af37; border-radius: 10px; padding: 20px; text-align: center; background: linear-gradient(145deg, #2b221a, #000); animation: fadeIn 2s; }
    @keyframes fadeIn { from { opacity: 0; } to { opacity: 1; } }
    
    /* INPUT & BUTTON */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div { background-color: rgba(0, 0, 0, 0.5) !important; color: #d4af37 !important; border: 1px solid #554433 !important; border-radius: 10px; }
    .stButton>button { background: linear-gradient(145deg, #3e3226, #1a1510); color: #d4af37; border: 1px solid #d4af37; font-family: 'Playfair Display', serif; text-transform: uppercase; letter-spacing: 1.5px; width: 100%; }
    .stButton>button:hover { background: #d4af37; color: #000; box-shadow: 0 0 20px rgba(212, 175, 55, 0.6); }
    
    /* LİDERLİK SATIRI */
    .leaderboard-row { padding: 10px; border-bottom: 1px solid rgba(212, 175, 55, 0.1); display: flex; justify-content: space-between; font-size: 14px; }
    </style>
""", unsafe_allow_html=True)

# --- 2. KAHİN: GEMINI 2.5 FLASH ---
if "GEMINI_API_KEY" in st.secrets:
    try: genai.configure(api_key=st.secrets["GEMINI_API_KEY"])
    except: pass

@st.cache_resource
def get_model_name():
    # Öncelik: 2.5 Flash
    target = "models/gemini-2.5-flash"
    try:
        models = [m.name for m in genai.list_models()]
        if any('gemini-2.5-flash' in m for m in models): return [m for m in models if 'gemini-2.5-flash' in m][0]
        if any('gemini-1.5-flash' in m for m in models): return [m for m in models if 'gemini-1.5-flash' in m][0]
        return "models/gemini-pro"
    except: return "models/gemini-pro"

def ask_oracle(prompt):
    if "GEMINI_API_KEY" not in st.secrets: return "⚠️ API Anahtarı Eksik."
    try:
        model = genai.GenerativeModel(get_model_name())
        return model.generate_content(f"Sen 'Study OS' kütüphanesinin kadim koruyucususun. Cevapların kısa, bilgece ve gizemli olsun. Soru: {prompt}").text
    except Exception as e: return f"Kahin uykuda... ({e})"

# --- 3. VERİTABANI (HYBRID & SAĞLAM) ---
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

@st.cache_data(ttl=600) 
def get_cached_leaderboard():
    sheet = get_db()
    if sheet:
        try: return sheet.get_all_records()
        except: return []
    return []

def login_or_register(username):
    users_sheet = get_db()
    
    # OFFLINE MOD
    if not users_sheet:
        st.toast("⚠️ Sunucu Yoğun: Çevrimdışı Moddasın.")
        return {"Username": username, "XP": 100, "Level": 1, "History": [], "Tasks": [], "Inventory": [], "Active_Buffs": [], "Last_Oracle": ""}
    
    # ONLINE MOD
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
        
        # Yeni Kayıt
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
        # Kritik verileri güncelle
        sheet.update_cell(r, 2, user_data['XP'])
        sheet.update_cell(r, 4, json.dumps(user_data['History']))
        sheet.update_cell(r, 5, json.dumps(user_data['Tasks']))
        sheet.update_cell(r, 8, json.dumps(user_data['Inventory']))
        sheet.update_cell(r, 9, json.dumps(user_data['Active_Buffs']))
        sheet.update_cell(r, 10, str(user_data['Last_Oracle']))
        get_cached_leaderboard.clear()
    except: pass

def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    fig = go.Figure(data=go.Scatterpolar(r=stats['duration'], theta=stats['course'], fill='toself', line_color='#d4af37', fillcolor='rgba(212, 175, 55, 0.3)'))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, showticklabels=False, linecolor='#555')), paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), font=dict(family="Playfair Display", color="#d4af37"))
    return fig

# --- UYGULAMA ---
if 'username' not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>🦉 Study OS <span style='font-size:1.5rem; color:#888'>Complete</span></h1>", unsafe_allow_html=True)
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Kapıdan Gir"):
            with st.spinner("Ruhun tartılıyor..."):
                u = login_or_register(name)
                st.session_state.username = u['Username']
                st.session_state.user_data = u
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

username = st.session_state.username
data = st.session_state.user_data
# Veri Onarımı
for k in ['Inventory', 'Active_Buffs', 'Tasks']: 
    if k not in data: data[k] = []

# --- SIDEBAR (Liderlik Dahil) ---
with st.sidebar:
    # Profil
    gold_cls = "painting-frame-gold" if "Altın Çerçeve" in data['Inventory'] else ""
    mushroom = "🍄" if "Mantar Rozeti" in data['Inventory'] else ""
    
    st.markdown(f"""
    <div style="text-align:center;">
        <img src="https://images.unsplash.com/photo-1543549790-8b5f4a028cfb?q=80&w=400" class="painting-frame {gold_cls}">
        <h2 style="margin:10px 0 0 0;">{username} {mushroom}</h2>
        <div style="border:1px solid #d4af37; border-radius:20px; padding:5px 15px; margin-top:10px; display:inline-block; background:rgba(212,175,55,0.1);">
            <span style="color:#fff; font-weight:bold;">{data['XP']} XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🏆 Liderler")
    ldr = get_cached_leaderboard()
    if ldr:
        sorted_users = sorted(ldr, key=lambda x: x['XP'], reverse=True)[:5]
        for rank, u in enumerate(sorted_users, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            u_badge = "🍄" if "Mantar Rozeti" in str(u.get('Inventory', [])) else ""
            st.markdown(f"<div class='leaderboard-row'><span style='color:#d4af37'>{medal} {u['Username']} {u_badge}</span> <span>{u['XP']}</span></div>", unsafe_allow_html=True)
    else: st.caption("Çevrimdışı")

    st.markdown("---")
    st.subheader("🎧 Atmosfer")
    snd = st.selectbox("Ses:", ["Sessiz 🔇", "Yağmurlu 🌧️", "Şömine 🔥", "Lofi ☕", "Brown Noise 🧠"])
    if "Yağmur" in snd: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in snd: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    elif "Lofi" in snd: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in snd: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")

# --- ANA EKRAN ---
t1, t2, t3, t4, t5, t6 = st.tabs(["🔥 Odaklan", "🔮 Kahin", "🎒 Dükkan", "🃏 Tarot", "📜 Ajanda", "🕰️ Geçmiş"])

# 1. ODAKLAN
with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        topic = st.text_input("Çalışma Konusu:")
        if st.button("🔥 25 Dakika Başlat"):
            if topic:
                mult = 1.5 if any(b['name']=="Odak İksiri" for b in data['Active_Buffs']) else 1.0
                xp_gain = int(50 * mult)
                data['XP'] += xp_gain
                data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": 25})
                data['Active_Buffs'] = [] # İksir tükendi
                sync_user(data)
                st.balloons()
                st.success(f"Oturum Bitti! +{xp_gain} XP")
                if mult > 1: st.toast("İksir etkisi kullanıldı!")
                time.sleep(2); st.rerun()
            else: st.warning("Konu gir.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)

# 2. KAHİN
with t2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.markdown("### 🔮 Kahin'in Gözü")
    q = st.text_input("Sorunu sor:")
    if st.button("Danış"):
        with st.spinner("Kahin düşünüyor..."):
            res = ask_oracle(q)
            st.markdown(f"<div style='background:rgba(255,255,255,0.05); padding:15px; border-radius:10px; border-left:3px solid #d4af37;'>{res}</div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 3. DÜKKAN
with t3:
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🧪 Odak İksiri (x1.5 XP)"); st.caption("Fiyat: 200 XP")
        if st.button("Satın Al (200 XP)"):
            if data['XP'] >= 200:
                data['XP'] -= 200
                data['Active_Buffs'] = [{"name": "Odak İksiri", "multiplier": 1.5}]
                sync_user(data); st.toast("Gluk gluk... 🧪"); time.sleep(1); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)
    with col_s2:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Altın Çerçeve"); st.caption("Fiyat: 500 XP")
        if "Altın Çerçeve" in data['Inventory']: st.success("Sahipsin")
        elif st.button("Al (500 XP)"):
            if data['XP'] >= 500:
                data['XP'] -= 500; data['Inventory'].append("Altın Çerçeve")
                sync_user(data); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)

# 4. TAROT
with t4:
    st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
    st.subheader("🃏 Günün Kader Kartı")
    today = str(datetime.date.today())
    if data.get('Last_Oracle') != today:
        if st.button("Kart Çek"):
            c = random.choice([{"name":"Büyücü","desc":"(+50 XP)","xp":50}, {"name":"Güç","desc":"(+100 XP)","xp":100}])
            st.session_state.card = c
            data['XP'] += c['xp']; data['Last_Oracle'] = today
            sync_user(data); st.rerun()
    else: st.info("Yarın gel.")
    if 'card' in st.session_state:
        st.markdown(f"<div class='tarot-card'><h2>{st.session_state.card['name']}</h2><p>{st.session_state.card['desc']}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

# 5. AJANDA
with t5:
    c_add, c_list = st.columns([1,2])
    with c_add:
        with st.form("task"):
            t = st.text_input("Görev:")
            if st.form_submit_button("Ekle") and t:
                data['Tasks'].append({"task": t, "done": False})
                sync_user(data); st.rerun()
    with c_list:
        if data['Tasks']:
            for i, task in enumerate(data['Tasks']):
                c1, c2 = st.columns([5,1])
                c1.markdown(f"📜 {task['task']}")
                if c2.button("✅", key=f"d{i}"):
                    data['XP'] += 20; data['Tasks'].pop(i); sync_user(data); st.rerun()
        else: st.info("Boş.")

# 6. GEÇMİŞ
with t6:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
