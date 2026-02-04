import pandas as pd
import matplotlib.pyplot as plt

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

# 년도별 MDD 계산
yearly_mdds = {}
for coin in coins:
    df = df_dict[coin].copy()
    df['year'] = df.index.to_period('Y')
    yearly_mdd = df.groupby('year')['close'].apply(calculate_mdd)
    yearly_mdds[coin] = yearly_mdd

# 월별 MDD 그래프
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('Monthly MDD for Each Coin (%)')
axes = axes.flatten()
for i, coin in enumerate(coins):
    monthly_mdds[coin].plot(ax=axes[i], kind='bar')
    axes[i].set_title(coin)
    axes[i].set_ylabel('MDD (%)')
    axes[i].tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.show()

# 년도별 MDD 그래프
fig, axes = plt.subplots(2, 2, figsize=(15, 10))
fig.suptitle('Yearly MDD for Each Coin (%)')
axes = axes.flatten()
for i, coin in enumerate(coins):
    yearly_mdds[coin].plot(ax=axes[i], kind='bar')
    axes[i].set_title(coin)
    axes[i].set_ylabel('MDD (%)')
    axes[i].tick_params(axis='x', rotation=45)
plt.tight_layout()
plt.show()

# 결과 출력 (콘솔)
print("월별 MDD (%):")
for coin, mdd in monthly_mdds.items():
    print(f"\n{coin}:")
    print(mdd.to_string())

print("\n년도별 MDD (%):")
for coin, mdd in yearly_mdds.items():
    print(f"\n{coin}:")
    print(mdd.to_string())