import time
import requests
import ccxt
import pandas as pd
import pandas_ta as ta
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# ==========================================
# 1. RENDER FREE TIER DUMMY WEB SERVER
# ==========================================
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot is Running 24/7 Free!")

def run_web_server():
    server = HTTPServer(('0.0.0.0', 10000), SimpleHTTPRequestHandler)
    server.serve_forever()

# Background mein web server start karein
threading.Thread(target=run_web_server, daemon=True).start()

# ==========================================
# 2. CONFIGURATION (APNI DETAILS YAHAN DAALEIN)
# ==========================================
TELEGRAM_TOKEN = "YAHAN_APNI_BOT_TOKEN_PASTE_KAREIN"
TELEGRAM_CHAT_ID = "YAHAN_APNI_CHAT_ID_PASTE_KAREIN"

# Multiple Exchanges setup
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
    """ Active USDT Spot pairs fetch karta hai """
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
    """ EMA + RSI + ICT FVG Multi-Confluence Strategy """
    bars = exchange.fetch_ohlcv(symbol, timeframe='1h', limit=100)
    df = pd.DataFrame(bars, columns=['time', 'open', 'high', 'low', 'close', 'volume'])
    
    # Technical Indicators
    df['EMA_20'] = ta.ema(df['close'], length=20)
    df['EMA_50'] = ta.ema(df['close'], length=50)
    df['RSI'] = ta.rsi(df['close'], length=14)
    
    curr = df.iloc[-1]
    prev = df.iloc[-2]
    prev2 = df.iloc[-3]
    
    # ICT Fair Value Gap (FVG) Detection
    bullish_fvg = curr['low'] > prev2['high']
    bearish_fvg = curr['high'] < prev2['low']
    
    price = curr['close']
    rsi = round(curr['RSI'], 1)
    
    # 🟢 LONG SIGNAL CONFLUENCE
    if (prev['EMA_20'] < prev['EMA_50'] and curr['EMA_20'] > curr['EMA_50']) and rsi > 45 and bullish_fvg:
        return f"🟢 *LONG SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: Bullish EMA Cross + ICT FVG Detected!"
        
    # 🔴 SHORT SIGNAL CONFLUENCE
    elif (prev['EMA_20'] > prev['EMA_50'] and curr['EMA_20'] < curr['EMA_50']) and rsi < 55 and bearish_fvg:
        return f"🔴 *SHORT SETUP FOUND!*\n\nCoin: *{symbol}*\nPrice: ${price}\nRSI: {rsi}\nReason: Bearish EMA Cross + ICT FVG Detected!"
        
    return None

def start_scanner():
    send_telegram("🚀 *Multi-Exchange Scanner Active! 24/7 Scanning Started...*")
    
    while True:
        for ex_name, exchange_obj in exchanges.items():
            print(f"Fetching coins from {ex_name}...")
            symbols = get_all_usdt_pairs(exchange_obj)
            
            # Rate limits se bachne ke liye top pairs scan honge
            for symbol in symbols[:400]: 
                try:
                    alert = scan_symbol(exchange_obj, symbol)
                    if alert:
                        full_msg = f"🏛 *Exchange:* {ex_name}\n" + alert
                        send_telegram(full_msg)
                        print(f"Alert Sent: {symbol} on {ex_name}")
                        
                    time.sleep(0.15) # Safe rate limit pause
                    
                except Exception:
                    continue
                    
        # Ek poora market scan complete karne ke baad 5 min delay
        time.sleep(300)

if __name__ == "__main__":
    start_scanner()
