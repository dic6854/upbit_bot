# 시장가 매수 확인

import pyupbit
import os
import time

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

def auto_market_buy(ticker, price, amount):
    while True:
        current_price = pyupbit.get_current_price(ticker)
        print(f"[{ticker}] 현재가격: {current_price:,.0f}원 - 목표가격: {price:,.0f}원 - 간격: {(current_price-price):,.0f}원")

        if current_price <= price:      # 현재가(current_price)가 목표가(price)보다 아래에 있는 경우
            order = upbit.buy_market_order(ticker, price=amount)
            print("시장가 매수 완료:", order)
            break

        time.sleep(0.2)

if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

    order = upbit.buy_market_order(ticker="KRW-BTC", price=1000)
    print("시장가 매수 완료:", order)
    #현재가가 목표가(price)까지 내려오는 지를 조회해보다가 목표가에 도달하면 시장가로 특정 규모 만큼 (예: amount=1만원)을 매수한다.
    # auto_market_buy(ticker="KRW-BTC", price=140710000, amount=1000)
