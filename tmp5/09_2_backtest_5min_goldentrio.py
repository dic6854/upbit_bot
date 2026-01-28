import pandas as pd
import numpy as np

# 1. 데이터 로드 및 지표 계산 (원본 데이터 활용)
def calculate_indicators(df):
    # EMA 200 (대추세 필터)
    df['EMA200'] = df['close'].ewm(span=200, adjust=False).mean()
    
    # ATR (변동성 기반 손절선 계산용)
    df['tr'] = np.maximum(df['high'] - df['low'], 
                          np.maximum(abs(df['high'] - df['close'].shift(1)), 
                                     abs(df['low'] - df['close'].shift(1))))
    df['ATR'] = df['tr'].rolling(window=14).mean()
    
    # Stochastic RSI (눌림목 확인용)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    df['stoch_rsi'] = (df['RSI'] - df['RSI'].rolling(14).min()) / (df['RSI'].rolling(14).max() - df['RSI'].rolling(14).min())
    df['StochRSI_K'] = df['stoch_rsi'].rolling(3).mean() * 100
    
    return df.dropna().reset_index(drop=True)

# 2. 백테스트 실행 함수
def run_proper_backtest(file_name):
    df_raw = pd.read_excel(file_name)
    df_raw['date'] = pd.to_datetime(df_raw['date'])
    df = calculate_indicators(df_raw)

    initial_capital = 100_000_000 # 1억 원
    capital = initial_capital
    fee = 0.0005 # 업비트 수수료 0.05%
    risk_ratio = 0.02 # 자산의 2% 리스크 적용

    position = 0
    entry_price = 0
    trailing_stop = 0
    
    history = []
    equity_curve = []

    # 시뮬레이션 루프
    
    for i in range(1, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        # 현재 시점의 총 평가자산 계산 (현금 + 보유코인 가치)
        current_val = capital + (position * row['close'] * (1 - fee))
        equity_curve.append({'date': row['date'], 'equity': current_val})

        # --- 매수 진입 (Long) ---
        if position == 0:
            # 조건: EMA200 위(상승장) + StochRSI 과매도(눌림목) + 전봉 고가 돌파(모멘텀)
            if row['close'] > row['EMA200'] and prev['StochRSI_K'] < 20 and row['close'] > prev['high']:
                entry_price = row['close']
                # 초기 손절가: 진입가 - (ATR * 2.5)
                initial_sl = entry_price - (row['ATR'] * 2.5)
                
                # 수량 계산: 2% 리스크 룰 적용
                risk_amt = current_val * risk_ratio
                price_gap = entry_price - initial_sl
                
                if price_gap > 0:
                    buy_qty = risk_amt / price_gap
                    # 실제 현금 한도 내에서 매수
                    max_qty = (capital * (1 - fee)) / entry_price
                    position = min(buy_qty, max_qty)
                    
                    capital -= (position * entry_price * (1 + fee))
                    trailing_stop = initial_sl
                    history.append({'date': row['date'], 'type': 'BUY', 'price': entry_price})

        # --- 매도 및 추격 손절 (Trailing Stop) ---
        elif position > 0:
            # 가격 상승에 따라 손절선 상향 조정 (ATR 3배 추격)
            new_stop = row['close'] - (row['ATR'] * 3.0)
            trailing_stop = max(trailing_stop, new_stop)
            
            # 가격이 추격 손절선에 닿으면 전량 매도
            if row['low'] <= trailing_stop:
                capital += (position * trailing_stop * (1 - fee))
                history.append({'date': row['date'], 'type': 'EXIT', 'price': trailing_stop})
                position = 0

    # 3. 월별 수익표 작성
    eq_df = pd.DataFrame(equity_curve)
    eq_df['month'] = eq_df['date'].dt.to_period('M')
    
    monthly_report = []
    for month, group in eq_df.groupby('month'):
        start_val = group['equity'].iloc[0]
        end_val = group['equity'].iloc[-1]
        m_yield = ((end_val - start_val) / start_val) * 100
        
        monthly_report.append({
            'Month': str(month),
            '월초평가자산': f"{int(start_val):,}원",
            '월말평가자산': f"{int(end_val):,}원",
            '수익률': f"{m_yield:+.2f}%"
        })
    
    return pd.DataFrame(monthly_report), initial_capital, current_val

# 4. 결과 출력
report_table, start_cap, end_cap = run_proper_backtest("코인_5분봉_지표org.xlsx")

print("\n" + "="*60)
print("      [ 비트코인 추세 추종전략 월별 수익 분석표 ]")
print("="*60)
print(report_table.to_string(index=False))
print("-" * 60)
print(f"최종 누적 수익률: {((end_cap - start_cap) / start_cap) * 100:.2f}%")
print(f"최종 자산 가치: {int(end_cap):,}원")
print("="*60)