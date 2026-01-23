import streamlit as st
import pandas as pd
import datetime
import time
import json
import random
import os
import plotly.express as px
import plotly.graph_objects as go

# --- 1. AYARLAR & TASARIM (DARK ACADEMIA - RENAISSANCE) ---
st.set_page_config(page_title="Study OS Local", page_icon="🦉", layout="wide")

# Görsel Stil (Senin sevdiğin o karanlık ve altın tema)
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600&family=Playfair+Display:ital,wght@0,400;0,700;1,400&display=swap');
    
    .stApp {
        background-color: #050505;
        background-image: radial-gradient(circle at 50% 0%, #1a1510 0%, #050505 90%);
        color: #e0e0e0;
        font-family: 'Inter', sans-serif;
    }
    
    h1, h2, h3, h4 {
        font-family: 'Playfair Display', serif !important;
        color: #d4af37 !important;
        letter-spacing: 1px;
        text-shadow: 0 4px 15px rgba(0,0,0,0.9);
    }
    
    .glass-card {
        background: rgba(20, 15, 10, 0.7);
        backdrop-filter: blur(20px);
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 16px;
        padding: 25px;
        margin-bottom: 20px;
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.5);
    }
    
    .stTextInput input, .stSelectbox div[data-baseweb="select"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        color: #d4af37 !important;
        border: 1px solid #4a3c31 !important;
        border-radius: 8px !important;
    }
    
    .stButton > button {
        background: linear-gradient(145deg, #3e3226, #1a1510) !important;
        color: #d4af37 !important;
        border: 1px solid #d4af37 !important;
        font-family: 'Playfair Display', serif !important;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        font-weight: bold;
        transition: all 0.3s ease;
    }
    .stButton > button:hover {
        background: #d4af37 !important;
        color: #050505 !important;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.6);
    }
    
    .painting-frame {
        width: 160px; height: 160px; object-fit: cover;
        border: 4px solid #4a3c31; outline: 2px solid #d4af37;
        border-radius: 50%; box-shadow: 0 0 30px rgba(0,0,0,0.8);
        margin: 0 auto 15px auto; display: block; filter: sepia(0.2) contrast(1.1);
    }
    .painting-frame-gold {
        border-color: #d4af37 !important; outline: 2px solid #fff !important;
        box-shadow: 0 0 40px #d4af37 !important;
    }
    
    .shop-item {
        background: rgba(255, 255, 255, 0.03); border: 1px solid #333;
        border-radius: 10px; padding: 15px; text-align: center;
        transition: transform 0.2s;
    }
    .shop-item:hover { border-color: #d4af37; transform: scale(1.02); }
    
    .tarot-card {
        background: linear-gradient(180deg, #1a1510 0%, #000 100%);
        border: 2px solid #d4af37; border-radius: 12px; padding: 20px;
        text-align: center; animation: fadeIn 1.5s ease-in-out;
    }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
    </style>
""", unsafe_allow_html=True)

# --- 2. YEREL VERİTABANI SİSTEMİ (JSON) ---
DB_FILE = "study_data.json"

def load_data():
    """Verileri yerel dosyadan çeker. Yoksa oluşturur."""
    if not os.path.exists(DB_FILE):
        return {}
    try:
        with open(DB_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except:
        return {}

def save_data(all_data):
    """Verileri yerel dosyaya yazar."""
    with open(DB_FILE, "w", encoding="utf-8") as f:
        json.dump(all_data, f, ensure_ascii=False, indent=4)

def get_user(username):
    all_data = load_data()
    clean_name = username.strip().lower()
    
    # Kullanıcı var mı?
    for user_key, user_val in all_data.items():
        if user_key == clean_name:
            return user_val
            
    # Yoksa yeni oluştur
    new_user = {
        "Username": username, "XP": 0, "Level": 1, 
        "History": [], "Tasks": [], "Inventory": [], 
        "Active_Buffs": [], "Last_Oracle": ""
    }
    all_data[clean_name] = new_user
    save_data(all_data)
    return new_user

def update_user(user_data):
    all_data = load_data()
    clean_name = user_data['Username'].strip().lower()
    all_data[clean_name] = user_data
    save_data(all_data)

# --- 3. GRAFİK SİSTEMİ ---
def create_radar_chart(history):
    if not history: return None
    df = pd.DataFrame(history)
    if 'course' not in df.columns or df.empty: return None
    stats = df.groupby('course')['duration'].sum().reset_index()
    fig = go.Figure(data=go.Scatterpolar(r=stats['duration'], theta=stats['course'], fill='toself', line_color='#d4af37', fillcolor='rgba(212, 175, 55, 0.3)'))
    fig.update_layout(polar=dict(bgcolor='rgba(0,0,0,0)', radialaxis=dict(visible=True, showticklabels=False, linecolor='#555'), angularaxis=dict(linecolor='#555', color='#d4af37')), paper_bgcolor='rgba(0,0,0,0)', margin=dict(l=20, r=20, t=20, b=20), font=dict(family="Playfair Display", color="#d4af37"))
    return fig

# --- 4. UYGULAMA GİRİŞİ ---
if 'username' not in st.session_state:
    st.markdown("<br><br><br>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center; font-size: 80px;'>🦉</h1>", unsafe_allow_html=True)
    st.markdown("<h1 style='text-align: center;'>Study OS <span style='font-size:20px; opacity:0.7'>Local Edition</span></h1>", unsafe_allow_html=True)
    
    c1, c2, c3 = st.columns([1,2,1])
    with c2:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        name = st.text_input("Kod Adın:", placeholder="Gezgin...")
        if st.button("Giriş Yap", use_container_width=True):
            if name:
                with st.spinner("Yerel arşivler açılıyor..."):
                    time.sleep(1)
                    u = get_user(name)
                    st.session_state.username = u['Username']
                    st.session_state.user_data = u
                    st.rerun()
        st.markdown('</div>', unsafe_allow_html=True)
    st.stop()

# --- 5. ANA EKRAN ---
username = st.session_state.username
data = st.session_state.user_data

# Sidebar (Profil)
with st.sidebar:
    gold_cls = "painting-frame-gold" if "Altın Çerçeve" in data['Inventory'] else ""
    mushroom = "🍄" if "Mantar Rozeti" in data['Inventory'] else ""
    
    st.markdown(f"""
    <div style="text-align:center; padding-bottom:20px;">
        <img src="https://images.unsplash.com/photo-1519052537078-e6302a4968d4?q=80&w=400" class="painting-frame {gold_cls}">
        <h2 style="margin:10px 0 5px 0;">{username} {mushroom}</h2>
        <div style="background: rgba(212,175,55,0.1); border:1px solid #d4af37; border-radius:20px; padding:5px 15px; display:inline-block;">
            <span style="color:#d4af37; font-weight:bold;">{data['XP']} XP</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    st.subheader("🎧 Atmosfer")
    snd = st.selectbox("Ses:", ["Sessiz", "Yağmur 🌧️", "Şömine 🔥", "Lofi ☕", "Brown Noise 🧠"])
    if "Yağmur" in snd: st.video("https://www.youtube.com/watch?v=mPZkdNFkNps")
    elif "Şömine" in snd: st.video("https://www.youtube.com/watch?v=K0pJRo0XU8s")
    elif "Lofi" in snd: st.video("https://www.youtube.com/watch?v=jfKfPfyJRdk")
    elif "Brown" in snd: st.video("https://www.youtube.com/watch?v=RqzGzwTY-6w")

# Ana Sekmeler (AI YOK)
t1, t2, t3, t4, t5 = st.tabs(["🔥 Odaklan", "🎒 Dükkan", "🃏 Kader", "📜 Ajanda", "🕰️ Geçmiş"])

with t1:
    c1, c2 = st.columns([2,1])
    with c1:
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        st.markdown("### 🍄 Odaklanma Ritüeli")
        topic = st.text_input("Çalışma Konusu:", placeholder="Matematik, Kodlama...")
        
        if st.button("🔥 25 Dakika Başlat", use_container_width=True):
            if topic:
                mult = 1.5 if any(b['name']=="Odak İksiri" for b in data['Active_Buffs']) else 1.0
                xp_gain = int(50 * mult)
                
                # İlerlemeyi kaydet
                data['XP'] += xp_gain
                data['History'].insert(0, {"date": str(datetime.datetime.now())[:16], "course": topic, "duration": 25})
                data['Active_Buffs'] = [] # İksir kullanıldı
                update_user(data)
                
                st.balloons()
                st.success(f"Oturum Tamamlandı! +{xp_gain} XP eklendi.")
                time.sleep(1.5); st.rerun()
            else: st.warning("Bir konu girmelisin.")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown("### 🕸️ Yetenek Ağı")
        fig = create_radar_chart(data['History'])
        if fig: st.plotly_chart(fig, use_container_width=True)
        else: st.info("Henüz veri yok.")

with t2:
    c1, c2 = st.columns(2)
    with c1:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🧪 Odak İksiri"); st.caption("200 XP")
        if st.button("Satın Al 🧪", use_container_width=True):
            if data['XP'] >= 200:
                data['XP'] -= 200; data['Active_Buffs'] = [{"name": "Odak İksiri", "multiplier": 1.5}]
                update_user(data); st.toast("İksir çantana eklendi!"); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)
    with c2:
        st.markdown('<div class="shop-item">', unsafe_allow_html=True)
        st.markdown("### 🖼️ Altın Çerçeve"); st.caption("500 XP")
        if "Altın Çerçeve" in data['Inventory']: st.success("Alındı ✅")
        elif st.button("Satın Al 🖼️", use_container_width=True):
            if data['XP'] >= 500:
                data['XP'] -= 500; data['Inventory'].append("Altın Çerçeve")
                update_user(data); st.rerun()
            else: st.error("Yetersiz XP")
        st.markdown('</div>', unsafe_allow_html=True)

with t3:
    st.markdown('<div class="glass-card" style="text-align:center;">', unsafe_allow_html=True)
    st.subheader("🃏 Günün Kader Kartı")
    today = str(datetime.date.today())
    
    if data.get('Last_Oracle') != today:
        if st.button("Kart Çek", use_container_width=True):
            cards = [
                {"name":"Büyücü","desc":"Potansiyelin sınırsız. (+50 XP)","xp":50},
                {"name":"Güç","desc":"Zorlukların üstesinden geleceksin. (+100 XP)","xp":100},
                {"name":"Yıldız","desc":"Umutların yeşeriyor. (+30 XP)","xp":30},
                {"name":"Ermiş","desc":"İçine dön ve cevapları bul. (+40 XP)","xp":40}
            ]
            c = random.choice(cards)
            st.session_state.card = c
            data['XP'] += c['xp']; data['Last_Oracle'] = today
            update_user(data); st.rerun()
    else:
        st.info("Bugünlük şansını denedin. Yarın tekrar gel.")
        
    if 'card' in st.session_state:
        c = st.session_state.card
        st.markdown(f"<div class='tarot-card'><h2>{c['name']}</h2><p>{c['desc']}</p></div>", unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

with t4:
    c_add, c_list = st.columns([1,2])
    with c_add:
        with st.form("add_task"):
            t = st.text_input("Görev:")
            if st.form_submit_button("Ekle", use_container_width=True) and t:
                data['Tasks'].append({"task": t})
                update_user(data); st.rerun()
    with c_list:
        if data['Tasks']:
            for i, task in enumerate(data['Tasks']):
                col_a, col_b = st.columns([5,1])
                col_a.markdown(f"📜 {task['task']}")
                if col_b.button("✅", key=f"done_{i}"):
                    data['XP'] += 20; data['Tasks'].pop(i); update_user(data); st.rerun()
        else: st.caption("Yapılacak görev yok.")

with t5:
    if data['History']: st.dataframe(pd.DataFrame(data['History']), use_container_width=True)
    else: st.info("Kayıt bulunamadı.")
