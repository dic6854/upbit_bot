import pandas as pd
import numpy as np

def calculate_indicators(df_hour, df_day):
    """지표 및 듀얼 노이즈 필터 계산"""
    # --- [1] 1시간봉 지표 계산 ---
    df = df_hour.copy()
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # ATR (14)
    tr = pd.concat([df['high'] - df['low'], 
                    abs(df['high'] - df['close'].shift(1)), 
                    abs(df['low'] - df['close'].shift(1))], axis=1).max(axis=1)
    df['ATR'] = tr.rolling(window=14).mean()
    
    # ADX (14)
    up = df['high'].diff(); down = -df['low'].diff()
    pdm = np.where((up > down) & (up > 0), up, 0)
    mdm = np.where((down > up) & (down > 0), down, 0)
    pdi = 100 * (pd.Series(pdm).rolling(14).sum() / tr.rolling(14).sum())
    mdi = 100 * (pd.Series(mdm).rolling(14).sum() / tr.rolling(14).sum())
    df['ADX'] = 100 * (abs(pdi - mdi) / (pdi + mdi + 1e-9)).rolling(14).mean()
    
    # Stochastic RSI
    rsi = (df['close'].diff().where(df['close'].diff() > 0, 0).rolling(14).mean() / 
           (df['close'].diff().abs().rolling(14).mean() + 1e-9)) * 100
    stoch_rsi = (rsi - rsi.rolling(14).min()) / (rsi.rolling(14).max() - rsi.rolling(14).min() + 1e-9)
    df['Stoch_K'] = stoch_rsi.rolling(3).mean() * 100
    df['Stoch_D'] = df['Stoch_K'].rolling(3).mean()

    # --- [2] 듀얼 노이즈 계산 (세용님 로직 이식) ---
    window = 10
    # 시간봉 노이즈
    df['noise_hour'] = 1 - abs(df['open'] - df['close']) / (df['high'] - df['low'] + 1e-9)
    # 일봉 노이즈
    df_day['noise_day'] = 1 - abs(df_day['open'] - df_day['close']) / (df_day['high'] - df_day['low'] + 1e-9)
    
    # 일봉 노이즈를 시간봉에 매칭 (날짜 기준)
    df['date_only'] = df['date'].dt.date
    df_day['date_only'] = df_day['date'].dt.date
    df = pd.merge(df, df_day[['date_only', 'noise_day']], on='date_only', how='left')
    
    # 듀얼 노이즈 평균
    df['dual_noise'] = (df['noise_hour'].rolling(window).mean() + df['noise_day'].rolling(window).mean()) / 2
    
    return df.dropna().reset_index(drop=True)

def run_backtest(file_hour, file_day):
    # 데이터 로드
    df_hour = pd.read_excel(file_hour)
    df_day = pd.read_excel(file_day)
    df_hour['date'] = pd.to_datetime(df_hour['date'])
    df_day['date'] = pd.to_datetime(df_day['date'])
    
    df = calculate_indicators(df_hour, df_day)

    # 초기 설정
    capital = 1_000_000
    initial_cap = capital
    fee = 0.0005; risk_ratio = 0.02
    
    pos_qty, entry_p, sl_p, tp1_p, tp2_p = 0, 0, 0, 0, 0
    be_moved, partial_done = False, False
    equity_curve = []

    for i in range(1, len(df)):
        row, prev = df.iloc[i], df.iloc[i-1]
        curr_eq = capital + (pos_qty * row['close'] * (1 - fee))
        equity_curve.append({'date': row['date'], 'equity': curr_eq})

        if pos_qty == 0:
            # 진입 조건 (5단계 + 듀얼 노이즈 필터)
            c1 = row['close'] > row['EMA200']
            c2 = row['EMA21'] > row['EMA200']
            c3 = row['EMA9'] > row['EMA21'] and prev['EMA9'] <= prev['EMA21']
            
            recent_k = df['Stoch_K'].iloc[max(0, i-10):i]
            c4 = (row['Stoch_K'] > 30 and recent_k.min() < 25) or (row['Stoch_K'] > row['Stoch_D'] and row['Stoch_K'] > 35)
            c5 = row['ADX'] > 22.5 and row['ADX'] > prev['ADX']
            
            # [핵심] 듀얼 노이즈 필터 (0.65 미만일 때만 진입)
            c6 = row['dual_noise'] < 0.65
            
            if c1 and c2 and c3 and c4 and c5 and c6:
                entry_p = row['close']
                sl_p = entry_p - (1.8 * row['ATR'])
                dist = entry_p - sl_p
                if dist > 0:
                    buy_q = (curr_eq * risk_ratio) / dist
                    pos_qty = min(buy_q, (capital * (1 - fee)) / entry_p)
                    capital -= pos_qty * entry_p * (1 + fee)
                    tp1_p, tp2_p = entry_p + dist, entry_p + (2 * dist)
                    be_moved, partial_done = False, False

        elif pos_qty > 0:
            # 포지션 관리 (본절 이동, 2R 익절, 트레일링 스탑)
            if not be_moved and row['high'] >= tp1_p:
                sl_p, be_moved = entry_p, True
            if row['low'] <= sl_p:
                capital += pos_qty * sl_p * (1 - fee); pos_qty = 0
            elif not partial_done and row['high'] >= tp2_p:
                ex_q = pos_qty / 2; capital += ex_q * tp2_p * (1 - fee)
                pos_qty -= ex_q; partial_done = True
            elif partial_done and row['close'] < row['EMA21']:
                capital += pos_qty * row['close'] * (1 - fee); pos_qty = 0

    return pd.DataFrame(equity_curve), capital + (pos_qty * df.iloc[-1]['close'] * (1 - fee))

# 실행
report_df, final_val = run_backtest("코인_60분봉_org.xlsx", "코인_일봉_org.xlsx")
# 월별 리포트 생성 및 출력 로직 (생략 - 이전과 동일)
print(report_df.to_string(index=False))
print(f"\n최종 평가자산: {int(final_val):,}원")