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
import streamlit.components.v1 as components # Modul untuk Kalender Ekonomi

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
# 1. KONFIGURASI HALAMAN & UI STYLE
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Pro Max v8.8", page_icon="💱", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;800;900&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    
    [data-testid="stAppViewContainer"] { background: radial-gradient(circle at 50% -20%, #0f172a, #020617) !important; color: #f8fafc !important; }
    [data-testid="stHeader"] { background: transparent !important; }
    
    .block-container { padding-top: 1.5rem; padding-bottom: 2rem; max-width: 98% !important; }
    h1 { color: #f8fafc; font-weight: 900; letter-spacing: -1px; font-size: 2.2rem !important; margin-bottom: 0; }
    p { color: #94a3b8; font-weight: 300; }
    
    /* Scrollbar Global & Tabel HTML Native */
    ::-webkit-scrollbar { width: 8px; height: 10px; }
    ::-webkit-scrollbar-track { background: rgba(15, 23, 42, 0.5); border-radius: 10px; }
    ::-webkit-scrollbar-thumb { background: rgba(250, 204, 21, 0.5); border-radius: 10px; border: 2px solid rgba(15, 23, 42, 0.5); }
    ::-webkit-scrollbar-thumb:hover { background: rgba(250, 204, 21, 1); }
    
    section[data-testid="stSidebar"] { background-color: rgba(2, 6, 23, 0.75) !important; backdrop-filter: blur(15px); border-right: 1px solid rgba(255, 255, 255, 0.05); }
    .premium-card { background: rgba(30, 41, 59, 0.3); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 10px; padding: 15px; box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.3); transition: all 0.3s ease-in-out; }
    .premium-card:hover { transform: translateY(-5px); box-shadow: 0 12px 25px -5px rgba(250, 204, 21, 0.3); border-color: rgba(250, 204, 21, 0.4); }
    [data-testid="stForm"] { background: rgba(30, 41, 59, 0.3); backdrop-filter: blur(16px); border: 1px solid rgba(255, 255, 255, 0.08); border-left: 5px solid #facc15; border-radius: 10px; padding: 20px; box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); }
    
    .ihsg-box { text-align: right; display: flex; flex-direction: column; justify-content: center; height: 100%; padding: 10px 15px !important; }
    .ihsg-title { color: #94a3b8; font-size: 0.65rem; font-weight: 600; letter-spacing: 1.5px; text-transform: uppercase; }
    .ihsg-score { color: #facc15; font-size: 1.5rem; font-weight: 900; line-height: 1.1; margin: 2px 0; }
    .strat-num { font-size: 2.2rem; font-weight: 900; margin: 2px 0; line-height: 1; text-align: center; }
    .strat-label { font-size: 0.75rem; font-weight: 600; text-align: center; letter-spacing: 1px; }
    
    div.stButton > button:first-child, div[data-testid="stFormSubmitButton"] > button { background: rgba(250, 204, 21, 0.1) !important; border: 1px solid rgba(250, 204, 21, 0.5) !important; color: #facc15 !important; border-radius: 6px !important; padding: 8px 12px !important; transition: all 0.3s ease; }
    div.stButton > button:first-child p, div[data-testid="stFormSubmitButton"] > button p { color: #facc15 !important; font-weight: 800 !important; font-size: 0.95rem !important; letter-spacing: 0.5px; margin: 0; }
    div.stButton > button:first-child:hover, div[data-testid="stFormSubmitButton"] > button:hover { background: #facc15 !important; transform: scale(1.02); box-shadow: 0 0 15px rgba(250, 204, 21, 0.5); }
    div.stButton > button:first-child:hover p, div[data-testid="stFormSubmitButton"] > button:hover p { color: #020617 !important; }
    
    .login-header { text-align: center; color: #facc15; font-size: 2.2rem; font-weight: 900; margin-top: 80px; margin-bottom: 5px; }
    .stDataFrame { font-size: 13px !important; }
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
        elif "4 Jam" in mode_tf: per, inv = "1mo", "1h" # Di-resample 4H
        else: per, inv = "3mo", "1d" # Daily
            
        df = yf.download(ticker, period=per, interval=inv, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        
        # PERBAIKAN BUG DATA 4 JAM FOREX
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
            "RAW_DF": df.tail(100) # Disimpan untuk chart Plotly
        }
    except: return None

# ==========================================
# 4. SIDEBAR (CYBER COMMAND CENTER)
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #facc15; font-size: 1.35rem; font-weight: 900; margin-bottom: 0px; text-align: left; margin-left: -5px; white-space: nowrap;'>👨‍💻 JIHAN-GHINA FX</h2>", unsafe_allow_html=True)
    st.markdown("<p style='text-align: left; margin-left: 20px; color: #94a3b8; font-size: 0.7rem; letter-spacing: 2px; margin-bottom: 15px;'>FOREX & GOLD v8.8</p>", unsafe_allow_html=True)
    
    st.markdown("""
    <div style='background: rgba(30, 41, 59, 0.4); border: 1px solid rgba(255,255,255,0.05); border-radius: 8px; padding: 10px; margin-bottom: 20px; border-left: 3px solid #10b981;'>
        <div style='font-size: 0.65rem; color: #94a3b8; letter-spacing: 1px; margin-bottom: 5px;'>SYSTEM STATUS</div>
        <div style='font-size: 0.8rem; color: #10b981; margin-bottom: 2px;'>🟢 FX Engine: <strong>Online</strong></div>
        <div style='font-size: 0.8rem; color: #38bdf8;'>⚡ Live Rates: <strong>Synced</strong></div>
    </div>
    """, unsafe_allow_html=True)
    
    # Deteksi Perubahan Timeframe untuk Auto-Scan
    tf_pilihan = st.selectbox("⏱️ Timeframe Analisis:", ["15 Menit", "1 Jam", "4 Jam", "1 Hari (Daily)"], index=3, label_visibility="visible")
    
    tf_berubah = False
    if tf_pilihan != st.session_state.current_tf:
        tf_berubah = True
        st.session_state.current_tf = tf_pilihan
        
    st.markdown("<br>", unsafe_allow_html=True)
    
    # TRIGGER: Jika tombol diklik ATAU timeframe berubah
    if st.button("🔄 SCAN MAJOR PAIRS", use_container_width=True) or tf_berubah:
        st.session_state.scan_clicked = True
        st.cache_data.clear()
        st.session_state.raw_forex = []
        
        bar = st.progress(0, text=f"Mengkalibrasi Harga Global ({st.session_state.current_tf})...")
        for i, t in enumerate(roster_forex):
            bar.progress((i + 1) / len(roster_forex), text=f"Scanning {nama_pairs[t]}...")
            data = fetch_single_forex(t, st.session_state.current_tf)
            if data: st.session_state.raw_forex.append(data)
            gc.collect()
            
        bar.empty()
        st.session_state.last_update = get_waktu_wib()
        
        # Simpan state (kecuali RAW_DF karena tidak bisa di-JSON)
        cache_safe_data = [{k: v for k, v in item.items() if k != 'RAW_DF'} for item in st.session_state.raw_forex]
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({"raw_forex": cache_safe_data, "last_update": st.session_state.last_update}, f)
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
    st.info("👈 Sistem aman dan standby. Tekan '🔄 SCAN MAJOR PAIRS' di sidebar.")
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
            rek = "🟡 WAIT / RANGE"
            entry, sl, tp = raw["HARGA"], raw["HARGA"], raw["HARGA"]
            
        hasil_fx.append({
            "PAIR": raw["NAMA"], "HARGA NOW": format_fx(raw["TICKER"], raw["HARGA"]),
            "ENTRY AREA": format_fx(raw["TICKER"], entry),
            "TAKE PROFIT (TP)": format_fx(raw["TICKER"], tp),
            "STOP LOSS (SL)": format_fx(raw["TICKER"], sl),
            "PIVOT POINT": format_fx(raw["TICKER"], raw["PIVOT"]),
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
            elif c == 'PIVOT POINT': styles.append('color: #94a3b8;')
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
    
    # Gunakan fungsi native table agar scrollbar HTML bisa bekerja
    st.dataframe(df_fx.style.apply(style_fx, axis=1), use_container_width=True, hide_index=True)
    
    # ==========================================
    # 6. MASTERPIECE FX SIGNAL & PLOTLY CHART
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='color: #f8fafc; font-weight: 800; margin-bottom: 1rem;'>🎯 FX Masterpiece Signal & Price Action</h3>", unsafe_allow_html=True)
    
    scanned_names = df_fx['PAIR'].tolist()
    pilihan_fx_nama = st.selectbox("⚡ Evaluasi Teknikal & Volatilitas Pair:", scanned_names)
    
    # Ambil Ticker asli untuk mencari RAW_DF
    pilihan_fx_ticker = [k for k, v in nama_pairs.items() if v == pilihan_fx_nama][0]
    
    row_data = df_fx[df_fx['PAIR'] == pilihan_fx_nama].iloc[0]
    aksi = row_data['ACTION']
    
    if "LONG" in aksi: 
        final = "🚀 STRONG BULLISH BIAS"
        clr = "#10b981"
        desc = f"Momentum dan Trend mendukung kenaikan di timeframe {st.session_state.current_tf}. Fokus cari peluang BUY dekat EMA20."
    elif "SHORT" in aksi:
        final = "🩸 STRONG BEARISH BIAS"
        clr = "#f43f5e"
        desc = f"Tekanan jual dominan di timeframe {st.session_state.current_tf}. Fokus cari peluang SELL dekat EMA20."
    else:
        final = "⚖️ RANGE BOUND (CHOPPY)"
        clr = "#fbbf24"
        desc = "Harga sedang bolak-balik tanpa arah jelas. Lebih baik Wait & See atau scalping range pendek."

    col_sig, col_chart = st.columns([1, 2])
    
    with col_sig:
        st.markdown(f"""
        <div class='premium-card' style='border-left: 5px solid {clr}; height: 100%; display: flex; flex-direction: column; justify-content: center;'>
            <div style='text-align: center;'>
                <span style='color: #94a3b8; font-size: 0.75rem; letter-spacing: 2px;'>STATUS ALGORITMA</span><br>
                <span style='color: {clr}; font-weight: 900; font-size: 1.6rem; display: block; margin: 10px 0;'>{final}</span>
                <span style='color: #cbd5e1; font-size: 0.85rem;'>{desc}</span>
            </div>
            <hr style='border-color: rgba(255,255,255,0.05); margin: 15px 0;'>
            <div style='display: flex; justify-content: space-around; text-align: center; color: #94a3b8; font-size: 0.8rem;'>
                <div>RSI<br><strong style='color:#f8fafc; font-size:1.1rem;'>{row_data['RSI']}</strong></div>
                <div>ENTRY PLAN<br><strong style='color:#38bdf8; font-size:1.1rem;'>{row_data['ENTRY AREA']}</strong></div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    with col_chart:
        # Plotly Candlestick Terkunci (Locked)
        raw_target = next((item for item in st.session_state.raw_forex if item["TICKER"] == pilihan_fx_ticker), None)
        if raw_target and "RAW_DF" in raw_target:
            df_chart = raw_target["RAW_DF"]
            fig = go.Figure()
            # Candlestick
            fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Price'))
            # Garis EMA20
            fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], mode='lines', line=dict(color='#00f2fe', width=1.5), name='EMA20'))
            
            fig.update_layout(
                margin=dict(l=10, r=10, t=10, b=10),
                paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                font=dict(color='#94a3b8'),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=10)),
                dragmode=False, xaxis_rangeslider_visible=False, hovermode='x unified', height=300
            )
            fig.update_xaxes(fixedrange=True, showgrid=False)
            fig.update_yaxes(fixedrange=True, gridcolor='rgba(255,255,255,0.05)')
            
            st.markdown(f"<h5 style='color: #facc15; text-align:center; font-size: 0.85rem; margin-bottom: 0px;'>📈 Live Chart: {pilihan_fx_nama} ({st.session_state.current_tf})</h5>", unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False})
        else:
            st.info("⚠️ Silakan klik SCAN MAJOR PAIRS untuk memuat grafik historis.")

    # ==========================================
    # 7. KALENDER EKONOMI (FUNDAMENTAL DATA)
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='color: #f8fafc; font-weight: 800; margin-bottom: 1rem;'>📅 Global Economic Calendar</h3>", unsafe_allow_html=True)
    st.markdown("<p style='color: #94a3b8; font-size: 0.85rem; margin-bottom: 15px;'>Jadwal rilis berita (NFP, CPI, The Fed) sangat menentukan ledakan volatilitas pasar.</p>", unsafe_allow_html=True)

    # Widget Kalender Ekonomi TradingView
    components.html(
        """
        <div class="tradingview-widget-container">
          <div class="tradingview-widget-container__widget"></div>
          <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
          {
          "colorTheme": "dark",
          "isTransparent": true,
          "width": "100%",
          "height": "450",
          "locale": "id",
          "importanceFilter": "-1,0,1",
          "currencyFilter": "USD,EUR,GBP,JPY,AUD,CAD,CHF,NZD"
          }
          </script>
        </div>
        """,
        height=450,
    )

st.markdown("---")
st.markdown("<p style='text-align: center; color: #475569; font-size: 0.75rem;'>⚡ JIHAN-GHINA FX ENGINE • SECURE ALGORITHMIC TERMINAL v8.8</p>", unsafe_allow_html=True)
