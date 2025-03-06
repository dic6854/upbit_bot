import backtrader as bt
import pandas as pd

class RSIBollingerMACross(bt.Strategy):
    params = (
        ('rsi_period', 14),
        ('rsi_upper', 60),  # 더 완화: 65 → 60
        ('rsi_lower', 40),  # 더 완화: 35 → 40
        ('sma_short', 5),
        ('sma_long', 20),
        ('size', 0.01),
    )

    def __init__(self):
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)
        self.sma_short = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.sma_short
        )
        self.sma_long = bt.indicators.SimpleMovingAverage(
            self.data.close, period=self.p.sma_long
        )
        self.ma_cross = bt.indicators.CrossOver(self.sma_short, self.sma_long)
        self.order = None

    def log(self, txt):
        dt = self.datas[0].datetime.datetime(0)
        print(f'{dt}: {txt}')

    def notify_order(self, order):
        if order.status in [order.Completed]:
            if order.isbuy():
                self.log(f'BUY EXECUTED, Price: {order.executed.price:,.0f}')
            elif order.issell():
                self.log(f'SELL EXECUTED, Price: {order.executed.price:,.0f}')
            self.order = None

    def next(self):
        if self.order:
            return

        price = self.data.close[0]
        rsi = self.rsi[0]
        ma_cross = self.ma_cross[0]

        # 디버깅용 로그
        self.log(f'RSI: {rsi:.2f}, Price: {price:,.0f}, MA Cross: {ma_cross}')

        if not self.position:
            if rsi <= self.p.rsi_lower and ma_cross > 0:
                self.log(f'BUY SIGNAL - RSI: {rsi:.2f}, Price: {price:,.0f}')
                self.order = self.buy(size=self.p.size)
        elif self.position:
            if rsi >= self.p.rsi_upper and ma_cross < 0:
                self.log(f'SELL SIGNAL - RSI: {rsi:.2f}, Price: {price:,.0f}')
                self.order = self.sell(size=self.p.size)

if __name__ == '__main__':
    cerebro = bt.Cerebro()
    cerebro.addstrategy(RSIBollingerMACross)

    # 데이터 로드 및 확인
    df = pd.read_excel('KRW-BTC.xlsx', parse_dates=[0], index_col=0)
    print("Data Preview:")
    print(df.head())  # 데이터 확인용 출력
    print("Columns:", df.columns.tolist())  # 열 이름 확인

    # 열 이름 조정 (필요 시 주석 해제)
    # df = df.rename(columns={'시가': 'open', '고가': 'high', '저가': 'low', '종가': 'close', '거래량': 'volume'})

    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)
    cerebro.broker.setcash(10000000)  # 1000만 원
    cerebro.broker.setcommission(commission=0.0005)  # 0.05%

    # 분석기 추가
    cerebro.addanalyzer(bt.analyzers.SharpeRatio, _name='sharpe')
    cerebro.addanalyzer(bt.analyzers.Returns, _name='returns')
    cerebro.addanalyzer(bt.analyzers.TradeAnalyzer, _name='trades')

    print('Starting Portfolio Value: %.2f' % cerebro.broker.getvalue())
    results = cerebro.run()
    print('Final Portfolio Value: %.2f' % cerebro.broker.getvalue())

    strat = results[0]
    print('Sharpe Ratio:', strat.analyzers.sharpe.get_analysis().get('sharperatio', 'N/A'))
    print('Total Return:', strat.analyzers.returns.get_analysis().get('rtot', 'N/A'))

    trade_analysis = strat.analyzers.trades.get_analysis()
    total_trades = trade_analysis.get('total', {}).get('total', 0) if trade_analysis else 0
    print('Total Trades:', total_trades)
    if total_trades > 0:
        print('Profit/Loss:', trade_analysis.get('pnl', {}).get('net', {}).get('total', 'N/A'))
    else:
        print('No trades executed.')