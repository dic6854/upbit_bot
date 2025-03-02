import pyupbit
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time

MAX_COUNT = 200

def fetch_ohlcv_5min(ticker, interval, count, to_kst):
    unit = 5

    if type(to_kst) == str:
        to_kst = datetime.strptime(to_kst, "%Y-%m-%d %H:%M:%S")
    to_utc = to_kst - timedelta(hours=9)

    quotient, remainder = divmod(count, MAX_COUNT)
    to_go = quotient * MAX_COUNT * unit
    to_utc = to_utc - timedelta(minutes=to_go)
    print(f"to_go : {to_go}, to_utc1 : {to_utc}")

    df = pd.DataFrame()

    if quotient == 0 and remainder == 0 :
        print("count is ZERO.")
        return None

    if remainder != 0:
        df1 = pyupbit.get_ohlcv(ticker, interval="minute5", count=remainder, to=to_utc)
        df = pd.concat([df, df1])

    if quotient != 0:
        for i in range(quotient):
            to_utc = to_utc + timedelta(minutes=MAX_COUNT * unit)
            df1 = pyupbit.get_ohlcv(ticker, interval="minute5", count=MAX_COUNT, to=to_utc)
            df = pd.concat([df, df1])
            time.sleep(0.15)

    return df

if __name__ == "__main__":
    ticker = "KRW-BTC"
    interval = "minute5"
    count = 203
    to_kst = "2025-03-02 18:21:00"

    f_kst = datetime.strptime(to_kst, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=count*5)
    print(f"f_kst : {f_kst}")

    df = fetch_ohlcv_5min(ticker, interval, count, to_kst)
    print(df)

    df.to_csv("mydata.csv", header=False)
    print("CSV 파일 저장 완료!")

    time.sleep(3)

    df.to_csv("mydata.csv", mode='a', header=False)
    print("CSV 파일2 저장 완료!")