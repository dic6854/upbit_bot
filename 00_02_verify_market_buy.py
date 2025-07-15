# 시장가 매수 확인

import pyupbit
import os
import time

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

def buy_market_coin(myTicker, myBuy_amount):
    print(f"{myTicker} 시장가 매수 진행... 매수할 금액:{myBuy_amount}")
    order = upbit.buy_market_order(ticker=myTicker, price=myBuy_amount)
    print("시장가 매수 완료:", order)

def auto_market_buy(myTicker, myTarget_price, myBuy_amount):
    while True:
        current_price = pyupbit.get_current_price(ticker=myTicker)
        print(f"[{myTicker}] 현재가격: {current_price:,.0f}원 - 목표가격: {myTarget_price:,.0f}원 - 간격: {(current_price-myTarget_price):,.0f}원")

        if current_price <= myTarget_price:
            buy_market_coin(myTicker=myTicker, myBuy_amount=myBuy_amount)
            print("목표가에 도달하여 매수 완료")
            break

        time.sleep(0.2)

if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

    # 목표가에 도달할 때까지 현재가를 조회해보다가 목표가에 도달하면 시장가로 매수
    auto_market_buy(myTicker="KRW-BTC", myTarget_price=165650000, myBuy_amount=10000)
