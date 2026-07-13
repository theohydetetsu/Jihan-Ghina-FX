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
import streamlit.components.v1 as components # <--- TAMBAHAN UNTUK WIDGET FUNDAMENTAL

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
    if len(st.session_state.raw_forex) > 0:
        st.session_state.scan_clicked = True
    else:
        st.session_state.scan_clicked = False

if "page_matrix" not in st.session_state:
    st.session_state.page_matrix = 0

# ==========================================
# 1. KONFIGURASI HALAMAN & UI STYLE
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Pro Max v1.1", page_icon="logo.ico", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle at 50% -20%, #0f172a, #020617) !important; color: #f8fafc !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98% !important; }
    h1 { color: #f8fafc; font-weight: 900; letter-spacing: -1px; font-size: 2.2rem !important; margin-bottom: 0; }
    p { color: #94a3b8; font-weight: 300; }
    
    section[data-testid="stSidebar"] { 
        background-color: rgba(2, 6, 23, 0.75) !important; 
        backdrop-filter: blur(15px); 
        border-right: 1px solid rgba(255, 255, 255, 0.05); 
    }
    
    .premium-card { 
        background: rgba(30, 41, 59, 0.3); 
        backdrop-filter: blur(16px); 
        border: 1px solid rgba(255, 255, 255, 0.08); 
        border-radius: 10px; 
        padding: 15px; 
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); 
        transition: all 0.3s ease-in-out;
    }
    .premium-card:hover { transform: translateY(-5px); box-shadow: 0 12px 25px -5px rgba(250, 204, 21, 0.3); border-color: rgba(250, 204, 21, 0.4); }
    
    [data-testid="stForm"] {
        background: rgba(30, 41, 59, 0.3); backdrop-filter: blur(16px); 
        border: 1px solid rgba(255, 255, 255, 0.08); border-left: 5px solid #facc15;
        border-radius: 10px; padding: 20px; box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5);
    }
    
    .ihsg-box { text-align: right; display: flex; flex-direction: column; justify-content: center; height: 100%; padding: 10px 15px !important; }
    .ihsg-title { color: #94a3b8; font-size: 0.65rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; }
    .ihsg-score { color: #facc15; font-size: 1.5rem; font-weight: 900; line-height: 1.1; margin: 2px 0; }
    
    .strat-num { font-size: 2.2rem; font-weight: 900; margin: 2px 0; line-height: 1; text-align: center; }
    .strat-label { font-size: 0.75rem; font-weight: 600; text-align: center; letter-spacing: 1px; }
    
    .stDataFrame { font-size: 13px !important; }
    
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button { 
        background: rgba(250, 204, 21, 0.1) !important; border: 1px solid rgba(250, 204, 21, 0.5) !important; 
        color: #facc15 !important; border-radius: 6px !important; padding: 8px 12px !important; transition: all 0.3s ease;
    }
    div.stButton > button:first-child p, div[data-testid="stFormSubmitButton"] > button p {
        color: #facc15 !important; font-weight: 800 !important; font-size: 0.95rem !important; letter-spacing: 0.5px; margin: 0;
    }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover { 
        background: #facc15 !important; transform: scale(1.02); box-shadow: 0 0 15px rgba(250, 204, 21, 0.5); 
    }
    div.stButton > button:first-child:hover p, div[data-testid="stFormSubmitButton"] > button:hover p { color: #020617 !important; }
    
    .login-header { text-align: center; color: #facc15; font-size: 2.2rem; font-weight: 900; margin-top: 80px; margin-bottom: 5px; }

    .swipe-panel { background: rgba(56, 189, 248, 0.1); border: 1px solid #38bdf8; padding: 8px; border-radius: 6px; text-align: center; margin-bottom: 15px; }

    @media (max-width: 768px) {
        .block-container { padding-top: 1rem !important; padding-left: 0.5rem !important; padding-right: 0.5rem !important; }
        h1 { font-size: 1.3rem !important; }
        .login-header { font-size: 1.4rem !important; margin-top: 20px !important; } 
        p { font-size: 0.8rem !important; }
        .ihsg-score { font-size: 1.2rem !important; }
        .ihsg-title { font-size: 0.6rem !important; }
        .strat-num { font-size: 1.4rem !important; margin: 0px !important; }
        .strat-label { font-size: 0.6rem !important; }
        .premium-card { padding: 10px !important; }
        [data-testid="stForm"] { padding: 12px !important; }
        div.stButton > button:first-child { padding: 4px 8px !important; }
        div.stButton > button:first-child p { font-size: 0.8rem !important; }
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 1.5. SISTEM KEAMANAN
# ==========================================
USERNAME_RAHASIA = "theo"
PASSWORD_RAHASIA = "216455"

if "akses_diberikan" not in st.session_state: st.session_state.akses_diberikan = False

if not st.session_state.akses_diberikan:
    st.markdown("<div class='login-header'>🔒 FX TERMINAL TERKUNCI</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #94a3b8; font-size: 0.85rem; margin-bottom: 20px;'>Otorisasi Khusus Forex & XAU.</p>", unsafe_allow_html=True)
    col1, col2, col3 = st.columns([1, 4, 1])
    with col2:
        with st.form(key="login_form"):
            user_input = st.text_input("👤 Username:")
            pwd_input = st.text_input("🔑 Password:", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("VERIFIKASI AKSES", use_container_width=True):
                if user_input.strip().lower() == USERNAME_RAHASIA.lower() and pwd_input.strip() == PASSWORD_RAHASIA:
                    st.session_state.akses_diberikan = True
                    if hasattr(st, 'rerun'): st.rerun()
                    else: st.experimental_rerun()
                else: st.error("Akses Ditolak!")
    st.stop()

# ==========================================
# 2. FUNGSI PEMROSESAN FOREX
# ==========================================
def get_waktu_wib():
    return datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d %b %Y - %H:%M WIB")

roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "NZDUSD=X": "NZD/USD", "XAUUSD=X": "GOLD (XAU/USD)"}

def format_fx(ticker, val):
    if pd.isna(val): return "-"
    if "JPY" in ticker or "XAU" in ticker: return f"{val:.2f}"
    return f"{val:.4f}"

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
    true_range = np.max(ranges, axis=1)
    return true_range.rolling(period).mean()

def fetch_single_forex(ticker):
    try:
        df = yf.download(ticker, period="3mo", interval="1d", progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        df = df.ffill()
        
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        df['ATR'] = hitung_atr(df)
        
        delta = df['Close'].diff()
        gain = delta.clip(lower=0).ewm(alpha=1/14, min_periods=14).mean()
        loss = (-1 * delta.clip(upper=0)).ewm(alpha=1/14, min_periods=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        
        close = float(df['Close'].iloc[-1])
        ema20 = float(df['EMA20'].iloc[-1])
        atr = float(df['ATR'].iloc[-1])
        rsi = float(df['RSI'].iloc[-1])
        macd_val = float(df['MACD'].iloc[-1])
        macd_sig = float(df['Signal'].iloc[-1])
        
        prev_high = float(df['High'].iloc[-2])
        prev_low = float(df['Low'].iloc[-2])
        prev_close = float(df['Close'].iloc[-2])
        pivot = (prev_high + prev_low + prev_close) / 3
        
        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA": close, 
            "RSI": round(rsi, 2), "ATR": atr, "PIVOT": pivot, "EMA20": ema20,
            "UP_EMA20": close > ema20, "MACD_BULL": macd_val > macd_sig
        }
    except: return None

# ==========================================
# 4. SIDEBAR
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #facc15; font-size: 1.35rem; font-weight: 900; margin-bottom: 0px; text-align: left; margin-left: -5px; white-space: nowrap;'>👨‍💻 JIHAN-GHINA FX</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: left; margin-left: 20px; color: #94a3b8; font-size: 0.7rem; letter-spacing: 2px; margin-bottom: 15px;'>FOREX & COMMODITY v1.1</p>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 10px; margin-bottom: 20px; border-left: 3px solid #10b981;'>
        <div style='font-size: 0.65rem; color: #94a3b8; letter-spacing: 1px; margin-bottom: 5px;'>SYSTEM STATUS</div>
        <div style='font-size: 0.8rem; color: #10b981; margin-bottom: 2px;'>🟢 FX Engine: <strong>Online</strong></div>
        <div style='font-size: 0.8rem; color: #38bdf8;'>⚡ Live Rates: <strong>Synced</strong></div>
    </div>
    """, unsafe_allow_html=True)
    
    if st.button("🔄 SCAN MAJOR PAIRS", use_container_width=True):
        st.session_state.scan_clicked = True
        st.cache_data.clear()
        st.session_state.raw_forex = []
        
        bar = st.progress(0, text="Mengkalibrasi Harga Global...")
        for i, t in enumerate(roster_forex):
            bar.progress((i + 1) / len(roster_forex), text=f"Scanning {nama_pairs[t]}...")
            data = fetch_single_forex(t)
            if data: st.session_state.raw_forex.append(data)
            gc.collect()
            
        bar.empty()
        st.session_state.last_update = get_waktu_wib()
        
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"raw_forex": st.session_state.raw_forex, "last_update": st.session_state.last_update}, f)
        except: pass
        if hasattr(st, 'rerun'): st.rerun()
        else: st.experimental_rerun()
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 LOGOUT", use_container_width=True):
        st.session_state.akses_diberikan = False
        st.session_state.scan_clicked = False
        if hasattr(st, 'rerun'): st.rerun()
        else: st.experimental_rerun()

# ==========================================
# 5. HEADER & MATRIKS UTAMA
# ==========================================
st.markdown("<h1>🌍 Global Macro Intelligence</h1>", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([3.5, 1.5])
with col_h1:
    upd = st.session_state.last_update if st.session_state.last_update else "Standby..."
    st.markdown(f"<p style='font-size: 0.9rem;'>🕒 Update: <span style='color:#facc15;'>{upd}</span><br>Algoritma FX berbasis Volatilitas (ATR) & Momentum.</p>", unsafe_allow_html=True)

dxy_val, dxy_chg, dxy_pct = fetch_dxy()
with col_h2:
    if dxy_val:
        w_panah = "▲" if dxy_chg >= 0 else "▼"
        w_garis = '#10b981' if dxy_chg >= 0 else '#f43f5e'
        st.markdown(f"""
        <div class="premium-card ihsg-box" style="border-left: 5px solid {w_garis};">
            <span class="ihsg-title">US DOLLAR INDEX (DXY)</span>
            <span class="ihsg-score" style="color: {w_garis};">{dxy_val:,.2f}</span>
            <span style="color: {w_garis}; font-weight: 800; font-size: 0.9rem;">{w_panah} {dxy_chg:+,.2f} ({dxy_pct:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

if not st.session_state.scan_clicked or not st.session_state.raw_forex:
    st.info("👈 Sistem FX aman dan standby. Tekan '🔄 SCAN MAJOR PAIRS' di sidebar.")
else:
    st.markdown("<h3>🛰️ Pro Max FX Action Plan</h3>", unsafe_allow_html=True)
    
    hasil_fx = []
    for raw in st.session_state.raw_forex:
        skor = 0
        if raw["UP_EMA20"]: skor += 30
        if raw["MACD_BULL"]: skor += 30
        
        if 40 <= raw["RSI"] <= 65: skor += 40
        elif raw["RSI"] > 70: skor -= 20
        elif raw["RSI"] < 30: skor += 20
        
        if skor >= 70: 
            rek = "🟢 LONG (BUY)"
            entry = raw["EMA20"] if raw["HARGA"] > raw["EMA20"] else raw["HARGA"]
            sl = entry - (1.5 * raw["ATR"])
            tp = entry + (2.0 * raw["ATR"])
        elif skor <= 30: 
            rek = "🔴 SHORT (SELL)"
            entry = raw["EMA20"] if raw["HARGA"] < raw["EMA20"] else raw["HARGA"]
            sl = entry + (1.5 * raw["ATR"])
            tp = entry - (2.0 * raw["ATR"])
        else: 
            rek = "🟡 WAIT / NO TRADE"
            entry, sl, tp = raw["HARGA"], raw["HARGA"], raw["HARGA"]
            
        hasil_fx.append({
            "PAIR": raw["NAMA"], "HARGA NOW": format_fx(raw["TICKER"], raw["HARGA"]),
            "ENTRY AREA": format_fx(raw["TICKER"], entry),
            "TAKE PROFIT (TP)": format_fx(raw["TICKER"], tp),
            "STOP LOSS (SL)": format_fx(raw["TICKER"], sl),
            "PIVOT DAILY": format_fx(raw["TICKER"], raw["PIVOT"]),
            "RSI": f"{raw['RSI']:.1f}", "ACTION": rek
        })
        
    df_fx = pd.DataFrame(hasil_fx)
    
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='premium-card' style='border-left: 5px solid #10b981;'><div class='strat-label' style='color:#34d399;'>🟢 TOTAL LONG</div><div class='strat-num' style='color:#f8fafc;'>{sum('LONG' in x for x in df_fx['ACTION'])}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='premium-card' style='border-left: 5px solid #fbbf24;'><div class='strat-label' style='color:#fbbf24;'>🟡 WAIT & SEE</div><div class='strat-num' style='color:#f8fafc;'>{sum('WAIT' in x for x in df_fx['ACTION'])}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='premium-card' style='border-left: 5px solid #f43f5e;'><div class='strat-label' style='color:#fb7185;'>🔴 TOTAL SHORT</div><div class='strat-num' style='color:#f8fafc;'>{sum('SHORT' in x for x in df_fx['ACTION'])}</div></div>", unsafe_allow_html=True)
    
    st.write(" ")
    
    def style_fx(row):
        styles = []
        if 'LONG' in row['ACTION']: bg = 'background-color: rgba(16, 185, 129, 0.1); color: #34d399;'
        elif 'SHORT' in row['ACTION']: bg = 'background-color: rgba(244, 63, 94, 0.1); color: #fb7185;'
        else: bg = 'background-color: rgba(245, 158, 11, 0.1); color: #fbbf24;'
        
        for c, val in row.items():
            if c == 'PAIR': styles.append('font-weight: 900; color: #facc15;')
            elif c == 'TAKE PROFIT (TP)': styles.append('color: #10b981; font-weight: 800;') 
            elif c == 'STOP LOSS (SL)': styles.append('color: #f43f5e; font-weight: 800;')  
            elif c == 'ENTRY AREA': styles.append('color: #38bdf8; font-weight: 800;')  
            elif c == 'PIVOT DAILY': styles.append('color: #94a3b8;')
            elif c == 'ACTION': styles.append(bg)
            elif c == 'RSI':
                try:
                    r = float(val)
                    if r > 70: styles.append('color: #f43f5e; font-weight: 800;') 
                    elif r < 30: styles.append('color: #10b981; font-weight: 800;') 
                    else: styles.append('')
                except: styles.append('')
            else: styles.append('')
        return styles

    st.markdown("📄 **Forex Matrix (ATR-Based Stops)**")
    
    st.markdown("""
    <div class='swipe-panel'>
        <span style='color: #38bdf8; font-size: 0.8rem; font-weight: 600;'>↔️ INFO: Geser tabel ke Kiri/Kanan. SL & TP dihitung otomatis menggunakan formula volatilitas ATR.</span>
    </div>
    """, unsafe_allow_html=True)
    
    st.dataframe(df_fx.style.apply(style_fx, axis=1), use_container_width=True, hide_index=True)
    
    # ==========================================
    # 6. MASTERPIECE FX SIGNAL
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='color: #f8fafc; font-weight: 800; margin-bottom: 1rem;'>🎯 FX Masterpiece Signal</h3>", unsafe_allow_html=True)
    
    pilihan_fx = st.selectbox("⚡ Cek Kekuatan Trend Pair:", df_fx['PAIR'].tolist())
    
    row_data = df_fx[df_fx['PAIR'] == pilihan_fx].iloc[0]
    aksi = row_data['ACTION']
    
    if "LONG" in aksi: 
        final = "🚀 STRONG BULLISH BIAS"
        clr = "#10b981"
        desc = "Momentum dan Trend mendukung kenaikan. Fokus cari peluang BUY di area support/EMA20."
    elif "SHORT" in aksi:
        final = "🩸 STRONG BEARISH BIAS"
        clr = "#f43f5e"
        desc = "Tekanan jual dominan. Fokus cari peluang SELL saat harga pullback (naik sementara)."
    else:
        final = "⚖️ RANGE BOUND (CHOPPY)"
        clr = "#fbbf24"
        desc = "Harga sedang bolak-balik tanpa arah jelas (Sideways). Lebih baik diam (Wait & See) atau Scalping pendek."

    st.markdown(f"""
    <div class='premium-card' style='border-left: 5px solid {clr};'>
        <div style='text-align: center;'>
            <span style='color: #94a3b8; font-size: 0.75rem; letter-spacing: 2px;'>ALGORITMA REKOMENDASI</span><br>
            <span style='color: {clr}; font-weight: 900; font-size: 1.8rem; display: block; margin: 10px 0;'>{final}</span>
            <span style='color: #cbd5e1; font-size: 0.85rem;'>{desc}</span>
        </div>
        <hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>
        <div style='display: flex; justify-content: space-around; text-align: center; color: #94a3b8; font-size: 0.8rem;'>
            <div>RSI<br><strong style='color:#f8fafc; font-size:1rem;'>{row_data['RSI']}</strong></div>
            <div>PIVOT POINT<br><strong style='color:#f8fafc; font-size:1rem;'>{row_data['PIVOT DAILY']}</strong></div>
            <div>ENTRY PLAN<br><strong style='color:#38bdf8; font-size:1rem;'>{row_data['ENTRY AREA']}</strong></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ==========================================
    # 7. KALENDER EKONOMI (FUNDAMENTAL DATA)
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='color: #f8fafc; font-weight: 800; margin-bottom: 1rem;'>📅 Global Economic Calendar</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 15px;'>Jadwal rilis data fundamental (NFP, CPI, Suku Bunga) untuk mendeteksi lonjakan volatilitas pasar.</p>", unsafe_allow_html=True)

    # Widget Kalender Ekonomi dari TradingView (Real-time & Gratis)
    components.html(
        """
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {
          "colorTheme": "dark",
          "isTransparent": true,
          "width": "100%",
          "height": "500",
          "locale": "id",
          "importanceFilter": "-1,0,1",
          "currencyFilter": "USD,EUR,GBP,JPY,AUD,CAD,CHF,NZD"
          }
          </script>
        </div>
        """,
        height=500,
    )

st.markdown("---")
st.markdown("<p style='text-align: center; color: #475569; font-size: 0.75rem;'>⚡ JIHAN-GHINA FX ENGINE • ALGORITHMIC TERMINAL v1.1</p>", unsafe_allow_html=True)
