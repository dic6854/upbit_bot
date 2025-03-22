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

coin_balance = upbit.get_balance("BTC")
print(f"coin_balance = {coin_balance:,.8f}")

ticker="KRW-BTC"
order = upbit.sell_market_order(ticker, coin_balance)
time.sleep(1)
print(order)

# if order:
#     order_uuid = order['uuid']
#     print(f"시장가 매도 주문 ID: {order_uuid}")

#     time.sleep(1) # 필요에 따라 대기

#     order_info = upbit.get_order(order_uuid)
#     if order_info and order_info.get('state') == 'done':
#         trades = order_info.get('trades')
#         if trades:
#             total_price = 0
#             total_volume = 0
#             for trade in trades:
#                 trade_price = float(trade['price'])
#                 trade_volume = float(trade['volume'])
#                 total_price += trade_price * trade_volume
#                 total_volume += trade_volume
#             if total_volume > 0:
#                 average_sell_price = total_price / total_volume
#                 print(f"이번 매도 거래 평균가 (체결 내역 기반): {average_sell_price:,.2f} 원")
#             else:
#                 print("체결된 거래 내역이 없습니다.")
#         else:
#             print("체결 내역 정보를 찾을 수 없습니다.")
#     else:
#         print("주문 정보를 가져오거나 아직 체결되지 않았습니다.")
# else:
#     print("시장가 매도 주문 실패.")


# print(f"average_sell_price = {average_sell_price:,.2f}")