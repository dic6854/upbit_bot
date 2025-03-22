import time
import pyupbit
import pandas as pd
from datetime import datetime
import os
import logging

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

ACCESS_KEY, SECRET_KEY = get_keys()

upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)

krw_balance = upbit.get_balance("KRW")
print(f"krw_balance = {krw_balance:,.0f}")

# ticker="KRW-BTC"
# order = upbit.buy_market_order(ticker, 5000)
# time.sleep(2)
# print(f"order = {order}")

# {'currency': 'BTC', 'balance': '0.0012345', 'locked': '0.0', 'avg_buy_price': '50000000.0', 'avg_buy_price_modified': False, 'unit_currency': 'KRW'}

coin_balance = upbit.get_balance("BTC")
print(f"coin_balance = {coin_balance:,.8f}")

balances = upbit.get_balances()
for balance in balances:
    if balance['currency'] == 'BTC':
        avg_buy_price = float(balance.get('avg_buy_price'))

print(f"avg_buy_price = {avg_buy_price:,.0f}")