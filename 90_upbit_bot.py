import time
import pyupbit
import pandas as pd
from datetime import datetime
import os
import logging

# 로깅 설정
logging.basicConfig(
    filename='trading_log.txt',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

class UpbitTradingBot:
    def __init__(self, access_key, secret_key, ticker="KRW-BTC", initial_capital=1000000):
        """
        업비트 자동 거래 봇 초기화
        :param access_key: 업비트 API access key
        :param secret_key: 업비트 API secret key
        :param ticker: 거래할 암호화폐 티커 (기본값: KRW-BTC)
        :param initial_capital: 초기 자본금 (기본값: 1,000,000원)
        """
        # API 연결 설정
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.profit = 0
        self.coin_balance = 0
        self.is_holding = False
        
        # 연결 확인
        if self.upbit is None:
            logging.error("업비트 API 연결 실패")
            raise Exception("업비트 API 연결 실패")
        
        # 잔고 확인
        try:
            krw_balance = self.get_balance("KRW")
            if krw_balance < initial_capital:
                logging.warning(f"KRW 잔고({krw_balance}원)가 초기 자본금({initial_capital}원)보다 적습니다.")
                print(f"경고: KRW 잔고({krw_balance}원)가 초기 자본금({initial_capital}원)보다 적습니다.")
                self.current_capital = krw_balance
        except Exception as e:
            logging.error(f"잔고 확인 중 오류 발생: {e}")
        
        logging.info(f"업비트 자동 거래 봇 초기화 완료 (티커: {ticker}, 초기 자본금: {initial_capital}원)")
        
    def get_balance(self, ticker="KRW"):
        """
        특정 티커의 잔고 조회
        :param ticker: 잔고를 조회할 티커 (기본값: KRW)
        :return: 잔고
        """
        try:
            return self.upbit.get_balance(ticker)
        except Exception as e:
            logging.error(f"잔고 조회 실패: {e}")
            return 0
            
    def get_current_price(self):
        """
        현재 가격 조회
        :return: 현재 가격
        """
        try:
            return pyupbit.get_current_price(self.ticker)
        except Exception as e:
            logging.error(f"현재 가격 조회 실패: {e}")
            return None
            
    def get_ohlcv(self):
        """
        5분봉 데이터 조회
        :return: 5분봉 OHLCV 데이터
        """
        try:
            df = pyupbit.get_ohlcv(self.ticker, interval="minute5", count=30)
            return df
        except Exception as e:
            logging.error(f"OHLCV 데이터 조회 실패: {e}")
            return None
            
    def calculate_sma(self, df, period=20):
        """
        단순이동평균(SMA) 계산
        :param df: OHLCV 데이터프레임
        :param period: 이동평균 기간 (기본값: 20)
        :return: SMA가 추가된 데이터프레임
        """
        df['sma'] = df['close'].rolling(window=period).mean()
        return df
        
    def check_buy_signal(self, df):
        """
        매수 신호 확인 (5분봉이 20SMA를 상향 돌파)
        :param df: SMA가 계산된 데이터프레임
        :return: 매수 신호 여부 (True/False)
        """
        if len(df) < 2:
            return False
            
        # 현재 봉과 이전 봉
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        # 상향 돌파 조건: 이전 봉은 SMA 아래, 현재 봉은 SMA 위
        if previous_candle['close'] < previous_candle['sma'] and current_candle['close'] > current_candle['sma']:
            logging.info(f"매수 신호 감지: 이전 종가({previous_candle['close']}) < 이전 SMA({previous_candle['sma']}), 현재 종가({current_candle['close']}) > 현재 SMA({current_candle['sma']})")
            return True
        return False
        
    def check_sell_signal(self, df):
        """
        매도 신호 확인 (5분봉이 20SMA를 하향 돌파)
        :param df: SMA가 계산된 데이터프레임
        :return: 매도 신호 여부 (True/False)
        """
        if len(df) < 2:
            return False
            
        # 현재 봉과 이전 봉
        current_candle = df.iloc[-1]
        previous_candle = df.iloc[-2]
        
        # 하향 돌파 조건: 이전 봉은 SMA 위, 현재 봉은 SMA 아래
        if previous_candle['close'] > previous_candle['sma'] and current_candle['close'] < current_candle['sma']:
            logging.info(f"매도 신호 감지: 이전 종가({previous_candle['close']}) > 이전 SMA({previous_candle['sma']}), 현재 종가({current_candle['close']}) < 현재 SMA({current_candle['sma']})")
            return True
        return False
        
    def buy(self):
        """
        매수 실행
        :return: 매수 성공 여부 (True/False)
        """
        if self.is_holding:
            logging.info("이미 코인을 보유 중입니다.")
            return False
            
        try:
            # 현재 가격 조회
            current_price = self.get_current_price()
            if current_price is None:
                return False
                
            # 매수 가능한 최대 수량 계산 ((수수료 0.05%  + 여유분 0.01%) 고려)
            max_amount = self.current_capital * 0.9994 / current_price
            
            # 매수 주문
            order = self.upbit.buy_market_order(self.ticker, self.current_capital * 0.9994)
            if order and 'uuid' in order:
                time.sleep(1)  # 주문 체결 대기
                self.coin_balance = self.get_balance(self.ticker.split('-')[1])
                self.is_holding = True
                logging.info(f"매수 성공: {self.coin_balance} {self.ticker.split('-')[1]} (가격: {current_price}원)")
                return True
            else:
                logging.error(f"매수 주문 실패: {order}")
                return False
        except Exception as e:
            logging.error(f"매수 실행 중 오류 발생: {e}")
            return False
            
    def sell(self):
        """
        매도 실행
        :return: 매도 성공 여부 (True/False)
        """
        if not self.is_holding:
            logging.info("보유 중인 코인이 없습니다.")
            return False
            
        try:
            # 보유 코인 수량 확인
            coin_ticker = self.ticker.split('-')[1]
            coin_balance = self.get_balance(coin_ticker)
            
            if coin_balance <= 0:
                logging.info(f"보유 중인 {coin_ticker}이(가) 없습니다.")
                self.is_holding = False
                return False
                
            # 매도 주문
            order = self.upbit.sell_market_order(self.ticker, coin_balance)
            if order and 'uuid' in order:
                time.sleep(1)  # 주문 체결 대기
                
                # 매도 후 KRW 잔고 확인
                krw_balance = self.get_balance("KRW")
                
                # 수익 계산 및 자본금 재설정
                if krw_balance > self.initial_capital:
                    self.profit += (krw_balance - self.initial_capital)
                    self.current_capital = self.initial_capital
                    logging.info(f"매도 성공: 수익금 {krw_balance - self.initial_capital}원 발생, 총 수익금: {self.profit}원")
                else:
                    self.current_capital = krw_balance
                    logging.info(f"매도 성공: 손실금 {self.initial_capital - krw_balance}원 발생, 현재 자본금: {self.current_capital}원")
                
                self.coin_balance = 0
                self.is_holding = False
                return True
            else:
                logging.error(f"매도 주문 실패: {order}")
                return False
        except Exception as e:
            logging.error(f"매도 실행 중 오류 발생: {e}")
            return False
            
    def run(self):
        """
        자동 거래 실행
        """
        logging.info("자동 거래 시작")
        print(f"자동 거래 시작 (티커: {self.ticker}, 초기 자본금: {self.initial_capital}원)")
        
        try:
            while True:
                # 5분봉 데이터 조회 및 20SMA 계산
                df = self.get_ohlcv()
                if df is None or len(df) < 20:
                    logging.warning("충분한 데이터를 가져오지 못했습니다. 5초 후 재시도합니다.")
                    time.sleep(5)
                    continue
                    
                df = self.calculate_sma(df)
                
                # 현재 상태 출력
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                current_price = self.get_current_price()
                print(f"[{current_time}] 현재 가격: {current_price}원, 자본금: {self.current_capital}원, 수익금: {self.profit}원")
                
                # 매수/매도 신호 확인 및 실행
                if not self.is_holding and self.check_buy_signal(df):
                    print("매수 신호 감지! 매수를 실행합니다.")
                    self.buy()
                elif self.is_holding and self.check_sell_signal(df):
                    print("매도 신호 감지! 매도를 실행합니다.")
                    self.sell()
                
                # 5초 대기 (너무 자주 API 호출하지 않도록)
                time.sleep(5)
                
        except KeyboardInterrupt:
            logging.info("사용자에 의해 프로그램이 종료되었습니다.")
            print("프로그램이 종료되었습니다.")
        except Exception as e:
            logging.error(f"프로그램 실행 중 오류 발생: {e}")
            print(f"오류 발생: {e}")
            
            # 오류 발생 시 보유 중인 코인 매도
            if self.is_holding:
                print("오류로 인해 보유 중인 코인을 매도합니다.")
                self.sell()


def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key


if __name__ == "__main__":
    # API 키 설정
    ACCESS_KEY, SECRET_KEY = get_keys()

    # 거래할 암호화폐 티커 설정 (기본값: KRW-BTC)
    TICKER = "KRW-BTC"
    
    # 초기 자본금 설정
    INITIAL_CAPITAL = 1000000
    
    # 봇 생성 및 실행
    try:
        bot = UpbitTradingBot(ACCESS_KEY, SECRET_KEY, TICKER, INITIAL_CAPITAL)
        bot.run()
    except Exception as e:
        logging.error(f"봇 실행 실패: {e}")
        print(f"봇 실행 실패: {e}")
