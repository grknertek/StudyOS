import streamlit as st
import pandas as pd
import datetime
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. GÖRSEL AYARLAR ---
st.set_page_config(page_title="Study OS Online", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .stApp {
        background-color: #0e0e0e;
        background-image: radial-gradient(circle at 50% 0%, #1f1f1f 0%, #0e0e0e 70%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 { font-family: 'Playfair Display', serif; color: #d4af37; letter-spacing: 0.5px; }
    
    .glass-card {
        background: rgba(30, 30, 30, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(212, 175, 55, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }
    
    /* Input Alanları Özelleştirme */
    .stTextInput input {
        background-color: #1a1a1a;
        color: #d4af37;
        border: 1px solid #333;
    }
    
    /* Liderlik Tablosu */
    .leaderboard-row {
        padding: 12px;
        border-bottom: 1px solid #333;
        display: flex;
        justify-content: space-between;
        align-items: center;
        background: rgba(255, 255, 255, 0.03);
        margin-bottom: 5px;
        border-radius: 8px;
    }
    .rank-1 { color: #FFD700; font-weight: bold; }
    .rank-2 { color: #C0C0C0; font-weight: bold; }
    .rank-3 { color: #CD7F32; font-weight: bold; }
    
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #2b221a);
        color: #d4af37;
        border: 1px solid #d4af37;
        font-family: 'Playfair Display', serif;
        border-radius: 8px;
        transition: all 0.3s ease;
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
        st.error(f"Bağlantı Hatası: {e}")
        return None

def fetch_all_data_now():
    sheet = get_safe_sheet()
    if sheet:
        try:
            if not sheet.row_values(1):
                headers = ["Username", "XP", "Level", "History", "Tasks", "Cards", "Last_Login"]
                sheet.append_row(headers)
            return sheet.get_all_records()
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            return []
    return []

def get_user_from_local(username, all_records):
    for row in all_records:
        if row['Username'] == username:
            for key in ['History', 'Tasks', 'Cards']:
                if isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            return row
    return {
        "Username": username, "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today())
    }

def sync_user_to_cloud(user_data):
    sheet = get_safe_sheet()
    if not sheet: return

    try:
        cell = sheet.find(user_data['Username'])
        row_num = cell.row
    except:
        json_user = user_data.copy()
        for key in ['History', 'Tasks', 'Cards']:
            json_user[key] = json.dumps(json_user[key])
        sheet.append_row(list(json_user.values()))
        return

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
            st.toast(f"{username_to_delete} silindi.", icon="🗑️")
            return True
        except:
            return False
    return False

# --- 3. UYGULAMA AKIŞI ---

if 'username' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🦉 Study OS Online</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            name_input = st.text_input("Kod Adın:", placeholder="Örn: Gürkan")
            submitted = st.form_submit_button("Giriş Yap")
            if submitted and name_input:
                st.session_state.username = name_input
                st.rerun()
    st.stop()

username = st.session_state.username

if 'all_records' not in st.session_state:
    st.session_state.all_records = fetch_all_data_now()

if 'user_data' not in st.session_state:
    st.session_state.user_data = get_user_from_local(username, st.session_state.all_records)

data = st.session_state.user_data
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False

# --- SIDEBAR ---
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;">
        <div style="font-size: 50px;">🦉</div>
        <h2>{username}</h2>
        <h3 style="color:#d4af37;">{data['XP']} XP</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🔄 Yenile (Liderlik Tablosu)", use_container_width=True):
        with st.spinner("Veriler çekiliyor..."):
            st.session_state.all_records = fetch_all_data_now()
            st.session_state.user_data = get_user_from_local(username, st.session_state.all_records)
            st.rerun()
            
    st.markdown("---")
    st.subheader("🏆 Liderlik Tablosu")
    
    admin_key = st.text_input("Admin:", type="password", placeholder="Gizli")
    is_admin = (admin_key == "admin")
    
    sorted_users = sorted(st.session_state.all_records, key=lambda x: x['XP'], reverse=True)
    
    for rank, u in enumerate(sorted_users, 1):
        medal = "🥇" if rank == 1 else "🥈" if rank == 2 else "🥉" if rank == 3 else f"#{rank}"
        style_cls = f"rank-{rank}" if rank <= 3 else ""
        
        col_rank, col_del = st.columns([4, 1])
        with col_rank:
            st.markdown(f"""
            <div class="leaderboard-row">
                <span class="{style_cls}">{medal} {u['Username']}</span>
                <span style="color:#d4af37;">{u['XP']} XP</span>
            </div>""", unsafe_allow_html=True)
        
        with col_del:
            if is_admin and u['Username'] != username:
                if st.button("🗑️", key=f"del_{u['Username']}"):
                    delete_user_from_cloud(u['Username'])
                    time.sleep(1)
                    st.rerun()

# --- ANA EKRAN ---
st.title("Study OS")
st.caption("“Bilgi, bir ışık gibidir. Onu kullanırsan daha parlak olur.”")

tab1, tab2, tab3, tab4 = st.tabs(["🔥 Odaklan", "✅ Görevler", "🧠 Kartlar", "📊 Geçmiş"])

# --- TAB 1: ODAKLAN (SERBEST GİRİŞ) ---
with tab1:
    col_main, col_stat = st.columns([2, 1])
    
    with col_main:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Derin Çalışma Modu")
        
        # ARTIK LİSTE YOK, SERBEST GİRİŞ VAR
        study_topic = st.text_input("Şu an ne üzerine çalışıyorsun?", placeholder="Örn: Matematik, Roman Yazımı, Piyano...")
        
        if not st.session_state.is_running:
            if st.button("🔥 BAŞLAT (25 dk)"):
                if study_topic:
                    st.session_state.is_running = True
                    st.session_state.start_time = time.time()
                    st.rerun()
                else:
                    st.warning("Lütfen bir konu yaz!")
        else:
            elapsed = int(time.time() - st.session_state.start_time)
            remaining = (25 * 60) - elapsed
            
            if remaining <= 0:
                st.balloons()
                st.session_state.is_running = False
                
                xp_gain = 50
                data['XP'] += xp_gain
                new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": 25, "xp": xp_gain}
                data['History'].insert(0, new_hist)
                sync_user_to_cloud(data)
                
                st.success(f"Oturum Bitti! +50 XP ({study_topic})")
                st.rerun()
            
            mins, secs = divmod(remaining, 60)
            st.markdown(f"<h1 style='text-align:center; font-size: 80px; color:#ff4b4b; text-shadow: 0 0 20px rgba(255, 75, 75, 0.4);'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            st.caption(f"Odaklanılan Konu: {study_topic}")
            
            if st.button("🛑 İPTAL"):
                st.session_state.is_running = False
                st.rerun()
            
            time.sleep(1)
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

    with col_stat:
        st.markdown(f"""
        <div class="glass-card">
            <h4 style="color:#888; margin:0;">Toplam XP</h4>
            <h2 style="margin:0; color:#FFD700;">{data['XP']}</h2>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: GÖREVLER (KİŞİSEL AJANDA) ---
with tab2:
    st.subheader("Kişisel Ajandan")
    
    with st.form("add_task"):
        new_task = st.text_input("Yeni Görev Ekle:")
        if st.form_submit_button("Ekle") and new_task:
            data['Tasks'].append({"task": new_task, "done": False})
            sync_user_to_cloud(data)
            st.rerun()
            
    if data['Tasks']:
        for i, t in enumerate(data['Tasks']):
            col_t1, col_t2 = st.columns([4, 1])
            with col_t1:
                st.markdown(f"**{t['task']}**")
            with col_t2:
                if st.button("✅", key=f"done_{i}"):
                    data['XP'] += 20
                    data['Tasks'].pop(i)
                    sync_user_to_cloud(data)
                    st.toast("+20 XP: Görev Tamamlandı!")
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("Yapılacak görev yok. Harika!")

# --- TAB 3: KARTLAR ---
with tab3:
    c1, c2 = st.columns([2, 1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        with st.form("add_card"):
            f = st.text_input("Ön Yüz:")
            b = st.text_input("Arka Yüz:")
            if st.form_submit_button("Kart Ekle") and f and b:
                data['Cards'].append({"front": f, "back": b})
                sync_user_to_cloud(data)
                st.success("Kart Eklendi!")
    
    with c1:
        if data['Cards']:
            if 'card_idx' not in st.session_state: st.session_state.card_idx = 0
            idx = st.session_state.card_idx
            if idx >= len(data['Cards']): idx = 0
            
            card = data['Cards'][idx]
            
            # Kart Görünümü
            if st.checkbox("Cevabı Göster", key="flip"):
                st.info(f"📝 {card['back']}")
            else:
                st.warning(f"❓ {card['front']}")
            
            if st.button("Sonraki Kart"):
                st.session_state.card_idx = (idx + 1) % len(data['Cards'])
                st.rerun()
        else:
            st.info("Henüz kartın yok.")

# --- TAB 4: GEÇMİŞ ---
with tab3:
    pass # Kartlar tab'ı ile karışmasın diye
with tab4:
    if data['History']:
        st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else:
        st.info("Henüz bir çalışma kaydı yok.")
