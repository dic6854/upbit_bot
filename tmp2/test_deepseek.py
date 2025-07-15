import pandas as pd
import numpy as np
import talib
from datetime import datetime, timedelta

# 엑셀 파일에서 데이터 불러오기
file_path = "KRW-BTC.xlsx"
data_5min = pd.read_excel(file_path, sheet_name="minute5", index_col=0)
data_1min = pd.read_excel(file_path, sheet_name="minute1", index_col=0)

# 데이터 정리
data_5min = data_5min[['open', 'high', 'low', 'close', 'volume', 'value']]
data_1min = data_1min[['open', 'high', 'low', 'close', 'volume', 'value']]

# ATR 계산
data_5min['atr'] = talib.ATR(data_5min['high'], data_5min['low'], data_5min['close'], timeperiod=20)

# EMA 계산
data_5min['6ema'] = talib.EMA(data_5min['close'], timeperiod=6)
data_5min['12ema'] = talib.EMA(data_5min['close'], timeperiod=12)
data_5min['24ema'] = talib.EMA(data_5min['close'], timeperiod=24)

# MACD 계산
data_5min['macd1'], data_5min['macd1_signal'], _ = talib.MACD(data_5min['close'], fastperiod=6, slowperiod=12, signalperiod=9)
data_5min['macd2'], data_5min['macd2_signal'], _ = talib.MACD(data_5min['close'], fastperiod=6, slowperiod=24, signalperiod=9)
data_5min['macd3'], data_5min['macd3_signal'], _ = talib.MACD(data_5min['close'], fastperiod=12, slowperiod=24, signalperiod=9)

# Stage 판단
def get_stage(row):
    if row['6ema'] > row['12ema'] > row['24ema']:
        return 1
    elif row['12ema'] > row['6ema'] > row['24ema']:
        return 2
    elif row['12ema'] > row['24ema'] > row['6ema']:
        return 3
    elif row['24ema'] > row['12ema'] > row['6ema']:
        return 4
    elif row['24ema'] > row['6ema'] > row['12ema']:
        return 5
    elif row['6ema'] > row['24ema'] > row['12ema']:
        return 6
    else:
        return 0

data_5min['stage'] = data_5min.apply(get_stage, axis=1)

# MACD 우상향/우하향 판단
data_5min['macd1_up'] = data_5min['macd1'] > data_5min['macd1_signal']
data_5min['macd2_up'] = data_5min['macd2'] > data_5min['macd2_signal']
data_5min['macd3_up'] = data_5min['macd3'] > data_5min['macd3_signal']

# 매매 전략 실행
capital = 1000000  # 초기 자본금
risk_percent = 0.05  # 리스크 설정(R)
daily_pnl = []  # 일일 손익 기록
positions = []  # 보유 포지션

# 거래 시간 설정 (오전 9시 ~ 익일 오전 8시 51분)
start_time = datetime.strptime("09:00", "%H:%M").time()
end_time = datetime.strptime("08:51", "%H:%M").time()

# 매매 로직
for i in range(20, len(data_5min)):
    current_time = data_5min.index[i].time()
    if current_time < start_time or current_time >= end_time:
        continue  # 거래 시간이 아니면 건너뜀

    row_5min = data_5min.iloc[i]
    row_1min = data_1min.loc[data_5min.index[i] + timedelta(minutes=1)]

    # 매수 조건
    if row_5min['stage'] == 6 and row_5min['macd1_up'] and row_5min['macd2_up'] and row_5min['macd3_up']:
        if not positions:
            buy_price = row_1min['close']
            atr = row_5min['atr']
            risk_amount = capital * risk_percent
            position_size = (capital * risk_percent) / atr
            positions.append({'buy_price': buy_price, 'position_size': position_size, 'atr': atr, 'step': 1})

    # 추가 매수 조건
    for pos in positions:
        if row_1min['close'] >= pos['buy_price'] + 0.5 * pos['atr']:
            pos['buy_price'] = row_1min['close']
            pos['position_size'] += (capital * risk_percent) / pos['atr']
            pos['step'] += 1

    # 매도 조건
    if row_5min['stage'] == 3 and not row_5min['macd1_up'] and not row_5min['macd2_up'] and not row_5min['macd3_up']:
        for pos in positions:
            sell_price = row_1min['close']
            pnl = (sell_price - pos['buy_price']) * pos['position_size']
            daily_pnl.append(pnl)
            capital += pnl
        positions = []

    # 손절 조건
    for pos in positions:
        if row_1min['close'] <= pos['buy_price'] - 2 * pos['atr']:
            sell_price = row_1min['close']
            pnl = (sell_price - pos['buy_price']) * pos['position_size']
            daily_pnl.append(pnl)
            capital += pnl
            positions.remove(pos)

    # 익절 조건
    if len(data_5min) - i >= 12:
        recent_low = data_5min['close'].iloc[i-12:i].min()
        if row_1min['close'] <= recent_low:
            for pos in positions:
                sell_price = row_1min['close']
                pnl = (sell_price - pos['buy_price']) * pos['position_size']
                daily_pnl.append(pnl)
                capital += pnl
            positions = []

    # 매일 오전 8시 51분에 잔량 처분
    if current_time == end_time:
        for pos in positions:
            sell_price = row_1min['close']
            pnl = (sell_price - pos['buy_price']) * pos['position_size']
            daily_pnl.append(pnl)
            capital += pnl
        positions = []

# 일일 손익 기록
print("Daily PnL:", daily_pnl)
print("Final Capital:", capital)