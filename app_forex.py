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
st.set_page_config(page_title="JIHAN-GHINA FX v12.0", page_icon="💎", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #151111, #020202) !important; 
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
</style>
""", unsafe_allow_html=True)

# ==========================================
# 2. MEMORY & VISUAL JOURNALING SYSTEM
# ==========================================
CONFIG_FILE = "config_jgfx.json"
JOURNAL_FILE = "jgfx_journal.csv"
JOURNAL_DIR = "Visual_Journals"

if not os.path.exists(JOURNAL_DIR):
    os.makedirs(JOURNAL_DIR)

def load_capital():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f: return json.load(f).get("capital", 1000.0)
        except: pass
    return 1000.0

def save_capital():
    with open(CONFIG_FILE, "w") as f: json.dump({"capital": st.session_state.input_modal}, f)

def log_to_journal(asset, signal, lot, entry, sl, tp, fig=None):
    file_exists = os.path.isfile(JOURNAL_FILE)
    timestamp_obj = datetime.now(pytz.timezone('Asia/Jakarta'))
    timestamp = timestamp_obj.strftime("%Y-%m-%d %H:%M:%S")
    file_time = timestamp_obj.strftime("%Y%m%d_%H%M%S")
    
    # Text Log
    with open(JOURNAL_FILE, mode='a', newline='') as file:
        writer = csv.writer(file)
        if not file_exists:
            writer.writerow(["TIMESTAMP", "ASSET", "SIGNAL", "LOT", "ENTRY", "SL", "TARGET", "VISUAL_LOG"])
        visual_name = f"Log_{asset.replace('/','')}_{file_time}.html" if fig else "N/A"
        writer.writerow([timestamp, asset, signal, lot, entry, sl, tp, visual_name])
    
    # Auto-Capture Chart HTML (Pilar 3)
    if fig:
        file_path = os.path.join(JOURNAL_DIR, f"Log_{asset.replace('/','')}_{file_time}.html")
        fig.write_html(file_path)

# ==========================================
# 3. DYNAMIC MACRO & TECH SCANNER ENGINE
# ==========================================
DB_MACRO_BASE = {
    "USD": {"Skor_Base": 35}, "EUR": {"Skor_Base": 10}, "GBP": {"Skor_Base": 20},
    "JPY": {"Skor_Base": -30}, "AUD": {"Skor_Base": 15}, "CAD": {"Skor_Base": 5},
    "CHF": {"Skor_Base": -15}, "NZD": {"Skor_Base": 0}
}

# Pilar 1: Auto-Tuning Base Score USD menggunakan US 10Y Treasury
def get_dynamic_base_score():
    base = DB_MACRO_BASE.copy()
    try:
        tnx = yf.Ticker("^TNX").history(period="1d")['Close'].iloc[-1]
        if tnx >= 4.3: base["USD"]["Skor_Base"] += 15
        elif tnx >= 4.0: base["USD"]["Skor_Base"] += 5
        elif tnx <= 3.6: base["USD"]["Skor_Base"] -= 10
    except: pass
    return base

def parse_number(val):
    if not val or str(val).strip() == "": return None
    s = str(val).upper().replace(",", ".").replace("−", "-").replace("–", "-").strip()
    mult = 1
    if 'K' in s: mult = 1e3
    elif 'M' in s: mult = 1e6
    elif 'B' in s: mult = 1e9
    elif 'T' in s: mult = 1e12
    s_clean = ''.join(c for c in s if c.isdigit() or c in ['.', '-'])
    try:
        if s_clean in ["", "-", "."]: return None
        return float(s_clean) * mult
    except: return None

def fetch_live_calendar(dynamic_bases):
    impact = {k: 0 for k in dynamic_bases.keys()}
    api_status = "OK"
    timestamp_now = int(datetime.now().timestamp())
    url_primary = f"https://nfs.faireconomy.media/ff_calendar_thisweek.json?_={timestamp_now}"
    
    data = None
    try:
        resp = requests.get(url_primary, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        if resp.status_code == 200: data = resp.json()
    except: api_status = "API TIMEOUT/OFFLINE"

    if data:
        for raw_ev in data:
            ev = {str(k).lower(): v for k, v in raw_ev.items()}
            curr = str(ev.get("country", ev.get("currency", ""))).upper()
            imp = str(ev.get("impact", ev.get("importance", ""))).upper()
            title = str(ev.get("title", "")).lower()
            
            if curr in impact and ("HIGH" in imp or "3" in imp):
                a, f = parse_number(ev.get("actual", "")), parse_number(ev.get("forecast", ""))
                if f is None: f = parse_number(ev.get("previous", ""))
                
                if a is not None and f is not None:
                    is_inverse = any(kw in title for kw in ["unemployment", "jobless", "claims", "trade balance", "deficit", "inventory"])
                    if not is_inverse:
                        impact[curr] += 20 if a > f else (-20 if a < f else 0)
                    else:
                        impact[curr] += 20 if a < f else (-20 if a > f else 0)
    else: api_status = "NO DATA FETCHED"
        
    return impact, api_status

roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "XAUUSD=X": "GOLD (XAU/USD)"}

def fetch_op_forex(ticker):
    try:
        tk = yf.Ticker(ticker)
        df_h1 = tk.history(period="1mo", interval="1h").ffill()
        df_m5 = tk.history(period="1d", interval="5m").ffill() # Data M5 untuk Anti-Whiplash
        if df_h1.empty or df_m5.empty: return None
        
        df_h4 = df_h1.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
        df_d1 = df_h1.resample('1d').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()

        # Pilar 4: 3D Pivot & Support Resistance Mapping
        prev_h, prev_l, prev_c = float(df_d1['High'].iloc[-2]), float(df_d1['Low'].iloc[-2]), float(df_d1['Close'].iloc[-2])
        pivot = (prev_h + prev_l + prev_c) / 3
        r1, s1 = (2 * pivot) - prev_l, (2 * pivot) - prev_h
        r2, s2 = pivot + (prev_h - prev_l), pivot - (prev_h - prev_l)

        df_h1['EMA20'] = df_h1['Close'].ewm(span=20, adjust=False).mean()
        df_h1['EMA50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
        
        delta = df_h1['Close'].diff()
        gain, loss = (delta.where(delta > 0, 0)).rolling(14).mean(), (-delta.where(delta < 0, 0)).rolling(14).mean()
        df_h1['RSI'] = 100 - (100 / (1 + gain / loss))
        
        df_h1['MACD'] = df_h1['Close'].ewm(span=12, adjust=False).mean() - df_h1['Close'].ewm(span=26, adjust=False).mean()
        df_h1['Signal'] = df_h1['MACD'].ewm(span=9, adjust=False).mean()
        
        tr = np.max([df_h1['High']-df_h1['Low'], np.abs(df_h1['High']-df_h1['Close'].shift()), np.abs(df_h1['Low']-df_h1['Close'].shift())], axis=0)
        df_h1['ATR'] = pd.Series(tr, index=df_h1.index).rolling(14).mean()
        
        # Pilar 2: Anti-Whiplash M5 Checker
        m5_spread = float(df_m5['High'].iloc[-1] - df_m5['Low'].iloc[-1])
        current_atr = float(df_h1['ATR'].iloc[-1])
        whiplash_safe = True if m5_spread < (1.5 * current_atr) else False

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
            "EMA20": float(last['EMA20']), "ATR": float(last['ATR']), "RSI": float(last['RSI']),
            "MTF": f"{d1_trend} | {h4_trend} | {h1_trend}", "TECH_SCORE": tech_score,
            "PIVOT": pivot, "R1": r1, "R2": r2, "S1": s1, "S2": s2, "WHIPLASH_SAFE": whiplash_safe
        }
    except: return None

# ==========================================
# 4. SIDEBAR & CONTROL PANEL
# ==========================================
if "op_data" not in st.session_state: st.session_state.op_data = []
if "new_scan" not in st.session_state: st.session_state.new_scan = False

with st.sidebar:
    st.markdown("<h3 style='color: #d4af37; font-family: Oswald;'>☠️ COMMAND CENTER</h3>", unsafe_allow_html=True)
    saved_cap = load_capital()
    acc_balance = st.number_input("CAPITAL (USD):", min_value=10.0, value=float(saved_cap), step=100.0, key="input_modal", on_change=save_capital)
    risk_pct = st.slider("RISK PER TRADE (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    st.markdown("---")
    
    with st.expander("🚨 FF LIVE OVERRIDE", expanded=False):
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
            
    manual_impact_dict = {"USD": man_usd, "EUR": man_eur, "GBP": man_gbp, "JPY": man_jpy, "AUD": man_aud, "CAD": man_cad, "CHF": man_chf, "NZD": man_nzd}

    if st.button("🔥 EXECUTE SCAN", use_container_width=True):
        with st.spinner("QUANTUM SCANNING..."):
            dynamic_bases = get_dynamic_base_score()
            st.session_state.dynamic_bases = dynamic_bases
            cal_dict, api_status = fetch_live_calendar(dynamic_bases)
            st.session_state.cal_impact_dict = cal_dict
            st.session_state.api_status = api_status
            st.session_state.op_data = [x for x in [fetch_op_forex(t) for t in roster_forex] if x is not None]
            st.session_state.last_run = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S WIB")
            st.session_state.new_scan = True 
        st.rerun()

# ==========================================
# 5. MAIN DASHBOARD AREA
# ==========================================
st.markdown("<p class='title-op'>JIHAN-GHINA FX <span style='color: #ffffff; font-size: 1.1rem; font-weight: 300;'>v12.0 <span style='color:#00bfff; font-size:0.8rem;'>TITANIUM PROTOCOL</span></span></p>", unsafe_allow_html=True)

if not st.session_state.op_data:
    st.info("System Standby. Initiate Scan to extract market intelligence.")
else:
    api_status = st.session_state.get('api_status', 'STANDBY')
    st.markdown(f"<p style='color:#9ca3af; font-size: 0.8rem;'>⚡ Timestamp: <span style='color:#d4af37;'>{st.session_state.get('last_run', '')}</span> | API: <span style='color:#00ff88;'>{api_status}</span></p>", unsafe_allow_html=True)
    
    cal_mod = st.session_state.get("cal_impact_dict", {})
    bases = st.session_state.get("dynamic_bases", DB_MACRO_BASE)
    
    macro_html = '<div class="macro-container">'
    final_macro_db = {}
    
    for curr, base_data in bases.items():
        base_score = base_data["Skor_Base"]
        live_impact = manual_impact_dict.get(curr, 0) if use_manual_ff else cal_mod.get(curr, 0)
        total_score = base_score + live_impact
        final_macro_db[curr] = total_score
        
        c_color = "#00ff88" if total_score > 15 else ("#ff3366" if total_score < -15 else "#d4af37")
        macro_html += f'<div class="macro-badge"><p style="margin:0; font-size:0.75rem; color:#fff;">{curr}</p><p style="margin:2px 0 0 0; font-size:1.1rem; font-family:Oswald; color:{c_color};">{total_score:+d}</p></div>'
    st.markdown(macro_html + '</div>', unsafe_allow_html=True)

    matrix_rows = []
    for raw in st.session_state.op_data:
        pair = raw["NAMA"]
        if "GOLD" in pair: f_score = 30 if final_macro_db["USD"] < 0 else -30
        else:
            try: b, q = pair.split("/"); f_score = final_macro_db[b] - final_macro_db[q]
            except: f_score = 0
            
        total_score = raw["TECH_SCORE"] + f_score
        
        if total_score >= 60: rek = "🔥 TITANIUM BUY"
        elif total_score >= 30: rek = "🟢 STRONG BUY"
        elif total_score <= -60: rek = "🩸 TITANIUM SELL"
        elif total_score <= -30: rek = "🔴 STRONG SELL"
        else: rek = "⚪ NEUTRAL"
        
        warn = "⚠️" if not raw["WHIPLASH_SAFE"] else ""

        matrix_rows.append({
            "ASSET": pair + f" {warn}", "PRICE": f"{raw['HARGA_SCAN']:.4f}" if "JPY" not in pair else f"{raw['HARGA_SCAN']:.2f}",
            "SCORE": f"{total_score:+d}", "SIGNAL": rek, "RAW_TOTAL": total_score
        })

    def style_matrix(val):
        if isinstance(val, str):
            if "BUY" in val: return 'color: #00ff88;'
            elif "SELL" in val: return 'color: #ff3366;'
            elif "⚠️" in val: return 'color: #ff9900; font-weight:bold;'
        return 'color: #d1d5db;'
    st.dataframe(pd.DataFrame(matrix_rows).drop(columns=['RAW_TOTAL']).style.map(style_matrix), use_container_width=True, hide_index=True)

    # ==========================================
    # 6. TACTICAL EXECUTION
    # ==========================================
    st.markdown("---")
    pilihan = st.selectbox("SELECT ASSET FOR EXECUTION:", [x["NAMA"] for x in st.session_state.op_data])
    
    if pilihan:
        active_data = next((item for item in st.session_state.op_data if item["NAMA"] == pilihan), None)
        active_matrix = next((item for item in matrix_rows if pilihan in item["ASSET"]), None)
        
        if active_data and active_matrix:
            tk_chart = yf.Ticker(active_data["TICKER"])
            df_chart = tk_chart.history(period="5d", interval="15m")
            live_harga = active_data["HARGA_SCAN"]
            
            sig = active_matrix["SIGNAL"]
            is_buy, is_sell = "BUY" in sig, "SELL" in sig
            
            sl_dist = 1.2 * active_data["ATR"]
            risk_amount = acc_balance * (risk_pct / 100)
            pips = sl_dist * (100 if "JPY" in active_data["TICKER"] else (10 if "XAU" in active_data["TICKER"] else 10000))
            lot = max(0.01, round((risk_amount / (pips * 10.0)) if pips > 0 else 0, 2))
            fmt = ".3f" if "JPY" in active_data["TICKER"] or "XAU" in active_data["TICKER"] else ".5f"

            # 3D Profit Scaling Logic
            if is_buy:
                entry = live_harga
                sl = entry - sl_dist
                tp1 = active_data["R1"] if active_data["R1"] > entry else entry + (sl_dist * 1.5)
                color = "#00ff88"
            elif is_sell:
                entry = live_harga
                sl = entry + sl_dist
                tp1 = active_data["S1"] if active_data["S1"] < entry else entry - (sl_dist * 1.5)
                color = "#ff3366"
            else: entry, sl, tp1, lot, color = live_harga, live_harga, live_harga, 0.00, "#9ca3af"

            whiplash_alert = "<p style='color:#ff9900; font-weight:bold;'>⚠️ WHIPLASH DETECTED! Pasar fluktuatif ekstrem di M5. Tunggu Pullback!</p>" if not active_data["WHIPLASH_SAFE"] else ""

            st.markdown(f"""
            <div class="directive-card neon-float">
                <h3 style="color: {color}; font-family: Oswald; margin: 0;">{sig}</h3>
                {whiplash_alert}
                <div style="display: flex; justify-content: space-between; background: rgba(0,0,0,0.5); padding: 12px; border-radius: 8px; margin-top: 10px;">
                    <div style="text-align: center;"><p style="color:#9ca3af; font-size:0.7rem; margin:0;">LOT</p><p style="color:#fff; font-size:1.2rem; font-family:Oswald; margin:0;">{lot}</p></div>
                    <div style="text-align: center;"><p style="color:#9ca3af; font-size:0.7rem; margin:0;">ENTRY</p><p style="color:#d4af37; font-size:1.2rem; font-family:Oswald; margin:0;">{format(entry, fmt)}</p></div>
                    <div style="text-align: center;"><p style="color:#9ca3af; font-size:0.7rem; margin:0;">SL</p><p style="color:#ff3366; font-size:1.2rem; font-family:Oswald; margin:0;">{format(sl, fmt)}</p></div>
                    <div style="text-align: center;"><p style="color:#9ca3af; font-size:0.7rem; margin:0;">TARGET (3D)</p><p style="color:#00ff88; font-size:1.2rem; font-family:Oswald; margin:0;">{format(tp1, fmt)}</p></div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            fig = go.Figure(data=[go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Price')])
            fig.update_layout(template='plotly_dark', height=350, margin=dict(l=0, r=0, t=20, b=0), xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

            if st.button("💾 SAVE & CAPTURE CHART TO JOURNAL", use_container_width=True):
                # Menambahkan garis Entry/SL/TP ke chart jurnal
                fig.add_hline(y=entry, line_dash="dash", line_color="#d4af37", annotation_text="ENTRY")
                fig.add_hline(y=sl, line_dash="solid", line_color="#ff3366", annotation_text="SL")
                fig.add_hline(y=tp1, line_dash="solid", line_color="#00ff88", annotation_text="TP 1")
                log_to_journal(active_data["NAMA"], sig, lot, format(entry, fmt), format(sl, fmt), format(tp1, fmt), fig)
                st.success(f"Rekaman Taktis & Visual Chart {active_data['NAMA']} berhasil diamankan di folder 'Visual_Journals'!")

    # ==========================================
    # 7. AREA JURNAL
    # ==========================================
    st.markdown("---")
    st.markdown("<h3 style='font-family: Oswald; color: #d4af37;'>📜 BLACK BOX JOURNAL</h3>", unsafe_allow_html=True)
    if os.path.exists(JOURNAL_FILE):
        df_journal = pd.read_csv(JOURNAL_FILE)
        st.dataframe(df_journal.tail(10), hide_index=True, use_container_width=True)
        if st.button("🗑️ CLEAR JOURNAL"):
            os.remove(JOURNAL_FILE)
            st.rerun()
