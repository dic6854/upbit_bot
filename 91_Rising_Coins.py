import pyupbit
import pandas as pd
import time
from datetime import datetime, timedelta

# 설정값
RSI_PERIOD = 14
MIN_PRICE_CHANGE = 0
MIN_VOLUME_CHANGE = 0
MIN_RSI = 45

# 상위 5개 상승 추세 코인 선정 함수
def select_top_rising_coins():
    # 모든 KRW 마켓 티커 가져오기
    tickers = pyupbit.get_tickers(fiat="KRW")
    total_count = len(tickers)
    print(f"총 {total_count}개 코인 조회됨")

    # 결과 저장용 리스트
    rising_coins = []

    # df = pd.DataFrame(columns=['ticker', 'price_change', 'volume_change', 'rsi', 'ma5', 'current_price', 'condition'])
    df = pd.DataFrame(columns=['ticker', 'price_change', 'volume_change', 'rsi', 'ma5', 'current_price'])
    current_count = 1
    for ticker in tickers:
        try:
            # 24시간 가격 상승률 계산 (일봉 데이터)
            df_day = pyupbit.get_ohlcv(ticker, interval="day", count=(RSI_PERIOD+1))
            if df_day is None or len(df_day) < (RSI_PERIOD+1):
                print(f"[{current_count} / {total_count}] - ticker: {ticker} was skipped")
                current_count += 1
                continue

            time.sleep(0.05)

            current_price = pyupbit.get_current_price(ticker)
            prev_close = df_day['close'].iloc[-2]
            price_change = (current_price - prev_close) / prev_close * 100

            # 거래량 증가율 계산
            current_volume = df_day['volume'].iloc[-1]
            prev_volume = df_day['volume'].iloc[-2]
            volume_change = (current_volume - prev_volume) / prev_volume if prev_volume > 0 else 0

            # MA5 계산
            # df_5day = pyupbit.get_ohlcv(ticker, interval="day", count=6)
            # if len(df_day) < 6:
            #     continue
            ma5 = df_day['close'].rolling(window=5).mean().iloc[-1]

            # RSI 계산 (5분봉 기준)
            delta = df_day['close'].diff()
            gain = delta.where(delta > 0, 0).rolling(window=RSI_PERIOD).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=RSI_PERIOD).mean()
            rs = gain / loss if loss.iloc[-2] != 0 else float('inf')
            rsi = 100 - (100 / (1 + rs.iloc[-2]))

            # 조건: 가격 상승률 > 0, 거래량 증가, 현재가 >= MA5, RSI >= 50
            if (price_change > MIN_PRICE_CHANGE and  volume_change > MIN_VOLUME_CHANGE and rsi >= MIN_RSI and current_price >= ma5):
                rising_coins.append({'ticker': ticker, 'price_change': price_change, 'volume_change': volume_change, 'rsi': rsi, 'ma5': ma5, 'current_price': current_price})
            # else:
            #     rising_coins.append({'ticker': ticker, 'price_change': price_change, 'volume_change': volume_change, 'ma5': ma5, 'rsi': rsi, 'current_price': current_price, 'condition': False})

            print(f"[{current_count} / {total_count}] - ticker: {ticker}, price_change: {price_change:.2f}, volume_change: {volume_change:.2f}, rsi: {rsi:.2f}, ma5: {ma5:.2f}, current_price: {current_price:.2f}")

        except Exception as e:
            print(f"{ticker} 처리 중 오류: {e}")
            continue

        current_count += 1

    print(f"Skip_Count = {skip_count}")
    # rising_coins_df = pd.DataFrame(rising_coins)
    # if not rising_coins_df.empty and not rising_coins_df.isnull().all().all():
    #     df = pd.concat([df, rising_coins_df], ignore_index=True)
    #     df.to_csv('Riasing_Coins.csv', index=True)

    # 가격 상승률 기준으로 상위 5개 정렬
    rising_coins = sorted(rising_coins, key=lambda x: x['price_change'], reverse=True)[:5]
    
    return rising_coins

# RSIBollingerDayTradingBot 적용
if __name__ == "__main__":
    # 상위 5개 코인 선정
    top_coins = select_top_rising_coins()
    # print(top_coins)
    # print("\n상승 추세 상위 5개 코인:")
    # coin = top_coins[0]
    # print(f"{coin['ticker']}: 상승률 {coin['price_change']:.2f}%, 거래량 증가율 {coin['volume_change']:.2f}, RSI {coin['rsi']:.2f}")
    for coin in top_coins:
        print(f"{coin['ticker']}: 상승률 {coin['price_change']:.2f}%, 거래량 증가율 {coin['volume_change']:.2f}, RSI {coin['rsi']:.2f}")

    '''
    # 각 코인에 대해 RSIBollingerDayTradingBot 실행
    for coin in top_coins:
        bot = RSIBollingerDayTradingBot(ticker=coin['ticker'], debug=True)
        print(f"\n{coin['ticker']}에 대해 봇 실행 중...")
        bot.run()  # 실제로는 별도 스레드나 프로세스로 실행 권장
    '''