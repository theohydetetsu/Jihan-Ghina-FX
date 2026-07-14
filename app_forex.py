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
import requests 
import xml.etree.ElementTree as ET
import plotly.graph_objects as go
import streamlit.components.v1 as components 

warnings.filterwarnings('ignore')

# ==========================================
# 0. SISTEM CACHE & TRACKING TIMEFRAME
# ==========================================
CACHE_FILE = "jihan_ghina_fx_cache.json"

if "raw_forex" not in st.session_state:
    st.session_state.raw_forex = []
    st.session_state.last_update = None
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache_data = json.load(f)
                st.session_state.raw_forex = cache_data.get("raw_forex", [])
                st.session_state.last_update = cache_data.get("last_update", None)
        except: pass

if "scan_clicked" not in st.session_state:
    st.session_state.scan_clicked = True if len(st.session_state.raw_forex) > 0 else False

if "current_tf" not in st.session_state:
    st.session_state.current_tf = "1 Hari (Daily)"

# ==========================================
# 1. KONFIGURASI HALAMAN & UI STYLE (ULTRA-PREMIUM)
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Pro Max v9.0", page_icon="💱", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800;900&display=swap');
    
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #1e1b4b, #020617, #000000) !important; 
        color: #f8fafc !important; 
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 96% !important; }
    
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(250, 204, 21, 0.4); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(250, 204, 21, 0.8); }
    
    h1 { color: #ffffff; font-weight: 800; letter-spacing: -1px; font-size: 2.4rem !important; margin-bottom: 0; text-shadow: 0 0 20px rgba(255,255,255,0.1); }
    p { color: #94a3b8; font-weight: 300; line-height: 1.6; }
    
    .premium-card { 
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4));
        backdrop-filter: blur(20px); -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.05); border-top: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; padding: 20px; box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); 
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s ease;
    }
    .premium-card:hover { transform: translateY(-3px); box-shadow: 0 15px 35px -10px rgba(250, 204, 21, 0.15); border-color: rgba(250, 204, 21, 0.3); }
    
    .mini-card {
        background: rgba(15, 23, 42, 0.5); border: 1px solid rgba(255,255,255,0.05);
        border-radius: 12px; padding: 15px; text-align: center;
    }
    .mini-card-title { color: #64748b; font-size: 0.7rem; font-weight: 700; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 5px; }
    .mini-card-val { color: #ffffff; font-size: 1.3rem; font-weight: 800; font-variant-numeric: tabular-nums; }

    hr { border: 0; height: 1px; background: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0.15), rgba(255,255,255,0)); margin: 2rem 0; }
    .thin-divider { background: linear-gradient(to right, rgba(250,204,21,0), rgba(250,204,21,0.5), rgba(250,204,21,0)); height: 1px; width: 100%; margin: 15px 0; border: none; }
    
    section[data-testid="stSidebar"] { background-color: rgba(2, 6, 23, 0.6) !important; backdrop-filter: blur(25px); border-right: 1px solid rgba(255, 255, 255, 0.03); }
    
    .ihsg-box { display: flex; flex-direction: column; justify-content: center; text-align: right; }
    .ihsg-title { color: #cbd5e1; font-size: 0.7rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 5px; }
    .ihsg-score { font-size: 1.8rem; font-weight: 800; line-height: 1.1; margin: 0; font-variant-numeric: tabular-nums; }
    
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button { 
        background: linear-gradient(135deg, rgba(250, 204, 21, 0.15) 0%, rgba(250, 204, 21, 0.05) 100%) !important; 
        border: 1px solid rgba(250, 204, 21, 0.4) !important; 
        border-radius: 8px !important; padding: 10px 15px !important; transition: all 0.3s ease;
    }
    div.stButton > button:first-child p, div[data-testid="stFormSubmitButton"] > button p { color: #facc15 !important; font-weight: 700 !important; font-size: 0.95rem !important; letter-spacing: 1px; margin: 0; }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover { background: linear-gradient(135deg, #facc15 0%, #eab308 100%) !important; border-color: #facc15 !important; box-shadow: 0 0 20px rgba(250, 204, 21, 0.4); }
    div.stButton > button:first-child:hover p, div[data-testid="stFormSubmitButton"] > button:hover p { color: #020617 !important; }
    
    .login-header { text-align: center; color: #ffffff; font-size: 2.5rem; font-weight: 800; margin-top: 10vh; margin-bottom: 10px; text-shadow: 0 0 20px rgba(250,204,21,0.2); }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1.5. SISTEM KEAMANAN
# ==========================================
USERNAME_RAHASIA = "theo"
PASSWORD_RAHASIA = "216455"

if "akses_diberikan" not in st.session_state: st.session_state.akses_diberikan = False

if not st.session_state.akses_diberikan:
    st.markdown("<div class='login-header'>🔐 FX TERMINAL SECURED</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.9rem; margin-bottom: 30px; letter-spacing: 1px;'>INSTITUTIONAL GRADE ALGORITHMIC TRADING</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 2.5, 1])
    with col2:
        with st.form(key="login_form"):
            user_input = st.text_input("👤 Username Identification:")
            pwd_input = st.text_input("🔑 Passcode:", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("AUTHORIZE ACCESS", use_container_width=True):
                if user_input.strip().lower() == USERNAME_RAHASIA.lower() and pwd_input.strip() == PASSWORD_RAHASIA:
                    st.session_state.akses_diberikan = True
                    st.rerun()
                else: st.error("❌ Access Denied. Invalid Credentials.")
    st.stop()

# ==========================================
# 2. FUNGSI DATA (TEKNIKAL & FUNDAMENTAL)
# ==========================================
def get_waktu_wib():
    return datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d %b %Y • %H:%M WIB")

roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "NZDUSD=X": "NZD/USD", "XAUUSD=X": "GOLD (XAU/USD)"}

def format_fx(ticker, val):
    if pd.isna(val): return "-"
    if "JPY" in ticker or "XAU" in ticker: return f"{val:.3f}"
    return f"{val:.5f}"

@st.cache_data(ttl=600, show_spinner=False)
def fetch_fundamental_sentiment():
    # Menarik sentimen fundamental live dari XML Forex Factory
    sentiment = {"USD": 0, "EUR": 0, "GBP": 0, "JPY": 0, "AUD": 0, "CAD": 0, "CHF": 0, "NZD": 0, "XAU": 0}
    try:
        response = requests.get("https://nfs.faireconomy.media/ff_calendar_thisweek.xml", timeout=10)
        root = ET.fromstring(response.content)
        today_str = datetime.now(pytz.timezone('US/Eastern')).strftime("%m-%d-%Y")
        
        for event in root.findall('event'):
            if event.find('date').text != today_str: continue
            
            impact = event.find('impact').text
            currency = event.find('country').text
            actual_str, forecast_str = event.find('actual').text, event.find('forecast').text
            
            if actual_str and forecast_str and impact in ["High", "Medium"]:
                try:
                    act = float(''.join(c for c in actual_str if c.isdigit() or c == '.' or c == '-'))
                    fct = float(''.join(c for c in forecast_str if c.isdigit() or c == '.' or c == '-'))
                    multiplier = 20 if impact == "High" else 10
                    
                    if act > fct: sentiment[currency] += multiplier
                    elif act < fct: sentiment[currency] -= multiplier
                except: pass
        return sentiment
    except: return sentiment

@st.cache_data(ttl=300, show_spinner=False)
def fetch_dxy():
    try:
        df = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)
        if df.empty: return None, None, None
        df = df.ffill()
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        close_now, close_prev = float(df['Close'].iloc[-1]), float(df['Close'].iloc[-2])
        chg = close_now - close_prev
        return close_now, chg, (chg / close_prev) * 100
    except: return None, None, None

def hitung_atr(df, period=14):
    high_low = df['High'] - df['Low']
    high_close = np.abs(df['High'] - df['Close'].shift())
    low_close = np.abs(df['Low'] - df['Close'].shift())
    ranges = pd.concat([high_low, high_close, low_close], axis=1)
    return np.max(ranges, axis=1).rolling(period).mean()

def fetch_single_forex(ticker, mode_tf):
    try:
        if "15 Menit" in mode_tf: per, inv = "5d", "15m"
        elif "1 Jam" in mode_tf: per, inv = "1mo", "1h"
        elif "4 Jam" in mode_tf: per, inv = "1mo", "1h" 
        else: per, inv = "3mo", "1d" 
            
        df = yf.download(ticker, period=per, interval=inv, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        
        if "4 Jam" in mode_tf:
            df = df.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna(subset=['Close'])
            
        df = df.ffill()
        if len(df) < 20: return None
        
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['ATR'] = hitung_atr(df)
        
        delta = df['Close'].diff()
        gain, loss = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean(), (-1 * delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))
        
        close = float(df['Close'].iloc[-1])
        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA": close, 
            "RSI": round(float(df['RSI'].iloc[-1]), 2), "ATR": float(df['ATR'].iloc[-1]), 
            "PIVOT": (float(df['High'].iloc[-2]) + float(df['Low'].iloc[-2]) + float(df['Close'].iloc[-2])) / 3, 
            "EMA20": float(df['EMA20'].iloc[-1]), "UP_EMA20": close > float(df['EMA20'].iloc[-1]), 
            "MACD_BULL": float(df['MACD'].iloc[-1]) > float(df['Signal'].iloc[-1]),
            "RAW_DF": df.tail(120) 
        }
    except: return None

# ==========================================
# 4. SIDEBAR (NAVIGASI ASSET SPESIFIK)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #ffffff; font-size: 1.4rem; font-weight: 800; text-align: left; margin-bottom: 2px;'>❖ JIHAN-GHINA FX</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: left; color: #fbbf24; font-size: 0.65rem; letter-spacing: 3px; font-weight: 700; margin-bottom: 20px;'>PRO MAX v9.0</p>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 25px;'>
        <div style='font-size: 0.6rem; color: #10b981; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;'>SERVER STATUS</div>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
            <span style='font-size: 0.8rem; color: #cbd5e1;'>FX Engine</span>
            <span style='font-size: 0.75rem; color: #10b981; font-weight: 600;'>🟢 ONLINE</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    # [MODIFIKASI 1]: PEMILIHAN PAIR DI SIDEBAR
    st.markdown("<h3 style='color:#cbd5e1; font-size:0.75rem; letter-spacing:1px; margin-bottom:10px; font-weight:800; text-transform: uppercase;'>🎯 ASSET NAVIGATOR</h3>", unsafe_allow_html=True)
    pilihan_fx_nama = st.radio("Select Asset", list(nama_pairs.values()), label_visibility="collapsed")
    pilihan_fx_ticker = [k for k, v in nama_pairs.items() if v == pilihan_fx_nama][0]
    
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown("<h3 style='color:#cbd5e1; font-size:0.75rem; letter-spacing:1px; margin-bottom:10px; font-weight:800; text-transform: uppercase;'>⏱️ TIMEFRAME</h3>", unsafe_allow_html=True)
    tf_pilihan = st.selectbox("Timeframe", ["15 Menit", "1 Jam", "4 Jam", "1 Hari (Daily)"], index=3, label_visibility="collapsed")
    
    tf_berubah = False
    if tf_pilihan != st.session_state.current_tf:
        tf_berubah = True
        st.session_state.current_tf = tf_pilihan
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("📡 REFRESH DATA", use_container_width=True) or tf_berubah:
        st.session_state.scan_clicked = True
        st.cache_data.clear()
        st.session_state.raw_forex = []
        
        bar = st.progress(0, text=f"Calibrating Global Rates ({st.session_state.current_tf})...")
        for i, t in enumerate(roster_forex):
            bar.progress((i + 1) / len(roster_forex), text=f"Analyzing {nama_pairs[t]}...")
            data = fetch_single_forex(t, st.session_state.current_tf)
            if data: st.session_state.raw_forex.append(data)
            gc.collect()
            
        bar.empty()
        st.session_state.last_update = get_waktu_wib()
        
        cache_safe_data = [{k: v for k, v in item.items() if k != 'RAW_DF'} for item in st.session_state.raw_forex]
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"raw_forex": cache_safe_data, "last_update": st.session_state.last_update}, f)
        except: pass
        st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔌 DISCONNECT", use_container_width=True):
        st.session_state.akses_diberikan = False
        st.session_state.scan_clicked = False
        st.rerun()

# ==========================================
# 5. DASHBOARD UTAMA (FOKUS 1 ASSET)
# ==========================================
st.markdown("<h1>GLOBAL MACRO INTELLIGENCE</h1>", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([3.5, 1.5])
with col_h1:
    upd = st.session_state.last_update if st.session_state.last_update else "System on Standby"
    st.markdown(f"<p style='font-size: 0.95rem;'>📡 Last Sync: <span style='color:#facc15; font-weight:600;'>{upd}</span></p>", unsafe_allow_html=True)

dxy_val, dxy_chg, dxy_pct = fetch_dxy()
with col_h2:
    if dxy_val:
        w_panah = "▲" if dxy_chg >= 0 else "▼"
        w_garis = '#10b981' if dxy_chg >= 0 else '#f43f5e'
        st.markdown(f"""
        <div class="premium-card ihsg-box" style="border-right: 5px solid {w_garis}; border-left: none; padding-right: 25px; padding-top:10px; padding-bottom:10px;">
            <span class="ihsg-title">US DOLLAR INDEX (DXY)</span>
            <span class="ihsg-score" style="color: {w_garis}; font-size:1.4rem;">{dxy_val:,.3f}</span>
            <span style="color: {w_garis}; font-weight: 700; font-size: 0.75rem;">{w_panah} {dxy_chg:+,.3f} ({dxy_pct:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

if not st.session_state.scan_clicked or not st.session_state.raw_forex:
    st.info("💡 System initialized. Click 'REFRESH DATA' in the control panel to begin analysis.")
else:
    # Mengambil data Fundamental
    funda_sentiment = fetch_fundamental_sentiment()
    
    # Ekstraksi Data Spesifik Pair yang dipilih di Sidebar
    raw_target = next((item for item in st.session_state.raw_forex if item["NAMA"] == pilihan_fx_nama), None)
    
    if raw_target:
        # [MODIFIKASI 2]: SKORING GABUNGAN TEKNIKAL & FUNDAMENTAL
        skor_tech, skor_funda = 0, 0
        
        # Logika Teknikal
        if raw_target["UP_EMA20"]: skor_tech += 30
        if raw_target["MACD_BULL"]: skor_tech += 30
        if 40 <= raw_target["RSI"] <= 65: skor_tech += 40
        elif raw_target["RSI"] > 70: skor_tech -= 20
        elif raw_target["RSI"] < 30: skor_tech += 20
        
        # Logika Fundamental (Base vs Quote)
        base_curr = "XAU" if "GOLD" in pilihan_fx_nama else pilihan_fx_nama.split("/")[0][-3:]
        quote_curr = "USD" if "GOLD" in pilihan_fx_nama else pilihan_fx_nama.split("/")[1][:3]
        
        skor_funda += funda_sentiment.get(base_curr, 0)
        skor_funda -= funda_sentiment.get(quote_curr, 0)
        
        skor_total = skor_tech + skor_funda
        
        # Keputusan
        if skor_total >= 70: 
            rek, clr, desc = "STRONG BULLISH", "#10b981", f"Struktur Teknikal & Sentimen Fundamental mendukung kenaikan di {st.session_state.current_tf}. Tunggu koreksi ke area EMA20 untuk BUY."
            entry = raw_target["EMA20"] if raw_target["HARGA"] > raw_target["EMA20"] else raw_target["HARGA"]
            sl, tp = entry - (1.5 * raw_target["ATR"]), entry + (2.0 * raw_target["ATR"])
        elif skor_total <= 30: 
            rek, clr, desc = "STRONG BEARISH", "#f43f5e", f"Tekanan jual dominan dari segi Teknikal & Fundamental di {st.session_state.current_tf}. Cari pantulan harga ke area EMA20 untuk SELL."
            entry = raw_target["EMA20"] if raw_target["HARGA"] < raw_target["EMA20"] else raw_target["HARGA"]
            sl, tp = entry + (1.5 * raw_target["ATR"]), entry - (2.0 * raw_target["ATR"])
        else: 
            rek, clr, desc = "RANGE BOUND / WAIT", "#fbbf24", "Tidak ada konfirmasi tren yang kuat. Harga sedang konsolidasi. Disarankan menunggu atau scalping pendek."
            entry, sl, tp = raw_target["HARGA"], raw_target["HARGA"], raw_target["HARGA"]

        # ---------------- HEADER PAIR SPESIFIK ----------------
        st.markdown(f"<h2 style='color:#ffffff; font-weight:900; margin-bottom: 20px;'>{pilihan_fx_nama} <span style='color:#64748b; font-size:1.3rem; font-weight:600;'>| {st.session_state.current_tf}</span></h2>", unsafe_allow_html=True)
        
        c1, c2, c3, c4 = st.columns(4)
        with c1: st.markdown(f"<div class='mini-card'><div class='mini-card-title'>CURRENT PRICE</div><div class='mini-card-val' style='color:#cbd5e1;'>{format_fx(pilihan_fx_ticker, raw_target['HARGA'])}</div></div>", unsafe_allow_html=True)
        with c2: st.markdown(f"<div class='mini-card'><div class='mini-card-title'>ENTRY ZONE</div><div class='mini-card-val' style='color:#38bdf8;'>{format_fx(pilihan_fx_ticker, entry)}</div></div>", unsafe_allow_html=True)
        with c3: st.markdown(f"<div class='mini-card'><div class='mini-card-title'>TAKE PROFIT</div><div class='mini-card-val' style='color:#10b981;'>{format_fx(pilihan_fx_ticker, tp)}</div></div>", unsafe_allow_html=True)
        with c4: st.markdown(f"<div class='mini-card'><div class='mini-card-title'>STOP LOSS (ATR)</div><div class='mini-card-val' style='color:#f43f5e;'>{format_fx(pilihan_fx_ticker, sl)}</div></div>", unsafe_allow_html=True)
        
        st.markdown("<br>", unsafe_allow_html=True)

        # ---------------- ANALISA KIRI & CHART KANAN ----------------
        col_sig, col_chart = st.columns([1, 2.2])
        
        with col_sig:
            st.markdown(f"""
            <div class='premium-card' style='border: 1px solid {clr}; background: linear-gradient(180deg, rgba(15,23,42,0.6) 0%, rgba(2,6,23,0.8) 100%); height: 100%; display: flex; flex-direction: column; justify-content: center;'>
                <div style='text-align: center;'>
                    <span style='color: #64748b; font-size: 0.7rem; letter-spacing: 2px; font-weight:700;'>ALGORITHMIC VERDICT</span><br>
                    <span style='color: {clr}; font-weight: 900; font-size: 1.8rem; display: block; margin: 10px 0; letter-spacing: -0.5px;'>{rek}</span>
                    <span style='color: #94a3b8; font-size: 0.85rem; line-height: 1.4;'>{desc}</span>
                </div>
                <hr class='thin-divider' style='background: linear-gradient(to right, rgba(255,255,255,0), {clr}, rgba(255,255,255,0)); opacity: 0.3;'>
                <div style='display: flex; justify-content: space-around; text-align: center; color: #64748b; font-size: 0.7rem; font-weight: 600; letter-spacing: 1px;'>
                    <div>SCORE TECH<br><strong style='color:#ffffff; font-size:1.1rem;'>{skor_tech}/100</strong></div>
                    <div>SCORE FUNDA<br><strong style='color:#ffffff; font-size:1.1rem;'>{skor_funda:+d}</strong></div>
                    <div>RSI<br><strong style='color:#ffffff; font-size:1.1rem;'>{raw_target['RSI']}</strong></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

        with col_chart:
            if "RAW_DF" in raw_target:
                df_chart = raw_target["RAW_DF"]
                fig = go.Figure()
                
                fig.add_trace(go.Candlestick(
                    x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], 
                    name='Price Action', increasing_line_color='#10b981', increasing_fillcolor='#10b981', decreasing_line_color='#f43f5e', decreasing_fillcolor='#f43f5e'
                ))
                
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], mode='lines', line=dict(color='#0ea5e9', width=2), name='EMA 20'))
                
                fig.update_layout(
                    margin=dict(l=5, r=5, t=30, b=5), paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                    font=dict(color='#94a3b8', family='Plus Jakarta Sans'),
                    legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color='#cbd5e1')),
                    dragmode='pan', xaxis_rangeslider_visible=False, hovermode='x unified', height=380,
                    title=dict(text=f"Live Order Flow: {pilihan_fx_nama}", font=dict(size=14, color="#facc15", weight='bold'))
                )
                
                fig.update_xaxes(showgrid=False, zeroline=False, showline=False)
                fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False, side='right')
                
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})
            else:
                st.info("⚠️ Execute scan to render historical chart data.")

        # ==========================================
        # 7. KALENDER EKONOMI
        # ==========================================
        st.markdown("<hr>", unsafe_allow_html=True)
        st.markdown("<h3 style='font-size: 1.5rem; font-weight: 800; color: #ffffff;'>📰 MACROECONOMIC CALENDAR</h3>", unsafe_allow_html=True)
        st.markdown("<p style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px;'>Monitor rilis berita skala global secara real-time yang memengaruhi sentimen pasar.</p>", unsafe_allow_html=True)

        components.html(
            """
            <div id="economicCalendarWidget"></div>
            <script async type="text/javascript" data-type="calendar-widget" src="https://www.mql5.com/js/widgets/calendar/widget.js?v=1">
            {"width":"100%","height":"550","mode":"1","colorTheme":"1"}
            </script>
            """,
            height=550,
        )

st.markdown("<br><p style='text-align: center; color: #475569; font-size: 0.75rem; letter-spacing: 2px; font-weight: 600;'>⚡ JIHAN-GHINA FX ENGINE • PROPRIETARY TRADING TERMINAL v9.0</p>", unsafe_allow_html=True)
