import pandas as pd
import numpy as np

def calculate_ema(df, period, column='close'):
    """지수이동평균(EMA) 계산"""
    return df[column].ewm(span=period, adjust=False).mean()

def calculate_macd(df, fast_period, slow_period, signal_period, column='close'):
    """MACD, Signal, Histogram 계산"""
    ema_fast = calculate_ema(df, fast_period, column)
    ema_slow = calculate_ema(df, slow_period, column)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(df, signal_period, macd_line)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram

def calculate_atr(df, period):
    """ATR(Average True Range) 계산"""
    high_low = df['high'] - df['low']
    high_close_prev = abs(df['high'] - df['close'].shift(1))
    low_close_prev = abs(df['low'] - df['close'].shift(1))
    tr = pd.concat([high_low, high_close_prev, low_close_prev], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

def get_stage(ema6, ema12, ema24):
    """EMA 스테이지 판단"""
    if ema6 > ema12 > ema24:
        return "Stage 1"
    elif ema12 > ema6 > ema24:
        return "Stage 2"
    elif ema12 > ema24 > ema6:
        return "Stage 3"
    elif ema24 > ema12 > ema6:
        return "Stage 4"
    elif ema24 > ema6 > ema12:
        return "Stage 5"
    elif ema6 > ema24 > ema12:
        return "Stage 6"
    else:
        return "No Stage"

def is_macd_upward(macd_line, signal_line):
    """MACD 우상향 조건 확인"""
    return (macd_line.iloc[-1] > signal_line.iloc[-1]) and (macd_line.iloc[-2] <= signal_line.iloc[-2])

def is_macd_downward(macd_line, signal_line):
    """MACD 우하향 조건 확인"""
    return (macd_line.iloc[-1] < signal_line.iloc[-1]) and (macd_line.iloc[-2] >= signal_line.iloc[-2])

def turtle_trading_strategy(file_path):
    """터틀 트레이딩 전략 시뮬레이션"""
    # 엑셀 파일에서 데이터 로드
    minute5_df = pd.read_excel(file_path, sheet_name="minute5", index_col=0)
    minute1_df = pd.read_excel(file_path, sheet_name="minute1", index_col=0)

    # 결과 저장을 위한 DataFrame
    daily_results = []

    # 일별 시뮬레이션
    for date in minute5_df.index.date.unique():
        if pd.Timestamp(date).time() < pd.Timestamp("09:00").time(): # 첫날짜 오전 9시 이전 데이터 제외
            continue

        print(f"Simulating for date: {date}")

        # 해당 날짜의 데이터 필터링 (5분봉, 1분봉)
        daily_minute5_df = minute5_df[minute5_df.index.date == date].copy()
        daily_minute1_df = minute1_df[minute1_df.index.date == date].copy()

        if daily_minute5_df.empty or daily_minute1_df.empty: # 데이터 없는 날짜 건너뛰기
            print(f"No data for {date}, skipping...")
            continue

        # EMA 계산 (5분봉 기준)
        daily_minute5_df['6EMA'] = calculate_ema(daily_minute5_df, 6)
        daily_minute5_df['12EMA'] = calculate_ema(daily_minute5_df, 12)
        daily_minute5_df['24EMA'] = calculate_ema(daily_minute5_df, 24)

        # MACD 계산 (5분봉 기준)
        macd1_line, macd1_signal, _ = calculate_macd(daily_minute5_df, 6, 12, 9)
        macd2_line, macd2_signal, _ = calculate_macd(daily_minute5_df, 6, 24, 9)
        macd3_line, macd3_signal, _ = calculate_macd(daily_minute5_df, 12, 24, 9)
        daily_minute5_df['MACD1_Line'] = macd1_line
        daily_minute5_df['MACD1_Signal'] = macd1_signal
        daily_minute5_df['MACD2_Line'] = macd2_line
        daily_minute5_df['MACD2_Signal'] = macd2_signal
        daily_minute5_df['MACD3_Line'] = macd3_line
        daily_minute5_df['MACD3_Signal'] = macd3_signal

        # ATR 계산 (5분봉 기준)
        daily_minute5_df['ATR'] = calculate_atr(daily_minute5_df, 20)

        # 스테이지 판단 (5분봉 기준)
        daily_minute5_df['Stage'] = daily_minute5_df.apply(lambda row: get_stage(row['6EMA'], row['12EMA'], row['24EMA']), axis=1)

        # 거래 로직
        capital = 1000000  # 매일 자본금 100만원
        R = 0.05  # 리스크 비율 5%
        position = 0 # 매수 잔량
        units = 0 # 매수 단위
        entry_prices = [] # 매수 가격 기록 (평균 매수 가격 계산을 위해)
        stop_loss_prices = [] # 스탑로스 가격 기록 (각 매수 단위별)
        trade_log = [] # 거래 기록
        daily_profit = 0

        # 1분봉 데이터 순회
        for i in range(len(daily_minute1_df)):
            current_time_1min = daily_minute1_df.index[i]

            # 거래 시간 확인 (오전9시 ~ 익일 오전8시51분)
            if not (pd.Timestamp("09:00").time() <= current_time_1min.time() <= pd.Timestamp("23:59").time() or
                    pd.Timestamp("00:00").time() <= current_time_1min.time() <= pd.Timestamp("08:51").time()):
                continue

            # 5분봉 데이터 가져오기 (현재 1분봉 시간 이전의 가장 최근 5분봉 데이터)
            current_5min_time = current_time_1min.floor('5T') # 현재 1분봉 시간의 5분봉 시간
            if current_5min_time not in daily_minute5_df.index: # 해당 5분봉 데이터가 없으면 건너뛰기 (데이터 시작 시점 등)
                continue

            current_5min_data = daily_minute5_df.loc[current_5min_time]

            # **매수 조건 확인**
            buy_condition = (
                current_5min_data['Stage'] == "Stage 6" and
                is_macd_upward(current_5min_data[['MACD1_Line']].iloc[:], current_5min_data[['MACD1_Signal']].iloc[:]) and
                is_macd_upward(current_5min_data[['MACD2_Line']].iloc[:], current_5min_data[['MACD2_Signal']].iloc[:]) and
                is_macd_upward(current_5min_data[['MACD3_Line']].iloc[:], current_5min_data[['MACD3_Signal']].iloc[:])
            )

            # **매도 조건 확인**
            sell_condition = (
                current_5min_data['Stage'] == "Stage 3" and
                is_macd_downward(current_5min_data[['MACD1_Line']].iloc[:], current_5min_data[['MACD1_Signal']].iloc[:]) and
                is_macd_downward(current_5min_data[['MACD2_Line']].iloc[:], current_5min_data[['MACD2_Signal']].iloc[:]) and
                is_macd_downward(current_5min_data[['MACD3_Line']].iloc[:], current_5min_data[['MACD3_Signal']].iloc[:])
            )

            current_price_1min = daily_minute1_df['close'].iloc[i]

            # **매수 로직**
            if buy_condition and position == 0:
                buy_price = daily_minute1_df['close'].iloc[i] # 매수 시점은 5분봉 해당 시간에서 1분 지난 1분봉 종가
                N = current_5min_data['ATR']
                if np.isnan(N) or N == 0: # ATR이 NaN이거나 0이면 매수 불가
                    continue
                U = (capital * R) / N
                buy_quantity = U / buy_price
                if buy_quantity > 0: # 매수 수량이 0보다 커야 매수 진행
                    position += buy_quantity
                    units += 1
                    entry_prices.append(buy_price)
                    stop_loss_prices.append(buy_price - 2 * N)
                    trade_log.append({'time': current_time_1min, 'action': 'buy', 'price': buy_price, 'quantity': buy_quantity, 'units': units})
                    print(f"{current_time_1min} Buy at {buy_price}, Quantity: {buy_quantity}, Units: {units}, Stop Loss: {stop_loss_prices[-1]:.2f}")

            # **추가 매수 로직**
            elif position > 0 and units < 4: # 최대 4차 매수
                avg_entry_price = sum(entry_prices) / len(entry_prices)
                if current_price_1min >= avg_entry_price + 0.5 * current_5min_data['ATR']:
                    buy_price = current_price_1min
                    N = current_5min_data['ATR']
                    U = (capital * R) / N
                    buy_quantity = U / buy_price
                    if buy_quantity > 0:
                        position += buy_quantity
                        units += 1
                        entry_prices.append(buy_price)
                        stop_loss_prices.append(entry_prices[-1-1] + 0.5*N - 2*N if units > 1 else buy_price - 2*N) # 스탑로스 갱신 (이전 매수가 + 0.5N - 2N)
                        trade_log.append({'time': current_time_1min, 'action': 'add_buy', 'price': buy_price, 'quantity': buy_quantity, 'units': units})
                        print(f"{current_time_1min} Add Buy at {buy_price}, Quantity: {buy_quantity}, Units: {units}, Stop Loss: {stop_loss_prices[-1]:.2f}")

            # **손절 로직**
            if position > 0:
                for idx, sl_price in enumerate(stop_loss_prices):
                    if current_price_1min <= sl_price:
                        sell_price = current_price_1min
                        sell_quantity = sum(entry_prices[idx:] ) / sell_price if idx > 0 else position # 해당 손절 라인 이후 매수 물량 전체 매도
                        profit = (sell_price - sum(entry_prices[idx:]) / len(entry_prices[idx:])) * sell_quantity if idx > 0 else (sell_price - entry_prices[0]) * position
                        daily_profit += profit
                        trade_log.append({'time': current_time_1min, 'action': 'stop_loss_sell', 'price': sell_price, 'quantity': position, 'profit': profit})
                        print(f"{current_time_1min} Stop Loss Sell at {sell_price}, Profit: {profit:.2f}, Cumulative Daily Profit: {daily_profit:.2f}")
                        position = 0
                        units = 0
                        entry_prices = []
                        stop_loss_prices = []
                        break # 손절 처리 후 루프 탈출

            # **익절 로직**
            if position > 0:
                min_low_12 = daily_minute1_df['low'].iloc[max(0, i-12):i].min() # 최근 12개봉의 최저점 (현재봉 제외)
                if current_price_1min <= min_low_12:
                    sell_price = current_price_1min
                    profit = (sell_price - sum(entry_prices) / len(entry_prices)) * position
                    daily_profit += profit
                    trade_log.append({'time': current_time_1min, 'action': 'profit_sell', 'price': sell_price, 'quantity': position, 'profit': profit})
                    print(f"{current_time_1min} Profit Sell at {sell_price}, Profit: {profit:.2f}, Cumulative Daily Profit: {daily_profit:.2f}")
                    position = 0
                    units = 0
                    entry_prices = []
                    stop_loss_prices = []

            # **매도 로직 (조건 매도)**
            if sell_condition and position > 0:
                sell_price = daily_minute1_df['close'].iloc[i] # 매도 시점은 5분봉 해당 시간에서 1분 지난 1분봉 종가
                profit = (sell_price - sum(entry_prices) / len(entry_prices)) * position
                daily_profit += profit
                trade_log.append({'time': current_time_1min, 'action': 'condition_sell', 'price': sell_price, 'quantity': position, 'profit': profit})
                print(f"{current_time_1min} Condition Sell at {sell_price}, Profit: {profit:.2f}, Cumulative Daily Profit: {daily_profit:.2f}")
                position = 0
                units = 0
                entry_prices = []
                stop_loss_prices = []


        # **오전 8시 51분 종가 매도 (잔량 청산)**
        end_of_day_time = pd.Timestamp(date).replace(hour=8, minute=51) + pd.Timedelta(days=1) # 익일 오전 8시 51분
        if position > 0:
            # 해당 시간의 1분봉 데이터가 있는지 확인
            if end_of_day_time in daily_minute1_df.index:
                end_price = daily_minute1_df.loc[end_of_day_time]['close']
            else: # 해당 시간 1분봉 데이터 없으면, 마지막 1분봉 종가로 청산 (예외 처리)
                end_price = daily_minute1_df['close'].iloc[-1]

            profit = (end_price - sum(entry_prices) / len(entry_prices)) * position
            daily_profit += profit
            trade_log.append({'time': end_of_day_time, 'action': 'forced_sell_851', 'price': end_price, 'quantity': position, 'profit': profit})
            print(f"{end_of_day_time} Forced Sell at 8:51 at {end_price}, Profit: {profit:.2f}, Cumulative Daily Profit: {daily_profit:.2f}")
            position = 0
            units = 0
            entry_prices = []
            stop_loss_prices = []

        daily_results.append({'date': date, 'daily_profit': daily_profit, 'trade_log': trade_log})

    return daily_results

# Main 실행 코드
if __name__ == "__main__":
    file_path = "KRW-BTC.xlsx"  # 엑셀 파일 경로
    results = turtle_trading_strategy(file_path)

    # 결과 출력 (일별 손익)
    print("\n--- Daily Profit/Loss ---")
    total_cumulative_profit = 0
    for result in results:
        daily_profit = result['daily_profit']
        total_cumulative_profit += daily_profit
        print(f"Date: {result['date']}, Daily Profit: {daily_profit:.2f}, Cumulative Profit: {total_cumulative_profit:.2f}")

    print("\n--- Trade Log (Example - First Day) ---")
    if results:
        for log in results[0]['trade_log']: # 첫날의 거래 로그만 예시로 출력
            print(log)