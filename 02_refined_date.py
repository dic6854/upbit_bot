import pyupbit
import pandas as pd
from datetime import datetime, time, timedelta

def fill_data(ticker):
    for i in range(1, 6, 4):
        file_name = f"cdata/{ticker}_m{i}.csv"

        df = pd.read_csv(file_name, index_col=0)
        try:
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M:%S")
        except:
            df.index = pd.to_datetime(df.index, format="%Y-%m-%d %H:%M")

        df = df.sort_index()
        df = df.drop_duplicates(keep='last')

        start_datetime = df.index[0]
        end_datetime = df.index[-1]

        unit_m = f"{i}min"
        expected_index = pd.date_range(start=start_datetime, end=end_datetime, freq=unit_m)
        df = df.reindex(expected_index, method='ffill')

        df.to_csv(file_name)

        print(f"[ {ct} / {tt} ] - {file_name} 파일 저장 완료")


if __name__ == "__main__":
    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    tt = len(krw_tickers)
    ct = 1
    for i in range(tt):
        ticker = krw_tickers[i]
        fill_data(ticker)

        ct += 1