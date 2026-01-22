import streamlit as st
import pandas as pd
import datetime
import time
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# --- 1. GÖRSEL AYARLAR (GOD MODE) ---
st.set_page_config(page_title="Study OS Ultimate Online", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    /* GENEL ATMOSFER */
    .stApp {
        background-color: #0e0e0e;
        background-image: radial-gradient(circle at 50% 0%, #1f1f1f 0%, #0e0e0e 70%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3 { font-family: 'Playfair Display', serif; color: #d4af37; letter-spacing: 0.5px; }
    
    /* CAM KARTLAR (GLASSMORPHISM) */
    .glass-card {
        background: rgba(30, 30, 30, 0.7);
        backdrop-filter: blur(10px);
        border: 1px solid rgba(212, 175, 55, 0.1);
        border-radius: 16px;
        padding: 24px;
        margin-bottom: 20px;
        box-shadow: 0 4px 30px rgba(0, 0, 0, 0.5);
    }
    
    /* LİDERLİK TABLOSU */
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
    .rank-1 { color: #FFD700; font-weight: bold; font-size: 1.1em; text-shadow: 0 0 10px rgba(255, 215, 0, 0.3); }
    .rank-2 { color: #C0C0C0; font-weight: bold; }
    .rank-3 { color: #CD7F32; font-weight: bold; }
    
    /* BUTONLAR */
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #2b221a);
        color: #d4af37;
        border: 1px solid #d4af37;
        font-family: 'Playfair Display', serif;
        border-radius: 8px;
        transition: all 0.3s ease;
    }
    .stButton>button:hover {
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.3);
        border-color: #fff;
    }
    
    /* DERS PROGRAMI */
    .schedule-card {
        background-color: rgba(20, 20, 20, 0.8);
        border: 1px solid #333;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        min-height: 150px;
    }
    .schedule-today {
        border: 2px solid #d4af37 !important;
        background-color: rgba(212, 175, 55, 0.05) !important;
        box-shadow: 0 0 15px rgba(212, 175, 55, 0.1);
    }

    /* SİLME BUTONU */
    .delete-btn { color: #ff4b4b; font-weight: bold; cursor: pointer; }
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

# SADECE İstendiğinde Veri Çek (Cache yok, manuel kontrol)
def fetch_all_data_now():
    sheet = get_safe_sheet()
    if sheet:
        try:
            # Başlık kontrolü
            if not sheet.row_values(1):
                headers = ["Username", "XP", "Level", "History", "Tasks", "Cards", "Last_Login"]
                sheet.append_row(headers)
            return sheet.get_all_records()
        except Exception as e:
            st.error(f"Veri çekme hatası: {e}")
            return []
    return []

# Kullanıcıyı Local State'e Al
def get_user_from_local(username, all_records):
    # Önce indirilen veride ara
    for row in all_records:
        if row['Username'] == username:
            # Veri onarımı
            for key in ['History', 'Tasks', 'Cards']:
                if isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            return row
            
    # Yoksa yeni şablon döndür (Kaydetme işlemi sonra yapılır)
    return {
        "Username": username, "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today())
    }

# Buluta Kaydet
def sync_user_to_cloud(user_data):
    sheet = get_safe_sheet()
    if not sheet: return

    try:
        cell = sheet.find(user_data['Username'])
        row_num = cell.row
    except:
        # Kullanıcı yoksa yeni satır
        json_user = user_data.copy()
        for key in ['History', 'Tasks', 'Cards']:
            json_user[key] = json.dumps(json_user[key])
        sheet.append_row(list(json_user.values()))
        return

    # Varsa güncelle
    sheet.update_cell(row_num, 2, user_data['XP'])
    sheet.update_cell(row_num, 4, json.dumps(user_data['History']))
    sheet.update_cell(row_num, 5, json.dumps(user_data['Tasks']))
    sheet.update_cell(row_num, 6, json.dumps(user_data['Cards']))
    sheet.update_cell(row_num, 7, str(datetime.date.today()))

# Kullanıcı Silme (Admin)
def delete_user_from_cloud(username_to_delete):
    sheet = get_safe_sheet()
    if sheet:
        try:
            cell = sheet.find(username_to_delete)
            sheet.delete_rows(cell.row)
            st.toast(f"{username_to_delete} veritabanından silindi.", icon="🗑️")
            return True
        except:
            st.error("Kullanıcı bulunamadı.")
            return False
    return False

# --- 3. DERS PROGRAMI & ROZETLER (STATİK VERİ) ---
schedule_data = {
    "Pazartesi": [("10:40", "Yazma Becerileri ✍️"), ("14:50", "Sözlü İletişim 🗣️")],
    "Salı": [("12:20", "Türk Dili I 📚"), ("14:50", "Bilişim Teknolojileri 💻")],
    "Çarşamba": [("09:50", "Yabancı Dil I 🌍"), ("13:10", "Eğitim Sosyolojisi 🏛️"), ("Online", "Atatürk İlkeleri 🇹🇷")],
    "Perşembe": [("09:50", "Eğitime Giriş 🏛️"), ("13:00", "Serbest Okuma 🕯️")],
    "Cuma": [("12:20", "Okuma Becerileri 📖"), ("15:40", "Dinleme ve Sesletim 🎧")],
    "Cumartesi": [("Haftasonu", "Kültürel Aktiviteler 🎙️")],
    "Pazar": [("Haftasonu", "Planlama & Dinlenme ☕")]
}

# --- 4. UYGULAMA AKIŞI ---

if 'username' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🦉 Study OS Online</h1>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #888;'>Akademik Dünyaya Giriş Kapısı</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            name_input = st.text_input("Kod Adın:", placeholder="Örn: Gürkan")
            submitted = st.form_submit_button("Giriş Yap")
            if submitted and name_input:
                st.session_state.username = name_input
                st.rerun()
    st.stop()

# --- GİRİŞ YAPILDI ---
username = st.session_state.username

# State Yönetimi
if 'all_records' not in st.session_state:
    st.session_state.all_records = fetch_all_data_now() # İlk açılışta çek

if 'user_data' not in st.session_state:
    st.session_state.user_data = get_user_from_local(username, st.session_state.all_records)

# Kısa yollar
data = st.session_state.user_data
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False

# --- SIDEBAR: LİDERLİK & ADMIN ---
with st.sidebar:
    st.markdown(f"""
    <div style="text-align:center;">
        <div style="font-size: 50px;">🦉</div>
        <h2>{username}</h2>
        <h3 style="color:#d4af37;">{data['XP']} XP</h3>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # YENİLEME BUTONU
    if st.button("🔄 Verileri Yenile (API)", use_container_width=True):
        with st.spinner("Buluttan veriler çekiliyor..."):
            st.session_state.all_records = fetch_all_data_now()
            # Kendi verini de güncelle
            st.session_state.user_data = get_user_from_local(username, st.session_state.all_records)
            st.rerun()
            
    st.markdown("---")
    st.subheader("🏆 Liderlik Tablosu")
    
    # Admin Girişi
    admin_key = st.text_input("Admin Anahtarı:", type="password", placeholder="Gizli")
    is_admin = (admin_key == "admin") # Şifre: admin
    
    # Sıralama
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
        
        # SİLME BUTONU (Sadece Admin ve Kendisi değilse)
        with col_del:
            if is_admin and u['Username'] != username:
                if st.button("🗑️", key=f"del_{u['Username']}"):
                    delete_user_from_cloud(u['Username'])
                    time.sleep(1)
                    st.rerun()

# --- ANA EKRAN ---
st.title("Study OS")
st.caption("“Bilgi, bir ışık gibidir. Onu kullanırsan daha parlak olur.”")

tab1, tab2, tab3 = st.tabs(["🔥 Odaklan", "📅 Takvim", "📊 Geçmiş"])

# --- TAB 1: ODAKLANMA ---
with tab1:
    col_main, col_stat = st.columns([2, 1])
    
    with col_main:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Derin Çalışma Modu")
        
        courses = sorted(list({lesson for day in schedule_data for _, lesson in schedule_data[day]})) + ["Diğer / Özel Çalışma"]
        selected_course = st.selectbox("Bugünkü Hedefin:", courses, disabled=st.session_state.is_running)
        
        if not st.session_state.is_running:
            if st.button("🔥 BAŞLAT (25 dk)"):
                st.session_state.is_running = True
                st.session_state.start_time = time.time()
                st.rerun()
        else:
            # Sayaç Mantığı
            elapsed = int(time.time() - st.session_state.start_time)
            remaining = (25 * 60) - elapsed
            
            if remaining <= 0:
                st.balloons()
                st.session_state.is_running = False
                
                # VERİ GÜNCELLEME (Local + Cloud)
                xp_gain = 50
                data['XP'] += xp_gain
                new_hist = {"date": str(datetime.datetime.now())[:16], "course": selected_course, "duration": 25, "xp": xp_gain}
                data['History'].insert(0, new_hist)
                
                # Buluta gönder
                sync_user_to_cloud(data)
                
                st.success("Oturum Bitti! +50 XP Kaydedildi.")
                st.rerun()
            
            mins, secs = divmod(remaining, 60)
            st.markdown(f"<h1 style='text-align:center; font-size: 80px; color:#ff4b4b; text-shadow: 0 0 20px rgba(255, 75, 75, 0.4);'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            st.caption("Odaklan... Dünyayı sessize al.")
            
            if st.button("🛑 İPTAL"):
                st.session_state.is_running = False
                st.rerun()
            
            time.sleep(1)
            st.rerun()
            
        st.markdown('</div>', unsafe_allow_html=True)

    with col_stat:
        total_xp = data['XP']
        total_sessions = len(data['History'])
        
        st.markdown(f"""
        <div class="glass-card">
            <h4 style="color:#888; margin:0;">Toplam XP</h4>
            <h2 style="margin:0; color:#FFD700;">{total_xp}</h2>
        </div>
        <div class="glass-card">
            <h4 style="color:#888; margin:0;">Oturumlar</h4>
            <h2 style="margin:0;">{total_sessions}</h2>
        </div>
        """, unsafe_allow_html=True)

# --- TAB 2: TAKVİM (Güzel Grid) ---
with tab2:
    st.subheader("Haftalık Program")
    today_tr = {"Monday":"Pazartesi","Tuesday":"Salı","Wednesday":"Çarşamba","Thursday":"Perşembe","Friday":"Cuma","Saturday":"Cumartesi","Sunday":"Pazar"}[datetime.datetime.now().strftime("%A")]
    
    cols = st.columns(3)
    for i, day in enumerate(schedule_data.keys()):
        with cols[i % 3]:
            is_today = (day == today_tr)
            card_class = "schedule-card schedule-today" if is_today else "schedule-card"
            header_color = "#d4af37" if is_today else "#888"
            
            html = f'<div class="{card_class}"><h4 style="color: {header_color}; margin-top:0; border-bottom:1px solid #444; padding-bottom:5px;">{day}</h4>'
            for time_slot, lesson in schedule_data[day]:
                html += f'<div style="display: flex; justify-content: space-between; margin-bottom: 8px; border-bottom: 1px dashed #333; font-size: 14px;"><span style="font-weight: bold; color: #888;">{time_slot}</span><span style="color: #ddd;">{lesson}</span></div>'
            html += '</div>'
            st.markdown(html, unsafe_allow_html=True)

# --- TAB 3: GEÇMİŞ ---
with tab3:
    if data['History']:
        st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else:
        st.info("Henüz bir kayıt yok. Masanın başına geç!")
