# 30일 단순이동평균선 상향 돌파 코인 찾기 : 10_sma_breakout.py

import pyupbit
import pandas as pd
import time
import os

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

    print(f"총 {len(tickers)}개 코인 조회 시작")

    # 결과 저장용 리스트
    breakout_coins = []

    for i, ticker in enumerate(tickers):
        try:
            # 일봉 데이터 가져오기 (32일치, 30일 SMA + 직전 캔들 비교용)
            df = pyupbit.get_ohlcv(ticker, interval="day", count=32)
            if df is None or len(df)<31:
                # print(f"{ticker}: 충분한 데이터 없음")
                continue

            # 현재가 조회
            current_price = pyupbit.get_current_price(ticker)
            if not current_price:
                # print(f"{ticker}: 현재가 조회 실패")
                continue

            # 30일 SMA 계산
            sma30 = df['close'].rolling(window=30).mean()
            curr0_sma30 = sma30.iloc[-1]    # 현재 캔들의 30일 단순이동평균값
            prev1_sma30 = sma30.iloc[-2]    # 직전 캔들의 30일 단순이동평균값
            prev2_sma30 = sma30.iloc[-3]    # 직전 직전 캔들의 30일 단순이동평균값
            prev1_close = df['close'].iloc[-2]  # 직전 캔들 종가
            prev2_close = df['close'].iloc[-3]  # 직전 직전 캔들 종가

            # 상향 돌파 조건: (직전 캔들 종가) >= (직전 캔들의 단순이동평균값) and (직전 직전 캔들 종가) < (직전 직전 캔들의 단순이동평균값)
            if prev1_close >= prev1_sma30 and prev2_close < prev2_sma30 and current_price >= curr0_sma30:
                breakout_coins.append(ticker)
                print(f"[{i}][{ticker}] is appended")
            # else:
            #     print(f"[{i}][{ticker}] is not appended")

            # API 호출 제한 방지
            time.sleep(0.1)

        except Exception as e:
            print(f"{ticker} 처리 중 오류: {e}")
            continue

    print(breakout_coins)