import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time
import os

MAX_COUNT = 200
tt = 1
ct = 1

def fetch_ohlcv(ticker, m_unit, count, to):
    global tt
    global ct

    interval = f"minute{m_unit}"
    if type(to) == str:
        to = datetime.strptime(to, "%Y-%m-%d %H:%M:%S")

    if count == 0 or count < 0:
        print("count 변수가 0이거나 음수입니다.")
        return False
    
    quotient = count // MAX_COUNT
    remainder = count % MAX_COUNT

    to_kst = to - timedelta(minutes=(count*m_unit))
    to_utc = to_kst - timedelta(hours=9)

    df = pd.DataFrame()
    if remainder != 0:
        to_utc = to_utc + timedelta(minutes=(remainder*m_unit))
        df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=remainder, to=to_utc)
        df = pd.concat([df, df1])

    if quotient != 0:
        for i in range(quotient):
            to_utc = to_utc + timedelta(minutes=MAX_COUNT * m_unit)
            df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=MAX_COUNT, to=to_utc)
            df = pd.concat([df, df1])
            print(f"[{ct} / {tt}] - [{i+1} / {quotient}] - [{ticker}] is finished")
            time.sleep(0.12)

    df = df[~df.index.duplicated(keep='last')]
    df = df.sort_index()

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
            return False
    elif isinstance(date, pd.Timestamp):
        return date.to_pydatetime()
    elif isinstance(date, datetime):
        return date
    else:
      print(f"Unsupported date type: {type(date)}")
      return False


def get_count(start, end, m_unit):
    time_difference = end - start
    total_minutes, total_seconds = divmod(time_difference.total_seconds(), 60)

    if int(total_seconds) != 0:
        total_minutes += 1

    count, remainder = divmod(total_minutes, m_unit)
    if int(remainder) != 0:
        count += 1
    
    return(int(count))


def get_data(ticker, m_unit, start, end):
    total_minutes = get_count(start, end, m_unit)
    df = fetch_ohlcv(ticker, m_unit, count=total_minutes, to=end)
    return df


def add_csv(ticker, m_unit, start_kst, end_kst):
    global tt
    global ct

    # interval = f"minute{m_unit}"
    file_path_in = f"cdata/{ticker}_m{m_unit}.csv"
    file_path_out = f"cdata/{ticker}_m{m_unit}.csv"

    # 기존 데이터 읽기
    old_df = pd.DataFrame()
    if os.path.exists(file_path_in):
        old_df = pd.read_csv(file_path_in, index_col=0)
        try:
            old_df.index = pd.to_datetime(old_df.index, format="%Y-%m-%d %H:%M:%S")
        except:
            old_df.index = pd.to_datetime(old_df.index, format="%Y-%m-%d %H:%M")

    start_kst = set_datetime(start_kst)
    if start_kst == False:
        return None
    end_kst1 = set_datetime(end_kst)
    if end_kst1 == False:
        return None
    end_kst = end_kst1 + timedelta(minutes=1)

    if old_df.empty:
        print(f"[{file_path_in} 파일에에 기존 데이터가 없음. 전체 기간 데이터를 가져옵니다.")
        df = get_data(ticker, m_unit, start=start_kst, end=end_kst)
    else:
        old_start = old_df.index[0]
        old_end = old_df.index[-1]

        df1 = pd.DataFrame()  # 앞부분 추가 데이터
        df2 = pd.DataFrame()  # 뒷부분 추가 데이터

        if start_kst < old_start:
            print(f"앞부분 데이터 가져오기 ({start_kst} ~ {old_start})")
            df1 = get_data(ticker, m_unit, start=start_kst, end=old_start)
        if end_kst1 > old_end:
            print(f"뒷부분 데이터 가져오기 ({old_end} ~ {end_kst1})")
            df2 = get_data(ticker, m_unit, start=old_end, end=end_kst)

        if df1.empty and df2.empty:
            print(f"이미 포함되어 있습니다. ({start_kst} ~ {old_start})")
            return True
        else:
            df = pd.concat([df1, old_df, df2]).sort_index().drop_duplicates()

    df.to_csv(file_path_out)
    print(f"{file_path_out} 파일 저장 완료")

    return True


if __name__ == "__main__":
    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    tt = len(krw_tickers)
    ct = 1
    # for i in range(tt):
    for i in range(2, 3):
        ticker = krw_tickers[i]

        start_kst = "2024-01-01 09:00:00"
        end_kst   = "2025-03-16 09:00:00"
        m_unit = 1
        add_csv(ticker, m_unit, start_kst, end_kst)
        start_kst = "2024-01-01 06:00:00"
        end_kst   = "2025-03-16 09:00:00"
        m_unit = 5
        add_csv(ticker, m_unit, start_kst, end_kst)

        print(f"[{ct} / {tt}] - {ticker} 파일 저장 완료")
        ct += 1

        exit()