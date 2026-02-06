import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.font_manager as fm
import matplotlib as mpl

# ── 한글 폰트 설정 (가장 중요한 부분) ───────────────────────────────
# Windows: Malgun Gothic (대부분 설치되어 있음)
# Mac: AppleGothic 또는 NanumGothic
# Linux: NanumGothic 등 설치 필요

plt.rc('font', family='Malgun Gothic')          # Windows 기본 한글 폰트
# plt.rc('font', family='AppleGothic')           # Mac용 (필요 시 주석 해제)
# plt.rc('font', family='NanumGothic')           # Linux / 추가 설치 시

# 음수 기호(-) 깨짐 방지
plt.rcParams['axes.unicode_minus'] = False

# (선택) 폰트 캐시 갱신 → 처음 실행 시 한 번만 필요할 수 있음
# fm._rebuild()   # 주석 해제하면 느려질 수 있으니 처음 깨질 때만 사용

# 만약 위 설정으로도 안 되면 아래처럼 명시적으로 폰트 파일 경로 지정 가능
# font_path = r'C:\Windows\Fonts\malgun.ttf'          # Windows 예시
# fontprop = fm.FontProperties(fname=font_path)
# plt.rc('font', family=fontprop.get_name())

# ──────────────────────────────────────────────────────────────────────

# 상수 설정
TOTAL_ASSETS = 10000000         # 1000만원
INVESTMENT_RATIO = 0.20         # 전체 자산의 20%만 투자
NUM_COINS = 4
INVEST_PER_COIN = TOTAL_ASSETS * INVESTMENT_RATIO / NUM_COINS  # 각 코인당 500,000원
FEE_RATE = 0.0005               # 0.05%

# 엑셀 파일에서 데이터 로드
file_path = 'day.xlsx'
coins = ['BTC', 'XRP', 'ETH', 'ADA']

data = {}
for coin in coins:
    df = pd.read_excel(file_path, sheet_name=coin)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df['MA5'] = df['close'].rolling(window=5).mean()
    data[coin] = df.dropna()  # MA5 계산으로 인해 앞 4일은 제거

# 모든 코인이 공통으로 존재하는 날짜만 사용
common_dates = set(data['BTC'].index)
for coin in coins[1:]:
    common_dates.intersection_update(data[coin].index)
common_dates = sorted(list(common_dates))

# 포트폴리오 초기화 - float 타입으로
portfolio = pd.DataFrame(
    index=common_dates,
    columns=['total_value', 'cash', 'holdings_value'],
    data=0.0
)

initial_cash = TOTAL_ASSETS * (1 - INVESTMENT_RATIO)
portfolio['cash'] = initial_cash
portfolio['total_value'] = initial_cash

# 포지션 및 투자금 추적
positions = {coin: 0.0 for coin in coins}
invested_amount = {coin: 0.0 for coin in coins}

trade_logs = []

# 백테스팅 시뮬레이션
for i, date in enumerate(common_dates):
    if i > 0:
        prev_date = common_dates[i-1]
        portfolio.loc[date, 'cash'] = portfolio.loc[prev_date, 'cash']

    current_holdings_value = 0.0

    for coin in coins:
        row = data[coin].loc[date]
        close = row['close']
        ma5 = row['MA5']

        if positions[coin] > 0:
            if close < ma5:
                sell_value = positions[coin] * close
                fee = sell_value * FEE_RATE
                cash_in = sell_value - fee
                portfolio.loc[date, 'cash'] += cash_in

                avg_buy_price = invested_amount[coin] / positions[coin] if positions[coin] > 0 else 0
                pl = (close - avg_buy_price) * positions[coin] - fee

                trade_logs.append({
                    'date': date,
                    'coin': coin,
                    'action': 'sell',
                    'price': close,
                    'quantity': positions[coin],
                    'profit_loss': pl
                })

                positions[coin] = 0.0
                invested_amount[coin] = 0.0
        else:
            if close > ma5:
                remaining_alloc = INVEST_PER_COIN - invested_amount[coin]
                buy_amount = min(remaining_alloc, portfolio.loc[date, 'cash'])
                
                if buy_amount > 0:
                    fee = buy_amount * FEE_RATE
                    actual_buy = buy_amount - fee
                    qty = actual_buy / close

                    portfolio.loc[date, 'cash'] -= buy_amount
                    positions[coin] += qty
                    invested_amount[coin] += buy_amount

                    trade_logs.append({
                        'date': date,
                        'coin': coin,
                        'action': 'buy',
                        'price': close,
                        'quantity': qty,
                        'profit_loss': 0.0
                    })

        current_holdings_value += positions[coin] * close

    portfolio.loc[date, 'holdings_value'] = current_holdings_value
    portfolio.loc[date, 'total_value'] = portfolio.loc[date, 'cash'] + current_holdings_value

