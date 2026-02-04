import pandas as pd
import numpy as np

def run_backtest(file_path):
    # 1. 데이터 로드 및 전처리
    df = pd.read_excel(file_path)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # 2. EMA 200 (200일 지수이동평균) 계산
    # span=200은 200일 기간을 의미하며, adjust=False는 실제 업비트/바이낸스 계산 방식과 일치시킵니다.
    # df['ema200'] = df['close'].ewm(span=200, adjust=False).mean()

    # 3. 초기 설정
    initial_balance = 1000000  # 초기 자본금 100만원
    cash = initial_balance
    coins = 0
    fee_rate = 0.0005          # 업비트 수수료 0.05%
    
    portfolio_history = []     # 일별 자산 추적용

    # 4. 백테스트 루프 (시뮬레이션)
    for i in range(len(df)):
        date = df.loc[i, 'date']
        close = df.loc[i, 'close']
        ema200 = df.loc[i, 'ema200']
        
        # 2일차 데이터부터 골든/데드크로스 판단 가능
        if i > 0:
            prev_close = df.loc[i-1, 'close']
            prev_ema200 = df.loc[i-1, 'ema200']
            
            # [BUY CONDITION] 종가가 EMA 200을 상향 돌파할 때 (Golden Cross)
            if prev_close <= prev_ema200 and close > ema200 and cash > 0:
                buy_amount = cash * (1 - fee_rate) # 수수료 제외 후 매수
                coins = buy_amount / close
                cash = 0
                # print(f"[{date}] BUY at {close:,} KRW")
                
            # [SELL CONDITION] 종가가 EMA 200을 하향 돌파할 때 (Dead Cross)
            elif prev_close >= prev_ema200 and close < ema200 and coins > 0:
                sell_amount = coins * close * (1 - fee_rate) # 수수료 제외 후 매도
                cash = sell_amount
                coins = 0
                # print(f"[{date}] SELL at {close:,} KRW")

        # 매일 밤 자정(종가 기준) 자산 가치 기록
        current_total_value = cash + (coins * close)
        portfolio_history.append({'date': date, 'total_value': current_total_value})

    # 5. 결과 데이터프레임 생성
    history_df = pd.DataFrame(portfolio_history)
    history_df['month'] = history_df['date'].dt.to_period('M')

    # 6. 월별 통계 계산
    monthly_stats = []
    for month, group in history_df.groupby('month'):
        start_val = group.iloc[0]['total_value']
        end_val = group.iloc[-1]['total_value']
        profit = end_val - start_val
        return_pct = (profit / start_val) * 100 if start_val != 0 else 0
        
        monthly_stats.append({
            'Month': str(month),
            'Start_Value': round(start_val),
            'End_Value': round(end_val),
            'Monthly_Profit': round(profit),
            'Return_Pct': round(return_pct, 2)
        })

    result_df = pd.DataFrame(monthly_stats)
    
    # 7. 최종 성과 출력
    final_value = history_df.iloc[-1]['total_value']
    total_return = ((final_value - initial_balance) / initial_balance) * 100
    
    print(f"--- 백테스트 결과 ---")
    print(f"최종 평가 자산: {final_value:,.0f} KRW")
    print(f"누적 수익률: {total_return:.2f}%")
    
    return result_df

# 실행 (파일명은 실제 경로에 맞춰 수정하세요)
result = run_backtest('코인_일봉_ema200.xlsx')
print(result)