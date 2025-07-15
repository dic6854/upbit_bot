import pyupbit
import time
import datetime
import numpy as np
import pandas as pd
import os
# import logging

# 설정값
INTERVAL = 1                     # 매수 시도 interval (1초 기본)
DEBUG = True                     # True: 매매 API 호출 안됨, False: 실제로 매매 API 호출
COIN_NUMS = 5                    # 분산 투자 코인 개수 (자산/COIN_NUMS를 각 코인에 투자)
DUAL_NOISE_LIMIT = 0.6           # 듀얼 노이즈 한계값 (이 값 이하인 코인만 선택)
LARRY_K = 0.4                    # 변동성 돌파 전략의 K값
TRAILING_STOP_MIN_PROFIT = 0.3   # 최소 30% 이상 수익이 발생한 경우에 Trailing Stop 동작
TRAILING_STOP_GAP = 0.03         # 최고점 대비 53하락시 매도

def get_keys():
    """
    환경 변수에서 API 키 가져오기
    """
    try:
        access_key = os.environ['UPBIT_ACCESS_KEY']
        secret_key = os.environ['UPBIT_SECRET_KEY']
        return access_key, secret_key
    except KeyError:
        print("오류: 환경 변수 UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY가 설정되지 않았습니다.")
        return None, None

ACCESS_KEY, SECRET_KEY = get_keys()

