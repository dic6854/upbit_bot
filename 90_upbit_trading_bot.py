import pyupbit
import time
import datetime
import numpy as np
import pandas as pd

# 설정값
INTERVAL = 1                     # 매수 시도 interval (1초 기본)
DEBUG = True                     # True: 매매 API 호출 안됨, False: 실제로 매매 API 호출
COIN_NUMS = 5                    # 분산 투자 코인 개수 (자산/COIN_NUMS를 각 코인에 투자)
DUAL_NOISE_LIMIT = 0.6           # 듀얼 노이즈 한계값 (이 값 이하인 코인만 선택)
LARRY_K = 0.5                    # 변동성 돌파 전략의 K값
TRAILING_STOP_MIN_PROFIT = 0.4   # 최소 40% 이상 수익이 발생한 경우에 Trailing Stop 동작
TRAILING_STOP_GAP = 0.05         # 최고점 대비 5% 하락시 매도

# 업비트 API 접속 정보 (실제 사용 시 파일에서 읽거나 환경변수로 설정)
# 디버그 모드에서는 사용하지 않음
ACCESS_KEY = "your-access-key"
SECRET_KEY = "your-secret-key"

class UpbitTradingBot:
    def __init__(self, access_key=None, secret_key=None, debug=True):
        """
        업비트 트레이딩 봇 초기화
        
        Args:
            access_key (str): 업비트 API 접속 키
            secret_key (str): 업비트 API 시크릿 키
            debug (bool): 디버그 모드 여부
        """
        self.debug = debug
        if not debug and access_key and secret_key:
            self.upbit = pyupbit.Upbit(access_key, secret_key)
        else:
            self.upbit = None
            
        self.portfolio = []          # 선택된 코인 포트폴리오
        self.targets = {}            # 각 코인별 목표가
        self.ma5s = {}               # 5일 이동평균
        self.high_prices = {}        # 당일 고가
        self.bought_prices = {}      # 매수 가격
        self.max_prices = {}         # 매수 후 최고가 (트레일링 스탑용)
        self.holdings = {}           # 보유 여부
        
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
                noise = 1 - abs(df['open'] - df['close']) / (df['high'] - df['low'])
                average_noise = noise.rolling(window=window).mean()
                
                if not np.isnan(average_noise.iloc[-2]):
                    noise_list.append((ticker, average_noise.iloc[-2]))
            
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
            today_open = yesterday['close']
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
        try:
            return pyupbit.get_current_price(self.portfolio)
        except Exception as e:
            print(f"현재가 조회 중 오류 발생: {e}")
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
            if ticker not in prices or ticker not in self.targets or ticker not in self.ma5s:
                continue
                
            price = prices[ticker]  # 현재가
            target = self.targets[ticker]  # 목표가
            ma5 = self.ma5s[ticker]  # 5일 이동평균
            high = self.high_prices.get(ticker, 0)  # 당일 고가
            
            # 매수 조건
            # 1) 현재가가 목표가 이상이고
            # 2) 당일 고가가 목표가 대비 2% 이상 오르지 않았으며
            # 3) 현재가가 5일 이동평균 이상이고
            # 4) 해당 코인을 보유하지 않았을 때
            if (price >= target and 
                high <= target * 1.02 and 
                price >= ma5 and 
                not self.holdings[ticker]):
                
                # 실제 매수 로직
                if not self.debug:
                    try:
                        orderbook = pyupbit.get_orderbook(ticker)[0]['orderbook_units'][0]
                        sell_price = int(orderbook['ask_price'])
                        sell_unit = orderbook['ask_size']
                        unit = budget_per_coin / float(sell_price)
                        min_unit = min(unit, sell_unit)
                        
                        result = self.upbit.buy_limit_order(ticker, sell_price, min_unit)
                        print(f"매수 주문: {ticker}, 가격: {sell_price:,.0f}원, 수량: {min_unit:.8f}")
                    except Exception as e:
                        print(f"{ticker} 매수 중 오류 발생: {e}")
                else:
                    print(f"[디버그] 매수 신호: {ticker}, 가격: {price:,.0f}원, 목표가: {target:,.0f}원")
                
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
            if not self.holdings[ticker] or ticker not in prices:
                continue
                
            current_price = prices[ticker]
            bought_price = self.bought_prices[ticker]
            
            # 최고가 업데이트 (트레일링 스탑용)
            if current_price > self.max_prices[ticker]:
                self.max_prices[ticker] = current_price
            
            # 트레일링 스탑 조건 확인
            profit_rate = (current_price / bought_price) - 1
            
            # 1) 수익률이 TRAILING_STOP_MIN_PROFIT 이상이고
            # 2) 현재가가 최고가 대비 TRAILING_STOP_GAP 이상 하락했을 때
            if (profit_rate >= TRAILING_STOP_MIN_PROFIT and
                current_price <= self.max_prices[ticker] * (1 - TRAILING_STOP_GAP)):
                
                # 실제 매도 로직
                if not self.debug:
                    try:
                        # 보유 수량 확인
                        balance = self.upbit.get_balance(ticker)
                        if balance > 0:
                            result = self.upbit.sell_market_order(ticker, balance)
                            print(f"트레일링 스탑 매도: {ticker}, 수량: {balance:.8f}, 수익률: {profit_rate:.2%}")
                    except Exception as e:
                        print(f"{ticker} 매도 중 오류 발생: {e}")
                else:
                    print(f"[디버그] 트레일링 스탑 매도 신호: {ticker}, 수익률: {profit_rate:.2%}")
                    print(f"  - 매수가: {bought_price:,.0f}원, 현재가: {current_price:,.0f}원, 최고가: {self.max_prices[ticker]:,.0f}원")
                
                # 매도 상태 업데이트
                self.holdings[ticker] = False
                
                time.sleep(INTERVAL)
    
    def sell_all_at_market_close(self):
        """
        장 마감 시 모든 보유 코인 매도
        """
        if self.debug:
            for ticker in self.portfolio:
                if self.holdings[ticker]:
                    print(f"[디버그] 장 마감 매도: {ticker}")
            return
            
        if not self.upbit:
            return
            
        for ticker in self.portfolio:
            try:
                balance = self.upbit.get_balance(ticker)
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
            total_budget = 1000000  # 디버그 모드에서는 가상의 예산 사용
            if not self.debug and self.upbit:
                total_budget = self.upbit.get_balance("KRW")
                
            budget_per_coin = total_budget / len(self.portfolio)
            print(f"코인당 투자 금액: {budget_per_coin:,.0f}원")
            
            # 메인 루프
            while True:
                now = datetime.datetime.now()
                
                # 현재 시간이 오전 8:50~59 사이면 모든 코인 매도 후 다음날 준비
                if now.hour == 8 and now.minute >= 50:
                    print("장 마감 준비 중...")
                    self.sell_all_at_market_close()
                    
                    # 다음 날 오전 9시까지 대기
                    target_time = datetime.datetime(now.year, now.month, now.day, 9, 0)
                    if now.hour >= 9:  # 이미 9시 이후라면 다음날로
                        target_time += datetime.timedelta(days=1)
                        
                    wait_seconds = (target_time - now).total_seconds()
                    print(f"다음 트레이딩 데이까지 {wait_seconds:.0f}초 대기...")
                    
                    if wait_seconds > 0:
                        time.sleep(min(wait_seconds, 600))  # 최대 10분씩 대기
                        continue
                
                # 오전 9:00~9:10 사이면 새로운 트레이딩 데이 초기화
                if now.hour == 9 and now.minute < 10:
                    print("새로운 트레이딩 데이 시작...")
                    self.initialize_trading_day()
                
                # 현재가 조회
                prices = self.get_current_prices()
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
                    holding_coins = [ticker for ticker in self.portfolio if self.holdings[ticker]]
                    print(f"현재 시간: {now}, 보유 코인: {holding_coins}")
                
                time.sleep(INTERVAL)
                
        except KeyboardInterrupt:
            print("프로그램 종료 요청...")
            self.sell_all_at_market_close()
            print("모든 코인 매도 완료. 프로그램을 종료합니다.")
        except Exception as e:
            print(f"예상치 못한 오류 발생: {e}")
            self.sell_all_at_market_close()
            print("모든 코인 매도 완료. 프로그램을 종료합니다.")

# 메인 실행 부분
if __name__ == "__main__":
    # 디버그 모드로 실행 (실제 거래 X)
    bot = UpbitTradingBot(debug=DEBUG)
    
    # 실제 거래를 위해서는 아래 코드 사용 (API 키 필요)
    # bot = UpbitTradingBot(access_key=ACCESS_KEY, secret_key=SECRET_KEY, debug=False)
    
    bot.run()
