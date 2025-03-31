import pyupbit
import time
import datetime
import numpy as np
import pandas as pd
import os
import logging
from logging.handlers import TimedRotatingFileHandler
import configparser
import json
from typing import Dict, List, Optional, Tuple

# 로깅 설정
def setup_logger():
    logger = logging.getLogger("upbit_trader")
    logger.setLevel(logging.INFO)
    
    # 콘솔 핸들러
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    
    # 파일 핸들러 (일별 로테이션)
    file_handler = TimedRotatingFileHandler(
        "logs/trading.log",
        when="midnight",
        interval=1,
        backupCount=7
    )
    file_handler.setLevel(logging.INFO)
    
    # 포맷터
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    console_handler.setFormatter(formatter)
    file_handler.setFormatter(formatter)
    
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger

logger = setup_logger()

# 설정 관리
class ConfigManager:
    def __init__(self, config_file="config.ini"):
        self.config = configparser.ConfigParser()
        self.config_file = config_file
        self.load_config()
        
    def load_config(self):
        if not os.path.exists(self.config_file):
            self.create_default_config()
        self.config.read(self.config_file)
        
    def create_default_config(self):
        self.config["TRADING"] = {
            "interval": "1",
            "debug": "True",
            "coin_nums": "5",
            "dual_noise_limit": "0.6",
            "larry_k": "0.4",
            "trailing_stop_min_profit": "0.3",
            "trailing_stop_gap": "0.03",
            "stop_loss": "0.05"
        }
        with open(self.config_file, "w") as f:
            self.config.write(f)
            
    def get_trading_config(self):
        return {
            "interval": int(self.config["TRADING"]["interval"]),
            "debug": self.config["TRADING"].getboolean("debug"),
            "coin_nums": int(self.config["TRADING"]["coin_nums"]),
            "dual_noise_limit": float(self.config["TRADING"]["dual_noise_limit"]),
            "larry_k": float(self.config["TRADING"]["larry_k"]),
            "trailing_stop_min_profit": float(self.config["TRADING"]["trailing_stop_min_profit"]),
            "trailing_stop_gap": float(self.config["TRADING"]["trailing_stop_gap"]),
            "stop_loss": float(self.config["TRADING"]["stop_loss"])
        }

config = ConfigManager()
TRADING_CONFIG = config.get_trading_config()

