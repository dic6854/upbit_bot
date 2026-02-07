import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.font_manager as fm

def __get_tick_size(price):     # 호가단위(Tick Size) 반환
    if price >= 2000000: return 1000
    elif price >= 1000000: return 500
    elif price >= 500000: return 100
    elif price >= 100000: return 50
    elif price >= 10000: return 10
    elif price >= 1000: return 1
    elif price >= 100: return 1     # 100원대 코인 (1원 단위)
    elif price >= 10: return 0.1    # 10원대 코인 (0.1원 단위)
    else: return 0.01               # 10원 미만 코인 (0.01원 단위)

# 상수 설정
TOTAL_ASSETS = 10000000.0       # 1000만원
INVESTMENT_RATIO = 0.20         # 전체 자산의 20%만 투자
TARGET_VOLATILITY = 2.0         # 목표 변동성 (타켓변동성) 2%로 설정
NUM_COINS = 4                   # 투자할 코인 개수 4개 : BTC, XRP, ETH, ADA
INVEST_PER_COIN = TOTAL_ASSETS * INVESTMENT_RATIO / NUM_COINS  # 각 코인당 500,000원
FEE_RATE = 0.001                # (수수료=0.05%=0.0005) + (슬리피지율=0.05%=0.0005)=0.1%=0.001

# 엑셀 파일에서 데이터 로드
file_path = 'day.xlsx'
coins = ['BTC', 'XRP', 'ETH', 'ADA']

data = {}
for coin in coins:
    df = pd.read_excel(file_path, sheet_name=coin)
    df['date'] = pd.to_datetime(df['date'])
    df.set_index('date', inplace=True)
    df.sort_index(inplace=True)
    df['MA5'] = df['close'].rolling(window=5).mean()
    df['MA10'] = df['close'].rolling(window=10).mean()
    df['MA20'] = df['close'].rolling(window=20).mean()

    # (1일변동성)=[[(전일고가)-(전일저가)]/(당일시가)]*100
    df['day_volatility'] = ((df['high'].shift(1) - df['low'].shift(1)) / df['open']) * 100
    # (5일평균변동성)=[(1일변동성)]
    df['VMA5'] = df['day_volatility'].rolling(window=5).mean()

    df = df.dropna()
    df = df.loc['2021-01-01':'2025-12-31']
    data[coin] = df

# 모든 코인이 공통으로 존재하는 날짜만 사용
common_dates = set(data['BTC'].index)
for coin in coins[1:]:
    common_dates.intersection_update(data[coin].index)
common_dates = sorted(list(common_dates))

# 포트폴리오 초기화 - float 타입으로
portfolio = pd.DataFrame(
    index=common_dates,
    columns=['total_value', 'cash', 'holdings_value'],      # 총자산, 현금, 코인투자대기금
    data=0.0
)

# initial_cash = TOTAL_ASSETS * (1 - INVESTMENT_RATIO)        # 현금현황 초기화
initial_cash = TOTAL_ASSETS                     # 현금현황 초기화
portfolio['cash'] = initial_cash                # 현금
portfolio['total_value'] = initial_cash         # 총자금

# 포지션 및 투자금 추적
positions = {coin: 0.0 for coin in coins}       # {'BTC': 0.0, 'XRP': 0.0, 'ETH': 0.0, 'ADA': 0.0}
invested_amount = {coin: 0.0 for coin in coins} # {'BTC': 0.0, 'XRP': 0.0, 'ETH': 0.0, 'ADA': 0.0}

trade_logs = []

# 백테스팅 시뮬레이션
for i, date in enumerate(common_dates):
    if i > 0:   # 첫요소는 넘어가고, 두번째 요소부터 체크
        prev_date = common_dates[i-1]   # 이전 요소의 날짜 데이터 저장
        portfolio.loc[date, 'cash'] = portfolio.loc[prev_date, 'cash']      # 이전요소의 현금상황을 현요소의 현금상황에 넣음

    current_holdings_value = 0.0    # 투자자금을 0으로 초기화

    for coin in coins:         # 코인을 BTC -> XRP -> ETH -> ADA 순으로 순환함
        row = data[coin].loc[date]  # 해당 날짜의 행(Row) 데이터값을 row 변수(dict형)에 저장
        close = row['close']        # row에서 'close'(종가) key의 key값을 close라는 변수에 저장
        ma5 = row['MA5']            # row에서 'MA5'(5일이평선값) key의 key값을 ma5라는 변수에 저장
        ma10 = row['MA10']          # row에서 'MA10'(10일이평선값) key의 key값을 ma10라는 변수에 저장
        ma20 = row['MA20']          # row에서 'MA20'(20일이평선값) key의 key값을 ma20라는 변수에 저장
        vma5 = row['VMA5']          # row에서 'VMA5'(5일평균변동성) key의 key값을 VMA5라는 변수에 저장

        if (close > ma5 and close > ma10 and close > ma20): # 현재가가 5일, 10일, 20일 이평선 모두의 위에 있을때 => 매수 조건 충족
            remaining_alloc = INVEST_PER_COIN - invested_amount[coin]   # 해당 코인의 투자 비중 설정    
            buy_amount = min(remaining_alloc, portfolio.loc[date, 'cash'])
            weight = (TARGET_VOLATILITY / vma5) * (1 / NUM_COINS)     # 해당 코인의 투자 비중 설정
            target_amount = buy_amount * weight

            if target_amount > 0:
                fee = target_amount * FEE_RATE
                actual_buy = target_amount - fee
                quantity = actual_buy / close
                safe_qty = float("{:.8f}".format(quantity))     # 수량: 소수점 8째 자리까지만 남기고 버림
                
                portfolio.loc[date, 'cash'] -= actual_buy
                positions[coin] += safe_qty
                invested_amount[coin] += actual_buy
                
                trade_logs.append({
                    'date': date,
                    'coin': coin,
                    'action': 'buy',
                    'price': close,
                    'quantity': safe_qty,
                    'profit_loss': 0.0
                })
        # 현재가가 5일, 10일, 20일 이평선 중 어느 하나 아래에 있고, 해당 코인을 보유하고 있을때 => 매도 조건 충족
        elif ((close < ma5 or close < ma10 or close < ma20) and (positions[coin] > 0)): 
            sell_value = positions[coin] * close        # 매도할 금액
            fee = sell_value * FEE_RATE                 # 수수료
            cash_in = sell_value - fee                  # 현금 증가
            portfolio.loc[date, 'cash'] += cash_in      # 현금 증가

            avg_buy_price = invested_amount[coin] / positions[coin]   # 평균 매수 단가
            pl = (close - avg_buy_price) * positions[coin] - fee      # 손익

            trade_logs.append({
                'date': date,
                'coin': coin,
                'action': 'sell',
                'price': close,
                'quantity': positions[coin],
                'profit_loss': pl
            })

            positions[coin] = 0.0   # 포지션 초기화
            invested_amount[coin] = 0.0   # 투자금 초기화
        
        current_holdings_value += positions[coin] * close

    portfolio.loc[date, 'holdings_value'] = current_holdings_value
    portfolio.loc[date, 'total_value'] = portfolio.loc[date, 'cash'] + current_holdings_value
            
# 결과 출력
trade_df = pd.DataFrame(trade_logs)
trade_df.set_index('date', inplace=True)
print(trade_df)
trade_df.to_excel('trade.xlsx')
print(portfolio)
portfolio.to_excel('portfolio.xlsx')