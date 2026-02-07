import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import matplotlib.font_manager as fm
import matplotlib as mpl

def __get_tick_size(price):
    """가격대에 따른 업비트 호가 단위(Tick Size) 반환"""
    if price >= 2000000: return 1000
    elif price >= 1000000: return 500
    elif price >= 500000: return 100
    elif price >= 100000: return 50
    elif price >= 10000: return 10
    elif price >= 1000: return 1
    elif price >= 100: return 1     # 100원대 코인 (1원 단위)
    elif price >= 10: return 0.1    # 10원대 코인 (0.1원 단위)
    else: return 0.01               # 10원 미만 코인 (0.01원 단위)

# 상수 설정
TOTAL_ASSETS = 10000000.0       # 1000만원
INVESTMENT_RATIO = 0.20         # 전체 자산의 20%만 투자
NUM_COINS = 4                   # 투자할 코인 개수 4개 : BTC, XRP, ETH, ADA
INVEST_PER_COIN = TOTAL_ASSETS * INVESTMENT_RATIO / NUM_COINS  # 각 코인당 500,000원
FEE_RATE = 0.0005               # 수수료 = 0.05%

# 엑셀 파일에서 데이터 로드
file_path = 'day.xlsx'
coins = ['BTC', 'XRP', 'ETH', 'ADA']

data = {}
for coin in coins:
    df = pd.read_excel(file_path, sheet_name=coin)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    df['MA30'] = df['close'].rolling(window=30).mean()
    df = df.dropna()
    df = df.loc['2021-01-01':'2025-12-31']
    data[coin] = df

# 모든 코인이 공통으로 존재하는 날짜만 사용
common_dates = set(data['BTC'].index)
for coin in coins[1:]:
    common_dates.intersection_update(data[coin].index)
common_dates = sorted(list(common_dates))

# 포트폴리오 초기화 - float 타입으로
portfolio = pd.DataFrame(
    index=common_dates,
    columns=['total_value', 'cash', 'holdings_value'],      # 총자산, 현금, 코인투자대기금
    data=0.0
)

# initial_cash = TOTAL_ASSETS * (1 - INVESTMENT_RATIO)        # 현금현황 초기화
initial_cash = TOTAL_ASSETS        # 현금현황 초기화
portfolio['cash'] = initial_cash                            # 현금
portfolio['total_value'] = initial_cash                     # 총자금

# 포지션 및 투자금 추적
positions = {coin: 0.0 for coin in coins}                   # {'BTC': 0.0, 'XRP': 0.0, 'ETH': 0.0, 'ADA': 0.0}
invested_amount = {coin: 0.0 for coin in coins}             # {'BTC': 0.0, 'XRP': 0.0, 'ETH': 0.0, 'ADA': 0.0}

trade_logs = []

# 백테스팅 시뮬레이션
for i, date in enumerate(common_dates):

    if i > 0:   # 첫요소는 넘어가고, 두번째 요소부터 체크
        prev_date = common_dates[i-1]   # 이전 요소의 날짜 데이터 저장
        portfolio.loc[date, 'cash'] = portfolio.loc[prev_date, 'cash']      # 이전요소의 현금상황을 현요소의 현금상황에 넣음

    current_holdings_value = 0.0    # 투자자금을 0으로 초기화

    for coin in coins:         # 코인을 BTC -> XRP -> ETH -> ADA 순으로 순환함
        row = data[coin].loc[date]  # 해당 날짜의 행(Row) 데이터값을 row 변수(dict형)에 저장
        close = row['close']        # row에서 'close'(종가) key의 key값을 close라는 변수에 저장
        ma30 = row['MA30']            # row에서 'MA5'(5일이평선값) key의 key값을 ma5라는 변수에 저장

        if (positions[coin] > 0) and (close < ma30):    # 매도 조건 충족
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
        elif close > ma30:    # 매수 조건 충족
            remaining_alloc = INVEST_PER_COIN - invested_amount[coin]
            buy_amount = min(remaining_alloc, portfolio.loc[date, 'cash'])

            if buy_amount > 0:
                fee = buy_amount * FEE_RATE
                actual_buy = buy_amount - fee
                quantity = actual_buy / close
                safe_qty = float("{:.8f}".format(quantity))     # 수량: 소수점 8째 자리까지만 남기고 버림

                portfolio.loc[date, 'cash'] -= buy_amount
                positions[coin] += safe_qty
                invested_amount[coin] += buy_amount

                trade_logs.append({
                    'date': date,
                    'coin': coin,
                    'action': 'buy',
                    'price': close,
                    'quantity': safe_qty,
                    'profit_loss': 0.0
                })

        current_holdings_value += positions[coin] * close

    portfolio.loc[date, 'holdings_value'] = current_holdings_value
    portfolio.loc[date, 'total_value'] = portfolio.loc[date, 'cash'] + current_holdings_value

# ── 결과 분석 ────
trade_df = pd.DataFrame(trade_logs)

