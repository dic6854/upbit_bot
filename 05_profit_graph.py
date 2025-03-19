import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# 데이터 로드
ticker = "KRW-BTC"
file_name = f"test/backtest/{ticker}_profit_m5.csv"
data = pd.read_csv(file_name)

# 날짜 컬럼 생성
data['date'] = pd.to_datetime(data[['year', 'month', 'day']])

# 일별 통계
daily_stats = data.groupby('date')['profit'].agg(['sum', 'mean', 'min', 'max'])

# 월별 통계
monthly_stats = data.groupby(['year', 'month'])['profit'].agg(['sum', 'mean', 'min', 'max']).reset_index()
monthly_stats['date'] = pd.to_datetime(monthly_stats[['year', 'month']].assign(day=1))

# 년별 통계
yearly_stats = data.groupby('year')['profit'].agg(['sum', 'mean', 'min', 'max']).reset_index()

# 그래프 그리기
font_path = 'C:/Windows/Fonts/malgun.ttf'
font_name = fm.FontProperties(fname=font_path).get_name()
plt.rc('font', family=font_name)
plt.figure(figsize=(15, 10))

# 일별 그래프
plt.subplot(3, 1, 1)
plt.plot(daily_stats.index, daily_stats['sum'], label='일별 총 수익')
plt.title(f'{ticker} 일별 수익')
plt.xlabel('Date')
plt.ylabel('Profit')
plt.legend()

# 월별 그래프
plt.subplot(3, 1, 2)
plt.plot(monthly_stats['date'], monthly_stats['sum'], label='월별 총 수익')
plt.title(f'{ticker} 월별 수익')
plt.xlabel('Date')
plt.ylabel('Profit')
plt.legend()

# 년별 그래프
plt.subplot(3, 1, 3)
plt.bar(yearly_stats['year'], yearly_stats['sum'], label='년별 총 수익')
plt.title(f'{ticker} 년별 수익')
plt.xlabel('Year')
plt.ylabel('Profit')
plt.legend()

plt.tight_layout()
plt.show()

# 통계 자료 출력
print("Daily Statistics:")
print(daily_stats)

print("\nMonthly Statistics:")
print(monthly_stats)

print("\nYearly Statistics:")
print(yearly_stats)