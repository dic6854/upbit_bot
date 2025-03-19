import pyupbit
from get_keys import get_keys
import time

access_key, secret_key = get_keys()
upbit = pyupbit.Upbit(access_key, secret_key)

def sell_limit_coin(ticker, price, volume):
    print(f"{ticker} 매도 진행... 가격: {price}")
    order = upbit.buy_limit_order(ticker, price, volume)
    print("주문 완료:", order)

def auto_limit_sell(ticker, target_price, volume):
    while True:
        price = pyupbit.get_current_price(ticker)
        print(f"{ticker} 현재 가격: {price:,.0f}원")

        if price > target_price:
            sell_limit_coin(ticker, price, volume)
            print("목표가에 도달하여 매도 완료")
            break

        time.sleep(1)

if __name__ == "__main__":
    auto_limit_sell(ticker="KRW-BTC", target_price=125731000, volume=0.0001)
