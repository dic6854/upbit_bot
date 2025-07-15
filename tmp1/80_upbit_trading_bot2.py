import pyupbit
import threading
import queue
import json
import time
import datetime
import pandas as pd
import numpy as np
import os
import logging
from select_rising_coins import select_top_rising_coins  # 이전 답변의 코인 선정 함수 가정

# 설정값
RSI_PERIOD = 14          # RSI 계산 기간
BB_PERIOD = 20           # 볼린저 밴드 기간
BB_K = 2                 # 볼린저 밴드 표준편차 배수
TARGET_PROFIT = 0.015    # 목표 수익률 1.5%
STOP_LOSS = -0.008       # 손절 -0.8%
VOLUME_THRESHOLD = 0.5   # 거래량 증가율 50%
INTERVAL = 5             # 체크 주기 (초)
INITIAL_BUDGET = 1000000 # 초기 자금 (디버그용)
DEBUG = True             # 디버그 모드
MAX_QUEUE_SIZE = 100     # 큐 최대 크기
lock = threading.Lock()  # 잔고 동기화용 Lock

# 로깅 설정
logging.basicConfig(
    filename='trading_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# API 키 설정
def get_keys():
    try:
        access_key = os.environ['UPBIT_ACCESS_KEY']
        secret_key = os.environ['UPBIT_SECRET_KEY']
        return access_key, secret_key
    except KeyError:
        logging.error("환경 변수 UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY가 설정되지 않았습니다.")
        print("오류: 환경 변수 UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY가 설정되지 않았습니다.")
        exit(1)

ACCESS_KEY, SECRET_KEY = get_keys()

class RSIBollingerDayTradingBot:
    def __init__(self, ticker, budget, price_queue, debug=DEBUG):
        """초기화"""
        self.ticker = ticker
        self.debug = debug
        self.upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY) if not debug else None
        self.budget = budget if debug else self.upbit.get_balance("KRW") / 5
        self.price_queue = price_queue
        self.bought_price = 0
        self.holding = False
        self.last_volume = 0
        self.df = pd.DataFrame(columns=['open', 'high', 'low', 'close', 'volume'])
        self.last_update = datetime.datetime.now()
        self.trade_log = []  # 거래 내역 저장

    def calculate_rsi(self):
        """RSI 계산 (최적화: 필요한 데이터만 사용)"""
        if len(self.df) < RSI_PERIOD + 1:
            return None
        delta = self.df['close'].iloc[-RSI_PERIOD-1:].diff()
        gain = delta.where(delta > 0, 0).mean()
        loss = (-delta.where(delta < 0, 0)).mean()
        rs = gain / loss if loss != 0 else float('inf')
        return 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self):
        """볼린저 밴드 계산 (최적화: 필요한 데이터만 사용)"""
        if len(self.df) < BB_PERIOD:
            return None, None, None
        close = self.df['close'].iloc[-BB_PERIOD:]
        sma = close.mean()
        std = close.std()
        upper_band = sma + (std * BB_K)
        lower_band = sma - (std * BB_K)
        return upper_band, sma, lower_band

    def initialize_day(self):
        """하루 초기화"""
        logging.info(f"{self.ticker} 데이트레이딩 초기화 중...")
        df = pyupbit.get_ohlcv(self.ticker, interval="minute5", count=BB_PERIOD + RSI_PERIOD)
        if df is not None:
            self.df = df
            self.last_volume = df['volume'].iloc[-2]
            self.holding = False
            self.bought_price = 0
            logging.info(f"{self.ticker} 초기화 완료")
        else:
            logging.warning(f"{self.ticker} 초기화 실패")

    def buy(self, current_price):
        """매수 실행"""
        with lock:
            if self.debug:
                logging.info(f"[디버그] 매수: {self.ticker}, 가격: {current_price:,.0f}원")
                self.bought_price = current_price
                self.budget -= self.budget
            else:
                result = self.upbit.buy_market_order(self.ticker, self.budget)
                if result:
                    logging.info(f"매수 완료: {self.ticker}, 금액: {self.budget:,.0f}원")
                    self.bought_price = current_price
                    self.budget = 0
            self.holding = True
            self.trade_log.append({'type': 'buy', 'price': current_price, 'time': datetime.datetime.now()})

    def sell(self, current_price):
        """매도 실행"""
        with lock:
            if self.debug:
                profit = (current_price - self.bought_price) / self.bought_price
                self.budget = INITIAL_BUDGET / 5 * (1 + profit)
                logging.info(f"[디버그] 매도: {self.ticker}, 가격: {current_price:,.0f}원, 수익률: {profit:.2%}")
            else:
                coin = self.ticker.split('-')[1]
                balance = self.upbit.get_balance(coin)
                if balance > 0:
                    result = self.upbit.sell_market_order(self.ticker, balance)
                    profit = (current_price - self.bought_price) / self.bought_price
                    logging.info(f"매도 완료: {self.ticker}, 수량: {balance:.8f}, 수익률: {profit:.2%}")
                    remaining_bots = 5 - sum(1 for b in bots if b.holding)
                    self.budget = self.upbit.get_balance("KRW") / (remaining_bots if remaining_bots > 0 else 1)
            self.holding = False
            self.trade_log.append({'type': 'sell', 'price': current_price, 'time': datetime.datetime.now(), 'profit': profit})

    def update_volume(self):
        """거래량 REST API로 주기적 업데이트"""
        df_5min = pyupbit.get_ohlcv(self.ticker, interval="minute5", count=2)
        if df_5min is not None and len(df_5min) >= 2:
            self.last_volume = df_5min['volume'].iloc[-1]

    def backtest(self, start_date, end_date):
        """백테스팅"""
        logging.info(f"{self.ticker} 백테스팅 시작: {start_date} ~ {end_date}")
        df = pyupbit.get_ohlcv(self.ticker, interval="minute5", to=end_date, count=1000)
        if df is None or len(df) < BB_PERIOD + RSI_PERIOD:
            logging.warning(f"{self.ticker} 백테스팅 데이터 부족")
            return None

        balance = INITIAL_BUDGET / 5
        holding = False
        bought_price = 0
        trades = []

        for i in range(BB_PERIOD + RSI_PERIOD, len(df)):
            close = df['close'].iloc[:i+1]
            rsi = self.calculate_rsi_from_series(close.iloc[-RSI_PERIOD-1:])
            upper_band, sma, lower_band = self.calculate_bollinger_bands_from_series(close.iloc[-BB_PERIOD:])
            current_price = close.iloc[-1]
            volume = df['volume'].iloc[i]

            if not holding and rsi < 30 and current_price < lower_band and volume > df['volume'].iloc[i-1] * (1 + VOLUME_THRESHOLD):
                holding = True
                bought_price = current_price
                balance -= balance
                trades.append({'type': 'buy', 'price': current_price, 'time': df.index[i]})

            elif holding:
                profit = (current_price - bought_price) / bought_price
                if (rsi > 70 and current_price > upper_band) or profit >= TARGET_PROFIT or profit <= STOP_LOSS:
                    holding = False
                    balance = (INITIAL_BUDGET / 5) * (1 + profit)
                    trades.append({'type': 'sell', 'price': current_price, 'time': df.index[i], 'profit': profit})

        final_balance = balance + (bought_price * (INITIAL_BUDGET / 5 / bought_price) if holding else 0)
        roi = (final_balance - (INITIAL_BUDGET / 5)) / (INITIAL_BUDGET / 5) * 100
        logging.info(f"{self.ticker} 백테스팅 결과: 최종 잔고 {final_balance:,.0f}원, ROI {roi:.2f}%")
        return {'roi': roi, 'trades': trades}

    def calculate_rsi_from_series(self, series):
        """백테스팅용 RSI 계산"""
        delta = series.diff()
        gain = delta.where(delta > 0, 0).mean()
        loss = (-delta.where(delta < 0, 0)).mean()
        rs = gain / loss if loss != 0 else float('inf')
        return 100 - (100 / (1 + rs))

    def calculate_bollinger_bands_from_series(self, series):
        """백테스팅용 볼린저 밴드 계산"""
        sma = series.mean()
        std = series.std()
        upper_band = sma + (std * BB_K)
        lower_band = sma - (std * BB_K)
        return upper_band, sma, lower_band

    def run(self):
        """메인 루프"""
        logging.info(f"{self.ticker} RSI-볼린저 데이트레이딩 봇 시작...")
        while True:
            try:
                now = datetime.datetime.now()

                # 장 마감 (08:50~09:00)
                if now.hour == 8 and now.minute >= 50:
                    if self.holding:
                        current_price = self.price_queue.get() if not self.price_queue.empty() else pyupbit.get_current_price(self.ticker)
                        self.sell(current_price)
                    self.initialize_day()
                    wait_time = (datetime.datetime(now.year, now.month, now.day, 9, 0) - now).total_seconds()
                    if wait_time > 0:
                        logging.info(f"{self.ticker} 다음 장 시작까지 {wait_time:.0f}초 대기...")
                        time.sleep(wait_time)
                    continue

                # 장 시작 초기화 (09:00~09:10)
                if now.hour == 9 and now.minute < 10:
                    self.initialize_day()

                # WebSocket에서 가격 데이터 가져오기
                if not self.price_queue.empty():
                    current_price = self.price_queue.get()

                    # 큐 크기 관리
                    while self.price_queue.qsize() > MAX_QUEUE_SIZE:
                        self.price_queue.get()

                    # 실시간 데이터 업데이트
                    new_data = pd.DataFrame({
                        'open': [current_price],
                        'high': [current_price],
                        'low': [current_price],
                        'close': [current_price],
                        'volume': [self.last_volume]
                    }, index=[datetime.datetime.now()])
                    self.df = pd.concat([self.df[-BB_PERIOD-RSI_PERIOD:], new_data])

                    # RSI와 볼린저 밴드 계산
                    rsi = self.calculate_rsi()
                    upper_band, sma, lower_band = self.calculate_bollinger_bands()
                    if rsi is None or upper_band is None:
                        continue

                    # 거래량 주기적 업데이트 (30초마다)
                    if (now - self.last_update).seconds >= 30:
                        self.update_volume()
                        self.last_update = now

                    # 매수 조건
                    if (not self.holding and 
                        rsi < 30 and 
                        current_price < lower_band and 
                        self.last_volume > self.last_volume * (1 + VOLUME_THRESHOLD)):
                        self.buy(current_price)

                    # 매도 조건
                    if self.holding:
                        profit = (current_price - self.bought_price) / self.bought_price
                        if (rsi > 70 and current_price > upper_band) or \
                           profit >= TARGET_PROFIT or profit <= STOP_LOSS:
                            self.sell(current_price)

                    # 상태 출력 (30초마다)
                    if now.second % 30 == 0:
                        logging.info(f"{self.ticker} 현재가: {current_price:,.0f}원, RSI: {rsi:.2f}, "
                                     f"BB 상단: {upper_band:,.0f}원, 하단: {lower_band:,.0f}원, "
                                     f"보유: {self.holding}, 잔고: {self.budget:,.0f}원")

                time.sleep(INTERVAL)

            except KeyboardInterrupt:
                logging.info(f"{self.ticker} 프로그램 종료 요청...")
                if self.holding:
                    self.sell(self.price_queue.get() if not self.price_queue.empty() else pyupbit.get_current_price(self.ticker))
                break
            except Exception as e:
                logging.error(f"{self.ticker} 오류 발생: {e}")
                time.sleep(5)

