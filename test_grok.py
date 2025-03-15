import pandas as pd
import numpy as np
import talib

# 랜덤 주가 데이터 생성 (실제로는 5분봉 및 1분봉 데이터를 사용)
np.random.seed(42)
data_5min = pd.DataFrame({
    'Close': np.random.normal(10000, 100, 1000).cumsum(),
    'Time': pd.date_range(start='2025-03-08 09:00', periods=1000, freq='5min')
})
data_1min = pd.DataFrame({
    'Close': np.random.normal(10000, 100, 5000).cumsum(),
    'Time': pd.date_range(start='2025-03-08 09:00', periods=5000, freq='1min')
})

# 초기 자본금 및 리스크 설정
initial_capital = 1000000  # 100만원
R = 0.05  # 자본금의 5% 리스크

# EMA 계산 (5분봉 기준)
data_5min['6EMA'] = talib.EMA(data_5min['Close'], timeperiod=6)
data_5min['12EMA'] = talib.EMA(data_5min['Close'], timeperiod=12)
data_5min['24EMA'] = talib.EMA(data_5min['Close'], timeperiod=24)

# MACD 계산 (5분봉 기준)
data_5min['MACD1'], data_5min['MACD1_Signal'], _ = talib.MACD(data_5min['Close'], fastperiod=6, slowperiod=12, signalperiod=9)
data_5min['MACD2'], data_5min['MACD2_Signal'], _ = talib.MACD(data_5min['Close'], fastperiod=6, slowperiod=24, signalperiod=9)
data_5min['MACD3'], data_5min['MACD3_Signal'], _ = talib.MACD(data_5min['Close'], fastperiod=12, slowperiod=24, signalperiod=9)

# ATR 계산 (20개봉 기준, 5분봉)
data_5min['High'] = data_5min['Close'] * 1.01  # 예시 High/Low 생성
data_5min['Low'] = data_5min['Close'] * 0.99
data_5min['ATR'] = talib.ATR(data_5min['High'], data_5min['Low'], data_5min['Close'], timeperiod=20)

# Stage 정의 함수
def get_stage(row):
    if row['6EMA'] > row['12EMA'] > row['24EMA']:
        return 1
    elif row['12EMA'] > row['6EMA'] > row['24EMA']:
        return 2
    elif row['12EMA'] > row['24EMA'] > row['6EMA']:
        return 3
    elif row['24EMA'] > row['12EMA'] > row['6EMA']:
        return 4
    elif row['24EMA'] > row['6EMA'] > row['12EMA']:
        return 5
    elif row['6EMA'] > row['24EMA'] > row['12EMA']:
        return 6
    return 0

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

for i in range(1, len(data_5min)):
    prev_row = data_5min.iloc[i-1]
    curr_row = data_5min.iloc[i]
    
    # Stage 계산
    data_5min.loc[curr_row.name, 'Stage'] = get_stage(curr_row)
    
    # N (ATR) 값
    N = curr_row['ATR']
    if pd.isna(N):
        continue
    
    # 매수 크기 (U) 계산
    U = (capital * R) / N
    
    # 거래 시간 체크
    if not (curr_row['Time'].time() >= pd.Timestamp('09:00').time() and curr_row['Time'].time() <= pd.Timestamp('08:51').time()):
        continue
    
    # 1차 매수 조건
    if len(positions) == 0 and curr_row['Stage'] == 6 and is_macd_upward(prev_row, curr_row):
        buy_price = data_1min[data_1min['Time'] == curr_row['Time'] + pd.Timedelta(minutes=1)]['Close'].values[0]
        positions.append({'entry_price': buy_price, 'units': U, 'stage': 1})
        print(f"1차 매수: {curr_row['Time']}, 가격: {buy_price}, 수량: {U}")
    
    # 추가 매수 및 손절/익절
    if positions:
        current_price = data_1min[data_1min['Time'] == curr_row['Time'] + pd.Timedelta(minutes=1)]['Close'].values[0]
        
        # 추가 매수
        last_position = positions[-1]
        if len(positions) < 4 and current_price >= last_position['entry_price'] + 0.5 * N:
            new_buy_price = current_price
            positions.append({'entry_price': new_buy_price, 'units': U, 'stage': len(positions) + 1})
            print(f"{len(positions)}차 매수: {curr_row['Time']}, 가격: {new_buy_price}, 수량: {U}")
        
        # 매도 조건
        if curr_row['Stage'] == 3 and is_macd_downward(prev_row, curr_row):
            sell_price = current_price
            total_pnl = sum((sell_price - pos['entry_price']) * pos['units'] for pos in positions)
            capital += total_pnl
            print(f"매도: {curr_row['Time']}, 가격: {sell_price}, 손익: {total_pnl}")
            positions = []
        
        # 손절
        stop_loss_price = positions[0]['entry_price'] - 2 * N if len(positions) == 1 else (positions[-2]['entry_price'] + 0.5 * N) - 2 * N
        if current_price <= stop_loss_price:
            total_pnl = sum((current_price - pos['entry_price']) * pos['units'] for pos in positions)
            capital += total_pnl
            print(f"손절: {curr_row['Time']}, 가격: {current_price}, 손익: {total_pnl}")
            positions = []
        
        # 익절 (최근 12개봉 최저점)
        recent_low = data_5min['Close'].iloc[i-12:i].min()
        if current_price <= recent_low:
            total_pnl = sum((current_price - pos['entry_price']) * pos['units'] for pos in positions)
            capital += total_pnl
            print(f"익절: {curr_row['Time']}, 가격: {current_price}, 손익: {total_pnl}")
            positions = []
    
    # 거래 종료 시 잔량 정리
    if curr_row['Time'].time() == pd.Timestamp('08:51').time() and positions:
        sell_price = current_price
        total_pnl = sum((sell_price - pos['entry_price']) * pos['units'] for pos in positions)
        capital += total_pnl
        daily_pnl.append(total_pnl)
        print(f"일일 마감: {curr_row['Time']}, 가격: {sell_price}, 손익: {total_pnl}")
        positions = []
        capital = initial_capital  # 다음 날 자본 초기화

# 결과 출력
print(f"최종 자본: {capital}")
print(f"일일 손익 기록: {daily_pnl}")