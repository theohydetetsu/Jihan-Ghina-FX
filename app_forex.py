import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz
import warnings
import json
import os
import requests
import plotly.graph_objects as go
import streamlit.components.v1 as components 

warnings.filterwarnings('ignore')

# ==========================================
# 0. SISTEM CACHE & TRACKING STATE
# ==========================================
CACHE_FILE = "jihan_ghina_fx_v10_cache.json"

if "raw_forex" not in st.session_state:
    st.session_state.raw_forex = []
    st.session_state.last_update = None
    st.session_state.cal_impact_dict = {}  
    if os.path.exists(CACHE_FILE):
        try:
            with open(CACHE_FILE, "r") as f:
                cache_data = json.load(f)
                st.session_state.raw_forex = cache_data.get("raw_forex", [])
                st.session_state.last_update = cache_data.get("last_update", None)
                st.session_state.cal_impact_dict = cache_data.get("cal_impact_dict", {})
        except: pass

if "scan_clicked" not in st.session_state:
    st.session_state.scan_clicked = False

# ==========================================
# 1. KONFIGURASI UI STYLE (ULTRA LUXURY V10.2)
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX Quantum Pro v10.2", page_icon="👑", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;600;700;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #0a0a0c, #000000) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98% !important; }
    
    .title-v10 {
        background: linear-gradient(to right, #d4af37, #fdf5e6, #d4af37);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 800;
        font-size: 2.5rem;
        margin-bottom: 0;
        letter-spacing: -1px;
    }
    
    .directive-card {
        background: linear-gradient(145deg, rgba(16, 20, 25, 0.9) 0%, rgba(5, 7, 10, 0.95) 100%);
        border: 1px solid rgba(212, 175, 55, 0.4);
        border-radius: 16px;
        padding: 25px;
        box-shadow: 0 15px 35px rgba(212, 175, 55, 0.1);
        position: relative;
        overflow: hidden;
    }
    
    .directive-card::before {
        content: "";
        position: absolute;
        top: 0; left: 0; width: 100%; height: 4px;
        background: linear-gradient(90deg, #d4af37, #f3f4f6, #d4af37);
    }
    
    .placeholder-card {
        background: rgba(15, 15, 20, 0.6);
        border: 1px dashed rgba(212, 175, 55, 0.3);
        border-radius: 12px;
        padding: 40px;
        text-align: center;
        margin-top: 20px;
        margin-bottom: 20px;
    }
    
    div.stButton > button:first-child { 
        background: linear-gradient(90deg, rgba(212,175,55,0.15) 0%, rgba(212,175,55,0.3) 100%) !important; 
        border: 1px solid #d4af37 !important; 
        color: #fdf5e6 !important; 
        border-radius: 8px !important; 
        font-weight: 800 !important;
        letter-spacing: 1px;
        transition: all 0.3s ease; 
    }
    div.stButton > button:first-child:hover { 
        background: #d4af37 !important; 
        color: #000000 !important;
        box-shadow: 0 0 25px rgba(212, 175, 55, 0.5);
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CALENDAR PARSER & DB FUNDAMENTAL
# ==========================================
DB_MACRO_BASE = {
    "USD": {"Negara": "US", "Suku_Bunga": 5.25, "Inflasi": 2.8, "Skor_Base": 35},
    "EUR": {"Negara": "EU", "Suku_Bunga": 3.75, "Inflasi": 2.4, "Skor_Base": 10},
    "GBP": {"Negara": "UK", "Suku_Bunga": 4.50, "Inflasi": 2.6, "Skor_Base": 20},
    "JPY": {"Negara": "JP", "Suku_Bunga": 0.25, "Inflasi": 2.1, "Skor_Base": -30},
    "AUD": {"Negara": "AU", "Suku_Bunga": 4.35, "Inflasi": 3.2, "Skor_Base": 15},
    "CAD": {"Negara": "CA", "Suku_Bunga": 4.25, "Inflasi": 2.5, "Skor_Base": 5},
    "CHF": {"Negara": "CH", "Suku_Bunga": 1.00, "Inflasi": 1.2, "Skor_Base": -15},
    "NZD": {"Negara": "NZ", "Suku_Bunga": 4.75, "Inflasi": 2.9, "Skor_Base": 0}
}

def fetch_live_calendar():
    impact = {k: 0 for k in DB_MACRO_BASE.keys()}
    try:
        url = "https://nfs.gweb.io/analytics/calendar/this-week"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
        if resp.status_code == 200:
            for ev in resp.json():
                curr = ev.get("currency", "").upper()
                imp = str(ev.get("importance", "")).upper()
                if curr in impact and ("HIGH" in imp or "3" in imp):
                    act, fore = ev.get("actual"), ev.get("forecast")
                    if act and fore:
                        try:
                            a = float(str(act).replace("%", "").replace("K", "").replace("M", "").strip())
                            f = float(str(fore).replace("%", "").replace("K", "").replace("M", "").strip())
                            if a > f: impact[curr] += 15
                            elif a < f: impact[curr] -= 15
                        except: pass
    except: pass
    return impact

# ==========================================
# 3. MULTI-TIMEFRAME (MTF) ENGINE - V10.2 SAFE
# ==========================================
roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "XAUUSD=X": "GOLD (XAU/USD)"}

def fetch_mtf_forex(ticker):
    try:
        # Menggunakan Ticker.history untuk menghindari problem multiindex kolom yfinance
        tk = yf.Ticker(ticker)
        df_h1 = tk.history(period="1mo", interval="1h")
        
        if df_h1.empty: 
            return None
            
        df_h1 = df_h1.ffill()
        
        # Resampling data flat
        df_h4 = df_h1.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
        df_d1 = df_h1.resample('1d').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()

        # Penghitungan Indikator H1
        df_h1['EMA20'] = df_h1['Close'].ewm(span=20, adjust=False).mean()
        df_h1['STD'] = df_h1['Close'].rolling(20).std()
        df_h1['BB_UP'] = df_h1['EMA20'] + (2 * df_h1['STD'])
        df_h1['BB_LOW'] = df_h1['EMA20'] - (2 * df_h1['STD'])
        h1_last = df_h1.iloc[-1]
        
        tr = np.max([df_h1['High']-df_h1['Low'], np.abs(df_h1['High']-df_h1['Close'].shift()), np.abs(df_h1['Low']-df_h1['Close'].shift())], axis=0)
        df_h1['ATR'] = pd.Series(tr, index=df_h1.index).rolling(14).mean()

        # Tren H4
        df_h4['EMA20'] = df_h4['Close'].ewm(span=20, adjust=False).mean()
        h4_trend = "BULL" if float(df_h4.iloc[-1]['Close']) > float(df_h4.iloc[-1]['EMA20']) else "BEAR"

        # Tren Daily
        df_d1['EMA20'] = df_d1['Close'].ewm(span=20, adjust=False).mean()
        d1_trend = "BULL" if float(df_d1.iloc[-1]['Close']) > float(df_d1.iloc[-1]['EMA20']) else "BEAR"

        h1_trend = "BULL" if float(h1_last['Close']) > float(h1_last['EMA20']) else "BEAR"
        confluence_score = 0
        if h1_trend == h4_trend == d1_trend == "BULL": confluence_score = 30
        elif h1_trend == h4_trend == d1_trend == "BEAR": confluence_score = -30

        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA": float(h1_last['Close']), 
            "ATR": float(h1_last['ATR']), "EMA20": float(h1_last['EMA20']),
            "BB_UP": float(h1_last['BB_UP']), "BB_LOW": float(h1_last['BB_LOW']), 
            "MTF_TREND": f"D1:{d1_trend} | H4:{h4_trend} | H1:{h1_trend}",
            "CONFLUENCE": confluence_score,
            "RAW_DF": df_h1.tail(120) 
        }
    except Exception as e:
        return None

def trigger_market_scan():
    st.session_state.scan_clicked = True
    progress_bar = st.progress(0)
    
    st.session_state.cal_impact_dict = fetch_live_calendar()
    st.session_state.raw_forex = []
    
    total_pairs = len(roster_forex)
    for idx, t in enumerate(roster_forex):
        data = fetch_mtf_forex(t)
        if data: 
            st.session_state.raw_forex.append(data)
        progress_bar.progress(int((idx + 1) / total_pairs * 100))
        
    progress_bar.empty()
    st.session_state.last_update = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%d %b %Y - %H:%M WIB")
    
    # Simpan ke cache jika ada data berhasil diambil
    if st.session_state.raw_forex:
        try:
            with open(CACHE_FILE, "w") as f:
                json.dump({
                    "raw_forex": [{k: v for k, v in item.items() if k != "RAW_DF"} for item in st.session_state.raw_forex],
                    "last_update": st.session_state.last_update,
                    "cal_impact_dict": st.session_state.cal_impact_dict
                }, f)
        except: pass

# ==========================================
# 4. SIDEBAR CONTROL PANEL & RISK MANAGER
# ==========================================
with st.sidebar:
    st.markdown("<h2 style='color: #d4af37; font-weight: 800;'>🛡️ V10.2 CONTROL</h2>", unsafe_allow_html=True)
    st.markdown("### Risk Management")
    acc_balance = st.number_input("Modal Trading (USD):", min_value=10.0, value=1000.0, step=100.0)
    risk_pct = st.slider("Risiko per Trade (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    st.markdown("---")
    if st.button("🔥 RE-SCAN MARKET DATA", use_container_width=True):
        trigger_market_scan()
        st.rerun()

# ==========================================
# 5. DASHBOARD UTAMA & MARKET SESSION
# ==========================================
st.markdown("<p class='title-v10'>🏛 Rose QUANTUM PRO v10.2</p>", unsafe_allow_html=True)
st.markdown(f"<p style='color:#9ca3af;'>The Anti-Bug Intraday Edition | Last Sync: <span style='color:#d4af37;'>{st.session_state.last_update or 'Awaiting Activation'}</span></p>", unsafe_allow_html=True)

# LIVE MARKET SESSION
def get_market_session():
    current_hour = datetime.now(pytz.timezone('Asia/Jakarta')).hour
    if 5 <= current_hour < 14:
        return "TOKYO/SYDNEY (Sesi Asia)", "🟡 Konsolidasi / Volatilitas Rendah (Hati-hati Fakeout)", "#fbbf24"
    elif 14 <= current_hour < 19:
        return "LONDON (Sesi Eropa)", "🟢 Momentum Terbentuk / Likuiditas Tinggi", "#10b981"
    elif 19 <= current_hour < 22:
        return "LONDON + NEW YORK OVERLAP", "🔥 ZONA TEMPUR / Volatilitas & Likuiditas Maksimal", "#f43f5e"
    elif 22 <= current_hour <= 23 or 0 <= current_hour < 4:
        return "NEW YORK (Sesi AS)", "🟠 Volatilitas Tinggi / Rawan Berita Makro", "#f97316"
    else:
        return "MARKET TRANSITION", "⚪ Penyesuaian Harga / Spread Sedang Melebar", "#9ca3af"

sesi_aktif, status_volatilitas, warna_sesi = get_market_session()

st.markdown(f"""
<div style="background: rgba(20, 24, 30, 0.6); border-left: 4px solid {warna_sesi}; padding: 15px; border-radius: 8px; margin-bottom: 20px;">
    <p style="margin: 0; font-size: 0.9rem; color: #9ca3af; font-weight: 700; letter-spacing: 1px;">LIVE MARKET SESSION DETECTOR (WIB)</p>
    <p style="margin: 5px 0 0 0; font-size: 1.4rem; font-weight: 800; color: {warna_sesi};">{sesi_aktif}</p>
    <p style="margin: 5px 0 0 0; font-size: 0.95rem; font-weight: 600; color: #f3f4f6;">Status: {status_volatilitas}</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# STATE HANDLER DISPLAY MATRIX
# ==========================================
if not st.session_state.scan_clicked:
    st.markdown("""
    <div class="placeholder-card">
        <h3 style="color: #d4af37; font-weight: 800; margin-bottom: 10px;">🏛️ SYSTEM INITIALIZATION REQUIRED</h3>
        <p style="color: #9ca3af; max-width: 600px; margin: 0 auto 25px auto;">
            Sistem Quantum Pro v10.2 siap digunakan. Klik tombol di bawah ini untuk mengaktifkan pemindaian data pasar real-time dan memicu kalkulasi matriks fundamental.
        </p>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns([2,1,2])
    with col2:
        if st.button("🚀 LAUNCH SYSTEM MATRIX", use_container_width=True):
            trigger_market_scan()
            st.rerun()

elif st.session_state.scan_clicked and not st.session_state.raw_forex:
    st.error("⚠️ Gagal menarik data dari server yFinance. Jaringan sedang sibuk atau bursa sedang offline sementara.")
    st.info("💡 Solusi: Silakan periksa koneksi internet Anda, lalu tekan tombol 'Coba Lagi' di bawah.")
    if st.button("🔄 Coba Lagi / Force Re-Scan"):
        trigger_market_scan()
        st.rerun()

else:
    # RUNNING MODE: DATA BERHASIL DITAMPILKAN
    final_macro_db = {}
    cal_mod = st.session_state.get("cal_impact_dict", {})
    for k, v in DB_MACRO_BASE.items():
        final_macro_db[k] = v["Skor_Base"] + cal_mod.get(k, 0)
    
    st.markdown("### 🧬 MTF Confluence Matrix (3-Dimensional Flat Scan)")
    
    matrix_rows = []
    for raw in st.session_state.raw_forex:
        pair_name = raw["NAMA"]
        if "GOLD" in pair_name:
            f_score = 25 if final_macro_db["USD"] < 0 else -25
        else:
            try:
                base, quote = pair_name.split("/")
                f_score = final_macro_db[base] - final_macro_db[quote]
            except:
                f_score = 0
            
        total_score = raw["CONFLUENCE"] + f_score
        
        if total_score >= 45: rek = "🟢 PERFECT BUY"
        elif total_score <= -45: rek = "🔴 PERFECT SELL"
        elif total_score >= 15: rek = "↗️ MODERATE BUY"
        elif total_score <= -15: rek = "↘️ MODERATE SELL"
        else: rek = "🟡 NO CONFLUENCE"
        
        matrix_rows.append({
            "PAIR": pair_name,
            "MTF TREND (D1|H4|H1)": raw["MTF_TREND"],
            "QUANT SCORE": total_score,
            "FINAL DECISION": rek,
            "TICKER": raw["TICKER"]
        })
        
    st.dataframe(pd.DataFrame(matrix_rows).drop(columns=["TICKER"]).style.apply(
        lambda r: ['color: #10b981; font-weight:bold;' if 'BUY' in str(r['FINAL DECISION']) else ('color: #f43f5e; font-weight:bold;' if 'SELL' in str(r['FINAL DECISION']) else 'color: #fbbf24;') for _ in r], subset=['FINAL DECISION'], axis=1
    ), use_container_width=True, hide_index=True)

    # ==========================================
    # 6. DIRECTIVE & AUTO LOT CALCULATOR
    # ==========================================
    st.markdown("---")
    st.markdown("### 🎯 V10.2 Tactical Execution & Risk Manager")
    pilihan_pair = st.selectbox("Pilih Aset untuk Analisa Eksekusi:", [x["NAMA"] for x in st.session_state.raw_forex])
    
    active_data = next((item for item in st.session_state.raw_forex if item["NAMA"] == pilihan_pair), None)
    active_matrix = next((item for item in matrix_rows if item["PAIR"] == pilihan_pair), None)
    
    if active_data and active_matrix:
        harga_now = active_data["HARGA"]
        atr = active_data["ATR"]
        ema = active_data["EMA20"]
        decision = active_matrix["FINAL DECISION"]
        
        is_buy = "BUY" in decision
        is_sell = "SELL" in decision
        
        sl_dist = 2.0 * atr
        risk_amount = acc_balance * (risk_pct / 100)
        
        if "JPY" in active_data["TICKER"]:
            pips = sl_dist * 100
            pip_value_std = 7.00
        elif "XAU" in active_data["TICKER"]:
            pips = sl_dist * 10
            pip_value_std = 10.0
        else:
            pips = sl_dist * 10000
            pip_value_std = 10.0
            
        lot_size = risk_amount / (pips * pip_value_std) if pips > 0 else 0
        lot_size = max(0.01, round(lot_size, 2))
        
        if is_buy:
            dir_bias = "MTF BULLISH ALIGNMENT"
            sl, tp1, tp2 = harga_now - sl_dist, harga_now + (1.5 * atr), harga_now + (3.0 * atr)
            entry = f"{ema:.5f} - {active_data['BB_LOW']:.5f}" if "JPY" not in active_data["TICKER"] else f"{ema:.3f} - {active_data['BB_LOW']:.3f}"
        elif is_sell:
            dir_bias = "MTF BEARISH ALIGNMENT"
            sl, tp1, tp2 = harga_now + sl_dist, harga_now - (1.5 * atr), harga_now - (3.0 * atr)
            entry = f"{ema:.5f} - {active_data['BB_UP']:.5f}" if "JPY" not in active_data["TICKER"] else f"{ema:.3f} - {active_data['BB_UP']:.3f}"
        else:
            dir_bias = "WAIT FOR ALIGNMENT"
            sl, tp1, tp2 = harga_now - sl_dist, harga_now + sl_dist, harga_now + (2*sl_dist)
            entry = "TIDAK DISARANKAN ENTRY"
            lot_size = 0.00

        format_p = ".5f" if "JPY" not in active_data["TICKER"] and "XAU" not in active_data["TICKER"] else ".3f"

        st.markdown(f"""
        <div class="directive-card">
            <div style="display: flex; justify-content: space-between; margin-bottom: 20px;">
                <span style="font-size: 1.4rem; font-weight: 800; color: #d4af37;">EXECUTION TICKET: {pilihan_pair}</span>
                <span style="background-color: rgba(244, 63, 94, 0.2); color: #f43f5e; padding: 5px 12px; border-radius: 6px; font-weight: bold; font-size: 0.9rem; border: 1px solid #f43f5e;">
                    RISK CAP: ${risk_amount:.2f} ({risk_pct}%)
                </span>
            </div>
            <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px;">
                <div>
                    <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">MTF SIGNAL</p>
                    <p style="font-size: 1.2rem; font-weight: 800; color: {'#10b981' if is_buy else ('#f43f5e' if is_sell else '#fbbf24')}; margin: 0;">{dir_bias}</p>
                </div>
                <div>
                    <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">SAFE LOT SIZE</p>
                    <p style="font-size: 1.5rem; font-weight: 800; color: #fdf5e6; margin: 0; text-shadow: 0 0 10px rgba(212,175,55,0.5);">{lot_size} LOT</p>
                </div>
                <div>
                    <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">ENTRY AREA</p>
                    <p style="font-size: 1.1rem; font-weight: 700; color: #d4af37; margin: 0;">{entry if not "TIDAK" in entry else "N/A"}</p>
                </div>
                <div>
                    <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">STOP LOSS (SL)</p>
                    <p style="font-size: 1.1rem; font-weight: 700; color: #f43f5e; margin: 0;">{format(sl, format_p)}</p>
                </div>
                <div>
                    <p style="font-size: 0.8rem; color: #9ca3af; margin: 0;">TARGET (TP 1 / TP 2)</p>
                    <p style="font-size: 1.1rem; font-weight: 700; color: #10b981; margin: 0;">{format(tp1, format_p)} / {format(tp2, format_p)}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

    # ==========================================
    # 7. CHARTING H1 PRESISI (Menggunakan Data Tunggal Hasil Filter Ticker)
    # ==========================================
    st.markdown("---")
    st.markdown("### 📈 H1 Precision Entry Chart")
    try:
        # Menarik ulang data chart khusus untuk pair terpilih agar visualnya full candle
        df_chart = yf.Ticker(active_data["TICKER"]).history(period="1mo", interval="1h").tail(100)
        df_chart['EMA20'] = df_chart['Close'].ewm(span=20, adjust=False).mean()
        
        fig = go.Figure()
        fig.add_trace(go.Candlestick(
            x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], 
            name='Price', increasing_line_color='#00e676', decreasing_line_color='#ff1744'
        ))
        fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], mode='lines', line=dict(color='#d4af37', width=2), name='EMA 20 (Trend)'))
        
        fig.update_layout(
            paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(5, 7, 10, 0.8)', 
            font=dict(color='#9ca3af', family='Plus Jakarta Sans'),
            margin=dict(l=0, r=0, t=10, b=0), height=450, dragmode="pan", xaxis_rangeslider_visible=False
        )
        fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)')
        fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.03)')
        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
    except:
        st.info("Bagan teknikal sedang memuat ulang baris lilin...")

# ==========================================
# 8. WEEKLY HIGH IMPACT CALENDAR
# ==========================================
st.markdown("---")
st.markdown("### 🗓️ Global Macro High Impact Calendar")
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
      "importanceFilter": "1",
      "currencyFilter": "USD,EUR,JPY,GBP,AUD,CAD,NZD,CHF"
      }
      </script>
    </div>
    """,
    height=500,
)