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
st.set_page_config(page_title="JIHAN-GHINA FX Pro Max v8.9", page_icon="💱", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    
    /* Global Typography & Background */
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #1e1b4b, #020617, #000000) !important; 
        color: #f8fafc !important; 
    }
    [data-testid="stHeader"] { background: transparent !important; }
    .block-container { padding-top: 1.5rem; padding-bottom: 2.5rem; max-width: 96% !important; }
    
    /* Scrollbar Sleek */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.2); }
    ::-webkit-scrollbar-thumb { background: rgba(250, 204, 21, 0.4); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(250, 204, 21, 0.8); }
    
    /* Headings & Texts */
    h1 { color: #ffffff; font-weight: 800; letter-spacing: -1px; font-size: 2.4rem !important; margin-bottom: 0; text-shadow: 0 0 20px rgba(255,255,255,0.1); }
    p { color: #94a3b8; font-weight: 300; line-height: 1.6; }
    
    /* Glassmorphism Cards */
    .premium-card { 
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.6), rgba(15, 23, 42, 0.4));
        backdrop-filter: blur(20px); 
        -webkit-backdrop-filter: blur(20px);
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-top: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; 
        padding: 20px; 
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); 
        transition: transform 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275), box-shadow 0.4s ease;
    }
    .premium-card:hover { 
        transform: translateY(-5px) scale(1.01); 
        box-shadow: 0 20px 40px -15px rgba(250, 204, 21, 0.15); 
        border-color: rgba(250, 204, 21, 0.3); 
    }
    
    /* Gradient Divider */
    hr {
        border: 0;
        height: 1px;
        background: linear-gradient(to right, rgba(255,255,255,0), rgba(255,255,255,0.15), rgba(255,255,255,0));
        margin: 2rem 0;
    }
    .thin-divider {
        background: linear-gradient(to right, rgba(250,204,21,0), rgba(250,204,21,0.5), rgba(250,204,21,0));
        height: 1px; width: 100%; margin: 15px 0; border: none;
    }
    
    /* Sidebar & Forms */
    section[data-testid="stSidebar"] { 
        background-color: rgba(2, 6, 23, 0.6) !important; 
        backdrop-filter: blur(25px); 
        border-right: 1px solid rgba(255, 255, 255, 0.03); 
    }
    [data-testid="stForm"] {
        background: rgba(15, 23, 42, 0.6); backdrop-filter: blur(20px); 
        border: 1px solid rgba(255, 255, 255, 0.05); border-left: 4px solid #facc15;
        border-radius: 12px; padding: 25px; box-shadow: 0 15px 35px -10px rgba(0,0,0,0.6);
    }
    
    /* Custom Elements */
    .ihsg-box { display: flex; flex-direction: column; justify-content: center; text-align: right; }
    .ihsg-title { color: #cbd5e1; font-size: 0.7rem; font-weight: 700; letter-spacing: 2px; text-transform: uppercase; margin-bottom: 5px; }
    .ihsg-score { font-size: 1.8rem; font-weight: 800; line-height: 1.1; margin: 0; font-variant-numeric: tabular-nums; }
    
    .strat-num { font-size: 2.5rem; font-weight: 800; margin: 0; line-height: 1; text-align: center; font-variant-numeric: tabular-nums; }
    .strat-label { font-size: 0.75rem; font-weight: 700; text-align: center; letter-spacing: 1.5px; text-transform: uppercase; margin-bottom: 8px; }
    
    /* Buttons */
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button { 
        background: linear-gradient(135deg, rgba(250, 204, 21, 0.15) 0%, rgba(250, 204, 21, 0.05) 100%) !important; 
        border: 1px solid rgba(250, 204, 21, 0.4) !important; 
        border-radius: 8px !important; padding: 10px 15px !important; transition: all 0.3s ease;
    }
    div.stButton > button:first-child p, div[data-testid="stFormSubmitButton"] > button p {
        color: #facc15 !important; font-weight: 700 !important; font-size: 0.95rem !important; letter-spacing: 1px; margin: 0;
    }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover { 
        background: linear-gradient(135deg, #facc15 0%, #eab308 100%) !important; 
        border-color: #facc15 !important;
        box-shadow: 0 0 20px rgba(250, 204, 21, 0.4); 
    }
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
                    if hasattr(st, 'rerun'): st.rerun()
                    else: st.experimental_rerun()
                else: st.error("❌ Access Denied. Invalid Credentials.")
    st.stop()

# ==========================================
# 2. FUNGSI PEMROSESAN FOREX
# ==========================================
def get_waktu_wib():
    return datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d %b %Y • %H:%M WIB")

roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "NZDUSD=X": "NZD/USD", "XAUUSD=X": "GOLD (XAU/USD)"}

def format_fx(ticker, val):
    if pd.isna(val): return "-"
    if "JPY" in ticker or "XAU" in ticker: return f"{val:.3f}"
    return f"{val:.5f}" # Presisi profesional

@st.cache_data(ttl=300, show_spinner=False)
def fetch_dxy():
    try:
        df = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)
        if df.empty: return None, None, None
        df = df.ffill()
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
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
            "UP_EMA20": close > ema20, "MACD_BULL": macd_val > macd_sig,
            "RAW_DF": df.tail(120) 
        }
    except: return None

