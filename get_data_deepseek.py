import pandas as pd
import numpy as np
import pyupbit
from datetime import datetime, timedelta
import openpyxl

# 데이터를 엑셀 파일에 저장하는 함수
def save_to_excel(file_path, df, sheet_name):
    try:
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
            df.to_excel(writer, sheet_name=sheet_name)
    except FileNotFoundError:
        with pd.ExcelWriter(file_path, engine='openpyxl', mode='w') as writer:
            df.to_excel(writer, sheet_name=sheet_name)

# 데이터 처리 함수
def process_data(file_path, sheet_name, start_date, end_date, interval):
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name, index_col=0)
        df.index = pd.to_datetime(df.index)
    except (FileNotFoundError, ValueError):
        print(f"{file_path} 파일 또는 '{sheet_name}' 시트가 존재하지 않습니다. 빈 DataFrame으로 초기화합니다.")
        df = pd.DataFrame()  # 파일 또는 시트가 없으면 빈 DataFrame으로 설정

    # df가 비어있는 경우
    if df.empty:
        print(f"빈 DataFrame입니다. 지정된 기간 전체를 업비트에서 불러옵니다. (시트: {sheet_name})")
        df = pyupbit.get_ohlcv("KRW-BTC", interval=interval, to=end_date, count=None)
        df = df[df.index >= start_date]
    else:
        # df 데이터의 첫 번째와 마지막 날짜 확인
        df_start = df.index[0]
        df_end = df.index[-1]

        # 앞쪽 데이터가 부족한 경우 (지정된 시작일이 df의 첫 번째 데이터보다 앞인 경우)
        if start_date < df_start:
            print(f"앞쪽 데이터가 부족합니다. 업비트에서 데이터를 불러옵니다. (시트: {sheet_name})")
            df1 = pyupbit.get_ohlcv("KRW-BTC", interval=interval, to=df_start, count=None)
            df1 = df1[df1.index >= start_date]
            df = pd.concat([df1, df])  # df1을 df 앞에 추가

        # 뒤쪽 데이터가 부족한 경우 (지정된 종료일이 df의 마지막 데이터보다 뒤인 경우)
        if end_date > df_end:
            print(f"뒤쪽 데이터가 부족합니다. 업비트에서 데이터를 불러옵니다. (시트: {sheet_name})")
            df2 = pyupbit.get_ohlcv("KRW-BTC", interval=interval, to=end_date, count=None)
            df2 = df2[df2.index > df_end]
            df = pd.concat([df, df2])  # df2를 df 뒤에 추가

    # 지정된 기간으로 데이터 필터링
    df = df[(df.index >= start_date) & (df.index <= end_date)]

    # 데이터를 엑셀 파일에 저장
    save_to_excel(file_path, df, sheet_name)
    print(f"{sheet_name} 시트 데이터 저장 완료.")

# 메인 로직
file_path = "KRW-BTC.xlsx"
start_date = datetime(2023, 1, 1, 9, 0, 0)  # 예시 시작일
end_date = datetime(2025, 3, 8, 9, 0, 0)    # 예시 종료일

# 1분봉 데이터 처리
process_data(file_path, "minute1", start_date, end_date, interval='minute1')

# 5분봉 데이터 처리
process_data(file_path, "minute5", start_date, end_date, interval='minute5')