import streamlit as st
import time
import requests
import ccxt
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Pro Crypto Scanner", page_icon="🎯", layout="centered")
st.title("🎯 Pro Trader Signal Scanner (OKX & KuCoin)")

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

def get_filtered_usdt_pairs(exchange_obj, min_volume_usdt=10000000, limit=200):
    try:
        tickers = exchange_obj.fetch_tickers()
        valid_pairs = []
        for symbol, ticker in tickers.items():
            if symbol.endswith('/USDT') and ticker.get('quoteVolume'):
                if ticker['quoteVolume'] >= min_volume_usdt:
                    valid_pairs.append((symbol, ticker['quoteVolume']))
        
        valid_pairs.sort(key=lambda x: x[1], reverse=True)
        return [pair[0] for pair in valid_pairs[:limit]]
    except Exception as e:
        st.error("Error fetching pairs")
        return []

# UI Controls
st.subheader("🤖 Bot Status & Controls")
if st.button("📢 Send Test Message"):
    res = send_telegram("🤖 *Pro Trader Scanner Connected Successfully!*")
    st.success("Test Message Sent!")

st.markdown("---")
run_scanner = st.checkbox("Start Pro Scanner Loop (High Volume Pairs)")

if run_scanner:
    st.info("Scanner Loop Active... Filtering Market with 4H Trend & Risk-Reward.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    signals_container = st.container()
    
    for ex_name, ex_obj in exchanges.items():
        status_text.text("Fetching pairs from " + ex_name)
        symbols = get_filtered_usdt_pairs(ex_obj, min_volume_usdt=10000000, limit=200)
        total_symbols = len(symbols)
        
        for idx, symbol in enumerate(symbols):
            percent_complete = int(((idx + 1) / total_symbols) * 100)
            progress_bar.progress(percent_complete)
            status_text.markdown("⏳ Scanning **" + ex_name + "**: `" + symbol + "` (" + str(idx+1) + "/" + str(total_symbols) + " - **" + str(percent_complete) + "%**)")
            
            try:
                # 1. 4-Hour Timeframe (Trend Filter)
                bars_4h = ex_obj.fetch_ohlcv(symbol, timeframe='4h', limit=200)
                df_4h = pd.DataFrame(bars_4h, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                df_4h['EMA_200'] = df_4h['close'].ewm(span=200, adjust=False).mean()
                is_4h_uptrend = df_4h['close'].iloc[-1] > df_4h['EMA_200'].iloc[-1]
                is_4h_downtrend = df_4h['close'].iloc[-1] < df_4h['EMA_200'].iloc[-1]

                # 2. 1-Hour Timeframe (Trigger Execution)
                bars_1h = ex_obj.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                df = pd.DataFrame(bars_1h, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                
                df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
                df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
                df['RSI'] = calculate_rsi(df['close'], 14)
                
                curr = df.iloc[-1]
                prev = df.iloc[-2]
                prev2 = df.iloc[-3]
                
                bullish_fvg = curr['low'] > prev2['high']
                bearish_fvg = curr['high'] < prev2['low']
                
                entry = round(curr['close'], 4)
                rsi = round(curr['RSI'], 1)
                
                # LONG SETUP
                if is_4h_uptrend and (prev['EMA_20'] < prev['EMA_50'] and curr['EMA_20'] > curr['EMA_50']) and rsi > 45 and bullish_fvg:
                    sl = round(prev2['low'], 4)
                    risk = entry - sl
                    if risk > 0:
                        tp1 = round(entry + (risk * 1.5), 4)
                        tp2 = round(entry + (risk * 2.5), 4)
                        
                        msg = "🟢 *PRO LONG SETUP FOUND!*\n\n" + "🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + str(entry) + "\n🛑 *Stop Loss:* $" + str(sl) + "\n🎯 *Target 1:* $" + str(tp1) + "\n🚀 *Target 2:* $" + str(tp2) + "\n📊 *RSI:* " + str(rsi)
                        send_telegram(msg)
                        
                        with signals_container:
                            with st.expander("🟢 LONG: " + symbol + " (" + ex_name + ")", expanded=True):
                                st.metric(label=symbol + " Entry", value="$" + str(entry), delta="PRO LONG SETUP")
                                st.write("**SL:** $" + str(sl) + " | **TP1:** $" + str(tp1) + " \vert{} **TP2:** $" + str(tp2))

                # SHORT SETUP
                elif is_4h_downtrend and (prev['EMA_20'] > prev['EMA_50'] and curr['EMA_20'] < curr['EMA_50']) and rsi < 55 and bearish_fvg:
                    sl = round(prev2['high'], 4)
                    risk = sl - entry
                    if risk > 0:
                        tp1 = round(entry - (risk * 1.5), 4)
                        tp2 = round(entry - (risk * 2.5), 4)
                        
                        msg = "🔴 *PRO SHORT SETUP FOUND!*\n\n" + "🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + str(entry) + "\n🛑 *Stop Loss:* $" + str(sl) + "\n🎯 *Target 1:* $" + str(tp1) + "\n🚀 *Target 2:* $" + str(tp2) + "\n📊 *RSI:* " + str(rsi)
                        send_telegram(msg)
                        
                        with signals_container:
                            with st.expander("🔴 SHORT: " + symbol + " (" + ex_name + ")", expanded=True):
                                st.metric(label=symbol + " Entry", value="$" + str(entry), delta="-PRO SHORT SETUP", delta_color="inverse")
                                st.write("**SL:** $" + str(sl) + " | **TP1:** $" + str(tp1) + " \vert{} **TP2:** $" + str(tp2))

                time.sleep(0.1)
                
            except Exception:
                continue
            
    status_text.success("✅ Market Scan Completed Successfully!")
    progress_bar.progress(100)
