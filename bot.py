import MetaTrader5 as mt5
import time
import os
import requests

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SYMBOL = "BTCUSD"
LOT = 0.01

def connect():
    if not mt5.initialize():
        print("MT5 failed")
        quit()
    print("MT5 connected")

def get_closes():
    rates = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M1, 0, 50)
    if rates is None:
        return None
    closes = []
    for r in rates:
        closes.append(r.close)
    return closes

def ask_ai(closes):

    headers = {
        "Authorization": "Bearer " + OPENAI_API_KEY,
        "Content-Type": "application/json"
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [
            {
                "role": "user",
                "content": "BTC closes: " + str(closes[-20:]) + ". Reply BUY SELL or WAIT"
            }
        ]
    }

    r = requests.post(
        "https://api.openai.com/v1/chat/completions",
        headers=headers,
        json=data
    )

    result = r.json()

    signal = result["choices"][0]["message"]["content"]

    print("Signal:", signal)

    return signal

def trade(signal):

    positions = mt5.positions_get(symbol=SYMBOL)

    if positions:
        print("Position exists")
        return

    tick = mt5.symbol_info_tick(SYMBOL)

    if signal == "BUY":

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": LOT,
            "type": mt5.ORDER_TYPE_BUY,
            "price": tick.ask,
            "deviation": 20,
            "magic": 1,
            "comment": "AI BOT"
        }

        mt5.order_send(request)

    elif signal == "SELL":

        request = {
            "action": mt5.TRADE_ACTION_DEAL,
            "symbol": SYMBOL,
            "volume": LOT,
            "type": mt5.ORDER_TYPE_SELL,
            "price": tick.bid,
            "deviation": 20,
            "magic": 1,
            "comment": "AI BOT"
        }

        mt5.order_send(request)

connect()

while True:

    closes = get_closes()

    if closes:

        signal = ask_ai(closes)

        trade(signal)

    time.sleep(15)
