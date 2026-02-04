import pandas as pd
import numpy as np

def calculate_indicators(df):
    """실전 로직에 필요한 모든 지표 계산"""
    # 1. 이동평균선 (EMA)
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. ATR (14) - 손절 및 변동성 계산용
    tr = pd.concat([df['high'] - df['low'], 
                    abs(df['high'] - df['close'].shift(1)), 
                    abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    # 3. Stochastic RSI (14, 3, 3)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    stoch_rsi = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min())
    df['Stoch_K'] = stoch_rsi.rolling(3).mean() * 100
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
    
    # 4. ADX (14) - 추세 강도
    up_move = df['high'] - df['high'].shift(1)
    down_move = df['low'].shift(1) - df['low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    tr_s = tr.rolling(window=14).sum()
    pdm_s = pd.Series(plus_dm).rolling(window=14).sum()
    mdm_s = pd.Series(minus_dm).rolling(window=14).sum()
    df['ADX'] = 100 * (abs(pdm_s - mdm_s) / (pdm_s + mdm_s)).rolling(window=14).mean()
    
    return df.dropna()

def run_backtest(file_path):
    # 데이터 로드
    df = pd.read_excel(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)
    df = calculate_indicators(df)

    # 설정값
    initial_capital = 1_000_000
    capital = initial_capital
    fee = 0.0005  # 업비트 수수료 0.05%
    risk_ratio = 0.02 # 계좌당 리스크 2%
    
    position_qty = 0
    entry_price = 0
    sl_price = 0
    tp_price_2r = 0
    partial_exit_done = False
    
    equity_curve = []

    # 백테스트 루프
    for i in range(15, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 현재 평가자산 기록
        current_equity = capital + (position_qty * row['close'] * (1 - fee))
        equity_curve.append({'date': row['date'], 'equity': current_equity})

        # --- 매수 진입 (No Position) ---
        if position_qty == 0:
            # 1. 대추세: 종가 > EMA 200
            # 2. 골든크로스: EMA 9 > EMA 21
            # 3. 에너지: Stoch_K 30이상 반등(최저점 25미만) 혹은 K>D & K>35
            # 4. 강도: ADX > 22.5
            c1 = row['close'] > row['EMA200']
            c2 = row['EMA9'] > row['EMA21'] and prev['EMA9'] <= prev['EMA21']
            
            recent_k = df['Stoch_K'].iloc[i-10:i]
            local_min_k = recent_k.min()
            c3 = (row['Stoch_K'] > 30 and local_min_k < 25) or (row['Stoch_K'] > row['Stoch_D'] and row['Stoch_K'] > 35)
            
            c4 = row['ADX'] > 22.5
            
            if c1 and c2 and c3 and c4:
                entry_price = row['close']
                sl_price = entry_price - (1.8 * row['ATR'])
                risk_dist = entry_price - sl_price
                
                if risk_dist > 0:
                    risk_amt = current_equity * risk_ratio
                    buy_qty = risk_amt / risk_dist
                    max_qty = (capital * (1 - fee)) / entry_price
                    position_qty = min(buy_qty, max_qty)
                    
                    capital -= position_qty * entry_price * (1 + fee)
                    tp_price_2r = entry_price + (2 * risk_dist) # 2R 익절 지점
                    partial_exit_done = False

        # --- 매도 및 관리 (In Position) ---
        elif position_qty > 0:
            # 1. 손절 처리
            if row['low'] <= sl_price:
                capital += position_qty * sl_price * (1 - fee)
                position_qty = 0
                continue
            
            # 2. 2R 도달 시 50% 분할 익절
            if not partial_exit_done and row['high'] >= tp_price_2r:
                exit_qty = position_qty / 2
                capital += exit_qty * tp_price_2r * (1 - fee)
                position_qty -= exit_qty
                partial_exit_done = True
                # 남은 물량의 손절가를 본절로 이동 (선택 사항이나 권장)
                # sl_price = entry_price 
                
            # 3. 나머지 물량 트레일링 스탑 (EMA 21 하향 이탈 시)
            if partial_exit_done and row['close'] < row['EMA21']:
                capital += position_qty * row['close'] * (1 - fee)
                position_qty = 0

    # 월별 수익 리포트 생성
    eq_df = pd.DataFrame(equity_curve)
    eq_df['month'] = eq_df['date'].dt.to_period('M')
    
    monthly_report = []
    for month, group in eq_df.groupby('month'):
        start_val = group['equity'].iloc[0]
        end_val = group['equity'].iloc[-1]
        diff = end_val - start_val
        pct = (diff / start_val) * 100
        
        monthly_report.append({
            '월(Month)': str(month),
            '   월초평가자산': f"{int(start_val):,}원",
            '   월말평가자산': f"{int(end_val):,}원",
            '   증가금액': f"{int(diff):+,}원",
            '   수익률(%)': f"{pct:+.2f}%"
        })
    
    final_equity = capital + (position_qty * df.iloc[-1]['close'] * (1 - fee))
    total_pct = (final_equity - initial_capital) / initial_capital * 100
    
    return pd.DataFrame(monthly_report), final_equity, total_pct

# 파일이 있는 경로를 지정하여 실행하세요
report, final_val, total_ret = run_backtest("코인_60분봉_org.xlsx")
print(report.to_string(index=False))
print(f'Final Equity = {final_val:,.4f},  Total Return = {total_ret:,.4f}')