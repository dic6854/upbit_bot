import pyupbit
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import os

MAX_COUNT = 200
UNIT = 5

def fetch_ohlcv_5min(ticker, interval, count, to_kst, tc, ct):
    if type(to_kst) == str:
        to_kst = datetime.strptime(to_kst, "%Y-%m-%d %H:%M:%S")

    quotient, remainder = divmod(count, MAX_COUNT)
    quotient = int(quotient)
    remainder = int(remainder)

    if quotient == 0 and remainder == 0 :
        print("count is ZERO.")
        return None

    to_go_kst = to_kst - timedelta(minutes=(count * UNIT)) + timedelta(minutes=(remainder * UNIT))
    to_utc = to_go_kst - timedelta(hours=9)
    
    df = pd.DataFrame()
    if remainder != 0:
        df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=remainder, to=to_utc)
        df = pd.concat([df, df1])

    if quotient != 0:
        for i in range(quotient):
            to_utc = to_utc + timedelta(minutes=MAX_COUNT * UNIT)
            df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=MAX_COUNT, to=to_utc)
            df = pd.concat([df, df1])
            print(f"[{ct} / {tc}] - [{i} / {quotient}] finished")
            time.sleep(0.15)

    return df

def file_remove(fname):
    if os.path.exists(fname):  # 파일이 존재하는지 확인
        try:
            os.remove(fname)  # 파일 삭제 시도
            print(f"{fname} 파일 삭제 성공")
            return True
        except PermissionError:
            print(f"{fname} 파일 삭제 권한 없음")
            return False
        except OSError as e:
            print(f"파일 삭제 중 오류 발생: {e}")
            return False
    else:
        print(f"{fname} 파일 없음")
        return True

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
      return -1

def save_csv(ticker, interval, start_kst, end_kst, fn, fmode, tc, ct):
    start_kst = set_datetime(start_kst)
    if start_kst == -1:
        return None
    end_kst = set_datetime(end_kst)
    if end_kst == -1:
        return None

    time_difference = end_kst - start_kst
    total_minute1, total_second = divmod(time_difference.total_seconds(), 60)
    if total_second != 0:
        total_minute1 += 1
    total_minute5, total_minute_remain = divmod(total_minute1, UNIT)
    if total_minute_remain != 0:
        total_minute5 += 1

    df = fetch_ohlcv_5min(ticker, interval=interval, count=total_minute5, to_kst=end_kst, tc=tc, ct=ct)

    df.index = df.index.strftime('%Y-%m-%d %H:%M')
    df['open'] = df['open'].round(6)
    df['high'] = df['high'].round(6)
    df['low'] = df['low'].round(6)
    df['close'] = df['close'].round(6)
    df['volume'] = df['volume'].round(8)
    df['value'] = df['value'].round(6)

    if fmode == True:
        file_remove(fn)

    df.to_csv(path_or_buf=fn, mode='a')
    # df.to_csv(path_or_buf=fn, mode='a')
    print(f"{fn} 파일 저장 완료!")



if __name__ == "__main__":
    interval="minute5"
    start_kst="2024-01-01 08:59:00"
    end_kst="2025-03-03 18:21:00"

    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    t_coin = len(krw_tickers)

    ct = 1
    for krw_ticker in krw_tickers:
        ticker = krw_ticker
        coin = ticker.split("-")[1]
        fn = f"hdata/{coin}_m5.csv"
        save_csv(ticker, interval, start_kst, end_kst, fn, fmode=True, tc=t_coin, ct=ct)
        ct += 1

