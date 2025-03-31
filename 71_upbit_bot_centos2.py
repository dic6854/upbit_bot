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
        self.krw_before = initial_capital
        self.krw_profit = 0
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
                logging.warning(f"KRW 잔고({krw_balance:,.0f}원)가 초기투자금({initial_capital:,.0f}원)보다 적습니다. 초기투자금을 KRW 잔고인 ({krw_balance:,.0f}원)으로 지정합니다.")
                print(f"경고: KRW 잔고({krw_balance:,.0f}원)가 초기투자금({initial_capital:,.0f}원)보다 적습니다. 초기투자금을 KRW 잔고인 ({krw_balance:,.0f}원)으로 지정합니다.")
                self.initial_capital = krw_balance
                self.current_capital = krw_balance
                self.krw_before = krw_balance
            else:
                logging.info(f"KRW잔고({krw_balance:,.0f}원)가 초기투자금({initial_capital:,.0f}원)보다 많습니다. 초기투자금을 ({initial_capital:,.0f}원)으로 합니다.")
                self.initial_capital = initial_capital
                self.current_capital = initial_capital
                self.krw_before = initial_capital
        except Exception as e:
            logging.error(f"잔고 확인 중 오류 발생: {e}")

        logging.info(f"업비트 자동 거래 봇 초기화 완료 (티커: {ticker}, 초기투자금: {self.current_capital:,.0f}원)")

    def get_balance(self, ticker="KRW"):
        """
        특정 티커의 잔고 조회
        :param ticker: 잔고를 조회할 티커 (기본값: KRW, 예: BTC, ETH)
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
            # logging.info(f"신호감지 (매수): 이전 종가({previous_candle['close']}) < 이전 SMA({previous_candle['sma']}), 현재 종가({current_candle['close']}) > 현재 SMA({current_candle['sma']})")
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
            # logging.info(f"신호감지 (매도): 이전 종가({previous_candle['close']}) > 이전 SMA({previous_candle['sma']}), 현재 종가({current_candle['close']}) < 현재 SMA({current_candle['sma']})")
            return True
        return False

    def get_trade_datetime(self, uuid):
        order = self.upbit.get_individual_order(uuid)
        created_at = order['trades'][0]['created_at']
        ldatetime = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z")
        tmp_str_datetime = ldatetime.strftime("%Y-%m-%d %H:%M:%S")
        trade_datetime = datetime.strptime(tmp_str_datetime, "%Y-%m-%d %H:%M:%S")
        return trade_datetime

    def get_buy_price(self, ticker):
        balances = self.upbit.get_balances()
        coin_avg_buy_price = False
        for balance in balances:
            if balance['currency'] == ticker:
                coin_avg_buy_price = float(balance.get('avg_buy_price'))

        return coin_avg_buy_price

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
            order = self.upbit.buy_market_order(self.ticker, self.current_capital * 0.9995)
            time.sleep(2)  # 주문 체결 대기
            if order and 'uuid' in order:
                order_uuid = order['uuid']
                buy_datetime = self.get_trade_datetime(order_uuid)

                lticker = self.ticker.split('-')[1]
                self.coin_balance = self.get_balance(lticker)
                avrg_buy_price = self.get_buy_price(lticker)

                total_buy_price = self.coin_balance * avrg_buy_price
                self.current_capital = self.current_capital - total_buy_price * 1.0005
                self.is_holding = True

                logging.info(f"매수 성공: [{buy_datetime}] {self.coin_balance:,.8f} {lticker} (평균매수가격: {avrg_buy_price:,.0f}원) - 매수금액: {total_buy_price:,.0f}원, 잔고: {self.current_capital:,.0f}원")
                print(f"매수 성공: [{buy_datetime}] {self.coin_balance:,.8f} {lticker} (평균매수가격: {avrg_buy_price:,.0f}원) - 매수금액: {total_buy_price:,.0f}원, 잔고: {self.current_capital:,.0f}원")

                return True
            else:
                logging.error(f"매수 주문 실패: {order}")
                print(f"매수 주문 실패: {order}")
                return False
        except Exception as e:
            logging.error(f"매수 실행 중 오류 발생: {e}")
            print(f"매수 실행 중 오류 발생: {e}")
            return False


    def get_sell_price(self, order_uuid):
        order_info = self.upbit.get_order(order_uuid)
        if order_info and order_info.get('state') == 'done':
            trades = order_info.get('trades')
            if trades:
                total_sell_price = 0
                total_sell_volume = 0

                for trade in trades:
                    price = float(trade['price'])
                    volume = float(trade['volume'])
                    total_sell_price += price * volume
                    total_sell_volume += volume
                if total_sell_volume > 0:
                    average_sell_price = total_sell_price / total_sell_volume
                    return average_sell_price
                else:
                    return False
            else:
                return False
        else:
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
            time.sleep(2)  # 주문 체결 대기

            if order and 'uuid' in order:
                # 매도 후 KRW 잔고 확인
                order_uuid = order['uuid']
                sell_datetime = self.get_trade_datetime(order_uuid)
                avrg_sell_price = self.get_sell_price(order_uuid)
                sell_volume = float(order['volume'])

                # 총 매도 금액 계산
                total_sell_price = avrg_sell_price * sell_volume

                # 초기투자금 대비 수익금 및 잔고
                self.current_capital = self.current_capital + total_sell_price * 0.9995
                current_profit = self.current_capital - self.initial_capital
                if current_profit > 0:
                    self.current_capital = self.initial_capital

                # 실제 잔고 대비 수익금
                krw_after = self.get_balance("KRW")
                krw_earnings = krw_after - self.krw_before
                self.krw_profit += krw_earnings
                self.krw_before = krw_after

                logging.info(f"매도 성공: [{sell_datetime}] {sell_volume:,.8f} {coin_ticker} (평균매도가격: {avrg_sell_price:,.0f}원) - 매도금액: {total_sell_price:,.0f}원, 손익금 {krw_earnings:,.0f}원, 총 수익금: {self.krw_profit:,.0f}원, 초기투자금 대비 잔고: {self.current_capital:,.0f}원")
                print(f"매도 성공: [{sell_datetime}] {sell_volume:,.8f} {coin_ticker} (평균매도가격: {avrg_sell_price:,.0f}원) - 매도금액: {total_sell_price:,.0f}원, 손익금 {krw_earnings:,.0f}원, 총 수익금: {self.krw_profit:,.0f}원, 초기투자금 대비 잔고: {self.current_capital:,.0f}원")

                self.coin_balance = 0
                self.is_holding = False
                return True
            else:
                logging.error(f"매도 주문 실패: {order}")
                print(f"매도 주문 실패: {order}")
                return False
        except Exception as e:
            logging.error(f"매도 실행 중 오류 발생: {e}")
            print(f"매도 실행 중 오류 발생: {e}")
            return False


    def run(self):
        """
        자동 거래 실행
        """
        logging.info(f"자동 거래 시작: (티커: {self.ticker}, 기존잔고: {self.get_balance('KRW'):,.0f}원, 초기투자금: {self.initial_capital:,.0f}원)")
        print(f"자동 거래 시작: (티커: {self.ticker}, 기존잔고: {self.get_balance('KRW'):,.0f}원, 초기투자금: {self.initial_capital:,.0f}원)")

        try:
            count = 1
            while True:
                # 5분봉 데이터 조회 및 20SMA 계산
                df = self.get_ohlcv()
                if df is None or len(df) < 23:  # 최소 23개 필요 (20개 SMA + 3개 신호 확인용)
                    logging.warning("충분한 데이터를 가져오지 못했습니다. 5초 후 재시도합니다.")
                    time.sleep(1)
                    continue

                df = self.calculate_sma(df)

                # 현재 상태 출력
                if count % 60 == 0:
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    krw_balance = self.get_balance("KRW")
                    if self.coin_balance == 0:
                        print(f"[{current_time}][{self.ticker}] [매수 대기 상태] 실제잔고: {krw_balance:,.0f}원, 초기투자금 대비 잔고: {self.current_capital:,.0f}원, 손익금: {self.krw_profit:,.0f}원")
                    else:
                        print(f"[{current_time}][{self.ticker}] [매도 대기 상태] 보유코인수: {self.coin_balance:,.8f}{self.ticker.split('-')[1]}, 손익금: {self.krw_profit:,.0f}원")

                # 매수/매도 신호 확인 및 실행
                if not self.is_holding and self.check_buy_signal(df):
                    print("매수 신호 감지! 현재 시장가로 매수를 실행합니다.")
                    self.buy()
                elif self.is_holding and self.check_sell_signal(df):
                    print("매도 신호 감지! 현재 시장가로 매도를 실행합니다.")
                    self.sell()

                # 1초 대기 (너무 자주 API 호출하지 않도록, 원래는 5초)
                time.sleep(1)
                count += 1

        except KeyboardInterrupt:
            logging.info("사용자에 의해 프로그램이 종료되었습니다.")
            print("프로그램이 종료되었습니다.")
            # 오류 발생 시 보유 중인 코인 매도
            if self.is_holding:
                print("사용자에 의해 프로그램이 종료되어 보유 중인 코인을 매도합니다.")
                self.sell()
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