import pandas as pd
import numpy as np

def calculate_indicators(df):
    """VWAP을 포함한 모든 보조지표 계산"""
    # 1. EMA (9, 21, 200)
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # 2. ATR (14) - 손절선용
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
    df['ADX'] = 100 * (abs(pdm_s - mdm_s) / (pdm_s + mdm_s + 1e-9)).rolling(window=14).mean()
    
    # 5. VWAP (당일 거래량 가중 평균가격 - 매일 00:00시 리셋)
    df['tp'] = (df['high'] + df['low'] + df['close']) / 3
    df['tp_vol'] = df['tp'] * df['volume']
    
    # 날짜별 그룹화하여 누적합 계산
    df['date_only'] = df['date'].dt.date
    df['cum_tp_vol'] = df.groupby('date_only')['tp_vol'].cumsum()
    df['cum_vol'] = df.groupby('date_only')['volume'].cumsum()
    df['VWAP'] = df['cum_tp_vol'] / df['cum_vol']
    
    return df.dropna()

def run_final_backtest_with_vwap(file_path):
    df = pd.read_excel(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = calculate_indicators(df)

    initial_capital = 1_000_000
    capital = initial_capital
    fee = 0.0005
    risk_ratio = 0.02 # 계좌당 리스크 2%
    
    position_qty = 0
    entry_price, sl_price, tp_price_1r, tp_price_2r = 0, 0, 0, 0
    be_moved, partial_exit_done = False, False
    
    equity_curve = []

    for i in range(1, len(df)):
        row, prev = df.iloc[i], df.iloc[i-1]
        current_equity = capital + (position_qty * row['close'] * (1 - fee))
        equity_curve.append({'date': row['date'], 'equity': current_equity})

        # --- 매수 진입 로직 ---
        if position_qty == 0:
            c1 = row['close'] > row['EMA200']
            c2 = row['EMA21'] > row['EMA200']
            c3 = row['EMA9'] > row['EMA21'] and prev['EMA9'] <= prev['EMA21']
            
            recent_k = df['Stoch_K'].iloc[max(0, i-10):i]
            c4 = (row['Stoch_K'] > 30 and recent_k.min() < 25) or (row['Stoch_K'] > row['Stoch_D'] and row['Stoch_K'] > 35)
            
            c5 = row['ADX'] > 22.5 and row['ADX'] > prev['ADX']
            
            # [추가] VWAP 필터: 현재가가 당일 평균단가(VWAP) 위에 있을 때만 진입
            c6 = row['close'] > row['VWAP']
            
            if c1 and c2 and c3 and c4 and c5 and c6:
                entry_price = row['close']
                sl_price = entry_price - (1.8 * row['ATR'])
                risk_dist = entry_price - sl_price
                
                if risk_dist > 0:
                    risk_amt = current_equity * risk_ratio
                    buy_qty = risk_amt / risk_dist
                    position_qty = min(buy_qty, (capital * (1 - fee)) / entry_price)
                    capital -= position_qty * entry_price * (1 + fee)
                    
                    tp_price_1r = entry_price + risk_dist
                    tp_price_2r = entry_price + (2 * risk_dist)
                    be_moved, partial_exit_done = False, False

        # --- 매도 관리 로직 ---
        elif position_qty > 0:
            if not be_moved and row['high'] >= tp_price_1r:
                sl_price, be_moved = entry_price, True

            if row['low'] <= sl_price:
                capital += position_qty * sl_price * (1 - fee)
                position_qty = 0
                continue
            
            if not partial_exit_done and row['high'] >= tp_price_2r:
                exit_qty = position_qty / 2
                capital += exit_qty * tp_price_2r * (1 - fee)
                position_qty -= exit_qty
                partial_exit_done = True
                
            if partial_exit_done and row['close'] < row['EMA21']:
                capital += position_qty * row['close'] * (1 - fee)
                position_qty = 0

    # 리포트 출력
    eq_df = pd.DataFrame(equity_curve)
    eq_df['month'] = eq_df['date'].dt.to_period('M')
    report = []
    for month, group in eq_df.groupby('month'):
        s, e = group['equity'].iloc[0], group['equity'].iloc[-1]
        report.append({'월': str(month), '월초': f"{int(s):,}원", '월말': f"{int(e):,}원", '증가': f"{int(e-s):+,}원", '%': f"{(e-s)/s*100:+.2f}%"})
    
    return pd.DataFrame(report), (capital + position_qty * df.iloc[-1]['close'])

# 실행
report, final_val = run_final_backtest_with_vwap("코인_60분봉_org.xlsx")
print(report.to_string(index=False))
print(f"\n최종 평가자산: {int(final_val):,}원")