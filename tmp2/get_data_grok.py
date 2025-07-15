import pandas as pd
import pyupbit
import datetime
from datetime import datetime, timedelta
import time
import os

# 날짜 지정을 datetime 데이터 타입으로 변환
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

# Upbit 데이터 가져오기 함수 (공통 함수)
def fetch_upbit_data(start_time, end_time, interval='minute1', file_path="KRW-BTC.xlsx", sheet_name="minute1"):
    """
    interval: 'minute1' 또는 'minute5'로 설정
    start_time, end_time: 데이터 요청 시작/종료 시간 (datetime 객체)
    file_path: 엑셀 파일 경로
    sheet_name: 저장할 시트 이름
    """
    # 기존 데이터 읽기
    if os.path.exists(file_path):
        try:
            df = pd.read_excel(io=file_path, sheet_name=sheet_name, engine='openpyxl', index_col=0, parse_dates=True)
        except ValueError:  # 시트가 없는 경우
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()

    # 지정된 기간 설정
    start_time = pd.Timestamp(start_time)
    end_time = pd.Timestamp(end_time)

    # 빈 데이터프레임 처리
    if df.empty:
        print(f"{sheet_name}: 기존 데이터가 없음. 전체 기간 데이터를 가져옵니다.")
        df_new = fetch_upbit_period_data(start_time, end_time, interval)
        save_to_excel(df_new, file_path, sheet_name)
        return df_new

    # 데이터 기간 확인 및 추가 데이터 요청
    df_start = df.index.min()
    df_end = df.index.max()

    df1 = pd.DataFrame()  # 앞부분 추가 데이터
    df2 = pd.DataFrame()  # 뒷부분 추가 데이터

    if start_time < df_start:
        print(f"{sheet_name}: 앞부분 데이터 가져오기 ({start_time} ~ {df_start})")
        df1 = fetch_upbit_period_data(start_time, df_start, interval)

    if end_time > df_end:
        print(f"{sheet_name}: 뒷부분 데이터 가져오기 ({df_end} ~ {end_time})")
        df2 = fetch_upbit_period_data(df_end, end_time, interval)

    # 데이터 병합
    if not df1.empty or not df2.empty:
        df_combined = pd.concat([df1, df, df2]).sort_index().drop_duplicates()
        save_to_excel(df_combined, file_path, sheet_name)
        return df_combined

    print(f"{sheet_name}: 지정된 기간 내 데이터가 이미 존재함.")
    return df[(df.index >= start_time) & (df.index <= end_time)]

# Upbit API로 특정 기간 데이터 가져오기 (200개 제한 고려)
def fetch_upbit_period_data(start_time, end_time, interval):
    """
    Upbit에서 과거 데이터를 200개 단위로 가져오는 함수
    """
    dfs = []
    current_time = end_time
    count_per_request = 200

    while current_time > start_time:
        # 요청할 데이터 개수 계산
        time_diff = (current_time - start_time).total_seconds() / 60
        if interval == 'minute5':
            time_diff /= 5
        requests_needed = min(count_per_request, int(time_diff) + 1)

        # 데이터 요청
        df_chunk = pyupbit.get_ohlcv(ticker="KRW-BTC", interval=interval, to=current_time, count=requests_needed)
        if df_chunk is None or df_chunk.empty:
            break

        dfs.append(df_chunk)
        current_time = df_chunk.index.min() - timedelta(minutes=1 if interval == 'minute1' else 5)

        # API 호출 제한을 고려한 대기 (필요 시 추가)
        time.sleep(0.15)

    # 데이터 병합
    if dfs:
        df_combined = pd.concat(dfs).sort_index().drop_duplicates()
        df_combined.index.name = 'timestamp'
        return df_combined[['open', 'high', 'low', 'close', 'volume']]
    return pd.DataFrame()

# 엑셀 파일에 저장
def save_to_excel(df, file_path, sheet_name):
    with pd.ExcelWriter(file_path, mode='a' if os.path.exists(file_path) else 'w', engine='openpyxl', if_sheet_exists='replace') as writer:
        df.to_excel(writer, sheet_name=sheet_name)
    print(f"{sheet_name}: 데이터가 {file_path}에 저장됨.")

# 메인 실행
def main(ticker, start, end):
    start_kst = set_datetime(start)
    if start_kst == False:
        return None
    end_kst = set_datetime(end)
    if end_kst == False:
        return None
    
    start_time = start_kst - timedelta(hours=9)
    end_time = end_kst - timedelta(hours=9)

    # 엑셀파일 이름 지정
    file_path = f"test/{ticker}.xlsx"

    # 1분봉 데이터 처리
    df_minute1 = fetch_upbit_data(start_time, end_time, interval='minute1', file_path=file_path, sheet_name="minute1")
    print("1분봉 데이터 크기:", df_minute1.shape)

    # 5분봉 데이터 처리
    df_minute5 = fetch_upbit_data(start_time, end_time, interval='minute5', file_path=file_path, sheet_name="minute5")
    print("5분봉 데이터 크기:", df_minute5.shape)

if __name__ == "__main__":
    ticker = "KRW-BTC"
    start = "2023-01-01 09:00:00"
    end = "2025-03-08 20:01:00"
    main(ticker, start, end)