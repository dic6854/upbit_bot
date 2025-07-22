import pyupbit
import pandas as pd
from datetime import datetime, timedelta
import time # API 호출 딜레이를 위한 라이브러리

# --- 1. 설정 변수 ---
START_DATE_STR = "2025-06-01"
END_DATE_STR = "2025-06-30"
INITIAL_CASH = 10000000  # 초기 현금 (1000만원), 여러 코인에 분산 투자 가정
BUY_AMOUNT_PER_TRADE = 100000  # 매수 금액 (10만원) - 각 코인별
MA_PERIOD = 30  # 이동평균 기간 (30일 단순 이동평균)
API_CALL_DELAY = 0.1 # API 호출 간 딜레이 (초), 너무 빠르면 API 제한 걸림

# --- 2. 날짜 문자열을 datetime 객체로 변환 ---
start_date = datetime.strptime(START_DATE_STR, "%Y-%m-%d")
end_date = datetime.strptime(END_DATE_STR, "%Y-%m-%d")

# --- 3. 모든 KRW 마켓 티커 가져오기 ---
all_krw_tickers = pyupbit.get_tickers(fiat="KRW")
print(f"총 {len(all_krw_tickers)}개의 KRW 마켓 코인을 대상으로 백테스트를 진행합니다.")

# --- 4. 백테스트 준비 ---
total_cash = INITIAL_CASH
coin_holdings = {ticker: 0 for ticker in all_krw_tickers} # 각 코인별 보유량 (개수)
daily_total_assets = {} # 날짜별 총 자산 기록

print(f"--- 백테스트 시작: 모든 KRW 코인 ({START_DATE_STR} ~ {END_DATE_STR}) ---")
print(f"초기 현금: {INITIAL_CASH:,.0f}원")
print(f"코인별 매수 금액: {BUY_AMOUNT_PER_TRADE:,.0f}원")
print(f"이동평균 기간: {MA_PERIOD}일\n")

