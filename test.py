import pandas as pd

df = pd.DataFrame({
    'close': [100, 105, 110, 115, 120, 125]
})

sma5 = df['close'].rolling(window=5).mean().iloc[-1]
prev_close = df['close'].iloc[-2]

print(sma5)
print(prev_close)