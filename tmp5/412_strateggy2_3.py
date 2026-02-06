import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# 시각화를 위한 설정
plt.style.use('seaborn-v0_8-darkgrid')

class CryptoBacktester:
    """
    암호화폐 과거 데이터를 이용한 시뮬레이션 클래스
    """
    def __init__(self, file_path, initial_capital=10_000_000, crypto_percent=0.2, fee_rate=0.0005):
        """
        초기화 함수
        :param file_path: day.xlsx 파일 경로
        :param initial_capital: 초기 자본금 (기본 1000만 원)
        :param crypto_percent: 가상화폐 투자 비중 (기본 20%)
        :param fee_rate: 거래 수수료 (기본 0.05%)
        """
        self.file_path = file_path
        self.initial_capital = initial_capital
        self.crypto_percent = crypto_percent
        self.fee_rate = fee_rate
        self.coins = ['BTC', 'ETH', 'XRP', 'ADA']
        self.data = {}
        self.fixed_cash = self.initial_capital * (1 - self.crypto_percent)
        self.alloc_per_coin = self.initial_capital * self.crypto_percent / len(self.coins)
        self.cash = {coin: self.alloc_per_coin for coin in self.coins}
        self.holdings = {coin: 0 for coin in self.coins}
        self.result_df = None
        self.trade_log = None

    def load_and_prepare_data(self):
        """
        데이터를 로드하고 전처리를 수행하는 함수
        """
        try:
            for coin in self.coins:
                df = pd.read_excel(self.file_path, sheet_name=coin)
                df.columns = [c.strip().lower() for c in df.columns]
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.sort_values('date').set_index('date')
                else:
                    raise ValueError(f"데이터에 'date' 컬럼이 존재하지 않습니다. ({coin})")
                df = df.ffill().dropna()
                print(f"{coin} 데이터 로드 완료: {len(df)}개의 행, 기간: {df.index[0]} ~ {df.index[-1]}")
                self.data[coin] = df

            # 공통 날짜 찾기
            all_dates = [set(df.index) for df in self.data.values()]
            common_dates = set.intersection(*all_dates)
            self.dates = sorted(common_dates)
            print(f"공통 기간: {self.dates[0]} ~ {self.dates[-1]}, {len(self.dates)} days")

        except Exception as e:
            print(f"데이터 로드 중 오류 발생: {e}")
            raise

    def add_indicators(self):
        """
        보조지표 생성 함수 (전략에 필요한 지표 계산)
        """
        for coin in self.coins:
            df = self.data[coin]
            # 5일 이동평균 (look-ahead bias 방지 위해 shift(1))
            df['ma5'] = df['close'].rolling(window=5).mean().shift(1)

    def run_simulation(self):
        """
        실제 매매 로직 시뮬레이션 수행
        """
        equity_curve = [self.initial_capital]
        trade_log = []

        for date in self.dates:
            current_equity = self.fixed_cash
            for coin in self.coins:
                row = self.data[coin].loc[date]
                if pd.isna(row['ma5']):
                    coin_value = self.holdings[coin] * row['close'] if self.holdings[coin] > 0 else 0
                    current_equity += self.cash[coin] + coin_value
                    continue

                close = row['close']
                ma5 = row['ma5']

                if self.holdings[coin] > 0:
                    coin_value = self.holdings[coin] * close
                    if close < ma5:
                        # 매도
                        sell_cash = coin_value * (1 - self.fee_rate)
                        trade_log.append({'date': date, 'coin': coin, 'action': 'sell', 'price': close, 'quantity': self.holdings[coin], 'cash_received': sell_cash})
                        self.cash[coin] += sell_cash
                        self.holdings[coin] = 0
                        coin_value = 0
                else:
                    coin_value = 0
                    if close > ma5 and self.cash[coin] > 0:
                        # 매수
                        quantity = self.cash[coin] * (1 - self.fee_rate) / close
                        trade_log.append({'date': date, 'coin': coin, 'action': 'buy', 'price': close, 'quantity': quantity, 'cost': self.cash[coin]})
                        self.holdings[coin] = quantity
                        self.cash[coin] = 0

                current_equity += self.cash[coin] + coin_value

            equity_curve.append(current_equity)

        self.result_df = pd.DataFrame({'date': self.dates, 'equity': equity_curve[1:]}).set_index('date')
        self.trade_log = pd.DataFrame(trade_log)

    def analyze_performance(self):
        """
        성과 분석 및 지표 출력
        """
        if self.result_df is None:
            print("시뮬레이션이 실행되지 않았습니다.")
            return

        total_return = (self.result_df['equity'].iloc[-1] / self.initial_capital) - 1

        self.result_df['hwm'] = self.result_df['equity'].cummax()
        self.result_df['dd'] = (self.result_df['equity'] - self.result_df['hwm']) / self.result_df['hwm']
        mdd = self.result_df['dd'].min()

        # 완료된 거래 (buy-sell 쌍) 계산
        trades = []
        current_trades = {coin: None for coin in self.coins}
        for _, row in self.trade_log.iterrows():
            coin = row['coin']
            if row['action'] == 'buy':
                current_trades[coin] = {'buy_price': row['price'], 'cost': row['cost']}
            elif row['action'] == 'sell' and current_trades[coin]:
                sell_price = row['price']
                ror = (row['cash_received'] / current_trades[coin]['cost'])
                trades.append({'coin': coin, 'ror': ror})
                current_trades[coin] = None

        num_trades = len(trades)
        win_rate = 0
        if num_trades > 0:
            trades_df = pd.DataFrame(trades)
            win_rate = len(trades_df[trades_df['ror'] > 1]) / num_trades

        print("="*40)
        print(f" 시뮬레이션 결과 보고서 ({self.file_path})")
        print("="*40)
        print(f"초기 자본금: {self.initial_capital:,.0f} KRW")
        print(f"최종 평가액: {self.result_df['equity'].iloc[-1]:,.0f} KRW")
        print(f"총 수익률 : {total_return * 100:.2f}%")
        print(f"MDD (최대 낙폭): {mdd * 100:.2f}%")
        print(f"매매 승률 : {win_rate * 100:.2f}%")
        print(f"총 거래 횟수 (완료된 buy-sell 쌍): {num_trades}")
        print("="*40)

        return self.result_df

# --- 실행 예시 ---
if __name__ == "__main__":
    # 파일 경로를 실제 경로로 변경하세요
    simulator = CryptoBacktester('day.xlsx')
    simulator.load_and_prepare_data()
    simulator.add_indicators()
    simulator.run_simulation()
    simulator.analyze_performance()

    # 선택적으로 자산 곡선 시각화
    simulator.result_df['equity'].plot(figsize=(12, 6), title='Portfolio Equity Curve')
    plt.show()