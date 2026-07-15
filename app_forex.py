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
# 0. SISTEM CACHE & TRACKING
# ==========================================
CACHE_FILE = "jihan_ghina_fx_cache.json"

if "raw_forex" not in st.session_state:
    st.session_state.raw_forex = []
    st.session_state.last_update = None
    st.session_state.us_yield_trend = 0  # Menyimpan data yield otomatis
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
# 1. KONFIGURASI HALAMAN & UI STYLE (ULTRA LUXURY)
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Quantum v9.0", page_icon="👑", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #0a1120, #02040a) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98% !important; }
    h1 { color: #fafafa; font-weight: 800; letter-spacing: -1px; font-size: 2.2rem !important; margin-bottom: 0; }
    
    /* Scrollbar Luxury */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: rgba(212, 175, 55, 0.4); border-radius: 10px; }
    ::-webkit-scrollbar-thumb:hover { background: rgba(212, 175, 55, 0.8); }
    
    section[data-testid="stSidebar"] { 
        background-color: rgba(2, 4, 10, 0.85) !important; 
        backdrop-filter: blur(20px); 
        border-right: 1px solid rgba(212, 175, 55, 0.15); 
    }
    
    .premium-card { 
        background: linear-gradient(145deg, rgba(30, 41, 59, 0.4) 0%, rgba(15, 23, 42, 0.6) 100%);
        backdrop-filter: blur(20px); 
        border: 1px solid rgba(255, 255, 255, 0.05); 
        border-radius: 12px; 
        padding: 20px; 
        box-shadow: 0 10px 30px -10px rgba(0, 0, 0, 0.5); 
        transition: all 0.3s ease; 
    }
    .premium-card:hover { transform: translateY(-2px); border-color: rgba(212, 175, 55, 0.4); }
    
    .ihsg-box { display: flex; flex-direction: column; justify-content: center; text-align: right; }
    .ihsg-title { color: #9ca3af; font-size: 0.7rem; font-weight: 700; letter-spacing: 2px; }
    
    div.stButton > button:first-child { 
        background: linear-gradient(90deg, rgba(212,175,55,0.1) 0%, rgba(212,175,55,0.25) 100%) !important; 
        border: 1px solid rgba(212, 175, 55, 0.5) !important; 
        color: #d4af37 !important; 
        border-radius: 8px !important; 
        font-weight: 700 !important;
        transition: all 0.3s ease; 
    }
    div.stButton > button:first-child:hover { 
        background: #d4af37 !important; 
        color: #02040a !important;
        box-shadow: 0 0 20px rgba(212, 175, 55, 0.4);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. AUTO-DATA FEED (YIELD PROXY ENGINE)
# ==========================================
@st.cache_data(ttl=300, show_spinner=False)
def fetch_macro_yield_proxy():
    """ Mengambil data US 10Y Bond Yield secara otomatis sebagai proxy Rilis Ekonomi """
    try:
        # ^TNX adalah US 10-Year Treasury Yield
        df = yf.download("^TNX", period="5d", interval="1d", progress=False)
        if df.empty: return 0
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        close_now = float(df['Close'].iloc[-1])
        close_prev = float(df['Close'].iloc[-2])
        
        # Jika Yield naik tajam, data ekonomi AS (NFP/CPI) sedang bagus -> Sentimen Hawkish USD
        if close_now > close_prev + 0.05: return 15  # USD Menguat
        elif close_now < close_prev - 0.05: return -15 # USD Melemah
        return 0
    except: return 0

@st.cache_data(ttl=300, show_spinner=False)
def fetch_dxy():
    try:
        df = yf.download("DX-Y.NYB", period="5d", interval="1d", progress=False)
        if df.empty: return None, None, None
        df = df.ffill()
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        return float(df['Close'].iloc[-1]), float(df['Close'].iloc[-1]) - float(df['Close'].iloc[-2]), ((float(df['Close'].iloc[-1]) - float(df['Close'].iloc[-2])) / float(df['Close'].iloc[-2])) * 100
    except: return None, None, None

# Base Fundamental Table
DB_MACRO = {
    "USD": {"Negara": "United States", "Suku_Bunga": 5.25, "Inflasi": 2.8, "Skor_Base": 35},
    "EUR": {"Negara": "Eurozone", "Suku_Bunga": 3.75, "Inflasi": 2.4, "Skor_Base": 10},
    "GBP": {"Negara": "United Kingdom", "Suku_Bunga": 4.50, "Inflasi": 2.6, "Skor_Base": 20},
    "JPY": {"Negara": "Japan", "Suku_Bunga": 0.25, "Inflasi": 2.1, "Skor_Base": -30},
    "AUD": {"Negara": "Australia", "Suku_Bunga": 4.35, "Inflasi": 3.2, "Skor_Base": 15},
    "CAD": {"Negara": "Canada", "Suku_Bunga": 4.25, "Inflasi": 2.5, "Skor_Base": 5},
    "CHF": {"Negara": "Switzerland", "Suku_Bunga": 1.00, "Inflasi": 1.2, "Skor_Base": -15},
    "NZD": {"Negara": "New Zealand", "Suku_Bunga": 4.75, "Inflasi": 2.9, "Skor_Base": 0}
}

def get_dynamic_fundamental_score(pair_nama, us_yield_modifier):
    try:
        base, quote = pair_nama.split("/")
        
        # Injeksi data otomatis ke USD
        usd_skor_final = DB_MACRO["USD"]["Skor_Base"] + us_yield_modifier
        
        if base == "GOLD (XAU": 
            base_score = 40 if us_yield_modifier < 0 else -10 
            return base_score - usd_skor_final, "SAFE HAVEN DEMAND" if (base_score - usd_skor_final) > 0 else "BEARISH GOLD (HIGH YIELD)"
            
        base_score = usd_skor_final if base == "USD" else DB_MACRO[base]["Skor_Base"]
        quote_score = usd_skor_final if quote == "USD" else DB_MACRO[quote]["Skor_Base"]
        
        net = base_score - quote_score
        if net >= 25: bias = "BULLISH DIVERGENCE (MACRO)"
        elif net <= -25: bias = "BEARISH DIVERGENCE (MACRO)"
        else: bias = "NEUTRAL BALANCED"
        return net, bias
    except: return 0, "UNKNOWN"

# ==========================================
# 3. ENGINE TEKNIKAL & FOREX SCANNER
# ==========================================
roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "NZDUSD=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "NZDUSD=X": "NZD/USD", "XAUUSD=X": "GOLD (XAU/USD)"}

def fetch_single_forex(ticker, mode_tf):
    try:
        per, inv = {"15 Menit": ("5d", "15m"), "1 Jam": ("1mo", "1h"), "4 Jam": ("1mo", "1h"), "1 Hari (Daily)": ("3mo", "1d")}[mode_tf]
        df = yf.download(ticker, period=per, interval=inv, progress=False)
        if df.empty: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = [col[0] for col in df.columns]
        
        if mode_tf == "4 Jam":
            df = df.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
            
        df = df.ffill()
        
        # Indikator Teknikal (Ditambah Bollinger Bands untuk Charting)
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        df['STD'] = df['Close'].rolling(20).std()
        df['BB_UP'] = df['EMA20'] + (2 * df['STD'])
        df['BB_LOW'] = df['EMA20'] - (2 * df['STD'])
        
        df['MACD'] = df['Close'].ewm(span=12, adjust=False).mean() - df['Close'].ewm(span=26, adjust=False).mean()
        df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # ATR & RSI
        tr = np.max([df['High']-df['Low'], np.abs(df['High']-df['Close'].shift()), np.abs(df['Low']-df['Close'].shift())], axis=0)
        df['ATR'] = pd.Series(tr, index=df.index).rolling(14).mean()
        
        delta = df['Close'].diff()
        rs = delta.clip(lower=0).ewm(alpha=1/14).mean() / (-1 * delta.clip(upper=0)).ewm(alpha=1/14).mean()
        df['RSI'] = 100 - (100 / (1 + rs))
        
        last = df.iloc[-1]
        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA": float(last['Close']), 
            "RSI": round(float(last['RSI']), 2), "ATR": float(last['ATR']), "EMA20": float(last['EMA20']),
            "UP_EMA20": float(last['Close']) > float(last['EMA20']), "MACD_BULL": float(last['MACD']) > float(last['Signal']),
            "RAW_DF": df.tail(120) # Ambil 120 candle untuk chart elegan
        }
    except: return None

# ==========================================
# 4. SIDEBAR & EXECUTION
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #d4af37; font-weight: 800;'>👑 QUANTUM ENGINE</h2>", unsafe_allow_html=True)
    st.markdown("<p style='color: #6b7280; font-size: 0.75rem; letter-spacing: 1px; margin-bottom: 20px;'>INSTITUTIONAL TERMINAL v9.0</p>", unsafe_allow_html=True)
    
    tf_pilihan = st.selectbox("⏱️ Timeframe Evaluasi:", ["15 Menit", "1 Jam", "4 Jam", "1 Hari (Daily)"], index=3)
    
    if st.button("🔄 AUTO-SCAN & SYNC MACRO", use_container_width=True) or (tf_pilihan != st.session_state.current_tf):
        st.session_state.current_tf = tf_pilihan
        st.session_state.scan_clicked = True
        st.cache_data.clear()
        st.session_state.raw_forex = []
        
        # Sync Automasi Macro
        st.session_state.us_yield_trend = fetch_macro_yield_proxy()
        
        bar = st.progress(0, text="Menyinkronkan Data Kalender & Harga...")
        for i, t in enumerate(roster_forex):
            bar.progress((i + 1) / len(roster_forex), text=f"Analyzing {nama_pairs[t]}...")
            data = fetch_single_forex(t, st.session_state.current_tf)
            if data: st.session_state.raw_forex.append(data)
            
        bar.empty()
        st.session_state.last_update = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d %b %Y - %H:%M WIB")
        st.rerun()

# ==========================================
# 5. DASHBOARD UTAMA
# ==========================================
col_h1, col_h2 = st.columns([3.5, 1.5])
with col_h1:
    st.markdown("<h1>🏛️ Market Intelligence Center</h1>", unsafe_allow_html=True)
    st.markdown(f"<p style='font-size: 0.95rem;'>🕒 Last Sync: <span style='color:#d4af37;'>{st.session_state.last_update or 'Awaiting Data...'}</span> | Algoritma: Volatilitas + Auto-Yield Proxy</p>", unsafe_allow_html=True)

dxy_val, dxy_chg, dxy_pct = fetch_dxy()
with col_h2:
    if dxy_val:
        clr = '#10b981' if dxy_chg >= 0 else '#f43f5e'
        st.markdown(f"""
        <div class="premium-card ihsg-box" style="border-left: 4px solid {clr}; padding: 15px;">
            <span class="ihsg-title">US DOLLAR (DXY)</span>
            <span style="color: {clr}; font-size: 1.6rem; font-weight: 800;">{dxy_val:,.2f}</span>
            <span style="color: {clr}; font-size: 0.85rem; font-weight:700;">{'▲' if dxy_chg >=0 else '▼'} {dxy_chg:+,.2f} ({dxy_pct:+.2f}%)</span>
        </div>
        """, unsafe_allow_html=True)

st.markdown("---")

# AUTOMATED FUNDAMENTAL TABLE (Instruksi #3)
st.markdown("### 📊 Auto-Synchronized Macro Fundamental Matrix")
st.markdown("<p style='font-size:0.85rem; color:#9ca3af;'>Tabel ini disinkronisasikan dengan pergerakan obligasi (Yield) secara real-time. Jika data rilis NFP/CPI mengejutkan pasar, skor USD akan otomatis terkoreksi.</p>", unsafe_allow_html=True)

macro_rows = []
usd_modifier = st.session_state.get('us_yield_trend', 0)
usd_status = "HAWKISH (+)" if usd_modifier > 0 else ("DOVISH (-)" if usd_modifier < 0 else "NEUTRAL")

for k, v in DB_MACRO.items():
    skor_akhir = v["Skor_Base"] + usd_modifier if k == "USD" else v["Skor_Base"]
    sentimen = usd_status if k == "USD" else ("NEUTRAL" if v["Skor_Base"] >= 0 else "DOVISH")
    macro_rows.append({"MATA UANG": k, "NEGARA": v["Negara"], "SUKU BUNGA": f"{v['Suku_Bunga']}%", "INFLASI CPI": f"{v['Inflasi']}%", "AUTO-SENTIMEN": sentimen, "NET SCORE": skor_akhir})

st.dataframe(pd.DataFrame(macro_rows).style.apply(lambda r: ['background-color: rgba(212,175,55,0.1); color:#d4af37; font-weight:bold;' if r['MATA UANG'] == 'USD' else '' for _ in r], axis=1), use_container_width=True, hide_index=True)

st.markdown("---")

# MATRIKS TRADING
if st.session_state.scan_clicked and st.session_state.raw_forex:
    st.markdown("<h3>🎯 Pro Max Trade Action Matrix</h3>", unsafe_allow_html=True)
    
    hasil_fx = []
    for raw in st.session_state.raw_forex:
        skor_tech = (30 if raw["UP_EMA20"] else 0) + (30 if raw["MACD_BULL"] else 0)
        if 40 <= raw["RSI"] <= 65: skor_tech += 20
        elif raw["RSI"] > 70: skor_tech -= 10
        elif raw["RSI"] < 30: skor_tech += 15
        
        f_skor, f_bias = get_dynamic_fundamental_score(raw["NAMA"], usd_modifier)
        total_score = (skor_tech * 1.2) + (f_skor * 1.5)
        
        if total_score >= 45: rek, clr = "🟢 BUY OP", "#10b981"
        elif total_score <= -20: rek, clr = "🔴 SELL OP", "#f43f5e"
        else: rek, clr = "🟡 WAIT", "#fbbf24"
            
        entry = raw["EMA20"]
        hasil_fx.append({
            "PAIR": raw["NAMA"], "PRICE": f"{raw['HARGA']:.4f}" if "JPY" not in raw["TICKER"] and "XAU" not in raw["TICKER"] else f"{raw['HARGA']:.2f}",
            "QUANT SCORE": round(total_score, 1), "MACRO BIAS": f_bias,
            "BUY/SELL ZONE (EMA)": f"{entry:.4f}" if "JPY" not in raw["TICKER"] and "XAU" not in raw["TICKER"] else f"{entry:.2f}",
            "RSI": f"{raw['RSI']:.1f}", "DECISION": rek
        })
        
    st.dataframe(pd.DataFrame(hasil_fx).style.apply(lambda r: ['color: #10b981; font-weight:bold;' if 'BUY' in r['DECISION'] else ('color: #f43f5e; font-weight:bold;' if 'SELL' in r['DECISION'] else 'color: #fbbf24;') for _ in r], subset=['DECISION'], axis=1), use_container_width=True, hide_index=True)
    
    # ==========================================
    # 6. ELEGANT CHART (Instruksi #1)
    # ==========================================
    st.markdown("---")
    st.markdown("<h3>📈 Institutional Advanced Charting</h3>", unsafe_allow_html=True)
    pilihan_fx_nama = st.selectbox("Pilih Pair untuk Visualisasi Deep Chart:", [x["NAMA"] for x in st.session_state.raw_forex])
    
    raw_target = next((item for item in st.session_state.raw_forex if item["NAMA"] == pilihan_fx_nama), None)
    if raw_target:
        df_chart = raw_target["RAW_DF"]
        fig = go.Figure()
        
        # Candlestick Elegan dengan warna Premium
        fig.add_trace(go.Candlestick(
            x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], 
            name='Price Action',
            increasing_line_color='#00e676', increasing_fillcolor='#00e676', # Neon Green
            decreasing_line_color='#ff1744', decreasing_fillcolor='#ff1744'  # Neon Red
        ))
        
        # Bollinger Bands & EMA (Pro Max Look)
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_UP'], mode='lines', line=dict(color='rgba(212,175,55,0.3)', width=1, dash='dot'), name='Volatility Band Upper'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_LOW'], mode='lines', line=dict(color='rgba(212,175,55,0.3)', width=1, dash='dot'), name='Volatility Band Lower', fill='tonexty', fillcolor='rgba(212,175,55,0.03)'))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], mode='lines', line=dict(color='#d4af37', width=2), name='Institutional EMA 20'))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(10, 17, 32, 0.6)', # Dark navy elegan
            font=dict(color='#9ca3af', family='Plus Jakarta Sans'),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="center", x=0.5, font=dict(size=11)),
            margin=dict(l=0, r=0, t=10, b=0), height=450, dragmode="pan", xaxis_rangeslider_visible=False
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)', zeroline=False)
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)', zeroline=False)
        
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})

# ==========================================
# 7. TRADINGVIEW ECONOMIC CALENDAR (Instruksi #2)
# ==========================================
st.markdown("---")
st.markdown("<h3>📅 Global Real-Time Economic Calendar (This Week)</h3>", unsafe_allow_html=True)
st.markdown("<p style='color: #9ca3af; font-size: 0.85rem; margin-bottom: 20px;'>Tampilan jadwal rilis makro ekonomi dalam seminggu penuh. Disaring secara otomatis hanya untuk berita berimpak Medium (2 bintang) dan High (3 Bintang).</p>", unsafe_allow_html=True)

# Widget Kalender TradingView Jauh Lebih Elegan dan Tidak Blank
components.html(
    """
    <div class="tradingview-widget-container">
      <div class="tradingview-widget-container__widget"></div>
      <script type="text/javascript" src="https://s3.tradingview.com/external-embedding/embed-widget-events.js" async>
      {
      "colorTheme": "dark",
      "isTransparent": true,
      "width": "100%",
      "height": "600",
      "locale": "id",
      "importanceFilter": "0,1",
      "currencyFilter": "USD,EUR,JPY,GBP,AUD,CAD,NZD,CHF"
      }
      </script>
    </div>
    """,
    height=600,
)