class UpbitTradingBot:
    def __init__(self, access_key=None, secret_key=None):
        """
        업비트 트레이딩 봇 초기화
        Args:
            access_key (str): 업비트 API 접속 키
            secret_key (str): 업비트 API 시크릿 키
            debug (bool): 디버그 모드 여부
        """
        self.upbit = pyupbit.Upbit(access_key, secret_key)
            
        self.portfolio = []          # 선택된 코인 포트폴리오
        self.targets = {}            # 각 코인별 목표가
        self.ma5s = {}               # 5일 이동평균
        self.high_prices = {}        # 당일 고가
        self.bought_prices = {}      # 매수 가격
        self.max_prices = {}         # 매수 후 최고가 (트레일링 스탑용)
        self.holdings = {}           # 보유 여부
        self.initialized = False     # 초기화 설정 여부
        
    def select_portfolio(self, tickers, window=5):
        """
        듀얼 노이즈 필터를 적용하여 포트폴리오 선택
        Args:
            tickers (list): 티커 리스트
            window (int): 평균을 위한 윈도우 길이
        Returns:
            list: 선택된 포트폴리오
        """
        try:
            portfolio = []
            noise_list = []
            
            print(f"전체 {len(tickers)}개 코인 중 노이즈가 낮은 {COIN_NUMS}개 선택 중...")
            
            for ticker in tickers:
                df = pyupbit.get_ohlcv(ticker, interval="day", count=10)
                if df is None or len(df) < window:
                    continue

                # 노이즈 계산: 1 - |시가-종가|/(고가-저가)
                noise_day = 1 - abs(df['open'] - df['close']) / (df['high'] - df['low'])
                df_hour = pyupbit.get_ohlcv(ticker, interval="minute60", count=10)
                noise_hour = 1 - abs(df_hour['open'] - df_hour['close']) / (df_hour['high'] - df_hour['low'])
                dual_noise = (noise_day.rolling(window).mean() + noise_hour.rolling(window).mean()) / 2
                noise_list.append((ticker, dual_noise.iloc[-2]))

            # 노이즈가 낮은 순으로 정렬
            sorted_noise_list = sorted(noise_list, key=lambda x: x[1])
            
            # 듀얼 노이즈 전략 기반으로 포트폴리오 구성
            for x in sorted_noise_list[:COIN_NUMS]:
                if x[1] < DUAL_NOISE_LIMIT:
                    portfolio.append(x[0])
                    print(f"선택된 코인: {x[0]}, 노이즈: {x[1]:.4f}")

            return portfolio
        except Exception as e:
            print(f"포트폴리오 선택 중 오류 발생: {e}")
            return []
    
    def calculate_target(self, ticker):
        """
        변동성 돌파 전략의 목표가 계산
        Args:
            ticker (str): 코인 티커
        Returns:
            float: 목표가
        """
        try:
            df = pyupbit.get_ohlcv(ticker, interval="day", count=10)
            if df is None or len(df) < 2:
                return None
                
            yesterday = df.iloc[-2]
            today = df.iloc[-1]
            today_open = today['open']
            yesterday_high = yesterday['high']
            yesterday_low = yesterday['low']
            
            target = today_open + (yesterday_high - yesterday_low) * LARRY_K
            return target
        except Exception as e:
            print(f"{ticker} 목표가 계산 중 오류 발생: {e}")
            return None
    
    def calculate_ma5(self, ticker):
        """
        5일 이동평균 계산
        Args:
            ticker (str): 코인 티커
        Returns:
            float: 5일 이동평균
        """
        try:
            df = pyupbit.get_ohlcv(ticker, interval="day", count=10)
            if df is None or len(df) < 5:
                return None
                
            ma5 = df['close'].rolling(window=5).mean().iloc[-2]
            return ma5
        except Exception as e:
            print(f"{ticker} 이동평균 계산 중 오류 발생: {e}")
            return None
    
    def get_current_prices(self):
        """
        포트폴리오 내 코인들의 현재가 조회
        Returns:
            dict: 코인별 현재가
        """
        for _ in range(3):
            try:
                if hasattr(self, 'last_fetch') and (datetime.datetime.now() - self.last_fetch).seconds < 5:
                    return self.last_prices
                self.last_prices = pyupbit.get_current_price(self.portfolio)
                self.last_fetch = datetime.datetime.now()
                return self.last_prices
            except Exception as e:
                print(f"현재가 조회 중 오류 발생: {e}")
                return {}
        return {}
    
    def update_daily_high_prices(self):
        """
        당일 고가 업데이트
        
        Returns:
            dict: 코인별 당일 고가
        """
        try:
            high_prices = {}
            for ticker in self.portfolio:
                df = pyupbit.get_ohlcv(ticker, interval="day", count=1)
                if df is not None and len(df) > 0:
                    today_high = df.iloc[-1]['high']
                    high_prices[ticker] = today_high
                else:
                    high_prices[ticker] = 0
            return high_prices
        except Exception as e:
            print(f"당일 고가 업데이트 중 오류 발생: {e}")
            return {ticker: 0 for ticker in self.portfolio}
    
    def initialize_trading_day(self):
        """
        트레이딩 데이 초기화 (목표가, 이동평균, 고가 계산)
        """
        print("트레이딩 데이 초기화 중...")
        
        # 목표가 계산
        self.targets = {}
        for ticker in self.portfolio:
            target = self.calculate_target(ticker)
            if target:
                self.targets[ticker] = target
                print(f"{ticker} 목표가: {target:,.0f}원")
        
        # 5일 이동평균 계산
        self.ma5s = {}
        for ticker in self.portfolio:
            ma5 = self.calculate_ma5(ticker)
            if ma5:
                self.ma5s[ticker] = ma5
                print(f"{ticker} 5일 이동평균: {ma5:,.0f}원")
        
        # 당일 고가 초기화
        self.high_prices = self.update_daily_high_prices()
        
        # 보유 상태 초기화
        self.holdings = {ticker: False for ticker in self.portfolio}
        
        # 매수 가격 및 최고가 초기화
        self.bought_prices = {ticker: 0 for ticker in self.portfolio}
        self.max_prices = {ticker: 0 for ticker in self.portfolio}
    
    def try_buy(self, prices, budget_per_coin):
        """
        매수 조건 확인 및 매수 시도
        Args:
            prices (dict): 코인별 현재가
            budget_per_coin (float): 코인당 투자 금액
        """
        for ticker in self.portfolio:
            if not self.holdings[ticker] and ticker in prices:  
                price = prices[ticker]  # 현재가
                target = self.targets[ticker]  # 목표가
                ma5 = self.ma5s[ticker]  # 5일 이동평균
            
            # 매수 조건
            # 1) 현재가가 목표가 이상이고
            # 2) 당일 고가가 목표가 대비 5% 이상 오르지 않았으며 (원래 2%였음)
            # 3) 현재가가 5일 이동평균 이상이고
            # 4) 해당 코인을 보유하지 않았을 때

            if price >= target and price >= ma5:
                # 실제 매수 로직
                try:
                    result = self.upbit.buy_market_order(ticker, budget_per_coin)
                    print(f"매수: {ticker}, 금액: {budget_per_coin:,.0f}원")
                except Exception as e:
                    print(f"{ticker} 매수 중 오류 발생: {e}")
                
                # 매수 상태 업데이트
                self.holdings[ticker] = True
                self.bought_prices[ticker] = price
                self.max_prices[ticker] = price
                
                time.sleep(INTERVAL)
    
    def try_sell(self, prices):
        """
        매도 조건 확인 및 매도 시도

        Args:
            prices (dict): 코인별 현재가
        """
        for ticker in self.portfolio:
            if self.holdings[ticker] and ticker in prices:
                if ticker not in self.holdings or not self.holdings[ticker]:
                    continue

                # current_price = prices[ticker]
                # bought_price = self.bought_prices[ticker]
                # self.max_prices[ticker] = max(self.max_prices[ticker], current_price)
                current_price = prices.get(ticker, 0)
                bought_price = self.bought_prices.get(ticker, 0)
                self.max_prices[ticker] = max(self.max_prices.get(ticker, 0), current_price)

                if bought_price == 0:
                    continue

                # 현재 수익률 계산
                profit_rate = (current_price / bought_price) - 1

                # 손절 (5% 손실 시 매도)
                if profit_rate < -0.05:
                    balance = self.upbit.get_balance(ticker.split('-')[1])
                    if balance > 0:
                        self.upbit.sell_market_order(ticker, balance)
                        print(f"손절 매도: {ticker}, 손실률: {profit_rate:.2%}")
                        self.holdings[ticker] = False
                    continue  # 매도 후 트레일링 스탑 체크 안 함
            
                # 1) 수익률이 TRAILING_STOP_MIN_PROFIT 이상이고
                # 2) 현재가가 최고가 대비 TRAILING_STOP_GAP 이상 하락했을 때
                if profit_rate >= TRAILING_STOP_MIN_PROFIT and current_price <= self.max_prices[ticker] * (1 - TRAILING_STOP_GAP):
                    balance = self.upbit.get_balance(ticker.split('-')[1])
                    if balance > 0:
                        self.upbit.sell_market_order(ticker, balance)
                        print(f"트레일링 스탑 매도: {ticker}, 수익률: {profit_rate:.2%}")
                        self.holdings[ticker] = False


    def sell_all_at_market_close(self):
        """
        장 마감 시 모든 보유 코인 매도
        """
        for ticker in self.portfolio:
            try:
                balance = self.upbit.get_balance(ticker.split('-')[1])
                if balance > 0:
                    result = self.upbit.sell_market_order(ticker, balance)
                    print(f"장 마감 매도: {ticker}, 수량: {balance:.8f}")
                    time.sleep(INTERVAL)
            except Exception as e:
                print(f"{ticker} 장 마감 매도 중 오류 발생: {e}")


    def run(self):
        """
        트레이딩 봇 실행
        """
        try:
            print("업비트 트레이딩 봇 시작...")
            
            # 티커 목록 가져오기
            tickers = pyupbit.get_tickers(fiat="KRW")
            print(f"총 {len(tickers)}개 코인 조회됨")
            
            # 포트폴리오 선택
            self.portfolio = self.select_portfolio(tickers)
            print(f"선택된 포트폴리오: {self.portfolio}")
            
            if not self.portfolio:
                print("포트폴리오가 비어있습니다. 프로그램을 종료합니다.")
                return
            
            # 트레이딩 데이 초기화
            self.initialize_trading_day()
            
            # 예산 계산
            total_budget = self.upbit.get_balance("KRW")
            budget_per_coin = total_budget / len(self.portfolio)
            print(f"코인당 투자 금액: {budget_per_coin:,.0f}원")
            
            # 메인 루프
            while True:
                now = datetime.datetime.now()
                
                # 현재 시간이 오전 8:50~59 사이면 모든 코인 매도 후 다음날 준비
                if now.hour == 8 and now.minute >= 58:
                    print("장 마감 준비 중...")
                    self.sell_all_at_market_close()
                    self.initialized = False
                    time.sleep(120)  # 2분 대기
                    continue
                
                # 오전 9:00~9:10 사이면 새로운 트레이딩 데이 초기화
                if now.hour == 9 and now.minute < 2 and self.initialized == False:
                    print("새로운 트레이딩 데이 시작...")
                    self.initialize_trading_day()
                    self.initialized = True
                
                # 현재가 조회
                prices = self.get_current_prices()
                # 당일의 고가 업데이트트
                self.high_prices = self.update_daily_high_prices()
                if not prices:
                    print("현재가 조회 실패, 10초 후 재시도...")
                    time.sleep(10)
                    continue
                
                # 매수 시도
                self.try_buy(prices, budget_per_coin)
                
                # 매도 시도 (트레일링 스탑)
                self.try_sell(prices)
                
                # 상태 출력
                if now.second % 30 == 0:  # 30초마다 상태 출력
                    holding_coins = [t for t in self.portfolio if self.holdings[t]]
                    print(f"현재 시간: {now}, 보유 코인: {holding_coins}")
                
                time.sleep(INTERVAL)

        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")
            self.sell_all_at_market_close()
            print("모든 코인 매도 완료. 프로그램을 종료합니다.")
            
        except KeyboardInterrupt:
            print("프로그램 종료 요청...")
            self.sell_all_at_market_close()
            print("모든 코인 매도 완료. 프로그램을 종료합니다.")


# 메인 실행 부분
if __name__ == "__main__":
    bot = UpbitTradingBot(access_key=ACCESS_KEY, secret_key=SECRET_KEY)
    bot.run()
