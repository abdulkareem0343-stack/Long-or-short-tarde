import streamlit as st
import time
import requests
import ccxt
import pandas as pd
import pandas_ta as ta

# --- APP TITLE & LAYOUT ---
st.set_page_config(page_title="Crypto Signal Bot", page_icon="📈")
st.title("🚀 Crypto Signal Bot Dashboard")

# --- CREDENTIALS ---
TELEGRAM_TOKEN = "8812805030:AAEA-Un5dpDtjDxrO89Nz06u7cVNsXLgzYg"
CHAT_ID = "@singnalsbyAK"

# Exchange setup
exchange = ccxt.binance()
symbols = ['BTC/USDT', 'ETH/USDT', 'SOL/USDT', 'BNB/USDT', 'XRP/USDT', 'ADA/USDT', 'DOGE/USDT', 'AVAX/USDT']

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        return str(e)

# Streamlit UI Buttons
st.subheader("🤖 Bot Control")
if st.button("📢 Send Test Message to Telegram"):
    result = send_telegram("🤖 *Crypto Signal Bot Connected Successfully!*")
    st.success("Test Message Sent!")

# Auto Scanner Toggle
st.markdown("---")
st.subheader("🔍 Live Market Scanner")
run_scanner = st.checkbox("Start 24/7 Scanner Loop")

if run_scanner:
    st.info("Scanner is active... Checking market every 5 minutes.")
    
    # Persistent Loop
    while run_scanner:
        for symbol in symbols:
            try:
                bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                
                df['EMA_20'] = ta.ema(df['close'], length=20)
                df['EMA_50'] = ta.ema(df['close'], length=50)
                df['RSI'] = ta.rsi(df['close'], length=14)
                
                curr = df.iloc[-1]
                prev = df.iloc[-2]
                prev2 = df.iloc[-3]
                
                bullish_fvg = curr['low'] > prev2['high']
                bearish_fvg = curr['high'] < prev2['low']
                
                price = curr['close']
                rsi = round(curr['RSI'], 1)
                
                # LONG SIGNAL
                if (prev['EMA_20'] < prev['EMA_50'] and curr['EMA_20'] > curr['EMA_50']) and rsi > 45 and bullish_fvg:
                    msg = f"🟢 *LONG SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: EMA Crossover + Bullish FVG!"
                    send_telegram(msg)
                    st.write(f"Alert Sent for {symbol} (LONG)")
                    
                # SHORT SIGNAL
                elif (prev['EMA_20'] > prev['EMA_50'] and curr['EMA_20'] < curr['EMA_50']) and rsi < 55 and bearish_fvg:
                    msg = f"🔴 *SHORT SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: Bearish EMA Cross + FVG!"
                    send_telegram(msg)
                    st.write(f"Alert Sent for {symbol} (SHORT)")
                    
            except Exception as e:
                pass
                
        st.write("Scan complete. Waiting 5 minutes for next cycle...")
        time.sleep(300)
        st.rerun()
