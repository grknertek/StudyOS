import streamlit as st
import pandas as pd
import datetime
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. PREMIUM GÖRSEL AYARLAR ---
st.set_page_config(page_title="Study OS Living World", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* GENEL ATMOSFER */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 80%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif;
        color: #d4af37;
        letter-spacing: 1px;
        text-shadow: 0 4px 10px rgba(0,0,0,0.8);
    }
    
    /* CAM KARTLAR */
    .glass-card {
        background: rgba(25, 20, 15, 0.7);
        backdrop-filter: blur(15px);
        -webkit-backdrop-filter: blur(15px);
        border: 1px solid rgba(212, 175, 55, 0.2);
        border-radius: 20px;
        padding: 30px;
        margin-bottom: 25px;
        box-shadow: 0 10px 40px rgba(0, 0, 0, 0.6);
    }
    
    /* TABLO ÇERÇEVESİ (HOGWARTS) */
    .painting-frame {
        width: 180px;
        height: 220px;
        object-fit: cover;
        border: 8px solid #4a3c31; 
        border-radius: 4px;
        box-shadow: inset 0 0 20px rgba(0,0,0,0.8), 0 10px 30px rgba(0,0,0,0.8), 0 0 0 2px #d4af37;
        margin: 0 auto 15px auto;
        display: block;
        filter: contrast(1.1) sepia(0.2);
    }
    .painting-frame-gold {
        border-color: #d4af37 !important; /* Dükkandan alınan altın çerçeve */
        box-shadow: 0 0 30px #d4af37, inset 0 0 20px #000 !important;
    }
    
    /* CHAT BALONLARI */
    .chat-row {
        padding: 10px;
        margin-bottom: 10px;
        border-radius: 10px;
        background: rgba(255, 255, 255, 0.05);
        border-left: 3px solid #d4af37;
    }
    .chat-user { font-weight: bold; color: #d4af37; font-size: 12px; }
    .chat-msg { color: #e0e0e0; margin-top: 2px; }
    .chat-time { float: right; font-size: 10px; color: #666; }
    
    /* DÜKKAN KARTLARI */
    .shop-item {
        border: 1px solid #444;
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        background: rgba(0,0,0,0.3);
        transition: transform 0.2s;
    }
    .shop-item:hover { transform: scale(1.03); border-color: #d4af37; }
    
    /* INPUTLAR */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(0, 0, 0, 0.4) !important;
        color: #d4af37 !important;
        border: 1px solid #443322 !important;
        border-radius: 10px;
    }
    
    /* BUTONLAR */
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #1a1510);
        color: #d4af37;
        border: 1px solid #d4af37;
        font-family: 'Playfair Display', serif;
        text-transform: uppercase;
        letter-spacing: 1.5px;
    }
    .stButton>button:hover {
        background: #d4af37;
        color: #000;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BACKEND: GOOGLE SHEETS & RÜTBE SİSTEMİ ---

RANKS = {
    0: "Mürekkep Çırağı 🖋️",
    500: "Kütüphane Muhafızı 🗝️",
    1500: "Hakikat Arayıcısı 🕯️",
    3000: "Bilgelik Mimarı 🏛️",
    5000: "Entelektüel Lord 👑"
}

def get_rank(xp):
    current_rank = "Mürekkep Çırağı 🖋️"
    for limit in sorted(RANKS.keys()):
        if xp >= limit:
            current_rank = RANKS[limit]
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
        # Sheet1: Kullanıcılar, Sheet2: Chat (Yoksa oluşturur ama manuel oluşturman daha güvenli)
        try: users_sheet = sheet.get_worksheet(0)
        except: users_sheet = sheet.add_worksheet(title="Users", rows=100, cols=10)
        
        try: chat_sheet = sheet.get_worksheet(1)
        except: chat_sheet = sheet.add_worksheet(title="OwlPost", rows=1000, cols=3)
        
        return users_sheet, chat_sheet
    except Exception as e:
        st.error(f"Veritabanı Hatası: {e}")
        return None, None

def check_db_setup(users_sheet, chat_sheet):
    # Kullanıcı Başlıkları
    if not users_sheet.row_values(1):
        users_sheet.append_row(["Username", "XP", "Level", "History", "Tasks", "Cards", "Last_Login", "Inventory"])
    # Chat Başlıkları
    if not chat_sheet.row_values(1):
        chat_sheet.append_row(["Timestamp", "Username", "Message"])

def login_or_register(username):
    users_sheet, _ = get_db()
    if not users_sheet: return None
    
    check_db_setup(users_sheet, _) # Başlık kontrolü
    
    all_records = users_sheet.get_all_records()
    clean_username = username.strip().lower()
    
    for row in all_records:
        if str(row['Username']).strip().lower() == clean_username:
            # JSON decode
            for key in ['History', 'Tasks', 'Cards', 'Inventory']:
                if key in row and isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            if 'Inventory' not in row: row['Inventory'] = [] # Eski kullanıcılar için fix
            return row
            
    # Yeni Kullanıcı
    new_user = {
        "Username": username.strip(), "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today()),
        "Inventory": []
    }
    save_user = new_user.copy()
    for key in ['History', 'Tasks', 'Cards', 'Inventory']:
        save_user[key] = json.dumps(save_user[key])
    
    users_sheet.append_row(list(save_user.values()))
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
    except: pass

# --- CHAT SİSTEMİ ---
def send_chat_message(username, message):
    _, chat_sheet = get_db()
    if chat_sheet:
        ts = datetime.datetime.now().strftime("%H:%M")
        chat_sheet.append_row([ts, username, message])

def get_chat_messages():
    _, chat_sheet = get_db()
    if chat_sheet:
        # Son 20 mesajı al (Performans için)
        all_rows = chat_sheet.get_all_values()
        if len(all_rows) > 1:
            return all_rows[-20:] # Başlık hariç son 20
    return []

# --- 3. GİRİŞ EKRANI ---
if 'username' not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    st.markdown("""
    <div style="text-align: center;">
        <img src="https://images.unsplash.com/photo-1543549790-8b5f4a028cfb?q=80&w=400&auto=format&fit=crop" 
             class="painting-frame">
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>Study OS <span style='font-size:20px'>Living World</span></h1>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("login_form"):
            name_input = st.text_input("Kimsin sen, gezgin?", placeholder="Kod Adın...")
            submitted = st.form_submit_button("Kapıdan Gir")
            if submitted and name_input:
                with st.spinner("Parşömenler taranıyor..."):
                    user_data = login_or_register(name_input)
                    if user_data:
                        st.session_state.username = user_data['Username']
                        st.session_state.user_data = user_data
                        st.rerun()
                    else: st.error("Sunucuya ulaşılamıyor. (Lütfen Sheet'i sıfırladığından emin ol)")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. ANA UYGULAMA ---
username = st.session_state.username
data = st.session_state.user_data
current_rank = get_rank(data['XP'])

# Envanter Kontrolleri (Görsel Efektler)
gold_frame_class = "painting-frame-gold" if "Altın Çerçeve" in data['Inventory'] else ""
mushroom_badge = "🍄" if "Mantar Rozeti" in data['Inventory'] else ""

if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'focus_mode' not in st.session_state: st.session_state.focus_mode = "Mantar (50 dk)"
if 'pomo_duration' not in st.session_state: st.session_state.pomo_duration = 50

# --- SIDEBAR ---
with st.sidebar:
    # PROFİL
    st.markdown(f"""
    <div style="text-align:center; margin-bottom: 20px;">
        <img src="https://images.unsplash.com/photo-1543549790-8b5f4a028cfb?q=80&w=400&auto=format&fit=crop" 
             class="painting-frame {gold_frame_class}">
        <h2 style="margin:10px 0 0 0; font-size: 24px;">{username} {mushroom_badge}</h2>
        <p style="color:#d4af37; font-weight:bold; margin-top:5px;">{current_rank}</p>
        <div style="background: rgba(212, 175, 55, 0.1); padding: 5px 15px; border-radius: 20px; display: inline-block; border: 1px solid rgba(212,175,55,0.3);">
            <span style="color:#fff; font-weight:bold;">{data['XP']} XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # ATMOSFER
    st.subheader("🎧 Atmosfer")
    sound_choice = st.selectbox("Ses Manzarası:", 
                                ["Sessiz 🔇", "Yağmurlu Kütüphane 🌧️", "Şömine Ateşi 🔥", "Lofi Study ☕", "Brown Noise (Odak) 🧠"])
    
    if "Yağmurlu" in sound_choice: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in sound_choice: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    elif "Lofi" in sound_choice: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in sound_choice: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")
    
    st.markdown("---")
    
    # LİDERLİK
    st.subheader("🏆 Liderler")
    if st.button("🔄 Yenile"):
        st.session_state.leaderboard = None # Cache temizle mantığı
        st.rerun()

    users_sheet, _ = get_db()
    if users_sheet:
        all_recs = users_sheet.get_all_records()
        sorted_users = sorted(all_recs, key=lambda x: x['XP'], reverse=True)
        
        for rank, u in enumerate(sorted_users, 1):
            medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
            u_badge = "🍄" if "Mantar Rozeti" in str(u.get('Inventory', [])) else ""
            
            st.markdown(f"""
            <div class="leaderboard-row">
                <span style="color: {'#FFD700' if rank==1 else '#e0e0e0'}; font-weight:bold;">{medal} {u['Username']} {u_badge}</span>
                <span style="color:#d4af37;">{u['XP']}</span>
            </div>""", unsafe_allow_html=True)

# --- ANA SEKME ---
st.title("Study OS")
st.caption(f"“Hoş geldin, {current_rank} {username}.”")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["🍄 Odaklan", "🦉 Baykuş Postası", "🎒 Dükkan", "📜 Ajanda", "🕰️ Geçmiş"])

# --- TAB 1: ODAKLANMA ---
with tab1:
    col_main, col_stat = st.columns([2, 1])
    with col_main:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        mode = st.radio("Mod:", ["🍄 Mantar Modu", "⏱️ Klasik (Kronometre)"], horizontal=True, disabled=st.session_state.is_running)
        
        if "Mantar" in mode:
            duration_opt = st.selectbox("Süre Seç:", ["25 dk (Klasik)", "50 dk (Derin Odak)", "90 dk (Flow State)"], disabled=st.session_state.is_running)
            pomo_min = int(duration_opt.split(" ")[0])
        
        st.markdown("---")
        study_topic = st.text_input("Çalışma Konusu:", placeholder="Örn: Edebiyat, Matematik...")
        
        if not st.session_state.is_running:
            btn_text = f"🔥 {pomo_min} DK BAŞLAT" if "Mantar" in mode else "⏱️ KRONOMETRE BAŞLAT"
            if st.button(btn_text):
                if study_topic:
                    st.session_state.is_running = True
                    st.session_state.start_time = time.time()
                    st.session_state.focus_mode = mode
                    if "Mantar" in mode: st.session_state.pomo_duration = pomo_min
                    st.rerun()
                else: st.warning("Konu giriniz.")
        else:
            elapsed = int(time.time() - st.session_state.start_time)
            if "Mantar" in st.session_state.focus_mode:
                target = st.session_state.pomo_duration * 60
                remaining = target - elapsed
                if remaining <= 0:
                    st.balloons()
                    st.session_state.is_running = False
                    xp_gain = st.session_state.pomo_duration * 2
                    data['XP'] += xp_gain
                    new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": st.session_state.pomo_duration, "xp": xp_gain}
                    data['History'].insert(0, new_hist)
                    sync_user_to_cloud(data)
                    st.success(f"Oturum Bitti! +{xp_gain} XP")
                    st.rerun()
                mins, secs = divmod(remaining, 60)
                color = "#ff4b4b"
            else:
                mins, secs = divmod(elapsed, 60)
                color = "#d4af37"
            
            st.markdown(f"<h1 style='text-align:center; font-size: 90px; color:{color}; text-shadow: 0 0 30px {color}; font-family: monospace;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            st.caption(f"Konu: {study_topic}")
            if st.button("🛑 DURDUR & KAYDET"):
                st.session_state.is_running = False
                if "Klasik" in st.session_state.focus_mode:
                    duration_mins = elapsed // 60
                    if duration_mins >= 1:
                        xp_gain = duration_mins * 2
                        data['XP'] += xp_gain
                        new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": duration_mins, "xp": xp_gain}
                        data['History'].insert(0, new_hist)
                        sync_user_to_cloud(data)
                        st.success(f"Kaydedildi: {duration_mins} dk | +{xp_gain} XP")
                    else: st.warning("1 dakikadan kısa.")
                st.rerun()
            time.sleep(1); st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_stat:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <h4 style="color:#888; margin:0;">Mevcut XP</h4>
            <h1 style="margin:0; color:#FFD700; font-size:40px;">{data['XP']}</h1>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: BAYKUŞ POSTASI (CHAT) ---
with tab2:
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    st.subheader("🦉 Baykuş Postası (Canlı Duvar)")
    
    # Mesaj Gönderme
    with st.form("chat_form", clear_on_submit=True):
        col_msg, col_btn = st.columns([4, 1])
        with col_msg:
            msg_input = st.text_input("Mesajın:", placeholder="Buraya yaz...", label_visibility="collapsed")
        with col_btn:
            sent = st.form_submit_button("Gönder ➤")
        
        if sent and msg_input:
            send_chat_message(username, msg_input)
            st.rerun()
    
    st.markdown("---")
    
    # Mesajları Listele
    messages = get_chat_messages()
    # Mesajlar: [Timestamp, Username, Message]
    # Sondan başa doğru (En yeni en üstte)
    for msg in reversed(messages):
        if len(msg) >= 3 and msg[1] != "Username": # Başlık değilse
            ts, user, text = msg[0], msg[1], msg[2]
            align = "text-align: right; border-left: none; border-right: 3px solid #d4af37;" if user == username else ""
            bg = "rgba(212, 175, 55, 0.1)" if user == username else "rgba(255, 255, 255, 0.05)"
            
            st.markdown(f"""
            <div class="chat-row" style="{align} background: {bg};">
                <span class="chat-user">{user}</span> <span class="chat-time">{ts}</span><br>
                <span class="chat-msg">{text}</span>
            </div>
            """, unsafe_allow_html=True)
            
    if st.button("🔄 Postayı Yenile"):
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 3: XP DÜKKANI ---
with tab3:
    st.subheader("🎒 XP Dükkanı & Envanter")
    
    col_s1, col_s2 = st.columns(2)
    
    # ÜRÜN 1: ALTIN ÇERÇEVE
    with col_s1:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Altın Çerçeve")
        st.caption("Profil resmine asil bir altın çerçeve ve parlama efekti ekler.")
        st.markdown("**Fiyat: 500 XP**")
        
        if "Altın Çerçeve" in data['Inventory']:
            st.success("✅ Satın Alındı")
        else:
            if st.button("Satın Al (500 XP)", key="buy_frame"):
                if data['XP'] >= 500:
                    data['XP'] -= 500
                    data['Inventory'].append("Altın Çerçeve")
                    sync_user_to_cloud(data)
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Yetersiz XP!")
        st.markdown('</div>', unsafe_allow_html=True)
        
    # ÜRÜN 2: MANTAR ROZETİ
    with col_s2:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🍄 Mantar Rozeti")
        st.caption("Liderlik tablosunda ve isminin yanında havalı bir mantar ikonu çıkar.")
        st.markdown("**Fiyat: 1000 XP**")
        
        if "Mantar Rozeti" in data['Inventory']:
            st.success("✅ Satın Alındı")
        else:
            if st.button("Satın Al (1000 XP)", key="buy_badge"):
                if data['XP'] >= 1000:
                    data['XP'] -= 1000
                    data['Inventory'].append("Mantar Rozeti")
                    sync_user_to_cloud(data)
                    st.balloons()
                    st.rerun()
                else:
                    st.error("Yetersiz XP!")
        st.markdown('</div>', unsafe_allow_html=True)

# --- TAB 4 & 5: AJANDA & GEÇMİŞ (ESKİSİ GİBİ) ---
with tab4:
    col_add, col_list = st.columns([1, 2])
    with col_add:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("add_task"):
            new_task = st.text_input("Yeni Görev:")
            if st.form_submit_button("Listeye Ekle") and new_task:
                data['Tasks'].append({"task": new_task, "done": False})
                sync_user_to_cloud(data)
                st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    with col_list:
        if data['Tasks']:
            for i, t in enumerate(data['Tasks']):
                with st.container():
                    c1, c2 = st.columns([5, 1])
                    with c1: st.markdown(f"📜 **{t['task']}**")
                    with c2:
                        if st.button("✅", key=f"done_{i}"):
                            data['XP'] += 20
                            data['Tasks'].pop(i)
                            sync_user_to_cloud(data)
                            st.toast("Görev tamamlandı! +20 XP")
                            time.sleep(1)
                            st.rerun()
                    st.markdown("<hr style='border-top: 1px dashed rgba(212,175,55,0.3);'>", unsafe_allow_html=True)
        else: st.info("Ajandan boş.")

with tab5:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else: st.info("Kayıt yok.")
