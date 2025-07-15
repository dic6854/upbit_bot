import mplfinance as mpf
import pandas as pd
import ta
from ta.trend import sma_indicator

df = pd.read_excel("mydata/KRW-BTC.xlsx")

df['SMA'] = sma_indicator(df['close'], window=5)

df.index = pd.to_datetime(df.index)

apds = [mpf.make_addplot(df["SMA"], color="red")] 
mpf.plot(df, type="candle", volume=True, addplot=apds, style="yahoo", warn_too_much_data=1000)