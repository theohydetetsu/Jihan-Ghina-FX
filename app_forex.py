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
st.set_page_config(page_title="JIHAN-GHINA FX v11.9", page_icon="💎", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #1a1616, #050505) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 3.5rem !important; padding-bottom: 2rem; max-width: 100% !important; }
    
    [data-testid="stSidebar"] {
        min-width: 270px !important;
        max-width: 270px !important;
        background: linear-gradient(180deg, rgba(15,12,12,0.98) 0%, rgba(5,5,5,0.98) 100%) !important;
        border-right: 1px solid rgba(212, 175, 55, 0.2) !important;
    }
    
    .title-op {
        font-family: 'Oswald', sans-serif;
        background: linear-gradient(to right, #d4af37, #ffdf00, #d4af37);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 2.2rem;
        text-transform: uppercase;
        margin-bottom: 5px;
        letter-spacing: 1px;
    }
    
    @keyframes neonPulse {
        0% { box-shadow: 0 0 5px rgba(212, 175, 55, 0.1), inset 0 0 2px rgba(212, 175, 55, 0.05); transform: translateY(0px); }
        50% { box-shadow: 0 8px 20px rgba(212, 175, 55, 0.4), inset 0 0 10px rgba(212, 175, 55, 0.2); transform: translateY(-3px); }
        100% { box-shadow: 0 0 5px rgba(212, 175, 55, 0.1), inset 0 0 2px rgba(212, 175, 55, 0.05); transform: translateY(0px); }
    }

    .neon-float { animation: neonPulse 3s infinite ease-in-out; }
    
    .macro-container { display: grid; grid-template-columns: repeat(4, 1fr); gap: 8px; margin-bottom: 15px; }
    
    .macro-badge {
        background: rgba(20, 15, 15, 0.8);
        border: 1px solid rgba(212, 175, 55, 0.4);
        border-radius: 8px;
        padding: 8px 2px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
        transition: all 0.3s ease;
    }
    
    .directive-card {
        background: linear-gradient(145deg, #120e0f 0%, #080606 100%);
        border: 1px solid rgba(212, 175, 55, 0.5);
        border-radius: 12px;
        padding: 20px;
        margin-bottom: 5px;
    }
    
    .btn-scan > button { 
        background: linear-gradient(90deg, #d4af37 0%, #ff9900 100%) !important; 
        border: none !important; 
        color: #000000 !important; 
        border-radius: 8px !important; 
        font-weight: 800 !important;
        font-family: 'Oswald', sans-serif;
        letter-spacing: 1px;
        font-size: 1.1rem !important;
        padding: 10px 0 !important;
        width: 100% !important;
    }
    .btn-logout > button {
        background: transparent !important;
        border: 1px solid rgba(255, 51, 102, 0.4) !important;
        color: #ff3366 !important;
        border-radius: 8px !important;
        width: 100% !important;
        margin-top: 10px !important;
    }
</style>
""", unsafe_allow_html=True)

if st.session_state.get('logged_out', False):
    st.markdown("<div style='text-align: center; margin-top: 15vh;'><h1 style='color: #d4af37; font-family: Oswald;'>SYSTEM DISCONNECTED</h1></div>", unsafe_allow_html=True)
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
# 3. DATA MACRO & TECH SCANNER ENGINE
# ==========================================
DB_MACRO_BASE = {
    "USD": {"Skor_Base": 35}, "EUR": {"Skor_Base": 10}, "GBP": {"Skor_Base": 20},
    "JPY": {"Skor_Base": -30}, "AUD": {"Skor_Base": 15}, "CAD": {"Skor_Base": 5},
    "CHF": {"Skor_Base": -15}, "NZD": {"Skor_Base": 0}
}

def parse_number(val):
    if not val or str(val).strip() == "": return None
    # Bersihkan semua jenis karakter koma dan aneka unicode minus
    s = str(val).upper().replace(",", ".").replace("−", "-").replace("–", "-").strip()
    
    mult = 1
    if 'K' in s: mult = 1e3
    elif 'M' in s: mult = 1e6
    elif 'B' in s: mult = 1e9
    elif 'T' in s: mult = 1e12
    
    # Ekstraksi hanya angka, titik, dan minus
    s_clean = ''.join(c for c in s if c.isdigit() or c in ['.', '-'])
    try:
        if s_clean in ["", "-", "."]: return None
        return float(s_clean) * mult
    except: 
        return None

def fetch_live_calendar():
    impact = {k: 0 for k in DB_MACRO_BASE.keys()}
    api_status = "OK"
    
    # CACHE BUSTING: Menyuntikkan timestamp untuk menembus cache Cloudflare API
    timestamp_now = int(datetime.now().timestamp())
    url_primary = f"https://nfs.faireconomy.media/ff_calendar_thisweek.json?_={timestamp_now}"
    url_backup = f"https://nfs.gweb.io/analytics/calendar/this-week?_={timestamp_now}"
    
    data = None
    try:
        resp = requests.get(url_primary, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=10)
        if resp.status_code == 200: data = resp.json()
    except: pass
        
    if not data:
        try:
            resp = requests.get(url_backup, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
            if resp.status_code == 200: data = resp.json()
        except Exception as e:
            api_status = "API TIMEOUT/OFFLINE"
            return impact, api_status

    if data:
        for raw_ev in data:
            # NORMALISASI: Mengubah semua key API menjadi lowercase agar kebal dari perubahan format
            ev = {str(k).lower(): v for k, v in raw_ev.items()}
            
            curr = str(ev.get("country", ev.get("currency", ""))).upper()
            imp = str(ev.get("impact", ev.get("importance", ""))).upper()
            title = str(ev.get("title", "")).lower()
            
            if curr in impact and ("HIGH" in imp or "3" in imp):
                act_raw = ev.get("actual", "")
                fore_raw = ev.get("forecast", "")
                prev_raw = ev.get("previous", "")
                
                a = parse_number(act_raw)
                f = parse_number(fore_raw)
                
                # Jaring Pengaman: Jika tidak ada forecast, gunakan Previous sebagai pembanding
                if f is None: 
                    f = parse_number(prev_raw)
                
                # Mesin HANYA akan menghitung jika data Aktual benar-benar sudah ditarik (Bukan None)
                if a is not None and f is not None:
                    # Cek logika terbalik (semakin tinggi semakin buruk)
                    is_inverse = any(kw in title for kw in ["unemployment", "jobless", "claims", "trade balance", "deficit", "inventory"])
                    
                    if not is_inverse:
                        if a > f: impact[curr] += 20
                        elif a < f: impact[curr] -= 20
                    else:
                        if a < f: impact[curr] += 20
                        elif a > f: impact[curr] -= 20
    else:
        api_status = "NO DATA FETCHED"
        
    return impact, api_status

roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "XAUUSD=X": "GOLD (XAU/USD)"}

def fetch_op_forex(ticker):
    try:
        tk = yf.Ticker(ticker)
        df_h1 = tk.history(period="1mo", interval="1h").ffill()
        if df_h1.empty: return None
        
        df_h4 = df_h1.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
        df_d1 = df_h1.resample('1d').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()

        support, resistance = float(df_d1['Low'].iloc[-5:].min()), float(df_d1['High'].iloc[-5:].max())

        df_h1['EMA20'] = df_h1['Close'].ewm(span=20, adjust=False).mean()
        df_h1['EMA50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
        
        delta = df_h1['Close'].diff()
        gain, loss = (delta.where(delta > 0, 0)).rolling(14).mean(), (-delta.where(delta < 0, 0)).rolling(14).mean()
        df_h1['RSI'] = 100 - (100 / (1 + gain / loss))
        
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
            "TECH_SCORE": tech_score, "SUPPORT": support, "RESISTANCE": resistance
        }
    except: return None

# ==========================================
# 4. SIDEBAR & CONTROL PANEL
# ==========================================
if "op_data" not in st.session_state: st.session_state.op_data = []
if "new_scan" not in st.session_state: st.session_state.new_scan = False

with st.sidebar:
    st.markdown("<h3 style='color: #d4af37; font-family: Oswald; font-size: 1.5rem;'>☠️ OP CONTROL</h3>", unsafe_allow_html=True)
    
    saved_cap = load_capital()
    acc_balance = st.number_input("CAPITAL (USD):", min_value=10.0, value=float(saved_cap), step=100.0, key="input_modal", on_change=save_capital)
    risk_pct = st.slider("RISK PER TRADE (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    st.markdown("---")
    
    with st.expander("🚨 FF MANUAL OVERRIDE", expanded=False):
        st.markdown("<div style='font-size:0.75rem; color:#9ca3af; margin-bottom:10px;'>Centang ini jika FF sudah rilis tapi data di aplikasi belum update. Masukkan skor manual (-20, 0, atau +20) lalu klik Scan.</div>", unsafe_allow_html=True)
        use_manual_ff = st.checkbox("AKTIFKAN MANUAL", value=False)
        col_m1, col_m2 = st.columns(2)
        with col_m1:
            man_usd = st.number_input("USD Live", value=0, step=20)
            man_eur = st.number_input("EUR Live", value=0, step=20)
            man_gbp = st.number_input("GBP Live", value=0, step=20)
            man_jpy = st.number_input("JPY Live", value=0, step=20)
        with col_m2:
            man_aud = st.number_input("AUD Live", value=0, step=20)
            man_cad = st.number_input("CAD Live", value=0, step=20)
            man_chf = st.number_input("CHF Live", value=0, step=20)
            man_nzd = st.number_input("NZD Live", value=0, step=20)
            
    manual_impact_dict = {
        "USD": man_usd, "EUR": man_eur, "GBP": man_gbp, "JPY": man_jpy,
        "AUD": man_aud, "CAD": man_cad, "CHF": man_chf, "NZD": man_nzd
    }

    st.markdown('<div class="btn-scan">', unsafe_allow_html=True)
    if st.button("🔥 IGNITE SCAN"):
        with st.spinner("SCANNING THE MARKET..."):
            cal_dict, api_status = fetch_live_calendar()
            st.session_state.cal_impact_dict = cal_dict
            st.session_state.api_status = api_status
            st.session_state.op_data = [x for x in [fetch_op_forex(t) for t in roster_forex] if x is not None]
            st.session_state.last_run = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S WIB")
            st.session_state.new_scan = True 
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

    st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
    if st.button("⏻ LOG OUT"):
        st.session_state.clear()
        st.session_state['logged_out'] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 5. MAIN DASHBOARD AREA & SESSIONS
# ==========================================
st.markdown("<p class='title-op'>JIHAN-GHINA FX <span style='color: #ffffff; font-size: 1.1rem; font-weight: 300;'>v11.9 <span style='color:#d4af37; font-size:0.8rem;'>REVISION 3</span></span></p>", unsafe_allow_html=True)

now_wib = datetime.now(pytz.timezone('Asia/Jakarta'))
jam = now_wib.hour

sesi_sydney = 4 <= jam < 13
sesi_tokyo = 7 <= jam < 16
sesi_london = 14 <= jam < 23
sesi_ny = jam >= 19 or jam < 4

def render_session(name, is_open, color):
    bg_color = color if is_open else "#1a1a1a"
    txt_color = "#000000" if is_open else "#4b5563"
    border = "none" if is_open else "1px solid #4b5563"
    status = "OPEN" if is_open else "CLOSED"
    glow = f"box-shadow: 0 0 8px {color};" if is_open else ""
    return f'<div style="background:{bg_color}; border:{border}; padding:4px 8px; border-radius:4px; font-size:0.65rem; font-weight:bold; color:{txt_color}; {glow}">{name} ({status})</div>'

sesi_html = f"""
<div style="display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 15px; margin-top: 5px;">
    {render_session("🇦🇺 SYDNEY", sesi_sydney, "#00bfff")}
    {render_session("🇯🇵 TOKYO", sesi_tokyo, "#00ff88")}
    {render_session("🇬🇧 LONDON", sesi_london, "#d4af37")}
    {render_session("🇺🇸 NEW YORK", sesi_ny, "#ff3366")}
</div>
"""
st.markdown(sesi_html, unsafe_allow_html=True)

if not st.session_state.op_data:
    st.markdown("<div style='background: rgba(212, 175, 55, 0.05); border: 1px dashed rgba(212, 175, 55, 0.4); padding: 30px; text-align: center; border-radius: 12px; margin-top: 20px;'><h3 style='color: #d4af37; font-family: Oswald;'>SYSTEM STANDBY</h3></div>", unsafe_allow_html=True)
else:
    status_api = st.session_state.get('api_status', 'STANDBY')
    api_color = "#00ff88" if status_api == "OK" else "#ff3366"
    api_text = f" | API SERVER: <span style='color:{api_color};'>{status_api}</span>" if not use_manual_ff else f" | <span style='color:#00bfff; font-weight:bold;'>🛠️ OVERRIDE MANUAL AKTIF</span>"
    
    st.markdown(f"<p style='color:#9ca3af; font-size: 0.8rem; margin-top:0; margin-bottom:10px;'>⚡ Timestamp: <span style='color:#d4af37; font-weight:bold;'>{st.session_state.get('last_run', '')}</span>{api_text}</p>", unsafe_allow_html=True)
    
    cal_mod = st.session_state.get("cal_impact_dict", {})
    macro_html = '<div class="macro-container">'
    final_macro_db = {}
    
    for curr, base_data in DB_MACRO_BASE.items():
        base_score = base_data["Skor_Base"]
        
        if use_manual_ff: live_impact = manual_impact_dict.get(curr, 0)
        else: live_impact = cal_mod.get(curr, 0)
            
        total_score = base_score + live_impact
        final_macro_db[curr] = total_score
        c_color = "#00ff88" if total_score > 15 else ("#ff3366" if total_score < -15 else "#d4af37")
        imp_color = "#00ff88" if live_impact > 0 else ("#ff3366" if live_impact < 0 else "#9ca3af")
        
        macro_html += f'<div class="macro-badge neon-float"><p style="margin:0; font-size:0.75rem; color:#ffffff; font-weight:bold;">{curr}</p><div style="font-size: 0.55rem; color: #9ca3af; margin: 2px 0;">BASE: {base_score} <br/> LIVE: <span style="color:{imp_color}; font-weight:bold;">{live_impact:+d}</span></div><p style="margin:2px 0 0 0; font-size:1.1rem; font-family:Oswald; color:{c_color}; font-weight:bold;">{total_score:+d}</p></div>'
    st.markdown(macro_html + '</div>', unsafe_allow_html=True)

    matrix_rows = []
    titanium_found = [] 

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
        
        if "TITANIUM" in rek: titanium_found.append(pair)

        matrix_rows.append({
            "ASSET": pair, "PRICE": f"{raw['HARGA_SCAN']:.4f}" if "JPY" not in pair else f"{raw['HARGA_SCAN']:.2f}",
            "MTF": raw["MTF"], "RSI": f"{raw['RSI']:.1f}", "FUND": f"{f_score:+d}",
            "SCORE": f"{total_score:+d}", "SIGNAL": rek, "RAW_TOTAL": total_score
        })

    if st.session_state.new_scan:
        if titanium_found:
            st.toast(f"🚨 TITANIUM DETECTED: {', '.join(titanium_found)}", icon='🔥')
            st.success(f"🚨 **TITANIUM SIGNAL DETECTED:** Segera periksa {', '.join(titanium_found)}!", icon="🔥")
            audio_str = """<audio autoplay="true"><source src="https://assets.mixkit.co/active_storage/sfx/2869/2869-preview.mp3" type="audio/mpeg"></audio>"""
            st.markdown(audio_str, unsafe_allow_html=True)
        else:
            st.toast('Scan Selesai. Standby for opportunities.', icon='🔍')
        st.session_state.new_scan = False

    def style_matrix(val):
        if isinstance(val, str):
            if "BUY" in val: return 'color: #00ff88;'
            elif "SELL" in val: return 'color: #ff3366;'
        return 'color: #d1d5db;'

    st.dataframe(pd.DataFrame(matrix_rows).drop(columns=['RAW_TOTAL']).style.map(style_matrix), use_container_width=True, hide_index=True)

    # ==========================================
    # 6. TITANIUM EXECUTION & CHART
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='font-family: Oswald; color: #d4af37; margin-bottom:5px;'>🎯 TACTICAL EXECUTION</h3>", unsafe_allow_html=True)
    
    col_sel1, col_sel2 = st.columns(2)
    with col_sel1: pilihan = st.selectbox("SELECT ASSET:", [x["NAMA"] for x in st.session_state.op_data], key="pair_selector")
    with col_sel2: tf_pilihan = st.selectbox("TIME FRAME:", ["15m", "1h", "1d"], index=1, key="tf_selector")
    
    if st.session_state.pair_selector:
        active_data = next((item for item in st.session_state.op_data if item["NAMA"] == st.session_state.pair_selector), None)
        active_matrix = next((item for item in matrix_rows if item["ASSET"] == st.session_state.pair_selector), None)
        
        if active_data and active_matrix:
            try:
                tk_chart = yf.Ticker(active_data["TICKER"])
                if tf_pilihan == "15m": df_chart = tk_chart.history(period="5d", interval="15m")
                elif tf_pilihan == "1h": df_chart = tk_chart.history(period="1mo", interval="1h")
                else: df_chart = tk_chart.history(period="3mo", interval="1d")
                live_harga = float(df_chart['Close'].iloc[-1]) if not df_chart.empty else active_data["HARGA_SCAN"]
            except:
                df_chart, live_harga = pd.DataFrame(), active_data["HARGA_SCAN"]

            atr, sig = active_data["ATR"], active_matrix["SIGNAL"]
            sl_dist, risk_amount = 1.2 * atr, acc_balance * (risk_pct / 100)
            
            win_rate = min(98, 50 + abs(active_matrix["RAW_TOTAL"]))
            if "NEUTRAL" in sig: win_rate = np.random.randint(45, 55)
            
            if "JPY" in active_data["TICKER"]: pips, pip_val, fmt = sl_dist * 100, 7.00, ".3f"
            elif "XAU" in active_data["TICKER"]: pips, pip_val, fmt = sl_dist * 10, 10.0, ".3f"
            else: pips, pip_val, fmt = sl_dist * 10000, 10.0, ".5f"
                
            lot = max(0.01, round((risk_amount / (pips * pip_val)) if pips > 0 else 0, 2))
            menit_sisa = 60 - datetime.now(pytz.timezone('Asia/Jakarta')).minute
            
            is_buy, is_sell, is_titanium = "BUY" in sig, "SELL" in sig, "TITANIUM" in sig

            if is_buy:
                entry_area = live_harga if is_titanium else active_data['EMA20']
                sl, tp1, tp2, color = entry_area - sl_dist, entry_area + (sl_dist * 1.0), entry_area + (sl_dist * 2.5), "#00ff88"
            elif is_sell:
                entry_area = live_harga if is_titanium else active_data['EMA20']
                sl, tp1, tp2, color = entry_area + sl_dist, entry_area - (sl_dist * 1.0), entry_area - (sl_dist * 2.5), "#ff3366"
            else: sl, tp1, tp2, lot, color, entry_area = live_harga, live_harga, live_harga, 0.00, "#9ca3af", live_harga

            st.markdown(f"""
            <div class="directive-card neon-float">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 5px;">
                    <h3 style="color: {color}; font-family: Oswald; font-size: 1.8rem; margin: 0;">{sig}</h3>
                    <span style="background: rgba(212,175,55,0.15); border: 1px solid #d4af37; padding: 4px 8px; border-radius: 6px; font-size: 0.7rem; font-weight: bold; color: #d4af37;">⚡ WIN-RATE: {win_rate}%</span>
                </div>
                <p style="color: #ffffff; font-size: 1rem; margin: 0 0 5px 0;">Live Price: <span style="color: #d4af37; font-weight: bold;">{format(live_harga, fmt)}</span></p>
                <div style="display: flex; justify-content: space-between; align-items: center; margin: 0 0 15px 0;">
                    <p style="color: rgba(255,255,255,0.5); font-size: 0.75rem; margin: 0;">⏳ EXPIRED: {menit_sisa} Min</p>
                    <p style="color: #00bfff; font-size: 0.7rem; margin: 0;">🎯 S/R: {format(active_data['RESISTANCE'], fmt)} / {format(active_data['SUPPORT'], fmt)}</p>
                </div>
                <div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.5); padding: 12px 4px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);">
                    <div style="text-align: center; flex: 1;">
                        <p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">LOT</p>
                        <p style="color: #ffffff; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0;">{lot}</p>
                    </div>
                    <div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">ENTRY</p>
                        <p style="color: #d4af37; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0;">{format(entry_area, fmt)}</p>
                    </div>
                    <div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">SL</p>
                        <p style="color: #ff3366; font-size: 1.1rem; font-family: Oswald; font-weight: 700; margin: 0;">{format(sl, fmt)}</p>
                    </div>
                    <div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.1);">
                        <p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">TARGET</p>
                        <p style="color: #00ff88; font-size: 1rem; font-family: Oswald; font-weight: 700; margin: 0;">{format(tp1, fmt)}</p>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            if st.button("💾 SAVE ENTRY TO JOURNAL", use_container_width=True):
                log_to_journal(active_data["NAMA"], sig, lot, format(entry_area, fmt), format(sl, fmt), format(tp1, fmt))
                st.success(f"Setup {active_data['NAMA']} berhasil direkam ke Jurnal!")

            st.markdown("<br>", unsafe_allow_html=True)
            with st.spinner("Memuat Chart Pro..."):
                if not df_chart.empty:
                    df_chart['EMA20'] = df_chart['Close'].ewm(span=20, adjust=False).mean()
                    df_chart['SMA50'] = df_chart['Close'].rolling(window=50).mean()
                    
                    fig = go.Figure()
                    fig.add_trace(go.Candlestick(
                        x=df_chart.index, open=df_chart['Open'], high=df_chart['High'],
                        low=df_chart['Low'], close=df_chart['Close'],
                        increasing_line_color='#00ff88', decreasing_line_color='#ff3366', name='Price'
                    ))
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], line=dict(color='#ffd700', width=1.5), name='EMA 20'))
                    fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['SMA50'], line=dict(color='#00bfff', width=1.5), name='SMA 50'))

                    fig.update_layout(
                        template='plotly_dark', height=380, margin=dict(l=5, r=5, t=35, b=5),
                        xaxis_rangeslider_visible=False,
                        yaxis=dict(fixedrange=True, autorange=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                        xaxis=dict(fixedrange=True, gridcolor='rgba(255,255,255,0.05)', zeroline=False),
                        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)',
                        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1, font=dict(size=10, color="#d1d5db"))
                    )
                    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False, 'scrollZoom': False, 'showAxisDragHandles': False})

    # ==========================================
    # 7. AREA JURNAL
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='font-family: Oswald; color: #d4af37; margin-bottom:10px;'>📜 BLACK BOX JOURNAL</h3>", unsafe_allow_html=True)
    
    if os.path.exists(JOURNAL_FILE):
        df_journal = pd.read_csv(JOURNAL_FILE)
        st.markdown(f"<p style='color:#00ff88; font-size:0.9rem;'>Total Pertempuran Direkam: {len(df_journal)} Setup</p>", unsafe_allow_html=True)
        st.dataframe(df_journal.tail(10), hide_index=True, use_container_width=True)
        
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            with open(JOURNAL_FILE, "rb") as file:
                st.download_button(label="📥 DOWNLOAD CSV", data=file, file_name="jgfx_journal.csv", mime="text/csv", use_container_width=True)
        with col_btn2:
            if st.button("🗑️ CLEAR JOURNAL", use_container_width=True):
                os.remove(JOURNAL_FILE)
                st.rerun()
    else:
        st.info("Jurnal masih kosong. Silakan klik 'SAVE ENTRY TO JOURNAL' pada kartu eksekusi untuk mulai merekam data.")