# 날짜 범위를 순회하며 일별 백테스트 진행
current_backtest_date = start_date
while current_backtest_date <= end_date:
    current_date_str = current_backtest_date.strftime("%Y-%m-%d")
    print(f"\n===== 날짜: {current_date_str} =====")
    
    # 일별 자산 계산을 위한 초기값 설정
    # 매매 전 현재가로 코인 가치 평가
    current_prices_for_evaluation = {}
    for t in all_krw_tickers:
        try:
            # 현재 날짜의 종가를 가져옴 (get_ohlcv는 to 날짜까지 포함)
            ohlcv_today = pyupbit.get_ohlcv(t, interval="day", to=current_backtest_date + timedelta(days=1))
            if ohlcv_today is not None and not ohlcv_today.empty:
                current_prices_for_evaluation[t] = ohlcv_today['close'].iloc[-1]
            time.sleep(API_CALL_DELAY) # API 호출 간 딜레이
        except Exception:
            current_prices_for_evaluation[t] = 0 # 데이터 없으면 0으로 간주

    day_start_coin_value = sum(coin_holdings[t] * current_prices_for_evaluation.get(t, 0)
                               for t in all_krw_tickers if coin_holdings[t] > 0)
    current_day_total_asset = total_cash + day_start_coin_value
    print(f"  > 시작 자산: {current_day_total_asset:,.0f}원 (현금: {total_cash:,.0f}원)")

    # 각 코인별로 데이터 가져오고 매매 로직 적용
    for ticker in all_krw_tickers:
        try:
            # 이동평균 계산을 위해 충분한 과거 데이터와 현재 날짜까지의 데이터를 가져옵니다.
            # to=current_backtest_date + timedelta(days=1)로 하면 오늘 데이터까지 가져옴
            ohlcv = pyupbit.get_ohlcv(ticker, interval="day", to=current_backtest_date + timedelta(days=1))
            
            if ohlcv is None or ohlcv.empty:
                continue

            # 백테스트에 필요한 최소 데이터 개수 (MA_PERIOD + 2 for prev_prev_close)
            if len(ohlcv) < MA_PERIOD + 2:
                continue

            ohlcv['ma'] = ohlcv['close'].rolling(window=MA_PERIOD).mean()

            # 현재 날짜 데이터 확인
            # 마지막 데이터가 오늘 날짜 데이터, 그 전이 어제, 그 전전이 그저께 데이터
            current_day_data = ohlcv.iloc[-1]
            prev_day_data = ohlcv.iloc[-2]
            prev_prev_day_data = ohlcv.iloc[-3]

            prev_close = prev_day_data['close']
            prev_ma = prev_day_data['ma']
            prev_prev_close = prev_prev_day_data['close']
            prev_prev_ma = prev_prev_day_data['ma']
            current_close = current_day_data['close']

            # 이동평균이 NaN인 경우 (데이터 부족) 스킵
            if pd.isna(prev_ma) or pd.isna(prev_prev_ma):
                continue

            # --- 상향 돌파 조건 ---
            is_golden_cross = (prev_close >= prev_ma) and (prev_prev_close < prev_prev_ma)

            # --- 하향 돌파 조건 ---
            is_death_cross = (prev_close <= prev_ma) and (prev_prev_close > prev_prev_ma)

            action = "유지"
            
            # 매매 로직 적용
            if is_golden_cross:
                if total_cash >= BUY_AMOUNT_PER_TRADE: # 총 현금 잔고 확인
                    trade_amount_btc = BUY_AMOUNT_PER_TRADE / current_close
                    coin_holdings[ticker] += trade_amount_btc
                    total_cash -= BUY_AMOUNT_PER_TRADE
                    action = f"매수 (종가: {current_close:,.0f}, {BUY_AMOUNT_PER_TRADE:,}원 어치)"
                    print(f"    {ticker}: {action} (남은 현금: {total_cash:,.0f}원)")
                else:
                    action = "매수 실패 (총 현금 부족)"
                    # print(f"    {ticker}: {action}")

            elif is_death_cross:
                if coin_holdings[ticker] > 0: # 해당 코인 보유량 확인
                    sell_value = coin_holdings[ticker] * current_close
                    total_cash += sell_value
                    print(f"    {ticker}: 전량 매도 (종가: {current_close:,.0f}, {coin_holdings[ticker]:.4f} {ticker.split('-')[1]}, {sell_value:,.0f}원)")
                    coin_holdings[ticker] = 0
                else:
                    action = "매도 실패 (보유 코인 없음)"
                    # print(f"    {ticker}: {action}")
            
            time.sleep(API_CALL_DELAY) # API 호출 간 딜레이
        
        except Exception as e:
            # print(f"    {ticker} 데이터 처리 중 오류 발생: {e}")
            pass # 오류 발생 시 해당 코인 스킵

    # 일별 총 자산 업데이트 (매매 후 현재가로 평가)
    total_coin_value_at_eod = sum(coin_holdings[t] * current_prices_for_evaluation.get(t, 0) for t in all_krw_tickers)
    daily_total_assets[current_backtest_date.strftime("%Y-%m-%d")] = total_cash + total_coin_value_at_eod
    
    print(f"  > 일일 종료 시 총 현금: {total_cash:,.0f}원")
    print(f"  > 일일 종료 시 총 코인 가치: {total_coin_value_at_eod:,.0f}원")
    print(f"  > 일일 종료 시 총 자산: {total_cash + total_coin_value_at_eod:,.0f}원")

    current_backtest_date += timedelta(days=1)

# --- 5. 최종 결과 출력 ---
final_total_asset = daily_total_assets[END_DATE_STR] if END_DATE_STR in daily_total_assets else INITIAL_CASH

print("\n--- 백테스트 종료 ---")
print(f"초기 자산: {INITIAL_CASH:,.0f}원")
print(f"최종 총 자산: {final_total_asset:,.0f}원")
net_profit_loss = final_total_asset - INITIAL_CASH
profit_loss_percentage = (net_profit_loss / INITIAL_CASH) * 100 if INITIAL_CASH > 0 else 0

print(f"순손익: {net_profit_loss:,.0f}원")
print(f"수익률: {profit_loss_percentage:.2f}%")

# 각 코인별 최종 보유량 및 가치 출력
print("\n--- 코인별 최종 보유 현황 ---")
for ticker, amount in coin_holdings.items():
    if amount > 0:
        final_price = current_prices_for_evaluation.get(ticker, 0) # 마지막 날의 평가 가격 사용
        print(f"  {ticker}: {amount:.4f}개 (현재가치: {amount * final_price:,.0f}원)")

# (선택 사항) 총 자산 변화 시각화
try:
    import matplotlib.pyplot as plt
    
    dates = list(daily_total_assets.keys())
    assets = list(daily_total_assets.values())

    plt.figure(figsize=(14, 7))
    plt.plot(dates, assets, marker='o', linestyle='-', color='purple')
    plt.title(f'전체 KRW 코인 백테스트 총 자산 변화 ({START_DATE_STR} ~ {END_DATE_STR})')
    plt.xlabel('날짜')
    plt.ylabel('총 자산 (원)')
    plt.grid(True)
    plt.xticks(rotation=45)
    plt.tight_layout()
    plt.show()
except ImportError:
    print("\nmatplotlib이 설치되어 있지 않아 그래프를 그릴 수 없습니다. 'pip install matplotlib'을 실행해주세요.")
