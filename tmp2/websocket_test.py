import multiprocessing as mp
import time
from pyupbit.websocket_api import WebSocketClient

def main():
    # 멀티프로세싱 큐 생성
    queue = mp.Queue()
    
    # 구독할 데이터 유형 및 암호화폐 코드 설정
    type_field = "ticker"  # ticker: 현재가, trade: 체결, orderbook: 호가
    codes = ["KRW-BTC"]    # 비트코인 코드
    
    # 웹소켓 클라이언트 프로세스 생성
    client = mp.Process(
        target=WebSocketClient,
        args=(type_field, codes, queue)
    )
    
    # 프로세스 시작
    client.start()
    print("WebSocket 연결 시작...")
    
    try:
        # 5개의 데이터를 수신하여 출력
        for i in range(5):
            # 큐에서 데이터 가져오기
            data = queue.get()
            
            # 연결 오류 확인
            if data == 'ConnectionClosedError':
                print("연결이 종료되었습니다. 재연결 중...")
                continue
            
            # 수신된 데이터 출력
            print(f"[{i+1}] 수신 데이터:")
            
            # ticker 타입의 주요 필드 출력
            if type_field == "ticker":
                print(f"코드: {data.get('code')}")
                print(f"현재가: {data.get('trade_price'):,}원")
                print(f"전일 대비: {data.get('signed_change_rate')*100:.2f}%")
                print(f"거래량: {data.get('acc_trade_volume_24h'):.4f}")
                print(f"최고가: {data.get('high_price'):,}원")
                print(f"최저가: {data.get('low_price'):,}원")
            else:
                # 다른 타입의 경우 전체 데이터 출력
                print(data)
            
            print("-" * 50)
            
            # 잠시 대기
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("프로그램 종료...")
    
    finally:
        # 프로세스 종료
        client.terminate()
        client.join()
        print("WebSocket 연결 종료")

if __name__ == "__main__":
    main()