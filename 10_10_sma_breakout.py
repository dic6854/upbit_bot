# 30일 단순이동평균선 상향 돌파 코인 찾기 : 10_sma_breakout.py

import pyupbit
import pandas as pd
import os
import time
import logging

# 로깅 설정
logging.basicConfig(
    filename="sma_breakout_log.txt",
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)


def get_keys():
    access_key = os.environ['UPBIT_ACCESS_KEY']
    secret_key = os.environ['UPBIT_SECRET_KEY']

    return access_key, secret_key



if __name__ == "__main__":
    # 로그인
    myAccess_key, mySecret_key = get_keys()
    upbit = pyupbit.Upbit(access=myAccess_key, secret=mySecret_key)

    # 모든 KRW 마켓 티커 가져오기
    tickers = pyupbit.get_tickers(fiat="KRW")

    logging.info(f"총 {len(tickers)}개 코인 조회 시작")
    print(f"총 {len(tickers)}개 코인 조회 시작")

    # 결과 저장용 리스트
    breakout_coins = []

    for ticker in tickers:
        try:
            # 일봉 데이터 가져오기 (31일치, 30일 SMA + 직전 캔들 비교용)
            df = pyupbit.get_ohlcv(ticker, interval="day", count=31)
            if df is None or len(df)<31:
                logging.warning(f"{ticker}: 충분한 데이터 없음")
                continue
        
            # 현재가 조회
            current_price = pyupbit.get_current_price(ticker)
            if not current_price:
                logging.warning(f"{ticker}: 현재가 조회 실패")
                continue
        
            # 30일 SMA 계산
            sma30 = df['close'].rolling(window=30).mean()
            curr_sma30 = sma30.iloc[-1]
            prev_sma30 = sma30.iloc[-2]
            prev_close = df['close'].iloc[-2]   # 직전 캔들 종가

            # 상향 돌파 조건: 현재가 >= 당일의 SMA30값 and 직전 종가 < 직전일의 SMA30값
            if current_price >= curr_sma30 and prev_close < prev_sma30:
                # 가격 상승률 계산 (직전 종가 대비)
                price_change = ((current_price - prev_close) / prev_close) * 100

                breakout_coins.append({
                    'ticker': ticker,
                    'current_price': current_price,
                    'sma30': sma30,
                    'prev_close': prev_close,
                    'price_change': price_change
                })

                logging.info(f"{ticker}: SMA 상향 돌파 - 현재가: {current_price:,.0f}원, "
                             f"SMA30: {sma30:,.0f}원, 직전 종가: {prev_close:,.0f}원, "
                             f"상승률: {price_change:.2f}%")

            # API 호출 제한 방지
            time.sleep(0.1)

        except Exception as e:
            logging.error(f"{ticker} 처리 중 오류: {e}")
            continue

    print(breakout_coins)
    # return breakout_coins

