# ATR을 활용한 손절가격 설정
import yfinance as yf
import pandas as pd
import numpy as np

# ATR 계산 함수 설정
def calculate_atr(df, period=14):
    """
    데이터프레임을 받아 ATR(Average True Range)을 계산하여 반환하는 함수
    :param df: High, Low, Close 컬럼이 포함된 DataFrame
    :param period: ATR 계산 기간 (기본 14일)
    :return: ATR 컬럼이 추가된 DataFrame
    """

    # 1. True Range (TR) 계산
    # 수식: Max(고가-저가, |고가-전일종가|, |저가-전일종가|), 세 가지 값 중 최댓값을 TR로 설정
    df['High-Low'] = df['high'] - df['low']
    df['High-PrevClose'] = abs(df['high'] - df['close'].shift(1))
    df['Low-PrevClose'] = abs(df['low'] - df['close'].shift(1))
    
    # 세 가지 값 중 최댓값을 TR로 설정
    df['TR'] = df[['High-Low', 'High-PrevClose', 'Low-PrevClose']].max(axis=1)

    # 2. ATR 계산 (Wilder's Smoothing 기법 사용 - 지수이동평균과 유사)
    # 첫 ATR은 단순 평균으로 구하고, 그 이후는 평활화 적용
    df['ATR'] = df['TR'].ewm(alpha=1/period, adjust=False).mean()

    return df

# ATR 기반의 손절가 구함
def get_stop_loss_price(ticker, entry_price, atr_multiplier=2.0, period=14):
    """
    특정 종목의 현재 ATR을 기반으로 손절가를 계산하는 함수
    :param ticker: 종목 코드 (예: 'AAPL', '005930.KS')
    :param entry_price: 진입(매수) 가격
    :param atr_multiplier: ATR 배수 (보통 1.5 ~ 3.0 사용)
    :param period: ATR 기간
    """
    # 데이터 가져오기 (충분한 기간 확보를 위해 3개월치 로드)
    df = yf.download(ticker, period='3mo', progress=False)

    if df.empty:
        print("데이터를 가져올 수 없습니다.")
        return None

    # ==========================================================
    # ★ [수정] yfinance 데이터 컬럼 정리 (핵심 해결 부분)
    # ==========================================================
    
    # 1) MultiIndex인 경우 (예: ('High', 'AAPL')) 컬럼 하나로 합치기
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)

    # 2) 컬럼 이름을 전부 소문자로 변경 (High -> high)
    df.columns = df.columns.str.lower()
    
    # ==========================================================

    # ATR 계산
    df = calculate_atr(df, period)

    # 가장 최근의 ATR 값 가져오기
    current_atr = df['ATR'].iloc[-1]

    # 롱 포지션(매수) 기준 손절가 계산 공식
    # 손절가 = 진입가 - (ATR * 배수)
    stop_loss_price = entry_price - (current_atr * atr_multiplier)

    return current_atr, stop_loss_price


if __name__ == "__main__":
    # # 1-1. 엑셀파일 읽어들임
    # file_name = "코인_5분봉_test.xlsx"
    # df = pd.read_excel(file_name)
    # df = df.sort_values(by='date', ascending=True).reset_index(drop=True)
    # print("읽어들임 완료!!")

    # df = calculate_atr(df)

    # print(df.head(15))

    # 1. 설정값 입력
    ticker_symbol = "AAPL"  # 애플 (한국 주식은 '005930.KS' 처럼 뒤에 .KS나 .KQ 붙임)
    my_entry_price = 230.0  # 내가 매수한(혹은 매수할) 가격
    multiplier = 2.0        # 손절폭 (ATR의 2배로 설정)

    # 2. 계산 실행
    atr_value, stop_loss = get_stop_loss_price(ticker_symbol, my_entry_price, multiplier)

    # 3. 결과 출력
    print(f"=== [{ticker_symbol}] 손절가 계산 결과 ===")
    print(f"진입 가격: ${my_entry_price}")
    print(f"현재 ATR({14}일 기준): {atr_value:.2f}")
    print(f"적용 배수: x{multiplier}")
    print(f"-" * 30)
    print(f"📉 추천 손절 가격: ${stop_loss:.2f}")
    print(f"손절 시 손실률: -{((my_entry_price - stop_loss) / my_entry_price * 100):.2f}%")