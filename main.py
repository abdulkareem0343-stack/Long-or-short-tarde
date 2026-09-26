import time
import requests
import ccxt
import pandas as pd
import pandas_ta as ta

# --- CONFIGURATION ---
TELEGRAM_TOKEN = "YAHAN_APNI_BOT_TOKEN_PASTE_KAREIN"
TELEGRAM_CHAT_ID = "YAHAN_APNI_CHAT_ID_PASTE_KAREIN"

# Multiple Exchanges Setup
exchanges = {
    'Binance': ccxt.binance({'enableRateLimit': True}),
    'Bybit': ccxt.bybit({'enableRateLimit': True})
}

def send_telegram(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "parse_mode": "Markdown"}
    try:
        requests.post(url, data=payload)
    except Exception as e:
        print("Telegram Error:", e)

def get_all_usdt_pairs(exchange):
    """ Exchange se saare USDT Spot / Futures pairs auto-fetch karta hai """
    try:
        markets = exchange.load_markets()
        usdt_pairs = [
            symbol for symbol in markets.keys() 
            if symbol.endswith('/USDT') and markets[symbol]['active']
        ]
        return usdt_pairs
    except Exception as e:
        print(f"Error fetching markets: {e}")
        return []

def scan_symbol(exchange, symbol):
    """ Single Coin Multi-Confluence Analysis """
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    
    # Indicators (EMA 20, 50 + RSI 14)
    df['EMA_20'] = ta.ema(df['close'], length=20)
    df['EMA_50'] = ta.ema(df['close'], length=50)
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    
    # ICT Fair Value Gap (FVG) Check
    bullish_fvg = curr['low'] > prev2['high']
    bearish_fvg = curr['high'] < prev2['low']
    
    price = curr['close']
    rsi = round(curr['RSI'], 1)
    
    # LONG SIGNAL
    if (prev['EMA_20'] < prev['EMA_50'] and curr['EMA_20'] > curr['EMA_50']) and rsi > 45 and bullish_fvg:
        return f"🟢 *LONG SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: EMA Crossover + Bullish FVG Detected!"
        
    # SHORT SIGNAL
    elif (prev['EMA_20'] > prev['EMA_50'] and curr['EMA_20'] < curr['EMA_50']) and rsi < 55 and bearish_fvg:
        return f"🔴 *SHORT SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: Bearish EMA Cross + FVG Detected!"
        
    return None

def start_scanner():
    send_telegram("🚀 *Multi-Exchange Scanner Active! Fetching All Coins...*")
    
    while True:
        for ex_name, exchange_obj in exchanges.items():
            print(f"Fetching coin list for {ex_name}...")
            symbols = get_all_usdt_pairs(exchange_obj)
            print(f"Total USDT Pairs Found on {ex_name}: {len(symbols)}")
            
            # Pehle 300-500 high volume/active coins scan hongy
            for symbol in symbols[:500]: 
                try:
                    alert = scan_symbol(exchange_obj, symbol)
                    if alert:
                        full_msg = f"🏛 *Exchange:* {ex_name}\n" + alert
                        send_telegram(full_msg)
                        print(f"Alert Sent for {symbol} on {ex_name}")
                        
                    # Rate Limit Se Bachne Ke Liye Small Delay (0.2s)
                    time.sleep(0.2)
                    
                except Exception as e:
                    # Agar coin data fetch na ho ya limit hit ho toh skip kare
                    continue
                    
        # Ek round khatam hone ke baad 5 minute pause
        time.sleep(300)

if __name__ == "__main__":
    start_scanner()
