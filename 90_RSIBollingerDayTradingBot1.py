import pyupbit
import time
import datetime
import pandas as pd
import numpy as np
import os
import logging

# 설정값
RSI_PERIOD = 14          # RSI 계산 기간
MIN_RSI = 45             # 최소 RSI 지표     (티커 선택시)
MIN_PRICE_CHANGE = 0     # 최소 가격 변화율   (티커 선택시)
MIN_VOLUME_CHANGE = 0    # 최소 거래량 변화율 (티커 선택시)

BB_PERIOD = 20           # 볼린저 밴드 기간
BB_K = 2                 # 볼린저 밴드 표준편차 배수
TARGET_PROFIT = 0.015    # 목표 수익률 1.5%
STOP_LOSS = -0.008       # 손절 -0.8%
VOLUME_THRESHOLD = 0.5   # 거래량 증가율 50%
INTERVAL = 5             # 체크 주기 (초)
INITIAL_BUDGET = 1000000 # 초기 자금 (디버그용)
DEBUG = True             # 디버그 모드

# 로깅 설정
logging.basicConfig(
    filename='trading_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

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
    def __init__(self, ticker="KRW-BTC"):
        """초기화"""
        self.ticker = ticker
        self.upbit = pyupbit.Upbit(ACCESS_KEY, SECRET_KEY)
        self.profit = 0  # 누적 이익금
        self.bought_price = 0
        self.holding = False
        self.last_volume = 0  # 전일 거래량

        if DEBUG:
            self.budget = INITIAL_BUDGET
        else:
            krw_balance = self.get_balance("KRW")
            if krw_balance < INITIAL_BUDGET:
                logging.warning(f"KRW잔고({krw_balance}원)가 초기 자본금({INITIAL_BUDGET}원)보다 적습니다. 초기 자본금을 KRW잔고({INITIAL_BUDGET}원)로 합니다.")
                print(f"경고: KRW 잔고({krw_balance}원)가 초기 자본금({INITIAL_BUDGET}원)보다 적습니다. 초기 자본금을 KRW잔고({INITIAL_BUDGET}원)로 합니다.")
                self.budget = krw_balance
            else:
                logging.warning(f"KRW잔고({krw_balance}원)가 초기 자본금({INITIAL_BUDGET}원)보다 많습니다. 초기 자본금을 ({INITIAL_BUDGET}원)로 합니다.")
                self.budget = INITIAL_BUDGET


    def calculate_rsi(self, df):
        """RSI 계산"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=RSI_PERIOD).mean()    # 최근 N(14)일 동안의 평균 상승폭
        loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()   # 최근 N(14)일 동안의 평균 하락폭
        rs = gain / loss
        rsi = 100 - (100 / (1 + rs))
        return rsi


    def calculate_bollinger_bands(self, df):
        """볼린저 밴드 계산"""
        sma = df['close'].rolling(window=BB_PERIOD).mean()   # 최근 N(20)일 동안의 평균값
        std = df['close'].rolling(window=BB_PERIOD).std()    # 최근 N(20)일 동안의 표준편차값
        upper_band = sma + (std * BB_K)   # 볼린저밴드 상한선 값
        lower_band = sma - (std * BB_K)   # 볼린저밴드 하한선 값
        return upper_band, sma, lower_band


    def get_data(self):
        """5분봉 데이터 가져오기"""
        df = pyupbit.get_ohlcv(self.ticker, interval="minute5", count=BB_PERIOD + RSI_PERIOD)
        if df is None or len(df) < BB_PERIOD + RSI_PERIOD:
            return None
        return df


    def initialize_day(self):
        """하루 초기화"""
        logging.info(f"{self.ticker} 데이트레이딩 초기화 중...")
        print(f"{self.ticker} 데이트레이딩 초기화 중...")

        df = pyupbit.get_ohlcv(self.ticker, interval="day", count=2)
        self.last_volume = df['volume'].iloc[-2]

        if DEBUG:
            lprofit = self.budget - INITIAL_BUDGET
            if lprofit > 0:
                self.profit += lprofit
                self.budget = INITIAL_BUDGET
                logging.info(f"금일 매매는 수익으로 끝났습니다. 수익금({lprofit:,.0f}원)을 총수익금({self.profit:,.0f}원)으로 적립합니다.")
                print(f"정보 - 금일 매매는 수익으로 끝났습니다. 수익금({lprofit:,.0f}원)을 총수익금({self.profit:,.0f}원)으로 적립합니다.")
            else:
                logging.info(f"금일 매매는 손실로 끝났습니다. 손실금({lprofit:,.0f}원)")
                print(f"정보 - 금일 매매는 손실로 끝났습니다. 손실금({lprofit:,.0f}원)")               
        else:
            krw_balance = self.get_balance("KRW")
            lprofit = krw_balance - INITIAL_BUDGET
            if lprofit > 0:
                logging.info(f"금일 매매는 수익으로 끝났습니다. 수익금({lprofit:,.0f}원)을 총수익금({self.profit:,.0f}원)으로 적립합니다. KRW잔고({krw_balance:,.0f}원)")
                print(f"정보 - 금일 매매는 수익으로 끝났습니다. 수익금({lprofit:,.0f}원)을 총수익금({self.profit:,.0f}원)으로 적립합니다. KRW잔고({krw_balance:,.0f}원)")
                self.profit += lprofit
                self.budget = INITIAL_BUDGET
            else:
                logging.warning(f"KRW잔고({krw_balance:,.0f}원)가 초기 자본금({INITIAL_BUDGET}원)보다 적습니다. 초기 자본금을 KRW잔고({krw_balance:,.0f}원)로 합니다.")
                print(f"경고: KRW잔고({krw_balance:,.0f}원)가 초기 자본금({INITIAL_BUDGET}원)보다 적습니다. 초기 자본금을 KRW잔고({krw_balance:,.0f}원)로 합니다.")
                self.budget = krw_balance

        self.holding = False


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
                if now.hour == 8 and now.minute >= 55 and now.minute <= 59:
                    if self.holding:
                        current_price = pyupbit.get_current_price(self.ticker)
                        self.sell(current_price)
                    self.initialize_day()
                    wait_time = (datetime.datetime(now.year, now.month, now.day, 9, 0) - now).total_seconds()
                    if wait_time > 0:
                        print(f"다음 장 시작(09:00)까지 {wait_time:.0f}초 대기...")
                        time.sleep(wait_time)
                    continue

                # 데이터 조회
                df = self.get_data()
                if df is None:
                    print("데이터 조회 실패, 2초 후 재시도...")
                    time.sleep(2)
                    continue

                current_price = pyupbit.get_current_price(self.ticker)
                if not current_price:
                    print("현재가 조회 실패, 2초 후 재시도...")
                    time.sleep(2)
                    continue

                # RSI 계산
                rsi = self.calculate_rsi(df).iloc[-1]
                # 볼린저 밴드 계산
                upper_band, sma, lower_band = self.calculate_bollinger_bands(df)
                # 거래량 파악
                df_vol = pyupbit.get_ohlcv(self.ticker, interval="day", count=2)
                previous_volume = df_vol['volume'].iloc[-2]
                current_volume = df_vol['volume'].iloc[-1]

                # 매수 조건
                # RSI < 30 (과매도), 가격이 하단 밴드 아래, 거래량 증가
                if (not self.holding and 
                    rsi < 30 and 
                    current_price < lower_band.iloc[-1] and 
                    current_volume > previous_volume * (1 + VOLUME_THRESHOLD)):
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

# 상위 5개 상승 추세 코인 선정 함수
def select_top_rising_coins():
    tickers = pyupbit.get_tickers(fiat="KRW")
    total_count = len(tickers)
    print(f"총 {total_count}개 코인 조회됨")

    # 결과 저장용 리스트
    rising_coins = []
    current_count = 1
    for ticker in tickers:
        try:
            # 24시간 가격 상승률 계산 (일봉 데이터)
            df_day = pyupbit.get_ohlcv(ticker, interval="day", count=(RSI_PERIOD+1))
            if df_day is None or len(df_day) < (RSI_PERIOD+1):
                print(f"[{current_count} / {total_count}] - ticker: {ticker} was skipped")
                current_count += 1
                continue

            time.sleep(0.12)

            current_price = pyupbit.get_current_price(ticker)
            prev_close = df_day['close'].iloc[-2]
            price_change = (current_price - prev_close) / prev_close * 100

            # 거래량 증가율 계산
            current_volume = df_day['volume'].iloc[-1]
            prev_volume = df_day['volume'].iloc[-2]
            volume_change = (current_volume - prev_volume) / prev_volume if prev_volume > 0 else 0

            # MA5 계산
            ma5 = df_day['close'].rolling(window=5).mean().iloc[-1]

            # RSI 계산 (5분봉 기준)
            delta = df_day['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=RSI_PERIOD).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
            rs = gain / loss if loss.iloc[-2] != 0 else float('inf')
            rsi = 100 - (100 / (1 + rs.iloc[-2]))

            # 조건: 가격 상승률 > 0, 거래량 증가, 현재가 >= MA5, RSI >= 50
            if (price_change > MIN_PRICE_CHANGE and  volume_change > MIN_VOLUME_CHANGE and rsi >= MIN_RSI and current_price >= ma5):
                rising_coins.append({'ticker': ticker, 'price_change': price_change, 'volume_change': volume_change, 'rsi': rsi, 'ma5': ma5, 'current_price': current_price})

            print(f"[{current_count} / {total_count}] - ticker: {ticker}, price_change: {price_change:.2f}, volume_change: {volume_change:.2f}, rsi: {rsi:.2f}, ma5: {ma5:.2f}, current_price: {current_price:.2f}")

        except Exception as e:
            print(f"{ticker} 처리 중 오류: {e}")
            continue

    # 가격 상승률 기준으로 상위 5개 정렬
    rising_coins = sorted(rising_coins, key=lambda x: x['price_change'], reverse=True)[:5]
    
    return rising_coins

if __name__ == "__main__":
    top_coins = select_top_rising_coins()
    coin = top_coins[0]
    bot = RSIBollingerDayTradingBot(ticker=coin['ticker'], debug=DEBUG)
    bot.run()
    # for coin in top_coins:
    #     bot = RSIBollingerDayTradingBot(ticker=coin['ticker'], debug=DEBUG)
    #     bot.run()