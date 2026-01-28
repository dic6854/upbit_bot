import pandas as pd
import numpy as np

period=14

file_name = "hdata\코인_5분봉_org.xlsx"
df = pd.read_excel(file_name)
df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
print("읽어들임 완료!!")

df['High-Low'] = df['high'] - df['low']
df['High-PrevClose'] = abs(df['high'] - df['close'].shift(1))
df['Low-PrevClose'] = abs(df['low'] - df['close'].shift(1))
    
df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)
df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()

df['STOP'] = df['close'] - df['ATR'] * 2

print(df)
df.to_excel("hdata\코인_5분봉_ATR.xlsx", index=False, sheet_name="비트코인")
print("저장완료!")

# 1. 차트로 간단히 확인 (matplotlib)
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 2. 'date' 컬럼을 datetime 타입으로 변환하고 인덱스로 설정하여 플롯의 xlabel에 정확하게 표시
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# 3. 플롯 그리기
plt.figure(figsize=(14, 7), dpi=100)
plt.rc('font', family='Malgun Gothic')

# 4. 선 색상과 두께 설정 (시각적으로 구분 잘 되도록)
plt.plot(df.index, df['close'],  label='종가',   color='#1f77b4', linewidth=2.0, alpha=0.9)
plt.plot(df.index, df['STOP'],   label='손절가',   color='#ff7f0e', linewidth=2.2)

# 5. 그래프 꾸미기
plt.title('BTC-KRW 일봉 + 손절가', fontsize=14, pad=15)
plt.xlabel('날짜', fontsize=12)
plt.ylabel('가격 (KRW)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# 6. 범례 위치 (그래프가 가려지지 않도록)
plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., fontsize=11)

# 7. 날짜 축 포맷 예쁘게 (최근 1~2년 데이터 기준)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.gca().xaxis.set_major_locator(mdates.MinuteLocator(interval=30))    # 30분 간격
plt.xticks(rotation=30)

# 8. 여백 조정
plt.tight_layout()

# 9. 보여주기
plt.show()