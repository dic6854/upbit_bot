import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time

def __convert_to_utc_str(my_date):
    if my_date is None:
        my_date_dt = datetime.now()
    elif " " in my_date or "T" in my_date:
        my_date_dt = datetime.strptime(my_date, "%Y-%m-%d %H:%M:%S")
    else:
        my_date = my_date + " 09:00:00"
        my_date_dt = datetime.strptime(my_date, "%Y-%m-%d %H:%M:%S")

    my_date_utc_dt = my_date_dt - timedelta(hours=9)
    my_date_utc_str = my_date_utc_dt.strftime("%Y-%m-%d %H:%M:%S")

    return my_date_utc_str


def get_historical_data(ticker, interval, to_date=None, from_date=None):
    all_data = pd.DataFrame()

    to_date_utc_str = __convert_to_utc_str(to_date)

    i = 1
    while True:
        df = pyupbit.get_ohlcv(ticker, interval=interval, to=to_date_utc_str)

        if df is None or df.empty:
            break

        first_index_kst_dt = df.index[0]
        first_index_kst_str = first_index_kst_dt.strftime("%Y-%m-%d %H:%M:%S")
        first_index_utc_dt = first_index_kst_dt - timedelta(hours=9)
        first_index_utc_str = first_index_utc_dt.strftime("%Y-%m-%d %H:%M:%S")

        print(f'[{i}] first_index = {first_index_kst_str}, from_date = {from_date}')
        i += 1

        if first_index_kst_str < from_date:
            all_data = pd.concat([df, all_data])
            break

        all_data = pd.concat([df, all_data])
        to_date_utc_str = first_index_utc_str
        time.sleep(0.2)  # API rate limit 고려

    all_data.sort_index(ascending=True, inplace=True)
    all_data.index.name = 'date'        # 1. 인덱스 이름 설정   
    all_data.reset_index(inplace=True)  # 2. 인덱스를 컬럼으로 이동 (inplace=True로 원본 변경)
    all_data['date'] = all_data['date'].astype('string')  # 3. date 컬럼을 문자열로 변환
    all_data = all_data[all_data['date'] >= from_date].reset_index(drop=True)
    return all_data

    
if __name__ == "__main__":
    ticker = "KRW-BTC"

    df = get_historical_data(ticker, interval="minute5", to_date="2026-01-28 09:00:00", from_date="2024-01-01 09:00:00")

    df.to_excel("코인_5분봉_org.xlsx", index=False, sheet_name="비트코인")
    print("저장완료!")
