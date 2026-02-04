import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates

# 파일 경로
file_path = '60min.xlsx'

# 코인 목록과 시트 이름
coins = ['BTC', 'XRP', 'ETH', 'ADA']

# 각 코인 데이터 로드
df_dict = {}
for coin in coins:
    df = pd.read_excel(file_path, sheet_name=coin)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df_dict[coin] = df

# MDD 계산 함수
def calculate_mdd(series):
    peak = series.expanding(min_periods=1).max()
    drawdown = (series - peak) / peak
    mdd = drawdown.min()
    return mdd * 100  # 퍼센트로 변환

# 월별 MDD 계산
monthly_mdds = {}
for coin in coins:
    df = df_dict[coin].copy()
    df['month'] = df.index.to_period('M')
    monthly_mdd = df.groupby('month')['close'].apply(calculate_mdd)
    monthly_mdds[coin] = monthly_mdd

# 년도별 MDD 계산 (참고용으로 유지)
yearly_mdds = {}
for coin in coins:
    df = df_dict[coin].copy()
    df['year'] = df.index.to_period('Y')
    yearly_mdd = df.groupby('year')['close'].apply(calculate_mdd)
    yearly_mdds[coin] = yearly_mdd

# 월별 MDD 그래프 - x축 6개월 간격으로 표시
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
fig.suptitle('Monthly Maximum Drawdown (MDD) for Each Coin (%)', fontsize=16)

axes = axes.flatten()

for i, coin in enumerate(coins):
    ax = axes[i]
    mdd_series = monthly_mdds[coin]
    
    # 인덱스를 datetime으로 변환 (to_timestamp 사용)
    x_dates = mdd_series.index.to_timestamp()
    ax.plot(x_dates, mdd_series.values, marker='o', linestyle='-', markersize=4)
    
    ax.set_title(f'{coin} - Monthly MDD', fontsize=12)
    ax.set_ylabel('MDD (%)', fontsize=10)
    ax.grid(True, linestyle='--', alpha=0.7)
    
    # x축을 6개월 간격으로 설정
    ax.xaxis.set_major_locator(mdates.MonthLocator(interval=6))
    ax.xaxis.set_major_formatter(mdates.DateFormatter('%Y-%m'))
    
    # x축 레이블 회전 및 간격 조정
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
    
    # y축 범위 조정 (필요 시)
    ax.set_ylim(min(mdd_series.min() * 1.1, -100), 5)  # MDD는 보통 음수이므로 아래쪽으로 넓게

plt.tight_layout(rect=[0, 0, 1, 0.96])  # suptitle 공간 확보
plt.show()

# 콘솔에 결과 요약 출력 (선택)
print("월별 MDD 최저값 (가장 큰 낙폭) 요약:")
for coin in coins:
    worst_mdd = monthly_mdds[coin].min()
    worst_month = monthly_mdds[coin].idxmin()
    print(f"{coin}: {worst_mdd:.2f}% (최악 시점: {worst_month})")

print("\n년도별 MDD 요약:")
for coin in coins:
    print(f"\n{coin}:")
    print(yearly_mdds[coin].to_string())