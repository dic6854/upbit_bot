import pyupbit
import time
import datetime
import pandas as pd
import numpy as np
import os

# 설정값
RSI_PERIOD = 14          # RSI 계산 기간
BB_PERIOD = 20           # 볼린저 밴드 기간
BB_K = 2                # 볼린저 밴드 표준편차 배수
TARGET_PROFIT = 0.015    # 목표 수익률 1.5%
STOP_LOSS = -0.008       # 손절 -0.8%
VOLUME_THRESHOLD = 0.5   # 거래량 증가율 50%
INTERVAL = 5             # 체크 주기 (초)
INITIAL_BUDGET = 1000000 # 초기 자금 (디버그용)
DEBUG = True             # 디버그 모드

# API 키 설정
def get_keys():
    try:
        access_key = os.environ['UPBIT_ACCESS_KEY']
        secret_key = os.environ['UPBIT_SECRET_KEY']
        return access_key, secret_key
    except KeyError:
        print("오류: UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY 환경 변수가 설정되지 않았습니다.")
        exit(1)

ACCESS_KEY, SECRET_KEY = get_keys()

class RSIBollingerDayTradingBot:
    def __init__(self, ticker="KRW-BTC", budget=INITIAL_BUDGET, debug=DEBUG):
        """초기화"""
        self.ticker = ticker
        self.debug = debug
        self.upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY) if not debug else None
        self.budget = budget if debug else self.upbit.get_balance("KRW")
        self.bought_price = 0
        self.holding = False
        self.last_volume = 0  # 전일 거래량

    def calculate_rsi(self, df):
        """RSI 계산"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

    def calculate_bollinger_bands(self, df):
        """볼린저 밴드 계산"""
        sma = df['close'].rolling(window=BB_PERIOD).mean()
        std = df['close'].rolling(window=BB_PERIOD).std()
        upper_band = sma + (std * BB_K)
        lower_band = sma - (std * BB_K)
        return upper_band, sma, lower_band

    def get_data(self):
        """5분봉 데이터 가져오기"""
        df = pyupbit.get_ohlcv(self.ticker, interval="minute5", count=BB_PERIOD + RSI_PERIOD)
        if df is None or len(df) < BB_PERIOD + RSI_PERIOD:
            return None
        return df

    def initialize_day(self):
        """하루 초기화"""
        print(f"{self.ticker} 데이트레이딩 초기화 중...")
        df = self.get_data()
        if df is not None:
            self.last_volume = df['volume'].iloc[-2]  # 전일 마지막 거래량
            self.holding = False
            self.bought_price = 0
            print("초기화 완료")
        else:
            print("초기화 실패, 데이터를 확인해주세요.")

    def buy(self, current_price):
        """매수 실행"""
        if self.debug:
            print(f"[디버그] 매수: {self.ticker}, 가격: {current_price:,.0f}원")
            self.bought_price = current_price
            self.budget -= self.budget
        else:
            result = self.upbit.buy_market_order(self.ticker, self.budget)
            if result:
                print(f"매수 완료: {self.ticker}, 금액: {self.budget:,.0f}원")
                self.bought_price = current_price
                self.budget = 0
        self.holding = True

    def sell(self, current_price):
        """매도 실행"""
        if self.debug:
            profit = (current_price - self.bought_price) / self.bought_price
            self.budget = INITIAL_BUDGET * (1 + profit)
            print(f"[디버그] 매도: {self.ticker}, 가격: {current_price:,.0f}원, 수익률: {profit:.2%}")
        else:
            coin = self.ticker.split('-')[1]
            balance = self.upbit.get_balance(coin)
            if balance > 0:
                result = self.upbit.sell_market_order(self.ticker, balance)
                profit = (current_price - self.bought_price) / self.bought_price
                print(f"매도 완료: {self.ticker}, 수량: {balance:.8f}, 수익률: {profit:.2%}")
                self.budget = self.upbit.get_balance("KRW")
        self.holding = False

    def run(self):
        """메인 루프"""
        print(f"{self.ticker} RSI-볼린저 데이트레이딩 봇 시작...")
        while True:
            try:
                now = datetime.datetime.now()

                # 장 마감 (08:50~09:00) 처리
                if now.hour == 8 and now.minute >= 50:
                    if self.holding:
                        current_price = pyupbit.get_current_price(self.ticker)
                        self.sell(current_price)
                    self.initialize_day()
                    wait_time = (datetime.datetime(now.year, now.month, now.day, 9, 0) - now).total_seconds()
                    if wait_time > 0:
                        print(f"다음 장 시작까지 {wait_time:.0f}초 대기...")
                        time.sleep(wait_time)
                    continue

                # 장 시작 초기화 (09:00~09:10)
                if now.hour == 9 and now.minute < 10:
                    self.initialize_day()

                # 데이터 조회
                df = self.get_data()
                if df is None:
                    print("데이터 조회 실패, 10초 후 재시도...")
                    time.sleep(10)
                    continue

                current_price = pyupbit.get_current_price(self.ticker)
                if not current_price:
                    print("현재가 조회 실패, 5초 후 재시도...")
                    time.sleep(5)
                    continue

                # RSI 계산
                rsi = self.calculate_rsi(df).iloc[-1]
                # 볼린저 밴드 계산
                upper_band, sma, lower_band = self.calculate_bollinger_bands(df)
                current_volume = df['volume'].iloc[-1]

                # 매수 조건
                # RSI < 30 (과매도), 가격이 하단 밴드 아래, 거래량 증가
                if (not self.holding and 
                    rsi < 30 and 
                    current_price < lower_band.iloc[-1] and 
                    current_volume > self.last_volume * (1 + VOLUME_THRESHOLD)):
                    self.buy(current_price)

                # 매도 조건
                # RSI > 70 (과매수), 가격이 상단 밴드 위, 또는 수익/손실 기준
                if self.holding:
                    profit = (current_price - self.bought_price) / self.bought_price
                    if (rsi > 70 and current_price > upper_band.iloc[-1]) or profit >= TARGET_PROFIT or profit <= STOP_LOSS:
                        self.sell(current_price)

                # 상태 출력 (30초마다)
                if now.second % 30 == 0:
                    print(f"현재가: {current_price:,.0f}원, RSI: {rsi:.2f}, "
                          f"BB 상단: {upper_band.iloc[-1]:,.0f}원, 하단: {lower_band.iloc[-1]:,.0f}원, "
                          f"보유: {self.holding}, 잔고: {self.budget:,.0f}원")

                self.last_volume = current_volume  # 거래량 업데이트
                time.sleep(INTERVAL)

            except KeyboardInterrupt:
                print("프로그램 종료 요청...")
                if self.holding:
                    self.sell(pyupbit.get_current_price(self.ticker))
                break
            except Exception as e:
                print(f"오류 발생: {e}")
                time.sleep(5)

if __name__ == "__main__":
    bot = RSIBollingerDayTradingBot(ticker="KRW-BTC", debug=DEBUG)
    bot.run()