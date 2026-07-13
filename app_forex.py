import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz
import warnings
import gc
import json
import os
import requests # <--- TAMBAHAN UNTUK TARIK DATA API
import xml.etree.ElementTree as ET # <--- TAMBAHAN UNTUK BACA DATA XML
import streamlit.components.v1 as components 

warnings.filterwarnings('ignore')

# ==========================================
# 0. SISTEM CACHE (AUTO-RESTORE)
# ==========================================
CACHE_FILE = "jihan_ghina_forex_cache.json"

if "raw_forex" not in st.session_state:
    st.session_state.raw_forex = []
    st.session_state.last_update = None
    
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache_data = json.load(f)
                st.session_state.raw_forex = cache_data.get("raw_forex", [])
                st.session_state.last_update = cache_data.get("last_update", None)
        except Exception as e:
            pass

if "scan_clicked" not in st.session_state:
    st.session_state.scan_clicked = len(st.session_state.raw_forex) > 0

# ==========================================
# 1. KONFIGURASI HALAMAN & UI STYLE (Sama seperti sebelumnya)
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Pro Max v1.2", page_icon="💱", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle at 50% -20%, #0f172a, #020617) !important; color: #f8fafc !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98% !important; }
    h1 { color: #f8fafc; font-weight: 900; letter-spacing: -1px; font-size: 2.2rem !important; margin-bottom: 0; }
    p { color: #94a3b8; font-weight: 300; }
    section[data-testid="stSidebar"] { background-color: rgba(2, 6, 23, 0.75) !important; backdrop-filter: blur(15px); border-right: 1px solid rgba(255, 255, 255, 0.05); }
    .premium-card { background: rgba(30, 41, 59, 0.3); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); transition: all 0.3s ease-in-out; }
    .premium-card:hover { transform: translateY(-5px); box-shadow: 0 12px 25px -5px rgba(250, 204, 21, 0.3); border-color: rgba(250, 204, 21, 0.4); }
    .ihsg-box { text-align: right; display: flex; flex-direction: column; justify-content: center; height: 100%; padding: 10px 15px !important; }
    .ihsg-title { color: #94a3b8; font-size: 0.65rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; }
    .ihsg-score { color: #facc15; font-size: 1.5rem; font-weight: 900; line-height: 1.1; margin: 2px 0; }
    .strat-num { font-size: 2.2rem; font-weight: 900; margin: 2px 0; line-height: 1; text-align: center; }
    .strat-label { font-size: 0.75rem; font-weight: 600; text-align: center; letter-spacing: 1px; }
    .swipe-panel { background: rgba(56, 189, 248, 0.1); border: 1px solid #38bdf8; padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 15px; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1.5. SISTEM KEAMANAN
# ==========================================
USERNAME_RAHASIA = "theo"
PASSWORD_RAHASIA = "216455"

if "akses_diberikan" not in st.session_state: st.session_state.akses_diberikan = False

if not st.session_state.akses_diberikan:
    st.markdown("<h2 style='text-align: center; color: #facc15; margin-top: 80px;'>🔒 FX TERMINAL TERKUNCI</h2>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.form(key="login_form"):
            user_input = st.text_input("👤 Username:")
            pwd_input = st.text_input("🔑 Password:", type="password")
            if st.form_submit_button("VERIFIKASI AKSES", use_container_width=True):
                if user_input.strip().lower() == USERNAME_RAHASIA.lower() and pwd_input.strip() == PASSWORD_RAHASIA:
                    st.session_state.akses_diberikan = True
                    st.rerun()
                else: st.error("Akses Ditolak!")
    st.stop()

# ==========================================
# 2. FUNGSI PEMROSESAN FOREX & FUNDAMENTAL
# ==========================================
def get_waktu_wib():
    return datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d %b %Y - %H:%M WIB")

roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "NZDUSD=X": "NZD/USD", "XAUUSD=X": "GOLD (XAU/USD)"}

def format_fx(ticker, val):
    if pd.isna(val): return "-"
    if "JPY" in ticker or "XAU" in ticker: return f"{val:.2f}"
    return f"{val:.4f}"

# [TAMBAHAN FUNDAMENTAL] - Fungsi menarik data Kalender Forex Factory
@st.cache_data(ttl=600, show_spinner=False) # Cache 10 menit agar tidak diblokir
def fetch_fundamental_sentiment():
    sentiment = {"USD": 0, "EUR": 0, "GBP": 0, "JPY": 0, "AUD": 0, "CAD": 0, "CHF": 0, "NZD": 0}
    try:
        url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
        response = requests.get(url, timeout=10)
        root = ET.fromstring(response.content)
        
        today_str = datetime.now(pytz.timezone('US/Eastern')).strftime("%m-%d-%Y")
        
        for event in root.findall('event'):
            date = event.find('date').text
            if date != today_str: continue # Hanya ambil data hari ini
            
            impact = event.find('impact').text # High, Medium, Low
            currency = event.find('country').text # USD, EUR, etc.
            actual_str = event.find('actual').text
            forecast_str = event.find('forecast').text
            
            # Jika data sudah rilis (Actual ada isinya) dan berdampak tinggi/sedang
            if actual_str and forecast_str and impact in ["High", "Medium"]:
                try:
                    # Membersihkan karakter string (seperti %, K, M, B)
                    act = float(''.join(c for c in actual_str if c.isdigit() or c == '.' or c == '-'))
                    fct = float(''.join(c for c in forecast_str if c.isdigit() or c == '.' or c == '-'))
                    
                    multiplier = 20 if impact == "High" else 10
                    
                    # Logika dasar: Actual > Forecast biasanya baik untuk mata uang tersebut
                    if act > fct:
                        sentiment[currency] += multiplier
                    elif act < fct:
                        sentiment[currency] -= multiplier
                except:
                    pass
                    
        return sentiment
    except:
        return sentiment # Kembalikan nol jika gagal koneksi

@st.cache_data(ttl=300, show_spinner=False)
def fetch_dxy():
    try:
        df = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)
        if df.empty: return None, None, None
        df = df.ffill()
        close_now = float(df['Close'].iloc[-1])
        close_prev = float(df['Close'].iloc[-2])
        chg = close_now - close_prev
        pct = (chg / close_prev) * 100
        return close_now, chg, pct
    except: return None, None, None

def hitung_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    return np.max(ranges, axis=1).rolling(period).mean()

def fetch_single_forex(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df = df.ffill()
        
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['ATR'] = hitung_atr(df)
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-1 * delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        close = float(df['Close'].iloc[-1])
        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA": close, 
            "RSI": round(float(df['RSI'].iloc[-1]), 2), "ATR": float(df['ATR'].iloc[-1]), 
            "PIVOT": (float(df['High'].iloc[-2]) + float(df['Low'].iloc[-2]) + float(df['Close'].iloc[-2])) / 3, 
            "EMA20": float(df['EMA20'].iloc[-1]),
            "UP_EMA20": close > float(df['EMA20'].iloc[-1]), 
            "MACD_BULL": float(df['MACD'].iloc[-1]) > float(df['Signal'].iloc[-1])
        }
    except: return None

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #facc15;'>👨‍💻 JIHAN-GHINA FX</h2>", unsafe_allow_html=True)
    if st.button("🔄 SCAN MAJOR PAIRS", use_container_width=True):
        st.session_state.scan_clicked = True
        st.cache_data.clear()
        st.session_state.raw_forex = []
        
        bar = st.progress(0, text="Mengkalibrasi Harga Global...")
        for i, t in enumerate(roster_forex):
            bar.progress((i + 1) / len(roster_forex), text=f"Scanning {nama_pairs[t]}...")
            data = fetch_single_forex(t)
            if data: st.session_state.raw_forex.append(data)
            
        bar.empty()
        st.session_state.last_update = get_waktu_wib()
        st.rerun()

# ==========================================
# 5. HEADER & MATRIKS UTAMA
# ==========================================
st.markdown("<h1>🌍 Global Macro Intelligence</h1>", unsafe_allow_html=True)

# [TAMBAHAN FUNDAMENTAL] - Panggil sentimen saat render
funda_sentiment = fetch_fundamental_sentiment()

if not st.session_state.scan_clicked or not st.session_state.raw_forex:
    st.info("👈 Sistem FX aman dan standby. Tekan '🔄 SCAN MAJOR PAIRS' di sidebar.")
else:
    st.markdown("<h3>🛰️ Pro Max FX Action Plan (Tech + Funda)</h3>", unsafe_allow_html=True)
    
    hasil_fx = []
    for raw in st.session_state.raw_forex:
        skor_tech = 0
        skor_funda = 0
        
        # --- LOGIKA TEKNIKAL ---
        if raw["UP_EMA20"]: skor_tech += 30
        if raw["MACD_BULL"]: skor_tech += 30
        
        if 40 <= raw["RSI"] <= 65: skor_tech += 40
        elif raw["RSI"] > 70: skor_tech -= 20
        elif raw["RSI"] < 30: skor_tech += 20
        
        # --- LOGIKA FUNDAMENTAL ---
        pair_str = raw["NAMA"] # Contoh: "EUR/USD" atau "GOLD (XAU/USD)"
        
        # Deteksi Base (Mata Uang Kiri) dan Quote (Mata Uang Kanan)
        if "/" in pair_str:
            base_curr = pair_str.split("/")[0][-3:] # Ambil 3 huruf terakhir sebelum / (Untuk kasus GOLD XAU)
            quote_curr = pair_str.split("/")[1][:3]
            
            # Jika rilis data base bagus, tambah skor. Jika rilis data quote bagus, kurangi skor.
            skor_funda += funda_sentiment.get(base_curr, 0)
            skor_funda -= funda_sentiment.get(quote_curr, 0)
            
        skor_total = skor_tech + skor_funda
        
        # --- KEPUTUSAN FINAL ---
        if skor_total >= 70: 
            rek = "🟢 LONG (BUY)"
            entry = raw["EMA20"] if raw["HARGA"] > raw["EMA20"] else raw["HARGA"]
            sl = entry - (1.5 * raw["ATR"])
            tp = entry + (2.0 * raw["ATR"])
        elif skor_total <= 30: 
            rek = "🔴 SHORT (SELL)"
            entry = raw["EMA20"] if raw["HARGA"] < raw["EMA20"] else raw["HARGA"]
            sl = entry + (1.5 * raw["ATR"])
            tp = entry - (2.0 * raw["ATR"])
        else: 
            rek = "🟡 WAIT / NO TRADE"
            entry, sl, tp = raw["HARGA"], raw["HARGA"], raw["HARGA"]
            
        hasil_fx.append({
            "PAIR": raw["NAMA"], 
            "HARGA NOW": format_fx(raw["TICKER"], raw["HARGA"]),
            "ENTRY AREA": format_fx(raw["TICKER"], entry),
            "TAKE PROFIT (TP)": format_fx(raw["TICKER"], tp),
            "STOP LOSS (SL)": format_fx(raw["TICKER"], sl),
            "SKOR FINAL": f"{skor_total} (Tech:{skor_tech}|Fund:{skor_funda})", # <--- MENAMPILKAN SKOR
            "ACTION": rek
        })
        
    df_fx = pd.DataFrame(hasil_fx)
    
    st.dataframe(df_fx, use_container_width=True, hide_index=True)

    # ==========================================
    # 7. KALENDER EKONOMI (TETAP ADA SEBAGAI REFERENSI VISUAL)
    # ==========================================
    st.markdown("---")
    st.markdown("<h3>📅 Global Economic Calendar</h3>", unsafe_allow_html=True)
    components.html(
        """
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {
          "colorTheme": "dark", "isTransparent": true, "width": "100%", "height": "500",
          "locale": "id", "importanceFilter": "-1,0,1", "currencyFilter": "USD,EUR,GBP,JPY,AUD,CAD,CHF,NZD"
          }
          </script>
        </div>
        """,
        height=500,
    )
