import streamlit as st
import time
import requests
import ccxt
import pandas as pd

# --- APP CONFIG ---
st.set_page_config(page_title="15M Structure Scalper", page_icon="⚡", layout="centered")
st.title("⚡ 15M Fast Structure Scalper (OKX & KuCoin)")

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
run_scanner = st.checkbox("Start 15M Scalper Loop")

if run_scanner:
    st.info("Scalper Active... Scanning 1H Trend + 15M Structure Setups.")
    
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
                    # 1. Macro Trend Filter (1H Timeframe - 200 EMA)
                    bars_1h = ex_obj.fetch_ohlcv(symbol, timeframe='1h', limit=200)
                    df_1h = pd.DataFrame(bars_1h, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    df_1h['EMA_200'] = df_1h['close'].ewm(span=200, adjust=False).mean()
                    
                    price_above_200 = df_1h.iloc[-1]['close'] > df_1h.iloc[-1]['EMA_200']
                    price_below_200 = df_1h.iloc[-1]['close'] < df_1h.iloc[-1]['EMA_200']
                    
                    # 2. Fast Scalping Execution (15M Timeframe Structure)
                    bars_15m = ex_obj.fetch_ohlcv(symbol, timeframe='15m', limit=50)
                    df_15m = pd.DataFrame(bars_15m, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
                    
                    c1 = df_15m.iloc[-3]
                    c2 = df_15m.iloc[-2]
                    c3 = df_15m.iloc[-1]
                    
                    entry = c3['close']
                    
                    # LONG SCALP: 1H Uptrend + 15M Inefficiency & Bullish Close
                    if price_above_200 and (c1['high'] < c3['low']) and (c3['close'] > c3['open']):
                        sl = min(c1['low'], c2['low'], c3['low'])
                        risk = entry - sl
                        
                        # Risk filter: Trade tabhi legi jab SL reasonable ho (>0)
                        if risk > 0:
                            tp1 = entry + (risk * 1.5)
                            tp2 = entry + (risk * 2.5)
                            
                            entry_str, sl_str = format_price(entry), format_price(sl)
                            tp1_str, tp2_str = format_price(tp1), format_price(tp2)
                            
                            msg = "⚡ *15M STRUCTURE SCALP LONG!*\n\n🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + entry_str + "\n🛑 *SL (15M Low):* $" + sl_str + "\n🎯 *TP1 (1:1.5):* $" + tp1_str + "\n🚀 *TP2 (1:2.5):* $" + tp2_str
                            send_telegram(msg)
                            total_signals_this_run += 1
                            
                            with signals_container:
                                with st.expander("⚡ SCALP LONG: " + symbol + " (" + ex_name + ")", expanded=True):
                                    st.metric(label=symbol + " Entry", value="$" + entry_str, delta="15M SCALP LONG")
                                    st.write("**SL:** $" + sl_str + " | **TP1:** $" + tp1_str + " \vert{} **TP2:** $" + tp2_str)

                    # SHORT SCALP: 1H Downtrend + 15M Inefficiency & Bearish Close
                    elif price_below_200 and (c1['low'] > c3['high']) and (c3['close'] < c3['open']):
                        sl = max(c1['high'], c2['high'], c3['high'])
                        risk = sl - entry
                        
                        if risk > 0:
                            tp1 = entry - (risk * 1.5)
                            tp2 = entry - (risk * 2.5)
                            
                            entry_str, sl_str = format_price(entry), format_price(sl)
                            tp1_str, tp2_str = format_price(tp1), format_price(tp2)
                            
                            msg = "⚡ *15M STRUCTURE SCALP SHORT!*\n\n🏛 *Exchange:* " + ex_name + "\n📌 *Coin:* " + symbol + "\n💵 *Entry:* $" + entry_str + "\n🛑 *SL (15M High):* $" + sl_str + "\n🎯 *TP1 (1:1.5):* $" + tp1_str + "\n🚀 *TP2 (1:2.5):* $" + tp2_str
                            send_telegram(msg)
                            total_signals_this_run += 1
                            
                            with signals_container:
                                with st.expander("⚡ SCALP SHORT: " + symbol + " (" + ex_name + ")", expanded=True):
                                    st.metric(label=symbol + " Entry", value="$" + entry_str, delta="-15M SCALP SHORT", delta_color="inverse")
                                    st.write("**SL:** $" + sl_str + " | **TP1:** $" + tp1_str + " \vert{} **TP2:** $" + tp2_str)

                    time.sleep(0.02)
                    
                except Exception:
                    continue
                
        status_text.success("✅ Scalp Scan Complete. Found " + str(total_signals_this_run) + " signals. Re-scanning in 3 minutes...")
        progress_bar.progress(100)
        time.sleep(180) # 3-minute fast scalping loop
        st.rerun()
