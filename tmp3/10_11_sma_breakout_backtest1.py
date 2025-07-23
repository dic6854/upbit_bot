# 30일 단순이동평균선 상향 돌파 코인 찾기 : 10_sma_breakout.py

import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time
import logging

# 로깅 설정
logging.basicConfig(
    filename="sma_breakout_log.txt",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'
)


def find_sma_breakout_coins(date_str):
    """30일 SMA 상향 돌파 코인 검색"""

    # 모든 KRW 마켓 티커 가져오기
    tickers = pyupbit.get_tickers(fiat="KRW")

    t_coins = len(tickers)
    logging.info(f"총 {t_coins}개 코인 조회 시작")
    print(f"총 {t_coins}개 코인 조회 시작")

    # 결과 저장용 리스트
    breakout_coins = []

    i = 1
    for ticker in tickers:
        try:
            # 일봉 데이터 가져오기 (32일치, 30일 SMA + 직전 캔들 비교용)
            df = pyupbit.get_ohlcv(ticker, interval="day", count=32, to=date_str)
            if df is None or len(df)<32:
                logging.warning(f"{ticker}: 충분한 데이터 없음")
                continue
        
            # 30일 SMA 계산
            sma30 = df['close'].rolling(window=30).mean()

            current_price = df['close'].iloc[-1]
            curr0_sma30 = sma30.iloc[-1]    # 현재 캔들의 30일 단순이동평균값
            prev1_sma30 = sma30.iloc[-2]    # 직전 캔들의 30일 단순이동평균값
            prev2_sma30 = sma30.iloc[-3]    # 직전 직전 캔들의 30일 단순이동평균값
            prev1_close = df['close'].iloc[-2]  # 직전 캔들 종가
            prev2_close = df['close'].iloc[-3]  # 직전 직전 캔들 종가

            # 상향 돌파 조건: (직전 캔들 종가) >= (직전 캔들의 30단순이평값) and (직전 직전 캔들 종가) < (직전 직전 캔들의 30단순이평값) and (현재 캔들 종가) >= (현재 캔들의 30단순이평선)
            if prev1_close >= prev1_sma30 and prev2_close < prev2_sma30 and current_price >= curr0_sma30:
                breakout_coins.append({
                    'date': date_str,
                    'ticker': ticker,
                    'curr0_sma30': float(curr0_sma30),
                    'prev1_sma30': float(prev1_sma30),
                    'prev2_sma30': float(prev2_sma30),
                    'current_price': float(current_price),
                    'prev1_close': float(prev1_close),
                    'prev2_close': float(prev2_close)                   
                })

            # API 호출 제한 방지
            time.sleep(0.1)

            print(f"[{date_str}][{i}/{t_coins}] is checked.")
            i += 1

        except Exception as e:
            logging.error(f"{ticker} 처리 중 오류: {e}")
            continue

    return breakout_coins


if __name__ == "__main__":
    start_date_str = "2025-07-01 09:00:00"
    end_date_str = "2025-07-02 09:00:00"

    start_date = datetime.strptime(start_date_str, "%Y-%m-%d %H:%M:%S")
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d %H:%M:%S")

    one_day = timedelta(days=1)

    current_date = start_date

    total_breakout_coins = []

    while current_date <= end_date:
    # 코인 검색
        breakout_coins = find_sma_breakout_coins(date_str=current_date.strftime("%Y-%m-%d %H:%M:%S"))

        total_breakout_coins.append(breakout_coins)

        current_date += one_day
    
    print(total_breakout_coins)

