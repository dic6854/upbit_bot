import pandas as pd
import ta

# 엑셀 파일 불러오기 (5분봉 데이터)
# 날짜를 인덱스로 지정하고 datetime 형식으로 변환
file = "mydata/KRW-BTC.xlsx"
df = pd.read_excel(file, index_col=0, parse_dates=True)

# 데이터 확인
print(df.head())

# Simple Moving Average (SMA) 추가 (단기 9일, 장기 21일)
df['SMA9'] = ta.trend.sma_indicator(df['close'], window=9)
df['SMA21'] = ta.trend.sma_indicator(df['close'], window=21)

# Relative Strength Index (RSI) 추가
df['RSI14'] = ta.momentum.rsi(df['close'], window=14)

# 매매 신호 생성 (SMA9 > SMA21 및 RSI14 < 30 -> 매수, SMA9 < SMA21 및 RSI14 > 70 -> 매도)
df['Buy_Signal'] = (df['SMA9'] > df['SMA21']) & (df['RSI14'] < 30)
df['Sell_Signal'] = (df['SMA9'] < df['SMA21']) & (df['RSI14'] > 70)

# 초기 자본 설정
initial_capital = 1000000  # 100만 원
capital = initial_capital
position = 0

# 백테스팅 로직
for index, row in df.iterrows():
    if row['Buy_Signal'] and capital > 0:
        position = capital / row['close']
        capital = 0
        print(f"[BUY] {index} - Price: {row['close']:.2f}, Position: {position:.6f}")
    elif row['Sell_Signal'] and position > 0:
        capital = position * row['close']
        position = 0
        print(f"[SELL] {index} - Price: {row['close']:.2f}, Capital: {capital:.2f}")

# 마지막 포지션 청산
if position > 0:
    capital = position * df['close'].iloc[-1]
    position = 0
    print(f"[FINAL SELL] {df.index[-1]} - Price: {df['close'].iloc[-1]:.2f}, Capital: {capital:.2f}")

# 수익률 평가
profit = capital - initial_capital
roi = (profit / initial_capital) * 100
print(f"Initial Capital: {initial_capital:.2f} KRW")
print(f"Final Capital: {capital:.2f} KRW")
print(f"Profit: {profit:.2f} KRW")
print(f"ROI: {roi:.2f}%")