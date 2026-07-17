import streamlit as st
import pandas as pd
import yfinance as yf
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import pytz
import warnings
import requests
import json
import os

warnings.filterwarnings('ignore')

# ==========================================
# 1. KONFIGURASI UI STYLE & LUXURY CSS
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX v11.4", page_icon="💎", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% 0%, #1a1616, #050505) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 0.5rem; padding-bottom: 2rem; max-width: 100% !important; }
    
    /* LUXURY SIDEBAR */
    [data-testid="stSidebar"] {
        min-width: 260px !important;
        max-width: 260px !important;
        background: linear-gradient(180deg, rgba(15,12,12,0.95) 0%, rgba(5,5,5,0.95) 100%) !important;
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
        margin-bottom: 0;
        letter-spacing: 1px;
    }
    
    /* TABS LUXURY DESIGN */
    .stTabs [data-baseweb="tab-list"] {
        gap: 10px;
        background-color: transparent;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: rgba(255, 255, 255, 0.02) !important;
        border: 1px solid rgba(212, 175, 55, 0.1) !important;
        border-radius: 6px !important;
        padding: 6px 16px !important;
        color: #9ca3af !important;
        font-family: 'Oswald', sans-serif;
        font-size: 1rem !important;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(90deg, rgba(212,175,55,0.15) 0%, rgba(0,0,0,0) 100%) !important;
        border: 1px solid #d4af37 !important;
        color: #d4af37 !important;
    }
    
    /* BADGES MOBILE RESPONSIVE GRID */
    .macro-container {
        display: grid;
        grid-template-columns: repeat(4, 1fr); 
        gap: 6px;
        margin-bottom: 15px;
    }
    
    .macro-badge {
        background: rgba(255, 255, 255, 0.02);
        border: 1px solid rgba(212, 175, 55, 0.15);
        border-radius: 8px;
        padding: 8px 2px;
        text-align: center;
        display: flex;
        flex-direction: column;
        justify-content: center;
    }
    
    .directive-card {
        background: linear-gradient(145deg, #120e0f 0%, #080606 100%);
        border: 1px solid rgba(212, 175, 55, 0.3);
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.8);
    }
    
    .academy-card {
        background: rgba(255, 255, 255, 0.01);
        border-left: 3px solid #d4af37;
        padding: 12px;
        margin-bottom: 10px;
        border-radius: 0 8px 8px 0;
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
# 2. MEMORY SYSTEM
# ==========================================
CONFIG_FILE = "config_jgfx.json"

def load_capital():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r") as f:
                return json.load(f).get("capital", 1000.0)
        except: pass
    return 1000.0

def save_capital():
    with open(CONFIG_FILE, "w") as f:
        json.dump({"capital": st.session_state.input_modal}, f)

# ==========================================
# 3. RAW DATA MACRO & SMART CALENDAR ENGINE
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
                title = str(ev.get("title", "")).lower() 
                
                if curr in impact and ("HIGH" in imp or "3" in imp):
                    act, fore = ev.get("actual"), ev.get("forecast")
                    if act and fore:
                        try:
                            a = float(str(act).replace("%", "").replace("K", "").replace("M", "").strip())
                            f = float(str(fore).replace("%", "").replace("K", "").replace("M", "").strip())
                            
                            is_inverse = any(kw in title for kw in ["unemployment", "jobless", "claims"])
                            
                            if not is_inverse:
                                if a > f: impact[curr] += 20
                                elif a < f: impact[curr] -= 20
                            else:
                                if a < f: impact[curr] += 20
                                elif a > f: impact[curr] -= 20
                        except: pass
    except: pass
    return impact

# ==========================================
# 4. TECHNICAL SCANNER ENGINE 
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
# 5. EXECUTOR CONTROL PANEL (SIDEBAR)
# ==========================================
if "op_data" not in st.session_state: st.session_state.op_data = []

with st.sidebar:
    st.markdown("<h3 style='color: #d4af37; font-family: Oswald; font-size: 1.5rem;'>☠️ OP CONTROL</h3>", unsafe_allow_html=True)
    
    saved_cap = load_capital()
    acc_balance = st.number_input("CAPITAL (USD):", min_value=10.0, value=float(saved_cap), step=100.0, key="input_modal", on_change=save_capital)
    risk_pct = st.slider("RISK PER TRADE (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    st.markdown("---")
    
    st.markdown('<div class="btn-scan">', unsafe_allow_html=True)
    if st.button("🔥 IGNITE SCAN"):
        with st.spinner("SCANNING..."):
            st.session_state.cal_impact_dict = fetch_live_calendar()
            st.session_state.op_data = [fetch_op_forex(t) for t in roster_forex]
            st.session_state.op_data = [x for x in st.session_state.op_data if x is not None]
            st.session_state.last_run = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S WIB")
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)
    
    st.markdown('<div class="btn-logout">', unsafe_allow_html=True)
    if st.button("⏻ LOG OUT"):
        st.session_state.clear()
        st.session_state['logged_out'] = True
        st.rerun()
    st.markdown('</div>', unsafe_allow_html=True)

# HEADER UTAMA
st.markdown("<p class='title-op'>JIHAN-GHINA FX <span style='color: #ffffff; font-size: 1.1rem; font-weight: 300;'>v11.4</span></p>", unsafe_allow_html=True)

# SEPARASI MENU MENGGUNAKAN TABS LUXURY
tab_terminal, tab_academy = st.tabs(["🔥 TITANIUM TERMINAL", "📖 NOTEBOOK ACADEMY"])

# ==========================================
# TAB 1: TERMINAL TRADING (CORE UTAMA)
# ==========================================
with tab_terminal:
    if not st.session_state.op_data:
        st.markdown("<div style='background: rgba(212, 175, 55, 0.05); border: 1px dashed rgba(212, 175, 55, 0.4); padding: 30px; text-align: center; border-radius: 12px; margin-top: 20px;'><h3 style='color: #d4af37; font-family: Oswald;'>SYSTEM STANDBY</h3><p style='color: #9ca3af; font-size:0.9rem;'>Klik <b>IGNITE SCAN</b> di sidebar untuk memuat data.</p></div>", unsafe_allow_html=True)
    else:
        st.markdown(f"<p style='color:#9ca3af; font-size: 0.8rem; margin-top:0; margin-bottom:10px;'>⚡ Timestamp: <span style='color:#d4af37; font-weight:bold;'>{st.session_state.get('last_run', '')}</span></p>", unsafe_allow_html=True)
        
        cal_mod = st.session_state.get("cal_impact_dict", {})
        
        # UI MACRO BADGES (1 BARIS HTML)
        macro_html = '<div class="macro-container">'
        final_macro_db = {}
        for curr, base_data in DB_MACRO_BASE.items():
            base_score = base_data["Skor_Base"]
            live_impact = cal_mod.get(curr, 0)
            total_score = base_score + live_impact
            final_macro_db[curr] = total_score
            
            c_color = "#00ff88" if total_score > 15 else ("#ff3366" if total_score < -15 else "#d4af37")
            impact_str = f"+{live_impact}" if live_impact > 0 else (f"{live_impact}" if live_impact < 0 else "0")
            impact_color = "#00ff88" if live_impact > 0 else ("#ff3366" if live_impact < 0 else "#9ca3af")
            
            macro_html += f'<div class="macro-badge"><p style="margin:0; font-size:0.75rem; color:#ffffff; font-weight:bold;">{curr}</p><div style="font-size: 0.55rem; color: #9ca3af; margin: 2px 0;">BASE: {base_score} <br/> LIVE: <span style="color:{impact_color}; font-weight:bold;">{impact_str}</span></div><p style="margin:2px 0 0 0; font-size:1.1rem; font-family:Oswald; color:{c_color}; font-weight:bold;">{total_score:+d}</p></div>'
            
        macro_html += '</div>'
        st.markdown(macro_html, unsafe_allow_html=True)

        # MATRIX DATA GENERATOR
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
                "RSI": f"{raw['RSI']:.1f}",
                "FUND": f"{f_score:+d}",
                "SCORE": f"{total_score:+d}",
                "SIGNAL": rek
            })

        def style_matrix(val):
            if isinstance(val, str):
                if "BUY" in val: return 'color: #00ff88;'
                elif "SELL" in val: return 'color: #ff3366;'
            return 'color: #d1d5db;'

        st.dataframe(pd.DataFrame(matrix_rows).style.map(style_matrix), use_container_width=True, hide_index=True)

        # ==========================================
        # 6. TITANIUM EXECUTION MANAGER & LIVE CHART
        # ==========================================
        st.markdown("---")
        st.markdown("<h3 style='font-family: Oswald; color: #d4af37; margin-bottom:5px;'>🎯 TACTICAL EXECUTION</h3>", unsafe_allow_html=True)
        
        pilihan = st.selectbox("SELECT ASSET:", [x["NAMA"] for x in st.session_state.op_data], key="pair_selector")
        
        if st.session_state.pair_selector:
            active_data = next((item for item in st.session_state.op_data if item["NAMA"] == st.session_state.pair_selector), None)
            active_matrix = next((item for item in matrix_rows if item["ASSET"] == st.session_state.pair_selector), None)
            
            if active_data and active_matrix:
                sig = active_matrix["SIGNAL"]
                is_buy, is_sell, is_titanium = "BUY" in sig, "SELL" in sig, "TITANIUM" in sig
                color_chart = "#00ff88" if is_buy else ("#ff3366" if is_sell else "#d4af37")
                
                # SELEKSI TIMEFRAME UNTUK LIVE CHART RAMPING
                tf_pilih = st.radio("TIMEFRAME CHART:", ["1 Hour", "4 Hours", "1 Day"], index=0, horizontal=True)
                tf_map = {"1 Hour": {"p": "5d", "i": "1h"}, "4 Hours": {"p": "20d", "i": "4h"}, "1 Day": {"p": "60d", "i": "1d"}}
                
                # ENGINE FETCH LIVE CHART & AUTO-LOCK AXIS
                try:
                    chart_tk = yf.Ticker(active_data["TICKER"])
                    df_chart = chart_tk.history(period=tf_map[tf_pilih]["p"], interval=tf_map[tf_pilih]["i"]).ffill()
                    
                    if not df_chart.empty:
                        # Auto lock logic: Hitung batas ketat min & max harga saat ini
                        price_min = float(df_chart['Close'].min())
                        price_max = float(df_chart['Close'].max())
                        padding_axis = (price_max - price_min) * 0.05 if price_max != price_min else price_min * 0.005
                        
                        # Bangun Plotly Ramping khusus layar HP
                        fig = go.Figure()
                        fig.add_trace(go.Scatter(
                            x=df_chart.index, y=df_chart['Close'],
                            mode='lines', line=dict(color=color_chart, width=2),
                            hovertemplate='%{y:.5f}<extra></extra>'
                        ))
                        fig.update_layout(
                            height=240, # Tinggi diperpendek biar ramping vertikal
                            margin=dict(l=8, r=8, t=5, b=5),
                            paper_bgcolor='rgba(0,0,0,0)',
                            plot_bgcolor='rgba(0,0,0,0)',
                            xaxis=dict(showgrid=False, color='#6b7280', tickfont=dict(size=8), showticklabels=True),
                            yaxis=dict(
                                showgrid=True, gridcolor='rgba(255,255,255,0.03)', 
                                color='#6b7280', tickfont=dict(size=8), side='right',
                                range=[price_min - padding_axis, price_max + padding_axis] # AUTO LOCK AXIS
                            ),
                            hovermode='x unified'
                        )
                        st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
                except:
                    st.caption("⚠️ Grafik gagal dimuat otomatis, periksa jaringan.")

                # FETCH LIVE TICK PRICE & CALCULATION RESULT
                try:
                    live_tk = yf.Ticker(active_data["TICKER"])
                    live_price_df = live_tk.history(period="1d", interval="1m")
                    live_harga = float(live_price_df['Close'].iloc[-1]) if not live_price_df.empty else active_data["HARGA_SCAN"]
                except: live_harga = active_data["HARGA_SCAN"]

                atr = active_data["ATR"]
                sl_dist, risk_amount = 1.2 * atr, acc_balance * (risk_pct / 100)
                
                if "JPY" in active_data["TICKER"]: pips, pip_val, fmt = sl_dist * 100, 7.00, ".3f"
                elif "XAU" in active_data["TICKER"]: pips, pip_val, fmt = sl_dist * 10, 10.0, ".3f"
                else: pips, pip_val, fmt = sl_dist * 10000, 10.0, ".5f"
                    
                lot = max(0.01, round((risk_amount / (pips * pip_val)) if pips > 0 else 0, 2))
                menit_sisa = 60 - datetime.now(pytz.timezone('Asia/Jakarta')).minute

                if is_buy:
                    entry_area = live_harga if is_titanium else active_data['EMA20']
                    sl, tp1, tp2, color = entry_area - sl_dist, entry_area + (sl_dist * 1.0), entry_area + (sl_dist * 2.5), "#00ff88"
                elif is_sell:
                    entry_area = live_harga if is_titanium else active_data['EMA20']
                    sl, tp1, tp2, color = entry_area + sl_dist, entry_area - (sl_dist * 1.0), entry_area - (sl_dist * 2.5), "#ff3366"
                else: sl, tp1, tp2, lot, color, entry_area = live_harga, live_harga, live_harga, 0.00, "#9ca3af", live_harga

                # CARD DIRECTIVE UTAMA (1 BARIS HTML)
                html_content = f'<div class="directive-card"><h3 style="color: {color}; font-family: Oswald; font-size: 1.8rem; margin: 0 0 5px 0;">{sig}</h3><p style="color: #ffffff; font-size: 1rem; margin: 0 0 5px 0;">Live Price: <span style="color: #d4af37; font-weight: bold;">{format(live_harga, fmt)}</span></p><p style="color: rgba(255,255,255,0.5); font-size: 0.75rem; margin: 0 0 15px 0;">⏳ EXPIRED IN: {menit_sisa} Min</p><div style="display: flex; justify-content: space-between; align-items: center; background: rgba(0,0,0,0.5); padding: 12px 4px; border-radius: 8px; border: 1px solid rgba(255,255,255,0.05);"><div style="text-align: center; flex: 1;"><p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">LOT</p><p style="color: #ffffff; font-size: 1rem; font-family: Oswald; font-weight: 700; margin: 0;">{lot}</p></div><div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.1);"><p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">ENTRY</p><p style="color: #d4af37; font-size: 1rem; font-family: Oswald; font-weight: 700; margin: 0;">{format(entry_area, fmt)}</p></div><div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.1);"><p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">SL</p><p style="color: #ff3366; font-size: 1rem; font-family: Oswald; font-weight: 700; margin: 0;">{format(sl, fmt)}</p></div><div style="text-align: center; flex: 1; border-left: 1px solid rgba(255,255,255,0.1);"><p style="color: #9ca3af; font-size: 0.6rem; margin: 0; font-weight: bold;">TARGET</p><p style="color: #00ff88; font-size: 1rem; font-family: Oswald; font-weight: 700; margin: 0;">{format(tp1, fmt)}</p><p style="color: #00ff88; font-size: 0.7rem; font-family: Oswald; opacity: 0.6; margin: 0;">{format(tp2, fmt)}</p></div></div></div>'
                st.markdown(html_content, unsafe_allow_html=True)

