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
    def __init__(self, access_key, secret_key, ticker="KRW-BTC", initial_capital=100000):
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
                logging.warning(f"KRW잔고({krw_balance}원)가 초기 자본금({initial_capital}원)보다 적습니다. 초기 자본금을 KRW잔고({krw_balance}원)로 합니다.")
                print(f"경고: KRW 잔고({krw_balance}원)가 초기 자본금({initial_capital}원)보다 적습니다. 초기 자본금을 KRW잔고({krw_balance}원)로 합니다.")
                self.current_capital = krw_balance
            else:
                logging.warning(f"KRW잔고({krw_balance}원)가 초기 자본금({initial_capital}원)보다 많습니다. 초기 자본금을 ({initial_capital}원)로 합니다.")
                self.current_capital = initial_capital

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
            # 충분한 데이터를 위해 더 많은 캔들을 가져옴 (최소 23개 필요: 20개 SMA + 3개 신호 확인용)
            df = pyupbit.get_ohlcv(self.ticker, interval="minute5", count=50)
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


    def get_buy_price(self, ticker):
        balances = self.upbit.get_balances()
        for balance in balances:
            if balance['currency'] == ticker:
                coin_avg_buy_price = float(balance.get('avg_buy_price'))
                return coin_avg_buy_price


    def get_sell_price(self, order_uuid):
        order_info = self.upbit.get_order(order_uuid)
        if order_info and order_info.get('state') == 'done':
            trades = order_info.get('trades')
            if trades:
                total_price = 0
                total_volume = 0
                for trade in trades:
                    trade_price = float(trade['price'])
                    trade_volume = float(trade['volume'])
                    total_price += trade_price * trade_volume
                    total_volume += trade_volume
                if total_volume > 0:
                    average_sell_price = total_price / total_volume
                    print(f"이번 매도 거래 평균가 (체결 내역 기반): {average_sell_price:,.2f} 원")
                    return average_sell_price, total_price, total_volume
                else:
                    print("체결된 거래 내역이 없습니다.")
                    return False
            else:
                print("체결 내역 정보를 찾을 수 없습니다.")
                return False
        else:
            print("주문 정보를 가져오거나 아직 체결되지 않았습니다.")
            return False


    def check_buy_signal(self, df):
        """
        매수 신호 확인 (5분봉이 20SMA를 상향 돌파)
        :param df: SMA가 계산된 데이터프레임
        :return: 매수 신호 여부 (True/False)
        """
        if len(df) < 3:  # 최소 3개의 캔들이 필요 (현재 미완결 봉 제외하고 2개 이상)
            return False

        # 완결된 봉들 사용 (최신 봉은 미완결 봉이므로 제외)
        current_candle = df.iloc[-2]  # 가장 최근 완결된 봉
        previous_candle = df.iloc[-3]  # 그 이전 완결된 봉

        # 상향 돌파 조건: 이전 봉은 SMA 아래, 현재 봉은 SMA 위
        if previous_candle['close'] < previous_candle['sma'] and current_candle['close'] > current_candle['sma']:
            logging.info(f"신호감지 (매수): 이전 종가({previous_candle['close']}) < 이전 SMA({previous_candle['sma']}), 현재 종가({current_candle['close']}) > 현재 SMA({current_candle['sma']})")
            # logging.info(f"매수 신호 캔들 시간: {df.index[-2]}")
            return True
        return False


    def check_sell_signal(self, df):
        """
        매도 신호 확인 (5분봉이 20SMA를 하향 돌파)
        :param df: SMA가 계산된 데이터프레임
        :return: 매도 신호 여부 (True/False)
        """
        if len(df) < 3:  # 최소 3개의 캔들이 필요 (현재 미완결 봉 제외하고 2개 이상)
            return False

        # 완결된 봉들 사용 (최신 봉은 미완결 봉이므로 제외)
        current_candle = df.iloc[-2]  # 가장 최근 완결된 봉
        previous_candle = df.iloc[-3]  # 그 이전 완결된 봉

        # 하향 돌파 조건: 이전 봉은 SMA 위, 현재 봉은 SMA 아래
        if previous_candle['close'] > previous_candle['sma'] and current_candle['close'] < current_candle['sma']:
            logging.info(f"신호감지 (매도): 이전 종가({previous_candle['close']}) > 이전 SMA({previous_candle['sma']}), 현재 종가({current_candle['close']}) < 현재 SMA({current_candle['sma']})")
            # logging.info(f"매도 신호 캔들 시간: {df.index[-2]}")
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
            # 매수 주문
            order = self.upbit.buy_market_order(self.ticker, self.current_capital * 0.9994)
            if order and 'uuid' in order:
                time.sleep(1)  # 주문 체결 대기
                self.coin_balance = self.get_balance(self.ticker.split('-')[1])
                lticker = self.ticker.split('-')[1]

                coin_avg_buy_price = self.get_buy_price(lticker)
                total_buy_price = self.coin_balance * coin_avg_buy_price
                self.current_capital = self.current_capital - total_buy_price * 1.0005

                logging.info(f"매수 성공: {self.coin_balance:,.8f} {lticker} (평균매수가격: {int(self.coin_avg_buy_price):,.0f}원) - 매수금액: {total_buy_price:,.0f}, 잔액: {self.current_capital:,.0f}")
                self.is_holding = True
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

                order_uuid = order['uuid']
                average_sell_price, total_sell_price, total_sell_volume = self.get_sell_price(order_uuid)
                # 매도 후 KRW 잔고 확인
                self.current_capital = self.current_capital + total_sell_price * 0.9995

                # 수익 계산 및 자본금 재설정
                earnings = self.current_capital - self.initial_capital
                if earnings > 0:
                    self.profit += earnings
                    self.current_capital = self.initial_capital
                    logging.info(f"매도 성공: {total_sell_volume:,.8f} {self.ticker.split('-')[1]} (평균매도가격: {average_sell_price:,.0f}원) - 매도금액: {total_sell_price:,.0f}, 수익금 {earnings:,.0f}원, 총 수익금: {self.profit:,.0f}원, 잔고: {self.current_capital:,.0f}원")
                else:
                    logging.info(f"매도 성공: 손실금 {earnings:,.0f}원, 잔고: {self.current_capital:,.0f}원")

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
        logging.info(f"자동 거래 시작: (티커: {self.ticker}, 기존 잔고: {self.get_balance('KRW'):,.0f}원, 초기 자본금: {self.initial_capital:,.0f}원)")
        print(f"자동 거래 시작: (티커: {self.ticker}, 기존 잔고: {self.get_balance('KRW'):,.0f}원, 초기 자본금: {self.initial_capital:,.0f}원)")

        try:
            while True:
                # 5분봉 데이터 조회 및 20SMA 계산
                df = self.get_ohlcv()
                if df is None or len(df) < 23:  # 최소 23개 필요 (20개 SMA + 3개 신호 확인용)
                    logging.warning("충분한 데이터를 가져오지 못했습니다. 5초 후 재시도합니다.")
                    time.sleep(5)
                    continue

                df = self.calculate_sma(df)

                # 현재 상태 출력
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                current_price = self.get_current_price()
                print(f"[{current_time}][{self.ticker}] 현재 가격: {current_price:,.0f}원, 현재 투자금: {self.current_capital:,.0f}원, 수익금: {self.profit:,.0f}원")

                # 매수/매도 신호 확인 및 실행
                if not self.is_holding and self.check_buy_signal(df):
                    print("매수 신호 감지! 현재 시장가로 매수를 실행합니다.")
                    self.buy()
                elif self.is_holding and self.check_sell_signal(df):
                    print("매도 신호 감지! 현재 시장가로 매도를 실행합니다.")
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

if __name__ == "__main__":
    # API 키 설정
    ACCESS_KEY, SECRET_KEY = get_keys()

    # 거래할 암호화폐 티커 설정 (기본값: KRW-BTC)
    TICKER = "KRW-BTC"

    # 초기 자본금 설정
    INITIAL_CAPITAL = 100000

    # 봇 생성 및 실행
    try:
        bot = UpbitTradingBot(ACCESS_KEY, SECRET_KEY, TICKER, INITIAL_CAPITAL)
        bot.run()
    except Exception as e:
        logging.error(f"봇 실행 실패: {e}")
        print(f"봇 실행 실패: {e}")