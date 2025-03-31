import pyupbit
import os
import datetime
import time

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']
    return access_key, secret_key

access_key, secret_key = get_keys()
upbit = pyupbit.Upbit(access_key, secret_key)
ticker = "KRW-BTC"
budget_per_coin = 10000
orderbook = pyupbit.get_orderbook(ticker)['orderbook_units'][0]
sell_price = int(orderbook['ask_price'])
sell_unit = orderbook['ask_size']
print(f"sell_price = {sell_price}, sell_unit={sell_unit}")
unit = budget_per_coin / float(sell_price)
min_unit = min(unit, sell_unit)
sell_price = 100000000
result = upbit.buy_limit_order(ticker, sell_price, min_unit)

print(result)
