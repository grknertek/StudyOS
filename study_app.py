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
    
    /* MOD SEÇİCİ */
    .stRadio > div {
        background-color: rgba(255, 255, 255, 0.05);
        padding: 10px;
        border-radius: 10px;
        border: 1px solid #333;
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
    .rank-1 { color: #FFD700; font-weight: bold; }
    
    /* BUTONLAR */
    .stButton>button {
        background: linear-gradient(145deg, #3e3226, #2b221a);
        color: #d4af37;
        border: 1px solid #d4af37;
        font-family: 'Playfair Display', serif;
        border-radius: 8px;
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
            return []
    return []

# --- KRİTİK DÜZELTME: ÇİFT ÜYELİK ENGELLEME ---
def login_or_register(username):
    sheet = get_safe_sheet()
    if not sheet: return None
    
    # Tüm verileri çek
    all_records = sheet.get_all_records()
    
    # 1. MEVCUT KULLANICIYI ARA (Büyük/Küçük harf duyarsız)
    clean_username = username.strip().lower()
    
    for row in all_records:
        if str(row['Username']).strip().lower() == clean_username:
            # Kullanıcı bulundu! Verilerini düzeltip döndür
            # JSON alanlarını string'den listeye çevir
            for key in ['History', 'Tasks', 'Cards']:
                if isinstance(row[key], str):
                    try: row[key] = json.loads(row[key])
                    except: row[key] = []
            return row
            
    # 2. BULUNAMADIYSA YENİ KAYIT AÇ
    new_user = {
        "Username": username.strip(), # Orijinal yazımı kullan
        "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Cards": [], 
        "Last_Login": str(datetime.date.today())
    }
    
    # Sheet'e kaydetmek için JSON string'e çeviriyoruz
    save_user = new_user.copy()
    for key in ['History', 'Tasks', 'Cards']:
        save_user[key] = json.dumps(save_user[key])
        
    sheet.append_row(list(save_user.values()))
    return new_user

# Buluta Kaydet
def sync_user_to_cloud(user_data):
    sheet = get_safe_sheet()
    if not sheet: return

    try:
        cell = sheet.find(user_data['Username'])
        row_num = cell.row
    except:
        return # Kullanıcı bulunamazsa işlem yapma

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

# --- 3. UYGULAMA AKIŞI ---

if 'username' not in st.session_state:
    st.markdown("<h1 style='text-align: center;'>🦉 Study OS Online</h1>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1,2,1])
    with col2:
        with st.form("login_form"):
            name_input = st.text_input("Kod Adın:", placeholder="Örn: Gürkan")
            submitted = st.form_submit_button("Giriş Yap")
            if submitted and name_input:
                with st.spinner("Kütüphaneye giriliyor..."):
                    user_data = login_or_register(name_input)
                    if user_data:
                        st.session_state.username = user_data['Username']
                        st.session_state.user_data = user_data
                        st.rerun()
                    else:
                        st.error("Bağlantı hatası.")
    st.stop()

# --- GİRİŞ YAPILDI ---
username = st.session_state.username
data = st.session_state.user_data

if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'focus_mode' not in st.session_state: st.session_state.focus_mode = "Pomodoro"

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
    
    if st.button("🔄 Liderlik Tablosunu Yenile", use_container_width=True):
        st.session_state.all_records_view = fetch_all_data_now()
    
    st.subheader("🏆 Liderlik Tablosu")
    
    # Liderlik tablosu verisi (Cache veya taze)
    if 'all_records_view' not in st.session_state:
        st.session_state.all_records_view = fetch_all_data_now()
        
    admin_key = st.text_input("Admin:", type="password", placeholder="Gizli")
    is_admin = (admin_key == "admin")
    
    sorted_users = sorted(st.session_state.all_records_view, key=lambda x: x['XP'], reverse=True)
    
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
                    st.toast(f"{u['Username']} silindi.")
                    time.sleep(1)
                    st.rerun()

# --- ANA EKRAN ---
st.title("Study OS")
st.caption(f"Kişisel çalışma alanın, {username}. Buradaki her şey sadece sana özel.")

tab1, tab2, tab3 = st.tabs(["🔥 Odaklan", "✅ Özel Ajanda", "📊 Geçmiş"])

# --- TAB 1: HİBRİT ODAKLANMA (GERİ GELDİ!) ---
with tab1:
    col_main, col_stat = st.columns([2, 1])
    
    with col_main:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        
        # 1. MOD SEÇİMİ
        mode = st.radio("Çalışma Modu:", ["🍅 Pomodoro (25 dk)", "⏱️ Klasik (Kronometre)"], horizontal=True, disabled=st.session_state.is_running)
        
        # 2. KONU GİRİŞİ
        study_topic = st.text_input("Bugün ne çalışıyorsun?", placeholder="Örn: Fizik, Roman Okuma...")
        
        if not st.session_state.is_running:
            btn_text = "🔥 POMODORO BAŞLAT" if "Pomodoro" in mode else "⏱️ KRONOMETRE BAŞLAT"
            if st.button(btn_text, use_container_width=True):
                if study_topic:
                    st.session_state.is_running = True
                    st.session_state.start_time = time.time()
                    st.session_state.focus_mode = mode
                    st.rerun()
                else:
                    st.warning("Lütfen bir konu yaz!")
        else:
            # ÇALIŞMA ANI
            elapsed = int(time.time() - st.session_state.start_time)
            
            if "Pomodoro" in st.session_state.focus_mode:
                # GERİ SAYIM
                target = 25 * 60
                remaining = target - elapsed
                
                if remaining <= 0:
                    st.balloons()
                    st.session_state.is_running = False
                    
                    xp_gain = 50
                    data['XP'] += xp_gain
                    new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": 25, "xp": xp_gain}
                    data['History'].insert(0, new_hist)
                    sync_user_to_cloud(data)
                    
                    st.success(f"Pomodoro Bitti! +50 XP")
                    st.rerun()
                
                mins, secs = divmod(remaining, 60)
                color = "#ff4b4b"
            else:
                # İLERİ SAYIM (KLASİK)
                mins, secs = divmod(elapsed, 60)
                color = "#d4af37"
            
            st.markdown(f"<h1 style='text-align:center; font-size: 80px; color:{color}; text-shadow: 0 0 20px {color};'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            st.caption(f"Konu: {study_topic}")
            
            # DURDURMA BUTONU
            if st.button("🛑 OTURUMU BİTİR / DURDUR", use_container_width=True):
                st.session_state.is_running = False
                
                # Klasik modda manuel bitirilirse kaydet
                if "Klasik" in st.session_state.focus_mode:
                    duration_mins = elapsed // 60
                    if duration_mins >= 1:
                        xp_gain = duration_mins * 2 # Dakika başı 2 XP
                        data['XP'] += xp_gain
                        new_hist = {"date": str(datetime.datetime.now())[:16], "course": study_topic, "duration": duration_mins, "xp": xp_gain}
                        data['History'].insert(0, new_hist)
                        sync_user_to_cloud(data)
                        st.success(f"Kayıt Başarılı: {duration_mins} dk | +{xp_gain} XP")
                    else:
                        st.warning("1 dakikadan kısa sürdü, kaydedilmedi.")
                
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

# --- TAB 2: ÖZEL AJANDA (GİZLİ BÖLÜM) ---
with tab2:
    st.info(f"🔒 **Gizli Ajanda:** Buraya yazdıklarını sadece sen ({username}) görebilirsin.")
    
    col_add, col_list = st.columns([1, 2])
    
    with col_add:
        with st.form("add_task"):
            new_task = st.text_input("Görev Ekle:")
            if st.form_submit_button("Listeye Ekle") and new_task:
                data['Tasks'].append({"task": new_task, "done": False})
                sync_user_to_cloud(data)
                st.rerun()
    
    with col_list:
        if data['Tasks']:
            for i, t in enumerate(data['Tasks']):
                # Her görev için bir kutu
                with st.container():
                    c1, c2 = st.columns([5, 1])
                    with c1:
                        st.markdown(f"⬜ **{t['task']}**")
                    with c2:
                        if st.button("✅", key=f"done_{i}"):
                            data['XP'] += 20
                            data['Tasks'].pop(i)
                            sync_user_to_cloud(data)
                            st.toast("Görev tamamlandı! +20 XP")
                            time.sleep(1)
                            st.rerun()
                    st.markdown("---")
        else:
            st.caption("Yapılacak görev yok.")

# --- TAB 3: GEÇMİŞ ---
with tab3:
    if data['History']:
        st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else:
        st.info("Henüz bir çalışma kaydı yok.")
