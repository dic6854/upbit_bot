import pyupbit
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import os

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

def set_datetime(date: str | pd.Timestamp | datetime | None) -> datetime:
    if date is None:
        date = datetime.now()
        date_format = "%Y-%m-%d %H:%M:%S"
        date = datetime.strftime(date, date_format)
        date = datetime.strptime(date, date_format)
        return date
    elif isinstance(date, str):
        try:
            return pd.to_datetime(date).to_pydatetime()
        except ValueError:
            print(f"Invalid date string: {date}")
            return -1
    elif isinstance(date, pd.Timestamp):
        return date.to_pydatetime()
    elif isinstance(date, datetime):
        return date
    else:
      print(f"Unsupported date type: {type(date)}")
      return -2

def save_csv(ticker, interval, count, start_kst, end_kst):
    start_kst = set_datetime(start_kst)
    end_kst = set_datetime(end_kst)

    time_difference = end_kst - start_kst
    total_minutes = time_difference.total_seconds()/60




if __name__ == "__main__":
    ticker = "KRW-BTC"
    interval = "minute5"
    count = 203
    to_kst = "2025-03-02 18:21:00"

    f_kst = datetime.strptime(to_kst, "%Y-%m-%d %H:%M:%S") - timedelta(minutes=count*5)
    print(f"f_kst : {f_kst}")

    df = fetch_ohlcv_5min(ticker, interval, count, to_kst)
    print(df)

    file_path = "hdata/mydata1.csv"
    if os.path.exists(file_path):
        os.remove(file_path)

    df.to_csv("hdata/mydata1.csv", mode='a', header=False)
    print("CSV 파일 저장 완료!")

    time.sleep(3)

    df.to_csv("hdata/mydata1.csv", mode='a', header=False)
    print("CSV 파일2 저장 완료!")