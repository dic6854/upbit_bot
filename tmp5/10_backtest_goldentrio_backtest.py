import pandas as pd
import numpy as np
import os

def calculate_indicators(df):
    """최종 확정 로직에 필요한 모든 보조지표 계산"""
    # 1. 이동평균선 (EMA 9, 21, 200)
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. ATR (14) - 변동성 기반 손절선
    tr = pd.concat([df['high'] - df['low'], 
                    abs(df['high'] - df['close'].shift(1)), 
                    abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    # 3. Stochastic RSI (14, 3, 3)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    stoch_rsi = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min() + 1e-9)
    df['Stoch_K'] = stoch_rsi.rolling(3).mean() * 100
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
    
    # 4. ADX (14) - 추세 강도 및 기울기
    up_move = df['high'] - df['high'].shift(1)
    down_move = df['low'].shift(1) - df['low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    tr_s = tr.rolling(window=14).sum()
    pdm_s = pd.Series(plus_dm).rolling(window=14).sum()
    mdm_s = pd.Series(minus_dm).rolling(window=14).sum()
    plus_di = 100 * (pdm_s / (tr_s + 1e-9))
    minus_di = 100 * (mdm_s / (tr_s + 1e-9))
    dx = 100 * (abs(plus_di - minus_di) / (plus_di + minus_di + 1e-9))
    df['ADX'] = dx.rolling(window=14).mean()
    
    return df.dropna()

def run_final_backtest(file_path):
    # 데이터 로드 (60분봉 원본 데이터)
    df = pd.read_excel(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df = calculate_indicators(df)

    # 설정값 (초기자금 100만원, 수수료 0.05%, 리스크 2%)
    initial_capital = 1_000_000
    capital = initial_capital
    fee = 0.0005
    risk_ratio = 0.02
    
    position_qty = 0
    entry_price, sl_price, tp_price_1r, tp_price_2r = 0, 0, 0, 0
    be_moved, partial_exit_done = False, False
    
    equity_curve = []

    for i in range(1, len(df)):
        row, prev = df.iloc[i], df.iloc[i-1]
        
        # 현재 평가자산 계산 (복리 적용용)
        current_equity = capital + (position_qty * row['close'] * (1 - fee))
        equity_curve.append({'date': row['date'], 'equity': current_equity})

        # --- 매수 진입 로직 ---
        if position_qty == 0:
            c1 = row['close'] > row['EMA200'] # 대추세
            c2 = row['EMA21'] > row['EMA200'] # 중기추세
            c3 = row['EMA9'] > row['EMA21'] and prev['EMA9'] <= prev['EMA21'] # 골든크로스
            
            recent_k = df['Stoch_K'].iloc[max(0, i-10):i]
            c4 = (row['Stoch_K'] > 30 and recent_k.min() < 25) or (row['Stoch_K'] > row['Stoch_D'] and row['Stoch_K'] > 35)
            
            c5 = row['ADX'] > 22.5 and row['ADX'] > prev['ADX'] # ADX 강도 + 기울기(상승)
            
            if c1 and c2 and c3 and c4 and c5:
                entry_price = row['close']
                sl_price = entry_price - (1.8 * row['ATR'])
                risk_dist = entry_price - sl_price
                
                if risk_dist > 0:
                    risk_amt = current_equity * risk_ratio
                    buy_qty = risk_amt / risk_dist
                    max_qty = (capital * (1 - fee)) / entry_price
                    position_qty = min(buy_qty, max_qty)
                    
                    capital -= position_qty * entry_price * (1 + fee)
                    tp_price_1r = entry_price + risk_dist # 본절 이동 기준
                    tp_price_2r = entry_price + (2 * risk_dist) # 50% 익절 기준
                    be_moved, partial_exit_done = False, False

        # --- 매도 및 관리 로직 ---
        elif position_qty > 0:
            # 1. 본절가 보호: 수익이 1R에 도달하면 손절가를 진입가로 이동
            if not be_moved and row['high'] >= tp_price_1r:
                sl_price = entry_price
                be_moved = True

            # 2. 손절/본절 매도
            if row['low'] <= sl_price:
                capital += position_qty * sl_price * (1 - fee)
                position_qty = 0
                continue
            
            # 3. 2R 도달 시 50% 분할 익절
            if not partial_exit_done and row['high'] >= tp_price_2r:
                exit_qty = position_qty / 2
                capital += exit_qty * tp_price_2r * (1 - fee)
                position_qty -= exit_qty
                partial_exit_done = True
                
            # 4. 나머지 50% 물량 Trailing Stop: EMA 21 하향 이탈 시 전량 매도
            if partial_exit_done and row['close'] < row['EMA21']:
                capital += position_qty * row['close'] * (1 - fee)
                position_qty = 0

    # 월별 리포트 생성
    eq_df = pd.DataFrame(equity_curve)
    eq_df['month'] = eq_df['date'].dt.to_period('M')
    monthly_report = []
    for month, group in eq_df.groupby('month'):
        start, end = group['equity'].iloc[0], group['equity'].iloc[-1]
        monthly_report.append({
            'Month': str(month),
            '월초평가자산': f"{int(start):,}원",
            '월말평가자산': f"{int(end):,}원",
            '증가금액': f"{int(end-start):+,}원",
            '수익률(%)': f"{(end-start)/start*100:+.2f}%"
        })
    
    final_equity = capital + (position_qty * df.iloc[-1]['close'] * (1 - fee))
    return pd.DataFrame(monthly_report), final_equity

# 실행 (파일명 '코인_60분봉_org.xlsx' 가 같은 경로에 있어야 함)
report, final_val = run_final_backtest("코인_60분봉_org.xlsx")
print(report.to_string(index=False))
print(f"\n[최종 결과] 평가자산: {int(final_val):,}원 | 누적 수익률: {((final_val-1000000)/1000000)*100:.2f}%")