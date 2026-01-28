import pandas as pd
import numpy as np

# 수정된 지표 함수 (division by zero 방지)
def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / (loss + 1e-10)  # epsilon 추가
    rsi_val = 100 - (100 / (1 + rs))
    rsi_val = rsi_val.fillna(50)  # both 0인 경우 중립 50으로
    return rsi_val

def stoch_rsi(rsi_series, stoch_period=14, k_period=3, d_period=3):
    lowest_rsi = rsi_series.rolling(stoch_period).min()
    highest_rsi = rsi_series.rolling(stoch_period).max()
    denom = (highest_rsi - lowest_rsi + 1e-10)  # epsilon 추가
    stoch_rsi_val = ((rsi_series - lowest_rsi) / denom) * 100
    k = stoch_rsi_val.rolling(k_period).mean()
    d = k.rolling(d_period).mean()
    return k, d

def atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = np.abs(high - close.shift())
    tr3 = np.abs(low - close.shift())
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    tr = tr.replace(0, 1e-10)  # 0 방지
    return tr.ewm(span=period, adjust=False).mean()

def adx(high, low, close, period=14):
    tr = atr(high, low, close, period)
    up = high - high.shift(1)
    down = low.shift(1) - low
    pdm = np.where((up > down) & (up > 0), up, 0)
    mdm = np.where((down > up) & (down > 0), down, 0)
    pdm_ema = pd.Series(pdm).ewm(span=period, adjust=False).mean()
    mdm_ema = pd.Series(mdm).ewm(span=period, adjust=False).mean()
    pdi = (pdm_ema / (tr + 1e-10)) * 100  # epsilon
    mdi = (mdm_ema / (tr + 1e-10)) * 100
    denom = (pdi + mdi + 1e-10)
    dx = np.abs(pdi - mdi) / denom * 100
    adx_val = dx.ewm(span=period, adjust=False).mean()
    return adx_val

# Load data
print("1. 파일 로드 중...")
df = pd.read_excel('코인_5분봉_지표org.xlsx')
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)
print(f"원본 데이터 행 수: {len(df)}")

# Resample to 1H (경고 무시 또는 'h'로 변경)
print("2. 1시간봉 생성 중...")
df_1h = df.resample('1h').agg({'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last'})
df_1h['EMA200_1h'] = df_1h['close'].ewm(span=100, adjust=False).mean()  # 200 → 100으로 줄임 (NaN 줄이기)
print(f"1시간봉 행 수: {len(df_1h)}")

print("3. 1시간 EMA200 매핑 중...")
df['EMA200_1h'] = df.index.map(lambda x: df_1h['EMA200_1h'].asof(x))

# Compute 5min indicators
print("4. 5분 지표 계산 중...")
df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ATR'] = atr(df['high'], df['low'], df['close'], 14)
df['ADX'] = adx(df['high'], df['low'], df['close'], 14)

rsi_val = rsi(df['close'], 14)
df['StochRSI_K'], df['StochRSI_D'] = stoch_rsi(rsi_val, 14, 3, 3)

# NaN 디버깅
print("5. NaN 제거 전 행 수:", len(df))
print("NaN per column:\n", df.isna().sum())

# NaN 처리: ffill + bfill (앞뒤 값으로 채움, 초기 NaN 처리)
df = df.fillna(method='ffill').fillna(method='bfill')

print("NaN 채움 후 행 수:", len(df))
print("남은 NaN per column:\n", df.isna().sum())

if df.isna().any().any():
    print("!!! 여전히 NaN 존재. 데이터 확인 필요.")
    df = df.dropna()  # 최종 dropna
    print("최종 dropna 후 행 수:", len(df))
    if len(df) == 0:
        print("여전히 0행. 데이터에 심각한 문제 (e.g., 모든 close 동일?). 파일 샘플 확인하세요.")
        exit()

# Backtest
capital = 1000000.0
in_position = False
position_quantity = 0.0
position_entry = 0.0
position_stop = 0.0
position_r = 0.0
position_tp1 = 0.0
position_tp2 = 0.0
portions = [1/3, 1/3, 1/3]
exited_portions = 0

