import pyupbit
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from datetime import datetime, timedelta
import time

# 백테스팅 설정값
COIN_TICKER = "KRW-BTC"  # 백테스팅할 코인 티커
DAYS = 180               # 백테스팅 기간 (일)
LARRY_K = 0.5            # 변동성 돌파 전략의 K값
DUAL_NOISE_LIMIT = 0.6   # 듀얼 노이즈 한계값
TRAILING_STOP_MIN_PROFIT = 0.4  # 트레일링 스탑 최소 수익률
TRAILING_STOP_GAP = 0.05  # 트레일링 스탑 갭
FEE = 0.0005             # 거래 수수료 (0.05%)

class BackTester:
    def __init__(self, ticker, days, k, noise_limit, trailing_min_profit, trailing_gap, fee):
        """
        백테스터 초기화
        
        Args:
            ticker (str): 코인 티커
            days (int): 백테스팅 기간 (일)
            k (float): 변동성 돌파 전략의 K값
            noise_limit (float): 듀얼 노이즈 한계값
            trailing_min_profit (float): 트레일링 스탑 최소 수익률
            trailing_gap (float): 트레일링 스탑 갭
            fee (float): 거래 수수료
        """
        self.ticker = ticker
        self.days = days
        self.k = k
        self.noise_limit = noise_limit
        self.trailing_min_profit = trailing_min_profit
        self.trailing_gap = trailing_gap
        self.fee = fee
        
        self.df = None
        self.result_df = None
        
    def fetch_data(self):
        """
        백테스팅에 필요한 데이터 가져오기
        """
        print(f"{self.ticker} 데이터 {self.days}일치 가져오는 중...")
        
        # 일봉 데이터 가져오기
        date = None
        dfs = []
        
        # 200일씩 나눠서 가져오기 (API 제한 때문)
        for i in range(self.days // 200 + 1):
            if i < self.days // 200:
                df = pyupbit.get_ohlcv(self.ticker, to=date, interval="day", count=200)
                if df is not None and len(df) > 0:
                    date = df.index[0]
                    dfs.append(df)
            elif self.days % 200 != 0:
                df = pyupbit.get_ohlcv(self.ticker, to=date, interval="day", count=self.days % 200)
                if df is not None and len(df) > 0:
                    dfs.append(df)
            
            time.sleep(0.1)  # API 호출 제한 방지
        
        if not dfs:
            raise ValueError(f"{self.ticker} 데이터를 가져오지 못했습니다.")
            
        self.df = pd.concat(dfs).sort_index()
        print(f"총 {len(self.df)}일치 데이터 로드 완료")
        
        return self.df
    
    def calculate_noise(self, window=5):
        """
        노이즈 계산
        
        Args:
            window (int): 노이즈 평균 계산을 위한 윈도우 크기
            
        Returns:
            Series: 노이즈 시리즈
        """
        # 노이즈 = 1 - |시가-종가|/(고가-저가)
        noise = 1 - abs(self.df['open'] - self.df['close']) / (self.df['high'] - self.df['low'])
        avg_noise = noise.rolling(window=window).mean()
        
        return avg_noise
    
    def prepare_data(self):
        """
        백테스팅을 위한 데이터 준비
        """
        if self.df is None:
            self.fetch_data()
        
        # 결과 데이터프레임 복사
        self.result_df = self.df.copy()
        
        # 노이즈 계산
        self.result_df['noise'] = self.calculate_noise()
        
        # 전일 고가-저가 범위 계산
        self.result_df['range'] = self.result_df['high'].shift(1) - self.result_df['low'].shift(1)
        
        # 목표가 계산 (당일 시가 + 전일 범위 * K)
        self.result_df['target'] = self.result_df['open'] + self.result_df['range'] * self.k
        
        # 5일 이동평균 계산
        self.result_df['ma5'] = self.result_df['close'].rolling(window=5).mean().shift(1)
        
        # 매수 여부 초기화
        self.result_df['buy'] = False
        
        # 수익률 초기화
        self.result_df['ror'] = 1.0
        
        # 트레일링 스탑 관련 변수 초기화
        self.result_df['max_price'] = 0.0
        self.result_df['trailing_stop'] = False
        
        # 누적 수익률 초기화
        self.result_df['acc_ror'] = 1.0
        
        return self.result_df
    
    def run_backtest(self):
        """
        백테스팅 실행
        """
        if self.result_df is None:
            self.prepare_data()
        
        # 초기 자본금
        initial_balance = 10000000  # 1천만원
        balance = initial_balance
        
        # 보유 코인 수량
        coin_amount = 0
        
        # 매수 가격
        buy_price = 0
        
        # 최고가 (트레일링 스탑용)
        max_price = 0
        
        # 거래 기록
        trades = []
        
        # 날짜별 자산 가치
        daily_balance = []
        
        # 백테스팅 시작
        for i in range(1, len(self.result_df)):
            date = self.result_df.index[i]
            row = self.result_df.iloc[i]
            prev_row = self.result_df.iloc[i-1]
            
            # 당일 시가, 고가, 저가, 종가
            open_price = row['open']
            high_price = row['high']
            low_price = row['low']
            close_price = row['close']
            
            # 목표가
            target_price = row['target']
            
            # 5일 이동평균
            ma5 = row['ma5']
            
            # 노이즈
            noise = prev_row['noise']
            
            # 당일 자산 가치 (시가 기준)
            if coin_amount > 0:
                day_start_balance = balance + coin_amount * open_price
            else:
                day_start_balance = balance
            
            daily_balance.append((date, day_start_balance))
            
            # 매수 조건 확인
            # 1) 현재 보유 중이 아니고
            # 2) 노이즈가 한계값 이하이고
            # 3) 고가가 목표가 이상이고
            # 4) 고가가 5일 이동평균 이상일 때
            if (coin_amount == 0 and 
                noise <= self.noise_limit and 
                high_price >= target_price and 
                high_price >= ma5):
                
                # 목표가에 매수
                buy_price = target_price
                coin_amount = (balance * (1 - self.fee)) / buy_price
                balance = 0
                max_price = buy_price  # 최고가 초기화
                
                # 거래 기록 추가
                trades.append({
                    'date': date,
                    'type': 'buy',
                    'price': buy_price,
                    'amount': coin_amount,
                    'balance': balance,
                    'coin_value': coin_amount * buy_price
                })
                
                # 매수 표시
                self.result_df.at[date, 'buy'] = True
            
            # 보유 중인 경우
            if coin_amount > 0:
                # 최고가 업데이트
                if high_price > max_price:
                    max_price = high_price
                
                # 트레일링 스탑 조건 확인
                # 1) 현재 수익률이 최소 수익률 이상이고
                # 2) 저가가 최고가 대비 갭 이상 하락했을 때
                profit_rate = (high_price / buy_price) - 1
                
                if (profit_rate >= self.trailing_min_profit and 
                    low_price <= max_price * (1 - self.trailing_gap)):
                    
                    # 트레일링 스탑 가격에 매도
                    sell_price = max_price * (1 - self.trailing_gap)
                    balance = coin_amount * sell_price * (1 - self.fee)
                    coin_amount = 0
                    
                    # 거래 기록 추가
                    trades.append({
                        'date': date,
                        'type': 'sell_trailing',
                        'price': sell_price,
                        'amount': 0,
                        'balance': balance,
                        'coin_value': 0
                    })
                    
                    # 트레일링 스탑 표시
                    self.result_df.at[date, 'trailing_stop'] = True
                    
                    # 수익률 계산
                    ror = (sell_price * (1 - self.fee)) / (buy_price * (1 + self.fee))
                    self.result_df.at[date, 'ror'] = ror
                
                # 당일 종가에 매도 (트레일링 스탑으로 매도되지 않은 경우)
                elif coin_amount > 0:
                    # 종가에 매도
                    sell_price = close_price
                    balance = coin_amount * sell_price * (1 - self.fee)
                    coin_amount = 0
                    
                    # 거래 기록 추가
                    trades.append({
                        'date': date,
                        'type': 'sell_close',
                        'price': sell_price,
                        'amount': 0,
                        'balance': balance,
                        'coin_value': 0
                    })
                    
                    # 수익률 계산
                    ror = (sell_price * (1 - self.fee)) / (buy_price * (1 + self.fee))
                    self.result_df.at[date, 'ror'] = ror
            
            # 최고가 기록
            self.result_df.at[date, 'max_price'] = max_price
        
        # 누적 수익률 계산
        acc_ror = 1.0
        for i in range(len(self.result_df)):
            ror = self.result_df.iloc[i]['ror']
            acc_ror *= ror
            self.result_df.at[self.result_df.index[i], 'acc_ror'] = acc_ror
        
        # 최종 수익률
        final_balance = daily_balance[-1][1] if daily_balance else initial_balance
        total_ror = (final_balance / initial_balance) - 1
        
        # 연간 수익률 (CAGR)
        days = (self.result_df.index[-1] - self.result_df.index[0]).days
        annual_ror = (1 + total_ror) ** (365 / days) - 1
        
        # MDD (Maximum Drawdown) 계산
        max_value = 0
        mdd = 0
        
        for date, value in daily_balance:
            if value > max_value:
                max_value = value
            
            drawdown = (max_value - value) / max_value
            if drawdown > mdd:
                mdd = drawdown
        
        # 승률 계산
        win_count = len([ror for ror in self.result_df['ror'] if ror > 1])
        total_trades = len([ror for ror in self.result_df['ror'] if ror != 1])
        win_rate = win_count / total_trades if total_trades > 0 else 0
        
        # 결과 요약
        summary = {
            'ticker': self.ticker,
            'period': f"{self.result_df.index[0].date()} ~ {self.result_df.index[-1].date()} ({days}일)",
            'k': self.k,
            'noise_limit': self.noise_limit,
            'trailing_min_profit': self.trailing_min_profit,
            'trailing_gap': self.trailing_gap,
            'initial_balance': initial_balance,
            'final_balance': final_balance,
            'total_return': total_ror,
            'annual_return': annual_ror,
            'mdd': mdd,
            'win_rate': win_rate,
            'total_trades': total_trades
        }
        
        return summary, self.result_df, trades, daily_balance
    
    def plot_results(self, daily_balance):
        """
        백테스팅 결과 시각화
        
        Args:
            daily_balance (list): 날짜별 자산 가치 리스트
        """
        # 결과 데이터프레임이 없으면 백테스팅 실행
        if self.result_df is None:
            self.run_backtest()
        
        # 그래프 크기 설정
        plt.figure(figsize=(15, 12))
        
        # 1. 가격 차트 및 매수 시점
        plt.subplot(3, 1, 1)
        plt.plot(self.result_df.index, self.result_df['close'], label='Close Price')
        plt.plot(self.result_df.index, self.result_df['ma5'], label='MA5', alpha=0.7)
        
        # 매수 시점 표시
        buy_points = self.result_df[self.result_df['buy'] == True].index
        plt.scatter(buy_points, self.result_df.loc[buy_points, 'close'], 
                   color='red', marker='^', s=100, label='Buy')
        
        # 트레일링 스탑 시점 표시
        trailing_points = self.result_df[self.result_df['trailing_stop'] == True].index
        plt.scatter(trailing_points, self.result_df.loc[trailing_points, 'close'], 
                   color='blue', marker='v', s=100, label='Trailing Stop')
        
        plt.title(f'{self.ticker} 가격 차트 및 매매 시점')
        plt.ylabel('Price (KRW)')
        plt.legend()
        plt.grid(True)
        
        # 2. 누적 수익률
        plt.subplot(3, 1, 2)
        plt.plot(self.result_df.index, self.result_df['acc_ror'], label='Accumulated Return')
        plt.title('누적 수익률')
        plt.ylabel('Return')
        plt.legend()
        plt.grid(True)
        
        # 3. 자산 가치 변화
        plt.subplot(3, 1, 3)
        dates = [item[0] for item in daily_balance]
        values = [item[1] for item in daily_balance]
        plt.plot(dates, values, label='Portfolio Value')
        plt.title('자산 가치 변화')
        plt.ylabel('Value (KRW)')
        plt.legend()
        plt.grid(True)
        
        plt.tight_layout()
        plt.savefig('/home/ubuntu/backtest_result.png')
        plt.close()
        
        print(f"백테스팅 결과 그래프가 '/home/ubuntu/backtest_result.png'에 저장되었습니다.")

def run_parameter_optimization(ticker, days):
    """
    최적의 파라미터 조합 찾기
    
    Args:
        ticker (str): 코인 티커
        days (int): 백테스팅 기간 (일)
        
    Returns:
        dict: 최적의 파라미터 조합 및 결과
    """
    print(f"{ticker} 파라미터 최적화 시작...")
    
    # 테스트할 파라미터 범위
    k_values = [0.3, 0.4, 0.5, 0.6, 0.7]
    noise_limits = [0.4, 0.5, 0.6, 0.7]
    trailing_min_profits = [0.3, 0.4, 0.5]
    trailing_gaps = [0.03, 0.05, 0.07]
    
    best_result = None
    best_params = None
    best_annual_return = -1
    
    results = []
    
    # 모든 파라미터 조합 테스트
    total_combinations = len(k_values) * len(noise_limits) * len(trailing_min_profits) * len(trailing_gaps)
    current = 0
    
    for k in k_values:
        for noise_limit in noise_limits:
            for trailing_min_profit in trailing_min_profits:
                for trailing_gap in trailing_gaps:
                    current += 1
                    print(f"파라미터 조합 테스트 중: {current}/{total_combinations} "
                          f"(K={k}, Noise={noise_limit}, Min_Profit={trailing_min_profit}, Gap={trailing_gap})")
                    
                    # 백테스터 생성 및 실행
                    backtester = BackTester(
                        ticker=ticker,
                        days=days,
                        k=k,
                        noise_limit=noise_limit,
                        trailing_min_profit=trailing_min_profit,
                        trailing_gap=trailing_gap,
                        fee=FEE
                    )
                    
                    try:
                        summary, _, _, _ = backtester.run_backtest()
                        
                        # 결과 저장
                        results.append({
                            'k': k,
                            'noise_limit': noise_limit,
                            'trailing_min_profit': trailing_min_profit,
                            'trailing_gap': trailing_gap,
                            'annual_return': summary['annual_return'],
                            'total_return': summary['total_return'],
                            'mdd': summary['mdd'],
                            'win_rate': summary['win_rate'],
                            'total_trades': summary['total_trades']
                        })
                        
                        # 최고 수익률 갱신 확인
                        if summary['annual_return'] > best_annual_return:
                            best_annual_return = summary['annual_return']
                            best_result = summary
                            best_params = {
                                'k': k,
                                'noise_limit': noise_limit,
                                'trailing_min_profit': trailing_min_profit,
                                'trailing_gap': trailing_gap
                            }
                            
                            print(f"새로운 최적 파라미터 발견: 연간 수익률 {best_annual_return:.2%}")
                    
                    except Exception as e:
                        print(f"백테스팅 오류: {e}")
    
    # 결과를 데이터프레임으로 변환
    results_df = pd.DataFrame(results)
    
    # 연간 수익률 기준으로 정렬
    results_df = results_df.sort_values('annual_return', ascending=False)
    
    # 결과 저장
    results_df.to_csv('/home/ubuntu/parameter_optimization_results.csv', index=False)
    
    print(f"파라미터 최적화 완료. 결과가 '/home/ubuntu/parameter_optimization_results.csv'에 저장되었습니다.")
    
    return best_params, best_result, results_df

# 메인 실행 부분
if __name__ == "__main__":
    # 백테스팅 실행
    backtester = BackTester(
        ticker=COIN_TICKER,
        days=DAYS,
        k=LARRY_K,
        noise_limit=DUAL_NOISE_LIMIT,
        trailing_min_profit=TRAILING_STOP_MIN_PROFIT,
        trailing_gap=TRAILING_STOP_GAP,
        fee=FEE
    )
    
    # 데이터 가져오기
    backtester.fetch_data()
    
    # 데이터 저장 (최적화에서 재사용)
    df = backtester.df.copy()
    
    # 백테스팅 실행
    summary, result_df, trades, daily_balance = backtester.run_backtest()
    
    # 결과 출력
    print("\n===== 백테스팅 결과 =====")
    print(f"코인: {summary['ticker']}")
    print(f"기간: {summary['period']}")
    print(f"파라미터: K={summary['k']}, 노이즈 한계={summary['noise_limit']}, "
          f"트레일링 최소 수익률={summary['trailing_min_profit']}, 트레일링 갭={summary['trailing_gap']}")
    print(f"초기 자본: {summary['initial_balance']:,.0f}원")
    print(f"최종 자본: {summary['final_balance']:,.0f}원")
    print(f"총 수익률: {summary['total_return']:.2%}")
    print(f"연간 수익률: {summary['annual_return']:.2%}")
    print(f"최대 낙폭 (MDD): {summary['mdd']:.2%}")
    print(f"승률: {summary['win_rate']:.2%}")
    print(f"총 거래 횟수: {summary['total_trades']}")
    
    # 결과 시각화
    backtester.plot_results(daily_balance)
    
    # 파라미터 최적화 실행 (시간이 오래 걸릴 수 있음)
    # 최적화 범위를 줄여서 실행 시간 단축
    print("\n파라미터 최적화를 시작합니다. 이 과정은 몇 분 정도 소요될 수 있습니다...")
    
    # 테스트할 파라미터 범위 축소
    k_values = [0.4, 0.5, 0.6]
    noise_limits = [0.5, 0.6, 0.7]
    trailing_min_profits = [0.3, 0.4]
    trailing_gaps = [0.03, 0.05]
    
    best_result = None
    best_params = None
    best_annual_return = -1
    
    results = []
    
    # 모든 파라미터 조합 테스트
    total_combinations = len(k_values) * len(noise_limits) * len(trailing_min_profits) * len(trailing_gaps)
    current = 0
    
    for k in k_values:
        for noise_limit in noise_limits:
            for trailing_min_profit in trailing_min_profits:
                for trailing_gap in trailing_gaps:
                    current += 1
                    print(f"파라미터 조합 테스트 중: {current}/{total_combinations} "
                          f"(K={k}, Noise={noise_limit}, Min_Profit={trailing_min_profit}, Gap={trailing_gap})")
                    
                    # 백테스터 생성 및 실행
                    backtester = BackTester(
                        ticker=COIN_TICKER,
                        days=DAYS,
                        k=k,
                        noise_limit=noise_limit,
                        trailing_min_profit=trailing_min_profit,
                        trailing_gap=trailing_gap,
                        fee=FEE
                    )
                    
                    try:
                        # 데이터는 이미 가져온 것을 재사용
                        backtester.df = df.copy()
                        summary, _, _, _ = backtester.run_backtest()
                        
                        # 결과 저장
                        results.append({
                            'k': k,
                            'noise_limit': noise_limit,
                            'trailing_min_profit': trailing_min_profit,
                            'trailing_gap': trailing_gap,
                            'annual_return': summary['annual_return'],
                            'total_return': summary['total_return'],
                            'mdd': summary['mdd'],
                            'win_rate': summary['win_rate'],
                            'total_trades': summary['total_trades']
                        })
                        
                        # 최고 수익률 갱신 확인
                        if summary['annual_return'] > best_annual_return:
                            best_annual_return = summary['annual_return']
                            best_result = summary
                            best_params = {
                                'k': k,
                                'noise_limit': noise_limit,
                                'trailing_min_profit': trailing_min_profit,
                                'trailing_gap': trailing_gap
                            }
                            
                            print(f"새로운 최적 파라미터 발견: 연간 수익률 {best_annual_return:.2%}")
                    
                    except Exception as e:
                        print(f"백테스팅 오류: {e}")
    
    # 결과를 데이터프레임으로 변환
    results_df = pd.DataFrame(results)
    
    # 연간 수익률 기준으로 정렬
    results_df = results_df.sort_values('annual_return', ascending=False)
    
    # 결과 저장
    results_df.to_csv('/home/ubuntu/parameter_optimization_results.csv', index=False)
    
    print("\n===== 파라미터 최적화 결과 =====")
    print(f"최적 파라미터: K={best_params['k']}, 노이즈 한계={best_params['noise_limit']}, "
          f"트레일링 최소 수익률={best_params['trailing_min_profit']}, 트레일링 갭={best_params['trailing_gap']}")
    print(f"연간 수익률: {best_result['annual_return']:.2%}")
    print(f"총 수익률: {best_result['total_return']:.2%}")
    print(f"최대 낙폭 (MDD): {best_result['mdd']:.2%}")
    print(f"승률: {best_result['win_rate']:.2%}")
    
    # 최적 파라미터로 백테스팅 다시 실행하고 그래프 생성
    print("\n최적 파라미터로 백테스팅 다시 실행...")
    optimal_backtester = BackTester(
        ticker=COIN_TICKER,
        days=DAYS,
        k=best_params['k'],
        noise_limit=best_params['noise_limit'],
        trailing_min_profit=best_params['trailing_min_profit'],
        trailing_gap=best_params['trailing_gap'],
        fee=FEE
    )
    optimal_backtester.df = df.copy()
    _, _, _, optimal_daily_balance = optimal_backtester.run_backtest()
    optimal_backtester.plot_results(optimal_daily_balance)
    print(f"최적화된 파라미터 백테스팅 결과 그래프가 '/home/ubuntu/backtest_result.png'에 저장되었습니다.")