class UpbitTradingBot:
    def __init__(self, access_key: Optional[str] = None, secret_key: Optional[str] = None):
        """
        업비트 트레이딩 봇 초기화
        
        Args:
            access_key (str): 업비트 API 접속 키
            secret_key (str): 업비트 API 시크릿 키
        """
        self.upbit = pyupbit.Upbit(access_key, secret_key)
        self.initialized = False
        self.reset_portfolio()
        
        # 웹소켓 클라이언트 초기화
        self.ws_manager = WebSocketManager()
        
    def reset_portfolio(self):
        """포트폴리오 관련 변수 초기화"""
        self.portfolio = []          # 선택된 코인 포트폴리오
        self.targets = {}           # 각 코인별 목표가
        self.ma5s = {}              # 5일 이동평균
        self.high_prices = {}       # 당일 고가
        self.bought_prices = {}     # 매수 가격
        self.max_prices = {}        # 매수 후 최고가 (트레일링 스탑용)
        self.holdings = {}          # 보유 여부
        self.volatility = {}        # 코인별 변동성
        
    def get_tickers(self) -> List[str]:
        """KRW 마켓의 티커 리스트 가져오기"""
        for _ in range(3):  # 최대 3번 재시도
            try:
                tickers = pyupbit.get_tickers(fiat="KRW")
                logger.info(f"총 {len(tickers)}개 코인 조회 완료")
                return tickers
            except Exception as e:
                logger.error(f"티커 조회 실패: {e}")
                time.sleep(1)
        return []
    
    def select_portfolio(self, tickers: List[str], window: int = 5) -> List[str]:
        """
        듀얼 노이즈 필터를 적용하여 포트폴리오 선택
        
        Args:
            tickers (list): 티커 리스트
            window (int): 평균을 위한 윈도우 길이
            
        Returns:
            list: 선택된 포트폴리오
        """
        noise_list = []
        selected = []
        
        logger.info(f"전체 {len(tickers)}개 코인 중 노이즈가 낮은 {TRADING_CONFIG['coin_nums']}개 선택 시작")
        
        for ticker in tickers:
            try:
                # 일봉 데이터로 노이즈 계산
                df_day = self.get_ohlcv_with_retry(ticker, "day", 10)
                if df_day is None or len(df_day) < window:
                    continue
                
                noise_day = 1 - abs(df_day['open'] - df_day['close']) / (df_day['high'] - df_day['low'])
                
                # 시간봉 데이터로 노이즈 계산
                df_hour = self.get_ohlcv_with_retry(ticker, "minute60", 10)
                if df_hour is None or len(df_hour) < window:
                    continue
                
                noise_hour = 1 - abs(df_hour['open'] - df_hour['close']) / (df_hour['high'] - df_hour['low'])
                
                # 듀얼 노이즈 계산 (일봉과 시간봉의 평균)
                dual_noise = (noise_day.rolling(window).mean() + noise_hour.rolling(window).mean()) / 2
                last_noise = dual_noise.iloc[-2]
                
                # 변동성 계산 (전일 고가-저가)
                volatility = (df_day.iloc[-2]['high'] - df_day.iloc[-2]['low']) / df_day.iloc[-2]['open']
                
                noise_list.append({
                    'ticker': ticker,
                    'noise': last_noise,
                    'volatility': volatility
                })
                
            except Exception as e:
                logger.error(f"{ticker} 노이즈 계산 중 오류: {e}")
                continue
        
        # 노이즈가 낮고 변동성이 적절한 코인 선정
        sorted_coins = sorted(
            [x for x in noise_list if x['noise'] < TRADING_CONFIG['dual_noise_limit']],
            key=lambda x: (x['noise'], -x['volatility'])  # 노이즈는 낮을수록, 변동성은 높을수록 좋음
        )
        
        selected = [x['ticker'] for x in sorted_coins[:TRADING_CONFIG['coin_nums']]]
        
        if selected:
            logger.info("선택된 포트폴리오:")
            for coin in selected:
                noise = next(x['noise'] for x in noise_list if x['ticker'] == coin)
                logger.info(f"- {coin}: 노이즈 {noise:.4f}")
        else:
            logger.warning("선택된 코인이 없습니다!")
        
        return selected
    
    def get_ohlcv_with_retry(self, ticker: str, interval: str, count: int, retries: int = 3) -> Optional[pd.DataFrame]:
        """재시도 로직이 포함된 OHLCV 데이터 조회"""
        for attempt in range(retries):
            try:
                df = pyupbit.get_ohlcv(ticker, interval=interval, count=count)
                if df is not None and len(df) >= 2:  # 최소 2개 이상의 데이터 필요
                    return df
            except Exception as e:
                logger.warning(f"{ticker} {interval} 데이터 조회 실패 ({attempt+1}/{retries}): {e}")
                time.sleep(1)
        return None
    
    def calculate_target_price(self, ticker: str) -> Optional[float]:
        """변동성 돌파 전략의 목표가 계산"""
        try:
            df = self.get_ohlcv_with_retry(ticker, "day", 10)
            if df is None or len(df) < 2:
                return None
                
            yesterday = df.iloc[-2]
            today_open = df.iloc[-1]['open']
            
            # 변동성 돌파 목표가 계산: 오늘 시가 + (어제 고가-저가) * K
            target = today_open + (yesterday['high'] - yesterday['low']) * TRADING_CONFIG['larry_k']
            return target
        except Exception as e:
            logger.error(f"{ticker} 목표가 계산 실패: {e}")
            return None
    
    def calculate_ma5(self, ticker: str) -> Optional[float]:
        """5일 이동평균 계산"""
        try:
            df = self.get_ohlcv_with_retry(ticker, "day", 10)
            if df is None or len(df) < 5:
                return None
                
            ma5 = df['close'].rolling(window=5).mean().iloc[-2]  # 어제 기준 5일 이동평균
            return ma5
        except Exception as e:
            logger.error(f"{ticker} 이동평균 계산 실패: {e}")
            return None
    
    def initialize_trading_day(self):
        """거래일 초기화 - 목표가, 이동평균 등 계산"""
        logger.info("거래일 초기화 시작")
        self.reset_portfolio()
        
        # 포트폴리오 선택
        tickers = self.get_tickers()
        if not tickers:
            logger.error("티커 조회 실패로 거래일 초기화 중단")
            return False
            
        self.portfolio = self.select_portfolio(tickers)
        if not self.portfolio:
            logger.error("포트폴리오 선택 실패로 거래일 초기화 중단")
            return False
        
        # 목표가 및 이동평균 계산
        success_count = 0
        for ticker in self.portfolio:
            target = self.calculate_target_price(ticker)
            ma5 = self.calculate_ma5(ticker)
            
            if target and ma5:
                self.targets[ticker] = target
                self.ma5s[ticker] = ma5
                self.volatility[ticker] = (target - self.get_ohlcv_with_retry(ticker, "day", 2).iloc[-1]['open']) / self.get_ohlcv_with_retry(ticker, "day", 2).iloc[-1]['open']
                success_count += 1
                
                logger.info(f"{ticker} - 목표가: {target:,.0f}원, 5일평균: {ma5:,.0f}원, 예상변동성: {self.volatility[ticker]:.2%}")
        
        if success_count < len(self.portfolio):
            logger.warning(f"일부 코인 초기화 실패 ({success_count}/{len(self.portfolio)})")
            
        # 보유 상태 초기화
        self.update_holdings_status()
        
        # 웹소켓 시작
        self.ws_manager.start(self.portfolio, self.handle_ws_message)
        
        self.initialized = True
        logger.info("거래일 초기화 완료")
        return True
    
    def update_holdings_status(self):
        """보유 상태 업데이트"""
        try:
            balances = self.upbit.get_balances()
            holdings = {f"KRW-{balance['currency']}": float(balance['balance']) for balance in balances if balance['currency'] != 'KRW'}
            
            for ticker in self.portfolio:
                if ticker in holdings and holdings[ticker] > 0:
                    self.holdings[ticker] = True
                    # 매수 가격이 없으면 현재가로 설정
                    if ticker not in self.bought_prices or self.bought_prices[ticker] == 0:
                        self.bought_prices[ticker] = pyupbit.get_current_price(ticker)
                    self.max_prices[ticker] = max(self.max_prices.get(ticker, 0), pyupbit.get_current_price(ticker))
                else:
                    self.holdings[ticker] = False
        except Exception as e:
            logger.error(f"보유 상태 업데이트 실패: {e}")
    
    def handle_ws_message(self, msg: dict):
        """웹소켓 메시지 핸들러"""
        try:
            if 'code' in msg:
                ticker = msg['code']
                if ticker in self.portfolio:
                    # 현재가 업데이트
                    current_price = msg.get('trade_price', 0)
                    
                    # 고가 업데이트
                    if 'high_price' in msg:
                        self.high_prices[ticker] = msg['high_price']
                    
                    # 매수 조건 체크
                    if not self.holdings.get(ticker, False):
                        self.check_buy_condition(ticker, current_price)
                    else:
                        # 매도 조건 체크
                        self.check_sell_condition(ticker, current_price)
        except Exception as e:
            logger.error(f"웹소켓 메시지 처리 오류: {e}")
    
    def check_buy_condition(self, ticker: str, current_price: float):
        """매수 조건 확인 및 실행"""
        if ticker not in self.targets or ticker not in self.ma5s:
            return
            
        target = self.targets[ticker]
        ma5 = self.ma5s[ticker]
        
        # 매수 조건:
        # 1. 현재가가 목표가 이상
        # 2. 현재가가 5일 이동평균 이상
        # 3. 보유하지 않은 상태
        if current_price >= target and current_price >= ma5:
            logger.info(f"{ticker} 매수 조건 충족: 현재가 {current_price:,.0f}원, 목표가 {target:,.0f}원")
            
            # 분산 투자 금액 계산
            krw_balance = self.get_krw_balance()
            budget_per_coin = krw_balance / TRADING_CONFIG['coin_nums']
            
            if budget_per_coin < 5000:  # 최소 주문 금액 체크
                logger.warning(f"잔고 부족으로 {ticker} 매수 불가 (가용잔고: {krw_balance:,.0f}원)")
                return
                
            # 매수 주문 실행
            self.execute_buy_order(ticker, budget_per_coin)
    
    def execute_buy_order(self, ticker: str, amount: float):
        """매수 주문 실행"""
        try:
            if TRADING_CONFIG['debug']:
                logger.info(f"[DEBUG] {ticker} 매수 시뮬레이션: {amount:,.0f}원")
                self.holdings[ticker] = True
                self.bought_prices[ticker] = pyupbit.get_current_price(ticker)
                self.max_prices[ticker] = self.bought_prices[ticker]
                return
                
            # 실제 매수 주문
            result = self.upbit.buy_market_order(ticker, amount)
            if 'uuid' in result:
                logger.info(f"{ticker} 매수 주문 성공: {amount:,.0f}원")
                
                # 주문 체결 확인
                time.sleep(1)
                order = self.upbit.get_order(result['uuid'])
                if order and order['state'] == 'done':
                    executed_price = float(order['price'])
                    volume = float(order['executed_volume'])
                    
                    self.holdings[ticker] = True
                    self.bought_prices[ticker] = executed_price
                    self.max_prices[ticker] = executed_price
                    logger.info(f"{ticker} 매수 체결: {volume:.8f}개 @ {executed_price:,.0f}원")
                else:
                    logger.warning(f"{ticker} 매수 체결 확인 실패")
            else:
                logger.error(f"{ticker} 매수 주문 실패: {result}")
        except Exception as e:
            logger.error(f"{ticker} 매수 주문 중 오류: {e}")
    
    def check_sell_condition(self, ticker: str, current_price: float):
        """매도 조건 확인 및 실행"""
        if ticker not in self.bought_prices or self.bought_prices[ticker] == 0:
            return
            
        bought_price = self.bought_prices[ticker]
        profit_rate = (current_price / bought_price) - 1
        
        # 손절 조건 체크 (-5%)
        if profit_rate <= -TRADING_CONFIG['stop_loss']:
            logger.info(f"{ticker} 손절 조건 충족: 수익률 {profit_rate:.2%}")
            self.execute_sell_order(ticker, "손절")
            return
            
        # 트레일링 스탑 조건 체크
        self.max_prices[ticker] = max(self.max_prices[ticker], current_price)
        max_price = self.max_prices[ticker]
        
        if (profit_rate >= TRADING_CONFIG['trailing_stop_min_profit'] and 
            current_price <= max_price * (1 - TRADING_CONFIG['trailing_stop_gap'])):
            logger.info(f"{ticker} 트레일링 스탑 조건 충족: 최고가 {max_price:,.0f}원, 현재가 {current_price:,.0f}원, 수익률 {profit_rate:.2%}")
            self.execute_sell_order(ticker, "트레일링 스탑")
    
    def execute_sell_order(self, ticker: str, reason: str):
        """매도 주문 실행"""
        try:
            volume = self.upbit.get_balance(ticker.split('-')[1])
            if volume == 0:
                logger.warning(f"{ticker} 매도 실패: 보유량 0")
                self.holdings[ticker] = False
                return
                
            if TRADING_CONFIG['debug']:
                logger.info(f"[DEBUG] {ticker} {reason} 매도 시뮬레이션: {volume:.8f}개")
                self.holdings[ticker] = False
                return
                
            # 실제 매도 주문
            result = self.upbit.sell_market_order(ticker, volume)
            if 'uuid' in result:
                logger.info(f"{ticker} {reason} 매도 주문 성공: {volume:.8f}개")
                
                # 주문 체결 확인
                time.sleep(1)
                order = self.upbit.get_order(result['uuid'])
                if order and order['state'] == 'done':
                    executed_price = float(order['price'])
                    logger.info(f"{ticker} {reason} 매도 체결: {volume:.8f}개 @ {executed_price:,.0f}원")
                    self.holdings[ticker] = False
                else:
                    logger.warning(f"{ticker} 매도 체결 확인 실패")
            else:
                logger.error(f"{ticker} 매도 주문 실패: {result}")
        except Exception as e:
            logger.error(f"{ticker} 매도 주문 중 오류: {e}")
    
    def get_krw_balance(self) -> float:
        """KRW 잔고 조회"""
        try:
            balance = self.upbit.get_balance("KRW")
            logger.info(f"현재 KRW 잔고: {balance:,.0f}원")
            return balance
        except Exception as e:
            logger.error(f"잔고 조회 실패: {e}")
            return 0
    
    def close_market(self):
        """장 마감 처리 - 모든 포지션 청산"""
        logger.info("장 마감 처리 시작")
        
        for ticker in self.portfolio:
            if self.holdings.get(ticker, False):
                self.execute_sell_order(ticker, "장 마감")
        
        self.ws_manager.stop()
        self.initialized = False
        logger.info("장 마감 처리 완료")
    
    def run(self):
        """트레이딩 봇 실행"""
        try:
            logger.info("업비트 트레이딩 봇 시작")
            
            while True:
                now = datetime.datetime.now()
                
                # 장 마감 시간 확인 (오전 8:50~59)
                if now.hour == 8 and now.minute >= 50 and self.initialized:
                    logger.info("장 마감 시간 approaching")
                    self.close_market()
                    time.sleep(60)  # 1분 대기
                    continue
                
                # 새로운 거래일 시작 (오전 9:00~9:05)
                if now.hour == 9 and now.minute < 5 and not self.initialized:
                    logger.info("새로운 거래일 시작")
                    if self.initialize_trading_day():
                        # 초기화 성공 시 잔고 확인
                        self.get_krw_balance()
                    time.sleep(60)  # 1분 대기
                    continue
                
                # 30분마다 상태 로깅
                if now.minute % 30 == 0 and now.second == 0:
                    self.log_status()
                
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("사용자에 의해 종료 요청됨")
            self.close_market()
        except Exception as e:
            logger.error(f"치명적 오류 발생: {e}")
            self.close_market()
        finally:
            logger.info("트레이딩 봇 종료")
    
    def log_status(self):
        """현재 상태 로깅"""
        status = {
            "시간": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "포트폴리오": self.portfolio,
            "보유_코인": [ticker for ticker, holding in self.holdings.items() if holding],
            "잔고": self.get_krw_balance()
        }
        logger.info(f"현재 상태: {json.dumps(status, indent=2, ensure_ascii=False)}")

class WebSocketManager:
    """웹소켓 관리 클래스"""
    def __init__(self):
        self.ws = None
        self.thread = None
        
    def start(self, tickers: List[str], callback):
        """웹소켓 시작"""
        if self.ws is not None:
            self.stop()
            
        self.tickers = tickers
        self.callback = callback
        
        # 웹소켓 연결 시작
        self.ws = pyupbit.WebSocketClient(
            "ticker",
            self.tickers,
            qsize=100
        )
        
        # 콜백 설정
        self.ws.on_message = callback
        
        logger.info(f"웹소켓 시작: {len(tickers)}개 코인 모니터링")
    
    def stop(self):
        """웹소켓 중지"""
        if self.ws is not None:
            self.ws.close()
            self.ws = None
            logger.info("웹소켓 중지")

if __name__ == "__main__":
    # API 키 확인
    access_key = os.getenv("UPBIT_ACCESS_KEY")
    secret_key = os.getenv("UPBIT_SECRET_KEY")
    
    if not access_key or not secret_key:
        logger.error("API 키가 설정되지 않았습니다. 환경 변수를 확인하세요.")
        exit(1)
    
    # 트레이딩 봇 실행
    bot = UpbitTradingBot(access_key, secret_key)
    bot.run()