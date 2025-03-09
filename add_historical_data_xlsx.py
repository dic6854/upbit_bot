import pyupbit
import pandas as pd
from datetime import datetime, timedelta
from dateutil.relativedelta import relativedelta
import time
import os

MAX_COUNT = 200

def fetch_ohlcv(ticker, interval, count, to):
    
    if type(to) == str:
        to = datetime.strptime(to, "%Y-%m-%d %H:%M:%S")

    quotient, remainder = divmod(count, MAX_COUNT)
    quotient = int(quotient)
    remainder = int(remainder)

    if quotient == 0 and remainder == 0 :
        print("count is ZERO.")
        return None

    if interval == "minute5":
        to_kst = to - timedelta(minutes=(count*5)) + timedelta(minutes=(remainder*5))
        unit = 5
    elif interval == "minute1":
        to_kst = to - timedelta(minutes=count) + timedelta(minutes=remainder)
        unit = 1
    to_utc = to_kst - timedelta(hours=9)

    df = pd.DataFrame()
    if remainder != 0:
        df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=remainder, to=to_utc)
        df = pd.concat([df, df1])

    if quotient != 0:
        for i in range(quotient):
            to_utc = to_utc + timedelta(minutes=MAX_COUNT * unit)
            df1 = pyupbit.get_ohlcv(ticker, interval=interval, count=MAX_COUNT, to=to_utc)
            df = pd.concat([df, df1])
            print(f"[{i} / {quotient}] - [{ticker}] is finished")
            time.sleep(0.12)

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

def cal_time_differ(start, end):
    time_difference = end - start
    total_minutes, total_seconds = divmod(time_difference.total_seconds(), 60)

    if int(total_seconds) != 0:
        total_minutes += 1
    
    return(int(total_minutes))


def get_data(ticker, interval, start, end):
    total_minutes = cal_time_differ(start, end)

    df = fetch_ohlcv(ticker, interval=interval, count=total_minutes, to=end)

    return df

def add_excel(ticker, m_unit, start_kst, end_kst):
    interval = f"minute{m_unit}"
    file_path_in = f"test/{ticker}.xlsx"
    file_path_out = f"test/{ticker}.xlsx"
    sheet_name = interval

    # 기존 데이터 읽기
    if os.path.exists(file_path_in):
        try:
            old_df = pd.read_excel(io=file_path_in, sheet_name=sheet_name, engine='openpyxl', index_col=0, parse_dates=True)
        except ValueError:  # 시트가 없는 경우
            old_df = pd.DataFrame()
    else:
        old_df = pd.DataFrame()

    start_kst = set_datetime(start_kst)
    if start_kst == False:
        return None
    end_kst1 = set_datetime(end_kst)
    if end_kst1 == False:
        return None
    end_kst = end_kst1 + timedelta(minutes=1)

    # 빈 데이터프레임 처리
    if old_df.empty:
        print(f"{sheet_name}: 기존 데이터가 없음. 전체 기간 데이터를 가져옵니다.")
        df = get_data(ticker, interval, start=start_kst, end=end_kst)
    else:
        # 데이터 기간 확인 및 추가 데이터 요청
        old_start = old_df.index[0].to_pydatetime()
        old_end = old_df.index[-1].to_pydatetime()

        df1 = pd.DataFrame()  # 앞부분 추가 데이터
        df2 = pd.DataFrame()  # 뒷부분 추가 데이터

        if start_kst < old_start:
            print(f"{sheet_name}: 앞부분 데이터 가져오기 ({start_kst} ~ {old_start})")
            df1 = get_data(ticker, interval, start=start_kst, end=old_start)
        if end_kst1 > old_end:
            print(f"{sheet_name}: 뒷부분 데이터 가져오기 ({old_end} ~ {end_kst})")
            df2 = get_data(ticker, interval, start=old_end, end=end_kst)
        
        if df1.empty and df2.empty:
            print(f"{sheet_name}: 이미 포함되어 있습니다. ({start_kst} ~ {old_start})")
            return
        else:
            df = pd.concat([df1, old_df, df2]).sort_index().drop_duplicates()

    with pd.ExcelWriter(path=file_path_out, engine='openpyxl', mode='a', if_sheet_exists='overlay') as writer:
        df.to_excel(writer, sheet_name='minute1', index=True)
    print(f"{file_path_out} 파일의 {sheet_name} 쉬트트 저장 완료!")

    return df


if __name__ == "__main__":
    m_unit = 1
    start_kst = "2024-01-01 00:00:00"
    end_kst   = "2024-01-02 00:00:00"

    ticker = "KRW-BTC"
    add_excel(ticker, m_unit, start_kst, end_kst)

    # krw_tickers = pyupbit.get_tickers(fiat="KRW")

    # for i in range(len(krw_tickers)):
    #     ticker = krw_tickers[i]
    #     add_excel(ticker, interval, start_kst, end_kst)

