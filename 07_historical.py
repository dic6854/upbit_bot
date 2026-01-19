import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time

def get_historical_data(ticker, interval="minute5", to_date=None, from_date=None):
    all_data = pd.DataFrame()

    if to_date is None:
        to_date = datetime.now() - timedelta(hours=9) + timedelta(seconds=1)
        to_date = to_date.strftime("%Y-%m-%d %H:%M:%S")
    elif " " in to_date or "T" in to_date:
        date_obj = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")
        date_utc = date_obj - timedelta(hours=9) + timedelta(seconds=1)
        to_date = date_utc.strftime("%Y-%m-%d %H:%M:%S")
    else:
        date_obj = to_date + " 09:00:00"
        date_obj = datetime.strptime(date_obj, "%Y-%m-%d %H:%M:%S")
        date_utc = date_obj - timedelta(hours=9) + timedelta(seconds=1)
        to_date = date_utc.strftime("%Y-%m-%d %H:%M:%S")

    print(to_date)

if __name__ == "__main__":
    ticker = "KRW-BTC"

    get_historical_data(ticker, to_date="2026-01-19 20:59:37")

    '''
    date_obj = datetime.strptime(to_date, "%Y-%m-%d %H:%M:%S")
    print(date_obj)

    date_utc = date_obj - timedelta(hours=9) + timedelta(seconds=1)
    date_ytc_str = date_utc.strftime("%Y-%m-%d %H:%M:%S")


    while True:
        data = pyupbit.get_ohlcv(ticker, interval=interval, to=to)
        if data is None or data.empty:
            break
        all_data = pd.concat([data, all_data])
        to = (data.index[0] - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
        time.sleep(0.2)  # API rate limit 고려

    return all_data
    '''

'''
date_str = "2026-01-19"
date_obj = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
print(date_obj)

date_utc = date_obj - timedelta(hours=9) + timedelta(seconds=1)
date_ytc_str = date_utc.strftime("%Y-%m-%d %H:%M:%S")

date_obj_end = date_obj - timedelta(minutes=1000)
print(date_obj_end)

df = pyupbit.get_ohlcv(ticker="KRW-BTC", interval="minute5", to=date_ytc_str)
print(df)

f_index = df.index[0]
f_index_utc = f_index - timedelta(hours=9) - timedelta(seconds=1)
f_index_utc_str = f_index_utc.strftime("%Y-%m-%d %H:%M:%S")
print(f_index_utc_str)

df = pyupbit.get_ohlcv(ticker="KRW-BTC", interval="minute5", to=f_index_utc_str)
print(df)

def get_historical_data(ticker, interval="minute5", to=None, count=999):
    all_data = pd.DataFrame()
    to = None

    while True:
        data = pyupbit.get_ohlcv(ticker, interval=interval, to=to, count=count)
        if data is None or data.empty:
            break
        all_data = pd.concat([data, all_data])
        to = (data.index[0] - timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")
        time.sleep(0.2)  # API rate limit 고려

    return all_data

ticker = "KRW-BTC"

# 최근 3년치 정도 가져오려면 이렇게
df = pyupbit.get_ohlcv(ticker, interval="day", count=999) # 최대한 많이

# 또는 특정 날짜부터 그 이전 데이터를 최대한 많이 가져오기
# df = pyupbit.get_ohlcv(ticker, "day", to="2024-01-01", count=999)

print(df)
'''