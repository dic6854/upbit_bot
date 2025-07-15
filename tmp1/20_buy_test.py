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

def get_buy_price(ticker):
    balances = upbit.get_balances()
    coin_avg_buy_price = False
    for balance in balances:
        if balance['currency'] == ticker:
            coin_avg_buy_price = float(balance.get('avg_buy_price'))
    
    return coin_avg_buy_price

ACCESS_KEY, SECRET_KEY = get_keys()

upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)

balances = upbit.get_balances()
print(balances)


krw_balance = upbit.get_balance("KRW")
print(f"krw_balance = {krw_balance:,.0f}")

# ticker="KRW-BTC"
# order = upbit.buy_market_order(ticker, 10000)
# time.sleep(2)
# print(f"order = {order}")

# {'currency': 'BTC', 'balance': '0.0012345', 'locked': '0.0', 'avg_buy_price': '50000000.0', 'avg_buy_price_modified': False, 'unit_currency': 'KRW'}

avg_buy_price = get_buy_price('BTC')
if avg_buy_price:
    print(f"avg_buy_price = {avg_buy_price:,.0f}")