def websocket_listener(tickers, price_queues):
    """WebSocket으로 실시간 가격 데이터 수신"""
    def on_message(ws, message):
        try:
            data = json.loads(message.decode('utf-8'))
            ticker = data['code']
            price = data['trade_price']
            if ticker in price_queues:
                price_queues[ticker].put(price)
        except Exception as e:
            logging.error(f"WebSocket 메시지 처리 오류: {e}")

    while True:
        try:
            ws_client = pyupbit.WebSocketClient("ticker", tickers)
            ws_client.on_message = on_message
            logging.info("WebSocket 연결 성공")
            ws_client.run_forever()
        except Exception as e:
            logging.error(f"WebSocket 오류: {e}, 5초 후 재연결...")
            time.sleep(5)

# 전역 변수로 bots 리스트 정의
bots = []

if __name__ == "__main__":
    # 상위 5개 상승 추세 코인 선정
    top_coins = select_top_rising_coins()
    if not top_coins:
        logging.error("코인 선정 실패, 프로그램 종료.")
        exit(1)

    logging.info("\n선정된 상승 추세 코인:")
    for coin in top_coins:
        logging.info(f"{coin['ticker']}: 상승률 {coin['price_change']:.2f}%")

    # 각 코인당 예산 분배
    total_budget = INITIAL_BUDGET if DEBUG else pyupbit.Upbit(ACCESS_KEY, SECRET_KEY).get_balance("KRW")
    budget_per_coin = total_budget / len(top_coins)
    logging.info(f"코인당 예산: {budget_per_coin:,.0f}원")

    # 백테스팅 (선택적 실행)
    bots.clear()  # bots 리스트 초기화
    for coin in top_coins:
        bot = RSIBollingerDayTradingBot(ticker=coin['ticker'], budget=budget_per_coin, price_queue=queue.Queue())
        backtest_result = bot.backtest("2025-03-01", "2025-03-30")
        if backtest_result:
            logging.info(f"{coin['ticker']} 백테스팅 ROI: {backtest_result['roi']:.2f}%")
        bots.append(bot)

    # 가격 데이터를 저장할 큐
    price_queues = {coin['ticker']: bot.price_queue for coin, bot in zip(top_coins, bots)}

    # WebSocket 스레드 시작
    tickers = [coin['ticker'] for coin in top_coins]
    ws_thread = threading.Thread(target=websocket_listener, args=(tickers, price_queues))
    ws_thread.daemon = True
    ws_thread.start()

    # 각 코인에 대해 봇 스레드 생성 및 실행
    threads = []
    for bot in bots:
        thread = threading.Thread(target=bot.run)
        threads.append(thread)
        thread.start()

    # 모든 스레드가 종료될 때까지 대기
    for thread in threads:
        thread.join()

    logging.info("모든 봇 실행 완료.")