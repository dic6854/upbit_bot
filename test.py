import pyupbit
import pandas as pd
import time

RSI_PERIOD = 14 

df = pd.DataFrame(columns=['ticker', 'price_change', 'volume_change', 'ma5', 'rsi', 'current_price'])

tickers = pyupbit.get_tickers(fiat="KRW")
rising_coins = []
i = 1
for ticker in tickers:
    df_day = pyupbit.get_ohlcv(ticker, interval="day", count=(RSI_PERIOD+1))

    time.sleep(0.2)

    current_price = pyupbit.get_current_price(ticker)
    prev_close = df_day['close'].iloc[-2]
    price_change = (current_price - prev_close) / prev_close * 100

    current_volume = df_day['volume'].iloc[-1]
    prev_volume = df_day['volume'].iloc[-2]
    volume_change = (current_volume - prev_volume) / prev_volume if prev_volume > 0 else 0

    ma5 = df_day['close'].rolling(window=5).mean().iloc[-1]

    delta = df_day['close'].diff()
    gain = delta.where(delta > 0, 0).rolling(window=RSI_PERIOD).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
    rs = gain / loss if loss.iloc[-2] != 0 else float('inf')
    rsi = 100 - (100 / (1 + rs.iloc[-2]))

    rising_coins.append({'ticker': ticker, 'price_change': price_change, 'volume_change': volume_change, 'ma5': ma5, 'rsi': rsi, 'current_price': current_price})

    if i == 5:
        break
    i += 1

rising_coins_df = pd.DataFrame(rising_coins)
df = pd.concat([df, rising_coins_df], ignore_index=True)

print(df)

