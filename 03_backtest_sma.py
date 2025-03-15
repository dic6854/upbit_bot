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

cut_datetime = pd.to_datetime("2025-03-12 08:55:00")
df_m5 = df_m5[df_m5.index >= cut_datetime]

# 초기 자본금 및 리스크 설정
initial_capital = 1000000.0  # 100만원
R = 0.01  # 상승 폭 비율

# 매매 로직 구현
position = 0  # 0: 보유 없음, 1: 보유 있음

trades = []
capital = initial_capital
profits = []
U = 0.001

for i in range(1, len(df_m5)):
    prev_row = df_m5.iloc[i-1]
    curr_row = df_m5.iloc[i]

    curr_datetime = curr_row.name

    if position == 0 and prev_row['close'] <= prev_row['SMA20'] and curr_row['close'] >= curr_row['SMA20'] :
        buy_time = curr_datetime + pd.Timedelta(minutes=1)
        buy_price = df_m1.loc[buy_time, 'close']
        trades.append({'time': buy_time,'entry_price': float(buy_price), 'units': U, 'trade': 1})
        capital = capital - buy_price * U - (buy_price * U) * 0.0005
        print(f"매수: {buy_time}, 가격: {buy_price}, 수량: {U}")
        position = 1
    elif position == 1 and prev_row['close'] >= prev_row['SMA20'] and curr_row['close'] <= curr_row['SMA20'] :
        sell_time = curr_datetime + pd.Timedelta(minutes=1)
        sell_price = df_m1.loc[sell_time, 'close']
        trades.append({'time': sell_time,'entry_price': float(sell_price), 'units': U, 'trade': 0})
        capital = capital + sell_price * U - (sell_price * U) * 0.0005
        print(f"매도: {sell_time}, 가격: {sell_price}, 손익: {capital-initial_capital}")
        position = 0

print(f"profit = {capital - initial_capital}")
for trade in trades:
    print(trade)

'''
    curr_datetime = curr_row.name
    curr_time = curr_datetime.time()

    if (curr_time > pd.Timestamp("08:50").time()) and (curr_time < pd.Timestamp("09:00").time()): # 정산 계산 중
        print(f"[{curr_datetime}] - 정산 계산 중")
    else:
        print(f"[{curr_datetime}] - Stage : {int(curr_row['Stage'])}")

        # 1차 매수 조건
        if len(positions) == 0 and curr_row['Stage'] == 6:
            buy_time = curr_datetime + pd.Timedelta(minutes=1)
            buy_price = df_m1.loc[buy_time, 'close']
            positions.append({'entry_price': float(buy_price), 'units': U, 'step': 1})
            print(f"1차 매수: {buy_time}, 가격: {buy_price}, 수량: {U}")
        
        # 추가 매수 및 손절/익절
        if positions:
            current_time = curr_datetime + pd.Timedelta(minutes=1)
            current_price = df_m1.loc[current_time, 'close']           

            # 추가 매수
            last_position = positions[-1]
            if len(positions) < 4 and current_price >= last_position['entry_price'] + 0.5 * N:
                new_buy_price = current_price
                positions.append({'entry_price': float(new_buy_price), 'units': U, 'step': len(positions) + 1})
                print(f"{len(positions)}차 매수: {current_time}, 가격: {new_buy_price}, 수량: {U}")

            # 매도 조건
            if curr_row['Stage'] == 3:
                sell_price = current_price
                total_pnl = sum((float(sell_price) - float(pos['entry_price'])) * float(pos['units']) for pos in positions)
                capital += total_pnl
                print(f"매도: {current_time}, 가격: {sell_price}, 손익: {total_pnl}")
                positions = []
            else:
                # 손절
                stop_loss_price = positions[0]['entry_price'] - 2 * N if len(positions) == 1 else (positions[-2]['entry_price'] + 0.5 * N) - 2 * N
                if current_price <= stop_loss_price:
                    total_pnl = sum((current_price - pos['entry_price']) * pos['units'] for pos in positions)
                    capital += total_pnl
                    print(f"손절: {current_time}, 가격: {current_price}, 손익: {total_pnl}")
                    positions = []
            
            # 익절 (최근 12개봉 최저점)
            recent_low = df_m5['close'].iloc[i-12:i].min()
            if current_price <= recent_low:
                total_pnl = sum((float(current_price) - float(pos['entry_price'])) * float(pos['units']) for pos in positions)
                capital += total_pnl
                print(f"익절: {current_time}, 가격: {current_price}, 손익: {total_pnl}")
                positions = []

        # 거래 종료 시 잔량 정리
        if curr_time == pd.Timestamp('08:50').time() and positions:
            sell_price = current_price
            total_pnl = sum((float(sell_price) - float(pos['entry_price'])) * float(pos['units']) for pos in positions)
            capital += total_pnl
            daily_pnl.append(total_pnl)
            print(f"일일 마감: {current_time}, 가격: {sell_price}, 손익: {total_pnl}")
            positions = []
            capital = initial_capital  # 다음 날 자본 초기화

# 결과 출력
print(f"최종 자본: {capital}")
print(f"일일 손익 기록: {daily_pnl}")
'''