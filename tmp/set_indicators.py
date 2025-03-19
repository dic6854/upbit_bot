import pandas as pd
import time
from datetime import datetime
import talib

file_name_m5 = "test/KRW-BTC_m5.csv"
df_m5 = pd.read_csv(file_name_m5, index_col=0)

# 6(단기), 12(중기), 24(장기) EMA 계산 (5분봉 기준)
df_m5['EMA6'] = talib.EMA(df_m5['close'], timeperiod=6)
df_m5['EMA12'] = talib.EMA(df_m5['close'], timeperiod=12)
df_m5['EMA24'] = talib.EMA(df_m5['close'], timeperiod=24)

# MACD 계산 (5분봉 기준)
df_m5['MACD1'], df_m5['MACD1_Signal'], df_m5['MACD1_Oscilator'] = talib.MACD(df_m5['close'], fastperiod=6, slowperiod=12, signalperiod=9)
df_m5['MACD2'], df_m5['MACD2_Signal'], df_m5['MACD2_Oscilator'] = talib.MACD(df_m5['close'], fastperiod=6, slowperiod=24, signalperiod=9)
df_m5['MACD3'], df_m5['MACD3_Signal'], df_m5['MACD3_Oscilator'] = talib.MACD(df_m5['close'], fastperiod=12, slowperiod=24, signalperiod=9)

# ATR 계산 (20개봉 기준, 5분봉)
df_m5['ATR_High'] = df_m5['close'] * 1.01  # 예시 High/Low 생성
df_m5['ATR_Low'] = df_m5['close'] * 0.99
df_m5['ATR'] = talib.ATR(df_m5['ATR_High'], df_m5['ATR_Low'], df_m5['close'], timeperiod=20)

# Stage 정의 함수
def get_stage(row):
    if row['EMA6'] > row['EMA12'] > row['EMA24']:
        return 1
    elif row['EMA12'] > row['EMA6'] > row['EMA24']:
        return 2
    elif row['EMA12'] > row['EMA24'] > row['EMA6']:
        return 3
    elif row['EMA24'] > row['EMA12'] > row['EMA6']:
        return 4
    elif row['EMA24'] > row['EMA6'] > row['EMA12']:
        return 5
    elif row['EMA6'] > row['EMA24'] > row['EMA12']:
        return 6
    return 0

for i in range(1, len(df_m5)):
    prev_row = df_m5.iloc[i-1]
    curr_row = df_m5.iloc[i]

    df_m5.loc[curr_row.name, 'Stage'] = get_stage(curr_row)

print("Starting")
df_m5.to_csv(file_name_m5)
print("Ended")