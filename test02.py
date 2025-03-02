import pyupbit
import os
import time
import threading

access_key = os.environ['UPBIT_ACCESS_KEY']
secret_key = os.environ['UPBIT_SECRET_KEY']

upbit = pyupbit.Upbit(access_key, secret_key)

buy_amount = 10000
order = upbit.buy_market_order(ticker="KRW-BTC", price=buy_amount)
print("매수수 주문 완료:", order)



