import pyupbit
import pandas as pd
import ta

total_tickers = 0
current_ticker = 0

def add_bollinger_macd_rsi(ticker, interval):
    # 데이터 불러오기
    file = f"mydata/{ticker}.xlsx"
    df = pd.read_excel(file, index_col=0, parse_dates=True, engine='openpyxl')
    df = df.sort_index()  # 날짜 순서 정렬
    df = df.groupby(df.index).last()  # 날짜가 중복된 경우 뒤의 것을 유지하고 앞을 것을 삭제한다.

    # 기술적 지표 추가
    # 볼린저 밴드
    df['BB_Middle'] = ta.volatility.bollinger_mavg(df['close'], window=20)
    df['BB_Upper'] = ta.volatility.bollinger_hband(df['close'], window=20, window_dev=2)
    df['BB_Lower'] = ta.volatility.bollinger_lband(df['close'], window=20, window_dev=2)

    print(f"Bollinger Band Indicators oF {ticker} are calculated.")

    # MACD
    df['MACD_26_12'] = ta.trend.macd(df['close'], window_slow=26, window_fast=12)
    df['MACD_Signal_26_12_9'] = ta.trend.macd_signal(df['close'], window_slow=26, window_fast=12, window_sign=9)

    print(f"MACD oF {ticker} are calculated.")

    # RSI
    df['RSI_14'] = ta.momentum.rsi(df['close'], window=14)

    print(f"RSI oF {ticker} are calculated.")

    file_name = f"data/{ticker}.xlsx"
    sheet_name = interval
    df.to_excel(excel_writer=file_name, sheet_name=sheet_name, index=True)
    print(f"[{current_ticker} - {total_tickers}]{file_name} 파일의 {sheet_name} 쉬트트 저장 완료!")

if __name__ == "__main__":
    interval = "minute5"

    krw_tickers = pyupbit.get_tickers(fiat="KRW")
    total_tickers = len(krw_tickers)

    for i in range(len(krw_tickers)):
        current_ticker = i+1
        ticker = krw_tickers[i]
        add_bollinger_macd_rsi(ticker, interval)
