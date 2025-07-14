import pyupbit
from datetime import datetime
import os
import json

def get_all_krw_tickers():
    """
    원화 마켓의 모든 티커 목록을 가져오는 함수
    
    Returns:
    list: 원화 마켓 티커 목록
    """
    tickers = pyupbit.get_tickers(fiat="KRW")
    return tickers


def calculate_trend_indicators(ticker, days=30):
    """
    일봉 기준 상승 추세를 판단하기 위한 지표 계산 함수
    
    Parameters:
    ticker (str): 암호화폐 티커
    days (int): 분석할 일수
    
    Returns:
    dict: 상승 추세 관련 지표
    """
    try:
        # 일봉 데이터 가져오기
        df = pyupbit.get_ohlcv(ticker=ticker, interval="day", count=days)
        if df is None or len(df) < 20:
            return None

        # 이동평균선 계산
        df['ma5'] = df['close'].rolling(window=5).mean()
        df['ma10'] = df['close'].rolling(window=10).mean()
        df['ma20'] = df['close'].rolling(window=20).mean()

        # 최근 데이터만 사용
        recent_df = df.iloc[-5:].copy()

        # 상승 추세 지표 계산
        # 1. 현재가가 5일, 10일, 20일 이동평균선 위에 있는지
        price_above_ma5 = recent_df['close'].iloc[-1] > recent_df['ma5'].iloc[-1]
        price_above_ma10 = recent_df['close'].iloc[-1] > recent_df['ma10'].iloc[-1]
        price_above_ma20 = recent_df['close'].iloc[-1] > recent_df['ma20'].iloc[-1]

        # 2. 이동평균선의 기울기 (상승 중인지)
        ma5_slope = (recent_df['ma5'].iloc[-1] - recent_df['ma5'].iloc[0]) / recent_df['ma5'].iloc[0] * 100
        ma10_slope = (recent_df['ma10'].iloc[-1] - recent_df['ma10'].iloc[0]) / recent_df['ma10'].iloc[0] * 100
        ma20_slope = (recent_df['ma20'].iloc[-1] - recent_df['ma20'].iloc[0]) / recent_df['ma20'].iloc[0] * 100

        # 3. 최근 5일간의 상승일 수
        price_changes = recent_df['close'].pct_change()
        up_days = len(price_changes[price_changes > 0])
        
        # 4. 최근 5일간의 평균 거래량 대비 현재 거래량
        avg_volume = recent_df['volume'].mean()
        current_volume = recent_df['volume'].iloc[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 0

        # 5. 최근 상승률
        price_change_5d = (recent_df['close'].iloc[-1] - recent_df['close'].iloc[0]) / recent_df['close'].iloc[0] * 100

        # 결과 반환
        result = {
            'ticker': ticker,
            'price': df['close'].iloc[-1],
            'price_above_ma5': price_above_ma5,
            'price_above_ma10': price_above_ma10,
            'price_above_ma20': price_above_ma20,
            'ma5_slope': ma5_slope,
            'ma10_slope': ma10_slope,
            'ma20_slope': ma20_slope,
            'up_days': up_days,
            'volume_ratio': volume_ratio,
            'price_change_5d': price_change_5d,
            'uptrend_score': 0  # 초기값, 아래에서 계산
        }

        # 상승 추세 점수 계산
        score = 0
        if price_above_ma5: score += 1
        if price_above_ma10: score += 1
        if price_above_ma20: score += 1
        if ma5_slope > 0: score += 1
        if ma10_slope > 0: score += 1
        if ma20_slope > 0: score += 1
        if up_days >= 3: score += 1
        if volume_ratio > 1: score += 1
        if price_change_5d > 0: score += 1
        
        result['uptrend_score'] = score

        return result

    except Exception as e:
        print(f"{ticker} 상승 추세 분석 오류: {e}")
        return None



def select_uptrend_coins(top_n=5, save_results=True):
    """
    일봉 기준 상승 추세에 있는 상위 n개 코인 선정 함수
    
    Parameters:
    top_n (int): 선정할 코인 수
    save_results (bool): 결과를 파일로 저장할지 여부
    
    Returns:
    list: 선정된 코인 티커 목록
    """
    print(f"일봉 기준 상승 추세 코인 {top_n}개 선정 중...") 

    # 원화 마켓 티커 목록 가져오기
    tickers = get_all_krw_tickers()

    # 상승 추세 지표 계산
    trend_results = []
    for ticker in tickers:
        print(f"{ticker} 분석 중...")
        result = calculate_trend_indicators(ticker)
        if result is not None:
            trend_results.append(result)

    # 상승 추세 점수 기준으로 정렬
    sorted_results = sorted(trend_results, key=lambda x: (-x['uptrend_score'], -x['price_change_5d']))

    # 상위 n개 코인 선정
    selected_coins = [result['ticker'] for result in sorted_results[:top_n]]

    # 선정 결과 출력
    print(f"\n===== 선정된 상위 {top_n}개 상승 추세 코인 =====")
    for i, result in enumerate(sorted_results[:top_n], 1):
        print(f"{i}. {result['ticker']}: 점수={result['uptrend_score']}, 5일 변동률={result['price_change_5d']:.2f}%, 가격={result['price']:,.0f}원")

    # 결과 저장
    if save_results:
        save_selected_coins(selected_coins, sorted_results[:top_n])
    
    return selected_coins


def save_selected_coins(selected_coins, detailed_results):
    """
    선정된 코인 정보를 파일로 저장하는 함수
    
    Parameters:
    selected_coins (list): 선정된 코인 티커 목록
    detailed_results (list): 선정된 코인의 상세 정보
    """
    # 저장 디렉토리 생성
    save_dir = "selected_coins"
    os.makedirs(save_dir, exist_ok=True)

    # 현재 날짜 기준 파일명 생성
    today = datetime.now().strftime("%Y-%m-%d")
    file_path = f"{save_dir}/selected_coins_{today}.json"

    # 저장할 데이터 구성
    save_data = {
        "date": today,
        "selected_coins": selected_coins,
        "detailed_results": [
            {
                "ticker": result["ticker"],
                "price": float(result["price"]),
                "uptrend_score": result["uptrend_score"],
                "price_change_5d": float(result["price_change_5d"]),
                "ma5_slope": float(result["ma5_slope"]),
                "ma10_slope": float(result["ma10_slope"]),
                "ma20_slope": float(result["ma20_slope"]),
                "up_days": result["up_days"],
                "volume_ratio": float(result["volume_ratio"])
            }
            for result in detailed_results
        ]
    }

    # JSON 파일로 저장
    with open(file_path, 'w') as f:
        json.dump(save_data, f, indent=4)
    
    print(f"선정된 코인 정보가 저장되었습니다: {file_path}")


def daily_coin_selcetion_and_trading():
    """
    매일 오전 8시 55분에 실행할 코인 선정 및 데이 트레이딩 함수
    
    참고: 실제 스케줄링은 외부 스케줄러(cron 등)를 사용해야 합니다.
    """
    print("일봉 기준 상승 추세 코인 선정 및 데이 트레이딩 시작...")

    # 현재 시간 출력
    now = datetime.now()
    print(f"실행 시간: {now.strftime('%Y-%m-%d %H:%M:%S')}")

    # 상승 추세 코인 5개 선정
    selected_coins = select_uptrend_coins(top_n=5)



if __name__ == "__main__":
    daily_coin_selcetion_and_trading()