import pandas as pd
import time
from datetime import datetime
import talib

file_name_m5 = "test/KRW-BTC_m5.csv"
df_m5 = pd.read_csv(file_name_m5, index_col=0)

# 5, 20 SMA 계산 (5분봉 기준)
df_m5['SMA5'] = talib.SMA(df_m5['close'], timeperiod=5)
df_m5['SMA20'] = talib.SMA(df_m5['close'], timeperiod=20)

df_m5.to_csv(file_name_m5)
print(f"{file_name_m5} 파일에 단순이동평균선 저장")
