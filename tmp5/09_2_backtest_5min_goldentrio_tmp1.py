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

# 2-1. Backtest 설정import pandas as pd
import numpy as np
from datetime import datetime

# 1. 데이터 로드
file_path = "코인_5분봉_ema_rsi_stochrsi.xlsx"
df = pd.read_excel(file_path)

# date 컬럼을 datetime으로 변환 후 인덱스로 설정
df['date'] = pd.to_datetime(df['date'])
df = df.set_index('date').sort_index()

# 기간 필터링
# START = "2023-01-01 09:00:00"
# END   = "2024-01-01 08:55:00"
# df = df.loc[START:END].copy()

# 추가 지표 (볼륨 평균, 있으면)
if 'volume' in df.columns:
    df['vol_avg'] = df['volume'].rolling(20).mean()

# -------------------------------------------------------------------------
# 백테스트 설정
# -------------------------------------------------------------------------
INITIAL_CAPITAL = 1_000_000
position_size_ratio = 0.30  # 개선: 30%로 줄여 리스크 ↓
STOP_LOSS_SWING_WINDOW = 20  # Swing Low 창 크기
TAKE_PROFIT_RATIO = 2.0  # 개선: 1:2 고정
MONTHLY_LOSS_LIMIT = -5.0  # 월 손실 5% 초과 시 거래 중지

# -------------------------------------------------------------------------
# 변수 초기화
# -------------------------------------------------------------------------
cash = INITIAL_CAPITAL
position = 0.0
entry_price = 0.0
stop_loss_price = 0.0
take_profit_price = 0.0
trailing_stop = 0.0  # 트레일링 스탑 초기

trades = []
monthly_stats = {}
prev_month = None
month_start_equity = INITIAL_CAPITAL
month_current_equity = INITIAL_CAPITAL
trade_pause = False  # 월 손실 제한 플래그

# -------------------------------------------------------------------------
# 메인 백테스트 루프
# -------------------------------------------------------------------------
for i in range(1, len(df)):
    row = df.iloc[i]
    prev = df.iloc[i-1]
    current_time = df.index[i]
    
    # 현재 자산 가치
    current_equity = cash + position * row['close']
    
    # 월 변경 체크
    current_month = current_time.strftime('%Y-%m')
    if prev_month is None:
        prev_month = current_month
    if current_month != prev_month:
        # 이전 달 마감
        monthly_stats[prev_month] = {
            'start_equity': month_start_equity,
            'end_equity': cash + position * prev['close'],
            'return_pct': ((cash + position * prev['close']) / month_start_equity - 1) * 100
        }
        month_start_equity = current_equity
        prev_month = current_month
        trade_pause = False  # 새 달 시작 시 리셋
    else:
        # 월 중 손실 체크
        month_return = ((current_equity / month_start_equity) - 1) * 100
        if month_return < MONTHLY_LOSS_LIMIT:
            trade_pause = True

    # 1. 기존 포지션 관리 (손절/익절/트레일링)
    if position > 0:
        # 트레일링 스탑 업데이트 (개선)
        if row['close'] > entry_price * 1.005:  # 0.5% 이상 이익 시
            trailing_stop = max(trailing_stop, entry_price)  # 브레이크이븐으로 이동
        
        stop_loss_price = max(stop_loss_price, trailing_stop)  # 트레일 적용
        
        if row['low'] <= stop_loss_price:
            # 손절
            exit_price = stop_loss_price
            proceeds = position * exit_price
            cash += proceeds
            pnl = proceeds - (position * entry_price)
            trades.append({'time': current_time, 'type': 'SELL', 'reason': 'STOP_LOSS', 'price': exit_price, 'pnl': pnl})
            position = 0
            trailing_stop = 0
        elif row['high'] >= take_profit_price:
            # 익절
            exit_price = take_profit_price
            proceeds = position * exit_price
            cash += proceeds
            pnl = proceeds - (position * entry_price)
            trades.append({'time': current_time, 'type': 'SELL', 'reason': 'TAKE_PROFIT', 'price': exit_price, 'pnl': pnl})
            position = 0
            trailing_stop = 0

    # 2. 진입 조건 체크 (포지션 없고, 거래 pause 아니면)
    if position == 0 and not trade_pause:
        # 조건 ①: EMA200 위
        if row['close'] > row['EMA200']:
            # 조건 ②: 골든크로스
            golden_cross = (prev['EMA9'] <= prev['EMA21']) and (row['EMA9'] > row['EMA21'])
            if golden_cross:
                # 조건 ③: Stoch RSI (개선: 더 엄격)
                oversold_bounce = (prev['StochRSI_K'] <= 15) and (row['StochRSI_K'] > prev['StochRSI_K'])
                stoch_cross = (prev['StochRSI_K'] <= prev['StochRSI_D']) and (row['StochRSI_K'] > row['StochRSI_D'])
                if oversold_bounce or stoch_cross:
                    # 개선: RSI > 45 추가
                    if row['RSI'] > 45:
                        # 볼륨 필터 (있으면)
                        vol_condition = True
                        if 'volume' in df.columns:
                            vol_condition = row['volume'] > row['vol_avg']
                        if vol_condition:
                            # 매수
                            buy_amount = cash * position_size_ratio
                            if buy_amount < 100:
                                continue
                            qty = buy_amount / row['close']
                            cash -= buy_amount
                            position = qty
                            entry_price = row['close']
                            
                            # 손절: Swing Low (개선)
                            swing_low = df.iloc[max(0, i - STOP_LOSS_SWING_WINDOW):i]['low'].min()
                            stop_loss_price = swing_low
                            
                            # 익절
                            risk = entry_price - stop_loss_price
                            take_profit_price = entry_price + risk * TAKE_PROFIT_RATIO
                            trailing_stop = stop_loss_price  # 초기 트레일 = SL
                            
                            trades.append({'time': current_time, 'type': 'BUY', 'price': entry_price})

# 마지막 달 통계
final_equity = cash + position * df.iloc[-1]['close']
last_month = df.index[-1].strftime('%Y-%m')
monthly_stats[last_month] = {
    'start_equity': month_start_equity,
    'end_equity': final_equity,
    'return_pct': ((final_equity / month_start_equity) - 1) * 100
}

# -------------------------------------------------------------------------
# 결과 출력 (매달 초/말 평가자산 포함)
# -------------------------------------------------------------------------
print("월별 평가자산 및 수익률")
print("-" * 60)
for m, stat in sorted(monthly_stats.items()):
    print(f"{m} | 초 평가자산: ₩{stat['start_equity']:,.0f} | 말 평가자산: ₩{stat['end_equity']:,.0f} | 수익률: {stat['return_pct']:>+7.2f}%")

total_return = ((final_equity / INITIAL_CAPITAL) - 1) * 100
print(f"\n총 수익률: {total_return:+.2f}%")
print(f"최종 자산: ₩{final_equity:,.0f}")
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


