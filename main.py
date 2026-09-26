import streamlit as st
import time
import requests
import ccxt
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Crypto Signal Scanner", page_icon="🎯", layout="centered")
st.title("🎯 Live Crypto Signal Scanner (OKX & KuCoin)")

# --- CREDENTIALS ---
TELEGRAM_TOKEN = "8812805030:AAEA-Un5dpDtjDxrO89Nz06u7cVNsXLgzYg"
CHAT_ID = "@singnalsbyAK"

# --- EXCHANGES SETUP ---
exchanges = {
    'OKX': ccxt.okx({'enableRateLimit': True}),
    'KuCoin': ccxt.kucoin({'enableRateLimit': True})
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        return str(e)

def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_top_pairs(exchange_obj, limit=200):
    try:
        markets = exchange_obj.load_markets()
        usdt_pairs = [
            symbol for symbol in markets.keys() 
            if symbol.endswith('/USDT') and markets[symbol]['active']
        ]
        return usdt_pairs[:limit]
    except Exception as e:
        st.error("Error fetching pairs")
        return []

# UI Controls
st.subheader("🤖 Bot Status & Controls")
if st.button("📢 Send Test Message"):
    res = send_telegram("🤖 *Crypto Scanner Connected Successfully!*")
    st.success("Test Message Sent!")

st.markdown("---")
run_scanner = st.checkbox("Start Continuous Scanner Loop")

if run_scanner:
    st.info("Scanner Loop Active... Running background scans every 10 mins.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    signals_container = st.container()
    
    while run_scanner:
        total_signals_this_run = 0
        
        for ex_name, ex_obj in exchanges.items():
            status_text.text("Fetching pairs from " + ex_name)
            symbols = get_top_pairs(ex_obj, limit=200)
            total_symbols = len(symbols)
            
            for idx, symbol in enumerate(symbols):
                percent_complete = int(((idx + 1) / total_symbols) * 100)
                progress_bar.progress(percent_complete)
                status_text.markdown("⏳ Scanning **" + ex_name + "**: `" + symbol + "` (" + str(idx+1) + "/" + str(total_symbols) + " - **" + str(percent_complete) + "%**)")
                
                try:
                    # 1-Hour Timeframe Execution
                    bars_1h = ex_obj.fetch_ohlcv(symbol, timeframe='1h', limit=60)
                    df = pd.DataFrame(bars_1h, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    
                    df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
                    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
                    df['RSI'] = calculate_rsi(df['close'], 14)
                    
                    curr = df.iloc[-1]
                    prev = df.iloc[-2]
                    prev2 = df.iloc[-3]
                    
                    # Core Trigger Conditions
                    ema_long = (prev['EMA_20'] <= prev['EMA_50']) and (curr['EMA_20'] > curr['EMA_50'])
                    ema_short = (prev['EMA_20'] >= prev['EMA_50']) and (curr['EMA_20'] < curr['EMA_50'])
                    
                    bullish_fvg = curr['low'] > prev2['high']
                    bearish_fvg = curr['high'] < prev2['low']
                    
                    entry = round(curr['close'], 4)
                    rsi = round(curr['RSI'], 1)
                    
                    # FLEXIBLE LONG SETUP (EMA Cross OR FVG + RSI Support)
                    if (ema_long or bullish_fvg) and rsi >= 40:
                        sl = round(prev2['low'], 4)
                        risk = entry - sl
                        if risk > 0:
                            tp1 = round(entry + (risk * 1.5), 4)
                            tp2 = round(entry + (risk * 2.5), 4)
                            
                            msg = "🟢 *LONG SETUP FOUND!*\n\n" + "🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + str(entry) + "\n🛑 *Stop Loss:* $" + str(sl) + "\n🎯 *Target 1:* $" + str(tp1) + "\n🚀 *Target 2:* $" + str(tp2) + "\n📊 *RSI:* " + str(rsi)
                            send_telegram(msg)
                            total_signals_this_run += 1
                            
                            with signals_container:
                                with st.expander("🟢 LONG: " + symbol + " (" + ex_name + ")", expanded=True):
                                    st.metric(label=symbol + " Entry", value="$" + str(entry), delta="LONG SETUP")
                                    st.write("**SL:** $" + str(sl) + " | **TP1:** $" + str(tp1) + " \vert{} **TP2:** $" + str(tp2))

                    # FLEXIBLE SHORT SETUP (EMA Cross OR FVG + RSI Resistance)
                    elif (ema_short or bearish_fvg) and rsi <= 60:
                        sl = round(prev2['high'], 4)
                        risk = sl - entry
                        if risk > 0:
                            tp1 = round(entry - (risk * 1.5), 4)
                            tp2 = round(entry - (risk * 2.5), 4)
                            
                            msg = "🔴 *SHORT SETUP FOUND!*\n\n" + "🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + str(entry) + "\n🛑 *Stop Loss:* $" + str(sl) + "\n🎯 *Target 1:* $" + str(tp1) + "\n🚀 *Target 2:* $" + str(tp2) + "\n📊 *RSI:* " + str(rsi)
                            send_telegram(msg)
                            total_signals_this_run += 1
                            
                            with signals_container:
                                with st.expander("🔴 SHORT: " + symbol + " (" + ex_name + ")", expanded=True):
                                    st.metric(label=symbol + " Entry", value="$" + str(entry), delta="-SHORT SETUP", delta_color="inverse")
                                    st.write("**SL:** $" + str(sl) + " | **TP1:** $" + str(tp1) + " \vert{} **TP2:** $" + str(tp2))

                    time.sleep(0.02)
                    
                except Exception:
                    continue
                
        status_text.success("✅ Cycle Complete. Found " + str(total_signals_this_run) + " setups. Waiting 10 minutes for next cycle...")
        progress_bar.progress(100)
        time.sleep(600)
        st.rerun()
      
