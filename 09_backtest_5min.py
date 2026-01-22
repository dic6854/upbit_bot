import pandas as pd
from datetime import datetime

file_path = "코인_5분봉.xlsx"
df1 = pd.read_excel(file_path)
df = df1[['date', 'close', 'SMA300']].copy()

df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
df = df.dropna(subset=['SMA300'])

# start_time = datetime.strftime(df.loc[0, 'date'], "%Y-%m-%d %H:%M:%S")
start_time = "2024-01-02 09:55:00"
end_time = "2025-01-01 09:00:00"
df = df[df['date'] < end_time].reset_index(drop=True)

df['prev_close'] = df['close'].shift(1)
df['prev_SMA300'] = df['SMA300'].shift(1)

df['golden_cross'] = (df['close'] > df['SMA300']) & (df['prev_close'] <= df['prev_SMA300'])
df['dead_cross'] = (df['close'] < df['SMA300']) & (df['prev_close'] >= df['prev_SMA300'])

initial_cash = 1000000  # 초기 자본금 100만원
cash = initial_cash
position = 0  # 보유 코인 수
entry_price = 0  # 매수 가격
trades = [] # 거래 내역 기록 (매수.매도 로그)
portfolio_values = []  # 각 캔들 끝 포트폴리오 가치 기록 ((cash) + (position * close(포지션 가치)))

for idx, row in df.iterrows():
    current_price = row['close']

    if position > 0:
        # 현재 수익률 계산
        profit_pct = (current_price - entry_price) / entry_price

        # 익절/손절 체크
        if profit_pct >= 0.03:  # 3% 익절
            sell_price = current_price  # 종가로 매도 가정 (또는 low로 조정 가능)
            cash += position * sell_price
            trades.append({'time': row['date'], 'action': 'SELL_PROFIT', 'price': sell_price, 'quantity': position, 'profit_pct': profit_pct})
            position = 0
        elif profit_pct <= -0.05:  # -5% 손절
            sell_price = current_price  # 종가로 매도 가정 (또는 high로 조정 가능)
            cash += position * sell_price
            trades.append({'time': row['date'], 'action': 'SELL_LOSS', 'price': sell_price, 'quantity': position, 'profit_pct': profit_pct})
            position = 0
        elif row['dead_cross']: # 데드크로스 매도
            sell_price = current_price  # 종가로 매도 가정 (또는 low로 조정 가능)
            cash += position * sell_price
            trades.append({'time': row['date'], 'action': 'SELL_DEAD_CROSS', 'price': sell_price, 'quantity': position, 'profit_pct': profit_pct})
            position = 0

    if position == 0 and row['golden_cross']:   # 골든크로스 매수
        buy_amount = cash * 0.5  # 자본금의 50%로 매수
        if buy_amount > 0:
            buy_price = current_price  # 종가로 매수 가정 (또는 high로 조정 가능)
            position = buy_amount / buy_price
            cash -= buy_amount
            entry_price = buy_price
            trades.append({'time': row['date'], 'action': 'BUY', 'price': buy_price, 'quantity': position})

    # 각 캔들 끝 portfolio 가치 기록
    portfolio_value = cash + (position * current_price if position > 0 else 0)
    portfolio_values.append({'time': row['date'], 'portfolio': portfolio_value})

# portfolio_values를 DataFrame으로 변환
portfolio_df = pd.DataFrame(portfolio_values).set_index('time')
# 인덱스를 날짜형으로 변환
portfolio_df.index = pd.to_datetime(portfolio_df.index)

# 7. 월별 수익률 계산
portfolio_df['month'] = portfolio_df.index.to_period('M')
monthly = portfolio_df.groupby('month').agg(start_port=('portfolio', 'first'), end_port=('portfolio', 'last'))
monthly['monthly_return'] = (monthly['end_port'] - monthly['start_port']) / monthly['start_port'] * 100

# 총 누적 수익률
total_return = (portfolio_df['portfolio'].iloc[-1] - initial_cash) / initial_cash * 100

# 8. 결과 출력
print("거래 기록:")
for trade in trades:
    print(trade)

print("\n월별 수익률 (%):")
print(monthly['monthly_return'])

print(f"\n총 누적 수익률: {total_return:.2f}%")
print(f"최종 자산: {portfolio_df['portfolio'].iloc[-1]:.0f}원")