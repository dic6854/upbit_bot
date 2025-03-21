import pyupbit
import pandas as pd
import time
from datetime import datetime
import talib
import calendar

def get_price(buy_time, df):
    while True:
        try:
            buy_time = buy_time + pd.Timedelta(minutes=1)
            buy_price = df.loc[buy_time, 'close']
            return buy_time, buy_price
        except:
            buy_time += pd.Timedelta(minutes=1)

def set_volume(capital, price):
    unit = int((capital / price) * 10000) / 10000

    while True:
        volume = price * unit + price * unit * 0.0005

        if float(volume) < float(capital):
            return unit
        unit -= 0.0001

if __name__ == "__main__":

    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    tt = len(krw_tickers)
    ct = 1
    for i in range(tt):
        ticker = krw_tickers[i]
        file_name_m1 = f"test/{ticker}_m1.csv"
        file_name_m5 = f"test/{ticker}_m5.csv"
        trade_output = f"test/backtest/{ticker}_trade_m5.csv"
        profit_output = f"test/backtest/{ticker}_profit_m5.csv"

        df_m1 = pd.read_csv(file_name_m1, index_col=0)
        df_m5 = pd.read_csv(file_name_m5, index_col=0)

        try:
            df_m1.index = pd.to_datetime(df_m1.index, format="%Y-%m-%d %H:%M:%S")
        except:
            df_m1.index = pd.to_datetime(df_m1.index, format="%Y-%m-%d %H:%M")

        try:
            df_m5.index = pd.to_datetime(df_m5.index, format="%Y-%m-%d %H:%M:%S")
        except:
            df_m5.index = pd.to_datetime(df_m5.index, format="%Y-%m-%d %H:%M")

        # 초기 자본금 및 리스크 설정
        initial_capital = 1000000.0  # 초기 자본 : 100만원
        position = 0  # 0: 보유 없음, 1: 보유 있음
        trades = []
        profits = []
        capital = initial_capital
        volume = 0.001
        curr_profit = 0.0
        flag = False

        start_datetime = df_m5.index[0]
        end_datetime = df_m5.index[-1]

        current_year = start_datetime.year
        gcount = 0
        while current_year <= end_datetime.year:
            current_month = start_datetime.month if current_year == start_datetime.year else 1

            while current_month <= 12:
                if current_year == start_datetime.year and current_month == start_datetime.month:
                    first_day_of_month = start_datetime.day
                else:
                    first_day_of_month = 1
                    # print(f"first_day_of_month={first_day_of_month}")
                if current_year == end_datetime.year and current_month == end_datetime.month:
                    last_day_of_month = end_datetime.day
                else:
                    last_day = calendar.monthrange(current_year, current_month)[1]
                    last_day_of_month = last_day
                    # print(f"last_day_of_month={last_day_of_month}")

                sdatetime = datetime(year=current_year, month=current_month, day=first_day_of_month, hour=8, minute=55, second=0)
                edatetime = datetime(year=current_year, month=current_month, day=last_day_of_month, hour=8, minute=55, second=0)

                curr_datetime = sdatetime
                while curr_datetime <= edatetime:
                    next_datetime = curr_datetime + pd.Timedelta(days=1)
                    df_t = df_m5[(df_m5.index >= curr_datetime) & (df_m5.index <= next_datetime)].copy()
                    for i in range(1, len(df_t)):
                        gcount += 1
                        prev_row = df_t.iloc[i-1]
                        curr_row = df_t.iloc[i]
                        if position == 0 and prev_row['close'] <= prev_row['SMA20'] and curr_row['close'] >= curr_row['SMA20'] :
                            buy_time = curr_row.name + pd.Timedelta(minutes=1)
                            buy_price = df_m1.loc[buy_time, 'close']
                            trade_flag = 'buy'

                            volume = set_volume(capital, buy_price)
                            capital = capital - (buy_price * volume + buy_price * volume * 0.0005)
                            curr_profit = 0.0

                            trade = [buy_time, trade_flag, buy_price, volume, capital, curr_profit]
                            trades.append(trade)            
                            # print(f"매수: {buy_time}, 가격: {buy_price}, 수량: {volume}, 잔고: {capital}")
                            position = 1
                            continue
                        elif position == 1  and prev_row['close'] >= prev_row['SMA20'] and curr_row['close'] <= curr_row['SMA20'] :
                            sell_time = curr_row.name + pd.Timedelta(minutes=1)
                            sell_price = df_m1.loc[sell_time, 'close']
                            trade_flag = 'sell'
                            capital = capital + (sell_price * volume - sell_price * volume * 0.0005)
                            curr_profit = capital - initial_capital
                            if curr_profit < 0.0:
                                curr_profit = 0.0
                            else:
                                kday = sell_time.day
                                profit = [current_year, current_month, kday, curr_profit]
                                profits.append(profit)
                                capital = initial_capital
                            trade = [sell_time, trade_flag, sell_price, volume, capital, curr_profit]
                            trades.append(trade)
                            # print(f"매도: {sell_time}, 가격: {sell_price}, 수량: {volume}, 잔고: {capital}, 수익: {curr_profit}")
                            position = 0                    
                            continue
                    curr_datetime = next_datetime

                if position == 1:
                    sell_time = curr_row.name + pd.Timedelta(minutes=1)
                    sell_price = df_m1.loc[sell_time, 'close']
                    trade_flag = 'sell'
                    capital = capital + (sell_price * volume - sell_price * volume * 0.0005)
                    curr_profit = capital - initial_capital
                    if curr_profit <= 0.0:
                        curr_profit = 0.0
                    else:
                        kday = sell_time.day
                        profit = [current_year, current_month, kday, curr_profit]
                        profits.append(profit)
                        capital = initial_capital
                    trade = [sell_time, trade_flag, sell_price, volume, capital, curr_profit]
                    trades.append(trade)
                    # print(f"매도: {sell_time}, 가격: {sell_price}, 수량: {volume}, 잔고: {capital}, 수익: {curr_profit}")
                    position = 0

                if current_year == end_datetime.year and current_month == end_datetime.month:
                    break
                current_month += 1

            if current_year == end_datetime.year:
                break
            current_year += 1

        df = pd.DataFrame(trades, columns=['time', 'trade', 'price', 'volume', 'balance', 'profit'])
        df.to_csv(trade_output)
        
        df = pd.DataFrame(profits, columns=['year', 'month', 'day', 'profit'])
        df.to_csv(profit_output)

        print(f"[ {ct} / {tt} ] - {profit_output} 파일에 Profit 저장")
        print(f"gcount = {gcount}")

        ct += 1

