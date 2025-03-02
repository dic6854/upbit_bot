import pyupbit
import os
import time
import threading
import logging

# 로깅 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

access_key = os.environ['UPBIT_ACCESS_KEY']
secret_key = os.environ['UPBIT_SECRET_KEY']
upbit = pyupbit.Upbit(access_key, secret_key)

# 상태 관리용 Lock과 플래그
lock = threading.Lock()
is_running = True

def buy_market_coin(ticker, price):
    with lock:
        logging.info(f"{ticker} 매수 진행... 가격: {price}")
        try:
            order = upbit.buy_market_order(ticker, price)
            logging.info(f"주문 완료: {order}")
            return order
        except Exception as e:
            logging.error(f"매수 실패: {e}")
            return None

def auto_market_buy(ticker, target_price, buy_amount):
    global is_running
    while is_running:
        try:
            price = pyupbit.get_current_price(ticker)
            logging.info(f"{ticker} 현재 가격: {price:,.0f}원")
            if price <= target_price:
                if buy_market_coin(ticker, buy_amount):
                    logging.info("목표가에 도달하여 매수 완료")
                    break
        except Exception as e:
            logging.error(f"매수 루프 오류: {e}")
        time.sleep(2)  # API 호출 간격 증가

def sell_market_coin(ticker, volume):
    with lock:
        logging.info(f"{ticker} 매도 진행... 수량: {volume}")
        try:
            order = upbit.sell_market_order(ticker, volume)
            logging.info(f"주문 완료: {order}")
            return order
        except Exception as e:
            logging.error(f"매도 실패: {e}")
            return None

def auto_trading(ticker, target_profit, stop_loss_percent):
    global is_running
    coin = ticker.split('-')[1]  # "KRW-BTC" -> "BTC"
    while is_running:
        try:
            available_volume = upbit.get_balance(coin)
            if available_volume > 0:
                buy_price = upbit.get_avg_buy_price(ticker)
                price = pyupbit.get_current_price(ticker)
                profit = ((price - buy_price) / buy_price) * 100
                stop_price = buy_price * (1 - (stop_loss_percent / 100))

                logging.info(f"{ticker} 현재 가격: {price:,.0f}원 | 수익률: {profit:.2f}% | 손절 가격: {stop_price:,.0f}원")

                if profit >= target_profit:
                    if sell_market_coin(ticker, available_volume):
                        logging.info("목표 수익률 도달, 매도 완료")
                        break
                elif price <= stop_price:
                    if sell_market_coin(ticker, available_volume):
                        logging.info("손절 가격 도달, 매도 완료")
                        break
        except Exception as e:
            logging.error(f"매도/손절 루프 오류: {e}")
        time.sleep(2)

if __name__ == "__main__":
    ticker = "KRW-BTC"
    target_price = 60000000
    buy_amount = 10000
    target_profit = 2  # 2% 수익률
    stop_loss_percent = 3  # 3% 손절

    # 매수와 매도/손절을 별도 스레드로 실행
    threading.Thread(target=auto_market_buy, args=(ticker, target_price, buy_amount)).start()
    threading.Thread(target=auto_trading, args=(ticker, target_profit, stop_loss_percent)).start()