import streamlit as st
import pandas as pd
import datetime
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. PREMIUM GÖRSEL AYARLAR ---
st.set_page_config(page_title="Study OS Grand Design", page_icon="🍄", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* GENEL ATMOSFER (Derin Siyah & Altın) */
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 80%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    /* BAŞLIKLAR */
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif;
        color: #d4af37;
        letter-spacing: 1px;
        text-shadow: 0 4px 10px rgba(0,0,0,0.8);
    }
    
    /* CAM KARTLAR (Daha Kaliteli) */
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
    
    /* PROFİL RESMİ (BAYKUŞ) */
    .profile-img {
        width: 160px;
        height: 160px;
        border-radius: 50%;
        object-fit: cover;
        border: 3px solid #d4af37;
        box-shadow: 0 0 25px rgba(212, 175, 55, 0.3);
        margin-bottom: 15px;
        display: block;
        margin-left: auto;
        margin-right: auto;
    }
    
    /* INPUT VE SEÇİCİLER */
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(0, 0, 0, 0.4) !important;
        color: #d4af37 !important;
        border: 1px solid #443322 !important;
        border-radius: 10px;
    }
    
    /* BUTONLAR (ALTIN EFEKTLİ) */
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #1a1510);
        color: #d4af37;
        border: 1px solid #d4af37;
        font-family: 'Playfair Display', serif;
        font-size: 16px;
        padding: 10px 24px;
        border-radius: 8px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        width: 100%;
    }
    .stButton>button:hover {
        background: #d4af37;
        color: #000;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.5);
        border-color: #fff;
    }
    
    /* LİDERLİK TABLOSU */
    .leaderboard-row {
        padding: 15px;
        border-bottom: 1px solid rgba(212, 175, 55, 0.1);
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: linear-gradient(90deg, rgba(255,255,255,0.02) 0%, rgba(0,0,0,0) 100%);
        margin-bottom: 8px;
        border-radius: 8px;
        transition: transform 0.2s;
    }
    .leaderboard-row:hover {
        transform: scale(1.02);
        background: rgba(212, 175, 55, 0.08);
        border-left: 3px solid #d4af37;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. BACKEND: GOOGLE SHEETS ---
@st.cache_resource
def get_google_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

def get_safe_sheet():
    try:
        client = get_google_sheet_client()
        sheet = client.open("StudyOS_DB").sheet1
        return sheet
    except Exception as e:
        st.error(f"Sunucu Bağlantı Hatası: {e}")
        return None

def fetch_all_data_now():
    sheet = get_safe_sheet()
    if sheet:
        try:
            if not sheet.row_values(1):
                headers = ["Username", "XP", "Level", "History", "Tasks", "Cards", "Last_Login"]
                sheet.append_row(headers)
            return sheet.get_all_records()
        except: return []
    return []

def login_or_register(username):
    sheet = get_safe_sheet()
    if not sheet: return None
    all_records = sheet.get_all_records()
    clean_username = username.strip().lower()
    
    for row in all_records:
        if str(row['Username']).strip().lower() == clean_username:
            for key in ['History', 'Tasks', 'Cards']:
                if isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            return row
            
    new_user = {
        "Username": username.strip(), "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today())
    }
    save_user = new_user.copy()
    for key in ['History', 'Tasks', 'Cards']:
        save_user[key] = json.dumps(save_user[key])
    sheet.append_row(list(save_user.values()))
    return new_user

def sync_user_to_cloud(user_data):
    sheet = get_safe_sheet()
    if not sheet: return
    try:
        cell = sheet.find(user_data['Username'])
        row_num = cell.row
    except: return
    
    sheet.update_cell(row_num, 2, user_data['XP'])
    sheet.update_cell(row_num, 4, json.dumps(user_data['History']))
    sheet.update_cell(row_num, 5, json.dumps(user_data['Tasks']))
    sheet.update_cell(row_num, 6, json.dumps(user_data['Cards']))
    sheet.update_cell(row_num, 7, str(datetime.date.today()))

def delete_user_from_cloud(username_to_delete):
    sheet = get_safe_sheet()
    if sheet:
        try:
            cell = sheet.find(username_to_delete)
            sheet.delete_rows(cell.row)
            return True
        except: return False
    return False

# --- 3. GİRİŞ EKRANI ---
if 'username' not in st.session_state:
    st.markdown("<br><br>", unsafe_allow_html=True)
    # Yeni Baykuş Resmi (Büyük)
    st.markdown("""
    <div style="text-align: center;">
        <img src="https://images.unsplash.com/photo-1519052537078-e6302a4968d4?q=80&w=1000&auto=format&fit=crop" 
             class="profile-img" style="width: 200px; height: 200px;">
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h1 style='text-align: center;'>Study OS</h1>", unsafe_allow_html=True)
    
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
                    else:
                        st.error("Sunucu yanıt vermiyor.")
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 4. ANA UYGULAMA ---
username = st.session_state.username
data = st.session_state.user_data

if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'focus_mode' not in st.session_state: st.session_state.focus_mode = "Pomodoro"
if 'pomo_duration' not in st.session_state: st.session_state.pomo_duration = 25

# --- SIDEBAR (YENİ TASARIM) ---
with st.sidebar:
    # 1. PROFİL KARTI
    st.markdown(f"""
    <div style="text-align:center; margin-bottom: 20px;">
        <img src="https://images.unsplash.com/photo-1519052537078-e6302a4968d4?q=80&w=1000&auto=format&fit=crop" class="profile-img">
        <h2 style="margin:10px 0 0 0; font-size: 24px;">{username}</h2>
        <p style="color:#888; font-size: 14px; margin-top:5px;">Seviye {int(data['XP']/500) + 1}</p>
        <div style="background: rgba(212, 175, 55, 0.1); padding: 5px 15px; border-radius: 20px; display: inline-block; border: 1px solid rgba(212,175,55,0.3);">
            <span style="color:#d4af37; font-weight:bold;">{data['XP']} XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # 2. ATMOSFER
    st.subheader("🎧 Atmosfer")
    sound_choice = st.selectbox("Ses Manzarası:", 
                                ["Sessiz 🔇", "Yağmurlu Kütüphane 🌧️", "Şömine Ateşi 🔥", "Lofi Study ☕", "Brown Noise (Odak) 🧠"])
    
    if "Yağmurlu" in sound_choice: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in sound_choice: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    elif "Lofi" in sound_choice: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in sound_choice: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")
    
    st.markdown("---")
    
    if st.button("🔄 Liderlik Tablosunu Yenile"):
        st.session_state.all_records_view = fetch_all_data_now()
    
    # 3. LİDERLİK TABLOSU
    st.subheader("🏆 Liderler")
    if 'all_records_view' not in st.session_state:
        st.session_state.all_records_view = fetch_all_data_now()
        
    admin_key = st.text_input("Admin:", type="password", placeholder="Gizli", label_visibility="collapsed")
    is_admin = (admin_key == "admin")
    
    sorted_users = sorted(st.session_state.all_records_view, key=lambda x: x['XP'], reverse=True)
    
    for rank, u in enumerate(sorted_users, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
        
        col_rank, col_del = st.columns([4, 1])
        with col_rank:
            st.markdown(f"""
            <div class="leaderboard-row">
                <span style="color: {'#FFD700' if rank==1 else '#e0e0e0'}; font-weight:bold;">{medal} {u['Username']}</span>
                <span style="color:#d4af37;">{u['XP']}</span>
            </div>""", unsafe_allow_html=True)
        
        with col_del:
            if is_admin and u['Username'] != username:
                if st.button("🗑️", key=f"del_{u['Username']}"):
                    delete_user_from_cloud(u['Username'])
                    st.toast(f"{u['Username']} silindi.")
                    time.sleep(1)
                    st.rerun()

# --- ANA SEKME ---
st.title("Study OS")
st.caption("“Zihnin neredeyse, gücün oradadır.”")

tab1, tab2, tab3 = st.tabs(["🍄 Odaklan", "📜 Ajanda", "🕰️ Geçmiş"])

# --- TAB 1: ODAKLANMA (MANTAR MODU) ---
with tab1:
    col_main, col_stat = st.columns([2, 1])
    
    with col_main:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        # 1. MOD SEÇİMİ (Radio Button)
        mode = st.radio("Mod:", ["🍄 Mantar (Pomodoro)", "⏱️ Klasik (Kronometre)"], horizontal=True, disabled=st.session_state.is_running)
        
        # 2. SÜRE SEÇİMİ (Sadece Mantar Modu ise göster)
        if "Mantar" in mode:
            duration_opt = st.selectbox("Süre Seç:", ["25 dk (Klasik)", "50 dk (Derin Odak)", "90 dk (Flow State)"], disabled=st.session_state.is_running)
            # Seçilen süreyi sayıya çevir
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
                    if "Mantar" in mode:
                        st.session_state.pomo_duration = pomo_min
                    st.rerun()
                else:
                    st.warning("Lütfen bir konu yaz!")
        else:
            # AKTİF SAYAÇ
            elapsed = int(time.time() - st.session_state.start_time)
            
            if "Mantar" in st.session_state.focus_mode:
                target = st.session_state.pomo_duration * 60
                remaining = target - elapsed
                
                if remaining <= 0:
                    st.balloons()
                    st.session_state.is_running = False
                    
                    # XP HESABI: Dakika başına 2 XP
                    xp_gain = st.session_state.pomo_duration * 2
                    data['XP'] += xp_gain
                    new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": st.session_state.pomo_duration, "xp": xp_gain}
                    data['History'].insert(0, new_hist)
                    sync_user_to_cloud(data)
                    
                    st.success(f"Oturum Bitti! +{xp_gain} XP")
                    st.rerun()
                
                mins, secs = divmod(remaining, 60)
                color = "#ff4b4b" # Kırmızı (Mantar rengi)
            else:
                mins, secs = divmod(elapsed, 60)
                color = "#d4af37" # Altın
            
            st.markdown(f"<h1 style='text-align:center; font-size: 90px; color:{color}; text-shadow: 0 0 30px {color}; font-family: monospace;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            st.caption(f"Konu: {study_topic}")
            
            if st.button("🛑 DURDUR & KAYDET"):
                st.session_state.is_running = False
                # Klasik mod kaydı
                if "Klasik" in st.session_state.focus_mode:
                    duration_mins = elapsed // 60
                    if duration_mins >= 1:
                        xp_gain = duration_mins * 2
                        data['XP'] += xp_gain
                        new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": duration_mins, "xp": xp_gain}
                        data['History'].insert(0, new_hist)
                        sync_user_to_cloud(data)
                        st.success(f"Kaydedildi: {duration_mins} dk | +{xp_gain} XP")
                    else: st.warning("1 dakikadan kısa, XP yok.")
                st.rerun()
            time.sleep(1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

    with col_stat:
        st.markdown(f"""
        <div class="glass-card" style="text-align:center;">
            <h4 style="color:#888; margin:0;">Mevcut XP</h4>
            <h1 style="margin:0; color:#FFD700; font-size:40px;">{data['XP']}</h1>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: AJANDA ---
with tab2:
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
        else:
            st.info("Ajandan boş. Özgürsün!")

# --- TAB 3: GEÇMİŞ ---
with tab3:
    if data['History']:
        st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else:
        st.info("Henüz kayıt yok.")