# portfolio.to_excel('portfolio.xlsx')
# print("일짜별 수익현황 파일 저장 완료 : portfolio.xlsx")    
# trade_df.to_excel('trade.xlsx')
# print("거래내역 파일 저장 완료 : trade.xlsx")

trade_df['month'] = trade_df['date'].dt.to_period('M')      # month 컬럼에 yyyy-mm 형식으로 저장
trade_df['year'] = trade_df['date'].dt.to_period('Y')       # year 컬럼에 yyyy 형식으로 저장

sells = trade_df[trade_df['action'] == 'sell'].copy()       # 매도 거래만 필터링

monthly_stats = sells.groupby('month')['profit_loss'].agg(
    total_pl='sum',         # 월별 총수익 (월별 총매도금액 - 월별 총매수금액 - 월별 총수수료)
    avg_pl='mean',          # 월별 평균수익 = 총수익 / 거래횟수
    count='count'           # 월별 거래횟수
)

# 승률
monthly_wins = sells[sells['profit_loss'] > 0].groupby('month').size()  # 월별로 수익이 난 거래(익절) 횟수
monthly_total = sells.groupby('month').size()   # 월별 총 거래횟수
monthly_winrate = (monthly_wins / monthly_total).fillna(0) * 100 # 월별 승률 = (월별 익절횟수 / 월별 총 거래횟수) * 100

# 손익비
monthly_wins_value = sells[sells['profit_loss'] > 0].groupby('month')['profit_loss'].sum()  # 월별로 수익이 난 거래(익절) 횟수
monthly_losses_value = sells[sells['profit_loss'] < 0].groupby('month')['profit_loss'].sum()  # 월별로 손실이 난 거래(손절) 횟수
monthly_pfls_ratio = (monthly_wins_value / monthly_losses_value.abs()).fillna(0) * 100 # 월별 손익비 100보다 작으면 손실이 수익보다 큰 것임 

# avg_profit = sells[sells['profit_loss'] > 0].groupby('month')['profit_loss'].mean()
# avg_loss = sells[sells['profit_loss'] < 0].groupby('month')['profit_loss'].mean().abs()
# monthly_pl_ratio = (avg_profit / avg_loss).fillna(0)

# 월별 통계 (monthly_stats)에 승률, 손익비 추가
monthly_stats = monthly_stats.join(monthly_winrate.rename('winrate_%'))
monthly_stats = monthly_stats.join(monthly_pfls_ratio.rename('monthly_pfls_ratio_%'))

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
# 한글 폰트 및 마이너스 기호 설정
plt.rc('font', family='Malgun Gothic')
plt.rcParams['axes.unicode_minus'] = False

# 전체 Figure 설정
fig = plt.figure(figsize=(14, 14)) # 세로 길이를 조금 더 늘렸습니다.
fig.suptitle("백테스트 결과", fontsize=16)

# --- 1행: 전체 병합 (colspan=2) ---
# (3행 2열) 격자에서 (0,0) 위치부터 2칸을 차지함
ax1 = plt.subplot2grid((3, 2), (0, 0), colspan=2)
ax1.plot(portfolio.index, portfolio['total_value'], label='총 자산 가치', color='tab:blue')
ax1.set_title('포트폴리오 가치 추이')
ax1.set_xlabel('날짜')
ax1.set_ylabel('원')
ax1.legend()
ax1.grid(True, alpha=0.3)

# --- 2행: 좌/우 분리 ---
# (1,0) 위치: 월별 손익
ax2 = plt.subplot2grid((3, 2), (1, 0))
monthly_stats['total_pl'].plot(kind='bar', ax=ax2, color='tab:orange')
ax2.set_title('월별 손익')
ax2.set_ylabel('원')
ax2.grid(True, alpha=0.3)

# (1,1) 위치: 월별 승률
ax3 = plt.subplot2grid((3, 2), (1, 1))
monthly_stats['winrate_%'].plot(kind='bar', ax=ax3, color='tab:green')
ax3.set_title('월별 승률 (%)')
ax3.grid(True, alpha=0.3)

# --- 3행: 좌/우 분리 ---
# (2,0) 위치: 월별 손익비
ax4 = plt.subplot2grid((3, 2), (2, 0))
monthly_stats['monthly_pfls_ratio_%'].plot(kind='bar', ax=ax4, color='tab:red')
ax4.set_title('월별 손익비')
ax4.grid(True, alpha=0.3)

# (2,1) 위치: 월별 최대 낙폭
ax5 = plt.subplot2grid((3, 2), (2, 1))
monthly_mdd.plot(kind='bar', ax=ax5, color='gray')
ax5.set_title('월별 최대 낙폭 (MDD %)')
ax5.set_ylabel('%')
ax5.grid(True, alpha=0.3)

# 레이아웃 조정 및 상단 여백 확보
plt.tight_layout(rect=[0, 0, 1, 0.96])
plt.show()