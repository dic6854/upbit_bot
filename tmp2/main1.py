import pyupbit
import os
import time
import threading

access_key = os.environ['UPBIT_ACCESS_KEY']
secret_key = os.environ['UPBIT_SECRET_KEY']

upbit = pyupbit.Upbit(access_key, secret_key)

def buy_market_coin(ticker, price):
    print(f"{ticker} 매수 진행... 가격: {price}")
    order = upbit.buy_market_order(ticker, price)
    print("주문 완료:", order)

def auto_market_buy(ticker, target_price, buy_amount):
    while True:
        price = pyupbit.get_current_price(ticker)
        print(f"{ticker} 현재 가격: {price:,.0f}원")

        if price <= target_price:
            buy_market_coin(ticker, buy_amount)
            print("목표가에 도달하여 매수 완료")
            break

        time.sleep(1)

def sell_market_coin(ticker, volume):
    print(f"{ticker} 매도 진행... 수량: {volume}")
    order = upbit.sell_market_order(ticker, volume)
    print("주문 완료:", order)

def auto_market_sell(ticker, target_profit):
    while True:
        available_volume = upbit.get_balance(ticker="KRW-BTC")

        if available_volume != 0:
            buy_price = upbit.get_avg_buy_price(ticker)
            print(f"{ticker} 평균 매수 가격: {buy_price:,.0f}원, 매도 가능 수량: {available_volume}")

            price = pyupbit.get_current_price(ticker)
            profit = ((price - buy_price) / buy_price) * 100

            print(f"현재 가격: {price}원 | 수익률: {profit:.2f}%")

            if profit > target_profit:
                sell_market_coin(ticker, available_volume)
                print("목표 수익률에 도달하여 매도 완료")
                break

        time.sleep(1)

def stop_loss(ticker, stop_loss_percent):
    while True:
        available_volume = upbit.get_balance(ticker="KRW-BTC")

        if available_volume != 0:
            buy_price = upbit.get_avg_buy_price(ticker)
            stop_price = buy_price * (1 - (stop_loss_percent / 100))
            print(f"{ticker} 평균 매수 가격: {buy_price:,.0f}원, 매도 가능 수량: {available_volume}, 손절 가격: {stop_price}원")

            price = pyupbit.get_current_price(ticker)
            if price <= stop_price:
                sell_market_coin(ticker, available_volume)
                print("손절 가격에 도달하여 매도 완료")
                break
        
        time.sleep(1)

if __name__ == "__main__":
    ticker = "KRW-BTC"
    target_price = 60000000
    buy_amount = 10000
    target_profit = 2  # 2% 수익률
    stop_loss_percent = 3  # 3% 손절

    threading.Thread(target=auto_market_buy, args=(ticker, target_price, buy_amount)).start()
    threading.Thread(target=auto_market_sell, args=(ticker, target_profit)).start()
    threading.Thread(target=stop_loss, args=(ticker, stop_loss_percent)).start()