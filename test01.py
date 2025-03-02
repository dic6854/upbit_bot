import pyupbit
import os
import time
import threading

access_key = os.environ['UPBIT_ACCESS_KEY']
secret_key = os.environ['UPBIT_SECRET_KEY']

upbit = pyupbit.Upbit(access_key, secret_key)

buy_price = upbit.get_avg_buy_price(ticker="KRW-BTC")

print("매수 가격:", buy_price)



