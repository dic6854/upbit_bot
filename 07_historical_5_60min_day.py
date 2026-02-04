import os
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
    file_path1 = "60min.xlsx"

    coins = ['BTC', 'XRP', 'ETH', 'ADA']

    for coin in coins:
        ticker = "KRW-" + coin
        df = get_historical_data(ticker, interval="minute60", to_date="2026-02-03 19:00:00", from_date="2020-01-01 00:00:00")

        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df_filled = df.asfreq('h').ffill()

        df_filled.index.name = 'date'
        df_filled = df_filled.reset_index()
        # df_filled.rename(columns={'index': 'date'}, inplace=True)
        df_filled['date'] = df_filled['date'].astype('string')

        # 1. 파일이 존재하는지 확인
        if not os.path.exists(file_path1):
            # 파일이 없으면 'w' 모드(새로 만들기)로 저장
            df_filled.to_excel(file_path1, index=False, sheet_name=coin)
            print(f"{file_path1} 파일을 새로 생성했습니다.")
        else:
            # 파일이 있으면 'a' 모드(추가하기)로 실행
            with pd.ExcelWriter(file_path1, engine='openpyxl', mode='a', if_sheet_exists='replace') as writer:
                df_filled.to_excel(writer, index=False, sheet_name=coin)
            print(f"{file_path1} 파일에 {coin} 시트를 업데이트했습니다.")
