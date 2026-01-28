import pandas as pd

# 1-1. 엑셀파일 읽어들임
file_name = "코인_5분봉_ema_rsi_stochrsi.xlsx"
df = pd.read_excel(file_name)
print(f"{file_name} 엑셀파일 읽어들임 완료!!")

# 1-2. date 컬럼을 datetime으로 변환 후 인덱스로 설정
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()

# 1-3.기간 필터링 (필요 시 주석 해제하거나 값 변경)
# START = df.index[0]  # 예: pd.to_datetime("2023-01-01 00:00:00")
# END   = df.index[-1]  # 예: pd.to_datetime("2023-12-31 23:55:00")

# 2-1. Backtest 설정
INITIAL_CAPITAL = 1000000  # 초기 자본금 100만원 설정
position_size_ratio = 0.5  # 자본금의 50%씩 매수

# 2-2. 손절/익절 설정 (퍼센트 기준으로 단순함 - 직전 저점 대신)
STOP_LOSS_PCT = -0.02           # 손절 -2%
TAKE_PROFIT_PCT_RATIO = 1.8     # 손익비 1:1.8 예시 (1.5~2.0 사이 추천)

# 3. 변수 초기화
capital = INITIAL_CAPITAL   # 현재 자본금
cash = INITIAL_CAPITAL      # 현금 보유액
position = 0.0              # 보유 코인 수량
entry_price = 0.0           # 진입 가격
stop_loss_price = 0.0       # 손절 가격
take_profit_price = 0.0     # 익절 가격

trades = []  # 거래 내역 기록용

equity_curve = []   # 자본 곡선 기록용 (매 캔들 끝 자산 기록)
monthly_stats = {}  # 월초 자본금 기록용

prev_month = None
month_start_equity = INITIAL_CAPITAL


# 4. 메인 백테스트 루프
for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]
    current_time = df.index[i]

    # 4-1. 현재 자산 가치 계산 (포지션 평가 포함)
    current_equity = cash + position * row['close']
    equity_curve.append({'datetime': current_time, 'equity': current_equity})

    # 4-2. 월 변경 체크
    current_month = current_time.strftime('%Y-%m')
    if prev_month is None:
        prev_month = current_month
    if current_month != prev_month:
        # 4-2-1. 이전 달 마감
        monthly_stats[prev_month] = {
            'start': month_start_equity,
            'end': cash + position * prev['close'],
            'return_pct': ((cash + position * prev['close']) / month_start_equity - 1) * 100
        }
        month_start_equity = cash + position * row['close']
        prev_month = current_month

    # 4-2-2. 기존 포지션 청산 여부 체크 (손절 / 익절)
    if position > 0:
        # 4-2-2-1. 당일 고점/저점으로 hit(매매체결) 여부 판단 (5분봉이므로 현실적 근사)
        if row['low'] <= stop_loss_price:
            # 4-2-2-1-1 손절
            exit_price = stop_loss_price
            proceeds = position * exit_price
            cash += proceeds
            pnl = proceeds - (position * entry_price)
            trades.append({
                'time': current_time,
                'type': 'SELL',
                'reason':'STOP_LOSS',
                'price': exit_price,
                'qty': position,
                'pnl': pnl,
                'cash_after': cash
            })
            position = 0.0
        elif row['high'] >= take_profit_price:
            # 4-2-2-1-2 익절
            exit_price = take_profit_price
            proceeds = position * exit_price
            cash += proceeds
            pnl = proceeds - (position * entry_price)
            trades.append({
                'time': current_time,
                'type': 'SELL',
                'reason':'TAKE_PROFIT',
                'price': exit_price,
                'qty': position,
                'pnl': pnl,
                'cash_after': cash
            })
            position = 0.0

    # 4-3. 신규 진입 조건 체크 (EMA 골든트리오 및 StochRSI 과매도)
    if position == 0:
        # 4-3-1. 조건 1: EMA200 위 (상승 추세)
        if row['close'] > row['EMA200']:
            # 조건 2: EMA9 > EMA21 (골든크로스 상태)
            golden_cross = (prev['EMA9'] <= prev['EMA21']) and (row['EMA9'] > row['EMA21'])

            if golden_cross:
                # 4-3-2. 조건 3: StochRSI %K < 20 (과매도 구간)
                oversold_bounce = (prev['StochRSI_K'] <= 20) and (row['StochRSI_K'] > prev['StochRSI_K'])
                stoch_cross = (prev['StochRSI_K'] <= prev['StochRSI_D']) and (row['StochRSI_K'] > row['StochRSI_D'])

                if oversold_bounce or stoch_cross:
                    # 4-3-2-1. 매수 진입
                    buy_amount = cash * position_size_ratio
                    if buy_amount < 100:
                        continue  # 너무 적은 금액은 매수하지 않음

                    qty = buy_amount / row['close']
                    cash -= buy_amount
                    position = qty
                    entry_price = row['close']

                    # 4-3-2-2.손절/익절 가격 설정 (퍼센트 기준)
                    stop_loss_price = entry_price * (1 + STOP_LOSS_PCT)
                    risk = entry_price - stop_loss_price
                    take_profit_price = entry_price + risk * TAKE_PROFIT_PCT_RATIO 

                    trades.append({
                        'time': current_time,
                        'type': 'BUY',
                        'reason':'ENTRY_CONDITION_MET',
                        'price': entry_price,
                        'qty': qty,
                        'cash_after': cash
                    })

# 5. 마지막 달 통계
final_equity = cash + position * df.iloc[-1]['close']
last_month = df.index[-1].strftime('%Y-%m')
monthly_stats[last_month] = {
    'start': month_start_equity,
    'end': final_equity,
    'return_pct': ((final_equity) / month_start_equity - 1) * 100 if month_start_equity > 0 else 0
}

# 6. 결과 출력
total_return = (final_equity / INITIAL_CAPITAL - 1) * 100
total_trades = len(trades)
win_trades = len([t for t in trades if t.get('pnl',0) > 0])
win_rate = win_trades / (total_trades//2) * 100 if total_trades > 0 else 0   # 왕복 기준 근사

print(f"백테스트 기간: {df.index[0]} ~ {df.index[-1]}")
print(f"초기 자본  : ₩{INITIAL_CAPITAL:,.0f}")
print(f"최종 자산  : ₩{final_equity:,.0f}")
print(f"총 수익률  : {total_return:+.2f}%")
print(f"총 거래 횟수: {total_trades//2} 회 (진입 기준)")
print(f"승률(대략) : {win_rate:.1f}%")
print()

print("월별 수익률")
print("-"*50)
for m, stat in sorted(monthly_stats.items()):
    print(f"{m} : {stat['return_pct']:>+7.2f}%  (₩{stat['end']:,.0f})")

# 필요 시 거래 내역 저장
# pd.DataFrame(trades).to_csv("trades_log.csv", index=False)
# pd.DataFrame(equity_curve).to_csv("equity_curve.csv", index=False)


