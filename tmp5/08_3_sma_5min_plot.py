import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

file_name = "코인_5분봉_2026.xlsx"
df = pd.read_excel(file_name)
df = df.sort_values(by='date', ascending=True).reset_index(drop=True)

print("읽어들임 완료!!")

# 2. 'date' 컬럼을 datetime 타입으로 변환하고 인덱스로 설정하여 플롯의 xlabel에 정확하게 표시
df['date'] = pd.to_datetime(df['date'])
df.set_index('date', inplace=True)

# 3. 플롯 그리기
plt.figure(figsize=(14, 7), dpi=100)
plt.rc('font', family='Malgun Gothic')

# 4. 선 색상과 두께 설정 (시각적으로 구분 잘 되도록)
plt.plot(df.index, df['close'],  label='종가',   color='#1f77b4', linewidth=1.0, alpha=0.9)
plt.plot(df.index, df['SMA5'],   label='SMA5',   color='#ff7f0e', linewidth=1.2)
plt.plot(df.index, df['SMA30'],  label='SMA30',  color='#2ca02c', linewidth=1.4)
plt.plot(df.index, df['SMA60'],  label='SMA60',  color='#d62728', linewidth=1.6)
plt.plot(df.index, df['SMA300'], label='SMA300', color='#9467bd', linewidth=2.2, alpha=0.9)
plt.plot(df.index, df['SMA600'], label='SMA600', color="#3228c2", linewidth=2.2, alpha=0.9)
plt.plot(df.index, df['SMA900'], label='SMA900', color="#097a22", linewidth=2.2, alpha=0.9)

# 5. 그래프 꾸미기
plt.title('BTC-KRW 일봉 + 다중 이동평균 (SMA5/30/60/300)', fontsize=14, pad=15)
plt.xlabel('날짜', fontsize=12)
plt.ylabel('가격 (KRW)', fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# 6. 범례 위치 (그래프가 가려지지 않도록)
plt.legend(loc='upper left', bbox_to_anchor=(1.02, 1), borderaxespad=0., fontsize=11)

# 7. 날짜 축 포맷 예쁘게 (최근 1~2년 데이터 기준)
plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
plt.gca().xaxis.set_major_locator(mdates.DayLocator(interval=7))  # 3개월 간격
plt.xticks(rotation=30)

# 8. 여백 조정
plt.tight_layout()

# 9. 보여주기
plt.show()