capital_history = pd.Series(index=df.index, dtype=float)
capital_history.iloc[0] = capital

for i in range(10, len(df)):
    idx = df.index[i]
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    # Update history
    if in_position:
        unrealized = position_quantity * (prev_row['close'] - position_entry)
        capital_history.iloc[i-1] = capital + unrealized
    else:
        capital_history.iloc[i-1] = capital

    # Exits
    if in_position:
        if row['low'] <= position_stop:
            exit_price = position_stop
            pnl = position_quantity * (exit_price - position_entry)
            capital += pnl
            in_position = False
            exited_portions = 0
            continue

        if exited_portions < 1 and row['high'] >= position_tp1:
            exit_qty = position_quantity * portions[0]
            pnl = exit_qty * (position_tp1 - position_entry)
            capital += pnl
            position_quantity -= exit_qty
            exited_portions += 1

        if exited_portions < 2 and row['high'] >= position_tp2:
            exit_qty = position_quantity * portions[1]
            pnl = exit_qty * (position_tp2 - position_entry)
            capital += pnl
            position_quantity -= exit_qty
            exited_portions += 1

        if exited_portions >= 2:
            trailing_stop = row['EMA21']
            if row['low'] <= trailing_stop:
                exit_price = trailing_stop
                pnl = position_quantity * (exit_price - position_entry)
                capital += pnl
                in_position = False
                exited_portions = 0
                continue

    # Entry
    if row['close'] > row['EMA200_1h'] and row['EMA21'] > row['EMA200']:
        if prev_row['EMA9'] <= prev_row['EMA21'] and row['EMA9'] > row['EMA21']:
            if row['ADX'] > 20:
                recent_k_min = df['StochRSI_K'].iloc[i-10:i].min()
                stoch_cond1 = (prev_row['StochRSI_K'] == recent_k_min) and (row['StochRSI_K'] >= 30)
                stoch_cond2 = (prev_row['StochRSI_K'] <= prev_row['StochRSI_D']) and (row['StochRSI_K'] > row['StochRSI_D']) and (row['StochRSI_K'] > 35)
                if stoch_cond1 or stoch_cond2:
                    entry_price = row['close']
                    stop_price = entry_price - 1.8 * row['ATR']
                    if stop_price >= entry_price:
                        continue
                    risk_per_unit = entry_price - stop_price
                    risk_amount = capital * 0.01
                    position_quantity = risk_amount / risk_per_unit
                    position_entry = entry_price
                    position_stop = stop_price
                    position_r = risk_per_unit
                    position_tp1 = entry_price + 1 * position_r
                    position_tp2 = entry_price + 2 * position_r
                    in_position = True
                    exited_portions = 0

# Last bar
if len(capital_history) > 0:
    last_price = df.iloc[-1]['close']
    if in_position:
        unrealized = position_quantity * (last_price - position_entry)
        capital_history.iloc[-1] = capital + unrealized
    else:
        capital_history.iloc[-1] = capital

capital_history = capital_history.ffill().bfill()

# Monthly calculations
df['month'] = df.index.to_period('M')
monthly = capital_history.resample('M').agg(['first', 'last'])
monthly['profit'] = monthly['last'] - monthly['first']
monthly['return_rate'] = (monthly['profit'] / monthly['first'] * 100).fillna(0)

results = []
for month, row in monthly.iterrows():
    results.append({
        'Month': str(month.to_period('M')),
        '월초평가자산': f"{row['first']:,.0f}원",
        '월말평가자산': f"{row['last']:,.0f}원",
        '수익금': f"{row['profit']:,.0f}원",
        '수익률': f"{row['return_rate']:.2f}%"
    })

# Total cumulative return
final_balance = capital_history.iloc[-1]
total_cumulative_return = ((final_balance - 1000000.0) / 1000000.0) * 100

monthly_df = pd.DataFrame(results)
print(monthly_df.to_string(index=False))
print(f"\n총 누적 수익률: {total_cumulative_return:.2f}%")