import streamlit as st
import time
import requests
import ccxt
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="OKX & KuCoin Scanner", page_icon="📈", layout="centered")
st.title("🚀 Crypto Signal Bot (OKX & KuCoin)")

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

# --- TECHNICAL INDICATORS ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def get_top_usdt_pairs(exchange_obj, limit=500):
    try:
        markets = exchange_obj.load_markets()
        usdt_pairs = [
            symbol for symbol in markets.keys() 
            if symbol.endswith('/USDT') and markets[symbol]['active']
        ]
        return usdt_pairs[:limit]
    except Exception as e:
        st.error(f"Error fetching markets: {e}")
        return []

# UI Controls
st.subheader("🤖 Bot Status & Controls")
if st.button("📢 Send Test Message"):
    res = send_telegram("🤖 *OKX & KuCoin Scanner Connected Successfully!*")
    st.success("Test Message Sent!")

st.markdown("---")
run_scanner = st.checkbox("Start Live Scanner (OKX + KuCoin - 1000 Coins)")

if run_scanner:
    st.info("Scanner Loop Active... Monitoring OKX & KuCoin Pairs.")
    
    # Progress UI Elements
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    signals_container = st.container()
    
    for ex_name, ex_obj in exchanges.items():
        status_text.text(f"🔍 Fetching pairs from {ex_name}...")
        symbols = get_top_usdt_pairs(ex_obj, limit=500)
        total_symbols = len(symbols)
        
        for idx, symbol in enumerate(symbols):
            # Progress calculation & percentage bar
            percent_complete = int(((idx + 1) / total_symbols) * 100)
            progress_bar.progress(percent_complete)
            status_text.markdown(f"⏳ **Scanning {ex_name}:** `{symbol}` ({idx+1}/{total_symbols} - **{percent_complete}%**)")
            
            try:
                bars = ex_obj.fetch_ohlcv(symbol, timeframe='1h', limit=100)
                df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                
                # EMA & RSI Calculations
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
                    msg = f"🟢 *LONG SETUP FOUND!*\n\n🏛 *Exchange:* {ex_name}\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: EMA Crossover + Bullish FVG!"
                    send_telegram(msg)
                    
                    # Mobile Friendly Box UI
                    with signals_container:
                        with st.expander(f"🟢 LONG: {symbol} ({ex_name})", expanded=True):
                            st.metric(label=f"{symbol} Price", value=f"${price}", delta="LONG SETUP")
                            st.write(f"**RSI:** {rsi} | **Reason:** EMA Cross + Bullish FVG")
                
                # SHORT SIGNAL
                elif (prev['EMA_20'] > prev['EMA_50'] and curr['EMA_20'] < curr['EMA_50']) and rsi < 55 and bearish_fvg:
                    msg = f"🔴 *SHORT SETUP FOUND!*\n\n🏛 *Exchange:* {ex_name}\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: Bearish EMA Cross + ICT FVG!"
                    send_telegram(msg)
                    
                    # Mobile Friendly Box UI
                    with signals_container:
                        with st.expander(f"🔴 SHORT: {symbol} ({ex_name})", expanded=True):
                            st.metric(label=f"{symbol} Price", value=f"${price}", delta="-SHORT SETUP", delta_color="inverse")
                            st.write(f"**RSI:** {rsi} | **Reason:** Bearish EMA Cross + FVG")
                            
                time.sleep(0.1)
                
            except Exception:
                continue
            
    status_text.success("✅ Full Market Scan Completed!")
    progress_bar.progress(100)
