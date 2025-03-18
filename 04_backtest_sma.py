import pyupbit
import pandas as pd
# import time
# from datetime import datetime
# import talib

def get_price(buy_time, df):
    while True:
        try:
            buy_time = buy_time + pd.Timedelta(minutes=1)
            buy_price = df.loc[buy_time, 'close']
            return buy_time, buy_price
        except:
            buy_time += pd.Timedelta(minutes=1)

def set_volume(capital, price):
    unit = capital / price

    while True:
        volume = capital - price * unit - (price * unit) * 0.0005
        if float(volume) < float(capital):
            return unit
        unit -= 0.0001

if __name__ == "__main__":
    # 초기 자본금 및 리스크 설정
    initial_capital = 1000000.0  # 100만원

    # 매매 로직 구현
    position = 0  # 0: 보유 없음, 1: 보유 있음
    trades = []
    capital = initial_capital
    profits = []
    myprofits = []
    volume = 0.001

    krw_tickers = pyupbit.get_tickers(fiat="KRW")

    tt = len(krw_tickers)
    ct = 1
    for i in range(tt):
        ticker = krw_tickers[i]
        file_name_m1 = f"test/{ticker}_m1.csv"
        file_name_m5 = f"test/{ticker}_m5.csv"
        trade_output = f"test/{ticker}_trade_m5.csv"
        profit_output = f"test/{ticker}_profit_m5.csv"
        my_profit_output = f"test/{ticker}_myprofit_m5.csv"

        # file_name_m1 = f"hdata/{ticker}_m1.csv"
        # file_name_m5 = f"hdata/{ticker}_m5.csv"
        # trade_output = f"backtest/{ticker}_trade_m5.csv"
        # profit_output = f"backtest/{ticker}_profit_m5.csv"

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

        start_datetime = df_m5.index[0]
        start_datetime = start_datetime.replace(hour=8, minute=55, second=0)
        end_datetime = df_m5.index[-1]

        curr_datetime = start_datetime

        while curr_datetime <= end_datetime:
            next_datetime = curr_datetime + pd.Timedelta(days=1)
            df_t = df_m5[(df_m5.index >= curr_datetime) & (df_m5.index <= next_datetime)].copy()

            for i in range(1, len(df_t)):
                prev_row = df_t.iloc[i-1]
                curr_row = df_t.iloc[i]

                if position == 0 and prev_row['close'] <= prev_row['SMA20'] and curr_row['close'] >= curr_row['SMA20'] :
                    buy_time = curr_row.name + pd.Timedelta(minutes=1)
                    buy_price = df_m1.loc[buy_time, 'close']
                    trade_flag = 'buy'

                    volume = int(set_volume(capital, buy_price) * 1000) / 1000
                    capital = capital - buy_price * volume - (buy_price * volume) * 0.0005

                    trade = [buy_time, trade_flag, buy_price, volume, capital]
                    trades.append(trade)            
                    print(f"매수: {buy_time}, 가격: {buy_price}, 수량: {volume}")
                    position = 1
                    continue
                elif position == 1  and prev_row['close'] >= prev_row['SMA20'] and curr_row['close'] <= curr_row['SMA20'] :
                    sell_time = curr_row.name + pd.Timedelta(minutes=1)
                    sell_price = df_m1.loc[sell_time, 'close']
                    trade_flag = 'sell'
                    capital = capital + sell_price * volume - (sell_price * volume) * 0.0005

                    if capital > initial_capital:
                        myprofit = [sell_time, float(capital - initial_capital)]
                        myprofits.append(myprofit)
                        capital = initial_capital

                    trade = [sell_time, trade_flag, sell_price, volume, capital]
                    trades.append(trade)            
                    print(f"매도: {sell_time}, 가격: {sell_price}, 손익: {capital-initial_capital}")
                    position = 0
                    continue

            profit = [curr_datetime, float(capital-initial_capital)]
            profits.append(profit)

            capital = initial_capital
            curr_datetime = next_datetime

        if position == 1:
            sell_time = curr_row.name + pd.Timedelta(minutes=1)
            sell_price = df_m1.loc[sell_time, 'close']
            trade_flag = 'sell'
            capital = capital + sell_price * volume - (sell_price * volume) * 0.0005

            if capital > initial_capital:
                myprofit = [sell_time, float(capital - initial_capital)]
                myprofits.append(myprofit)
                capital = initial_capital

            trade = [sell_time, trade_flag, sell_price, volume, capital]
            trades.append(trade)            
            print(f"매도: {sell_time}, 가격: {sell_price}, 손익: {capital-initial_capital}")
            position = 0 

        df = pd.DataFrame(trades, columns=['time', 'trade', 'price', 'volume', 'capital'])
        df.to_csv(trade_output)
        
        df = pd.DataFrame(profits, columns=['time', 'profit'])
        df.to_csv(profit_output)

        df = pd.DataFrame(myprofits, columns=['time', 'profit'])
        df.to_csv(my_profit_output)

        print(f"[ {ct} / {tt} ] - {profit_output} 파일에 Profit 저장")

        ct += 1
        break
