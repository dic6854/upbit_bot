import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time
import os
# import talib

MAX_COUNT = 200
tt = 1
ct = 1

def fetch_ohlcv(ticker, unit, count, to):
    global tt
    global ct

    interval = f"minute{unit}"
    if type(to) == str:
        to = datetime.strptime(to, "%Y-%m-%d %H:%M:%S")

    if count == 0 or count < 0:
        print("count 변수가 0이거나 음수입니다.")
        return False
    
    quotient = count // MAX_COUNT
    remainder = count % MAX_COUNT

    to_kst = to - timedelta(minutes=(count*unit))
    to_utc = to_kst - timedelta(hours=9)

    df = pd.DataFrame()
    if remainder != 0:
        to_utc = to_utc + timedelta(minutes=(remainder*unit))
        df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=remainder, to=to_utc)
        df = pd.concat([df, df1])

    if quotient != 0:
        for i in range(quotient):
            to_utc = to_utc + timedelta(minutes=MAX_COUNT * unit)
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


def get_count(start, end, unit):
    delta = end - start
    total_minutes, total_seconds = divmod(delta.total_seconds(), 60)

    if int(total_seconds) != 0:
        total_minutes += 1

    count, remainder = divmod(total_minutes, unit)
    if int(remainder) != 0:
        count += 1
    
    return(int(count))


def get_data(ticker, m_unit, start, end):
    total_minutes = get_count(start, end, m_unit)
    df = fetch_ohlcv(ticker, m_unit, count=total_minutes, to=end)
    return df


def add_df(ticker, unit, start_kst, end_kst):
    file_name = f"adata/{ticker}_m{unit}.csv"

    # 기존 데이터 읽기
    old_df = pd.DataFrame()
    if os.path.exists(file_name):
        old_df = pd.read_csv(file_name, index_col=0)
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
        # print(f"[{file_name} 파일에에 기존 데이터가 없음. 전체 기간 데이터를 가져옵니다.")
        df = get_data(ticker, unit, start=start_kst, end=end_kst)
    else:
        old_start = old_df.index[0]
        old_end = old_df.index[-1]

        df1 = pd.DataFrame()  # 앞부분 추가 데이터
        df2 = pd.DataFrame()  # 뒷부분 추가 데이터

        if start_kst < old_start:
            # print(f"앞부분 데이터 가져오기 ({start_kst} ~ {old_start})")
            df1 = get_data(ticker, unit, start=start_kst, end=old_start)
        if end_kst1 > old_end:
            # print(f"뒷부분 데이터 가져오기 ({old_end} ~ {end_kst1})")
            df2 = get_data(ticker, unit, start=old_end, end=end_kst)

        if df1.empty and df2.empty:
            # print(f"이미 포함되어 있습니다. ({start_kst} ~ {old_start})")
            df = old_df
        else:
            df = pd.concat([df1, old_df, df2]).sort_index().drop_duplicates()

    return df


def fill_data(df, unit):
    df = df.sort_index()
    df = df.drop_duplicates(keep='last')

    start_datetime = df.index[0]
    end_datetime = df.index[-1]

    unit_m = f"{unit}min"
    expected_index = pd.date_range(start=start_datetime, end=end_datetime, freq=unit_m)
    df = df.reindex(expected_index, method='ffill')

    return df


# def set_indicator(df):
#     # 5, 20 SMA 계산 (5분봉 기준)
#     df['SMA5'] = talib.SMA(df['close'], timeperiod=5)
#     df['SMA20'] = talib.SMA(df['close'], timeperiod=20)

#     return df

if __name__ == "__main__":

    start_kst = datetime(2024, 1, 1, 6, 0, 0)
    end_kst = datetime(2025, 3, 18, 9, 0, 0)

    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    tt = len(krw_tickers)
    
    # for i in range(tt): KRW-ME
    for i in range(148, tt):
        ct = i + 1
        ticker = krw_tickers[i]

        for j in range(1, 6, 4):
            unit = j
            df = add_df(ticker, unit, start_kst, end_kst)
            print(f"[{ct} / {tt}] - [{ticker}] - 업비트로부터 데이터 읽기 완료")
            df = fill_data(df, unit)
            print(f"[{ct} / {tt}] - [{ticker}] - 데이터 채우기 검증 완료")

            if unit == 5:
                # df = set_indicator(df)
                print(f"[{ct} / {tt}] - [{ticker}] - 5분봉 5, 20 SMA 지표 설정 완료")

            file_name = f"adata/{ticker}_m{unit}.csv"
            df.to_csv(file_name)

        print(f"[{ct} / {tt}] - [{ticker}] 파일 저장 완료")

