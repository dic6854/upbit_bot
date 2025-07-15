import time
import pyupbit
import pandas as pd
from datetime import datetime
import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from functools import lru_cache, wraps


# 로깅 설정
def setup_logging(log_dir='logs'):
    """
    로깅 설정 함수
    """
    # 로그 디렉토리 생성
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)
    
    # 로그 파일 경로
    log_file = os.path.join(log_dir, 'trading_log.txt')
    
    # 로거 설정
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    
    # 기존 핸들러 제거
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # 파일 핸들러 (로테이팅 파일 핸들러 사용)
    file_handler = RotatingFileHandler(
        log_file, maxBytes=10*1024*1024, backupCount=5
    )
    file_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    file_handler.setFormatter(file_format)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_format)
    
    # 핸들러 추가
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger


# 재시도 데코레이터
def retry_on_failure(max_attempts=3, delay=5):
    """
    API 호출 실패 시 재시도하는 데코레이터
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        logging.error(f"{func.__name__} 함수 실행 실패 (최대 시도 횟수 초과): {e}")
                        raise
                    logging.warning(f"{func.__name__} 함수 실행 실패, {delay}초 후 재시도 ({attempts}/{max_attempts}): {e}")
                    time.sleep(delay)
        return wrapper
    return decorator


def get_keys():
    """
    환경 변수에서 API 키 가져오기
    """
    try:
        access_key = os.environ['UPBIT_ACCESS_KEY']
        secret_key = os.environ['UPBIT_SECRET_KEY']
        return access_key, secret_key
    except KeyError:
        logging.error("환경 변수 UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY가 설정되지 않았습니다.")
        print("오류: 환경 변수 UPBIT_ACCESS_KEY 또는 UPBIT_SECRET_KEY가 설정되지 않았습니다.")
        print("다음 명령어로 환경 변수를 설정해주세요:")
        print("export UPBIT_ACCESS_KEY='your_access_key'")
        print("export UPBIT_SECRET_KEY='your_secret_key'")
        sys.exit(1)


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

        # 안전 장치 설정
        self.max_loss_percent = 5  # 최대 손실 허용 비율 (%)
        self.max_daily_trades = 30  # 일일 최대 거래 횟수
        self.daily_trade_count = 0  # 일일 거래 횟수 카운터
        self.last_trade_date = datetime.now().date()  # 마지막 거래 날짜
        
        # 거래 기록 파일 설정
        self.trade_log_dir = 'trade_logs'
        if not os.path.exists(self.trade_log_dir):
            os.makedirs(self.trade_log_dir)
        
        self.trade_log_file = os.path.join(
            self.trade_log_dir, 
            f'trade_log_{ticker}_{datetime.now().strftime("%Y%m%d")}.csv'
        )
        
        # 거래 기록 파일이 없으면 헤더 작성
        if not os.path.exists(self.trade_log_file):
            with open(self.trade_log_file, 'w', newline='') as f:
                writer = pd.DataFrame(columns=[
                    'Timestamp', 'Type', 'Ticker', 'Price', 'Amount', 
                    'Total', 'Balance', 'Profit'
                ])
                writer.to_csv(f, index=False)

        # 연결 확인
        if self.upbit is None:
            logging.error("업비트 API 연결 실패")
            raise Exception("업비트 API 연결 실패")

        # 잔고 확인
        try:
            krw_balance = self.get_balance("KRW")
            if krw_balance < initial_capital:
                self.log_and_print(f"KRW 잔고({krw_balance:,.0f}원)가 초기투자금({initial_capital:,.0f}원)보다 적습니다. 초기투자금을 KRW 잔고인 ({krw_balance:,.0f}원)으로 지정합니다.", level=logging.WARNING)
                self.initial_capital = krw_balance
                self.current_capital = krw_balance
                self.krw_before = krw_balance
            else:
                self.log_and_print(f"KRW잔고({krw_balance:,.0f}원)가 초기투자금({initial_capital:,.0f}원)보다 많습니다. 초기투자금을 ({initial_capital:,.0f}원)으로 합니다.")
                self.initial_capital = initial_capital
                self.current_capital = initial_capital
                self.krw_before = initial_capital
        except Exception as e:
            self.log_and_print(f"잔고 확인 중 오류 발생: {e}", level=logging.ERROR)

        self.log_and_print(f"업비트 자동 거래 봇 초기화 완료 (코인명: {ticker}, 초기투자금: {self.current_capital:,.0f}원)")


    def log_and_print(self, message, level=logging.INFO):
        """
        로깅과 출력을 동시에 수행하는 헬퍼 함수
        """
        if level == logging.INFO:
            logging.info(message)
        elif level == logging.WARNING:
            logging.warning(message)
        elif level == logging.ERROR:
            logging.error(message)
        elif level == logging.DEBUG:
            logging.debug(message)
        
        print(message)
    
    def record_trade(self, trade_type, price, amount, total, balance, profit=0):
        """
        거래 기록 저장
        """
        try:
            new_row = pd.DataFrame([{
                'Timestamp': datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                'Type': trade_type,
                'Ticker': self.ticker,
                'Price': price,
                'Amount': amount,
                'Total': total,
                'Balance': balance,
                'Profit': profit
            }])
            
            # 기존 CSV 파일에 추가
            new_row.to_csv(self.trade_log_file, mode='a', header=False, index=False)
            
            self.log_and_print(f"거래 기록 저장: {trade_type}, {self.ticker}, {price:,.0f}원, {amount:,.8f}", level=logging.DEBUG)
        except Exception as e:
            self.log_and_print(f"거래 기록 저장 중 오류 발생: {e}", level=logging.ERROR)


    @retry_on_failure(max_attempts=3, delay=5)
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


    @retry_on_failure(max_attempts=3, delay=5)
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


    @lru_cache(maxsize=32)
    def get_cached_ohlcv(self, ticker, interval, count):
        """
        OHLCV 데이터를 캐싱하여 반복적인 API 호출 감소
        """
        return pyupbit.get_ohlcv(ticker, interval=interval, count=count)


    @retry_on_failure(max_attempts=3, delay=5)
    def get_ohlcv(self):
        """
        5분봉 데이터 조회 - 캐싱 활용
        :return: 5분봉 OHLCV 데이터
        """
        try:
            # 현재 시간을 5분 단위로 내림하여 캐시 키로 사용
            now = datetime.now()
            cache_key = now.replace(minute=now.minute - now.minute % 5, second=0, microsecond=0)
            
            # 충분한 데이터를 위해 더 많은 캔들을 가져옴 (최소 23개 필요: 20개 SMA + 3개 신호 확인용)
            df = self.get_cached_ohlcv(self.ticker, "minute5", 50)
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
            logging.info(f"신호감지 (매수): 이전 종가({previous_candle['close']:.2f}) < 이전 SMA({previous_candle['sma']:.2f}), 현재 종가({current_candle['close']:.2f}) > 현재 SMA({current_candle['sma']:.2f})")
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
            logging.info(f"신호감지 (매도): 이전 종가({previous_candle['close']:.2f}) > 이전 SMA({previous_candle['sma']:.2f}), 현재 종가({current_candle['close']:.2f}) < 현재 SMA({current_candle['sma']:.2f})")
            return True
        return False


    @retry_on_failure(max_attempts=3, delay=5)
    def get_trade_datetime(self, uuid):
        """
        거래 시간 조회
        """
        try:
            order = self.upbit.get_individual_order(uuid)
            if 'trades' in order and len(order['trades']) > 0:
                created_at = order['trades'][0]['created_at']
                ldatetime = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%S%z")
                tmp_str_datetime = ldatetime.strftime("%Y-%m-%d %H:%M:%S")
                trade_datetime = datetime.strptime(tmp_str_datetime, "%Y-%m-%d %H:%M:%S")
                return trade_datetime
            else:
                logging.warning(f"거래 내역이 없습니다: {uuid}")
                return datetime.now()
        except Exception as e:
            logging.error(f"거래 시간 조회 중 오류 발생: {e}")
            return datetime.now()


    @retry_on_failure(max_attempts=3, delay=5)
    def get_buy_price(self, ticker):
        """
        매수 가격 조회
        """
        try:
            balances = self.upbit.get_balances()
            coin_avg_buy_price = False
            for balance in balances:
                if balance['currency'] == ticker:
                    coin_avg_buy_price = float(balance.get('avg_buy_price', 0))
                    break
            
            if coin_avg_buy_price:
                return coin_avg_buy_price
            else:
                current_price = self.get_current_price()
                logging.warning(f"매수 가격 정보를 얻지 못했습니다. 현재 시장 가격({current_price})을 사용합니다.")
                return current_price
        except Exception as e:
            logging.error(f"매수 가격 조회 중 오류 발생: {e}")
            current_price = self.get_current_price()
            return current_price


    def check_safety_limits(self):
        """
        안전 제한 확인
        """
        # 현재 날짜 확인
        current_date = datetime.now().date()
        
        # 날짜가 바뀌면 거래 횟수 리셋
        if self.last_trade_date != current_date:
            self.daily_trade_count = 0
            self.last_trade_date = current_date
        
        # 일일 최대 거래 횟수 확인
        if self.daily_trade_count >= self.max_daily_trades:
            logging.warning(f"일일 최대 거래 횟수({self.max_daily_trades}회)에 도달했습니다. 내일까지 거래를 중단합니다.")
            return False
        
        # 최대 손실 확인
        if self.is_holding:
            coin_ticker = self.ticker.split('-')[1]
            coin_balance = self.get_balance(coin_ticker)
            current_price = self.get_current_price()
            
            if current_price is not None and coin_balance > 0:
                buy_price = self.get_buy_price(coin_ticker)
                current_value = coin_balance * current_price
                buy_value = coin_balance * buy_price
                
                loss_percent = (buy_value - current_value) / buy_value * 100
                
                if loss_percent > self.max_loss_percent:
                    logging.warning(f"최대 손실 비율({self.max_loss_percent}%)을 초과했습니다. 손절합니다.")
                    self.sell()
                    return False
        
        return True


    @retry_on_failure(max_attempts=3, delay=5)
    def buy(self):
        """
        매수 실행
        :return: 매수 성공 여부 (True/False)
        """
        if self.is_holding:
            logging.info("이미 코인을 보유 중입니다.")
            return False

        try:
            # 매수 전 KRW 잔고 확인
            # krw_before = self.get_balance("KRW")
            
            # 매수 주문
            order = self.upbit.buy_market_order(self.ticker, self.current_capital * 0.9995)
            time.sleep(2)  # 주문 체결 대기
            
            if order and 'uuid' in order:
                order_uuid = order['uuid']
                buy_datetime = self.get_trade_datetime(order_uuid)
                
                # 매수 후 잔고 확인
                coin_ticker = self.ticker.split('-')[1]
                self.coin_balance = self.get_balance(coin_ticker)
                avrg_buy_price = self.get_buy_price(coin_ticker)
                
                # 실제 사용된 금액 계산
                # krw_after = self.get_balance("KRW")
                # actual_spent = krw_before - krw_after
                
                # 총 매수 금액 계산
                total_buy_price = self.coin_balance * avrg_buy_price
                
                # 자본금 업데이트
                self.current_capital = self.current_capital - total_buy_price * 1.0005
                self.is_holding = True
                
                # 일일 거래 횟수 증가
                self.daily_trade_count += 1
                
                # 거래 기록 저장
                self.record_trade('BUY', avrg_buy_price, self.coin_balance, total_buy_price, self.current_capital)
                
                message = f"매수 성공: [{buy_datetime}] {self.coin_balance:,.8f} {coin_ticker} (평균매수가격: {avrg_buy_price:,.0f}원) - 매수금액: {total_buy_price:,.0f}원, 잔고: {self.current_capital:,.0f}원"
                self.log_and_print(message)
                return True
            else:
                self.log_and_print(f"매수 주문 실패: {order}", level=logging.ERROR)
                return False
        except Exception as e:
            self.log_and_print(f"매수 실행 중 오류 발생: {e}", level=logging.ERROR)
            return False


    @retry_on_failure(max_attempts=3, delay=5)
    def get_sell_price(self, order_uuid):
        """
        매도 가격 조회
        """
        try:
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
            
            # 거래 정보를 얻지 못한 경우 현재 시장 가격 반환
            current_price = self.get_current_price()
            logging.warning(f"매도 가격 정보를 얻지 못했습니다. 현재 시장 가격({current_price})을 사용합니다.")
            return current_price
        except Exception as e:
            logging.error(f"매도 가격 조회 중 오류 발생: {e}")
            current_price = self.get_current_price()
            return current_price


    @retry_on_failure(max_attempts=3, delay=5)
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

                # 일일 거래 횟수 증가
                self.daily_trade_count += 1

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
                self.krw_before = krw_after
                self.krw_profit += krw_earnings

                message = f"매도 성공: [{sell_datetime}] {sell_volume:,.8f} {coin_ticker} (평균매도가격: {avrg_sell_price:,.0f}원) - 매도금액: {total_sell_price:,.0f}원, 손익금 {krw_earnings:,.0f}원, 총 수익금: {self.krw_profit:,.0f}원, 초기투자금 대비 잔고: {self.current_capital:,.0f}원"
                
                # 거래 기록 저장
                self.record_trade('SELL', avrg_sell_price, sell_volume, total_sell_price, self.current_capital, krw_earnings)
                
                self.log_and_print(message)

                self.coin_balance = 0
                self.is_holding = False
                return True
            else:
                self.log_and_print(f"매도 주문 실패: {order}", level=logging.ERROR)
                return False
        except Exception as e:
            self.log_and_print(f"매도 실행 중 오류 발생: {e}", level=logging.ERROR)
            return False


    def check_system_health(self):
        """
        시스템 건전성 확인
        """
        try:
            # API 연결 확인
            balance = self.upbit.get_balance("KRW")
            if balance is None:
                logging.error("API 연결 실패: 잔고 조회 불가")
                return False
            
            # 시장 데이터 접근 확인
            current_price = self.get_current_price()
            if current_price is None:
                logging.error("시장 데이터 접근 실패: 현재 가격 조회 불가")
                return False
            
            # OHLCV 데이터 접근 확인
            df = self.get_ohlcv()
            if df is None or len(df) < 20:
                logging.error("OHLCV 데이터 접근 실패: 충분한 데이터 조회 불가")
                return False
            
            logging.info("시스템 건전성 확인 완료: 정상")
            return True
        except Exception as e:
            logging.error(f"시스템 건전성 확인 중 오류 발생: {e}")
            return False


    def run(self):
        """
        자동 거래 실행
        """
        self.log_and_print(f"자동 거래 시작: (티커: {self.ticker}, 기존잔고: {self.get_balance('KRW'):,.0f}원, 초기투자금: {self.initial_capital:,.0f}원)")

        try:
            count = 1
            while True:
                # 시스템 건전성 확인 (1시간마다)
                if count % 720 == 0:  # 5초 간격으로 720회 = 1시간
                    if not self.check_system_health():
                        self.log_and_print("시스템 건전성 문제 감지, 1분 대기 후 재시도", level=logging.WARNING)
                        time.sleep(60)  # 1분 대기 후 재시도
                        continue
                
                # 안전 제한 확인
                if not self.check_safety_limits():
                    self.log_and_print("안전 제한으로 인해 거래를 건너뜁니다.", level=logging.INFO)
                    time.sleep(60)  # 1분 대기
                    continue
                
                # 5분봉 데이터 조회 및 20SMA 계산
                df = self.get_ohlcv()
                if df is None or len(df) < 23:  # 최소 23개 필요 (20개 SMA + 3개 신호 확인용)
                    self.log_and_print("충분한 데이터를 가져오지 못했습니다. 5초 후 재시도합니다.", level=logging.WARNING)
                    time.sleep(5)
                    continue

                df = self.calculate_sma(df)

                # 현재 상태 출력 (1분마다)
                if count % 12 == 0:  # 5초 간격으로 12회 = 1분
                    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    krw_balance = self.get_balance("KRW")
                    current_profit = self.current_capital - self.initial_capital
                    if self.coin_balance == 0:
                        print(f"[{current_time}][{self.ticker}] [매수 대기 상태] 실제잔고: {krw_balance:,.0f}원, 초기투자금 대비 잔고: {self.current_capital:,.0f}원, 손익금: {current_profit:,.0f}원")
                    else:
                        print(f"[{current_time}][{self.ticker}] [매도 대기 상태] 보유코인수: {self.coin_balance:,.8f}{self.ticker.split('-')[1]}, 손익금: {current_profit:,.0f}원")

                # 매수/매도 신호 확인 및 실행
                if not self.is_holding and self.check_buy_signal(df):
                    self.log_and_print("매수 신호 감지! 현재 시장가로 매수를 실행합니다.")
                    self.buy()
                elif self.is_holding and self.check_sell_signal(df):
                    self.log_and_print("매도 신호 감지! 현재 시장가로 매도를 실행합니다.")
                    self.sell()

                # 5초 대기 (API 호출 제한 고려)
                time.sleep(5)
                count += 1

        except KeyboardInterrupt:
            self.log_and_print("사용자에 의해 프로그램이 종료되었습니다.")
            # 오류 발생 시 보유 중인 코인 매도
            if self.is_holding:
                self.log_and_print("사용자에 의해 프로그램이 종료되어 보유 중인 코인을 매도합니다.")
                self.sell()
        except Exception as e:
            self.log_and_print(f"프로그램 실행 중 오류 발생: {e}", level=logging.ERROR)
            # 오류 발생 시 보유 중인 코인 매도
            if self.is_holding:
                self.log_and_print("오류로 인해 보유 중인 코인을 매도합니다.")
                self.sell()


if __name__ == "__main__":
    # 로깅 설정
    logger = setup_logging()
    
    # API 키 설정
    try:
        ACCESS_KEY, SECRET_KEY = get_keys()
        
        # 코인코드 및 초기투자금 설정
        TICKER = 'KRW-BTC'
        INITIAL_CAPITAL = 100000
        
        # 봇 생성 및 실행
        bot = UpbitTradingBot(ACCESS_KEY, SECRET_KEY, TICKER, INITIAL_CAPITAL)
        bot.run()
    except Exception as e:
        logging.error(f"봇 실행 실패: {e}")
        print(f"봇 실행 실패: {e}")