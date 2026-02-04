import pandas as pd
import numpy as np

def run_aggressive_backtest(file_path):
    # 1. 데이터 로드 및 지표 계산
    df = pd.read_excel(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 지표 계산
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    tr = pd.concat([df['high'] - df['low'], abs(df['high'] - df['close'].shift(1)), abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    # Stochastic RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))
    stoch_rsi = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min())
    df['Stoch_K'] = stoch_rsi.rolling(3).mean() * 100
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()
    
    # ADX
    up_move = df['high'] - df['high'].shift(1)
    down_move = df['low'].shift(1) - df['low']
    plus_dm = np.where((up_move > down_move) & (up_move > 0), up_move, 0)
    minus_dm = np.where((down_move > up_move) & (down_move > 0), down_move, 0)
    pdm_s = pd.Series(plus_dm).rolling(window=14).sum()
    mdm_s = pd.Series(minus_dm).rolling(window=14).sum()
    df['ADX'] = 100 * (abs(pdm_s - mdm_s) / (pdm_s + mdm_s)).rolling(window=14).mean()

    # 2. 백테스트 설정 (완전 복리 방식)
    initial_capital = 1_000_000
    capital = initial_capital
    fee = 0.0005
    risk_ratio = 0.02 # 리스크 2% 유지
    
    position_qty = 0
    highest_price = 0 # 트레일링 스탑용
    sl_price = 0
    
    equity_curve = []
    
    for i in range(20, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 현재 평가 자산
        current_equity = capital + (position_qty * row['close'] * (1 - fee))
        equity_curve.append({'date': row['date'], 'equity': current_equity})

        # 매수 진입
        if position_qty == 0:
            c1 = row['close'] > row['EMA200']
            c2 = row['EMA21'] > row['EMA200']
            c3 = prev['EMA9'] <= prev['EMA21'] and row['EMA9'] > row['EMA21']
            
            recent_k = df['Stoch_K'].iloc[i-10:i]
            c4 = (row['Stoch_K'] > 30 and recent_k.min() < 25) or (row['Stoch_K'] > row['Stoch_D'] and row['Stoch_K'] > 35)
            c5 = row['ADX'] > 20 # 진입 문턱을 살짝 낮춤
            
            if c1 and c2 and c3 and c4 and c5:
                entry_price = row['close']
                sl_price = entry_price - (2.0 * row['ATR']) # 손절폭 확대(노이즈 방지)
                
                risk_amt = current_equity * risk_ratio
                buy_qty = risk_amt / (entry_price - sl_price)
                max_qty = (capital * (1 - fee)) / entry_price
                position_qty = min(buy_qty, max_qty)
                
                capital -= position_qty * entry_price * (1 + fee)
                highest_price = entry_price

        # 매도 관리 (Chandelier Trailing Stop)
        elif position_qty > 0:
            highest_price = max(highest_price, row['high'])
            # 추격 손절선: 최고가 - 3.0 * ATR (시세를 끝까지 끌고 감)
            dynamic_exit = highest_price - (3.0 * row['ATR'])
            
            # 최종 손절선은 초기 손절선과 추격 손절선 중 높은 것
            final_sl = max(sl_price, dynamic_exit)
            
            if row['low'] <= final_sl:
                capital += position_qty * final_sl * (1 - fee)
                position_qty = 0

    # 3. 월별 결과 집계
    eq_df = pd.DataFrame(equity_curve)
    eq_df['month'] = eq_df['date'].dt.to_period('M')
    
    monthly_stats = []
    for month, group in eq_df.groupby('month'):
        m_start = group['equity'].iloc[0]
        m_end = group['equity'].iloc[-1]
        m_diff = m_end - m_start
        monthly_stats.append({
            'Month': str(month),
            '월초평가자산': f"{int(m_start):,}원",
            '월말평가자산': f"{int(m_end):,}원",
            '증가금액': f"{int(m_diff):+,}원",
            '수익률': f"{(m_diff/m_start)*100:+.2f}%"
        })
    
    return pd.DataFrame(monthly_stats), initial_capital, current_equity

# 시뮬레이션 실행 (결과 예시)
report, start, final = run_aggressive_backtest("코인_60분봉_org.xlsx")
print(report.to_string(index=False))
print(f'Start = {start:,.4f},  Final = {final:,.4f}')