import pandas as pd
from datetime import datetime
import ta

# 데이터 불러오기
file = "mydata/KRW-XRP.xlsx"
df1 = pd.read_excel(file, index_col=0, parse_dates=True)

start_date1 = "2024-02-23 09:00:00"
stop_date1 = "2024-04-10 09:00:00"

date_format = "%Y-%m-%d %H:%M:%S"
start_date = datetime.strptime(start_date1, date_format)
stop_date = datetime.strptime(stop_date1, date_format)

df = df1.reset_index()
df = df[(df['index'] >= start_date) & (df['index'] <= stop_date)].set_index('index').copy()


# 볼린저 밴드 계산
bb = ta.volatility.BollingerBands(df['close'], window=20, window_dev=2)
df['BB_Middle'] = bb.bollinger_mavg()
df['BB_Upper'] = bb.bollinger_hband()
df['BB_Lower'] = bb.bollinger_lband()

# MACD 계산
macd = ta.trend.MACD(df['close'], window_slow=26, window_fast=12, window_sign=9)
df['MACD'] = macd.macd()
df['MACD_Signal'] = macd.macd_signal()

# 매수/매도 신호 생성
df['Buy_Signal'] = (df['close'] < df['BB_Lower']) & (df['MACD'] > df['MACD_Signal'])
df['Sell_Signal'] = (df['close'] > df['BB_Upper']) & (df['MACD'] < df['MACD_Signal'])

# 초기 자본 설정
initial_capital = 1000000  # 100만 원
capital = initial_capital
position = 0

# 백테스팅 로직
for index, row in df.iterrows():
    if row['Buy_Signal'] and capital > 0:
        position = capital / row['close']
        capital = 0
    elif row['Sell_Signal'] and position > 0:
        capital = position * row['close']
        position = 0

# 마지막 포지션 청산
if position > 0:
    capital = position * df['close'].iloc[-1]
    position = 0

# 수익률 평가
profit = capital - initial_capital
roi = (profit / initial_capital) * 100

print(f"최종 수익: {profit:.2f}원")
print(f"수익률: {roi:.2f}%")