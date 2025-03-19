import pyupbit
from get_keys import get_keys
import time

access_key, secret_key = get_keys()
upbit = pyupbit.Upbit(access_key, secret_key)

def sell_market_coin(ticker, volume):
    print(f"{ticker} 매도 진행... 수량: {volume}")
    order = upbit.sell_market_order(ticker, volume)
    print("주문 완료:", order)

def auto_sell(ticker, target_profit, volume):
    buy_price = upbit.get_avg_buy_price(ticker)
    print(f"{ticker} 평균 매수 가격: {buy_price:,.0f}원")

    while True:
        price = pyupbit.get_current_price(ticker)
        profit = ((price - buy_price) / buy_price) * 100

        print(f"현재 가격: {price}원 | 수익률: {profit:.2f}%")

        if profit > target_profit:
            sell_market_coin(ticker, volume)
            print("목표 수익률에 도달하여 매도 완료")
            break

        time.sleep(1)

def stop_loss(ticker, stop_loss_percent, volume):
    buy_price = upbit.get_avg_buy_price(ticker)
    stop_price = buy_price * (1 - (stop_loss_percent / 100))
    print(f"손절 가격: {stop_price}원")

    while True:
        price = pyupbit.get_current_price(ticker)
        if price <= stop_price:
            sell_market_coin(ticker, volume)
            print("손절 가격에 도달하여 매도 완료")
            break
        time.sleep(1)

if __name__ == "__main__":
    ticker="KRW-BTC"
    sell_volume = upbit.get_balance(ticker)
    print("매도 가능 전체 수량:", sell_volume)
    auto_sell(ticker, target_profit=0.5, volume=sell_volume)
