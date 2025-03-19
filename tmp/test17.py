import pandas as pd
import ta  # 기술적 지표 라이브러리
import matplotlib.pyplot as plt

# 데이터 불러오기
file = "data/KRW-BTC.xlsx"
df = pd.read_excel(file, index_col=0, parse_dates=True, engine='openpyxl')
df = df.sort_index()  # 날짜 순서 정렬
df = df.groupby(df.index).last()  # 날짜가 중복된 경우 뒤의 것을 유지하고 앞을 것을 삭제한다.

# 매수/매도 조건 설정
df['Buy_Signal'] = (df['close'] < df['BB_Lower']) & (df['MACD_26_12'] > df['MACD_Signal_26_12_9']) & (df['RSI_14'] < 30)
df['Sell_Signal'] = (df['close'] > df['BB_Upper']) & (df['MACD_26_12'] < df['MACD_Signal_26_12_9']) & (df['RSI_14'] > 70)

# 백테스팅 초기 자본
initial_capital = 1000000  # 100만 원
capital = initial_capital
position = 0

# 백테스트 실행
for index, row in df.iterrows():
    if row['Buy_Signal'] and capital > 0:
        position = capital / row['close']
        capital = 0
        print(f"[BUY] {index.date()} - Price: {row['close']:.2f}")
    elif row['Sell_Signal'] and position > 0:
        capital = position * row['close']
        position = 0
        print(f"[SELL] {index.date()} - Price: {row['close']:.2f} - Capital : {capital}")

# 최종 자본 계산
if position > 0:
    capital = position * df['close'].iloc[-1]

profit = capital - initial_capital
roi = (profit / initial_capital) * 100

print(f"최종 수익: {profit:.2f}원")
print(f"수익률: {roi:.2f}%")

# 그래프 시각화
plt.figure(figsize=(14, 7))
plt.plot(df['close'], label='Close Price', color='blue')
plt.plot(df['BB_Upper'], label='BB Upper', linestyle='--', color='red')
plt.plot(df['BB_Lower'], label='BB Lower', linestyle='--', color='green')
plt.title('BTC Price with Bollinger Bands')
plt.legend()
plt.show()