# ==========================================
# TAB 2: NOTEBOOK ACADEMY (PANDUAN APLIKASI)
# ==========================================
with tab_academy:
    st.markdown("<h3 style='font-family: Oswald; color: #d4af37; margin-bottom:15px;'>📖 JFX TRADING ACADEMY BOOK</h3>", unsafe_allow_html=True)
    
    with st.expander("📊 1. STRUKTUR PEMBOBOTAN SKOR (TOTAL SCORE)"):
        st.markdown("""
        Total nilai indikator dihitung berdasarkan kombinasi rumus matematika:
        **[ Total Score = Technical Score + Fundamental Impact Score ]**
        
        *   **Technical Score (Max ±70 Point):** Diambil dari deteksi keselarasan tren *Multi-Timeframe* (D1, H4, H1), persilangan EMA 20/50, kondisi kekuatan RSI, dan momentum tren MACD.
        *   **Fundamental Score (Base + Live):** Berasal dari kekuatan suku bunga dasar (*Base Score*) digabungkan dengan kejutan kalender ekonomi mingguan berimpact tinggi (*Live Impact*).
        """)
        
    with st.expander("⚠️ 2. ATURAN HUKUM LOGIKA BERBALIK (INVERSE ECONOMY DATA)"):
        st.markdown("""
        Aplikasi ini telah ditanamkan kecerdasan buatan untuk mendeteksi berita yang bersifat **negatif berbalik untuk mata uang** (seperti tingkat pengangguran).
        
        *   **Berita Normal (GDP, NFP, Retail Sales):**
            *   *Actual > Forecast* = Ekonomi Bagus = Skor Mata Uang **Naik (+20)**
            *   *Actual < Forecast* = Ekonomi Buruk = Skor Mata Uang **Turun (-20)**
        *   **Berita Berbalik/Inverse (Unemployment Rate, Jobless Claims):**
            *   *Actual < Forecast* = Jumlah Orang Menganggur Sedikit = Ekonomi Menguat = Skor Mata Uang **Naik (+20)**
            *   *Actual > Forecast* = Jumlah Orang Menganggur Banyak = Ekonomi Melemah = Skor Mata Uang **Turun (-20)**
        """)
        
    with st.expander("🔥 3. RULE MATRIKS KEPUTUSAN SIGNAL SAKTI"):
        st.markdown('<div class="academy-card"><b>🔥 TITANIUM BUY / SELL (Score ≥ +60 atau ≤ -60)</b><br/>Kondisi Super-Trending. Kekuatan fundamental dan teknikal searah secara ekstrem. Eksekusi instan langsung menggunakan harga running saat ini (Live Price).</div>', unsafe_allow_html=True)
        st.markdown('<div class="academy-card"><b>🟢 / 🔴 STRONG BUY / SELL (Score +30 s/d +55 atau -30 s/d -55)</b><br/>Kondisi market sehat untuk entry. Disarankan melakukan pemesanan tertib antri memanfaatkan area dinamis EMA20 sebagai titik pijakan harga terbaik.</div>', unsafe_allow_html=True)
        st.markdown('<div class="academy-card"><b>⚪ NEUTRAL (Score di antara -25 s/d +25)</b><br/>Market tidak memiliki arah yang jelas atau sedang terjadi benturan keras antara fundamental dan teknikal. <b>Dilarang masuk posisi (Wait & See).</b></div>', unsafe_allow_html=True)

    with st.expander("🛡️ 4. MANAJEMEN RISIKO TITANIUM EXECUTION"):
        st.markdown("""
        *   **Pengamanan Modal:** Jarak Stop Loss (SL) dikunci mutlak menggunakan formula **1.2 × ATR (Average True Range)** jam terakhir untuk menghindari kegetiran *false breakout*.
        *   **Money Management Otomatis:** Perhitungan lot disesuaikan secara presisi hingga digit terkecil sesuai persentase batas toleransi resiko modal (*Risk per Trade %*) yang Anda geser pada bilah kontrol sidebar.
        """)
