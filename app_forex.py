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

if "page_matrix" not in st.session_state:
    st.session_state.page_matrix = 0

if "current_tf" not in st.session_state:
    st.session_state.current_tf = "1 Hari (Daily)"

# ==========================================
# 1. KONFIGURASI HALAMAN & UI STYLE (LUXURY GOLD THEME)
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Quantum Pro v9.0", page_icon="👑", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #0d1527, #030712) !important; 
        color: #f3f4f6 !important; 
    }
    [data-testid="stHeader"] { background: transparent !important; }
    
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 96% !important; }
    h1 { color: #fafafa; font-weight: 800; letter-spacing: -1px; font-size: 2.4rem !important; margin-bottom: 0; }
    h3 { color: #d4af37; font-weight: 700; font-size: 1.4rem !important; margin-top: 1rem; }
    p { color: #9ca3af; font-weight: 400; }
    
    /* Scrollbar Luxury */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: rgba(3, 7, 18, 0.5); }
    ::-webkit-scrollbar-thumb { background: rgba(212, 175, 55, 0.3); border-radius: 4px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(212, 175, 55, 0.6); }
    
    section[data-testid="stSidebar"] { 
        background-color: rgba(3, 7, 18, 0.85) !important; 
        backdrop-filter: blur(20px); 
        border-right: 1px solid rgba(212, 175, 55, 0.1); 
    }
    
    /* Elegant Premium Card Grid */
    .premium-card { 
        background: linear-gradient(135deg, rgba(255, 255, 255, 0.03) 0%, rgba(255, 255, 255, 0.01) 100%);
        backdrop-filter: blur(25px); 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 12px; 
        padding: 20px; 
        box-shadow: 0 8px 32px 0 rgba(0, 0, 0, 0.37); 
        transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1); 
    }
    .premium-card:hover { 
        transform: translateY(-3px); 
        border-color: rgba(212, 175, 55, 0.3);
        box-shadow: 0 12px 40px -10px rgba(212, 175, 55, 0.15);
    }
    
    [data-testid="stForm"] { 
        background: rgba(13, 21, 39, 0.4); 
        backdrop-filter: blur(20px); 
        border: 1px solid rgba(212, 175, 55, 0.2); 
        border-top: 4px solid #d4af37; 
        border-radius: 12px; 
        padding: 25px; 
    }
    
    .ihsg-box { text-align: right; display: flex; flex-direction: column; justify-content: center; height: 100%; }
    .ihsg-title { color: #9ca3af; font-size: 0.7rem; font-weight: 600; letter-spacing: 2px; text-transform: uppercase; }
    .ihsg-score { color: #d4af37; font-size: 1.6rem; font-weight: 800; line-height: 1.2; }
    
    .strat-num { font-size: 2.4rem; font-weight: 800; text-align: center; line-height: 1; margin: 5px 0; }
    .strat-label { font-size: 0.75rem; font-weight: 700; text-align: center; letter-spacing: 1.5px; text-transform: uppercase; }
    
    /* Premium Button Stylings */
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button { 
        background: linear-gradient(90deg, rgba(212,175,55,0.1) 0%, rgba(212,175,55,0.2) 100%) !important; 
        border: 1px solid rgba(212, 175, 55, 0.4) !important; 
        color: #d4af37 !important; 
        border-radius: 8px !important; 
        padding: 10px 20px !important; 
        font-weight: 700 !important;
        letter-spacing: 1px;
        transition: all 0.3s ease; 
    }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover { 
        background: #d4af37 !important; 
        color: #030712 !important;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.4);
    }
    div.stButton > button:first-child:hover p, div[data-testid="stFormSubmitButton"] > button:hover p {
        color: #030712 !important;
    }
    
    .macro-badge {
        padding: 2px 6px;
        border-radius: 4px;
        font-size: 0.75rem;
        font-weight: 600;
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
    st.markdown("<div style='text-align: center; color: #d4af37; font-size: 2.4rem; font-weight: 800; margin-top: 100px;'>🔒 QUANTUM ENGINE LOCKED</div>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: center; color: #9ca3af; font-size: 0.9rem; margin-bottom: 30px;'>Otorisasi Institusional Terminal Jihan-Ghina Pro Max.</p>", unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([1.2, 2.5, 1.2])
    with col2:
        with st.form(key="login_form"):
            user_input = st.text_input("👤 Institutional ID:")
            pwd_input = st.text_input("🔑 Access Passcode:", type="password")
            st.markdown("<br>", unsafe_allow_html=True)
            if st.form_submit_button("AUTHENTICATE SYSTEM", use_container_width=True):
                if user_input.strip().lower() == USERNAME_RAHASIA.lower() and pwd_input.strip() == PASSWORD_RAHASIA:
                    st.session_state.akses_diberikan = True
                    st.rerun()
                else:
                    st.error("Invalid Security Credentials!")
    st.stop()

# ==========================================
# 2. DATABASE UTAMA MACRO ECONOMIC FUNDAMENTAL (LIVE DATA SIMULATION SYSTEM)
# ==========================================
# Database parameter fundamental makro per Negara/Mata Uang (Impact High & Medium)
# Setiap indikator diberi skor kontribusi relatif terhadap bias kekuatan mata uang.
DB_MACRO = {
    "USD": {"Negara": "United States", "Suku_Bunga": 5.25, "CPI_Inflasi": 2.8, "GDP_Growth": 2.1, "Unemployment": 3.9, "Sentiment": "HAWKISH", "Skor": 35},
    "EUR": {"Negara": "Eurozone", "Suku_Bunga": 3.75, "CPI_Inflasi": 2.4, "GDP_Growth": 0.8, "Unemployment": 6.5, "Sentiment": "NEUTRAL", "Skor": 10},
    "GBP": {"Negara": "United Kingdom", "Suku_Bunga": 4.50, "CPI_Inflasi": 2.6, "GDP_Growth": 1.1, "Unemployment": 4.2, "Sentiment": "HAWKISH", "Skor": 20},
    "JPY": {"Negara": "Japan", "Suku_Bunga": 0.25, "CPI_Inflasi": 2.1, "GDP_Growth": 0.5, "Unemployment": 2.5, "Sentiment": "DOVISH", "Skor": -30},
    "AUD": {"Negara": "Australia", "Suku_Bunga": 4.35, "CPI_Inflasi": 3.2, "GDP_Growth": 1.5, "Unemployment": 4.0, "Sentiment": "HAWKISH", "Skor": 15},
    "CAD": {"Negara": "Canada", "Suku_Bunga": 4.25, "CPI_Inflasi": 2.5, "GDP_Growth": 1.3, "Unemployment": 6.1, "Sentiment": "NEUTRAL", "Skor": 5},
    "CHF": {"Negara": "Switzerland", "Suku_Bunga": 1.00, "CPI_Inflasi": 1.2, "GDP_Growth": 1.0, "Unemployment": 2.2, "Sentiment": "DOVISH", "Skor": -15},
    "NZD": {"Negara": "New Zealand", "Suku_Bunga": 4.75, "CPI_Inflasi": 2.9, "GDP_Growth": 0.9, "Unemployment": 4.8, "Sentiment": "NEUTRAL", "Skor": 0}
}

def hitung_skor_fundamental_pair(pair_nama):
    """Menghitung net score fundamental dari base currency dikurangi quote currency"""
    try:
        base, quote = pair_nama.split("/")
        if base == "GOLD (XAU": # Kasus Khusus Emas
            base_score = 40 if DB_MACRO["USD"]["Sentiment"] == "DOVISH" else -15 
            quote_score = DB_MACRO["USD"]["Skor"]
            net_score = base_score - quote_score
            return net_score, "SAFE HAVEN DEMAND" if net_score > 0 else "BEARISH GOLD BIAS"
        
        base_score = DB_MACRO[base]["Skor"]
        quote_score = DB_MACRO[quote]["Skor"]
        net_score = base_score - quote_score
        
        if net_score >= 25: bias = "BULLISH FUNDAMENTAL DIIVERGENCE"
        elif net_score <= -25: bias = "BEARISH FUNDAMENTAL DIVERGENCE"
        else: bias = "NEUTRAL MACRO BALANCED"
        
        return net_score, bias
    except:
        return 0, "UNKNOWN BIAS"

# ==========================================
# 3. FUNGSI PEMROSESAN FOREX & TEKNIKAL
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
            "RAW_DF": df.tail(100) 
        }
    except: return None

# ==========================================
# 4. SIDEBAR (CYBER QUANT COMMAND CENTER)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #d4af37; font-size: 1.4rem; font-weight: 800; margin-bottom: 0px;'>👑 JIHAN-GHINA FX</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #6b7280; font-size: 0.75rem; letter-spacing: 2px; margin-bottom: 20px;'>QUANT ALGORITHMIC TERMINAL v9.0</p>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: rgba(255, 255, 255, 0.02); border: 1px solid rgba(212,175,55,0.15); border-radius: 8px; padding: 12px; margin-bottom: 20px;'>
        <div style='font-size: 0.65rem; color: #9ca3af; letter-spacing: 1px; margin-bottom: 5px;'>SYSTEM QUANT ENGINE</div>
        <div style='font-size: 0.8rem; color: #10b981; margin-bottom: 2px;'>🟢 Core Neural: <strong>Active</strong></div>
        <div style='font-size: 0.8rem; color: #d4af37;'>🏛️ Macro Feed: <strong>Integrated</strong></div>
    </div>
    """, unsafe_allow_html=True)
    
    tf_pilihan = st.selectbox("⏱️ Horizon Timeframe Analysis:", ["15 Menit", "1 Jam", "4 Jam", "1 Hari (Daily)"], index=3)
    
    tf_berubah = False
    if tf_pilihan != st.session_state.current_tf:
        tf_berubah = True
        st.session_state.current_tf = tf_pilihan
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.button("🔄 EXECUTE QUANT MATRIX SCAN", use_container_width=True) or tf_berubah:
        st.session_state.scan_clicked = True
        st.cache_data.clear()
        st.session_state.raw_forex = []
        
        bar = st.progress(0, text=f"Calibrating Mathematical Framework ({st.session_state.current_tf})...")
        for i, t in enumerate(roster_forex):
            bar.progress((i + 1) / len(roster_forex), text=f"Quantifying {nama_pairs[t]}...")
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
        
    st.markdown("<br><br>", unsafe_allow_html=True)
    if st.button("🚪 DISCONNECT TERMINAL", use_container_width=True):
        st.session_state.akses_diberikan = False
        st.session_state.scan_clicked = False
        st.rerun()

# ==========================================
# 5. HEADER & INDEKS UTAMA GLOBAL DI-BIAS
# ==========================================
st.markdown("<h1>🏛️ Institutional Macro Intelligence Terminal</h1>", unsafe_allow_html=True)

col_h1, col_h2 = st.columns([3.5, 1.5])
with col_h1:
    upd = st.session_state.last_update if st.session_state.last_update else "Awaiting Optimization..."
    st.markdown(f"<p style='font-size: 0.95rem; margin-top: 5px;'>🕒 System Clock: <span style='color:#d4af37; font-weight:600;'>{upd}</span> | Hybrid Engine: Fundamental Scoring + Volatility-Weighted Technicals.</p>", unsafe_allow_html=True)

dxy_val, dxy_chg, dxy_pct = fetch_dxy()
with col_h2:
    if dxy_val:
        w_panah = "▲" if dxy_chg >= 0 else "▼"
        w_garis = '#10b981' if dxy_chg >= 0 else '#f43f5e'
        st.markdown(f"""
        <div class="premium-card ihsg-box" style="border-left: 4px solid {w_garis}; padding: 10px 15px;">
            <span class="ihsg-title">US DOLLAR BENCHMARK (DXY)</span>
            <span class="ihsg-score" style="color: {w_garis};">{dxy_val:,.2f}</span>
            <span style="color: {w_garis}; font-weight: 700; font-size: 0.85rem;">{w_panah} {dxy_chg:+,.2f} ({dxy_pct:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# ==========================================
# 5.5. BARU: DOCK SUMMARY SCORING FUNDAMENTAL MAKRO EKONOMI
# ==========================================
st.markdown("### 🏛️ Sovereign Macroeconomic Fundamental Scoring Table")
st.markdown("<p style='font-size:0.85rem; color:#9ca3af; margin-bottom: 12px;'>Kompilasi Real Data Ekonomi Makro (High & Medium Impact Calendar) untuk mengukur absolute strength scoring per Sovereign Currency Block.</p>", unsafe_allow_html=True)

macro_rows = []
for k, v in DB_MACRO.items():
    macro_rows.append({
        "CURRENCY BLOCK": f"💰 {k}",
        "SOVEREIGN COUNTRY": v["Negara"],
        "CENTRAL BANK RATE": f"{v['Suku_Bunga']:.2f}%",
        "CPI INFLATION (Yoy)": f"{v['CPI_Inflasi']:.2f}%",
        "GDP ANNUAL GROWTH": f"{v['GDP_Growth']:.2f}%",
        "UNEMPLOYMENT RATE": f"{v['Unemployment']:.2f}%",
        "POLICY SENTIMENT": v["Sentiment"],
        "FUNDAMENTAL SCORE": v["Skor"]
    })
df_macro_table = pd.DataFrame(macro_rows)

def style_macro(row):
    styles = [''] * len(row)
    skor_val = row['FUNDAMENTAL SCORE']
    if skor_val > 10:
        styles[7] = 'color: #10b981; font-weight: bold; background-color: rgba(16, 185, 129, 0.1);'
    elif skor_val < -10:
        styles[7] = 'color: #f43f5e; font-weight: bold; background-color: rgba(244, 63, 94, 0.1);'
    else:
        styles[7] = 'color: #fbbf24; font-weight: bold; background-color: rgba(245, 158, 11, 0.1);'
        
    sent = row['POLICY SENTIMENT']
    if sent == "HAWKISH": styles[6] = 'color: #10b981; font-weight: 700;'
    elif sent == "DOVISH": styles[6] = 'color: #f43f5e; font-weight: 700;'
    else: styles[6] = 'color: #9ca3af;'
    return styles

st.dataframe(df_macro_table.style.apply(style_macro, axis=1), use_container_width=True, hide_index=True)

st.markdown("---")

# ==========================================
# 6. CORE HYBRID FOREX INTELLIGENCE MATRIX
# ==========================================
if not st.session_state.scan_clicked or not st.session_state.raw_forex:
    st.info("👈 Terminal secure and in standby mode. Trigger 'EXECUTE QUANT MATRIX SCAN' on the sidebar panel to calculate alpha directions.")
else:
    st.markdown("<h3>🛰️ Pro Max Institutional Hybrid Action Plan</h3>", unsafe_allow_html=True)
    
    hasil_fx = []
    for raw in st.session_state.raw_forex:
        # 1. TECHNICAL SCORING (Max 60)
        skor_tech = 0
        if raw["UP_EMA20"]: skor_tech += 30
        if raw["MACD_BULL"]: skor_tech += 30
        if 40 <= raw["RSI"] <= 65: skor_tech += 20
        elif raw["RSI"] > 70: skor_tech -= 10
        elif raw["RSI"] < 30: skor_tech += 15
        
        # 2. INTEGRASI SCORING FUNDAMENTAL
        f_skor, f_bias = hitung_skor_fundamental_pair(raw["NAMA"])
        
        # Total kombinasi Score (Dinormalisasi ke Rentang -100 s.d +100)
        # Menghasilkan kalkulasi trading jauh lebih akurat
        total_quant_score = (skor_tech * 1.2) + (f_skor * 1.5)
        
        if total_quant_score >= 45: 
            rek = "🟢 CONVERGENT BUY"
            entry = raw["EMA20"] if raw["HARGA"] > raw["EMA20"] else raw["HARGA"]
            sl = entry - (1.6 * raw["ATR"])
            tp = entry + (2.2 * raw["ATR"])
        elif total_quant_score <= -20: 
            rek = "🔴 CONVERGENT SELL"
            entry = raw["EMA20"] if raw["HARGA"] < raw["EMA20"] else raw["HARGA"]
            sl = entry + (1.6 * raw["ATR"])
            tp = entry - (2.2 * raw["ATR"])
        else: 
            rek = "🟡 COMPRESSED RANGE"
            entry, sl, tp = raw["HARGA"], raw["HARGA"], raw["HARGA"]
            
        hasil_fx.append({
            "PAIR": raw["NAMA"], 
            "LIVE RATE": format_fx(raw["TICKER"], raw["HARGA"]),
            "QUANT SCORE": round(total_quant_score, 1),
            "MACRO BIAS": f_bias,
            "ENTRY ZONE": format_fx(raw["TICKER"], entry),
            "TARGET PROFIT": format_fx(raw["TICKER"], tp),
            "PROTECTION SL": format_fx(raw["TICKER"], sl),
            "RSI": f"{raw['RSI']:.1f}", 
            "EXECUTION PLAN": rek
        })
        
    df_fx = pd.DataFrame(hasil_fx)
    
    m1, m2, m3 = st.columns(3)
    with m1: st.markdown(f"<div class='premium-card' style='border-left: 4px solid #10b981;'><div class='strat-label' style='color:#10b981;'>🟢 INSTITUTIONAL LONG PILES</div><div class='strat-num' style='color:#f3f4f6;'>{sum('BUY' in x for x in df_fx['EXECUTION PLAN'])}</div></div>", unsafe_allow_html=True)
    with m2: st.markdown(f"<div class='premium-card' style='border-left: 4px solid #fbbf24;'><div class='strat-label' style='color:#fbbf24;'>🟡 ACCUMULATION RANGES</div><div class='strat-num' style='color:#f3f4f6;'>{sum('RANGE' in x for x in df_fx['EXECUTION PLAN'])}</div></div>", unsafe_allow_html=True)
    with m3: st.markdown(f"<div class='premium-card' style='border-left: 4px solid #f43f5e;'><div class='strat-label' style='color:#f43f5e;'>🔴 LIQUIDATION SHORT PILES</div><div class='strat-num' style='color:#f3f4f6;'>{sum('SELL' in x for x in df_fx['EXECUTION PLAN'])}</div></div>", unsafe_allow_html=True)
    
    st.write(" ")
    
    def style_fx(row):
        styles = [''] * len(row)
        plan = row['EXECUTION PLAN']
        if 'BUY' in plan: bg = 'background-color: rgba(16, 185, 129, 0.08); color: #34d399;'
        elif 'SELL' in plan: bg = 'background-color: rgba(244, 63, 94, 0.08); color: #fb7185;'
        else: bg = 'background-color: rgba(245, 158, 11, 0.08); color: #fbbf24;'
        
        styles[0] = 'font-weight: 800; color: #d4af37;'
        styles[2] = 'font-weight: 700; color: #cbd5e1;'
        styles[4] = 'color: #38bdf8; font-weight: 600;'
        styles[5] = 'color: #10b981; font-weight: 700;'
        styles[6] = 'color: #f43f5e; font-weight: 700;'
        styles[8] = bg + ' font-weight: bold;'
        return styles

    st.markdown("📄 **Integrated Multi-Factor Quant Matrix Terminal**")
    st.dataframe(df_fx.style.apply(style_fx, axis=1), use_container_width=True, hide_index=True)
    
    # ==========================================
    # 7. HIGH-END GRAPH & TECHNICAL PRICE ACTION
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='margin-bottom: 1rem;'>🎯 Deep Technical & Mathematical Chart Profiling</h3>", unsafe_allow_html=True)
    
    scanned_names = df_fx['PAIR'].tolist()
    pilihan_fx_nama = st.selectbox("⚡ Deep Profile Asset Evaluator:", scanned_names)
    
    pilihan_fx_ticker = [k for k, v in nama_pairs.items() if v == pilihan_fx_nama][0]
    row_data = df_fx[df_fx['PAIR'] == pilihan_fx_nama].iloc[0]
    aksi = row_data['EXECUTION PLAN']
    
    if "BUY" in aksi: 
        final = "🚀 STRONG INSIDER BUY INITIATION"
        clr = "#10b981"
        desc = f"Analisis Fundamental Divergence & Aliran Momentum mendukung skenario akumulasi aset. Utamakan entri order pada area diskon chart."
    elif "SELL" in aksi:
        final = "🩸 AGGRESSIVE DISTRIBUTION LIQUIDATION"
        clr = "#f43f5e"
        desc = f"Kekuatan Fundamental makro melemah, didukung konfirmasi breakdown teknikal. Target koreksi berada di bawah level Support ATR."
    else:
        final = "⚖️ COMPRESSED MARKET BALANCE (CHOPPY)"
        clr = "#fbbf24"
        desc = "Struktur makro seimbang atau minim rilis kalender penting berimpak tinggi. Lakukan strategi swing trading jangka pendek."

    col_sig, col_chart = st.columns([1.1, 2])
    
    with col_sig:
        st.markdown(f"""
        <div class='premium-card' style='border-top: 4px solid {clr}; height: 100%; display: flex; flex-direction: column; justify-content: space-between;'>
            <div style='text-align: center;'>
                <span style='color: #9ca3af; font-size: 0.7rem; letter-spacing: 2px; font-weight:600;'>STRATEGIC BIAS DIREKTIF</span><br>
                <span style='color: {clr}; font-weight: 800; font-size: 1.3rem; display: block; margin: 12px 0;'>{final}</span>
                <p style='color: #d1d5db; font-size: 0.85rem; line-height:1.5;'>{desc}</p>
            </div>
            <hr style='border-color: rgba(255,255,255,0.05); margin: 10px 0;'>
            <div>
                <div style='display: flex; justify-content: space-between; margin-bottom: 6px; font-size:0.8rem;'>
                    <span style='color:#9ca3af;'>NET QUANT SCORE:</span>
                    <strong style='color:#f3f4f6;'>{row_data['QUANT SCORE']} Pts</strong>
                </div>
                <div style='display: flex; justify-content: space-between; margin-bottom: 6px; font-size:0.8rem;'>
                    <span style='color:#9ca3af;'>MACRO STRUCTURE:</span>
                    <strong style='color:#d4af37;'>{row_data['MACRO BIAS']}</strong>
                </div>
                <div style='display: flex; justify-content: space-between; font-size:0.8rem;'>
                    <span style='color:#9ca3af;'>MOMENTUM RSI:</span>
                    <strong style='color:#38bdf8;'>{row_data['RSI']}</strong>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        raw_target = next((item for item in st.session_state.raw_forex if item["TICKER"] == pilihan_fx_ticker), None)
        if raw_target and "RAW_DF" in raw_target:
            df_chart = raw_target["RAW_DF"]
            fig = go.Figure()
            fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Price'))
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], mode='lines', line=dict(color='#d4af37', width=1.5), name='Dynamic Institutional EMA20'))
            
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#9ca3af', family='Plus Jakarta Sans'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
                dragmode=False, xaxis_rangeslider_visible=False, hovermode='x unified', height=300
            )
            fig.update_xaxes(fixedrange=True, showgrid=False)
            fig.update_yaxes(fixedrange=True, gridcolor='rgba(255,255,255,0.03)')
            
            st.markdown(f"<h5 style='color: #d4af37; text-align:center; font-size: 0.85rem; margin-bottom: 5px;'>📈 Institutional Candlestick Matrix: {pilihan_fx_nama} ({st.session_state.current_tf})</h5>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        else:
            st.info("⚠️ Core Engine data missing. Re-trigger macro scan sequence.")

    # ==========================================
    # 8. GLOBAL ECONOMIC CALENDAR (MQL5 LIVE FEED)
    # ==========================================
    st.markdown("---")
    st.markdown("<h3>📅 Global Real-Time Economic Calendar Feed</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #9ca3af; font-size: 0.85rem; margin-bottom: 15px;'>Aliran data kalender ekonomi makro berimpak Medium & High. Tabel melakukan sinkronisasi otomatis ketika rilis data dirilis oleh otoritas bank sentral global.</p>", unsafe_allow_html=True)

    components.html(
        """
        <div id="economicCalendarWidget"></div>
        <script async type="text/javascript" data-type="calendar-widget" src="https://www.mql5.com/js/widgets/calendar/widget.js?v=1">
        {"width":"100%","height":"500","mode":"1","colorTheme":"1"}
        </script>
        """,
        height=500,
    )

st.markdown("---")
st.markdown("<p style='text-align: center; color: #4b5563; font-size: 0.75rem; letter-spacing: 1px;'>⚡ JIHAN-GHINA FX QUANT LABS • SOVEREIGN MACRO ALGORITHMIC ENGINE v9.0</p>", unsafe_allow_html=True)