import pyupbit
import pandas as pd
import time

date_str = "2025-07-20 09:00:00"

tickers = pyupbit.get_tickers(fiat="KRW")
t_tickers = len(tickers)

coin_value = []
i = 1
for ticker in tickers:
    df = pyupbit.get_ohlcv(ticker, interval="day", to=date_str, count=1)
    value = df['value'].iloc[-1]

    coin_value.append({
        'ticker': ticker,
        'value': value
    })

    print(f"[{i}/{t_tickers}] - [{ticker}'s Value] - {value:,.2f}")

    i += 1
    time.sleep(0.1)

df_values = pd.DataFrame(coin_value)
df_sorted_values = df_values.sort_values(by='value', ascending=False)
value1 = df_sorted_values['value'].iloc[0]
print(f"{value1:,.2f}")

df_sorted_values['value_formatted'] = df_sorted_values['value'].apply(lambda x: f"{x:,.0f}원")

tickers = []

for i in range(20):
    ticker = df_sorted_values['ticker'].iloc[i]
    print(ticker)