import streamlit as st
import time
import requests
import ccxt
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="15M Scalping Scanner", page_icon="🎯", layout="centered")
st.title("🎯 Fast 15M Scalper Scanner (OKX & KuCoin)")

# --- CREDENTIALS ---
TELEGRAM_TOKEN = "8812805030:AAEA-Un5dpDtjDxrO89Nz06u7cVNsXLgzYg"
CHAT_ID = "@singnalsbyAK"

exchanges = {
    'OKX': ccxt.okx({'enableRateLimit': True}),
    'KuCoin': ccxt.kucoin({'enableRateLimit': True})
}

def send_telegram(message):
    url = "https://api.telegram.org/bot" + TELEGRAM_TOKEN + "/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload)
        return res.json()
    except Exception as e:
        return str(e)

def format_price(price):
    if price < 0.01:
        return "{:.6f}".format(price)
    elif price < 1.0:
        return "{:.4f}".format(price)
    else:
        return "{:.2f}".format(price)

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
        return []

st.subheader("🤖 Bot Status & Controls")
run_scanner = st.checkbox("Start 15M Scalping Scanner Loop")

if run_scanner:
    st.info("Scalping Active... Scanning 15M timeframe with Precision Price Formatting.")
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    signals_container = st.container()
    
    while run_scanner:
        total_signals_this_run = 0
        
        for ex_name, ex_obj in exchanges.items():
            symbols = get_top_pairs(ex_obj, limit=200)
            total_symbols = len(symbols)
            
            for idx, symbol in enumerate(symbols):
                percent_complete = int(((idx + 1) / total_symbols) * 100)
                progress_bar.progress(percent_complete)
                status_text.markdown("⏳ Scanning **" + ex_name + "**: `" + symbol + "` (" + str(idx+1) + "/" + str(total_symbols) + " - **" + str(percent_complete) + "%**)")
                
                try:
                    bars_15m = ex_obj.fetch_ohlcv(symbol, timeframe='15m', limit=60)
                    df = pd.DataFrame(bars_15m, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    
                    df['EMA_20'] = df['close'].ewm(span=20, adjust=False).mean()
                    df['EMA_50'] = df['close'].ewm(span=50, adjust=False).mean()
                    df['RSI'] = calculate_rsi(df['close'], 14)
                    
                    curr = df.iloc[-1]
                    prev = df.iloc[-2]
                    
                    ema_long = (prev['EMA_20'] <= prev['EMA_50']) and (curr['EMA_20'] > curr['EMA_50'])
                    ema_short = (prev['EMA_20'] >= prev['EMA_50']) and (curr['EMA_20'] < curr['EMA_50'])
                    
                    entry = curr['close']
                    rsi = round(curr['RSI'], 1)
                    
                    tight_risk_dist = entry * 0.01  
                    
                    # LONG SCALP
                    if ema_long and rsi >= 45:
                        sl = entry - tight_risk_dist
                        tp1 = entry + (tight_risk_dist * 1.5)
                        tp2 = entry + (tight_risk_dist * 2.5)
                        
                        entry_str = format_price(entry)
                        sl_str = format_price(sl)
                        tp1_str = format_price(tp1)
                        tp2_str = format_price(tp2)
                        
                        msg = "🟢 *15M SCALP LONG!*\n\n🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + entry_str + "\n🛑 *SL (1\%):* $" + sl_str + "\n🎯 *TP1:* $" + tp1_str + "\n🚀 *TP2:* $" + tp2_str + "\n📊 *RSI:* " + str(rsi)
                        send_telegram(msg)
                        total_signals_this_run += 1
                        
                        with signals_container:
                            with st.expander("🟢 SCALP LONG: " + symbol + " (" + ex_name + ")", expanded=True):
                                st.metric(label=symbol + " Entry", value="$" + entry_str, delta="SCALP LONG")
                                st.write("**SL:** $" + sl_str + " | **TP1:** $" + tp1_str + " \vert{} **TP2:** $" + str(tp2_str))

                    # SHORT SCALP
                    elif ema_short and rsi <= 55:
                        sl = entry + tight_risk_dist
                        tp1 = entry - (tight_risk_dist * 1.5)
                        tp2 = entry - (tight_risk_dist * 2.5)
                        
                        entry_str = format_price(entry)
                        sl_str = format_price(sl)
                        tp1_str = format_price(tp1)
                        tp2_str = format_price(tp2)
                        
                        msg = "🔴 *15M SCALP SHORT!*\n\n🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + entry_str + "\n🛑 *SL (1\%):* $" + sl_str + "\n🎯 *TP1:* $" + tp1_str + "\n🚀 *TP2:* $" + tp2_str + "\n📊 *RSI:* " + str(rsi)
                        send_telegram(msg)
                        total_signals_this_run += 1
                        
                        with signals_container:
                            with st.expander("🔴 SCALP SHORT: " + symbol + " (" + ex_name + ")", expanded=True):
                                st.metric(label=symbol + " Entry", value="$" + entry_str, delta="-SCALP SHORT", delta_color="inverse")
                                st.write("**SL:** $" + sl_str + " | **TP1:** $" + tp1_str + " \vert{} **TP2:** $" + str(tp2_str))

                    time.sleep(0.02)
                    
                except Exception:
                    continue
                
        status_text.success("✅ Scan Complete. Found " + str(total_signals_this_run) + " signals. Re-scanning in 3 minutes...")
        progress_bar.progress(100)
        time.sleep(180)
        st.rerun()
