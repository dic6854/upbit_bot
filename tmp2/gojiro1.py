import pandas as pd
import time
from datetime import datetime
import talib

file_name_m1 = "test/KRW-BTC_m1.csv"
file_name_m5 = "test/KRW-BTC_m5.csv"

df_m1 = pd.read_csv(file_name_m1, index_col=0)
df_m5 = pd.read_csv(file_name_m5, index_col=0)

# 초기 자본금 및 리스크 설정
initial_capital = 1000000  # 100만원
R = 0.05  # 자본금의 5% 리스크

# MACD 우상향/우하향 체크 함수
def is_macd_upward(prev_row, curr_row):
    return (curr_row['MACD1'] > curr_row['MACD1_Signal'] and prev_row['MACD1'] <= prev_row['MACD1_Signal']) and \
           (curr_row['MACD2'] > curr_row['MACD2_Signal'] and prev_row['MACD2'] <= prev_row['MACD2_Signal']) and \
           (curr_row['MACD3'] > curr_row['MACD3_Signal'] and prev_row['MACD3'] <= prev_row['MACD3_Signal'])

def is_macd_downward(prev_row, curr_row):
    return (curr_row['MACD1'] < curr_row['MACD1_Signal'] and prev_row['MACD1'] >= prev_row['MACD1_Signal']) and \
           (curr_row['MACD2'] < curr_row['MACD2_Signal'] and prev_row['MACD2'] >= prev_row['MACD2_Signal']) and \
           (curr_row['MACD3'] < curr_row['MACD3_Signal'] and prev_row['MACD3'] >= prev_row['MACD3_Signal'])

# 매매 로직 구현
positions = []
capital = initial_capital
daily_pnl = []

for i in range(1, len(df_m5)):
    prev_row = df_m5.iloc[i-1]
    curr_row = df_m5.iloc[i]

    # N (ATR) 값
    N = curr_row['ATR']
    if pd.isna(N):
        continue
    
    # 매수 크기 (U) 계산
    U = (capital * R) / N
    U = f"{U:.6f}"

    curr_datetime = datetime.strptime(curr_row.name, "%Y-%m-%d %H:%M:%S")
    curr_time = curr_datetime.time()

    if (curr_time > pd.Timestamp("08:50:00").time()) and (curr_time < pd.Timestamp("09:00:00").time()): # 정산 계산 중
        print(f"[{curr_datetime}] - 정산 계산 중")
    else:
        print(f"[{curr_row.name}] - Stage : {int(curr_row['Stage'])} - Uptrend : {is_macd_upward(prev_row, curr_row)}")

        # 1차 매수 조건
        if len(positions) == 0 and curr_row['Stage'] == 6 and is_macd_upward(prev_row, curr_row):
            buy_time = curr_row.name + pd.Timedelta(minutes=1)
            buy_price = df_m1.loc[buy_time, 'close']
            positions.append({'entry_price': buy_price, 'units': U, 'step': 1})
            print(f"1차 매수: {curr_row['Time']}, 가격: {buy_price}, 수량: {U}")
        
        # 추가 매수 및 손절/익절
        if positions:
            current_time = curr_row.name + pd.Timedelta(minutes=1)
            current_price = df_m1.loc[current_time, 'close']           

            # 추가 매수
            last_position = positions[-1]
            if len(positions) < 4 and current_price >= last_position['entry_price'] + 0.5 * N:
                new_buy_price = current_price
                positions.append({'entry_price': new_buy_price, 'units': U, 'step': len(positions) + 1})
                print(f"{len(positions)}차 매수: {curr_row['Time']}, 가격: {new_buy_price}, 수량: {U}")

            # 매도 조건
            if curr_row['Stage'] == 3 and is_macd_downward(prev_row, curr_row):
                sell_price = current_price
                total_pnl = sum((sell_price - pos['entry_price']) * pos['units'] for pos in positions)
                capital += total_pnl
                print(f"매도: {curr_row.name}, 가격: {sell_price}, 손익: {total_pnl}")
                positions = []

            # 손절
            if len(positions) == 1:   # positions 리스트의 길이가 1인 경우
                entry_price = positions[0]['entry_price']
                stop_loss_price = entry_price - 2 * N
            else:   # positions 리스트의 길이가 1이 아닌 경우 (2개 이상)
                entry_price = positions[-2]['entry_price']
                stop_loss_price = (entry_price + 0.5 * N) - 2 * N
            if current_price <= stop_loss_price:
                total_pnl = sum((current_price - pos['entry_price']) * pos['units'] for pos in positions)
                capital += total_pnl
                print(f"손절: {curr_row.name}, 가격: {current_price}, 손익: {total_pnl}")
                positions = []

            # 익절 (최근 12개봉 최저점)
            recent_low = df_m5['close'].iloc[i-12:i].min()
            if current_price <= recent_low:
                total_pnl = sum((current_price - pos['entry_price']) * pos['units'] for pos in positions)
                capital += total_pnl
                print(f"익절: {curr_row['Time']}, 가격: {current_price}, 손익: {total_pnl}")
                positions = []

            # 거래 종료 시 잔량 정리
            if curr_row.name.time() == pd.Timestamp('08:50').time() and positions:
                sell_price = current_price
                total_pnl = sum((sell_price - pos['entry_price']) * pos['units'] for pos in positions)
                capital += total_pnl
                daily_pnl.append(total_pnl)
                print(f"일일 마감: {curr_row.name}, 가격: {sell_price}, 손익: {total_pnl}")
                positions = []
                capital = initial_capital  # 다음 날 자본 초기화

# 결과 출력
print(f"최종 자본: {capital}")
print(f"일일 손익 기록: {daily_pnl}")