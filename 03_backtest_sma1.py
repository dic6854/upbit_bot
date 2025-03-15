import pandas as pd
import time
from datetime import datetime
import talib

file_name_m1 = "test/KRW-BTC_m1.csv"
file_name_m5 = "test/KRW-BTC_m5.csv"

df_m1 = pd.read_csv(file_name_m1, index_col=0)
df_m5 = pd.read_csv(file_name_m5, index_col=0)

df_m1.index = pd.to_datetime(df_m1.index, format="%Y-%m-%d %H:%M:%S")
df_m5.index = pd.to_datetime(df_m5.index, format="%Y-%m-%d %H:%M:%S")

# 초기 자본금 및 리스크 설정
initial_capital = 1000000.0  # 100만원
R = 0.01  # 상승 폭 비율

# 매매 로직 구현
position = 0  # 0: 보유 없음, 1: 보유 있음

trades = []
capital = initial_capital
profits = []
U = 0.001

cut_start = pd.to_datetime("2025-03-01 08:55:00")
cut_end = cut_start + pd.Timedelta(days=1)

# t = 1
while True:
    cut_end = cut_start + pd.Timedelta(days=1)
    df_m5_t = df_m5[(df_m5.index >= cut_start) & (df_m5.index <= cut_end)]

    if len(df_m5_t) < 288:
        break

    for i in range(1, len(df_m5_t)):
        prev_row = df_m5_t.iloc[i-1]
        curr_row = df_m5_t.iloc[i]

        curr_datetime = curr_row.name

        if position == 0 and prev_row['close'] <= prev_row['SMA20'] and curr_row['close'] >= curr_row['SMA20'] :
            buy_time = curr_datetime + pd.Timedelta(minutes=1)
            buy_price = df_m1.loc[buy_time, 'close']
            trade_flag = 'buy'
            volume = U
            capital = capital - buy_price * U - (buy_price * U) * 0.0005
            trade = [buy_time, trade_flag, buy_price, volume, capital]
            trades.append(trade)            
            print(f"매수: {buy_time}, 가격: {buy_price}, 수량: {U}")
            position = 1
        elif position == 1  and prev_row['close'] >= prev_row['SMA20'] and curr_row['close'] <= curr_row['SMA20'] :
            sell_time = curr_datetime + pd.Timedelta(minutes=1)
            sell_price = df_m1.loc[sell_time, 'close']
            trade_flag = 'sell'
            volume = U
            capital = capital + sell_price * U - (sell_price * U) * 0.0005
            trade = [sell_time, trade_flag, sell_price, volume, capital]
            trades.append(trade)            
            print(f"매도: {sell_time}, 가격: {sell_price}, 손익: {capital-initial_capital}")
            position = 0

    if position == 1:
        sell_time = curr_datetime + pd.Timedelta(minutes=1)
        sell_price = df_m1.loc[sell_time, 'close']
        trade_flag = 'sell'
        volume = U
        capital = capital + sell_price * U - (sell_price * U) * 0.0005
        trade = [sell_time, trade_flag, sell_price, volume, capital]
        trades.append(trade)            
        print(f"매도: {sell_time}, 가격: {sell_price}, 손익: {capital-initial_capital}")
        position = 0        

    profit = float(capital-initial_capital)
    profits.append(profit)

    capital = initial_capital
    cut_start = cut_start + pd.Timedelta(days=1)

df = pd.DataFrame(trades, columns=['time', 'trade', 'price', 'volume', 'capital'])
df.to_csv("test/output.csv")
print(profits)
print(f"Total Profit : {sum(profits)}")
