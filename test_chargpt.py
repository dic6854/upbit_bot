import pandas as pd
import numpy as np
import talib
import matplotlib.pyplot as plt

# 샘플 데이터 로드 (실제 데이터는 Upbit API나 다른 거래소 API에서 받아올 수 있음)
# df는 5분봉 데이터 예시입니다.
df = pd.read_csv('sample_data.csv')  # 실제 데이터로 교체 필요

# ATR 계산 (20개봉)
N = 20
df['ATR'] = talib.ATR(df['High'], df['Low'], df['Close'], timeperiod=N)

# EMA 계산 (6, 12, 24 EMA)
df['6EMA'] = talib.EMA(df['Close'], timeperiod=6)
df['12EMA'] = talib.EMA(df['Close'], timeperiod=12)
df['24EMA'] = talib.EMA(df['Close'], timeperiod=24)

# MACD 계산 (6, 12, 9 / 6, 24, 9 / 12, 24, 9)
macd1, macdsignal1, _ = talib.MACD(df['Close'], fastperiod=6, slowperiod=12, signalperiod=9)
macd2, macdsignal2, _ = talib.MACD(df['Close'], fastperiod=6, slowperiod=24, signalperiod=9)
macd3, macdsignal3, _ = talib.MACD(df['Close'], fastperiod=12, slowperiod=24, signalperiod=9)

df['MACD1'] = macd1
df['MACDSignal1'] = macdsignal1
df['MACD2'] = macd2
df['MACDSignal2'] = macdsignal2
df['MACD3'] = macd3
df['MACDSignal3'] = macdsignal3

# 매수 크기 계산 (자본금의 5%와 ATR을 기반으로 매수 크기 설정)
capital = 1000000  # 초기 자본금 100만원
R = 0.05  # 리스크 설정 (자본금의 5%)
df['U'] = (capital * R) / df['ATR']  # 매수 크기 U 계산

# EMA 상태를 구하는 함수
def get_stage(row):
    if row['6EMA'] > row['12EMA'] > row['24EMA']:
        return 1  # Stage 1
    elif row['12EMA'] > row['6EMA'] > row['24EMA']:
        return 2  # Stage 2
    elif row['12EMA'] > row['24EMA'] > row['6EMA']:
        return 3  # Stage 3
    elif row['24EMA'] > row['12EMA'] > row['6EMA']:
        return 4  # Stage 4
    elif row['24EMA'] > row['6EMA'] > row['12EMA']:
        return 5  # Stage 5
    elif row['6EMA'] > row['24EMA'] > row['12EMA']:
        return 6  # Stage 6

df['Stage'] = df.apply(get_stage, axis=1)

# 매수 및 매도 시점 판단 함수
def check_buy_sell_conditions(row, position, last_buy_price, buy_count):
    # 매수 조건 (Stage 6, MACD가 모두 우상향)
    if row['Stage'] == 6 and row['MACD1'] > row['MACDSignal1'] and row['MACD2'] > row['MACDSignal2'] and row['MACD3'] > row['MACDSignal3']:
        if position == 0:  # 포지션이 없으면 매수
            return 'buy'
    
    # 매도 조건 (Stage 3, MACD가 모두 우하향)
    elif row['Stage'] == 3 and row['MACD1'] < row['MACDSignal1'] and row['MACD2'] < row['MACDSignal2'] and row['MACD3'] < row['MACDSignal3']:
        if position > 0:  # 포지션이 있으면 매도
            return 'sell'
    
    # 손절 조건 (매수가 - 2 * N)
    if position > 0:
        if buy_count == 1 and row['Close'] < last_buy_price - 2 * row['ATR']:
            return 'stop_loss'
        elif buy_count == 2 and row['Close'] < (last_buy_price + 0.5 * row['ATR']) - 2 * row['ATR']:
            return 'stop_loss'
        elif buy_count == 3 and row['Close'] < (last_buy_price + 1 * row['ATR']) - 2 * row['ATR']:
            return 'stop_loss'
        elif buy_count == 4 and row['Close'] < (last_buy_price + 1.5 * row['ATR']) - 2 * row['ATR']:
            return 'stop_loss'
    
    # 익절 조건 (최근 12개봉의 최저점 도달)
    if position > 0 and row['Close'] <= df['Close'][-12:].min():
        return 'take_profit'
    
    return None

# 포지션 추적 변수
position = 0
last_buy_price = 0
buy_count = 0
trade_history = []

# 트레이딩 시뮬레이션
for i in range(1, len(df)):
    row = df.iloc[i]
    signal = check_buy_sell_conditions(row, position, last_buy_price, buy_count)
    
    if signal == 'buy':
        position += row['U']  # 매수
        last_buy_price = row['Close']
        buy_count += 1
        trade_history.append({'action': 'buy', 'price': row['Close'], 'position': position, 'buy_count': buy_count})
    
    elif signal == 'sell':
        position -= row['U']  # 매도
        trade_history.append({'action': 'sell', 'price': row['Close'], 'position': position, 'buy_count': buy_count})
    
    elif signal == 'stop_loss': # 손절
        position = 0
        buy_count = 0
        trade_history.append({'action': 'stop_loss', 'price': row['Close'], 'position': position, 'buy_count': buy_count})
    
    elif signal == 'take_profit': # 익절
        position = 0
        buy_count = 0
        trade_history.append({'action': 'take_profit', 'price': row['Close'], 'position': position, 'buy_count': buy_count})

# 결과 출력 (손익 기록)
trade_df = pd.DataFrame(trade_history)
print(trade_df)

# 시각화 (매매 시점 표시)
plt.figure(figsize=(12,6))
plt.plot(df['Close'], label='Close Price')
buy_signals = trade_df[trade_df['action'] == 'buy']
sell_signals = trade_df[trade_df['action'] == 'sell']
plt.scatter(buy_signals.index, buy_signals['price'], marker='^', color='g', label='Buy Signal')
plt.scatter(sell_signals.index, sell_signals['price'], marker='v', color='r', label='Sell Signal')
plt.legend()
plt.show()