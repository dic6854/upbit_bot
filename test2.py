import pandas as pd
import time
from datetime import datetime
import talib

file_name_m1 = "test/KRW-BTC_m1.csv"
file_name_m5 = "test/KRW-BTC_m5.csv"

df_m1 = pd.read_csv(file_name_m1, index_col=0, parse_dates=True)
df_m5 = pd.read_csv(file_name_m5, index_col=0, parse_dates=True)

df_m1.index.name = "Time"
df_m5.index.name = "Time"

for i in range(1, len(df_m5)):
    curr_row = df_m5.iloc[i]

    print(f"type of time = {type(curr_row.name)}")
    buy_time = curr_row.name + pd.Timedelta(minutes=1)
    buy_price = df_m1.loc[buy_time, 'close']
    break