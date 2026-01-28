import pandas as pd
import numpy as np

def rsi(series, period=14):
    delta = series.diff()
    gain = delta.where(delta > 0, 0).rolling(window=period).mean()
    loss = -delta.where(delta < 0, 0).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

def atr(high, low, close, period=14):
    tr1 = high - low
    tr2 = np.abs(high - close.shift())
    tr3 = np.abs(low - close.shift())
    tr = pd.DataFrame({'tr1': tr1, 'tr2': tr2, 'tr3': tr3}).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()

# Load data
df = pd.read_excel('코인_5분봉_지표org.xlsx')
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# Compute indicators
df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
df['ATR'] = atr(df['high'], df['low'], df['close'], 14)

rsi_period = 14
stoch_period = 14
k_period = 3
d_period = 3

rsi_val = rsi(df['close'], rsi_period)
lowest_rsi = rsi_val.rolling(stoch_period).min()
highest_rsi = rsi_val.rolling(stoch_period).max()
stoch_rsi_val = ((rsi_val - lowest_rsi) / (highest_rsi - lowest_rsi)) * 100
df['StochRSI_K'] = stoch_rsi_val.rolling(k_period).mean()
df['StochRSI_D'] = df['StochRSI_K'].rolling(d_period).mean()

# Drop NaN rows
df = df.dropna()

# Backtest
capital = 1000000.0
in_position = False
position_quantity = 0.0
position_entry = 0.0
position_stop = 0.0
position_tp = 0.0
half_sold = False
position_time = None

capital_history = pd.Series(index=df.index, dtype=float)

for i in range(1, len(df)):
    idx = df.index[i]
    row = df.iloc[i]
    prev_row = df.iloc[i-1]

    # Update capital history with mark-to-market for previous bar
    if in_position:
        unrealized = position_quantity * (prev_row['close'] - position_entry)
        capital_history.iloc[i-1] = capital + unrealized
    else:
        capital_history.iloc[i-1] = capital

    # Check exits if in position
    if in_position:
        # Check stop loss (using low for potential hit)
        if row['low'] <= position_stop:
            exit_price = position_stop
            pnl = position_quantity * (exit_price - position_entry)
            capital += pnl
            in_position = False
            half_sold = False
            continue

        # Check TP if not half sold (using high for potential hit)
        if not half_sold:
            if row['high'] >= position_tp:
                half_qty = position_quantity / 2
                pnl = half_qty * (position_tp - position_entry)
                capital += pnl
                position_quantity = half_qty
                half_sold = True

        # Check trailing exit if half sold
        if half_sold:
            if row['close'] < row['EMA9']:
                exit_price = row['close']
                pnl = position_quantity * (exit_price - position_entry)
                capital += pnl
                in_position = False
                half_sold = False
                continue

    # Check entry
    if row['close'] > row['EMA200']:
        if prev_row['EMA9'] <= prev_row['EMA21'] and row['EMA9'] > row['EMA21']:
            stoch_condition = False
            if row['StochRSI_K'] <= 20 and row['StochRSI_K'] > prev_row['StochRSI_K']:
                stoch_condition = True
            if prev_row['StochRSI_K'] <= prev_row['StochRSI_D'] and row['StochRSI_K'] > row['StochRSI_D']:
                stoch_condition = True
            if stoch_condition:
                entry_price = row['close']
                stop_price = row['EMA21'] - row['ATR']
                if stop_price >= entry_price:
                    continue
                risk_per_unit = entry_price - stop_price
                risk_amount = capital * 0.02
                position_quantity = risk_amount / risk_per_unit
                position_entry = entry_price
                position_stop = stop_price
                position_tp = entry_price + 1.5 * risk_per_unit
                position_time = idx
                in_position = True
                half_sold = False

# Last bar capital
if in_position:
    unrealized = position_quantity * (df.iloc[-1]['close'] - position_entry)
    capital_history.iloc[-1] = capital + unrealized
else:
    capital_history.iloc[-1] = capital

# Monthly calculations
df['month'] = df.index.to_period('M')
monthly_groups = df.groupby('month')

results = []
initial_capital = 1000000.0

for month, group in monthly_groups:
    month_start_idx = group.index[0]
    month_end_idx = group.index[-1]
    start_balance = capital_history[month_start_idx]
    end_balance = capital_history[month_end_idx]
    profit = end_balance - start_balance
    return_rate = (profit / start_balance * 100) if start_balance > 0 else 0.0
    results.append({
        'Month': str(month),
        '월초평가자산': f"{start_balance:,.0f}원",
        '월말평가자산': f"{end_balance:,.0f}원",
        '수익금': f"{profit:,.0f}원",
        '수익률': f"{return_rate:.2f}%"
    })

# Total cumulative return
final_balance = capital_history.iloc[-1]
total_cumulative_return = ((final_balance - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0

monthly_df = pd.DataFrame(results)
print(monthly_df.to_string(index=False))
print(f"\n총 누적 수익률: {total_cumulative_return:.2f}%")