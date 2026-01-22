import streamlit as st
import pandas as pd
import datetime
import time
import json
import random
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import streamlit.components.v1 as components

# --- 1. AYARLAR VE CSS ---
st.set_page_config(page_title="Study OS Online", page_icon="🦉", layout="wide")

st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    .stApp { background-color: #0e0e0e; color: #e0e0e0; font-family: 'Inter', sans-serif; }
    h1, h2, h3 { font-family: 'Playfair Display', serif; color: #d4af37; }
    .glass-card { background: rgba(30, 30, 30, 0.7); backdrop-filter: blur(10px); border: 1px solid rgba(212, 175, 55, 0.1); border-radius: 16px; padding: 24px; margin-bottom: 20px; }
    .leaderboard-row { padding: 10px; border-bottom: 1px solid #333; display: flex; justify-content: space-between; align-items: center; }
    .leaderboard-rank-1 { color: #FFD700; font-weight: bold; font-size: 1.2em; }
    .leaderboard-rank-2 { color: #C0C0C0; font-weight: bold; }
    .leaderboard-rank-3 { color: #CD7F32; font-weight: bold; }
    .stButton>button { background: linear-gradient(145deg, #3e3226, #2b221a); color: #d4af37; border: 1px solid #d4af37; }
    </style>
""", unsafe_allow_html=True)

# --- 2. GOOGLE SHEETS BAĞLANTISI ---
# Bu fonksiyon Streamlit Secrets'tan veriyi okuyup bağlanır
def get_google_sheet_client():
    scope = ['https://spreadsheets.google.com/feeds', 'https://www.googleapis.com/auth/drive']
    # Secrets'tan kimlik bilgilerini al
    creds_dict = dict(st.secrets["gcp_service_account"])
    creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
    client = gspread.authorize(creds)
    return client

# Veritabanı İşlemleri
def get_all_data():
    try:
        client = get_google_sheet_client()
        sheet = client.open("StudyOS_DB").sheet1
        # Tüm verileri al (Liste olarak döner)
        data = sheet.get_all_records()
        return data, sheet
    except Exception as e:
        st.error(f"Veritabanı Hatası: {e}")
        return [], None

def get_user_data(username, sheet, all_records):
    # Kullanıcıyı bul
    for row in all_records:
        if row['Username'] == username:
            # JSON stringlerini geri çevir
            try: row['History'] = json.loads(row['History'])
            except: row['History'] = []
            try: row['Tasks'] = json.loads(row['Tasks'])
            except: row['Tasks'] = []
            try: row['Cards'] = json.loads(row['Cards'])
            except: row['Cards'] = []
            return row
            
    # Kullanıcı yoksa oluştur (Varsayılan Veri)
    new_user = {
        "Username": username, "XP": 0, "Level": 1, 
        "History": "[]", "Tasks": "[]", "Cards": "[]", 
        "Last_Login": str(datetime.date.today())
    }
    # Sheet'e ekle
    sheet.append_row(list(new_user.values()))
    # Formatı düzeltip döndür
    new_user['History'] = []
    new_user['Tasks'] = []
    new_user['Cards'] = []
    return new_user

def update_user_data(sheet, user_data):
    # JSON'a çevirip güncelle
    cell = sheet.find(user_data['Username'])
    row_num = cell.row
    
    # Sadece değişenleri güncellemek daha güvenli ama şimdilik satırı güncelleyelim
    # Not: History, Tasks, Cards JSON string olmalı
    sheet.update_cell(row_num, 2, user_data['XP']) # XP
    sheet.update_cell(row_num, 4, json.dumps(user_data['History']))
    sheet.update_cell(row_num, 5, json.dumps(user_data['Tasks']))
    sheet.update_cell(row_num, 6, json.dumps(user_data['Cards']))
    sheet.update_cell(row_num, 7, str(datetime.date.today()))

# --- 3. UYGULAMA MANTIĞI ---

# Login Ekranı (Basit İsim Girişi)
if 'username' not in st.session_state:
    st.title("🦉 Study OS Online")
    st.markdown("Akademik yolculuğuna başlamak için ismini gir.")
    name_input = st.text_input("Kod Adın:", placeholder="Örn: Gürkan")
    if st.button("Giriş Yap"):
        if name_input:
            st.session_state.username = name_input
            st.rerun()
    st.stop() # İsim girmeden aşağıyı gösterme

# --- GİRİŞ YAPILDIKTAN SONRA ---
username = st.session_state.username
all_records, sheet = get_all_data()

# Kullanıcı verisini çek
if 'data' not in st.session_state:
    st.session_state.data = get_user_data(username, sheet, all_records)
    
data = st.session_state.data # Kısa yol

# State Tanımları
if 'start_time' not in st.session_state: st.session_state.start_time = None
if 'is_running' not in st.session_state: st.session_state.is_running = False
if 'pomo_mode' not in st.session_state: st.session_state.pomo_mode = "Work"

# --- SIDEBAR (LİDERLİK TABLOSU) ---
with st.sidebar:
    st.markdown(f"### 👤 {username}")
    st.markdown(f"**XP:** {data['XP']}")
    
    st.markdown("---")
    st.subheader("🏆 Liderlik Tablosu")
    
    # Sıralama Mantığı
    # Verileri XP'ye göre sırala
    sorted_users = sorted(all_records, key=lambda x: x['XP'], reverse=True)
    
    for rank, u in enumerate(sorted_users, 1):
        medal = ""
        if rank == 1: style = "leaderboard-rank-1"; medal="🥇"
        elif rank == 2: style = "leaderboard-rank-2"; medal="🥈"
        elif rank == 3: style = "leaderboard-rank-3"; medal="🥉"
        else: style = ""; medal = f"#{rank}"
        
        st.markdown(f"""
        <div class="leaderboard-row">
            <span class="{style}">{medal} {u['Username']}</span>
            <span style="color:#d4af37;">{u['XP']} XP</span>
        </div>
        """, unsafe_allow_html=True)
    
    if st.button("🔄 Yenile"):
        st.rerun()

# --- ANA EKRAN (Basitleştirilmiş Hibrit Mod) ---
st.title("Study OS Online")
st.caption(f"Hoş geldin, {username}. Rakiplerin çalışıyor, ya sen?")

tab1, tab2 = st.tabs(["🔥 Odaklan", "📊 Geçmiş"])

with tab1:
    col1, col2 = st.columns([2,1])
    with col1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.subheader("Pomodoro Sayacı")
        
        if not st.session_state.is_running:
            if st.button("🔥 BAŞLAT (25 dk)"):
                st.session_state.is_running = True
                st.session_state.start_time = time.time()
                st.rerun()
        else:
            elapsed = int(time.time() - st.session_state.start_time)
            remaining = (25 * 60) - elapsed
            
            if remaining <= 0:
                st.balloons()
                st.session_state.is_running = False
                # XP KAZANMA & KAYDETME
                data['XP'] += 50
                new_hist = {"date": str(datetime.datetime.now()), "course": "Online Çalışma", "duration": 25, "xp": 50}
                data['History'].insert(0, new_hist)
                
                # BULUTA KAYDET
                update_user_data(sheet, data)
                st.success("Oturum Bitti! +50 XP (Buluta Kaydedildi)")
                st.rerun()
            
            mins, secs = divmod(remaining, 60)
            st.markdown(f"<h1 style='text-align:center; font-size: 80px; color:#ff4b4b;'>{mins:02d}:{secs:02d}</h1>", unsafe_allow_html=True)
            
            if st.button("🛑 İPTAL"):
                st.session_state.is_running = False
                st.rerun()
            
            time.sleep(1)
            st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)

with tab2:
    if data['History']:
        st.dataframe(pd.DataFrame(data['History']))
    else:
        st.info("Henüz geçmiş kaydı yok.")