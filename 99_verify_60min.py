import pyupbit
import pandas as pd
from datetime import datetime, timedelta

def __convert_to_utc_str(my_date):
    if my_date is None:
        my_date_dt = datetime.now()
    elif " " in my_date or "T" in my_date:
        my_date_dt = datetime.strptime(my_date, "%Y-%m-%d %H:%M:%S")
    else:
        my_date = my_date + " 09:00:00"
        my_date_dt = datetime.strptime(my_date, "%Y-%m-%d %H:%M:%S")

    my_date_utc_dt = my_date_dt - timedelta(hours=9) + timedelta(seconds=1)
    my_date_utc_str = my_date_utc_dt.strftime("%Y-%m-%d %H:%M:%S")

    return my_date_utc_str


file_path = 'Coin_60min.xlsx'
sheets = {
    'BTC': 'BTC',
    'XRP': 'XRP',
    'ETH': 'ETH',
    'ADA': 'ADA'
}

for coin, sheet_name in sheets.items():
    df = pd.read_excel(file_path, sheet_name=sheet_name)

    df['date'] = pd.to_datetime(df['date'])
    df = df.set_index('date')

    df_filled = df.asfreq('h').ffill()




    full_range = pd.date_range(start=df_filled.index.min(), end=df_filled.index.max(), freq='h')

    # 4. 실제 인덱스와 비교하여 빠진 시간대 찾기
    missing_times = full_range.difference(df_filled.index)

    # ticker = "KRW-" + coin

    # for missing_time in missing_times:
    #     missing_time_str = missing_time.strftime('%Y-%m-%d %H:%M:%S')
    #     print(f'missing_time_str = {missing_time_str}')
    #     missing_time_str_utc = __convert_to_utc_str(missing_time_str)
    #     print(f'missing_time_str_utc = {missing_time_str_utc}')
    #     df = pyupbit.get_ohlcv(ticker, interval="minute60", to=missing_time_str_utc, count=2)
    #     print(df)
    #     exit()
    
    

    print(f"COIN = {coin}")
    print(f"    빠진 시간대 개수: {len(missing_times)}")
    print("    빠진 시간대 목록:")
    print(missing_times)    