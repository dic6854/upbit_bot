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

def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key


class UpbitTradingBot:
    def __init__(self, ticker="KRW-BTC", initial_capital=1000000):
        """
        업비트 자동 거래 봇 초기화
        :param ticker: 거래할 암호화폐 티커 (기본값: KRW-BTC)
        :param initial_capital: 초기 자본금 (기본값: 1,000,000원)
        """

        # 파일 이름 설정
        self.file_name_m1 = f"test/{ticker}_m1.csv"
        self.file_name_m5 = f"test/{ticker}_m5.csv"
        self.trade_output = f"test/backtest/{ticker}_trade_m5.csv"
        self.profit_output = f"test/backtest/{ticker}_profit_m5.csv"

        self.df_m1 = pd.read_csv(self.file_name_m1, index_col=0)
        self.df_m5 = pd.read_csv(self.file_name_m5, index_col=0)
        try:
            self.df_m1.index = pd.to_datetime(self.df_m1.index, format="%Y-%m-%d %H:%M:%S")
        except:
            self.df_m1.index = pd.to_datetime(self.df_m1.index, format="%Y-%m-%d %H:%M")
        try:
            self.df_m5.index = pd.to_datetime(self.df_m5.index, format="%Y-%m-%d %H:%M:%S")
        except:
            self.df_m5.index = pd.to_datetime(self.df_m5.index, format="%Y-%m-%d %H:%M")

        # API 연결 설정
        self.ticker = ticker
        self.initial_capital = initial_capital
        self.current_capital = initial_capital
        self.profit = 0
        self.coin_balance = 0
        self.is_holding = False

        logging.info(f"업비트 자동 거래 봇 초기화 완료 (티커: {ticker}, 초기 자본금: {initial_capital}원)")


    def check_buy_signal(self, pdatetime):
        current_candle = self.df_m5.loc[pdatetime]
        previous_time = pdatetime - pd.Timedelta(minutes=5)
        previous_candle = self.df_m5.loc[previous_time]

        # 상향 돌파 조건: 이전 봉은 SMA 아래, 현재 봉은 SMA 위
        if previous_candle['close'] < previous_candle['SMA20'] and current_candle['close'] > current_candle['SMA20']:
            logging.info(f"신호감지 (매수): 이전 종가({previous_candle['close']}) < 이전 SMA({previous_candle['SMA20']}), 현재 종가({current_candle['close']}) > 현재 SMA({current_candle['SMA20']})")
            return True
        return False


    def check_sell_signal(self, pdatetime):
        current_candle = self.df_m5.loc[pdatetime]
        previous_time = pdatetime - pd.Timedelta(minutes=5)
        previous_candle = self.df_m5.loc[previous_time]

        # 하향 돌파 조건: 이전 봉은 SMA 위, 현재 봉은 SMA 아래
        if previous_candle['close'] > previous_candle['SMA20'] and current_candle['close'] < current_candle['SMA20']:
            logging.info(f"신호감지 (매도): 이전 종가({previous_candle['close']}) > 이전 SMA({previous_candle['SMA20']}), 현재 종가({current_candle['close']}) < 현재 SMA({current_candle['SMA20']})")
            return True
        return False


    def set_volume(self, capital, price):
        unit = int((capital / price) * 10000) / 10000

        while True:
            volume = price * unit * 1.0005

            if float(volume) < float(capital):
                return unit
            unit -= 0.0001


    def buy(self, pdatetime):
        if self.is_holding:
            logging.info("이미 코인을 보유 중입니다.")
            return False

        # 매수 주문
        row_m1 = self.df_m1.loc[pdatetime]

        current_price = row_m1['close']
        self.coin_balance = self.set_volume(self.current_capital, current_price)
        buy_price = self.coin_balance * current_price
        self.current_capital = self.current_capital - buy_price * 1.0005

        logging.info(f"매수 성공: {self.coin_balance:,.8f} {self.ticker} (매수가격: {current_price:,.0f}원) - 매수금액: {buy_price:,.0f}, 잔고: {self.current_capital:,.0f}")
        self.is_holding = True
        return True


    def sell(self, pdatetime):
        if not self.is_holding:
            logging.info("보유 중인 코인이 없습니다.")
            return False

        # 매도 주문
        row_m1 = self.df_m1.loc[pdatetime]
  
        current_price = row_m1['close']
        sell_price = self.coin_balance * current_price

        # 매도 후 KRW 잔고 확인
        self.current_capital = self.current_capital + sell_price * 0.9995

        # 수익 계산 및 자본금 재설정
        earnings = self.current_capital - self.initial_capital
        if earnings > 0:
            self.profit += earnings
            self.current_capital = self.initial_capital

            logging.info(f"매도 성공: {self.coin_balance:,.8f} {self.ticker} (매도가격: {sell_price:,.0f}원) - 매도금액: {sell_price:,.0f}, 수익금 {earnings:,.0f}원, 총 수익금: {self.profit:,.0f}원, 잔고: {self.current_capital:,.0f}원")
        else:
            logging.info(f"매도 성공: 손실금 {earnings:,.0f}원, 잔고: {self.current_capital:,.0f}원")

        self.coin_balance = 0
        self.is_holding = False
        return True


    def run(self):
        """
        자동 거래 실행
        """
        logging.info(f"자동 거래 시작: (티커: {self.ticker}, 초기 자본금: {self.initial_capital:,.0f}원)")
        print(f"자동 거래 시작: (티커: {self.ticker}, 초기 자본금: {self.initial_capital:,.0f}원)")

        current_datetime = self.df_m5.index[0]
        current_datetime = current_datetime.replace(hour=9, minute=0, second=0)
        end_datetime = self.df_m5.index[-1]
        while current_datetime <= end_datetime:
            m1_datetime = current_datetime + pd.Timedelta(minutes=1)
            # 매수/매도 신호 확인 및 실행
            if not self.is_holding and self.check_buy_signal(current_datetime):
                print("매수 신호 감지! 현재 시장가로 매수를 실행합니다.")
                self.buy(m1_datetime)
            elif self.is_holding and self.check_sell_signal(current_datetime):
                print("매도 신호 감지! 현재 시장가로 매도를 실행합니다.")
                self.sell(m1_datetime)
            current_datetime += pd.Timedelta(minutes=5)

        # 오류 발생 시 보유 중인 코인 매도
        if self.is_holding:
            print("오류로 인해 보유 중인 코인을 매도합니다.")
            self.sell()

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