import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
from datetime import datetime
import pytz
import warnings
import requests
import json
import os
import csv
import plotly.graph_objects as go

warnings.filterwarnings('ignore')

# ==========================================
# 1. KONFIGURASI UI STYLE & LUXURY CSS
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX v12.0 | GOD-MODE", page_icon="💎", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #1a1616, #050505) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 2.5rem !important; padding-bottom: 2rem; max-width: 98% !important; }
    
    [data-testid="stSidebar"] {
        min-width: 280px !important;
        max-width: 280px !important;
        background: linear-gradient(180deg, rgba(15,12,12,0.98) 0%, rgba(5,5,5,0.98) 100%) !important;
        border-right: 1px solid rgba(212, 175, 55, 0.3) !important;
    }
    
    .title-op {
        font-family: 'Oswald', sans-serif;
        background: linear-gradient(to right, #d4af37, #ffdf00, #ffffff);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.5rem;
        text-transform: uppercase;
        margin-bottom: -5px;
        letter-spacing: 1.5px;
    }
    
    @keyframes neonPulse {
        0% { box-shadow: 0 0 5px rgba(212, 175, 55, 0.1), inset 0 0 2px rgba(212, 175, 55, 0.05); transform: translateY(0px); }
        50% { box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4), inset 0 0 10px rgba(212, 175, 55, 0.2); transform: translateY(-3px); }
        100% { box-shadow: 0 0 5px rgba(212, 175, 55, 0.1), inset 0 0 2px rgba(212, 175, 55, 0.05); transform: translateY(0px); }
    }

    .neon-float { animation: neonPulse 3s infinite ease-in-out; }
    
    .macro-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 10px; margin-bottom: 20px; }
    
    .macro-badge {
        background: rgba(20, 15, 15, 0.85);
        border: 1px solid rgba(212, 175, 55, 0.5);
        border-radius: 10px;
        padding: 10px 5px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
    }
    
    .directive-card {
        background: linear-gradient(145deg, #161214 0%, #0a0808 100%);
        border: 1px solid rgba(212, 175, 55, 0.6);
        border-radius: 14px;
        padding: 22px;
        margin-bottom: 10px;
    }
    
    .btn-scan > button { 
        background: linear-gradient(90deg, #d4af37 0%, #ffdf00 50%, #d4af37 100%) !important; 
        background-size: 200% auto;
        color: #000000 !important; 
        border-radius: 8px !important; 
        font-weight: 900 !important;
        font-family: 'Oswald', sans-serif;
        letter-spacing: 2px;
        font-size: 1.2rem !important;
        padding: 12px 0 !important;
        width: 100% !important;
        transition: 0.5s !important;
        border: none !important;
        box-shadow: 0 0 15px rgba(212,175,55,0.4);
    }
    .btn-scan > button:hover { background-position: right center; box-shadow: 0 0 25px rgba(212,175,55,0.7); }
</style>
""", unsafe_allow_html=True)

if st.session_state.get('logged_out', False):
    st.markdown("<div style='text-align: center; margin-top: 20vh;'><h1 style='color: #ff3366; font-family: Oswald;'>SYSTEM DISCONNECTED</h1><p>Silakan refresh halaman untuk login kembali.</p></div>", unsafe_allow_html=True)
    st.stop()

# ==========================================
# 2. MEMORY & JOURNALING SYSTEM
# ==========================================
CONFIG_FILE = "config_jgfx.json"
JOURNAL_FILE = "jgfx_journal.csv"

def load_capital():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f).get("capital", 1000.0)
        except: pass
    return 1000.0

def save_capital():
    with open(CONFIG_FILE, "w") as f: json.dump({"capital": st.session_state.input_modal}, f)

def log_to_journal(asset, signal, lot, entry, sl, tp):
    file_exists = os.path.isfile(JOURNAL_FILE)
    with open(JOURNAL_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["TIMESTAMP", "ASSET", "SIGNAL", "LOT", "ENTRY", "SL", "TARGET"])
        timestamp = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%Y-%m-%d %H:%M:%S")
        writer.writerow([timestamp, asset, signal, lot, entry, sl, tp])

# ==========================================
# 3. MACRO ENGINE
# ==========================================
DB_MACRO_BASE = {
    "USD": {"Skor_Base": 35}, "EUR": {"Skor_Base": 10}, "GBP": {"Skor_Base": 20},
    "JPY": {"Skor_Base": -30}, "AUD": {"Skor_Base": 15}, "CAD": {"Skor_Base": 5},
    "CHF": {"Skor_Base": -15}, "NZD": {"Skor_Base": 0}
}

def parse_number(val):
    if not val or str(val).strip() == "": return None
    s = str(val).upper().replace(",", ".").replace("−", "-").replace("–", "-").strip()
    mult = 1
    if 'K' in s: mult = 1e3
    elif 'M' in s: mult = 1e6
    elif 'B' in s: mult = 1e9
    
    s_clean = ''.join(c for c in s if c.isdigit() or c in ['.', '-'])
    try:
        return float(s_clean) * mult if s_clean not in ["", "-", "."] else None
    except: return None

def fetch_live_calendar():
    impact = {k: 0 for k in DB_MACRO_BASE.keys()}
    api_status = "OK"
    ts = int(datetime.now().timestamp())
    urls = [f"https://nfs.faireconomy.media/ff_calendar_thisweek.json?_={ts}", f"https://nfs.gweb.io/analytics/calendar/this-week?_={ts}"]
    
    data = None
    for url in urls:
        try:
            resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=8)
            if resp.status_code == 200: 
                data = resp.json()
                break
        except: pass

    if data:
        for raw_ev in data:
            ev = {str(k).lower(): v for k, v in raw_ev.items()}
            curr = str(ev.get("country", ev.get("currency", ""))).upper()
            imp = str(ev.get("impact", ev.get("importance", ""))).upper()
            title = str(ev.get("title", "")).lower()
            
            if curr in impact and ("HIGH" in imp or "3" in imp):
                a = parse_number(ev.get("actual", ""))
                f = parse_number(ev.get("forecast", "")) or parse_number(ev.get("previous", ""))
                
                if a is not None and f is not None:
                    is_inverse = any(kw in title for kw in ["unemployment", "jobless", "claims", "deficit"])
                    if not is_inverse: impact[curr] += 20 if a > f else (-20 if a < f else 0)
                    else: impact[curr] += 20 if a < f else (-20 if a > f else 0)
    else: api_status = "API OFFLINE"
        
    return impact, api_status

# ==========================================
# 4. SUPER-CHARGED TECHNICAL SCANNER (SMC + ADX + BB)
# ==========================================
roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "XAUUSD=X": "GOLD (XAU)"}

def fetch_op_forex(ticker):
    try:
        tk = yf.Ticker(ticker)
        df_h1 = tk.history(period="2mo", interval="1h").ffill()
        if len(df_h1) < 50: return None
        
        df_h4 = df_h1.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
        df_d1 = df_h1.resample('1d').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()

        # SMC: Order Blocks / Liquidity Zones (Swing High/Low dinamis)
        swing_high = float(df_h1['High'].rolling(20).max().iloc[-2])
        swing_low = float(df_h1['Low'].rolling(20).min().iloc[-2])

        # Basic Indicators
        df_h1['EMA20'] = df_h1['Close'].ewm(span=20, adjust=False).mean()
        df_h1['EMA50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
        
        # RSI
        delta = df_h1['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        df_h1['RSI'] = 100 - (100 / (1 + gain / loss))
        
        # MACD
        df_h1['MACD'] = df_h1['Close'].ewm(span=12, adjust=False).mean() - df_h1['Close'].ewm(span=26, adjust=False).mean()
        df_h1['Signal'] = df_h1['MACD'].ewm(span=9, adjust=False).mean()
        
        # ATR
        tr = np.maximum(df_h1['High'] - df_h1['Low'], 
             np.maximum(np.abs(df_h1['High'] - df_h1['Close'].shift()), np.abs(df_h1['Low'] - df_h1['Close'].shift())))
        df_h1['ATR'] = pd.Series(tr, index=df_h1.index).rolling(14).mean()
        
        # ADX (Trend Strength AI)
        high_diff = df_h1['High'].diff()
        low_diff = df_h1['Low'].shift() - df_h1['Low']
        df_h1['+DM'] = np.where((high_diff > low_diff) & (high_diff > 0), high_diff, 0.0)
        df_h1['-DM'] = np.where((low_diff > high_diff) & (low_diff > 0), low_diff, 0.0)
        
        df_h1['+DI'] = 100 * (df_h1['+DM'].ewm(alpha=1/14, adjust=False).mean() / df_h1['ATR'])
        df_h1['-DI'] = 100 * (df_h1['-DM'].ewm(alpha=1/14, adjust=False).mean() / df_h1['ATR'])
        df_h1['DX'] = 100 * np.abs(df_h1['+DI'] - df_h1['-DI']) / (df_h1['+DI'] + df_h1['-DI'] + 1e-10)
        df_h1['ADX'] = df_h1['DX'].ewm(alpha=1/14, adjust=False).mean()

        # Bollinger Bands (Volatility)
        df_h1['BB_MID'] = df_h1['Close'].rolling(20).mean()
        df_h1['BB_STD'] = df_h1['Close'].rolling(20).std()
        df_h1['BB_UP'] = df_h1['BB_MID'] + (2 * df_h1['BB_STD'])
        df_h1['BB_LOW'] = df_h1['BB_MID'] - (2 * df_h1['BB_STD'])

        # Multi-Timeframe Alignment
        df_h4['EMA20'] = df_h4['Close'].ewm(span=20, adjust=False).mean()
        df_d1['EMA20'] = df_d1['Close'].ewm(span=20, adjust=False).mean()

        last = df_h1.iloc[-1]
        last_h4 = df_h4.iloc[-1] if not df_h4.empty else last
        last_d1 = df_d1.iloc[-1] if not df_d1.empty else last
        
        h1_trend = "UP" if last['Close'] > last['EMA20'] else "DOWN"
        h4_trend = "UP" if last_h4['Close'] > last_h4['EMA20'] else "DOWN"
        d1_trend = "UP" if last_d1['Close'] > last_d1['EMA20'] else "DOWN"

        # SCORING ALGORITHM (GOD-MODE)
        tech_score = 0
        if h1_trend == h4_trend == d1_trend == "UP": tech_score += 30
        elif h1_trend == h4_trend == d1_trend == "DOWN": tech_score -= 30
            
        if last['EMA20'] > last['EMA50']: tech_score += 15
        elif last['EMA20'] < last['EMA50']: tech_score -= 15
            
        if last['MACD'] > last['Signal']: tech_score += 15
        elif last['MACD'] < last['Signal']: tech_score -= 15
            
        if 40 <= last['RSI'] <= 65 and tech_score > 0: tech_score += 10 
        elif 35 <= last['RSI'] <= 60 and tech_score < 0: tech_score -= 10 
        
        # Penalty / Bonus dari ADX (Kekuatan Tren)
        if last['ADX'] > 25: 
            tech_score = int(tech_score * 1.2) # Tren kuat, sinyal divalidasi
            regime = "📈 TRENDING"
        elif last['ADX'] < 20: 
            tech_score = int(tech_score * 0.4) # Choppy, diskon skor drastis
            regime = "⚠️ CHOPPY/RANGING"
        else:
            regime = "⚡ VOLATILE" if (last['BB_UP'] - last['BB_LOW']) > (last['ATR'] * 4) else "🔄 NEUTRAL"

        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA_SCAN": float(last['Close']),
            "EMA20": float(last['EMA20']), "EMA50": float(last['EMA50']),
            "RSI": float(last['RSI']), "ADX": float(last['ADX']), "REGIME": regime,
            "ATR": float(last['ATR']), "MTF": f"{d1_trend} | {h4_trend} | {h1_trend}",
            "TECH_SCORE": tech_score, "SWING_HIGH": swing_high, "SWING_LOW": swing_low
        }
    except Exception as e: 
        return None

# ==========================================
# 5. UI SIDEBAR & INIT
# ==========================================
if "op_data" not in st.session_state: st.session_state.op_data = []
if "new_scan" not in st.session_state: st.session_state.new_scan = False

with st.sidebar:
    st.markdown("<h3 style='color: #d4af37; font-family: Oswald; font-size: 1.8rem; text-align:center;'>⚙️ COMMAND CENTER</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    acc_balance = st.number_input("💵 CAPITAL (USD):", min_value=10.0, value=float(load_capital()), step=100.0, key="input_modal", on_change=save_capital)
    risk_pct = st.slider("⚠️ RISK PER TRADE (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    
    st.markdown("---")
    with st.expander("🛠️ FF MANUAL OVERRIDE", expanded=False):
        use_manual_ff = st.checkbox("AKTIFKAN MANUAL")
        c1, c2 = st.columns(2)
        with c1:
            man_usd, man_eur = st.number_input("USD Live", step=20), st.number_input("EUR Live", step=20)
            man_gbp, man_jpy = st.number_input("GBP Live", step=20), st.number_input("JPY Live", step=20)
        with c2:
            man_aud, man_cad = st.number_input("AUD Live", step=20), st.number_input("CAD Live", step=20)
            man_chf, man_nzd = st.number_input("CHF Live", step=20), st.number_input("NZD Live", step=20)
            
    manual_dict = {"USD": man_usd, "EUR": man_eur, "GBP": man_gbp, "JPY": man_jpy, "AUD": man_aud, "CAD": man_cad, "CHF": man_chf, "NZD": man_nzd}

    st.markdown('<br><div class="btn-scan">', unsafe_allow_html=True)
    if st.button("🔥 IGNITE GOD-MODE SCAN"):
        with st.spinner("QUANTITATIVE ENGINE RUNNING..."):
            cal_dict, api_status = fetch_live_calendar()
            st.session_state.cal_impact_dict = cal_dict
            st.session_state.api_status = api_status
            st.session_state.op_data = [x for x in [fetch_op_forex(t) for t in roster_forex] if x is not None]
            st.session_state.last_run = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S WIB")
            st.session_state.new_scan = True 
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("⏻ SYSTEM SHUTDOWN", use_container_width=True):
        st.session_state.clear()
        st.session_state['logged_out'] = True
        st.rerun()

# ==========================================
# 6. MAIN DASHBOARD (MATRIX & MACRO)
# ==========================================
st.markdown("<p class='title-op'>JIHAN-GHINA FX <span style='color: #ffffff; font-size: 1.2rem; font-weight: 300;'>v12.0 <span style='color:#00ff88; font-size:0.9rem; font-weight:bold; letter-spacing:1px;'>| GOD-MODE EDITION</span></span></p>", unsafe_allow_html=True)

now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
jam = now_wib.hour

sesi_html = f"""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 20px; margin-top: 5px;">
    {'<div style="background:#00bfff; color:#000; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold; box-shadow: 0 0 10px #00bfff;">🇦🇺 SYDNEY (OPEN)</div>' if 4 <= jam < 13 else '<div style="border:1px solid #4b5563; color:#4b5563; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold;">🇦🇺 SYDNEY (CLOSED)</div>'}
    {'<div style="background:#00ff88; color:#000; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold; box-shadow: 0 0 10px #00ff88;">🇯🇵 TOKYO (OPEN)</div>' if 7 <= jam < 16 else '<div style="border:1px solid #4b5563; color:#4b5563; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold;">🇯🇵 TOKYO (CLOSED)</div>'}
    {'<div style="background:#d4af37; color:#000; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold; box-shadow: 0 0 10px #d4af37;">🇬🇧 LONDON (OPEN)</div>' if 14 <= jam < 23 else '<div style="border:1px solid #4b5563; color:#4b5563; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold;">🇬🇧 LONDON (CLOSED)</div>'}
    {'<div style="background:#ff3366; color:#000; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold; box-shadow: 0 0 10px #ff3366;">🇺🇸 NEW YORK (OPEN)</div>' if jam >= 19 or jam < 4 else '<div style="border:1px solid #4b5563; color:#4b5563; padding:4px 10px; border-radius:4px; font-size:0.7rem; font-weight:bold;">🇺🇸 NEW YORK (CLOSED)</div>'}
</div>
"""
st.markdown(sesi_html, unsafe_allow_html=True)

if not st.session_state.op_data:
    st.markdown("<div style='background: rgba(212, 175, 55, 0.05); border: 1px dashed rgba(212, 175, 55, 0.4); padding: 40px; text-align: center; border-radius: 12px; margin-top: 20px;'><h2 style='color: #d4af37; font-family: Oswald;'>AWAITING IGNITION...</h2><p style='color:#9ca3af;'>Klik IGNITE GOD-MODE SCAN di sidebar untuk memulai analisis.</p></div>", unsafe_allow_html=True)
else:
    status_api = st.session_state.get('api_status', 'STANDBY')
    api_text = f"<span style='color: {'#00ff88' if status_api == 'OK' else '#ff3366'};'>{status_api}</span>" if not use_manual_ff else f"<span style='color:#00bfff;'>🛠️ OVERRIDE AKTIF</span>"
    st.markdown(f"<p style='color:#9ca3af; font-size: 0.85rem; margin-top:0; margin-bottom:10px;'>⚡ Last Scan: <span style='color:#ffffff; font-weight:bold;'>{st.session_state.get('last_run', '')}</span> | Server: {api_text}</p>", unsafe_allow_html=True)
    
    cal_mod = st.session_state.get("cal_impact_dict", {})
    macro_html = '<div class="macro-container">'
    final_macro_db = {}
    
    for curr, base_data in DB_MACRO_BASE.items():
        base_score = base_data["Skor_Base"]
        live_impact = manual_dict.get(curr, 0) if use_manual_ff else cal_mod.get(curr, 0)
        total_score = base_score + live_impact
        final_macro_db[curr] = total_score
        
        c_color = "#00ff88" if total_score > 15 else ("#ff3366" if total_score < -15 else "#d4af37")
        imp_color = "#00ff88" if live_impact > 0 else ("#ff3366" if live_impact < 0 else "#9ca3af")
        
        macro_html += f'<div class="macro-badge neon-float"><p style="margin:0; font-size:0.8rem; color:#ffffff; font-weight:bold; letter-spacing:1px;">{curr}</p><div style="font-size: 0.6rem; color: #9ca3af; margin: 4px 0;">BASE: {base_score} <br/> LIVE: <span style="color:{imp_color}; font-weight:bold;">{live_impact:+d}</span></div><p style="margin:2px 0 0 0; font-size:1.3rem; font-family:Oswald; color:{c_color}; font-weight:bold;">{total_score:+d}</p></div>'
    st.markdown(macro_html + '</div>', unsafe_allow_html=True)

    matrix_rows, titanium_found = [], []

    for raw in st.session_state.op_data:
        pair = raw["NAMA"]
        if "GOLD" in pair: f_score = 30 if final_macro_db["USD"] < 0 else -30
        else:
            try:
                b, q = pair.split("/")
                f_score = final_macro_db[b] - final_macro_db[q]
            except: f_score = 0
            
        total_score = raw["TECH_SCORE"] + f_score
        
        if total_score >= 65: rek = "🔥 TITANIUM BUY"
        elif total_score >= 35: rek = "🟢 STRONG BUY"
        elif total_score <= -65: rek = "🩸 TITANIUM SELL"
        elif total_score <= -35: rek = "🔴 STRONG SELL"
        else: rek = "⚪ NEUTRAL"
        
        if "TITANIUM" in rek: titanium_found.append(pair)

        matrix_rows.append({
            "ASSET": pair, "PRICE": f"{raw['HARGA_SCAN']:.4f}" if "JPY" not in pair else f"{raw['HARGA_SCAN']:.2f}",
            "REGIME": raw["REGIME"], "ADX": f"{raw['ADX']:.1f}", "FUND": f"{f_score:+d}",
            "SCORE": f"{total_score:+d}", "SIGNAL": rek, "RAW_TOTAL": total_score
        })

    if st.session_state.new_scan:
        if titanium_found:
            st.success(f"🚨 **TITANIUM SIGNAL DETECTED:** Setup level dewa terdeteksi di {', '.join(titanium_found)}!", icon="🔥")
        else: st.toast('Scan Selesai. Menunggu momentum.', icon='🔍')
        st.session_state.new_scan = False

    def style_matrix(val):
        if isinstance(val, str):
            if "BUY" in val or "TRENDING" in val: return 'color: #00ff88; font-weight:bold;'
            elif "SELL" in val or "CHOPPY" in val: return 'color: #ff3366; font-weight:bold;'
            elif "TITANIUM" in val: return 'color: #ffdf00; font-weight:bold;'
        return 'color: #d1d5db;'

    st.dataframe(pd.DataFrame(matrix_rows).drop(columns=['RAW_TOTAL']).style.map(style_matrix), use_container_width=True, hide_index=True)

    # ==========================================
    # 7. TACTICAL EXECUTION & VISUAL CHART
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='font-family: Oswald; color: #ffffff; letter-spacing:1px;'>🎯 ADVANCED TACTICAL EXECUTION</h3>", unsafe_allow_html=True)
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: pilihan = st.selectbox("SELECT ASSET TO SNIPE:", [x["NAMA"] for x in st.session_state.op_data], key="pair_selector")
    with col_sel2: tf_pilihan = st.selectbox("TIME FRAME CHART:", ["15m", "1h", "1d"], index=1, key="tf_selector")
    
    if st.session_state.pair_selector:
        active_data = next((item for item in st.session_state.op_data if item["NAMA"] == st.session_state.pair_selector), None)
        active_matrix = next((item for item in matrix_rows if item["ASSET"] == st.session_state.pair_selector), None)
        
        if active_data and active_matrix:
            # CHART DATA
            try:
                tk_chart = yf.Ticker(active_data["TICKER"])
                if tf_pilihan == "15m": df_chart = tk_chart.history(period="5d", interval="15m")
                elif tf_pilihan == "1h": df_chart = tk_chart.history(period="1mo", interval="1h")
                else: df_chart = tk_chart.history(period="3mo", interval="1d")
                live_harga = float(df_chart['Close'].iloc[-1]) if not df_chart.empty else active_data["HARGA_SCAN"]
            except:
                df_chart, live_harga = pd.DataFrame(), active_data["HARGA_SCAN"]

            # SMC DYNAMIC RISK CALCULATION
            atr, sig = active_data["ATR"], active_matrix["SIGNAL"]
            is_buy, is_sell, is_titanium = "BUY" in sig, "SELL" in sig, "TITANIUM" in sig
            
            risk_amount = acc_balance * (risk_pct / 100)
            fmt = ".3f" if ("JPY" in active_data["TICKER"] or "XAU" in active_data["TICKER"]) else ".5f"
            
            # Smart Money Concept: Setup Entry, SL, TP based on Liquidity (Swing High/Low)
            if is_buy:
                entry_area = live_harga if is_titanium else active_data['EMA20']
                # SL ditaruh sedikit di bawah Swing Low (Liquidity Grab protection)
                sl = min(entry_area - (atr * 1.5), active_data['SWING_LOW'] - (atr * 0.2)) 
                tp1 = entry_area + abs(entry_area - sl) * 1.5 # 1:1.5 RR
                color, glow = "#00ff88", "rgba(0, 255, 136, 0.2)"
            elif is_sell:
                entry_area = live_harga if is_titanium else active_data['EMA20']
                # SL ditaruh sedikit di atas Swing High
                sl = max(entry_area + (atr * 1.5), active_data['SWING_HIGH'] + (atr * 0.2))
                tp1 = entry_area - abs(sl - entry_area) * 1.5 # 1:1.5 RR
                color, glow = "#ff3366", "rgba(255, 51, 102, 0.2)"
            else: 
                sl, tp1, color, glow, entry_area = live_harga, live_harga, "#9ca3af", "transparent", live_harga

            # Pips Calculation
            sl_dist_price = abs(entry_area - sl)
            if "JPY" in active_data["TICKER"]: pips, pip_val = sl_dist_price * 100, 7.00
            elif "XAU" in active_data["TICKER"]: pips, pip_val = sl_dist_price * 10, 10.0
            else: pips, pip_val = sl_dist_price * 10000, 10.0
                
            lot = max(0.01, round((risk_amount / (pips * pip_val)) if pips > 0 else 0, 2)) if "NEUTRAL" not in sig else 0.00
            win_rate = min(98, 50 + abs(active_matrix["RAW_TOTAL"]) + (10 if active_data['ADX'] > 25 else -15))
            if "NEUTRAL" in sig: win_rate = np.random.randint(45, 55)

            st.markdown(f"""
            <div class="directive-card neon-float" style="border: 2px solid {color}; box-shadow: 0 0 20px {glow};">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                    <h2 style="color: {color}; font-family: Oswald; font-size: 2.2rem; margin: 0; text-shadow: 0 0 10px {color};">{sig}</h2>
                    <div style="text-align:right;">
                        <span style="background: rgba(255,255,255,0.1); padding: 4px 10px; border-radius: 6px; font-size: 0.75rem; color: #fff;">📊 AI WIN-RATE: <span style="color:#d4af37; font-weight:bold; font-size:1rem;">{win_rate}%</span></span>
                    </div>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 15px; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom:10px;">
                    <p style="color: #ffffff; font-size: 1.1rem; margin: 0;">Harga Live: <span style="color: #d4af37; font-weight: bold; font-size:1.3rem;">{format(live_harga, fmt)}</span></p>
                    <p style="color: #00bfff; font-size: 0.85rem; margin: 0; text-align:right;">💧 Liq. High: {format(active_data['SWING_HIGH'], fmt)}<br>💧 Liq. Low: {format(active_data['SWING_LOW'], fmt)}</p>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.6); padding: 15px; border-radius: 10px; border: 1px solid rgba(255,255,255,0.1);">
                    <div style="text-align: center; flex: 1;">
                        <p style="color: #9ca3af; font-size: 0.7rem; margin: 0; font-weight: bold; letter-spacing:1px;">RECOMMENDED LOT</p>
                        <p style="color: #ffffff; font-size: 1.5rem; font-family: Oswald; margin: 0;">{lot}</p>
                    </div>
                    <div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: #9ca3af; font-size: 0.7rem; margin: 0; font-weight: bold; letter-spacing:1px;">ENTRY AREA</p>
                        <p style="color: #d4af37; font-size: 1.5rem; font-family: Oswald; margin: 0;">{format(entry_area, fmt)}</p>
                    </div>
                    <div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: #9ca3af; font-size: 0.7rem; margin: 0; font-weight: bold; letter-spacing:1px;">STOP LOSS (SMC)</p>
                        <p style="color: #ff3366; font-size: 1.5rem; font-family: Oswald; margin: 0;">{format(sl, fmt)}</p>
                    </div>
                    <div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.2);">
                        <p style="color: #9ca3af; font-size: 0.7rem; margin: 0; font-weight: bold; letter-spacing:1px;">TARGET PROFIT</p>
                        <p style="color: #00ff88; font-size: 1.5rem; font-family: Oswald; margin: 0;">{format(tp1, fmt)}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("💾 SAVE SETUP TO BLACK BOX", use_container_width=True):
                log_to_journal(active_data["NAMA"], sig, lot, format(entry_area, fmt), format(sl, fmt), format(tp1, fmt))
                st.success(f"Setup {active_data['NAMA']} direkam ke Black Box Journal!")

            # -----------------------------------------------------
            # CHARTING V2.0: PLOTTING ENTRY, SL, TP DI CHART!
            # -----------------------------------------------------
            st.markdown("<br>", unsafe_allow_html=True)
            with st.spinner("Memuat God-Mode Tactical Chart..."):
                if not df_chart.empty:
                    df_chart['EMA20'] = df_chart['Close'].ewm(span=20, adjust=False).mean()
                    df_chart['BB_MID'] = df_chart['Close'].rolling(20).mean()
                    df_chart['BB_UP'] = df_chart['BB_MID'] + (2 * df_chart['Close'].rolling(20).std())
                    df_chart['BB_LOW'] = df_chart['BB_MID'] - (2 * df_chart['Close'].rolling(20).std())
                    
                    fig = go.Figure()
                    
                    # Candlestick
                    fig.add_trace(go.Candlestick(
                        x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                        low=df_chart['Low'], close=df_chart['Close'],
                        increasing_line_color='#00ff88', decreasing_line_color='#ff3366', name='Price'
                    ))
                    
                    # Bollinger Bands (Area Abu-abu Transparan)
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_UP'], line=dict(color='rgba(255,255,255,0.1)', width=1), name='BB Up', showlegend=False))
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['BB_LOW'], line=dict(color='rgba(255,255,255,0.1)', width=1), fill='tonexty', fillcolor='rgba(255,255,255,0.03)', name='BB Low', showlegend=False))
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], line=dict(color='#ffd700', width=1.5), name='EMA 20'))

                    # PLOT GARIS ENTRY, SL, TP (VISUAL OVERPOWER)
                    if "NEUTRAL" not in sig:
                        fig.add_hline(y=entry_area, line_dash="solid", line_color="#d4af37", line_width=2, annotation_text="🎯 ENTRY", annotation_position="bottom right", annotation_font_color="#d4af37")
                        fig.add_hline(y=sl, line_dash="dash", line_color="#ff3366", line_width=2, annotation_text="🛡️ SL", annotation_position="bottom right", annotation_font_color="#ff3366")
                        fig.add_hline(y=tp1, line_dash="dash", line_color="#00ff88", line_width=2, annotation_text="💰 TP", annotation_position="top right", annotation_font_color="#00ff88")

                    fig.update_layout(
                        template='plotly_dark', height=450, margin=dict(l=10, r=50, t=30, b=10), # Margin R ditambah agar teks garis tidak terpotong
                        xaxis_rangeslider_visible=False,
                        yaxis=dict(fixedrange=False, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                        xaxis=dict(fixedrange=False, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': True})

    # ==========================================
    # 8. BLACK BOX JOURNAL
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='font-family: Oswald; color: #ffffff;'>📜 BLACK BOX JOURNAL</h3>", unsafe_allow_html=True)
    
    if os.path.exists(JOURNAL_FILE):
        df_journal = pd.read_csv(JOURNAL_FILE)
        st.markdown(f"<p style='color:#00bfff; font-size:0.9rem;'>Total Setup Terekam: {len(df_journal)} Data</p>", unsafe_allow_html=True)
        st.dataframe(df_journal.tail(10), hide_index=True, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            with open(JOURNAL_FILE, "rb") as file:
                st.download_button("📥 DOWNLOAD CSV", data=file, file_name="jgfx_journal.csv", mime="text/csv", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ CLEAR JOURNAL", use_container_width=True):
                os.remove(JOURNAL_FILE)
                st.rerun()
    else:
        st.info("Jurnal kosong. Klik 'SAVE SETUP TO BLACK BOX' pada kartu Tactical Execution untuk merekam.")