# ==========================================
# 4. SIDEBAR (CYBER COMMAND CENTER)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #ffffff; font-size: 1.4rem; font-weight: 800; text-align: left; margin-bottom: 2px;'>❖ JIHAN-GHINA FX</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: left; color: #fbbf24; font-size: 0.65rem; letter-spacing: 3px; font-weight: 700; margin-bottom: 20px;'>PRO MAX v8.9</p>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: rgba(16, 185, 129, 0.1); border: 1px solid rgba(16, 185, 129, 0.3); border-radius: 8px; padding: 12px; margin-bottom: 25px;'>
        <div style='font-size: 0.6rem; color: #10b981; letter-spacing: 1.5px; text-transform: uppercase; font-weight: 700; margin-bottom: 8px;'>SERVER STATUS</div>
        <div style='display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;'>
            <span style='font-size: 0.8rem; color: #cbd5e1;'>FX Engine</span>
            <span style='font-size: 0.75rem; color: #10b981; font-weight: 600;'>🟢 ONLINE</span>
        </div>
        <div style='display: flex; justify-content: space-between; align-items: center;'>
            <span style='font-size: 0.8rem; color: #cbd5e1;'>Data Feed</span>
            <span style='font-size: 0.75rem; color: #38bdf8; font-weight: 600;'>⚡ SYNCED</span>
        </div>
    </div>
    """, unsafe_allow_html=True)
    
    tf_pilihan = st.selectbox("⏱️ Timeframe Analysis", ["15 Menit", "1 Jam", "4 Jam", "1 Hari (Daily)"], index=3)
    
    tf_berubah = False
    if tf_pilihan != st.session_state.current_tf:
        tf_berubah = True
        st.session_state.current_tf = tf_pilihan
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("📡 EXECUTE SCAN", use_container_width=True) or tf_berubah:
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
        if hasattr(st, 'rerun'): st.rerun()
        else: st.experimental_rerun()
        
    st.markdown("<br>", unsafe_allow_html=True)
    if st.button("🔌 DISCONNECT", use_container_width=True):
        st.session_state.akses_diberikan = False
        st.session_state.scan_clicked = False
        if hasattr(st, 'rerun'): st.rerun()
        else: st.experimental_rerun()

# ==========================================
# 5. HEADER & MATRIKS UTAMA
# ==========================================
st.markdown("<h1>GLOBAL MACRO INTELLIGENCE</h1>", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([3.5, 1.5])
with col_h1:
    upd = st.session_state.last_update if st.session_state.last_update else "System on Standby"
    st.markdown(f"<p style='font-size: 0.95rem;'>📡 Last Sync: <span style='color:#facc15; font-weight:600;'>{upd}</span><br>Algorithmic trend detection utilizing Dynamic ATR Volatility & Momentum.</p>", unsafe_allow_html=True)

dxy_val, dxy_chg, dxy_pct = fetch_dxy()
with col_h2:
    if dxy_val:
        w_panah = "▲" if dxy_chg >= 0 else "▼"
        w_garis = '#10b981' if dxy_chg >= 0 else '#f43f5e'
        st.markdown(f"""
        <div class="premium-card ihsg-box" style="border-right: 5px solid {w_garis}; border-left: none; padding-right: 25px;">
            <span class="ihsg-title">US DOLLAR INDEX (DXY)</span>
            <span class="ihsg-score" style="color: {w_garis};">{dxy_val:,.3f}</span>
            <span style="color: {w_garis}; font-weight: 700; font-size: 0.85rem; letter-spacing: 1px;">{w_panah} {dxy_chg:+,.3f} ({dxy_pct:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("<hr>", unsafe_allow_html=True)

if not st.session_state.scan_clicked or not st.session_state.raw_forex:
    st.info("💡 System initialized. Click 'EXECUTE SCAN' in the control panel to begin market analysis.")
else:
    st.markdown("<h3 style='font-size: 1.5rem; font-weight: 800; color: #ffffff;'>⚡ ACTION PLAN MATRIX</h3>", unsafe_allow_html=True)
    
    hasil_fx = []
    for raw in st.session_state.raw_forex:
        skor = 0
        if raw["UP_EMA20"]: skor += 30
        if raw["MACD_BULL"]: skor += 30
        
        if 40 <= raw["RSI"] <= 65: skor += 40
        elif raw["RSI"] > 70: skor -= 20
        elif raw["RSI"] < 30: skor += 20
        
        if skor >= 70: 
            rek = "🟢 LONG"
            entry = raw["EMA20"] if raw["HARGA"] > raw["EMA20"] else raw["HARGA"]
            sl = entry - (1.5 * raw["ATR"])
            tp = entry + (2.0 * raw["ATR"])
        elif skor <= 30: 
            rek = "🔴 SHORT"
            entry = raw["EMA20"] if raw["HARGA"] < raw["EMA20"] else raw["HARGA"]
            sl = entry + (1.5 * raw["ATR"])
            tp = entry - (2.0 * raw["ATR"])
        else: 
            rek = "🟡 WAIT"
            entry, sl, tp = raw["HARGA"], raw["HARGA"], raw["HARGA"]
            
        hasil_fx.append({
            "ASSET": raw["NAMA"], 
            "CURRENT PRICE": format_fx(raw["TICKER"], raw["HARGA"]),
            "ENTRY ZONE": format_fx(raw["TICKER"], entry),
            "TARGET (TP)": format_fx(raw["TICKER"], tp),
            "RISK (SL)": format_fx(raw["TICKER"], sl),
            "PIVOT": format_fx(raw["TICKER"], raw["PIVOT"]),
            "RSI": f"{raw['RSI']:.1f}", 
            "SIGNAL": rek
        })
        
    df_fx = pd.DataFrame(hasil_fx)
    
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='premium-card' style='border-top: 3px solid #10b981;'><div class='strat-label' style='color:#34d399;'>BULLISH BIAS</div><div class='strat-num' style='color:#ffffff;'>{sum('LONG' in x for x in df_fx['SIGNAL'])}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='premium-card' style='border-top: 3px solid #fbbf24;'><div class='strat-label' style='color:#fbbf24;'>NEUTRAL / CHOPPY</div><div class='strat-num' style='color:#ffffff;'>{sum('WAIT' in x for x in df_fx['SIGNAL'])}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='premium-card' style='border-top: 3px solid #f43f5e;'><div class='strat-label' style='color:#fb7185;'>BEARISH BIAS</div><div class='strat-num' style='color:#ffffff;'>{sum('SHORT' in x for x in df_fx['SIGNAL'])}</div></div>", unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    def style_fx(row):
        styles = []
        if 'LONG' in row['SIGNAL']: bg = 'background-color: rgba(16, 185, 129, 0.15); color: #34d399; font-weight: 800;'
        elif 'SHORT' in row['SIGNAL']: bg = 'background-color: rgba(244, 63, 94, 0.15); color: #fb7185; font-weight: 800;'
        else: bg = 'background-color: rgba(250, 204, 21, 0.1); color: #fbbf24; font-weight: 800;'
        
        for c, val in row.items():
            if c == 'ASSET': styles.append('font-weight: 900; color: #ffffff;')
            elif c == 'TARGET (TP)': styles.append('color: #10b981; font-weight: 700;') 
            elif c == 'RISK (SL)': styles.append('color: #f43f5e; font-weight: 700;')  
            elif c == 'ENTRY ZONE': styles.append('color: #38bdf8; font-weight: 700;')  
            elif c == 'PIVOT': styles.append('color: #64748b;')
            elif c == 'CURRENT PRICE': styles.append('font-weight: 600; color: #cbd5e1;')
            elif c == 'SIGNAL': styles.append(bg)
            elif c == 'RSI':
                try:
                    r = float(val)
                    if r >= 70: styles.append('color: #f43f5e; font-weight: 800;') 
                    elif r <= 30: styles.append('color: #10b981; font-weight: 800;') 
                    else: styles.append('color: #94a3b8;')
                except: styles.append('')
            else: styles.append('')
        return styles

    st.dataframe(df_fx.style.apply(style_fx, axis=1), use_container_width=True, hide_index=True)
    
    # ==========================================
    # 6. MASTERPIECE FX SIGNAL & PLOTLY CHART
    # ==========================================
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 1.5rem; font-weight: 800; color: #ffffff;'>🎯 TECHNICAL VALIDATION & PRICE ACTION</h3>", unsafe_allow_html=True)
    
    scanned_names = df_fx['ASSET'].tolist()
    pilihan_fx_nama = st.selectbox("Select Asset for Deep Validation:", scanned_names)
    
    pilihan_fx_ticker = [k for k, v in nama_pairs.items() if v == pilihan_fx_nama][0]
    
    row_data = df_fx[df_fx['ASSET'] == pilihan_fx_nama].iloc[0]
    aksi = row_data['SIGNAL']
    
    if "LONG" in aksi: 
        final = "STRONG BULLISH"
        clr = "#10b981"
        desc = f"Momentum analysis indicates upward structure on {st.session_state.current_tf}. Seek entries on pullbacks to EMA20."
    elif "SHORT" in aksi:
        final = "STRONG BEARISH"
        clr = "#f43f5e"
        desc = f"Selling pressure dictates structure on {st.session_state.current_tf}. Seek entries on rallies to EMA20."
    else:
        final = "RANGE BOUND"
        clr = "#fbbf24"
        desc = "Asset is experiencing consolidation. Suggest remaining flat or trading extreme ranges (scalping)."

    col_sig, col_chart = st.columns([1, 2.2])
    
    with col_sig:
        st.markdown(f"""
        <div class='premium-card' style='border: 1px solid {clr}; background: linear-gradient(180deg, rgba(15,23,42,0.6) 0%, rgba(2,6,23,0.8) 100%); height: 100%; display: flex; flex-direction: column; justify-content: center;'>
            <div style='text-align: center;'>
                <span style='color: #64748b; font-size: 0.7rem; letter-spacing: 2px; font-weight:700;'>ALGORITHMIC VERDICT</span><br>
                <span style='color: {clr}; font-weight: 900; font-size: 1.7rem; display: block; margin: 15px 0; letter-spacing: -0.5px;'>{final}</span>
                <span style='color: #94a3b8; font-size: 0.85rem; line-height: 1.4;'>{desc}</span>
            </div>
            <hr class='thin-divider' style='background: linear-gradient(to right, rgba(255,255,255,0), {clr}, rgba(255,255,255,0)); opacity: 0.3;'>
            <div style='display: flex; justify-content: space-around; text-align: center; color: #64748b; font-size: 0.75rem; font-weight: 600; letter-spacing: 1px;'>
                <div>RSI<br><strong style='color:#ffffff; font-size:1.2rem; font-weight: 800;'>{row_data['RSI']}</strong></div>
                <div>OPTIMAL ENTRY<br><strong style='color:#38bdf8; font-size:1.2rem; font-weight: 800;'>{row_data['ENTRY ZONE']}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        raw_target = next((item for item in st.session_state.raw_forex if item["TICKER"] == pilihan_fx_ticker), None)
        if raw_target and "RAW_DF" in raw_target:
            df_chart = raw_target["RAW_DF"]
            fig = go.Figure()
            
            # Candlestick Premium Colors
            fig.add_trace(go.Candlestick(
                x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], 
                name='Price Action',
                increasing_line_color='#10b981', increasing_fillcolor='#10b981',
                decreasing_line_color='#f43f5e', decreasing_fillcolor='#f43f5e'
            ))
            
            # EMA Glowing Line
            fig.add_trace(go.Scatter(
                x=df_chart.index, y=df_chart['EMA20'], mode='lines', 
                line=dict(color='#0ea5e9', width=2), name='EMA 20'
            ))
            
            fig.update_layout(
                margin=dict(l=5, r=5, t=30, b=5),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#94a3b8', family='Plus Jakarta Sans'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11, color='#cbd5e1')),
                dragmode='pan', xaxis_rangeslider_visible=False, hovermode='x unified', height=360,
                title=dict(text=f"Live Order Flow: {pilihan_fx_nama}", font=dict(size=14, color="#facc15", weight='bold'))
            )
            
            fig.update_xaxes(showgrid=False, zeroline=False, showline=False)
            fig.update_yaxes(showgrid=True, gridcolor='rgba(255,255,255,0.03)', zeroline=False, side='right')
            
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})
        else:
            st.info("⚠️ Execute scan to render historical chart data.")

    # ==========================================
    # 7. KALENDER EKONOMI (MQL5 TABLE EDITION)
    # ==========================================
    st.markdown("<hr>", unsafe_allow_html=True)
    st.markdown("<h3 style='font-size: 1.5rem; font-weight: 800; color: #ffffff;'>📰 MACROECONOMIC CALENDAR</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.9rem; margin-bottom: 20px;'>Monitor high-impact news releases (NFP, CPI, FOMC) to anticipate institutional volatility spikes.</p>", unsafe_allow_html=True)

    components.html(
        """
        <div id="economicCalendarWidget"></div>
        <script async type="text/javascript" data-type="calendar-widget" src="https://www.mql5.com/js/widgets/calendar/widget.js?v=1">
        {"width":"100%","height":"550","mode":"1","colorTheme":"1"}
        </script>
        """,
        height=550,
    )

st.markdown("<br><p style='text-align: center; color: #475569; font-size: 0.75rem; letter-spacing: 2px; font-weight: 600;'>⚡ JIHAN-GHINA FX ENGINE • PROPRIETARY TRADING TERMINAL v8.9</p>", unsafe_allow_html=True)
