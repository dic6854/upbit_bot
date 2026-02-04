import pandas as pd

file_name = "코인_60분봉_org.xlsx"
df = pd.read_excel(file_name)

df['date'] = pd.to_datetime(df['date'])

buy_df = df[df['date'].dt.hour == 9].copy()
buy_df['date_key'] = buy_df['date'].dt.date

sell_df = df[df['date'].dt.hour == 20].copy()
sell_df['date_key'] = sell_df['date'].dt.date

trade_df = pd.merge(buy_df[['date_key', 'open']], 
                    sell_df[['date_key', 'close']], 
                    on='date_key', 
                    suffixes=('_buy', '_sell'))

initial_capital = 1000000
fee_rate = 0.0005

trade_df['buy_qty'] = (initial_capital / trade_df['open']) * (1 - fee_rate)
trade_df['sell_amount'] = (trade_df['buy_qty'] * trade_df['close']) * (1 - fee_rate)
trade_df['profit'] = trade_df['sell_amount'] - initial_capital

trade_df['month'] = pd.to_datetime(trade_df['date_key']).dt.strftime('%Y-%m')
monthly_stats = trade_df.groupby('month')['profit'].sum().reset_index()

print(trade_df)

print(monthly_stats)

'''
def backtest_strategy(file_path):
    # 1. 엑셀 파일 읽기
    print("파일을 읽는 중입니다...")
    try:
        df = pd.read_excel(file_path)
    except FileNotFoundError:
        print(f"오류: '{file_path}' 파일을 찾을 수 없습니다.")
        return

    # 컬럼명 공백 제거 및 소문자 변환 (오류 방지)
    df.columns = df.columns.str.strip().str.lower()
    
    # 날짜 컬럼을 datetime 형식으로 변환
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
    else:
        print("오류: 데이터에 'date' 컬럼이 없습니다.")
        return

    # 2. 매수/매도 데이터 필터링
    # 매수: 오전 9시
    buy_df = df[df['date'].dt.hour == 9].copy()
    buy_df['date_key'] = buy_df['date'].dt.date  # 매칭을 위한 날짜 키 생성

    # 매도: 오후 9시 (21시)
    sell_df = df[df['date'].dt.hour == 21].copy()
    sell_df['date_key'] = sell_df['date'].dt.date

    # 3. 같은 날짜의 매수/매도 데이터 합치기
    # inner join을 사용하여 9시와 21시 데이터가 모두 존재하는 날만 남김
    trade_df = pd.merge(buy_df[['date_key', 'open']], 
                        sell_df[['date_key', 'open']], 
                        on='date_key', 
                        suffixes=('_buy', '_sell'))

    # 4. 수익금 계산 로직
    initial_capital = 1000000  # 초기 자본금 100만원
    fee_rate = 0.0005          # 수수료 0.05%

    # 매수 수량 계산: (투입금액 / 매수단가) * (1 - 수수료)
    trade_df['buy_qty'] = (initial_capital / trade_df['open_buy']) * (1 - fee_rate)

    # 매도 금액 계산: (매수수량 * 매도단가) * (1 - 수수료)
    trade_df['sell_amount'] = (trade_df['buy_qty'] * trade_df['open_sell']) * (1 - fee_rate)

    # 손익금(Net Profit) 계산
    trade_df['profit'] = trade_df['sell_amount'] - initial_capital

    # 5. 월별 통계 집계
    trade_df['month'] = pd.to_datetime(trade_df['date_key']).dt.strftime('%Y-%m')
    monthly_stats = trade_df.groupby('month')['profit'].sum().reset_index()

    # 결과 출력
    print("\n[월별 수익금 통계]")
    print(monthly_stats)
    
    # 전체 총 손익
    total_profit = trade_df['profit'].sum()
    print(f"\n총 누적 수익금: {total_profit:,.0f}원")

    return monthly_stats

# 실행
file_name = "코인_60분봉_org.xlsx"
backtest_strategy(file_name)
'''