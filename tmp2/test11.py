import pandas as pd
import mplfinance as mpf
import ta

# 엑셀 파일 불러오기
# 날짜를 인덱스로 지정하고 datetime 형식으로 변환
file = "mydata/KRW-BTC.xlsx"
df = pd.read_excel(file, index_col=0, parse_dates=True)

# 데이터 확인
print(df.head())

# Simple Moving Average (SMA) 추가
df['SMA20'] = ta.trend.sma_indicator(df['close'], window=20)

# Relative Strength Index (RSI) 추가
df['RSI14'] = ta.momentum.rsi(df['close'], window=14)

# Bollinger Bands 추가
indicator_bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
df['BB_upper'] = indicator_bb.bollinger_hband()
df['BB_lower'] = indicator_bb.bollinger_lband()

# SMA와 Bollinger Bands 플롯 추가 설정
apds = [
    mpf.make_addplot(df['SMA20'], color='blue', label='SMA20'),
    mpf.make_addplot(df['BB_upper'], color='red', linestyle='dotted', label='BB Upper'),
    mpf.make_addplot(df['BB_lower'], color='green', linestyle='dotted', label='BB Lower'),
]

# 차트 출력
mpf.plot(df, type='candle', volume=True, addplot=apds, style='yahoo', title='KRW-BTC Technical Analysis')

# RSI 데이터 출력 (RSI는 차트에 표시 X, 콘솔 출력용)
print(df[['RSI14']].tail())