import pandas as pd
import numpy as np
from datetime import datetime

# 함수 정의: EMA 계산
def calculate_ema(series, period):
    return series.ewm(span=period, adjust=False).mean()

# 함수 정의: Stochastic RSI 계산
def calculate_stoch_rsi(close, period=14, smooth_k=3, smooth_d=3):
    rsi = calculate_rsi(close, period)
    rsi_min = rsi.rolling(window=period).min()
    rsi_max = rsi.rolling(window=period).max()
    stoch_rsi = 100 * (rsi - rsi_min) / (rsi_max - rsi_min + 1e-6)  # division by zero 방지
    k = stoch_rsi.rolling(window=smooth_k).mean()
    d = k.rolling(window=smooth_d).mean()
    return k, d

# 함수 정의: RSI 계산 (Stoch RSI에 사용)
def calculate_rsi(close, period=14):
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / (loss + 1e-6)
    rsi = 100 - (100 / (1 + rs))
    return rsi

# 함수 정의: ADX 계산
def calculate_adx(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    
    up = high - high.shift()
    down = low.shift() - low
    
    plus_dm = np.where((up > down) & (up > 0), up, 0)
    minus_dm = np.where((down > up) & (down > 0), down, 0)
    
    plus_di = 100 * pd.Series(plus_dm).rolling(window=period).mean() / atr
    minus_di = 100 * pd.Series(minus_dm).rolling(window=period).mean() / atr
    
    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di + 1e-6)
    adx = dx.rolling(window=period).mean()
    return adx

