import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

# ──────────────── 한글 폰트 설정 (가장 중요한 부분) ────────────────
# 환경에 따라 아래 3개 중 하나만 선택해서 사용하세요
# 1. 윈도우 → Malgun Gothic (대부분 기본 설치됨)
# 2. 맥 → AppleGothic
# 3. Colab / 리눅스 → NanumGothic (아래 설치 코드 필요 시 사용)

plt.rc('font', family='Malgun Gothic')          # ← 윈도우 추천
# plt.rc('font', family='NanumGothic')          # Colab/리눅스 추천
# plt.rc('font', family='AppleGothic')          # 맥 추천

plt.rcParams['axes.unicode_minus'] = False      # 마이너스 기호 깨짐 방지
# ────────────────────────────────────────────────────────────────

def run_backtest(file_path):
    # ===================== 설정값 =====================
    initial_capital = 10000000
    target_vol = 2.0
    fee = 0.001
    coins = ['BTC', 'XRP', 'ETH', 'ADA']
    n_coins = len(coins)
    
    # ===================== 데이터 로드 및 전처리 =====================
    all_data = {}
    for coin in coins:
        df = pd.read_excel(file_path, sheet_name=coin)
        df['date'] = pd.to_datetime(df['date'])
        df.set_index('date', inplace=True)
        df.sort_index(inplace=True)
        
        df['ma5']  = df['close'].rolling(5).mean()
        df['ma10'] = df['close'].rolling(10).mean()
        df['ma20'] = df['close'].rolling(20).mean()
        
        df['day_vol'] = ((df['high'].shift(1) - df['low'].shift(1)) / df['open'].shift(1)) * 100
        df['avg_vol_5d'] = df['day_vol'].rolling(5).mean()
        
        all_data[coin] = df

    # 공통 날짜 범위
    common_dates = all_data[coins[0]].index
    for coin in coins:
        common_dates = common_dates.intersection(all_data[coin].index)
    
    # ===================== 초기화 =====================
    cash = initial_capital
    positions = {coin: 0.0 for coin in coins}
    portfolio = pd.DataFrame(
        index=common_dates,
        columns=['total_value', 'cash', 'holdings_value'],
        data=0.0
    )
    trade_logs = []
    
    # ===================== 백테스트 메인 루프 =====================
    for date in common_dates:
        prices = {coin: all_data[coin].loc[date, 'close'] for coin in coins}
        
        holdings_value = sum(positions[coin] * prices[coin] for coin in coins)
        total_value_pre = cash + holdings_value
        
        portfolio.loc[date, 'total_value']    = total_value_pre
        portfolio.loc[date, 'cash']           = cash
        portfolio.loc[date, 'holdings_value'] = holdings_value
        
        target_amounts = {}
        
        for coin in coins:
            df = all_data[coin]
            curr_price = df.loc[date, 'close']
            ma5  = df.loc[date, 'ma5']
            ma10 = df.loc[date, 'ma10']
            ma20 = df.loc[date, 'ma20']
            vol_5d = df.loc[date, 'avg_vol_5d']
            
            if (pd.notna(ma5) and pd.notna(ma10) and pd.notna(ma20) and
                curr_price > ma5 and curr_price > ma10 and curr_price > ma20):
                
                if pd.notna(vol_5d) and vol_5d > 0:
                    weight = (target_vol / vol_5d) / n_coins
                    target_amounts[coin] = total_value_pre * weight
                else:
                    target_amounts[coin] = 0
            else:
                target_amounts[coin] = 0
        
        # 목표 금액 총합이 현재 자산 초과 시 정규화
        total_target = sum(target_amounts.values())
        if total_target > total_value_pre and total_target > 0:
            scale = total_value_pre / total_target
            for coin in target_amounts:
                target_amounts[coin] *= scale
        
        # 리밸런싱 & 거래 로그
        for coin in coins:
            current_val = positions[coin] * prices[coin]
            target_val  = target_amounts.get(coin, 0.0)
            diff        = target_val - current_val
            
            if abs(diff) > 1:  # 최소 거래 단위 이하 무시
                close = prices[coin]
                quantity = diff / close
                trade_fee = abs(diff) * fee
                
                pl = diff if diff < 0 else 0.0  # 매도 시 근사 손익
                
                trade_logs.append({
                    'date': date,
                    'coin': coin,
                    'action': 'buy' if diff > 0 else 'sell',
                    'price': close,
                    'quantity': abs(quantity),
                    'amount': abs(diff),
                    'fee': trade_fee,
                    'profit_loss': pl
                })
                
                cash -= (diff + trade_fee)
                positions[coin] = target_val / close if close > 0 else 0

    # ===================== 결과 정리 =====================
    result_df = portfolio.copy()
    result_df['daily_ret'] = result_df['total_value'].pct_change()
    result_df['cum_ret'] = result_df['total_value'] / initial_capital - 1
    
    result_df['peak'] = result_df['total_value'].cummax()
    result_df['drawdown'] = result_df['total_value'] / result_df['peak'] - 1
    mdd = result_df['drawdown'].min()
    
    final_value = result_df['total_value'].iloc[-1]
    final_return_pct = (final_value / initial_capital - 1) * 100
    
    print("\n===== 백테스트 최종 결과 =====")
    print(f"초기 자산       : {initial_capital:,.0f} 원")
    print(f"최종 자산       : {final_value:,.0f} 원")
    print(f"총 수익률       : {final_return_pct:,.2f}%")
    print(f"최대 낙폭 (MDD) : {mdd*100:,.2f}%")
    print(f"총 거래 횟수     : {len(trade_logs)} 회")
    
    # 거래 로그 요약
    if trade_logs:
        trades_df = pd.DataFrame(trade_logs)
        trades_df['date'] = pd.to_datetime(trades_df['date'])
        trades_df.set_index('date', inplace=True)
        
        print("\n코인별 거래 금액 합계:")
        print(trades_df.groupby('coin')['amount'].sum().round(0).astype(int))
        print("\n매도 시 근사 손익 합계:", round(trades_df[trades_df['action']=='sell']['profit_loss'].sum(), 0))
    
    # ===================== 월별 통계 및 그래프 =====================
    result_df['month'] = result_df.index.to_period('M')
    
    # 월말 기준 총자산
    monthly_end = result_df.groupby('month')['total_value'].last()
    monthly_end.index = monthly_end.index.to_timestamp()
    
    # 월별 누적 수익률 (%)
    monthly_growth = (monthly_end / initial_capital - 1) * 100
    
    # 그래프 1: 월말 총자산 추이 (선 그래프)
    plt.figure(figsize=(12, 6))
    plt.plot(monthly_end.index, monthly_end / 1_000_000,
             marker='o', linewidth=2, color='#1f77b4', label='월말 총자산')
    plt.axhline(y=initial_capital / 1_000_000, color='gray', linestyle='--',
                label=f'초기 자본 ({initial_capital/1_000_000:.1f}백만 원)')
    
    plt.title('월별 말일 기준 총자산 추이', fontsize=14, pad=12)
    plt.xlabel('날짜')
    plt.ylabel('총자산 (백만 원)')
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.tight_layout()
    plt.show()
    
    # 그래프 2: 월별 누적 수익률 (막대 그래프)
    plt.figure(figsize=(12, 6))
    colors = ['#2ca02c' if x >= 0 else '#d62728' for x in monthly_growth]
    bars = plt.bar(monthly_end.index, monthly_growth, color=colors, width=20)
    
    for bar, value in zip(bars, monthly_growth):
        height = bar.get_height()
        plt.text(bar.get_x() + bar.get_width()/2, height,
                 f'{value:.1f}%',
                 ha='center', va='bottom' if height >= 0 else 'top',
                 fontsize=9)
    
    plt.axhline(y=0, color='gray', linewidth=1)
    plt.title('월별 누적 수익률 (월말 기준)', fontsize=14, pad=12)
    plt.xlabel('날짜')
    plt.ylabel('누적 수익률 (%)')
    plt.grid(True, axis='y', alpha=0.3)
    plt.tight_layout()
    plt.show()
    
    return result_df, pd.DataFrame(trade_logs) if trade_logs else None, portfolio


# 사용 예시
result, trades, port = run_backtest('day.xlsx')