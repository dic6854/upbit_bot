import pyupbit
import os
import time
import threading

access_key = os.environ['UPBIT_ACCESS_KEY']
secret_key = os.environ['UPBIT_SECRET_KEY']

upbit = pyupbit.Upbit(access_key, secret_key)

available_volume = upbit.get_balance(ticker="KRW-BTC")
print("매도 가능 수량:", available_volume)

order = upbit.sell_market_order(ticker="KRW-BTC", volume=available_volume)
print("매도 주문 완료:", order)