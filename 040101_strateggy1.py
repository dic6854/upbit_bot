import pandas as pd
import matplotlib.pyplot as plt

def run_simulation(initial_total=10000000):
    # 파일 읽기
    file_path = 'Coin_60min.xlsx'
    sheets = {
        'BTC': 'BTC',
        'XRP': 'XRP',
        'ETH': 'ETH',
        'ADA': 'ADA'
    }
    
    df_dict = {}
    for coin, sheet_name in sheets.items():
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
        df_dict[coin] = df
    
    # 설정값
    cash_ratio = 0.9
    crypto_ratio = 0.1
    each_crypto_ratio = 0.025
    fee_rate = 0.0005  # 업비트 수수료 0.05%
    sell_threshold = 1.5  # 50% 상승
    sell_weight_limit = 0.15  # 비중 15% 초과
    buy_threshold = 0.67  # 33% 하락
    
    # 상태 변수 초기화
    current_cash = initial_total * cash_ratio
    last_rebalance_crypto_value = initial_total * crypto_ratio
    
    # 코인 목록
    coins = list(df_dict.keys())
    
    # 초기 수량 계산 (첫 번째 행 기준)
    first_prices = {coin: df_dict[coin].iloc[0]['close'] for coin in coins}
    amounts = {coin: (initial_total * each_crypto_ratio) / first_prices[coin] for coin in coins}
    
    history = []
    
    # 모든 코인 데이터프레임의 인덱스가 동일하다고 가정
    common_index = df_dict['BTC'].index
    for coin in coins:
        if not df_dict[coin].index.equals(common_index):
            raise ValueError(f"{coin}의 인덱스가 BTC와 일치하지 않습니다.")
    
    for current_time in common_index:
        prices = {coin: df_dict[coin].loc[current_time, 'close'] for coin in coins}
        
        # 현재 가상자산 가치 계산
        current_crypto_value = sum(amounts[coin] * prices[coin] for coin in coins)
        total_assets = current_cash + current_crypto_value
        crypto_weight = current_crypto_value / total_assets if total_assets > 0 else 0
        
        # 리밸런싱 판정
        need_rebalance = False
        
        # 조건 1: 50% 상승 및 비중 15% 초과
        if (current_crypto_value >= last_rebalance_crypto_value * sell_threshold) and (crypto_weight > sell_weight_limit):
            need_rebalance = True
        # 조건 2: 33% 하락
        elif current_crypto_value <= last_rebalance_crypto_value * buy_threshold:
            need_rebalance = True
        
        if need_rebalance:
            # 리밸런싱 실행: 목표는 현재 총자산의 10%를 4등분하여 재배분
            target_total_crypto = total_assets * crypto_ratio
            target_per_coin = target_total_crypto / len(coins)
            
            for coin in coins:
                current_value = amounts[coin] * prices[coin]
                trade_value = target_per_coin - current_value  # 양수: 매수, 음수: 매도
                
                # 수수료 적용
                fee = abs(trade_value) * fee_rate
                
                if trade_value > 0:  # 매수
                    current_cash -= trade_value + fee
                elif trade_value < 0:  # 매도
                    current_cash -= trade_value - fee  # trade_value가 음수이므로 -= 음수 = +
                
                # 수량 업데이트 (수수료 반영 없이 목표 가치로 설정 - 실제로는 약간 조정 필요하지만 근사)
                amounts[coin] = target_per_coin / prices[coin]
            
            # 리밸런싱 후 기준가 업데이트
            last_rebalance_crypto_value = target_total_crypto
        
        # 기록 저장
        history.append({
            'time': current_time,
            'total_assets': total_assets,
            'cash': current_cash,
            'crypto_value': current_crypto_value,
            'rebalanced': need_rebalance
        })
    
    results = pd.DataFrame(history)
    
    # 결과 출력
    print("시뮬레이션 결과 요약:")
    print(results.tail())  # 마지막 몇 행 출력
    print(f"초기 자본: {initial_total:.0f}원")
    print(f"최종 자산: {results['total_assets'].iloc[-1]:.0f}원")
    print(f"총 리밸런싱 횟수: {results['rebalanced'].sum()}")
    
    # 그래프 출력 (자산 추이)
    plt.figure(figsize=(12, 6))
    plt.plot(results['time'], results['total_assets'], label='Total Assets')
    plt.plot(results['time'], results['crypto_value'], label='Crypto Value')
    plt.title('Asset Value Over Time')
    plt.xlabel('Time')
    plt.ylabel('Value (KRW)')
    plt.legend()
    plt.grid(True)
    plt.show()
    
    return results

# 시뮬레이션 실행
results = run_simulation()