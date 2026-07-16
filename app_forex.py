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
# 1. KONFIGURASI UI STYLE (V10.6 GLOW & HOVER)
# ==========================================
st.set_page_config(page_title="JIHAN-GHINA FX OP-v10.6", page_icon="🔥", layout="wide")

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@400;600;700&family=Plus+Jakarta+Sans:wght@300;400;600;800&display=swap');
    html, body, [class*="css"] { font-family: 'Plus Jakarta Sans', sans-serif; }
    
    [data-testid="stAppViewContainer"] { 
        background: radial-gradient(circle at 50% -20%, #1a0b0b, #000000) !important; 
        color: #f3f4f6 !important; 
    }
    
    .block-container { padding-top: 1rem; padding-bottom: 2rem; max-width: 98% !important; }
    
    .title-op {
        font-family: 'Oswald', sans-serif;
        background: linear-gradient(to right, #ff3366, #ff9933, #ff3366);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-weight: 700;
        font-size: 3.5rem;
        text-transform: uppercase;
        margin-bottom: 0;
        letter-spacing: 2px;
    }
    
    /* Efek Mengambang & Menyala untuk Badge Score */
    .macro-badge {
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 8px;
        padding: 12px;
        text-align: center;
        box-shadow: 0 0 10px rgba(0, 0, 0, 0.5);
        transition: all 0.3s ease;
        cursor: pointer;
    }
    .macro-badge:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 255, 136, 0.3);
        border: 1px solid rgba(0, 255, 136, 0.5);
    }
    
    /* Efek Mengambang & Menyala untuk Kotak Eksekusi */
    .directive-card {
        background: linear-gradient(145deg, #0d0a0b 0%, #1a1516 100%);
        border: 2px solid #ff3366;
        border-radius: 12px;
        padding: 30px;
        box-shadow: 0 0 20px rgba(255, 51, 102, 0.2);
        transition: all 0.4s ease;
    }
    .directive-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 15px 40px rgba(255, 51, 102, 0.6);
        border-color: #ff5500;
    }
    
    .metric-value { font-family: 'Oswald', sans-serif; font-size: 1.8rem; font-weight: 700; }
    
    div.stButton > button:first-child { 
        background: linear-gradient(90deg, #ff0055 0%, #ff5500 100%) !important; 
        border: none !important; 
        color: #ffffff !important; 
        border-radius: 6px !important; 
        font-weight: 800 !important;
        font-family: 'Oswald', sans-serif;
        letter-spacing: 2px;
        font-size: 1.2rem !important;
        padding: 15px 0 !important;
        box-shadow: 0 10px 20px rgba(255, 0, 85, 0.4);
        transition: all 0.3s ease;
    }
    div.stButton > button:first-child:hover {
        transform: scale(1.02);
        box-shadow: 0 15px 30px rgba(255, 0, 85, 0.7);
    }
</style>
""", unsafe_allow_html=True)

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
        resp = requests.get("https://nfs.gweb.io/analytics/calendar/this-week", headers={"User-Agent": "Mozilla/5.0"}, timeout=5)
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
# 3. TECHNICAL SCANNER ENGINE
# ==========================================
roster_forex = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "AUDUSD=X", "USDCAD=X", "USDCHF=X", "XAUUSD=X"]
nama_pairs = {"EURUSD=X": "EUR/USD", "GBPUSD=X": "GBP/USD", "USDJPY=X": "USD/JPY", "AUDUSD=X": "AUD/USD", "USDCAD=X": "USD/CAD", "USDCHF=X": "USD/CHF", "XAUUSD=X": "GOLD (XAU/USD)"}

def calculate_rsi(data, window=14):
    delta = data.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def fetch_op_forex(ticker):
    try:
        tk = yf.Ticker(ticker)
        df_h1 = tk.history(period="1mo", interval="1h").ffill()
        if df_h1.empty: return None
        
        df_h4 = df_h1.resample('4h').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()
        df_d1 = df_h1.resample('1d').agg({'Open':'first', 'High':'max', 'Low':'min', 'Close':'last'}).dropna()

        df_h1['EMA20'] = df_h1['Close'].ewm(span=20, adjust=False).mean()
        df_h1['EMA50'] = df_h1['Close'].ewm(span=50, adjust=False).mean()
        df_h1['RSI'] = calculate_rsi(df_h1['Close'], 14)
        
        df_h1['EMA12'] = df_h1['Close'].ewm(span=12, adjust=False).mean()
        df_h1['EMA26'] = df_h1['Close'].ewm(span=26, adjust=False).mean()
        df_h1['MACD'] = df_h1['EMA12'] - df_h1['EMA26']
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
        elif last['RSI'] > 75: tech_score -= 20 
        elif last['RSI'] < 25: tech_score += 20 

        return {
            "TICKER": ticker, "NAMA": nama_pairs[ticker], "HARGA": float(last['Close']),
            "EMA20": float(last['EMA20']), "EMA50": float(last['EMA50']),
            "RSI": float(last['RSI']), "MACD_SIGNAL": "BULL" if last['MACD'] > last['Signal'] else "BEAR",
            "ATR": float(last['ATR']), "MTF": f"{d1_trend} | {h4_trend} | {h1_trend}",
            "TECH_SCORE": tech_score
        }
    except: return None

# ==========================================
# 4. EXECUTOR CONTROL PANEL
# ==========================================
if "op_data" not in st.session_state: st.session_state.op_data = []
if "play_alarm" not in st.session_state: st.session_state.play_alarm = False

with st.sidebar:
    st.markdown("<h2 style='color: #ff3366; font-family: Oswald; font-weight: 700; letter-spacing: 1px;'>☠️ OP CONTROL</h2>", unsafe_allow_html=True)
    acc_balance = st.number_input("CAPITAL (USD):", min_value=10.0, value=1000.0, step=100.0)
    risk_pct = st.slider("RISK PER TRADE (%):", min_value=0.5, max_value=5.0, value=1.0, step=0.5)
    st.markdown("---")
    if st.button("🔥 IGNITE OVERPOWER SCAN"):
        with st.spinner("QUANTUM ENGINE IS CALCULATING..."):
            st.session_state.cal_impact_dict = fetch_live_calendar()
            st.session_state.op_data = [fetch_op_forex(t) for t in roster_forex]
            st.session_state.op_data = [x for x in st.session_state.op_data if x is not None]
            st.session_state.last_run = datetime.now(pytz.timezone('Asia/Jakarta')).strftime("%H:%M:%S WIB")
            st.session_state.play_alarm = True
        st.rerun()

st.markdown("<p class='title-op'>JIHAN-GHINA FX <span style='color: #ffffff; font-size: 2rem;'>v10.6 GLOW EDITION</span></p>", unsafe_allow_html=True)

if not st.session_state.op_data:
    st.markdown("""
    <div style="background: rgba(255, 51, 102, 0.05); border: 1px dashed #ff3366; padding: 40px; text-align: center; border-radius: 10px; margin-top: 30px;">
        <h2 style="color: #ff3366; font-family: Oswald;">SYSTEM ON STANDBY</h2>
        <p style="color: #9ca3af;">Silakan klik tombol <b>IGNITE OVERPOWER SCAN</b> di panel kiri untuk memulai.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    st.markdown(f"<p style='color:#9ca3af; font-weight: bold;'>⚡ Last Live Matrix Update: <span style='color:#ff3366;'>{st.session_state.get('last_run', '')}</span></p>", unsafe_allow_html=True)
    
    cal_mod = st.session_state.get("cal_impact_dict", {})
    final_macro_db = {k: v["Skor_Base"] + cal_mod.get(k, 0) for k, v in DB_MACRO_BASE.items()}
    
    mac_cols = st.columns(8)
    for idx, (curr, score) in enumerate(final_macro_db.items()):
        with mac_cols[idx]:
            c_color = "#00ff88" if score > 15 else ("#ff0055" if score < -15 else "#fbbf24")
            # Glow color menyesuaikan dengan warna teks
            glow_color = "rgba(0, 255, 136, 0.3)" if score > 15 else ("rgba(255, 0, 85, 0.3)" if score < -15 else "rgba(251, 191, 36, 0.3)")
            border_color = "rgba(0, 255, 136, 0.5)" if score > 15 else ("rgba(255, 0, 85, 0.5)" if score < -15 else "rgba(251, 191, 36, 0.5)")
            
            # CSS inline khusus untuk override hover glow sesuai warna
            st.markdown(f"""
            <style>
                .badge-{curr}:hover {{
                    box-shadow: 0 10px 20px {glow_color} !important;
                    border: 1px solid {border_color} !important;
                }}
            </style>
            <div class="macro-badge badge-{curr}">
                <p style="margin:0; font-size:0.8rem; color:#9ca3af; font-weight:bold;">{curr}</p>
                <p style="margin:5px 0 0 0; font-size:1.6rem; font-family:Oswald; color:{c_color};">{score:+d}</p>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("<br>", unsafe_allow_html=True)

    matrix_rows = []
    has_titanium = False
    
    for raw in st.session_state.op_data:
        pair = raw["NAMA"]
        if "GOLD" in pair: 
            f_score = 30 if final_macro_db["USD"] < 0 else -30
        else:
            try:
                b, q = pair.split("/")
                f_score = final_macro_db[b] - final_macro_db[q]
            except: f_score = 0
            
        total_score = raw["TECH_SCORE"] + f_score
        
        if total_score >= 60: 
            rek = "🔥 TITANIUM BUY"
            has_titanium = True
        elif total_score >= 30: rek = "🟢 STRONG BUY"
        elif total_score <= -60: 
            rek = "🩸 TITANIUM SELL"
            has_titanium = True
        elif total_score <= -30: rek = "🔴 STRONG SELL"
        else: rek = "⚪ NEUTRAL / WAIT"
        
        matrix_rows.append({
            "ASSET": pair,
            "TREND (D|H4|H1)": raw["MTF"],
            "RSI 14": round(raw["RSI"], 1),
            "MACD": raw["MACD_SIGNAL"],
            "FUNDAMENTAL ACCEL": f_score,
            "OP SCORE": total_score,
            "SIGNAL": rek
        })
        
    if has_titanium and st.session_state.play_alarm:
        components.html("""
            <script>
                var audio = new Audio('https://actions.google.com/sounds/v1/alarms/digital_watch_alarm_long.ogg');
                audio.play();
            </script>
        """, height=0, width=0)
        st.session_state.play_alarm = False

    def style_matrix(val):
        if isinstance(val, str):
            if "TITANIUM BUY" in val: return 'color: #00ff88; font-weight: 900; background-color: rgba(0, 255, 136, 0.1);'
            elif "STRONG BUY" in val: return 'color: #00ff88; font-weight: bold;'
            elif "TITANIUM SELL" in val: return 'color: #ff0055; font-weight: 900; background-color: rgba(255, 0, 85, 0.1);'
            elif "STRONG SELL" in val: return 'color: #ff0055; font-weight: bold;'
            elif "BULL" in val: return 'color: #00ff88;'
            elif "BEAR" in val: return 'color: #ff0055;'
        elif isinstance(val, (int, float)):
            if val > 30: return 'color: #00ff88; font-weight: bold;'
            elif val < -30: return 'color: #ff0055; font-weight: bold;'
        return ''

    st.dataframe(pd.DataFrame(matrix_rows).style.applymap(style_matrix), use_container_width=True, hide_index=True)

    # ==========================================
    # 5. TITANIUM EXECUTION MANAGER
    # ==========================================
    st.markdown("---")
    st.markdown("### 🎯 TITANIUM TACTICAL EXECUTION")
    
    col1, col2 = st.columns([1, 2])
    with col1:
        pilihan = st.selectbox("SELECT ASSET FOR EXECUTION:", [x["NAMA"] for x in st.session_state.op_data])
    
    active_data = next((item for item in st.session_state.op_data if item["NAMA"] == pilihan), None)
    active_matrix = next((item for item in matrix_rows if item["ASSET"] == pilihan), None)
    
    if active_data and active_matrix:
        harga = active_data["HARGA"]
        atr = active_data["ATR"]
        sig = active_matrix["SIGNAL"]
        f_score = active_matrix["FUNDAMENTAL ACCEL"]
        
        if "GOLD" in pilihan:
            ringkasan_fund = f"Fundamental Support: XAU (Safe Haven) vs USD ({final_macro_db['USD']:+d}) = Dorongan Sektoral {f_score:+d}"
        else:
            b, q = pilihan.split("/")
            ringkasan_fund = f"Fundamental Support: {b} ({final_macro_db.get(b,0):+d}) mendominasi {q} ({final_macro_db.get(q,0):+d}) = Kekuatan Tren {f_score:+d}"

        is_buy = "BUY" in sig
        is_sell = "SELL" in sig
        
        sl_dist = 2.0 * atr
        risk_amount = acc_balance * (risk_pct / 100)
        
        if "JPY" in active_data["TICKER"]: pips, pip_val, fmt = sl_dist * 100, 7.00, ".3f"
        elif "XAU" in active_data["TICKER"]: pips, pip_val, fmt = sl_dist * 10, 10.0, ".3f"
        else: pips, pip_val, fmt = sl_dist * 10000, 10.0, ".5f"
            
        lot = max(0.01, round((risk_amount / (pips * pip_val)) if pips > 0 else 0, 2))
        
        now_jkt = datetime.now(pytz.timezone('Asia/Jakarta'))
        menit_sisa = 60 - now_jkt.minute
        
        if is_buy:
            sl = harga - sl_dist
            tp1, tp2 = harga + (sl_dist * 1.5), harga + (sl_dist * 3.0)
            entry_area = f"{active_data['EMA20']:{fmt}}"
            color = "#00ff88"
        elif is_sell:
            sl = harga + sl_dist
            tp1, tp2 = harga - (sl_dist * 1.5), harga - (sl_dist * 3.0)
            entry_area = f"{active_data['EMA20']:{fmt}}"
            color = "#ff0055"
        else:
            sl = tp1 = tp2 = harga
            entry_area = "N/A"
            lot, color = 0.00, "#9ca3af"
            ringkasan_fund = "Fundamental dan Teknikal sedang tidak searah (Sideways)."

        st.markdown(f"""
        <div class="directive-card">
            <h3 style="color: {color}; font-family: Oswald; margin-bottom: 5px;">{sig}</h3>
            <p style="color: #ffffff; font-size: 1.2rem; font-weight: bold; margin-bottom: 5px;">Harga Real-Time: <span style="color: #ff9933;">{format(harga, fmt)}</span></p>
            <p style="color: #9ca3af; font-size: 0.9rem; margin-bottom: 5px;">📊 <b>{ringkasan_fund}</b></p>
            <p style="color: #ff3366; font-size: 0.9rem; margin-bottom: 25px;">⏳ <b>EXPIRED DALAM:</b> {menit_sisa} Menit (Berakhir saat penutupan candle jam ini)</p>
            
            <div style="display: grid; grid-template-columns: repeat(4, 1fr); gap: 15px; background: rgba(0,0,0,0.3); padding: 15px; border-radius: 8px;">
                <div>
                    <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;">RECOMMENDED LOT (RISK: ${risk_amount:.2f})</p>
                    <p class="metric-value" style="color: #ffffff;">{lot}</p>
                </div>
                <div>
                    <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;">IDEAL ENTRY (EMA20 PULLBACK)</p>
                    <p class="metric-value" style="color: #ff9933;">{entry_area}</p>
                </div>
                <div>
                    <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;">STOP LOSS (-1R)</p>
                    <p class="metric-value" style="color: #ff0055;">{format(sl, fmt)}</p>
                </div>
                <div>
                    <p style="color: #9ca3af; font-size: 0.8rem; margin: 0;">TARGET (1.5R / 3R)</p>
                    <p class="metric-value" style="color: #00ff88;">{format(tp1, fmt)} <br> {format(tp2, fmt)}</p>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<br><h4 style='font-family: Oswald;'>📈 DYNAMIC CHART VISUALIZER</h4>", unsafe_allow_html=True)
        
        tf_map = {"M15 (Scalping)": "15m", "H1 (Intraday)": "1h", "H4 (Swing)": "4h"}
        selected_tf_label = st.radio("PILIH TIMEFRAME GRAFIK:", list(tf_map.keys()), horizontal=True)
        selected_tf = tf_map[selected_tf_label]
        
        try:
            with st.spinner("Memuat grafik..."):
                tk_chart = yf.Ticker(active_data["TICKER"])
                df_chart = tk_chart.history(period="2wk" if selected_tf == "15m" else "1mo", interval=selected_tf).ffill()
                
                df_chart['EMA20'] = df_chart['Close'].ewm(span=20, adjust=False).mean()
                df_chart['EMA50'] = df_chart['Close'].ewm(span=50, adjust=False).mean()
                df_chart = df_chart.tail(100)
                
                fig = go.Figure()
                fig.add_trace(go.Candlestick(x=df_chart.index, open=df_chart['Open'], high=df_chart['High'], low=df_chart['Low'], close=df_chart['Close'], name='Price', increasing_line_color='#00ff88', decreasing_line_color='#ff0055'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA20'], mode='lines', line=dict(color='#ff9933', width=2), name='EMA 20'))
                fig.add_trace(go.Scatter(x=df_chart.index, y=df_chart['EMA50'], mode='lines', line=dict(color='#3399ff', width=2, dash='dot'), name='EMA 50'))
                
                # MODIFIKASI: Memindahkan legend ke atas dan mengatur margin agar terlihat luas
                fig.update_layout(
                    paper_bgcolor='rgba(0,0,0,0)', 
                    plot_bgcolor='rgba(15, 10, 12, 0.8)', 
                    margin=dict(l=0, r=0, t=40, b=0), # Margin atas ditambah untuk legend
                    height=480, 
                    xaxis_rangeslider_visible=False,
                    legend=dict(
                        orientation="h",       # Legend horizontal
                        yanchor="bottom",      
                        y=1.02,                # Posisi di atas chart (y > 1)
                        xanchor="right", 
                        x=1                    # Rata kanan
                    )
                )
                fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')
                fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='rgba(255,255,255,0.05)')
                st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})
        except:
            st.error("Gagal memuat grafik. Data dari Yahoo Finance sedang sibuk.")

    # ==========================================
    # 6. J-G FX ACADEMY BOOK
    # ==========================================
    st.markdown("---")
    with st.expander("📚 BUKU PANDUAN ACADEMY (Cara Kerja Sistem V10.6)", expanded=False):
        st.markdown("""
        ### 🧠 1. Memahami Global Macro Strength Index (Fundamental Score)
        Sistem ini tidak hanya melihat grafik, tetapi mengukur kekuatan uang antar negara secara *real-time*.
        * **Base Score:** Setiap negara memiliki nilai dasar berdasarkan suku bunga bank sentralnya (Contoh: Suku bunga The Fed AS tinggi, maka skor USD tinggi).
        * **Live News Impact:** Jika ada berita ekonomi penting (seperti NFP, Inflasi CPI) yang hasilnya mengejutkan pasar, sistem otomatis menambahkan **+20** atau mengurangkan **-20** ke skor mata uang tersebut secara seketika.
        * **Cara Baca:** Selalu pasangkan mata uang yang berwarna **Hijau (Kuat)** melawan mata uang yang berwarna **Merah (Lemah)**.

        ### ⚙️ 2. Technical Score (Analisa Harga)
        Setelah fundamental terbaca, sistem melakukan konfirmasi melalui data harga (Teknikal) menggunakan indikator berlapis:
        * **Tren Multi-Timeframe:** Mencocokkan arah trend pada Daily, H4, dan H1.
        * **RSI (Relative Strength Index):** Mencari posisi harga yang sehat (tidak overbought/oversold sebelum waktunya).
        * **MACD & EMA 20/50:** Mencari persilangan momentum (Crossover).

        ### 🎯 3. Sistem OP Score & Keputusan Sinyal
        **OP SCORE** adalah gabungan total dari `Fundamental Accel + Technical Score`.
        * **🔥 TITANIUM (Score > 60 atau < -60):** Ini adalah sinyal kelas institusi. Fundamental dan Teknikal searah dan saling mendukung dengan sangat kuat. Eksekusi probabilitas tertinggi!
        * **🟢/🔴 STRONG (Score > 30 atau < -30):** Tren cukup bagus secara teknikal, namun dorongan berita fundamental mungkin biasa saja. Bisa ditradingkan dengan lot wajar.
        * **⚪ NEUTRAL / WAIT:** Arah market sedang *sideways* (Ragu-ragu). Fundamental menolak pergerakan teknikal. Sistem melarang Anda melakukan entry.
        
        *Jangan pernah entry di tengah-tengah jalan harga. Selalu tunggu harga mendekati area **IDEAL ENTRY (EMA20)** untuk rasio Risk/Reward yang sehat.*
        """)
