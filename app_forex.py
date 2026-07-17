import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz
import warnings
import plotly.graph_objects as go
import streamlit.components.v1 as components 
import requests

warnings.filterwarnings('ignore')

# ==========================================
# 1. KONFIGURASI UI STYLE & LUXURY CSS
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX v11", page_icon="💎", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #1a1616, #050505) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 100% !important; }
    
    /* LUXURY SIDEBAR */
    [data-testid="stSidebar"] {
        min-width: 270px !important;
        max-width: 270px !important;
        background: linear-gradient(180deg, rgba(15,12,12,0.95) 0%, rgba(5,5,5,0.95) 100%) !important;
        border-right: 1px solid rgba(212, 175, 55, 0.2) !important; /* Gold Accent Border */
    }
    
    .title-op {
        font-family: 'Oswald', sans-serif;
        background: linear-gradient(to right, #d4af37, #ffdf00, #d4af37); /* Gold Gradient */
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 3.5rem;
        text-transform: uppercase;
        margin-bottom: 0;
        letter-spacing: 2px;
    }
    
    /* BADGES */
    .macro-badge {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(212, 175, 55, 0.1);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        transition: all 0.3s ease;
    }
    
    /* LUXURY DIRECTIVE CARD */
    .directive-card {
        background: linear-gradient(145deg, #120e0f 0%, #080606 100%);
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 15px;
        padding: 25px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.8), inset 0 0 15px rgba(212, 175, 55, 0.03);
    }
    
    /* BUTTONS */
    .btn-scan > button { 
        background: linear-gradient(90deg, #d4af37 0%, #ff9900 100%) !important; 
        border: none !important; 
        color: #000000 !important; 
        border-radius: 8px !important; 
        font-weight: 800 !important;
        font-family: 'Oswald', sans-serif;
        letter-spacing: 1px;
        font-size: 1.2rem !important;
        padding: 12px 0 !important;
        width: 100% !important;
        box-shadow: 0 5px 15px rgba(212, 175, 55, 0.3);
    }
    .btn-logout > button {
        background: transparent !important;
        border: 1px solid rgba(255, 51, 102, 0.5) !important;
        color: #ff3366 !important;
        border-radius: 8px !important;
        width: 100% !important;
        margin-top: 15px !important;
    }
    
    /* DATAFRAME STYLING HIDE HEADER INDEX */
    [data-testid="stDataFrame"] { background: transparent !important; }
</style>
""", unsafe_allow_html=True)

if st.session_state.get('logged_out', False):
    st.markdown("<div style='text-align: center; margin-top: 15vh;'><h1 style='color: #d4af37; font-family: Oswald;'>SYSTEM DISCONNECTED</h1><p style='color: #ff3366;'>Refresh browser untuk login kembali.</p></div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 2. RAW DATA MACRO DATABASE
# ==========================================
DB_MACRO_BASE = {
    "USD": {"Skor_Base": 35}, "EUR": {"Skor_Base": 10}, "GBP": {"Skor_Base": 20},
    "JPY": {"Skor_Base": -30}, "AUD": {"Skor_Base": 15}, "CAD": {"Skor_Base": 5},
    "CHF": {"Skor_Base": -15}, "NZD": {"Skor_Base": 0}
}

def fetch_live_calendar():
    impact = {k: 0 for k in DB_MACRO_BASE.keys()}
    try:
        resp = requests.get("https://nfs.gweb.io/analytics/calendar/this-week", headers={"User-Agent": "Mozilla/5.0"}, timeout=3)
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
                            if a > f: impact[curr] += 20
                            elif a < f: impact[curr] -= 20
                        except: pass
    except: pass
    return impact

# ==========================================
# 3. TECHNICAL SCANNER ENGINE (AKURAT)
# ==========================================
roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "XAUUSD=X": "GOLD (XAU/USD)"}

def fetch_op_forex(ticker):
    try:
        tk = yf.Ticker(ticker)
        df_h1 = tk.history(period="1mo", interval="1h").ffill()
        if df_h1.empty: return None
        
        df_h4 = df_h1.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
        df_d1 = df_h1.resample('1d').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()

        df_h1['EMA20'] = df_h1['Close'].ewm(span=20, adjust=False).mean()
        df_h1['EMA50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
        
        delta = df_h1['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df_h1['RSI'] = 100 - (100 / (1 + rs))
        
        df_h1['MACD'] = df_h1['Close'].ewm(span=12, adjust=False).mean() - df_h1['Close'].ewm(span=26, adjust=False).mean()
        df_h1['Signal'] = df_h1['MACD'].ewm(span=9, adjust=False).mean()
        
        tr = np.max([df_h1['High']-df_h1['Low'], np.abs(df_h1['High']-df_h1['Close'].shift()), np.abs(df_h1['Low']-df_h1['Close'].shift())], axis=0)
        df_h1['ATR'] = pd.Series(tr, index=df_h1.index).rolling(14).mean()
        
        df_h4['EMA20'] = df_h4['Close'].ewm(span=20, adjust=False).mean()
        df_d1['EMA20'] = df_d1['Close'].ewm(span=20, adjust=False).mean()

        last = df_h1.iloc[-1]
        
        h1_trend = "UP" if last['Close'] > last['EMA20'] else "DOWN"
        h4_trend = "UP" if df_h4.iloc[-1]['Close'] > df_h4.iloc[-1]['EMA20'] else "DOWN"
        d1_trend = "UP" if df_d1.iloc[-1]['Close'] > df_d1.iloc[-1]['EMA20'] else "DOWN"

        tech_score = 0
        if h1_trend == h4_trend == d1_trend == "UP": tech_score += 30
        elif h1_trend == h4_trend == d1_trend == "DOWN": tech_score -= 30
            
        if last['EMA20'] > last['EMA50']: tech_score += 15
        elif last['EMA20'] < last['EMA50']: tech_score -= 15
            
        if last['MACD'] > last['Signal']: tech_score += 15
        elif last['MACD'] < last['Signal']: tech_score -= 15
            
        if 40 <= last['RSI'] <= 65 and tech_score > 0: tech_score += 10 
        elif 35 <= last['RSI'] <= 60 and tech_score < 0: tech_score -= 10 

        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA_SCAN": float(last['Close']),
            "EMA20": float(last['EMA20']), "EMA50": float(last['EMA50']),
            "RSI": float(last['RSI']), "MACD_SIGNAL": "BULL" if last['MACD'] > last['Signal'] else "BEAR",
            "ATR": float(last['ATR']), "MTF": f"{d1_trend} | {h4_trend} | {h1_trend}",
            "TECH_SCORE": tech_score
        }
    except: return None

# ==========================================
# 4. EXECUTOR CONTROL PANEL & SIDEBAR
# ==========================================
if "op_data" not in st.session_state: st.session_state.op_data = []

with st.sidebar:
    st.markdown("<h3 style='color: #d4af37; font-family: Oswald; font-size: 1.8rem;'>☠️ OP CONTROL</h3>", unsafe_allow_html=True)
    acc_balance = st.number_input("CAPITAL (USD):", min_value=10.0, value=1000.0, step=100.0)
    risk_pct = st.slider("RISK PER TRADE (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    st.markdown("---")
    
    st.markdown('<div class="btn-scan">', unsafe_allow_html=True)
    if st.button("🔥 IGNITE SCAN"):
        with st.spinner("QUANTITATIVE SCANNING..."):
            st.session_state.cal_impact_dict = fetch_live_calendar()
            st.session_state.op_data = [fetch_op_forex(t) for t in roster_forex]
            st.session_state.op_data = [x for x in st.session_state.op_data if x is not None]
            st.session_state.last_run = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S WIB")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    st.markdown("---")
    
    with st.expander("📖 BOOK ACADEMY (FULL)"):
        st.markdown("""
        <div style="font-size:0.8rem; color:#d1d5db; line-height:1.6;">
            <b>1. CUAN CEPAT (SCALPING)</b><br>
            Mode ini menggunakan ATR 1.2x. Sangat responsif. Entry Hajar Kanan (Market) jika sinyal TITANIUM.<br><br>
            <b>2. RISK MANAGEMENT</b><br>
            Lot dihitung otomatis berdasar Risk (%). Jaga emosi, biarkan probabilitas bekerja.<br><br>
            <b>3. GOLDEN RATIO</b><br>
            TP1 (1:1) wajib diamankan (Set BEP). Sisakan lot untuk TP2 (1:2.5 Runner).
        </div>
        """, unsafe_allow_html=True)
        
    st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
    if st.button("⏻ SECURE LOG OUT"):
        st.session_state.clear()
        st.session_state['logged_out'] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# HEADER DASHBOARD
st.markdown("<p class='title-op'>JIHAN-GHINA FX <span style='color: #ffffff; font-size: 1.5rem; font-weight: 300;'>v11 LUXURY EDITION</span></p>", unsafe_allow_html=True)

if not st.session_state.op_data:
    st.markdown("<div style='background: rgba(212, 175, 55, 0.05); border: 1px dashed rgba(212, 175, 55, 0.4); padding: 40px; text-align: center; border-radius: 15px; margin-top: 30px;'><h3 style='color: #d4af37; font-family: Oswald;'>SYSTEM STANDBY</h3><p style='color: #9ca3af;'>Klik <b>IGNITE SCAN</b> di sidebar untuk memuat matriks kuantitatif.</p></div>", unsafe_allow_html=True)
else:
    st.markdown(f"<p style='color:#9ca3af; font-size: 0.85rem;'>⚡ Data Timestamp: <span style='color:#d4af37; font-weight:bold;'>{st.session_state.get('last_run', '')}</span></p>", unsafe_allow_html=True)
    
    cal_mod = st.session_state.get("cal_impact_dict", {})
    final_macro_db = {k: v["Skor_Base"] + cal_mod.get(k, 0) for k, v in DB_MACRO_BASE.items()}
    
    mac_cols = st.columns(8)
    for idx, (curr, score) in enumerate(final_macro_db.items()):
        with mac_cols[idx]:
            c_color = "#00ff88" if score > 15 else ("#ff3366" if score < -15 else "#d4af37")
            st.markdown(f'<div class="macro-badge"><p style="margin:0; font-size:0.7rem; color:#9ca3af; font-weight:bold;">{curr}</p><p style="margin:3px 0 0 0; font-size:1.3rem; font-family:Oswald; color:{c_color};">{score:+d}</p></div>', unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)

    matrix_rows = []
    
    for raw in st.session_state.op_data:
        pair = raw["NAMA"]
        if "GOLD" in pair: f_score = 30 if final_macro_db["USD"] < 0 else -30
        else:
            try:
                b, q = pair.split("/")
                f_score = final_macro_db[b] - final_macro_db[q]
            except: f_score = 0
            
        total_score = raw["TECH_SCORE"] + f_score
        
        if total_score >= 60: rek = "🔥 TITANIUM BUY"
        elif total_score >= 30: rek = "🟢 STRONG BUY"
        elif total_score <= -60: rek = "🩸 TITANIUM SELL"
        elif total_score <= -30: rek = "🔴 STRONG SELL"
        else: rek = "⚪ NEUTRAL"
        
        matrix_rows.append({
            "ASSET": pair,
            "PRICE": f"{raw['HARGA_SCAN']:.4f}" if "JPY" not in pair else f"{raw['HARGA_SCAN']:.2f}",
            "MTF": raw["MTF"],
            "RSI": round(raw["RSI"], 1),
            "FUND": f_score,
            "SCORE": total_score,
            "SIGNAL": rek
        })

    def style_matrix(val):
        if isinstance(val, str):
            if "TITANIUM BUY" in val: return 'color: #00ff88; font-weight: 900;'
            elif "STRONG BUY" in val: return 'color: #00ff88;'
            elif "TITANIUM SELL" in val: return 'color: #ff3366; font-weight: 900;'
            elif "STRONG SELL" in val: return 'color: #ff3366;'
        elif isinstance(val, (int, float)):
            if val > 30: return 'color: #00ff88;'
            elif val < -30: return 'color: #ff3366;'
        return 'color: #d1d5db;'

    st.dataframe(pd.DataFrame(matrix_rows).style.map(style_matrix), use_container_width=True, hide_index=True)

    # ==========================================
    # 5. TITANIUM EXECUTION MANAGER (AKURAT & MOBILE-SAFE)
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='font-family: Oswald; color: #d4af37;'>🎯 TACTICAL EXECUTION</h3>", unsafe_allow_html=True)
    
    col1, col2 = st.columns([1, 2])
    with col1:
        pilihan = st.selectbox("SELECT ASSET:", [x["NAMA"] for x in st.session_state.op_data], key="pair_selector")
    
    if st.session_state.pair_selector:
        active_data = next((item for item in st.session_state.op_data if item["NAMA"] == st.session_state.pair_selector), None)
        active_matrix = next((item for item in matrix_rows if item["ASSET"] == st.session_state.pair_selector), None)
        
        if active_data and active_matrix:
            try:
                live_tk = yf.Ticker(active_data["TICKER"])
                live_price_df = live_tk.history(period="1d", interval="1m")
                live_harga = float(live_price_df['Close'].iloc[-1]) if not live_price_df.empty else active_data["HARGA_SCAN"]
            except:
                live_harga = active_data["HARGA_SCAN"]

            atr = active_data["ATR"]
            sig = active_matrix["SIGNAL"]
            score = active_matrix["SCORE"]
            f_score = active_matrix["FUND"]
            
            # SCALPING LOGIC - CEPET CUAN
            sl_dist = 1.2 * atr  # Sangat ketat
            risk_amount = acc_balance * (risk_pct / 100)
            
            if "JPY" in active_data["TICKER"]: 
                pips, pip_val, fmt = sl_dist * 100, 7.00, ".3f"
            elif "XAU" in active_data["TICKER"]: 
                pips, pip_val, fmt = sl_dist * 10, 10.0, ".3f"
            else: 
                pips, pip_val, fmt = sl_dist * 10000, 10.0, ".5f"
                
            lot = max(0.01, round((risk_amount / (pips * pip_val)) if pips > 0 else 0, 2))
            
            menit_sisa = 60 - datetime.now(pytz.timezone('Asia/Jakarta')).minute
            
            is_buy = "BUY" in sig
            is_sell = "SELL" in sig
            is_titanium = "TITANIUM" in sig

            # DYNAMIC ENTRY: Titanium = Market Exe (Hajar harga sekarang), Strong = Limit (Tunggu di EMA20)
            if is_buy:
                entry_area = live_harga if is_titanium else active_data['EMA20']
                sl = entry_area - sl_dist
                tp1 = entry_area + (sl_dist * 1.0) # 1:1 Cepet Cuan
                tp2 = entry_area + (sl_dist * 2.5) # Runner
                color = "#00ff88"
                entry_str = f"{entry_area:{fmt}}"
            elif is_sell:
                entry_area = live_harga if is_titanium else active_data['EMA20']
                sl = entry_area + sl_dist
                tp1 = entry_area - (sl_dist * 1.0) # 1:1 Cepet Cuan
                tp2 = entry_area - (sl_dist * 2.5) # Runner
                color = "#ff3366"
                entry_str = f"{entry_area:{fmt}}"
            else:
                sl = tp1 = tp2 = live_harga
                lot, color, entry_str = 0.00, "#9ca3af", "N/A"

            # PERBAIKAN HTML: Flexbox agar tidak pecah/turun baris di layar HP
            html_content = f"""
            <div class="directive-card">
                <h3 style="color: {color}; font-family: Oswald; font-size: 2rem; margin-bottom: 5px;">{sig}</h3>
                <p style="color: #ffffff; font-size: 1.1rem; margin-bottom: 5px;">Live Price: <span style="color: #d4af37; font-weight: bold;">{format(live_harga, fmt)}</span></p>
                <p style="color: rgba(255,255,255,0.5); font-size: 0.8rem; margin-bottom: 20px;">⏳ EXPIRED IN: {menit_sisa} Min</p>
                
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.5); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.05); flex-wrap: nowrap;">
                    
                    <div style="text-align: center; flex: 1; padding: 0 5px;">
                        <p style="color: #9ca3af; font-size: 0.65rem; margin: 0; font-weight: bold; letter-spacing: 1px;">LOT</p>
                        <p style="color: #ffffff; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0; white-space: nowrap;">{lot}</p>
                    </div>
                    
                    <div style="text-align: center; flex: 1; padding: 0 5px; border-left: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #9ca3af; font-size: 0.65rem; margin: 0; font-weight: bold; letter-spacing: 1px;">ENTRY</p>
                        <p style="color: #d4af37; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0; white-space: nowrap;">{entry_str}</p>
                    </div>
                    
                    <div style="text-align: center; flex: 1; padding: 0 5px; border-left: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #9ca3af; font-size: 0.65rem; margin: 0; font-weight: bold; letter-spacing: 1px;">STOP LOSS</p>
                        <p style="color: #ff3366; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0; white-space: nowrap;">{format(sl, fmt)}</p>
                    </div>
                    
                    <div style="text-align: center; flex: 1; padding: 0 5px; border-left: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #9ca3af; font-size: 0.65rem; margin: 0; font-weight: bold; letter-spacing: 1px;">TARGET</p>
                        <p style="color: #00ff88; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0; white-space: nowrap;">{format(tp1, fmt)}</p>
                        <p style="color: #00ff88; font-size: 0.8rem; font-family: Oswald; opacity: 0.7; margin: 0; white-space: nowrap;">{format(tp2, fmt)}</p>
                    </div>
                    
                </div>
            </div>
            """
            st.markdown(html_content, unsafe_allow_html=True)
            
            # Visualizer minimalis dihilangkan agar fokus ke eksekusi cepat (sesuai request) atau bisa Anda tambahkan kembali modul visualizer sebelumnya jika diperlukan.
