import streamlit as st
import time
import requests
import ccxt
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="Crypto Scanner Bot", page_icon="📈")
st.title("🚀 Crypto Signal Bot Dashboard")

# --- CREDENTIALS ---
TELEGRAM_TOKEN = "8812805030:AAEA-Un5dpDtjDxrO89Nz06u7cVNsXLgzYg"
CHAT_ID = "@singnalsbyAK"

exchange = ccxt.binance({'enableRateLimit': True})
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT', 'LINK/USDT', 'SUI/USDT']

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        return str(e)

# --- TECHNICAL INDICATORS (PURE PANDAS - NO EXTRA LIB) ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# UI Controls
st.subheader("🤖 Bot Status & Controls")
if st.button("📢 Send Test Message"):
    res = send_telegram("🤖 *Crypto Scanner Connected Successfully!*")
    st.success("Test Message Sent!")

st.markdown("---")
run_scanner = st.checkbox("Start Live Scanner")

if run_scanner:
    st.info("Scanner Loop Active... Monitoring Top Pairs.")
    
    for symbol in symbols:
        try:
            bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
            df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
            
            # EMA Calculations
            df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
            df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
            df['RSI'] = calculate_rsi(df['close'], 14)
            
            curr = df.iloc[-1]
            prev = df.iloc[-2]
            prev2 = df.iloc[-3]
            
            # FVG Detection
            bullish_fvg = curr['low'] > prev2['high']
            bearish_fvg = curr['high'] < prev2['low']
            
            price = round(curr['close'], 4)
            rsi = round(curr['RSI'], 1)
            
            # LONG SIGNAL
            if (prev['EMA_20'] < prev['EMA_50'] and curr['EMA_20'] > curr['EMA_50']) and rsi > 45 and bullish_fvg:
                msg = f"🟢 *LONG SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: EMA Crossover + Bullish FVG!"
                send_telegram(msg)
                st.write(f"✅ Alert Sent: {symbol} (LONG)")
                
            # SHORT SIGNAL
            elif (prev['EMA_20'] > prev['EMA_50'] and curr['EMA_20'] < curr['EMA_50']) and rsi < 55 and bearish_fvg:
                msg = f"🔴 *SHORT SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: Bearish EMA Cross + ICT FVG!"
                send_telegram(msg)
                st.write(f"🚨 Alert Sent: {symbol} (SHORT)")
                
        except Exception as e:
            continue
            
    st.success("Scan Cycle Completed!")