# 함수 정의: ATR 계산
def calculate_atr(high, low, close, period=14):
    tr = pd.concat([high - low, abs(high - close.shift()), abs(low - close.shift())], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

# 데이터 로드
df_5min = pd.read_excel('코인_5분봉_org.xlsx')
df_60min = pd.read_excel('코인_60분봉_org.xlsx')

# date 열을 datetime으로 변환
df_5min['date'] = pd.to_datetime(df_5min['date'])
df_60min['date'] = pd.to_datetime(df_60min['date'])

# 60min 데이터로 EMA200 계산
df_60min.set_index('date', inplace=True)
df_60min['EMA200_60min'] = calculate_ema(df_60min['close'], 200)

# 5min 데이터로 지표 계산
df_5min.set_index('date', inplace=True)
df_5min['EMA9_5min'] = calculate_ema(df_5min['close'], 9)
df_5min['EMA21_5min'] = calculate_ema(df_5min['close'], 21)
df_5min['EMA200_5min'] = calculate_ema(df_5min['close'], 200)  # 5min EMA200 for condition 2
df_5min['stoch_k'], df_5min['stoch_d'] = calculate_stoch_rsi(df_5min['close'], 14, 3, 3)
df_5min['ADX_5min'] = calculate_adx(df_5min['high'], df_5min['low'], df_5min['close'], 14)
df_5min['ATR_5min'] = calculate_atr(df_5min['high'], df_5min['low'], df_5min['close'], 14)

# 60min EMA200을 5min에 매핑 (resample or merge)
df_5min = df_5min.join(df_60min['EMA200_60min'], how='left').ffill()  # forward fill for missing

# 신호 생성
df_5min['above_EMA200_60min'] = df_5min['close'] > df_5min['EMA200_60min']
df_5min['EMA21_gt_EMA200_5min'] = df_5min['EMA21_5min'] > df_5min['EMA200_5min']
df_5min['EMA9_cross_EMA21'] = (df_5min['EMA9_5min'].shift(1) < df_5min['EMA21_5min'].shift(1)) & (df_5min['EMA9_5min'] > df_5min['EMA21_5min'])
df_5min['ADX_condition'] = df_5min['ADX_5min'] > 22.5  # 20~25 중간값 22.5 사용

# Stoch RSI 조건: K가 직전 5~10봉 중 최저에서 30 이상 상승 or K > D 크로스 + K > 35
def stoch_condition(row, df):
    idx = df.index.get_loc(row.name)
    if idx < 10:
        return False
    min_k_5_10 = df['stoch_k'].iloc[idx-10:idx-4].min()  # 직전 5~10봉 (idx-10 to idx-5, excluding last 4? adjust)
    strong_rise = (df['stoch_k'].iloc[idx] - min_k_5_10) >= 30
    cross = (df['stoch_k'].shift(1).iloc[idx] <= df['stoch_d'].shift(1).iloc[idx]) & (df['stoch_k'].iloc[idx] > df['stoch_d'].iloc[idx]) & (df['stoch_k'].iloc[idx] > 35)
    return strong_rise or cross

df_5min['stoch_condition'] = df_5min.apply(lambda row: stoch_condition(row, df_5min), axis=1)

# Entry 신호: 모든 조건 만족
df_5min['entry_signal'] = (
    df_5min['above_EMA200_60min'] &
    df_5min['EMA21_gt_EMA200_5min'] &
    df_5min['EMA9_cross_EMA21'] &
    df_5min['stoch_condition'] &
    df_5min['ADX_condition']
)

# 백테스트 로직
initial_capital = 1000000  # 100만원
capital = initial_capital
position = 0  # 포지션 수량 (BTC)
entry_price = 0
stop_loss = 0
risk_per_trade = 0.00875  # 0.75~1% 중간 0.875%
trades = []  # 거래 로그
portfolio_values = []  # 매봉 평가 자산

for idx, row in df_5min.iterrows():
    if position > 0:
        # 익절 체크
        current_price = row['close']
        profit = (current_price - entry_price) / entry_price
        r = (current_price - entry_price) / (entry_price - stop_loss)  # R 계산 (risk unit)
        
        # Trailing stop: EMA21 아래 or Chandelier (entry + ATR * multiplier, but for exit)
        chandelier_exit = current_price - 3 * row['ATR_5min']  # 예시 Chandelier for long: high - ATR*mult, but simplify to trailing
        trailing_stop = max(stop_loss, row['EMA21_5min'])  # EMA21 아래 trailing
        
        if current_price <= trailing_stop:
            # 전체 청산
            capital += position * current_price
            trades[-1]['exit_time'] = idx  # trades[-1]에 추가
            trades[-1]['exit_price'] = current_price
            trades[-1]['reason'] = 'trailing_stop'
            position = 0
        elif r >= 2 and 'partial_exit_2R' not in trades[-1]:
            # 2R: 1/3 청산
            sell_amount = (position * 3 / 2) / 3 if 'partial_exit_1R' in trades[-1] else position / 3  # 조정: 이미 1/3 팔았으면 remaining의 1/2 아님, 원래 plan 1/3 each
            # 간단히: 총 1/3 at 1R, 또 1/3 at 2R, remaining trail
            # position is reduced
            sell_amount = initial_position / 3 if 'initial_position' in trades[-1] else position / 2  # 복잡, simplify
            # better: track initial_position
            if 'initial_position' not in trades[-1]:
                trades[-1]['initial_position'] = position
            initial_pos = trades[-1]['initial_position']
            sell_amount = initial_pos / 3
            if 'partial_exit_1R' in trades[-1]:
                sell_amount = initial_pos / 3  # second 1/3
            capital += sell_amount * current_price
            position -= sell_amount
            trades[-1]['partial_exit_2R'] = current_price
        elif r >= 1 and 'partial_exit_1R' not in trades[-1]:
            initial_pos = position
            trades[-1]['initial_position'] = initial_pos
            sell_amount = initial_pos / 3
            capital += sell_amount * current_price
            position -= sell_amount
            trades[-1]['partial_exit_1R'] = current_price
        
        # 손절 체크 (익절 후에도)
        if current_price <= stop_loss:
            capital += position * current_price
            trades[-1]['exit_time'] = idx
            trades[-1]['exit_price'] = current_price
            trades[-1]['reason'] = 'stop_loss'
            position = 0
    
    if row['entry_signal'] and position == 0:
        risk_amount = capital * risk_per_trade
        atr_sl = 1.8 * row['ATR_5min']
        stop_loss = row['close'] - atr_sl  # 최근 스윙 저점 대신 ATR 사용 (or implement swing low)
        risk_per_unit = row['close'] - stop_loss
        if risk_per_unit <= 0:
            continue  # invalid
        position = risk_amount / risk_per_unit  # BTC 수량
        capital -= position * row['close']  # 매수
        entry_price = row['close']
        trades.append({'entry_time': idx, 'entry_price': entry_price, 'stop_loss': stop_loss})
    
    # 포트폴리오 가치 기록
    portfolio_value = capital + position * row['close']
    portfolio_values.append({'date': idx, 'value': portfolio_value})

# 포트폴리오 df
df_port = pd.DataFrame(portfolio_values).set_index('date')

# 월별 계산
df_port['month'] = df_port.index.to_period('M')
monthly = df_port.groupby('month')['value'].agg(['first', 'last'])
monthly.columns = ['month_start', 'month_end']
monthly['profit'] = monthly['month_end'] - monthly['month_start']
monthly['return'] = monthly['profit'] / monthly['month_start']
monthly['cumulative_return'] = (monthly['month_end'] / initial_capital) - 1

print(monthly)