import pandas as pd
import time
from datetime import datetime
import talib

file_name_m1 = "test/KRW-BTC_m1.csv"
file_name_m5 = "test/KRW-BTC_m5.csv"

df_m1 = pd.read_csv(file_name_m1, index_col=0)
df_m5 = pd.read_csv(file_name_m5, index_col=0)

df_m1.index = pd.to_datetime(df_m1.index)
df_m5.index = pd.to_datetime(df_m5.index)

# 초기 자본금 및 리스크 설정
initial_capital = 1000000  # 100만원
R = 0.05  # 자본금의 5% 리스크

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