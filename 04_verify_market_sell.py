# 시장가 매도 확인

import pyupbit
import os
import time

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

def sell_market_coin(myTicker, myVolume):
    print(f"{myTicker} 시장가 매도 진행... 매도할 수량:{myVolume}")
    order = upbit.sell_market_order(ticker=myTicker, volume=myVolume)
    print("시장가 매도 완료:", order)

def auto_market_sell(myTicker, myTarget_price, myVolume):
    while True:
        current_price = pyupbit.get_current_price(ticker=myTicker)
        print(f"[{myTicker}] 현재가격: {current_price:,.0f}원 - 목표가격: {myTarget_price:,.0f}원 - 간격: {(myTarget_price-current_price):,.0f}원")

        if current_price >= myTarget_price:
            sell_market_coin(myTicker=myTicker, myVolume=myVolume)
            print("목표가에 도달하여 시장가 매도 완료")
            break

        time.sleep(0.2)

if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

    sell_volume = upbit.get_balance(ticker="KRW-BTC")
    print("매도 가능 전체 수량:", sell_volume)

    auto_market_sell(myTicker="KRW-BTC", myTarget_price=160000000, myVolume=sell_volume)