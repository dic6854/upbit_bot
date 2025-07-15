# 지정가 매수 확인

import pyupbit
import os
import time

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key

def buy_limit_coin(myTicker, myPrice, myVolume):
    print(f"{myTicker} 지정가 매수 진행... 매수할 가격:{myPrice}, 매수할 수량:{myVolume}")
    order = upbit.buy_limit_order(ticker=myTicker, price=myPrice, volume=myVolume)
    print("지정가 매수 완료:", order)

def auto_limit_buy(myTicker, myTarget_price, myVolume):
    while True:
        current_price = pyupbit.get_current_price(ticker=myTicker)
        print(f"[{myTicker}] 현재가격: {current_price:,.0f}원 - 목표가격: {myTarget_price:,.0f}원 - 간격: {(current_price-myTarget_price):,.0f}원")

        if current_price <= myTarget_price:
            buy_limit_coin(myTicker=myTicker, myPrice=myTarget_price, myVolume=myVolume)
            print("목표가에 도달하여 매수 완료")
            break

        time.sleep(0.2)

if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

    # 목표가에 도달할 때까지 현재가를 조회해보다가 목표가에 도달하면 0.0001개의 비트코인을 지정가(목표가)로 매수
    auto_limit_buy(myTicker="KRW-BTC", myTarget_price=159930000, myVolume=0.0001)