# ── 결과 분석 ────────────────────────────────────────────────────────
trade_df = pd.DataFrame(trade_logs)
trade_df['month'] = trade_df['date'].dt.to_period('M')
trade_df['year'] = trade_df['date'].dt.to_period('Y')

sells = trade_df[trade_df['action'] == 'sell'].copy()

monthly_stats = sells.groupby('month')['profit_loss'].agg(
    total_pl='sum',
    avg_pl='mean',
    count='count'
)

monthly_wins = sells[sells['profit_loss'] > 0].groupby('month').size()
monthly_total = sells.groupby('month').size()
monthly_winrate = (monthly_wins / monthly_total).fillna(0) * 100

avg_profit = sells[sells['profit_loss'] > 0].groupby('month')['profit_loss'].mean()
avg_loss = sells[sells['profit_loss'] < 0].groupby('month')['profit_loss'].mean().abs()
monthly_pl_ratio = (avg_profit / avg_loss).fillna(0)

monthly_stats = monthly_stats.join(monthly_winrate.rename('winrate_%'))
monthly_stats = monthly_stats.join(monthly_pl_ratio.rename('profit_loss_ratio'))

# MDD
portfolio['peak'] = portfolio['total_value'].cummax()
portfolio['drawdown'] = (portfolio['total_value'] - portfolio['peak']) / portfolio['peak'] * 100
portfolio['month'] = portfolio.index.to_period('M')
portfolio['year'] = portfolio.index.to_period('Y')

monthly_mdd = portfolio.groupby('month')['drawdown'].min()
yearly_mdd = portfolio.groupby('year')['drawdown'].min()

# ── 출력 ──────────────────────────────────────────────────────────────
print("월별 통계")
print(monthly_stats.round(2))

print("\n월별 MDD (%)")
print(monthly_mdd.round(2))

print("\n연도별 MDD (%)")
print(yearly_mdd.round(2))

# ── 그래프 ────────────────────────────────────────────────────────────
fig, axs = plt.subplots(3, 2, figsize=(14, 12))
fig.suptitle("백테스트 결과", fontsize=16)

axs[0, 0].plot(portfolio.index, portfolio['total_value'], label='총 자산 가치')
axs[0, 0].set_title('포트폴리오 가치 추이')
axs[0, 0].set_xlabel('날짜')
axs[0, 0].set_ylabel('원')
axs[0, 0].legend()
axs[0, 0].grid(True, alpha=0.3)

monthly_stats['total_pl'].plot(kind='bar', ax=axs[0, 1])
axs[0, 1].set_title('월별 손익')
axs[0, 1].set_ylabel('원')
axs[0, 1].grid(True, alpha=0.3)

monthly_stats['winrate_%'].plot(kind='bar', ax=axs[1, 0])
axs[1, 0].set_title('월별 승률 (%)')
axs[1, 0].grid(True, alpha=0.3)

monthly_stats['profit_loss_ratio'].plot(kind='bar', ax=axs[1, 1])
axs[1, 1].set_title('월별 손익비')
axs[1, 1].grid(True, alpha=0.3)

monthly_mdd.plot(kind='bar', ax=axs[2, 0])
axs[2, 0].set_title('월별 최대 낙폭 (MDD %)')
axs[2, 0].set_ylabel('%')
axs[2, 0].grid(True, alpha=0.3)

plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()